---
tier: core
status: core
owner: core-team
verified_on: "2026-07-05"
dotnet_version: "10.0"
bloom: áp dụng
requires: [p6-layered]
est_minutes_fast: 25
---

# Repository & Unit of Work Pattern

!!! info "Bạn đang ở đây"
    cần trước: kiến trúc phân lớp (controller → service → data access), EF Core `DbContext`/`DbSet<T>` cơ bản, dependency injection.
    mở khoá: viết unit test cho Service mà không cần database thật, hiểu vì sao `SaveChangesAsync` chính là một Unit of Work có sẵn, và biết khi nào viết thêm lớp Repository là thừa — khi nào là cần thiết.

> Mục tiêu (đo được): sau chương này bạn **định nghĩa** được Repository pattern và Unit of Work pattern bằng lời của mình, **viết** được một `IProductRepository` tối thiểu và mock nó trong unit test, **giải thích** được vì sao `DbContext.SaveChangesAsync()` của EF Core đã là một Unit of Work có sẵn, và **đánh giá** được khi nào bọc thêm một lớp Repository riêng quanh `DbSet<T>` là thừa (che mất `Include`/projection của EF Core) so với khi nào nó thật sự cần thiết.

---

## 0. Đoán nhanh trước khi học

Bạn có đoạn code Service sau, gọi trực tiếp `AppDbContext` (một `DbContext` của EF Core):

```csharp title="OrderService.cs (hiện trạng)"
// test:skip minh hoa - chua co class AppDbContext/Order day du
public sealed class OrderService(AppDbContext db)
{
    public async Task<decimal> TinhTongDonHang(int orderId)
    {
        var order = await db.Orders.FindAsync(orderId);
        return order?.TongTien ?? 0m;
    }
}
```

Bạn muốn viết **unit test** cho `TinhTongDonHang` — test chạy nhanh, không cần cài SQL Server, không cần connection string.

??? question "Câu hỏi: bạn có test được hàm này mà không có database thật không?"
    **Rất khó, và nếu làm được thì bằng cách bất thường.** `AppDbContext` là một class cụ thể (concrete class) gắn liền với provider database thật (SQL Server, PostgreSQL...). Muốn "giả" nó trong test, bạn phải dùng `DbContextOptionsBuilder.UseInMemoryDatabase(...)` — nghĩa là **vẫn cần một database** (dù là in-memory), chỉ là nhẹ hơn SQL Server. Bạn **không mock được** `AppDbContext` một cách tự nhiên bằng các thư viện mock thông thường (Moq, NSubstitute) vì các phương thức của `DbSet<T>` không phải `virtual` theo cách dễ mock, và nhiều thứ (LINQ provider, transaction) chỉ hoạt động đúng khi có context thật phía sau.

    Mục 1–2 sẽ chỉ ra: nếu `OrderService` phụ thuộc vào một **interface** (không phụ thuộc trực tiếp `AppDbContext`), bạn mock được interface đó bằng một dòng code, test chạy trong vài milliseconds, không cần database ở bất kỳ dạng nào.

---

## 1. Repository pattern — định nghĩa và ví dụ tối thiểu

**Định nghĩa (một câu):** Repository pattern là một **interface trừu tượng hoá việc truy cập dữ liệu** (đọc/ghi một loại đối tượng) — code nghiệp vụ (business logic) gọi qua interface này, hoàn toàn không biết dữ liệu đến từ EF Core, SQL thô, hay một API bên ngoài.

Ví dụ tối thiểu, độc lập — một interface và một cách triển khai dùng EF Core:

```csharp title="IProductRepository.cs"
// test:compile
public sealed class Product
{
    public int Id { get; set; }
    public string Ten { get; set; } = "";
    public decimal Gia { get; set; }
}

public interface IProductRepository
{
    Task<Product?> LayTheoId(int id);
    Task<List<Product>> LayTatCa();
    void Them(Product product);
}
```

```csharp title="EfProductRepository.cs"
// test:skip minh hoa - AppDbContext chua duoc dinh nghia day du trong pham vi bai nay
using Microsoft.EntityFrameworkCore;

public sealed class EfProductRepository(AppDbContext db) : IProductRepository
{
    public async Task<Product?> LayTheoId(int id) =>
        await db.Products.FindAsync(id);

    public async Task<List<Product>> LayTatCa() =>
        await db.Products.ToListAsync();

    public void Them(Product product) => db.Products.Add(product);
}
```

Điểm mấu chốt: `IProductRepository` **không nhắc gì đến EF Core**. Nó chỉ nói "tôi lấy được một `Product` theo id", "tôi lấy được danh sách", "tôi thêm được một `Product`". `EfProductRepository` là **một cách** triển khai cụ thể — có thể có `SqlProductRepository`, `FakeProductRepository` khác, miễn là cùng thực hiện đúng interface.

!!! danger "Hiểu sai phổ biến: Repository = 'lớp bọc CRUD quanh bảng'"
    Nhiều người học Repository pattern nghĩ nó chỉ là "viết thêm một class có `Get`/`Add`/`Update`/`Delete` gọi `DbContext`" — đúng về hình thức nhưng **sai về mục đích**. Mục đích thật của pattern là **trừu tượng hoá** (business logic không biết chi tiết lưu trữ), không phải "thêm một lớp cho có". Mục 4 sẽ chỉ rõ: nếu Repository của bạn chỉ là CRUD generic gọi thẳng `DbSet<T>` không thêm giá trị gì, bạn đã trả giá (thêm code, mất tính năng EF Core) mà không nhận lại lợi ích trừu tượng hoá thật sự.

---

## 2. Vấn đề cụ thể Repository giải quyết — unit test không cần database

Đây là vấn đề mục 0 nêu ra: `OrderService` phụ thuộc trực tiếp `AppDbContext` nên không mock được dễ dàng. Sửa lại bằng cách cho `OrderService` phụ thuộc `IProductRepository` (interface) thay vì `AppDbContext` (class cụ thể):

```csharp title="OrderService.cs (dung Repository)"
// test:run
// --- Chạy thử như một unit test viết tay, không dùng framework test ---
// (Top-level statement PHẢI đứng trước mọi khai báo class/interface trong file .cs)
var service = new OrderService(new FakeProductRepository());
var gia = await service.TinhGiaVoiThue(1);
Console.WriteLine($"Gia sau thue: {gia}"); // ky vong: 110.0

if (gia != 110m)
    throw new Exception($"Test FAIL: ky vong 110, duoc {gia}");
Console.WriteLine("Test PASS");

public sealed class Product
{
    public int Id { get; set; }
    public string Ten { get; set; } = "";
    public decimal Gia { get; set; }
}

public interface IProductRepository
{
    Task<Product?> LayTheoId(int id);
}

// Service CHỈ phụ thuộc interface — không biết Product đến từ đâu.
public sealed class OrderService(IProductRepository repo)
{
    public async Task<decimal> TinhGiaVoiThue(int productId)
    {
        var product = await repo.LayTheoId(productId);
        if (product is null) return 0m;
        return product.Gia * 1.1m; // thuế 10%, ví dụ đơn giản
    }
}

// "Fake" repository viết tay - KHÔNG cần thư viện mock, KHÔNG cần database.
public sealed class FakeProductRepository : IProductRepository
{
    private readonly Dictionary<int, Product> _data = new()
    {
        [1] = new Product { Id = 1, Ten = "Ban phim", Gia = 100m },
    };

    public Task<Product?> LayTheoId(int id) =>
        Task.FromResult(_data.GetValueOrDefault(id));
}
```

