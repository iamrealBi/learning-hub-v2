---
tier: core
status: core
owner: core-team
verified_on: "2026-07-05"
dotnet_version: "10.0"
bloom: áp dụng
requires: [p3-api]
est_minutes_fast: 26
---

# Testing với xUnit: viết test làm tài liệu sống

!!! info "Bạn đang ở đây"
    cần trước: bạn đã viết được api tối thiểu (bạn biết một endpoint nhận gì, trả gì, và đã từng viết một hàm logic thuần tách khỏi endpoint).
    mở khoá: sau chương này bạn viết được test tự động cho logic thuần bằng xUnit (`[Fact]`, `[Theory]`), phân biệt được test logic thuần với test gọi api thật, hiểu giới hạn của mock và của con số coverage — nền tảng để đổi code về sau mà không phải "chạy tay lại từ đầu" mỗi lần.

> **Mục tiêu (đo được):** sau chương này bạn **áp dụng** được cấu trúc Arrange-Act-Assert để viết một test rõ ràng, **sử dụng** được `[Fact]` cho một ca cụ thể và `[Theory]`+`[InlineData]` cho nhiều bộ dữ liệu, **phân biệt** được unit test với integration test bằng đúng một tiêu chí (có I/O thật hay không), **giải thích** được vì sao mock thay được một dependency thật bằng một dependency giả có kiểm soát, và **đánh giá** được vì sao 100% coverage không đồng nghĩa với không có bug.

---

## 0. Đoán nhanh trước khi học

Bạn có một hàm tính giảm giá:

```csharp title="Chỉ để suy luận, chưa phải bài học"
// test:skip đoạn trích chỉ để đặt câu hỏi, không phải chương trình đầy đủ
decimal ApplyDiscount(decimal price, decimal percent) => price - (price * percent / 100);
```

Một đồng nghiệp sửa hàm này để thêm khuyến mãi ngày lễ. Sau khi sửa, `ApplyDiscount(100, 10)` bỗng trả `85` thay vì `90` — nhưng không ai để ý, vì không có gì tự động chạy lại để kiểm tra. Ba tuần sau, khách hàng report bị tính sai tiền.

1. Nếu có một test tự động cho `ApplyDiscount(100, 10) == 90`, chuyện gì sẽ khác đi ngay tại thời điểm sửa code?
2. Vì sao "tôi đã tự tay chạy thử rồi" không thay thế được test tự động?

??? note "Đáp án"
    1. Ngay khi đồng nghiệp sửa xong và build/test lại, test đó sẽ **fail ngay lập tức** — báo đỏ tại chính thời điểm gây lỗi, không phải ba tuần sau khi khách hàng report. Đây gọi là phát hiện **regression** (tính năng cũ bị hỏng do thay đổi mới) sớm nhất có thể.
    2. Vì "tự tay chạy thử" chỉ kiểm tra **một lần, tại một thời điểm** — nó không tự động chạy lại mỗi khi có người khác sửa code sau này. Test tự động thì chạy lại **mọi lần** (mỗi lần build, mỗi lần commit), nên nó bảo vệ được cả những thay đổi mà bạn không biết trước.

---

## 1. Vì sao cần test tự động

**Định nghĩa (một câu):** Test tự động là **mã kiểm tra mã** — bạn viết trước một đoạn mô tả "đầu vào X phải cho ra kết quả Y", máy chạy đoạn đó và tự báo cho bạn biết kết quả thực tế có khớp Y hay không, không cần bạn tự tay kiểm bằng mắt mỗi lần.

Hãy hình dung một hệ thống có hai phần liên quan tới nhau: hàm `ApplyDiscount` (tính giảm giá) và hàm `CalculateTotal` (tính tổng đơn hàng), trong đó `CalculateTotal` **gọi** `ApplyDiscount` bên trong. Nếu không có test tự động:

```csharp title="C#"
// test:run
decimal ApplyDiscount(decimal price, decimal percent) => price - (price * percent / 100);

decimal CalculateTotal(decimal price, int quantity, decimal discountPercent)
    => ApplyDiscount(price * quantity, discountPercent);

// Ai đó sửa ApplyDiscount để "tối ưu", vô tình đổi công thức sai:
// decimal ApplyDiscount(decimal price, decimal percent) => price - percent; // BUG giả lập

Console.WriteLine(CalculateTotal(price: 100, quantity: 1, discountPercent: 10));
// Kỳ vọng: 90. Nếu công thức bị đổi sai như comment trên, kết quả sẽ là 90 vẫn đúng ở ca này,
// nhưng sai ở ca khác (ví dụ price=50) — mà không có gì tự động BÁO cho bạn biết.
```