Kết quả kỳ vọng khi chạy:

```text title="output"
Gia sau thue: 110.0
Test PASS
```

So sánh trực tiếp với vấn đề ở mục 0: `FakeProductRepository` là một class C# thuần, không cần EF Core, không cần connection string, không cần cài database, chạy trong vài milliseconds. `OrderService` không biết (và không cần biết) `Product` id=1 đến từ một `Dictionary` trong bộ nhớ hay từ SQL Server — nó chỉ gọi qua `IProductRepository`. Đây chính là giá trị cốt lõi Repository pattern mang lại: **thay thế được implementation** mà không sửa code nghiệp vụ.

!!! warning "Interface phải do bên tiêu thụ định nghĩa vừa đủ"
    `IProductRepository` chỉ nên có các phương thức `OrderService` (và các service khác thật sự dùng) cần — không nên "thêm sẵn cho đủ" `Update`, `Delete`, `LayTheoTen`... nếu chưa ai gọi. Interface phình to không dùng hết là dấu hiệu vi phạm Interface Segregation Principle (đã học ở phần SOLID) — ở đây ta chỉ nhắc lại ngắn ở mức kiến trúc: mỗi interface Repository nên khớp đúng nhu cầu thật của caller, không phải khớp "mọi khả năng CRUD có thể có".

---

## 3. Unit of Work — định nghĩa và ví dụ có sẵn trong EF Core

**Định nghĩa (một câu):** Unit of Work là một pattern **gom nhiều thay đổi dữ liệu** (thêm, sửa, xoá trên nhiều bảng/nhiều đối tượng) thành **một giao dịch (transaction)** được lưu **một lần** — nếu bất kỳ thay đổi nào thất bại, toàn bộ nhóm thay đổi đó bị huỷ (rollback), không để dữ liệu ở trạng thái nửa-lưu.

Vấn đề cụ thể nó giải quyết: giả sử bạn cần chuyển tiền giữa hai tài khoản — trừ tiền tài khoản A, cộng tiền tài khoản B. Nếu bạn lưu riêng lẻ hai bước (gọi `SaveChanges` hai lần), và bước cộng tiền B thất bại (mất kết nối, exception) sau khi bước trừ tiền A đã lưu thành công, dữ liệu rơi vào trạng thái sai: tiền đã mất khỏi A nhưng chưa đến B.

```csharp title="ChuyenTien.cs"
// test:skip minh hoa - AppDbContext/TaiKhoan chua dinh nghia day du trong pham vi bai nay
public sealed class ChuyenTienService(AppDbContext db)
{
    public async Task ChuyenTien(int idNguon, int idDich, decimal soTien)
    {
        var nguon = await db.TaiKhoans.FindAsync(idNguon);
        var dich = await db.TaiKhoans.FindAsync(idDich);
        if (nguon is null || dich is null) throw new InvalidOperationException("Khong tim thay tai khoan");

        nguon.SoDu -= soTien;
        dich.SoDu += soTien;

        // MỘT lần SaveChangesAsync duy nhất cho CẢ HAI thay đổi.
        // EF Core tự gói tất cả thay đổi đang theo dõi (change tracker) vào
        // MỘT transaction database khi gọi SaveChangesAsync — đây CHÍNH LÀ
        // Unit of Work, không cần bạn viết thêm class "UnitOfWork" nào cả.
        await db.SaveChangesAsync();
    }
}
```

Nếu `dich.SoDu += soTien` không được lưu (ví dụ ràng buộc database từ chối), thì thay đổi `nguon.SoDu -= soTien` **cũng không được lưu** — vì cả hai nằm trong cùng một lệnh `SaveChangesAsync`, tức cùng một transaction. `DbContext` theo dõi (change tracking) mọi thay đổi trên các entity đã load, và khi bạn gọi `SaveChangesAsync()`, nó sinh ra đúng các câu lệnh `UPDATE` cần thiết, gói trong một transaction, gửi đi cùng lúc.

!!! danger "Nếu hiểu sai — gọi `SaveChanges` nhiều lần rời rạc"
    Nếu bạn gọi `SaveChangesAsync()` ngay sau `nguon.SoDu -= soTien` (trước khi sửa `dich`), bạn đã **tự tay phá vỡ** Unit of Work — biến hai thay đổi liên quan thành hai giao dịch độc lập. Nếu bước thứ hai thất bại, tiền đã "biến mất" khỏi tài khoản nguồn mà không đến tài khoản đích — một lỗi nghiệp vụ nghiêm trọng, và rất khó phát hiện vì không có exception nào ở bước đầu.

---

## 4. CẢNH BÁO QUAN TRỌNG — với EF Core, viết Repository riêng thường là THỪA

Đây là điểm dễ nhầm nhất khi học hai pattern này cùng lúc: **`DbContext` của EF Core đã LÀ một Unit of Work, và mỗi `DbSet<T>` đã LÀ một Repository-like abstraction có sẵn.** Chương [kiến trúc phân lớp](kien-truc-phan-lop.md) mục 6 đã đi qua ví dụ đầy đủ cho đúng cảnh báo này (Repository generic bọc `DbSet<T>` làm mất `Include`/projection mà không thêm giá trị trừu tượng hoá thật) — không lặp lại ở đây, chỉ tóm tắt kết luận thực dụng: nếu Repository riêng của bạn chỉ có `Add`/`Get`/`Update`/`Delete` gọi thẳng `DbSet<T>` mà không thêm logic gì, nó **không** đạt mục tiêu trừu tượng hoá thật mà **lại mất** những tính năng mạnh nhất của EF Core — over-engineering kinh điển.

!!! warning "Vậy khi nào Repository riêng THẬT SỰ hữu ích?"
    Hai trường hợp cụ thể:

    1. **Logic query phức tạp được tái sử dụng ở nhiều nơi.** Ví dụ `LayDonHangDangXuLyTrongThang(int nam, int thang)` với `Include` + `Where` + sắp xếp phức tạp, được gọi từ 5 controller/service khác nhau — gói nó trong `IOrderRepository.LayDonHangDangXuLyTrongThang(...)` giúp không lặp code, và nếu logic đó cần đổi (thêm điều kiện lọc), sửa một nơi.
    2. **Thật sự cần đổi database provider** hoặc cần một lớp trừu tượng để mock hoàn toàn trong test mà không dùng InMemory provider của EF Core — ví dụ hệ thống có thể chạy trên SQL Server hoặc PostgreSQL tuỳ khách hàng, và bạn muốn nghiệp vụ hoàn toàn không đụng tới chi tiết EF Core.

    Nếu không rơi vào hai trường hợp trên, dùng `DbContext`/`DbSet<T>` trực tiếp trong lớp Service (đã học ở kiến trúc phân lớp) là lựa chọn đơn giản, đủ tốt, và không mất tính năng EF Core.

---

## 5. Repository "đặc thù" đúng cách — khi logic query thật sự phức tạp

Mục 4 đã chỉ ra Repository generic (CRUD đơn giản) thường thừa. Nhưng khi rơi vào trường hợp (1) ở mục 4 — logic query phức tạp lặp lại nhiều nơi — cách viết Repository **đúng** không phải là bọc generic quanh `DbSet<T>`, mà là viết một interface **đặc thù cho từng entity**, với các phương thức phản ánh đúng câu hỏi nghiệp vụ, bên trong tự do dùng hết sức mạnh của `IQueryable<T>`.

**Định nghĩa (một câu) — Repository đặc thù (specific repository):** là một interface Repository được thiết kế riêng cho một entity, có các phương thức đặt tên theo **câu hỏi nghiệp vụ** (không phải theo động từ CRUD chung), và bên trong triển khai được dùng tự do `Include`, `Select`, `Where`, `OrderBy`, `AsNoTracking` của EF Core.

```csharp title="IOrderRepository.cs (dac thu - dung cach)"
// test:skip minh hoa - Order/Product/AppDbContext chua dinh nghia day du trong pham vi bai nay
public sealed class OrderSummary
{
    public int OrderId { get; set; }
    public string TenSanPham { get; set; } = "";
    public decimal TongTien { get; set; }
}

// Mỗi phương thức là MỘT câu hỏi nghiệp vụ cụ thể — không phải CRUD chung.
public interface IOrderRepository
{
    Task<List<OrderSummary>> LayDonHangDangXuLyTrongThang(int nam, int thang);
    Task<Order?> LayDonHangKemChiTietSanPham(int orderId);
}

public sealed class EfOrderRepository(AppDbContext db) : IOrderRepository
{
    public async Task<List<OrderSummary>> LayDonHangDangXuLyTrongThang(int nam, int thang) =>
        await db.Orders
            .Where(o => o.TrangThai == "DangXuLy"
                     && o.NgayTao.Year == nam
                     && o.NgayTao.Month == thang)
            .OrderByDescending(o => o.NgayTao)
            .Select(o => new OrderSummary
            {
                OrderId = o.Id,
                TenSanPham = o.Product!.Ten,
                TongTien = o.TongTien,
            })
            .AsNoTracking() // chỉ đọc, không cần change tracking -> nhanh hơn
            .ToListAsync();

    public async Task<Order?> LayDonHangKemChiTietSanPham(int orderId) =>
        await db.Orders
            .Include(o => o.Product)
            .FirstOrDefaultAsync(o => o.Id == orderId);
}
```

Khác biệt cốt lõi so với `GenericRepository<T>` ở mục 4: `IOrderRepository` **không cố tổng quát hoá** cho mọi entity — nó chỉ có hai phương thức, đặt tên theo đúng câu hỏi nghiệp vụ (`LayDonHangDangXuLyTrongThang`, không phải `GetAll` rồi filter ở tầng gọi), và bên trong triển khai tự do dùng `Include`/`Select`/`AsNoTracking` — không bị giới hạn bởi một interface generic chỉ trả `T` nguyên vẹn. Nếu logic lọc "đơn hàng đang xử lý trong tháng" cần đổi (ví dụ thêm điều kiện "chưa quá hạn thanh toán"), sửa **một nơi** — `EfOrderRepository` — mọi caller (5 controller/service khác nhau) tự động nhận thay đổi đúng, không phải rà soát từng nơi copy-paste LINQ.

!!! warning "Repository đặc thù khác Repository generic ở điểm nào — dễ nhầm"
    Cả hai đều là "một class implement một interface, gọi `DbContext` bên trong" — nhìn hình thức giống nhau. Khác biệt nằm ở **thiết kế interface**: generic (mục 4) có phương thức đặt tên theo động từ CRUD chung (`GetById`, `Update`) áp dụng cho **mọi** entity `T` — nên bắt buộc phải trả về `T` nguyên vẹn, không projection được. Đặc thù (mục 5) có phương thức đặt tên theo **câu hỏi nghiệp vụ cụ thể** của **một** entity — nên tự do trả về `OrderSummary` (projection), `List<Order>` kèm `Include`, hay bất kỳ hình dạng dữ liệu phù hợp nhất với câu hỏi đó. Đây là lý do Repository đặc thù không che mất tính năng EF Core, còn generic thì có.

---

## 6. `IUnitOfWork` tường minh — khi nào cần, và ví dụ tối thiểu

Mục 3 đã chỉ ra `DbContext.SaveChangesAsync()` đã là Unit of Work có sẵn — với **một** `DbContext`, bạn không cần viết thêm gì. Nhưng khi một nghiệp vụ cần phối hợp **nhiều Repository đặc thù** (mục 5) cùng lúc, và bạn muốn tầng Service không tự tay gọi `SaveChangesAsync()` trên `DbContext` (để giữ Service hoàn toàn không biết EF Core tồn tại), một interface `IUnitOfWork` tường minh, mỏng, có thể hữu ích.

**Định nghĩa (một câu):** `IUnitOfWork` tường minh là một interface gom quyền truy cập tới các Repository liên quan và **một** phương thức `LuuThayDoi()` duy nhất — bên dưới, phương thức đó chỉ gọi `SaveChangesAsync()` của **cùng một** `DbContext` mà mọi Repository đang dùng, đảm bảo mọi thay đổi từ các Repository khác nhau được lưu trong **một** transaction.

```csharp title="IUnitOfWork.cs"
// test:skip minh hoa - AppDbContext/IOrderRepository/IProductRepository chua day du
public interface IUnitOfWork
{
    IOrderRepository Orders { get; }
    IProductRepository Products { get; }
    Task<int> LuuThayDoi();
}

public sealed class EfUnitOfWork(AppDbContext db) : IUnitOfWork
{
    // Tạo Repository LƯỜI (lazy) khi lần đầu truy cập, tái dùng cho các lần sau
    // trong cùng một instance EfUnitOfWork — mọi Repository CHIA SẺ chung db.
    private IOrderRepository? _orders;
    private IProductRepository? _products;

    public IOrderRepository Orders => _orders ??= new EfOrderRepository(db);
    public IProductRepository Products => _products ??= new EfProductRepository(db);

    // Chỉ gọi ĐÚNG MỘT SaveChangesAsync của DbContext dùng chung -
    // đây KHÔNG phải Unit of Work "tự chế" mới, chỉ là bọc lại cái EF Core đã có sẵn.
    public Task<int> LuuThayDoi() => db.SaveChangesAsync();
}
```

Điểm mấu chốt cần thấy rõ: `EfUnitOfWork.LuuThayDoi()` **không tự viết logic transaction** — nó chỉ gọi `db.SaveChangesAsync()`, đúng cơ chế Unit of Work có sẵn từ mục 3. Giá trị thật của `IUnitOfWork` ở đây **không phải** "thêm khả năng transaction mới", mà là: (1) Service chỉ phụ thuộc `IUnitOfWork` + các Repository interface, hoàn toàn không `using Microsoft.EntityFrameworkCore`, không biết `DbContext` tồn tại; và (2) đảm bảo `Orders` và `Products` trong cùng một `IUnitOfWork` instance chắc chắn dùng chung một `AppDbContext` — tránh đúng lỗi nêu ở "Cạm bẫy" cuối bài (mỗi Repository tự inject `DbContext` riêng, phá vỡ transaction gộp).

```csharp title="ChuyenDoiSanPham.cs - Service dung IUnitOfWork"
// test:skip minh hoa - can IOrderRepository/IProductRepository/Order/Product day du
public sealed class DonHangService(IUnitOfWork uow)
{
    public async Task DanhDauDaGiao(int orderId)
    {
        var order = await uow.Orders.LayDonHangKemChiTietSanPham(orderId);
        if (order is null) throw new InvalidOperationException("Khong tim thay don hang");

        order.TrangThai = "DaGiao";
        // Nếu nghiệp vụ này còn cần sửa Product (ví dụ giảm SoLuongTonKho),
        // sửa qua uow.Products ở đây — VẪN chỉ gọi LuuThayDoi() một lần cuối.

        await uow.LuuThayDoi(); // MỘT lần lưu, gộp mọi thay đổi trên Order (và Product nếu có)
    }
}
```