Vấn đề không nằm ở chỗ bug **có thể xảy ra** — bug luôn có thể xảy ra. Vấn đề là: **ai/cái gì sẽ phát hiện** bug đó, và **khi nào**? Không có test, câu trả lời thường là "khách hàng, vài tuần sau". Có test, câu trả lời là "chính máy build, ngay lúc commit".

Hai giá trị cốt lõi của test tự động:

- **Chống hồi quy (regression):** khi sửa hàm A, nếu A vô tình làm hỏng hành vi của hàm B (vì B gọi A, hoặc vì A và B chia sẻ logic), test của B sẽ báo đỏ **ngay**, dù người sửa code không hề động vào B.
- **Tài liệu sống:** một danh sách tên test đọc được như một bản đặc tả hành vi hệ thống — nói cho người đọc sau này biết hệ thống **phải** làm gì, mà không cần đọc từng dòng cài đặt.

!!! danger "Hiểu lầm phổ biến"
    "Test chỉ để bắt bug lúc viết code." Sai một nửa. Giá trị lớn nhất của test lộ ra **về sau**: sáu tháng sau, một người (có thể chính là bạn) sửa một hàm không liên quan, và bộ test cũ báo đỏ đúng chỗ bị ảnh hưởng — điều mà đọc code bằng mắt rất khó phát hiện, vì người sửa không biết A và B có liên quan.

---

## 2. Arrange-Act-Assert (AAA): bố cục của một test

**Định nghĩa (một câu):** Arrange-Act-Assert (AAA) là cách chia **mọi** test thành ba phần theo thứ tự cố định: **Arrange** (dựng dữ liệu/đối tượng đầu vào), **Act** (gọi đúng một hành động cần kiểm), **Assert** (so kết quả thực tế với kết quả kỳ vọng).

Ba phần đó ứng với ba câu hỏi:

| Khối | Câu hỏi trả lời | Ví dụ với `ApplyDiscount` |
|---|---|---|
| Arrange | Đầu vào là gì? | `decimal price = 100; decimal percent = 10;` |
| Act | Gọi cái gì? | `var result = ApplyDiscount(price, percent);` |
| Assert | Kết quả đúng là gì? | `result` phải bằng `90` |

Ví dụ tối thiểu, tự chứa, chỉ minh hoạ đúng bố cục AAA — chưa cần xUnit, tự "assert" bằng `Console` để thấy rõ ý tưởng pass/fail:

```csharp title="C#"
// test:run
decimal ApplyDiscount(decimal price, decimal percent) => price - (price * percent / 100);

void AssertEqual(decimal expected, decimal actual, string tenTest)
{
    var dung = expected == actual;
    Console.WriteLine($"{(dung ? "PASS" : "FAIL")} {tenTest} (mong {expected}, được {actual})");
}

// ---- Test 1 ----
// Arrange
decimal gia = 100;
decimal phanTramGiam = 10;
// Act
var ketQua = ApplyDiscount(gia, phanTramGiam);
// Assert
AssertEqual(expected: 90, actual: ketQua, tenTest: "ApplyDiscount_Giam10Phan100_TraVe90");
```

Output kỳ vọng:

```text title="Kết quả"
PASS ApplyDiscount_Giam10Phan100_TraVe90 (mong 90, được 90)
```

Cùng logic đó viết bằng xUnit thật — một test method đánh dấu `[Fact]` cho **một** hàm logic thuần:

```csharp title="C#"
// test:skip cần package xunit, không build được bằng dotnet build/run đơn lẻ
using Xunit;

public class DiscountCalculator
{
    public decimal ApplyDiscount(decimal price, decimal percent)
        => price - (price * percent / 100);
}

public class DiscountCalculatorTests
{
    [Fact]
    public void ApplyDiscount_Giam10Phan100_TraVe90()
    {
        // Arrange
        var calc = new DiscountCalculator();
        decimal gia = 100;
        decimal phanTramGiam = 10;

        // Act
        var ketQua = calc.ApplyDiscount(gia, phanTramGiam);

        // Assert
        Assert.Equal(90, ketQua);
    }
}
```

Đặt tên test theo mẫu `Method_ĐiềuKiện_KỳVọng` (ở đây: `ApplyDiscount_Giam10Phan100_TraVe90`) chính là cách biến test thành **tài liệu sống**: đọc tên là biết hệ thống phải làm gì trong tình huống nào, không cần đọc cài đặt bên trong.