!!! danger "Sai lầm phổ biến: mỗi Repository tự `new` hoặc tự inject `DbContext` riêng"
    Nếu `EfOrderRepository` và `EfProductRepository` **không** được tạo qua cùng một `EfUnitOfWork` (ví dụ Service inject trực tiếp `IOrderRepository` và `IProductRepository` từ DI container mà **không** đi qua `IUnitOfWork`, và container cấu hình sai lifetime), mỗi Repository có thể nhận một `DbContext` **khác nhau** (nếu đăng ký `Transient` thay vì `Scoped`, hoặc nếu vô tình `new AppDbContext()` bên trong Repository). Khi đó, sửa `Order` qua repository A rồi gọi `SaveChangesAsync()` của `DbContext` A **không hề ảnh hưởng** tới thay đổi `Product` đang nằm trong `DbContext` B chưa lưu — mất chính xác lợi ích Unit of Work mục 3 đã giải thích. Cách tránh: đăng ký `AppDbContext` là `Scoped` (mặc định của `AddDbContext`), và để mọi Repository trong cùng một `IUnitOfWork` instance dùng chung tham số `db` được inject — đúng như `EfUnitOfWork` ở trên.

!!! warning "`IUnitOfWork` tường minh có thừa không? — áp lại tiêu chí over-engineering"
    Nếu ứng dụng của bạn chỉ có **một** `DbContext` và Service chỉ cần gọi **một** Repository cho mỗi nghiệp vụ (không phối hợp nhiều Repository), viết thêm `IUnitOfWork` là thừa — Service tiêm trực tiếp Repository đó, và Repository tự gọi `SaveChangesAsync()` trên `DbContext` nó nhận (như `EfProductRepository.Them()` có thể tự `db.SaveChangesAsync()` nếu cần, hoặc để tầng gọi tự quyết định thời điểm lưu). `IUnitOfWork` chỉ đáng viết khi thật sự có nhiều Repository đặc thù (mục 5) cần phối hợp trong cùng một giao dịch, và bạn muốn Service hoàn toàn không biết `DbContext` tồn tại.

---

## 7. Đăng ký Repository & Unit of Work với Dependency Injection

Repository và `IUnitOfWork` là interface — chúng cần được đăng ký vào DI container để ASP.NET Core biết class nào triển khai interface nào. Đây chỉ là áp dụng lại kiến thức DI đã học, không phải khái niệm mới, nhưng cần đúng **lifetime** để không lặp lại sai lầm ở mục 6.

```csharp title="Program.cs (trich - dang ky Repository + UnitOfWork)"
// test:skip minh hoa - can AppDbContext/cac Repository/UnitOfWork day du dinh nghia
var builder = WebApplication.CreateBuilder(args);

// AddDbContext mặc định đăng ký DbContext với lifetime Scoped -
// ĐÚNG mặc định cần cho web app: một DbContext dùng suốt MỘT request HTTP.
builder.Services.AddDbContext<AppDbContext>(options =>
    options.UseSqlServer(builder.Configuration.GetConnectionString("Default")));

// Repository PHẢI Scoped (khớp lifetime của AppDbContext nó phụ thuộc) -
// KHÔNG được Singleton (Repository sẽ giữ một DbContext cũ suốt đời app,
// gây lỗi "Cannot access a disposed context" sau request đầu tiên).
builder.Services.AddScoped<IOrderRepository, EfOrderRepository>();
builder.Services.AddScoped<IProductRepository, EfProductRepository>();
builder.Services.AddScoped<IUnitOfWork, EfUnitOfWork>();

builder.Services.AddScoped<DonHangService>();

var app = builder.Build();
app.Run();
```

!!! danger "Đăng ký sai lifetime — lỗi cụ thể xảy ra"
    Nếu bạn đăng ký `IOrderRepository` là `Singleton` (chỉ tạo một lần, dùng suốt đời ứng dụng) trong khi `AppDbContext` là `Scoped` (một instance mỗi request), ASP.NET Core sẽ ném `InvalidOperationException` ngay khi khởi động, với thông báo dạng **"Cannot consume scoped service ... from singleton"** — vì Singleton sống lâu hơn Scoped, không thể "giữ" một dependency có đời sống ngắn hơn mình. Nếu bạn né lỗi này bằng cách nào đó (ví dụ resolve thủ công qua `IServiceScopeFactory`), hậu quả tệ hơn: Repository giữ một `AppDbContext` từ request đầu tiên, dùng lại cho mọi request sau — request thứ hai sẽ gặp `ObjectDisposedException` (context đã bị dispose cuối request đầu) hoặc dữ liệu cũ/sai vì change tracker còn giữ entity từ request trước.

!!! note "Lưu ý thuật ngữ: Singleton pattern (GoF) khác Singleton lifetime (DI container)"
    Đừng nhầm hai khái niệm tên giống nhau nhưng khác hẳn phạm vi. **Singleton pattern** (một trong các Design Pattern gốc của GoF — Gang of Four) là một khuôn mẫu viết code: tự tay đảm bảo một class chỉ có **đúng một instance** trong toàn bộ vòng đời ứng dụng, thường qua constructor `private` + một property `static` trả về instance duy nhất đó — tự class đó tự quản lý việc chỉ-có-một-bản. **Singleton lifetime** (`builder.Services.AddSingleton<...>()`) là một tuỳ chọn cấu hình của **DI container**: container tự tạo instance một lần và trả lại instance đó cho mọi nơi yêu cầu — bản thân class được đăng ký không cần biết gì về việc "mình chỉ có một bản", container lo hộ. Trong ví dụ mục 7, câu cảnh báo về lifetime nói về **Singleton lifetime của DI container**, không liên quan gì tới việc tự viết Singleton pattern (GoF) cho `EfOrderRepository` — hai thứ giải quyết hai vấn đề khác nhau và không nên lẫn khi trao đổi với đồng nghiệp.

### Kiểm tra thủ công ý nghĩa "Scoped" — chạy được ngay, không cần DI container thật

Đoạn code sau **không** dùng `Microsoft.Extensions.DependencyInjection` thật (đó là một NuGet package, chỉ dùng được khi build trong project ASP.NET Core) — nó tự dựng một "mini-scope" chỉ bằng BCL để chứng minh đúng ý nghĩa của Scoped lifetime mà mục 7 vừa nhắc tới: **mỗi scope (request) phải nhận một instance riêng**, không chia sẻ giữa các scope khác nhau.

```csharp title="KiemTraScoped.cs"
// test:run
// --- Mô phỏng HAI request HTTP khác nhau bằng HAI "scope" tự tạo ---
var scope1 = new MiniScope();
var dbTrongRequest1 = scope1.LayDbContext();

var scope2 = new MiniScope();
var dbTrongRequest2 = scope2.LayDbContext();

Console.WriteLine($"DbContext id trong request 1: {dbTrongRequest1.InstanceId}");
Console.WriteLine($"DbContext id trong request 2: {dbTrongRequest2.InstanceId}");
Console.WriteLine($"Hai request co dung CHUNG mot DbContext khong: {dbTrongRequest1 == dbTrongRequest2}");

if (dbTrongRequest1 == dbTrongRequest2)
    throw new Exception("Test FAIL: hai scope khac nhau khong nen chia se DbContext");
Console.WriteLine("Test PASS: moi scope (request) co DbContext RIENG, dung nhu Scoped lifetime");

// Fake "DbContext" tối giản chỉ để minh hoạ vòng đời Scoped -
// không phải EF Core thật, nhưng đủ để chứng minh hành vi lifetime.
public sealed class FakeDbContext
{
    public Guid InstanceId { get; } = Guid.NewGuid();
}

// Mô phỏng đúng cơ chế AddScoped<T>() của DI container thật: TRONG một scope,
// gọi lại LayDbContext() nhiều lần vẫn trả về CÙNG một instance (được cache);
// nhưng MỖI scope MỚI (mỗi MiniScope() mới) tạo ra một instance HOÀN TOÀN mới.
public sealed class MiniScope
{
    private FakeDbContext? _cached;
    public FakeDbContext LayDbContext() => _cached ??= new FakeDbContext();
}
```