**Nếu bố cục sai — hậu quả cụ thể:** nếu bạn viết `Assert` **trước** `Act` (gọi hàm cần kiểm sau khi đã so sánh), biến `ketQua` chưa tồn tại tại thời điểm assert — code này không biên dịch được (lỗi `CS0103: The name 'ketQua' does not exist in the current context`). Nếu bạn trộn nhiều `Act` không liên quan vào một test (gọi 3 hàm khác nhau rồi assert cả 3), khi test fail bạn không biết **hành động nào** trong 3 hành động đó gây ra sai lệch — mất chính giá trị "chỉ đúng chỗ" mà AAA mang lại.

---

## 3. Assert cơ bản: `Equal`, `True`, `Throws`

**Định nghĩa (một câu):** `Assert` (lớp tĩnh của xUnit) là tập các phương thức so sánh kết quả thực tế với kỳ vọng — nếu khớp, phương thức trả về bình thường (test tiếp tục); nếu lệch, nó ném ra một exception đặc biệt khiến xUnit đánh dấu test đó là **fail** và in ra giá trị mong đợi lẫn giá trị thực tế.

Ba phương thức dùng nhiều nhất, mỗi phương thức minh hoạ bằng một ví dụ độc lập:

**`Assert.Equal(expected, actual)`** — kiểm hai giá trị bằng nhau:

```csharp title="C#"
// test:skip cần package xunit
using Xunit;

public class PhepCongTests
{
    [Fact]
    public void Cong_2Va3_TraVe5()
    {
        var ketQua = 2 + 3;
        Assert.Equal(5, ketQua); // fail nếu ketQua khác 5
    }
}
```

**`Assert.True(condition)`** (và `Assert.False`) — kiểm một biểu thức boolean:

```csharp title="C#"
// test:skip cần package xunit
using Xunit;

public class KiemTraTuoiTests
{
    [Fact]
    public void DuTuoiBauCu_Khi18_TraVeTrue()
    {
        var duTuoi = 18 >= 18;
        Assert.True(duTuoi, "18 tuổi phải đủ điều kiện bầu cử");
    }
}
```

**`Assert.Throws<TException>(action)`** — kiểm rằng một đoạn code **phải** ném đúng loại exception:

```csharp title="C#"
// test:skip cần package xunit
using Xunit;

public class RutTienTests
{
    [Fact]
    public void RutTien_KhiSoDuKhongDu_NemInvalidOperationException()
    {
        decimal soDu = 50;
        decimal soTienRut = 100;

        void RutTien()
        {
            if (soTienRut > soDu)
                throw new InvalidOperationException("Số dư không đủ");
        }

        // Assert.Throws vừa CHẠY hành động, vừa kiểm loại exception, trong một lời gọi.
        var ex = Assert.Throws<InvalidOperationException>(RutTien);
        Assert.Equal("Số dư không đủ", ex.Message);
    }
}
```

**Nếu dùng sai — hậu quả cụ thể:** nếu bạn viết `Assert.Throws<InvalidOperationException>(RutTien())` (có dấu `()` sau `RutTien`) thay vì truyền delegate chưa gọi, code **không biên dịch được**: `RutTien()` là một lời gọi trả về `void`, mà `void` không thể dùng làm giá trị đối số cho tham số kiểu `Action` — trình biên dịch báo lỗi ngay (kiểu `CS1503: Cannot convert from 'void' to 'System.Action'`), trước khi test kịp chạy. (Nếu `RutTien` có trả về giá trị khác `void`, lỗi biên dịch tương tự vẫn xảy ra vì kiểu trả về đó không khớp `Action`.) Đúng là phải truyền **delegate chưa gọi** (`RutTien` không có `()`, hoặc lambda `() => RutTien()`) để `Assert.Throws` tự gọi hành động đó **bên trong** một khối có bắt exception.

---

## 4. `[Theory]` + `[InlineData]`: nhiều bộ dữ liệu, một logic

**Định nghĩa (một câu):** `[Theory]` kết hợp với `[InlineData(...)]` cho phép viết **một** test method nhận tham số, rồi chạy lại method đó **nhiều lần**, mỗi lần với một bộ giá trị khác nhau khai báo trong từng `[InlineData]` — thay cho việc copy-paste nhiều `[Fact]` gần như giống nhau.

So sánh: nếu dùng `[Fact]`, kiểm 3 bộ giá trị của `ApplyDiscount` cần 3 method riêng gần như trùng lặp:

```csharp title="C#"
// test:skip cần package xunit — minh hoạ vấn đề LẶP, chưa phải cách nên dùng
using Xunit;

public class DiscountCalculatorTests
{
    [Fact]
    public void ApplyDiscount_Giam10Tren100_TraVe90()
        => Assert.Equal(90, new DiscountCalculator().ApplyDiscount(100, 10));

    [Fact]
    public void ApplyDiscount_Giam0Tren100_TraVe100()
        => Assert.Equal(100, new DiscountCalculator().ApplyDiscount(100, 0));

    [Fact]
    public void ApplyDiscount_Giam50Tren200_TraVe100()
        => Assert.Equal(100, new DiscountCalculator().ApplyDiscount(200, 50));
}
```

Dùng `[Theory]` + `[InlineData]`, gộp thành **một** method:

```csharp title="C#"
// test:skip cần package xunit
using Xunit;

public class DiscountCalculatorTests
{
    [Theory]
    [InlineData(100, 10, 90)]
    [InlineData(100, 0, 100)]
    [InlineData(200, 50, 100)]
    public void ApplyDiscount_NhieuBoGiaTri_TraDungKetQua(decimal price, decimal percent, decimal expected)
    {
        var ketQua = new DiscountCalculator().ApplyDiscount(price, percent);
        Assert.Equal(expected, ketQua);
    }
}
```

Chạy bằng `dotnet test`, xUnit thực thi method này **3 lần độc lập**, mỗi `[InlineData]` là một dòng kết quả riêng. Nếu bộ `(200, 50, 100)` fail, thông báo lỗi in **đúng** bộ tham số đó (`ApplyDiscount_NhieuBoGiaTri_TraDungKetQua(price: 200, percent: 50, expected: 100)`), không lẫn với hai bộ còn lại — mỗi `InlineData` vẫn là một test riêng biệt, chỉ chia sẻ **code** của method, không chia sẻ **kết quả pass/fail**.

**Nếu dùng sai — hậu quả cụ thể:** nếu số lượng tham số trong `[InlineData(...)]` không khớp với số tham số của method (ví dụ method nhận 3 tham số nhưng `[InlineData(100, 10)]` chỉ có 2), xUnit báo lỗi ngay khi khám phá test (`System.InvalidOperationException` báo "no data found"/lệch tham số) — test đó bị đánh dấu lỗi trước khi kịp chạy, không âm thầm bỏ qua.

---

## 5. Unit test và integration test

**Định nghĩa (một câu) — unit test:** Unit test kiểm **một đơn vị logic cô lập** (một hàm, một class), **không có I/O thật** (không gọi database, mạng, file thật) — mọi dependency bên ngoài được thay bằng phiên bản giả do bạn kiểm soát.

**Định nghĩa (một câu) — integration test:** Integration test kiểm **nhiều phần ghép lại chạy cùng nhau**, **có I/O thật** (hoặc gần thật) — ví dụ khởi động cả ứng dụng ASP.NET Core và gọi một request HTTP thật vào nó, đi qua đúng routing, middleware, dependency injection như khi chạy production.

Mọi ví dụ từ mục 2–4 (`ApplyDiscount`, `RutTien`) đều là **unit test**: chúng gọi trực tiếp một hàm C#, không có gì đi qua mạng hay ổ đĩa.

Một integration test dùng `WebApplicationFactory<TEntryPoint>` (gói `Microsoft.AspNetCore.Mvc.Testing`) khởi động **toàn bộ** app trong bộ nhớ, cho một `HttpClient` gọi endpoint thật:

```csharp title="C#"
// test:skip cần Microsoft.AspNetCore.Mvc.Testing + xunit, cần dự án test riêng
using Microsoft.AspNetCore.Mvc.Testing;
using Xunit;

public class SucKhoeApiTests(WebApplicationFactory<Program> factory)
    : IClassFixture<WebApplicationFactory<Program>>
{
    [Fact]
    public async Task Get_Health_TraVe200()
    {
        // Arrange
        var client = factory.CreateClient();

        // Act
        var response = await client.GetAsync("/health");

        // Assert
        Assert.True(response.IsSuccessStatusCode);
    }
}
```

`IClassFixture<WebApplicationFactory<Program>>` là dấu hiệu báo cho xUnit: "dựng **một** `WebApplicationFactory` (tức khởi động app) rồi **dùng lại** instance đó cho mọi `[Fact]` trong lớp `SucKhoeApiTests`" — thay vì khởi động lại toàn bộ app (tốn thời gian) trước mỗi test riêng lẻ. Tham số `factory` trong constructor chính là instance được chia sẻ đó, do xUnit tự truyền vào.