Kết quả kỳ vọng (GUID cụ thể sẽ khác mỗi lần chạy, nhưng luôn khác nhau giữa hai request):

```text title="output"
DbContext id trong request 1: <guid-A>
DbContext id trong request 2: <guid-B>
Hai request co dung CHUNG mot DbContext khong: False
Test PASS: moi scope (request) co DbContext RIENG, dung nhu Scoped lifetime
```

`MiniScope` ở đây chỉ là một mô hình thu nhỏ, tự viết bằng BCL thuần — DI container thật của ASP.NET Core (`AddScoped<T>()`) làm đúng nguyên lý này nhưng phức tạp hơn (quản lý nhiều type, tự resolve dependency lồng nhau, tích hợp với pipeline HTTP request). Điểm cốt lõi cần thấy: mỗi `IServiceScope` thật (tương ứng một request HTTP) hoạt động giống `MiniScope` ở trên — cache instance **trong** scope đó, nhưng **không chia sẻ** giữa các scope khác nhau. Nếu `IOrderRepository` được đăng ký `AddSingleton` thay vì `AddScoped`, nó sẽ hành xử như thể chỉ có **một `MiniScope` duy nhất cho toàn bộ ứng dụng** — cache đúng một `AppDbContext` mãi mãi, đúng nguyên nhân của lỗi "Cannot consume scoped service from singleton" hoặc `ObjectDisposedException` đã nêu ở khối cảnh báo phía trên.

---

## 8. So sánh tổng hợp — bốn cách tổ chức tầng data access

Sau khi đã học đủ Repository (đặc thù và generic), Unit of Work (có sẵn và tường minh), giờ mới đến lúc so sánh tổng hợp để chọn đúng cách cho từng tình huống:

| Cách tổ chức | Khi nào phù hợp | Test không cần database? | Rủi ro chính |
|---|---|---|---|
| **`DbContext`/`DbSet<T>` trực tiếp trong Service** | CRUD đơn giản, không logic query lặp lại, một Controller/Service gọi | Khó — cần InMemory provider hoặc SQLite in-memory | Không có — đây là baseline đơn giản nhất |
| **Repository generic (`IGenericRepository<T>`)** | Hầu như không có tình huống lý tưởng với EF Core (xem mục 4) | Khó tương tự trực tiếp — không thêm lợi ích | Che mất `Include`/projection; ảo tưởng đã "trừu tượng hoá" nhưng chưa |
| **Repository đặc thù (`IOrderRepository`...)** | Logic query phức tạp lặp lại ≥ 3 nơi, hoặc cần mock hoàn toàn trong test | Dễ — mock/fake interface đơn giản | Nếu lạm dụng cho cả CRUD đơn giản, thừa công sức thiết kế |
| **Repository đặc thù + `IUnitOfWork` tường minh** | Nhiều Repository đặc thù cần phối hợp cùng giao dịch, Service phải hoàn toàn không biết EF Core | Dễ nhất — mock cả `IUnitOfWork` | Thừa nếu chỉ có một `DbContext` và không cần phối hợp nhiều Repository |

Không có lựa chọn nào "luôn đúng" — bảng trên là công cụ quyết định theo **tình huống thật**, không phải thứ hạng "cái nào cao cấp hơn cái nào". Một project nhỏ dùng thẳng `DbSet<T>` cho 90% màn hình CRUD, và chỉ tách Repository đặc thù cho đúng 1-2 nghiệp vụ có query phức tạp lặp lại, là một quyết định kiến trúc **tốt** — không phải "làm dở vì lười".

### Chứng minh khép lại vòng lặp mục 0 — test toàn bộ `DonHangService` không cần database

Mục 0 mở đầu bằng vấn đề: `OrderService` gọi trực tiếp `AppDbContext` nên khó test. Sau khi đã học đủ Repository đặc thù (mục 5) và `IUnitOfWork` (mục 6), đoạn code sau chứng minh **toàn bộ** một nghiệp vụ nhiều bước (giống `DonHangService.DanhDauDaGiao` ở mục 6) test được hoàn toàn trong bộ nhớ:

```csharp title="KiemTraDonHangService.cs"
// test:run
var fakeUow = new FakeUnitOfWork();
var service = new DonHangService(fakeUow);

await service.DanhDauDaGiao(1);

Console.WriteLine($"Trang thai don hang sau khi xu ly: {fakeUow.OrdersFake.Data[1].TrangThai}");
Console.WriteLine($"So lan goi LuuThayDoi: {fakeUow.SoLanLuu}");

if (fakeUow.OrdersFake.Data[1].TrangThai != "DaGiao")
    throw new Exception("Test FAIL: trang thai chua duoc cap nhat dung");
if (fakeUow.SoLanLuu != 1)
    throw new Exception("Test FAIL: LuuThayDoi phai duoc goi DUNG MOT LAN");
Console.WriteLine("Test PASS");

public sealed class Order
{
    public int Id { get; set; }
    public string TrangThai { get; set; } = "";
}

public interface IOrderRepository
{
    Task<Order?> LayTheoId(int id);
}

public interface IUnitOfWork
{
    IOrderRepository Orders { get; }
    Task<int> LuuThayDoi();
}

public sealed class DonHangService(IUnitOfWork uow)
{
    public async Task DanhDauDaGiao(int orderId)
    {
        var order = await uow.Orders.LayTheoId(orderId);
        if (order is null) throw new InvalidOperationException("Khong tim thay don hang");

        order.TrangThai = "DaGiao";
        await uow.LuuThayDoi();
    }
}

// --- Fake toàn bộ: KHÔNG một dòng nào chạm EF Core hay database thật ---
public sealed class FakeOrderRepository : IOrderRepository
{
    public Dictionary<int, Order> Data { get; } = new()
    {
        [1] = new Order { Id = 1, TrangThai = "DangGiao" },
    };

    public Task<Order?> LayTheoId(int id) => Task.FromResult(Data.GetValueOrDefault(id));
}

public sealed class FakeUnitOfWork : IUnitOfWork
{
    public FakeOrderRepository OrdersFake { get; } = new();
    public IOrderRepository Orders => OrdersFake;
    public int SoLanLuu { get; private set; }

    public Task<int> LuuThayDoi()
    {
        SoLanLuu++; // đếm số lần "lưu" được gọi - kiểm tra đúng MỘT lần
        return Task.FromResult(1);
    }
}
```

Kết quả kỳ vọng:

```text title="output"
Trang thai don hang sau khi xu ly: DaGiao
So lan goi LuuThayDoi: 1
Test PASS
```