Khác biệt cốt lõi giữa hai loại, cùng một tiêu chí duy nhất — **có I/O thật hay không**:

| Tiêu chí | Unit test | Integration test |
|---|---|---|
| I/O thật (mạng, DB, file) | Không — mọi dependency bị thay giả | Có — hoặc gần thật (app chạy trong bộ nhớ) |
| Đi qua middleware/routing/DI thật | Không | Có |
| Tốc độ | Rất nhanh (mili-giây) | Chậm hơn (phải khởi động app) |
| Công cụ điển hình | xUnit + interface giả | xUnit + `WebApplicationFactory<T>` |
| Phát hiện lỗi loại gì | Lỗi logic trong một hàm/class | Lỗi "ghép nối" — routing sai, middleware chặn nhầm, DI thiếu đăng ký |

!!! tip "Kim tự tháp test"
    Viết **nhiều** unit test (nhanh, rẻ, chạy được hàng nghìn lần một phút) và **ít** integration test hơn (chậm, nhưng kiểm được cả đường đi thật). Đảo ngược tỉ lệ này — nhiều integration test, ít unit test — khiến bộ test chạy chậm và khó xác định chính xác chỗ hỏng khi có lỗi.

---

## 6. Mocking: đổi dependency thật bằng giả

**Định nghĩa (một câu):** Mocking là kỹ thuật **thay một dependency thật** (ví dụ một service gọi database) **bằng một phiên bản giả** mà bạn tự viết hoặc tạo qua thư viện — phiên bản giả trả về đúng giá trị bạn chỉ định, giúp test chạy nhanh, không cần I/O thật, và kết quả luôn giống nhau (tất định) mỗi lần chạy.

Xét một service phụ thuộc một interface `IKhoHang` (đại diện cho việc tra cứu tồn kho — thật ra có thể gọi database):

```csharp title="C#"
// test:skip đoạn trích, cần xunit để chạy assert
public interface IKhoHang
{
    bool ConHang(string sku);
}

public sealed class DatHangService(IKhoHang khoHang)
{
    public string Dat(string sku)
    {
        if (!khoHang.ConHang(sku))
            throw new InvalidOperationException($"Hết hàng: {sku}");
        return $"OK:{sku}";
    }
}
```

Nếu test `DatHangService` mà dùng thẳng một `IKhoHang` nối database thật, test sẽ chậm (phải mở kết nối) và **không tất định** (tồn kho database hôm nay khác hôm sau, test có thể pass hôm nay và fail ngày mai dù code không đổi). Thay vào đó, viết một fake thủ công — implement interface, tự quyết định giá trị trả về:

```csharp title="C#"
// test:skip cần package xunit
using Xunit;

// Fake thủ công: implement interface, trả giá trị ta điều khiển được, không đụng DB thật.
public sealed class KhoHangGia(bool conHang) : IKhoHang
{
    public bool ConHang(string sku) => conHang;
}

public class DatHangServiceTests
{
    [Fact]
    public void Dat_KhiConHang_TraOK()
    {
        var service = new DatHangService(new KhoHangGia(conHang: true));
        var ketQua = service.Dat("ABC");
        Assert.Equal("OK:ABC", ketQua);
    }

    [Fact]
    public void Dat_KhiHetHang_NemException()
    {
        var service = new DatHangService(new KhoHangGia(conHang: false));
        var ex = Assert.Throws<InvalidOperationException>(() => service.Dat("ABC"));
        Assert.Contains("Hết hàng", ex.Message);
    }
}
```

Fake thủ công (tự viết class implement interface) là cách **không cần thư viện ngoài**. Khi dependency phức tạp hơn (nhiều phương thức, cần kiểm "có gọi đúng bao nhiêu lần" không), người ta dùng **thư viện mock** như `NSubstitute` để tạo giả tự động:

```csharp title="C#"
// test:skip cần package xunit + NSubstitute, không có sẵn trong web project mặc định
using Xunit;
using NSubstitute;

public class DatHangServiceTests
{
    [Fact]
    public void Dat_KhiHetHang_NemException()
    {
        // Arrange: NSubstitute tạo một IKhoHang giả, chỉ định sẵn giá trị trả về.
        var khoHangGia = Substitute.For<IKhoHang>();
        khoHangGia.ConHang("ABC").Returns(false);
        var service = new DatHangService(khoHangGia);

        // Act + Assert
        Assert.Throws<InvalidOperationException>(() => service.Dat("ABC"));
    }
}
```