So sánh trực tiếp với câu hỏi mục 0 ("bạn có test được hàm này mà không có database thật không?"): câu trả lời giờ là **có, hoàn toàn** — không `UseInMemoryDatabase`, không SQLite in-memory, không connection string ở bất kỳ dạng nào. `FakeUnitOfWork.SoLanLuu` còn cho phép kiểm tra một chi tiết mà test dựa trên database thật khó kiểm tra trực tiếp: **đúng một lần** `SaveChangesAsync()`-tương-đương được gọi, đúng nguyên tắc Unit of Work ở mục 3 — nếu ai đó vô tình sửa `DonHangService` gọi `LuuThayDoi()` hai lần rời rạc, test này sẽ bắt được ngay (`SoLanLuu` sẽ là 2, không phải 1).

---

## Cạm bẫy & thực chiến

- **Viết Generic Repository bọc `DbSet<T>` "cho chuẩn kiến trúc" ngay từ đầu, dù chưa có nhu cầu:** che mất `Include`/projection, thêm code phải duy trì, không nhận lại lợi ích trừu tượng hoá thật — đây là over-engineering kinh điển với EF Core (xem mục 4).
- **Tưởng `SaveChangesAsync()` gọi nhiều lần rời rạc vẫn "an toàn" vì cùng một `DbContext`:** sai — mỗi lần gọi là một transaction riêng; muốn gộp nhiều thay đổi thành một giao dịch, phải sửa entity **trước rồi mới gọi `SaveChangesAsync()` một lần duy nhất** (mục 3).
- **Mock `AppDbContext` trực tiếp trong test bằng thư viện mock (Moq) thay vì phụ thuộc interface:** kỹ thuật (Moq mock được `DbSet<T>` qua một số thủ thuật `Mock<DbSet<T>>` phức tạp), nhưng rối, giòn (dễ vỡ khi đổi truy vấn), và bỏ lỡ lợi ích chính của Repository — phụ thuộc **interface** đơn giản hơn nhiều để mock (mục 2).
- **Repository interface phình to dần theo "có thể cần"**: thêm `GetByEmail`, `GetByPhone`, `GetActive`... trước khi có caller thật nào cần — vi phạm nguyên tắc interface chỉ nên khớp đúng nhu cầu thật (đã học ở SOLID, nhắc lại ở mức module tại mục 2).
- **Quên rằng `IProductRepository` không tự động transaction hoá nhiều repository khác nhau:** nếu bạn có `IOrderRepository` và `IProductRepository` riêng biệt, và một nghiệp vụ cần sửa cả `Order` và `Product` trong cùng một giao dịch, cả hai repository phải dùng chung **một** `DbContext` instance (thường tự động đúng nhờ DI scoped lifetime) để `SaveChangesAsync()` của `DbContext` đó gộp đúng thành một transaction — nếu vô tình mỗi repository tự inject `DbContext` riêng (khác scope), bạn lại quay về vấn đề mục 3.
- **Đăng ký Repository/`IUnitOfWork` với lifetime `Singleton` trong khi `DbContext` là `Scoped`:** ASP.NET Core ném lỗi ngay khi khởi động ("Cannot consume scoped service from singleton"), hoặc tệ hơn nếu né lỗi bằng resolve thủ công — Repository giữ một `DbContext` cũ từ request đầu tiên, gây `ObjectDisposedException` hoặc dữ liệu sai ở các request sau (mục 7).
- **Viết `IUnitOfWork` tường minh khi chỉ có một Repository, một nghiệp vụ đơn giản:** nếu Service của bạn chưa bao giờ cần phối hợp từ hai Repository đặc thù trở lên trong cùng một giao dịch, thêm `IUnitOfWork` chỉ là một lớp gián tiếp (indirection) không cần thiết — Service tiêm trực tiếp Repository đó là đủ (mục 6).
- **Đặt tên phương thức Repository đặc thù theo kiểu CRUD chung (`GetById`, `Update`) thay vì theo câu hỏi nghiệp vụ:** làm mất chính lợi ích của Repository đặc thù (mục 5) — tên phương thức nên đọc lên hiểu ngay câu hỏi nghiệp vụ (`LayDonHangDangXuLyTrongThang`), không phải một động từ CRUD tổng quát khiến Repository đặc thù trông giống generic mà không có lý do.

---

## Bài tập

**Bài 1 (giàn giáo):** `CustomerService` sau phụ thuộc trực tiếp `AppDbContext`, không test được mà không có database. Sửa để nó phụ thuộc một interface `ICustomerRepository` tối thiểu (chỉ có phương thức `CustomerService` thật sự cần), rồi viết một fake repository để chứng minh test chạy không cần database.

```csharp title="CustomerService.cs (co van de - can sua)"
// test:skip bai tap 1 - AppDbContext chua dinh nghia day du, chi la de bai minh hoa
public sealed class CustomerService(AppDbContext db)
{
    public async Task<bool> LaKhachHangVip(int customerId)
    {
        var customer = await db.Customers.FindAsync(customerId);
        return customer?.TongChiTieu > 10_000_000m;
    }
}
```

??? success "Lời giải + vì sao"
    ```csharp title="CustomerService.cs (da sua - dung Repository)"
    // test:run
    var service = new CustomerService(new FakeCustomerRepository());
    var vip = await service.LaKhachHangVip(1);
    var khongVip = await service.LaKhachHangVip(2);
    Console.WriteLine($"Khach 1 la VIP: {vip}");
    Console.WriteLine($"Khach 2 la VIP: {khongVip}");

    if (!vip || khongVip)
        throw new Exception("Test FAIL");
    Console.WriteLine("Test PASS");

    public sealed class Customer
    {
        public int Id { get; set; }
        public decimal TongChiTieu { get; set; }
    }

    // Interface chỉ có ĐÚNG MỘT phương thức CustomerService cần -
    // không thêm Update/Delete/GetAll vì chưa ai gọi.
    public interface ICustomerRepository
    {
        Task<Customer?> LayTheoId(int id);
    }

    public sealed class CustomerService(ICustomerRepository repo)
    {
        public async Task<bool> LaKhachHangVip(int customerId)
        {
            var customer = await repo.LayTheoId(customerId);
            return customer?.TongChiTieu > 10_000_000m;
        }
    }

    public sealed class FakeCustomerRepository : ICustomerRepository
    {
        private readonly Dictionary<int, Customer> _data = new()
        {
            [1] = new Customer { Id = 1, TongChiTieu = 15_000_000m },
            [2] = new Customer { Id = 2, TongChiTieu = 5_000_000m },
        };

        public Task<Customer?> LayTheoId(int id) =>
            Task.FromResult(_data.GetValueOrDefault(id));
    }
    ```

    **Vì sao đúng:** `ICustomerRepository` chỉ có `LayTheoId` — đúng một phương thức `CustomerService` thật sự gọi, không thêm gì "cho đủ". `FakeCustomerRepository` chứng minh test chạy hoàn toàn trong bộ nhớ, không cần EF Core, không cần connection string — đúng vấn đề mục 2 giải quyết.

**Bài 2 (thiết kế — đánh giá over-engineering):** Bạn được giao một API CRUD đơn giản cho bảng `Category` (chỉ có `Id`, `Ten`) — không có logic nghiệp vụ phức tạp, không có kế hoạch đổi database provider, chỉ có một Controller gọi trực tiếp. Đồng nghiệp đề xuất viết `ICategoryRepository` + `CategoryRepository` bọc `DbSet<Category>` "để đúng kiến trúc chuẩn". Bạn đồng ý hay phản đối? Giải thích bằng tiêu chí ở mục 4.