**Vì sao mock qua interface hoạt động được:** `DatHangService` không phụ thuộc một **lớp cụ thể** nối database, mà phụ thuộc **interface** `IKhoHang`. Nguyên lý này (phụ thuộc vào abstraction, không phụ thuộc vào cài đặt cụ thể) là điều cho phép ta "cắm" bất kỳ implementation nào vào — kể cả một implementation giả chỉ tồn tại trong test.

**Nếu dùng sai — hậu quả cụ thể:** nếu `DatHangService` viết trực tiếp logic gọi database bên trong nó (không qua interface), bạn **không có cách nào** thay dependency đó bằng giả — muốn test, bắt buộc phải có database thật kết nối được, khiến test chậm, cần môi trường phụ, và không chạy được trên máy không có kết nối tới database đó (ví dụ máy CI cách ly mạng).

---

## 7. Test coverage: là gì và giới hạn của nó

**Định nghĩa (một câu):** Test coverage là **tỉ lệ phần trăm dòng code (hoặc nhánh code) được chạy qua** trong lúc chạy toàn bộ bộ test — ví dụ coverage 80% nghĩa là 80% dòng code trong dự án được ít nhất một test "đi qua" khi chạy.

Coverage đo được **liệu code có được chạy tới hay không**, nhưng **không đo được liệu kết quả có được kiểm tra đúng hay không**. Ví dụ:

```csharp title="C#"
// test:skip cần package xunit
using Xunit;

public class DiscountCalculatorTests
{
    [Fact]
    public void ApplyDiscount_ChayKhongLoi()
    {
        var calc = new DiscountCalculator();
        var ketQua = calc.ApplyDiscount(100, 10); // dòng này CHẠY -> tính vào coverage
        // KHÔNG có Assert nào cả — test này luôn PASS dù kết quả sai bao nhiêu.
    }
}
```

Test này khiến dòng `calc.ApplyDiscount(100, 10)` được tính là "covered" (100% coverage cho dòng đó), nhưng test **không kiểm tra gì cả** — nếu `ApplyDiscount` có bug trả sai kết quả, test này vẫn pass, vì nó chưa từng so sánh kết quả với kỳ vọng.

**Nếu dùng sai — hậu quả cụ thể:** một dự án báo cáo "100% coverage" có thể vẫn chứa đầy bug, nếu phần lớn test giống ví dụ trên — chỉ **gọi** code mà không **assert** đúng behavior. Ngược lại, một dự án coverage 60% với các assert chặt chẽ, đúng trọng tâm (các nhánh logic quan trọng, các trường hợp biên) có thể đáng tin hơn một dự án 100% coverage nhưng assert hời hợt. Coverage là một **chỉ số hữu ích để tìm code chưa từng được chạy qua** (vùng mù hoàn toàn), không phải một **thước đo chất lượng test**.

---

## Cạm bẫy & thực chiến

- **Viết test không có `Assert` nào:** test luôn pass vì không kiểm tra gì cả, nhưng vẫn được tính vào coverage — tạo cảm giác an toàn giả.
- **Gộp nhiều `Act` không liên quan vào một test:** khi fail, không biết hành động nào gây lỗi; nên mỗi test chỉ kiểm **một** hành vi.
- **Truyền hành động đã gọi (`RutTien()` có dấu ngoặc) vào `Assert.Throws`** thay vì delegate chưa gọi (`RutTien` hoặc `() => RutTien()`): exception văng ra ngoài `Assert.Throws`, test sập vì lỗi runtime chưa kiểm soát, không phải fail có ý nghĩa.
- **Dùng database/API thật trong unit test:** khiến test chậm và không tất định (kết quả phụ thuộc dữ liệu bên ngoài thay đổi theo thời gian) — nên thay bằng fake/mock qua interface.
- **Đảo ngược kim tự tháp test** (nhiều integration test, ít unit test): bộ test chạy chậm, khó xác định chính xác chỗ lỗi vì mỗi integration test chạm vào nhiều phần cùng lúc.
- **Tin tưởng tuyệt đối vào số coverage cao:** coverage đo "code có được chạy qua", không đo "kết quả có được kiểm đúng" — một dự án 100% coverage vẫn có thể đầy bug nếu assert hời hợt.

---

## Bài tập