??? success "Lời giải + vì sao"
    **Phản đối (hoặc ít nhất đề nghị cân nhắc lại).** Áp hai tiêu chí ở mục 4 vào tình huống này:

    1. Không có logic query phức tạp tái sử dụng nhiều nơi — chỉ CRUD đơn giản, một Controller gọi.
    2. Không có kế hoạch đổi database provider, không cần trừu tượng hoá để mock nâng cao.

    Không rơi vào trường hợp nào cần Repository riêng. Viết `ICategoryRepository` lúc này chỉ tạo thêm một interface + một class có `Add`/`Get`/`Update`/`Delete` gọi thẳng `DbSet<Category>` — không thêm giá trị trừu tượng hoá thật (Controller/Service vẫn biết đây là dữ liệu quan hệ dạng bảng), lại mất khả năng dùng `Include`/projection tự nhiên nếu `Category` sau này có quan hệ với entity khác. Dùng trực tiếp `AppDbContext`/`DbSet<Category>` trong Service là đủ và đơn giản hơn. Nếu sau này xuất hiện nhu cầu thật (logic query phức tạp lặp lại, hoặc yêu cầu đổi provider), tách Repository ra lúc đó — không phải trước.

**Bài 3 (thiết kế — Repository đặc thù + Unit of Work):** Nghiệp vụ "Đặt hàng" cần: (1) kiểm tra `Product` còn đủ số lượng trong kho, (2) trừ số lượng tồn kho của `Product` đó, (3) tạo một `Order` mới — cả ba bước phải nằm trong **cùng một giao dịch** (nếu bước 3 thất bại, số lượng tồn kho ở bước 2 không được trừ). Thiết kế `IUnitOfWork`, các Repository liên quan (chỉ nêu tên phương thức, không cần triển khai đầy đủ EF Core), và Service gọi chúng.

??? success "Lời giải + vì sao"
    ```csharp title="DatHangService.cs (thiet ke)"
    // test:skip bai tap 3 - thiet ke minh hoa, Product/Order/cac Repository chua day du
    public interface IProductRepository
    {
        Task<Product?> LayTheoId(int id);
        void GiamSoLuongTonKho(Product product, int soLuong);
    }

    public interface IOrderRepository
    {
        void TaoDonHangMoi(Order order);
    }

    public interface IUnitOfWork
    {
        IProductRepository Products { get; }
        IOrderRepository Orders { get; }
        Task<int> LuuThayDoi();
    }

    public sealed class DatHangService(IUnitOfWork uow)
    {
        public async Task DatHang(int productId, int soLuong)
        {
            var product = await uow.Products.LayTheoId(productId);
            if (product is null || product.SoLuongTonKho < soLuong)
                throw new InvalidOperationException("Khong du hang trong kho");

            // Cả hai thay đổi (trừ kho + tạo đơn) chỉ SỬA trong bộ nhớ ở đây -
            // CHƯA lưu gì xuống database.
            uow.Products.GiamSoLuongTonKho(product, soLuong);
            uow.Orders.TaoDonHangMoi(new Order { ProductId = productId, SoLuong = soLuong });

            // MỘT lần lưu duy nhất, cuối cùng -> cả hai thay đổi cùng thành công
            // hoặc cùng thất bại, vì cùng một DbContext bên dưới IUnitOfWork.
            await uow.LuuThayDoi();
        }
    }
    ```

    **Vì sao đúng:** `IProductRepository.GiamSoLuongTonKho` và `IOrderRepository.TaoDonHangMoi` chỉ **sửa entity trong bộ nhớ** (change tracker của `DbContext` ghi nhận, chưa gửi SQL) — đúng nguyên tắc mục 3: mọi thay đổi liên quan phải chờ **một** `SaveChangesAsync()` cuối cùng. Vì cả hai Repository đến từ **cùng một** `IUnitOfWork` instance (mục 6), chúng chắc chắn dùng chung một `DbContext` — `LuuThayDoi()` gộp cả hai thay đổi vào một transaction. Nếu tách rời, gọi `SaveChangesAsync()` riêng cho từng Repository (như cảnh báo mục 3 và mục 6), một lỗi ở bước tạo đơn hàng sẽ để lại kho đã bị trừ số lượng mà không có đơn hàng tương ứng — dữ liệu sai lệch không thể chấp nhận trong nghiệp vụ bán hàng.

---

## Tự kiểm tra

1. Repository pattern định nghĩa là gì, và nó giải quyết vấn đề cụ thể nào khi viết unit test?

    ??? note "Đáp án"
        Repository là một interface trừu tượng hoá việc truy cập dữ liệu — business logic gọi qua interface, không biết dữ liệu đến từ EF Core/SQL/API nào. Nó giải quyết vấn đề: Service phụ thuộc trực tiếp một class cụ thể (như `DbContext`) rất khó mock trong unit test; phụ thuộc một interface thì mock được bằng một fake class viết tay, test chạy không cần database.

2. Unit of Work là gì? Cho ví dụ cụ thể trong EF Core chứng minh nó đã có sẵn.

    ??? note "Đáp án"
        Unit of Work gom nhiều thay đổi dữ liệu thành một giao dịch lưu một lần — nếu một phần thất bại, toàn bộ rollback. Trong EF Core, `DbContext.SaveChangesAsync()` chính là Unit of Work có sẵn: mọi thay đổi đang được change-tracker theo dõi (trên nhiều entity, nhiều bảng) được gói vào một transaction khi gọi `SaveChangesAsync()` một lần.

3. Vì sao viết một `GenericRepository<T>` bọc quanh `DbSet<T>` với chỉ `Add`/`Get`/`Update`/`Delete` thường là thừa khi dùng EF Core?

    ??? note "Đáp án"
        Vì `DbSet<T>` (qua `DbContext`) đã là một Repository-like abstraction + Unit of Work có sẵn. Bọc thêm một lớp generic chỉ CRUD đơn giản không thêm giá trị trừu tượng hoá thật (business logic vẫn biết đây là bảng EF Core), mà lại che mất `Include`, `Select` projection, `AsNoTracking` — các tính năng mạnh của `IQueryable<T>` — buộc phải thêm phương thức mới cho mỗi truy vấn phức tạp.

4. Nêu hai trường hợp cụ thể khi viết Repository riêng THẬT SỰ hữu ích với EF Core.

    ??? note "Đáp án"
        (1) Có logic query phức tạp (nhiều `Include`/`Where`/sắp xếp) được tái sử dụng ở nhiều nơi — gói vào một phương thức Repository để không lặp code và dễ sửa một chỗ. (2) Thật sự cần trừu tượng hoá để đổi database provider, hoặc cần mock hoàn toàn trong test mà không dùng InMemory provider của EF Core.

5. Nếu gọi `SaveChangesAsync()` hai lần rời rạc cho hai thay đổi liên quan (ví dụ trừ tiền tài khoản A rồi mới sửa tài khoản B), điều gì có thể xảy ra nếu bước thứ hai thất bại?

    ??? note "Đáp án"
        Hai lần gọi là hai transaction độc lập — nếu bước thứ hai thất bại, thay đổi của bước đầu (đã lưu thành công) không bị rollback theo. Kết quả: dữ liệu rơi vào trạng thái sai (tiền đã trừ khỏi A nhưng chưa cộng vào B). Phải sửa cả hai entity trước, rồi gọi `SaveChangesAsync()` một lần duy nhất để cả hai nằm trong cùng một transaction.

6. Interface Repository nên chứa bao nhiêu phương thức — càng nhiều "cho đủ dùng sau" càng tốt, hay chỉ vừa đủ nhu cầu hiện tại?

    ??? note "Đáp án"
        Chỉ nên chứa đúng những phương thức mà caller thật sự đang gọi. Thêm phương thức "cho đủ" trước khi có nhu cầu thật làm interface phình to không cần thiết, khó mock đầy đủ trong test, và vi phạm nguyên tắc interface nên khớp đúng nhu cầu sử dụng thật (Interface Segregation, nhắc lại ở mức module).