**Bài 1 (giàn giáo):** Cho hàm sau. Viết một `[Theory]` với ít nhất 3 `[InlineData]` để kiểm `PhanLoaiTuoi` trả đúng nhãn cho các mốc tuổi khác nhau (trẻ em, thanh niên, người lớn tuổi — bạn tự định nghĩa ngưỡng hợp lý).

```csharp title="C#"
// test:skip đoạn trích cần hoàn thiện, chưa có assert
string PhanLoaiTuoi(int tuoi)
{
    if (tuoi < 13) return "Trẻ em";
    if (tuoi < 60) return "Thanh niên";
    return "Người lớn tuổi";
}

// TODO: viết [Theory] + [InlineData] kiểm ít nhất 3 mốc tuổi khác nhóm.
```

??? success "Lời giải + vì sao"
    ```csharp title="C#"
    // test:skip cần package xunit
    using Xunit;

    public class PhanLoaiTuoiTests
    {
        [Theory]
        [InlineData(10, "Trẻ em")]
        [InlineData(30, "Thanh niên")]
        [InlineData(65, "Người lớn tuổi")]
        public void PhanLoaiTuoi_NhieuMocTuoi_TraDungNhan(int tuoi, string nhanMongDoi)
        {
            var ketQua = PhanLoaiTuoi(tuoi);
            Assert.Equal(nhanMongDoi, ketQua);
        }

        string PhanLoaiTuoi(int tuoi)
        {
            if (tuoi < 13) return "Trẻ em";
            if (tuoi < 60) return "Thanh niên";
            return "Người lớn tuổi";
        }
    }
    ```
    **Vì sao:** mỗi `[InlineData]` rơi vào đúng một nhánh `if` khác nhau trong `PhanLoaiTuoi` — ba bộ dữ liệu này đủ để chắc rằng cả ba nhãn đều được kiểm ít nhất một lần, mà chỉ cần viết **một** method test, không phải ba `[Fact]` lặp cấu trúc.

**Bài 2 (thiết kế):** Thiết kế test cho một `ThongBaoService` phụ thuộc `IGuiEmail` (interface gửi email, việc gửi thật cần mạng). `ThongBaoService.Gui(string diaChi)` phải: gọi `IGuiEmail.Gui(diaChi)`, trả về `"Đã gửi"` nếu thành công, và ném `ArgumentException` nếu `diaChi` là chuỗi rỗng (**không** gọi `IGuiEmail` trong trường hợp này). Viết fake thủ công và các test cho cả ba tình huống.

??? success "Lời giải + vì sao"
    ```csharp title="C#"
    // test:skip cần package xunit
    using Xunit;

    public interface IGuiEmail
    {
        void Gui(string diaChi);
    }

    public sealed class ThongBaoService(IGuiEmail guiEmail)
    {
        public string Gui(string diaChi)
        {
            if (string.IsNullOrWhiteSpace(diaChi))
                throw new ArgumentException("Địa chỉ email không được rỗng", nameof(diaChi));

            guiEmail.Gui(diaChi);
            return "Đã gửi";
        }
    }

    // Fake thủ công, tự đếm số lần Gui được gọi để verify sau.
    public sealed class GuiEmailGia : IGuiEmail
    {
        public int SoLanGoi { get; private set; }
        public void Gui(string diaChi) => SoLanGoi++;
    }

    public class ThongBaoServiceTests
    {
        [Fact]
        public void Gui_DiaChiHopLe_TraDaGuiVaGoiGuiEmailMotLan()
        {
            var emailGia = new GuiEmailGia();
            var service = new ThongBaoService(emailGia);

            var ketQua = service.Gui("a@example.com");

            Assert.Equal("Đã gửi", ketQua);
            Assert.Equal(1, emailGia.SoLanGoi);
        }

        [Theory]
        [InlineData("")]
        [InlineData("   ")]
        public void Gui_DiaChiRong_NemArgumentExceptionVaKhongGoiGuiEmail(string diaChi)
        {
            var emailGia = new GuiEmailGia();
            var service = new ThongBaoService(emailGia);

            Assert.Throws<ArgumentException>(() => service.Gui(diaChi));
            Assert.Equal(0, emailGia.SoLanGoi); // đảm bảo KHÔNG gọi gửi email khi input sai
        }
    }
    ```
    **Vì sao thiết kế này đúng:** `GuiEmailGia` không chỉ trả giá trị giả mà còn **tự đếm số lần gọi** — cho phép assert không chỉ "kết quả trả về đúng" mà còn "hành vi gọi dependency đúng" (gọi đúng 1 lần khi hợp lệ, 0 lần khi input sai). Đây là điểm mocking mạnh hơn việc chỉ kiểm giá trị trả về: nó kiểm được cả **tương tác** giữa các thành phần.

---

## Tự kiểm tra

1. Vì sao test tự động phát hiện lỗi sớm hơn việc tự tay chạy thử một lần?

    ??? note "Đáp án"
        Vì test tự động chạy lại **mọi lần** build/commit, kể cả khi người sửa code không biết đoạn code họ sửa có liên quan tới test đó — nó bảo vệ được cả những thay đổi không lường trước, còn tự tay chạy thử chỉ kiểm tại một thời điểm, không tự lặp lại sau này.

2. Ba khối Arrange-Act-Assert lần lượt trả lời câu hỏi gì?

    ??? note "Đáp án"
        Arrange: đầu vào/dữ liệu là gì. Act: gọi đúng một hành động cần kiểm. Assert: kết quả thực tế có khớp kết quả kỳ vọng không.

3. Khi nào nên dùng `[Theory]` + `[InlineData]` thay vì viết nhiều `[Fact]`?

    ??? note "Đáp án"
        Khi cùng một logic cần kiểm với **nhiều bộ dữ liệu khác nhau** — gộp thành một `[Theory]` tránh lặp code, và mỗi `[InlineData]` vẫn là một test độc lập, báo lỗi rõ đúng bộ tham số nào gây fail.

4. Tiêu chí duy nhất để phân biệt unit test và integration test là gì?

    ??? note "Đáp án"
        Có I/O thật (mạng, database, file) hay không. Unit test không có I/O thật, mọi dependency ngoài bị thay giả; integration test có I/O thật hoặc gần thật, ví dụ `WebApplicationFactory<T>` khởi động cả app trong bộ nhớ và gọi HTTP thật.

5. Vì sao mock qua interface hoạt động được, mà không mock được nếu code gọi trực tiếp một lớp cụ thể?

    ??? note "Đáp án"
        Vì service chỉ phụ thuộc vào **abstraction** (interface), không phụ thuộc cài đặt cụ thể — cho phép "cắm" bất kỳ implementation nào, kể cả một implementation giả chỉ tồn tại trong test. Nếu code gọi trực tiếp lớp cụ thể (ví dụ gọi thẳng class nối database), không có điểm nào để thay bằng giả.

6. Test không có `Assert` nào có làm tăng coverage không? Vì sao đây là vấn đề?

    ??? note "Đáp án"
        Có — dòng code được **chạy qua** vẫn tính vào coverage dù không có `Assert`. Đây là vấn đề vì test đó không kiểm tra gì cả, luôn pass bất kể kết quả đúng sai, tạo cảm giác an toàn giả từ con số coverage cao.

7. 100% test coverage có đảm bảo không có bug không? Vì sao?

    ??? note "Đáp án"
        Không. Coverage chỉ đo tỉ lệ code được **chạy qua** trong lúc test, không đo việc kết quả có được **kiểm tra đúng** hay không. Một dự án 100% coverage với assert hời hợt (hoặc thiếu hẳn) vẫn có thể chứa nhiều bug.

---

??? abstract "DEEP DIVE — fixture chia sẻ, verify số lần gọi, và song song hoá test"
    - **Chia sẻ instance tốn kém giữa các test:** `IClassFixture<T>` chia sẻ một instance trong **một** lớp test (ví dụ một `WebApplicationFactory` dựng một lần, dùng lại cho nhiều `[Fact]` trong cùng class); `ICollectionFixture<T>` kết hợp `[Collection("tên")]` chia sẻ **across** nhiều lớp test — hữu ích khi dựng một tài nguyên tốn kém (container database) một lần cho cả nhóm test.
    - **Verify số lần gọi bằng thư viện mock:** thay vì tự đếm bằng field như `SoLanGoi` ở bài tập 2, thư viện như `NSubstitute` cho phép viết `emailGia.Received(1).Gui("a@example.com")` để khẳng định chính xác lời gọi đã xảy ra đúng số lần, đúng tham số — tiện khi cần verify nhiều tương tác phức tạp cùng lúc.
    - **Song song hoá:** xUnit mặc định chạy các **collection** khác nhau song song để tăng tốc độ tổng thể. Test nào đụng vào tài nguyên chung (ví dụ cùng ghi một file, cùng một database instance) cần được gom vào cùng một `[Collection("tên")]` để tránh chạy chồng nhau gây kết quả ngẫu nhiên (flaky test).

**Tiếp theo →** [P4 · Structured Logging (ILogger)](logging-exceptions.md)