7. Một API CRUD đơn giản, không có logic query phức tạp, không có kế hoạch đổi database — có nên viết Repository riêng bọc `DbSet<T>` không? Vì sao?

    ??? note "Đáp án"
        Không nên. Không rơi vào hai trường hợp cần Repository riêng (mục 4) — viết thêm chỉ tạo code dư thừa, mất tính năng EF Core, mà không có lợi ích trừu tượng hoá thật. Dùng trực tiếp `DbContext`/`DbSet<T>` trong Service là đủ; tách Repository ra sau, khi nhu cầu thật xuất hiện.

8. Repository đặc thù (`IOrderRepository`) khác Repository generic (`IGenericRepository<T>`) ở điểm thiết kế nào, và vì sao khác biệt đó giúp không che mất `Include`/projection?

    ??? note "Đáp án"
        Repository đặc thù có phương thức đặt tên theo câu hỏi nghiệp vụ cụ thể của một entity (ví dụ `LayDonHangDangXuLyTrongThang`), không phải theo động từ CRUD chung áp dụng cho mọi `T`. Vì mỗi phương thức chỉ phục vụ một câu hỏi cụ thể, chữ ký (signature) của nó tự do trả về đúng hình dạng dữ liệu cần (projection như `OrderSummary`, hoặc entity kèm `Include`) — không bị ràng buộc phải trả `T` nguyên vẹn như generic, nên không cần "hy sinh" `Include`/`Select` để giữ tính tổng quát.

9. Khi nào cần một `IUnitOfWork` tường minh (không chỉ dựa vào `SaveChangesAsync()` của một `DbContext` đơn lẻ)? Nếu đăng ký sai lifetime cho Repository/`IUnitOfWork` so với `DbContext`, hậu quả cụ thể là gì?

    ??? note "Đáp án"
        Cần khi một nghiệp vụ phải phối hợp nhiều Repository đặc thù trong cùng một giao dịch, và muốn Service hoàn toàn không biết `DbContext`/EF Core tồn tại. Nếu đăng ký Repository/`IUnitOfWork` là `Singleton` trong khi `DbContext` là `Scoped`, ASP.NET Core ném lỗi ngay khi khởi động ứng dụng ("Cannot consume scoped service from singleton"); nếu né lỗi bằng cách khác, Repository sẽ giữ một `DbContext` cũ, gây `ObjectDisposedException` hoặc dữ liệu sai ở các request sau.

---

??? abstract "DEEP DIVE — nâng cao (ngoài fast path)"
    - **Unit of Work "thủ công" khi có nhiều `DbContext`:** trong một số kiến trúc phức tạp (ví dụ nhiều bounded context, mỗi context có `DbContext` riêng, hoặc microservice tách theo domain), đôi khi cần coordinate transaction giữa nhiều `DbContext` cùng lúc. EF Core hỗ trợ việc này qua `Database.BeginTransactionAsync()` trên một connection dùng chung, hoặc trong trường hợp phức tạp hơn (nhiều connection string khác nhau), qua `System.Transactions.TransactionScope` — nhưng `TransactionScope` với nhiều database vật lý khác nhau thường cần **distributed transaction coordinator (DTC)** của hệ điều hành, một cấu hình nặng và hiếm khi cần trong ứng dụng web thông thường. Đây là trường hợp hiếm, chỉ cần khi thật sự có nhiều `DbContext`/database phải đồng bộ tuyệt đối, không phải mặc định cho mọi project — tuyệt đại đa số ứng dụng chỉ cần một `DbContext` và `SaveChangesAsync()` như mục 3–6 đã trình bày.
    - **Specification pattern kết hợp Repository:** khi logic query phức tạp cần tái sử dụng nhưng vẫn muốn giữ Repository interface gọn (không phình thành hàng chục phương thức `GetByX`, `GetByY`), có thể dùng Specification pattern — đóng gói mỗi điều kiện lọc/sắp xếp thành một object `ISpecification<T>` riêng (ví dụ `DonHangDangXuLyTrongThangSpec`), Repository chỉ cần **một** phương thức tổng quát `Task<List<T>> ApDung(ISpecification<T> spec)` áp dụng spec đó lên `IQueryable<T>`. Cách này giữ Repository interface ổn định (không thêm phương thức mới cho mỗi truy vấn), nhưng vẫn giữ được khả năng biểu diễn logic phức tạp — đánh đổi lại là thêm một tầng trừu tượng (các class Specification) cần học và duy trì, chỉ đáng làm khi số lượng truy vấn phức tạp đủ lớn để việc chuẩn hoá này hoàn vốn.
    - **`IRepository<T>` generic vẫn có chỗ đứng ngoài EF Core:** nếu tầng data access KHÔNG phải EF Core (ví dụ gọi qua một API HTTP bên ngoài, gRPC, hoặc Dapper thuần với SQL viết tay không có `IQueryable<T>`), Repository generic có giá trị trừu tượng hoá thật hơn nhiều — không có `DbSet<T>`/`IQueryable<T>` sẵn để "mất" khi bọc thêm một lớp, vì bản thân tầng dưới đã không có LINQ provider mạnh như EF Core. Lúc đó cảnh báo "thường thừa" ở mục 4 (dành riêng cho ngữ cảnh EF Core) không áp dụng nguyên vẹn — với Dapper, một `IProductRepository` bọc các câu SQL viết tay là cách hợp lý để business logic không rải SQL string khắp nơi.
    - **Đo lường trước khi quyết định tách Repository:** một tín hiệu thực dụng để biết đã "đến lúc cần" Repository đặc thù là khi cùng một truy vấn phức tạp (`Include` + `Where` + sắp xếp, hoặc projection cụ thể) xuất hiện lặp lại ở **từ 3 nơi trở lên** trong codebase, hoặc khi một team viết unit test thấy mình liên tục phải dựng InMemory provider/SQLite in-memory chỉ để test logic không thật sự liên quan tới database. Dưới ngưỡng đó, một chút trùng lặp LINQ nhỏ (2 nơi, vài dòng) thường **rẻ hơn** chi phí thiết kế + duy trì một lớp trừu tượng mới — nguyên tắc "rule of three" áp dụng ở đây giống như khi quyết định tách một phương thức dùng chung.
    - **Repository và CQRS — không phải cùng một quyết định:** một nhầm lẫn thường gặp là nghĩ "đã có Repository thì nên tách luôn thành CQRS (Command Query Responsibility Segregation)". Hai quyết định này độc lập: Repository (đặc thù) giải quyết việc trừu tượng hoá truy cập dữ liệu và test được không cần database; CQRS giải quyết việc tách hẳn model đọc và model ghi khi hai model đó **khác nhau đáng kể** (ví dụ một báo cáo tổng hợp phức tạp đọc dữ liệu, khác hẳn với model ghi đơn giản của một lệnh cập nhật). Một ứng dụng CRUD đơn giản dùng Repository đặc thù cho vài truy vấn phức tạp **không cần** áp thêm CQRS — ghép hai pattern vào cùng một quyết định kiến trúc khi chưa có nhu cầu CQRS thật là chồng thêm một lớp over-engineering nữa lên trên.

**Tiếp theo →** [P6 · Design Patterns cốt lõi](design-patterns-co-ban.md)
