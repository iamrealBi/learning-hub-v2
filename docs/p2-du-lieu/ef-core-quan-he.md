---
tier: core
status: core
owner: core-team
verified_on: "2026-07-01"
dotnet_version: "10.0"
bloom: áp dụng
requires: [p2-ef]
est_minutes_fast: 40
---

# EF Core: Quan hệ & N+1

!!! info "Bạn đang ở đây"
    cần trước: ef core: dbcontext, entity & truy vấn — biết viết `DbContext`, `DbSet<T>`, entity POCO, truy vấn LINQ cơ bản (`Where`/`Select`/`FirstOrDefault`), phân biệt tracking và `AsNoTracking`.
    mở khoá: khai báo quan hệ 1-nhiều và nhiều-nhiều giữa các entity bằng navigation property, cấu hình quan hệ bằng fluent api, nạp dữ liệu liên quan bằng `include()`, nhận diện và sửa vấn đề N+1 query, và chọn đúng chiến lược nạp dữ liệu (lazy/eager/explicit) — trước khi sang migration.

> Mục tiêu (đo được): sau chương này bạn có thể **áp dụng** navigation property để mô hình hoá quan hệ 1-N và N-N giữa các entity, cấu hình quan hệ đó bằng Fluent API trong `OnModelCreating`, dùng `Include()`/`ThenInclude()` để eager load dữ liệu liên quan, **nhận diện** vấn đề N+1 query bằng cách đọc log SQL, và **giải thích** sự khác biệt giữa lazy loading, eager loading, và explicit loading để chọn đúng chiến lược cho từng tình huống.

## 0. Câu hỏi/đoán nhanh

Đọc các phát biểu sau rồi đoán đúng/sai trước khi xem đáp án:

1. Một navigation property (ví dụ `Author.Books`) là một cột thật sự tồn tại trong bảng `Authors` của database.
2. Nếu bạn viết `var authors = await db.Authors.ToListAsync();` rồi sau đó vòng `foreach` truy cập `author.Books` cho từng `author` mà **không** dùng `Include()`, mặc định EF Core sẽ tự động chạy thêm truy vấn để lấy `Books` cho bạn.
3. `Include()` luôn khiến EF Core chạy nhiều câu `SELECT` riêng biệt, mỗi navigation property một câu.
4. Vấn đề N+1 query có nghĩa là: 1 truy vấn để lấy danh sách cha, cộng thêm N truy vấn (N = số dòng cha) để lấy dữ liệu con cho từng dòng.
5. Lazy loading là hành vi **mặc định** của một `DbContext` mới tạo, không cần cấu hình gì thêm.

???+ note "Đáp án"
    1. **Sai.** Navigation property không ánh xạ tới cột nào cả — nó là một thuộc tính C# (kiểu entity khác hoặc tập hợp entity khác) giúp bạn *điều hướng* từ entity này sang entity liên quan trong code; quan hệ thật sự được lưu trong database bằng khoá ngoại (foreign key) trên bảng con.
    2. **Sai** (với cấu hình mặc định, không bật lazy loading). Nếu không `Include()` và không bật lazy loading, `author.Books` sẽ là `null` hoặc rỗng — EF Core không tự động chạy thêm truy vấn.
    3. **Sai.** Với quan hệ 1-N, `Include()` thường sinh ra **một** câu `SELECT` duy nhất dùng `JOIN` (hoặc trong một số trường hợp là 2 câu tách biệt được EF Core tối ưu) — đây chính là cách `Include()` *tránh* được N+1, khác hẳn với việc lặp và truy vấn riêng cho từng dòng cha.
    4. **Đúng.** Đây chính xác là định nghĩa của N+1 — mục 4 của chương sẽ minh hoạ cụ thể.
    5. **Sai.** Lazy loading **không** bật mặc định trong EF Core — phải cài thêm gói `Microsoft.EntityFrameworkCore.Proxies` và gọi `UseLazyLoadingProxies()` tường minh. Mặc định, navigation property không được nạp (là `null`/rỗng) trừ khi bạn `Include()` hoặc tự tải bằng explicit loading.

## 1. Navigation property là gì

**Định nghĩa:** navigation property là một thuộc tính C# trên entity, có kiểu là **một entity khác** (quan hệ 1-1 hoặc phía "1" của 1-N) hoặc **một tập hợp entity khác** (phía "nhiều" của 1-N, hay N-N) — nó không ánh xạ tới cột nào trong bảng, mà đại diện cho quan hệ giữa hai bảng để bạn *điều hướng* qua lại trong code C#, thay vì tự viết `JOIN` bằng tay.

Ví dụ tối thiểu — một tác giả (`Author`) có nhiều sách (`Book`), quan hệ 1-N kinh điển:

```csharp title="C#"
// test:skip cần EF Core, không tự-compile bằng BCL
public class Author
{
    public int Id { get; set; }
    public string Name { get; set; } = "";

    public List<Book> Books { get; set; } = new();   // navigation property: 1 Author -> nhiều Book
}

public class Book
{
    public int Id { get; set; }
    public string Title { get; set; } = "";

    public int AuthorId { get; set; }        // khoá ngoại (foreign key) — đây mới là cột thật
    public Author Author { get; set; } = null!;  // navigation property: mỗi Book -> đúng 1 Author
}
```

Ở đây `Author.Books` (kiểu `List<Book>`) và `Book.Author` (kiểu `Author`) đều là navigation property — chúng cho phép viết `author.Books` hoặc `book.Author.Name` trong C#. Cột thật sự tồn tại trong bảng `Books` chỉ có `AuthorId` (khoá ngoại trỏ về `Authors.Id`); bảng `Authors` không có cột nào tên `Books` cả.

**Dùng sai:** quên khởi tạo tập hợp navigation property phía "nhiều" (`Books`) bằng `= new()`, rồi cố `.Add()` vào nó ngay sau khi tạo entity mới bằng `new Author()` mà chưa gán gì cho `Books` — không lỗi biên dịch, nhưng ném exception lúc chạy.

```csharp title="C#"
// test:skip cần EF Core; minh hoạ NullReferenceException khi quên khởi tạo collection
public class Author
{
    public int Id { get; set; }
    public string Name { get; set; } = "";
    public List<Book> Books { get; set; } = null!;   // không khởi tạo sẵn
}

var author = new Author { Name = "Nguyễn Nhật Ánh" };
author.Books.Add(new Book { Title = "Kính vạn hoa" });   // Books đang là null
// System.NullReferenceException: Object reference not set to an instance of an object.
```

Vì thuộc tính `Books` được khai báo `= null!` (ép kiểu để qua mặt trình biên dịch nullable, nhưng thật sự vẫn là `null` lúc chạy) và không có gì gán giá trị thật trước khi `.Add()` được gọi, CLR ném `NullReferenceException` ngay khi cố truy cập một thành viên (`.Add`) trên tham chiếu `null`. Đây là lý do quy ước phổ biến là khởi tạo `List<T>`/`ICollection<T>` bằng `= new()` ngay tại nơi khai báo, như ví dụ `Author.Books` ban đầu.

## 2. Cấu hình quan hệ 1-N trong EF Core (Fluent API cơ bản)

**Định nghĩa:** Fluent API là cách cấu hình model của EF Core bằng code C# (thay vì data annotation `[Attribute]`), viết bên trong phương thức `OnModelCreating(ModelBuilder modelBuilder)` của `DbContext` — nó cho phép khai báo tường minh quan hệ giữa các entity (ai là "1", ai là "nhiều", khoá ngoại tên gì) khi EF Core không thể (hoặc bạn không muốn) tự suy luận bằng quy ước (convention).

Ví dụ tối thiểu — cấu hình tường minh quan hệ 1-N giữa `Author` và `Book` đã khai báo ở mục 1:

```csharp title="C#"
// test:skip cần EF Core, không tự-compile bằng BCL
using Microsoft.EntityFrameworkCore;

public class LibraryContext : DbContext
{
    public DbSet<Author> Authors => Set<Author>();
    public DbSet<Book> Books => Set<Book>();

    protected override void OnModelCreating(ModelBuilder modelBuilder)
    {
        modelBuilder.Entity<Book>()
            .HasOne(b => b.Author)       // mỗi Book có 1 Author
            .WithMany(a => a.Books)      // mỗi Author có nhiều Book
            .HasForeignKey(b => b.AuthorId);   // khoá ngoại nằm trên Book.AuthorId
    }
}
```

Câu lệnh này đọc thành: "một `Book` có một (`HasOne`) `Author`, và ngược lại một `Author` có nhiều (`WithMany`) `Book`, khoá ngoại (`HasForeignKey`) là cột `AuthorId` trên bảng `Books`". Thật ra, với đặt tên đúng quy ước như ở mục 1 (`AuthorId` trên `Book`, navigation property hai chiều), EF Core **tự suy luận** được quan hệ này mà không cần đoạn Fluent API trên — nhưng viết tường minh giúp code rõ ràng hơn và bắt buộc phải dùng khi tên không theo quy ước, hoặc khi có nhiều khoá ngoại cùng trỏ tới một bảng (ví dụ `Book` có cả `AuthorId` và `EditorId` cùng trỏ tới `Author`).

**Dùng sai:** gọi `HasForeignKey` với một thuộc tính không tồn tại trên entity (viết sai tên) — không phải lỗi biên dịch nếu dùng chuỗi tên thuộc tính, nhưng nếu dùng lambda biểu thức như ví dụ trên và thuộc tính không tồn tại thì đây **là** lỗi biên dịch:

```csharp title="C#"
// test:skip cần EF Core; minh hoạ lỗi CS0117 khi tên thuộc tính sai
modelBuilder.Entity<Book>()
    .HasOne(b => b.Author)
    .WithMany(a => a.Books)
    .HasForeignKey(b => b.AuthrId);   // gõ sai "AuthrId" — không tồn tại trên Book
// CS0117: 'Book' does not contain a definition for 'AuthrId'
```

Vì `HasForeignKey(b => b.AuthrId)` dùng biểu thức lambda kiểu mạnh (strongly-typed) trỏ trực tiếp vào thuộc tính C#, trình biên dịch kiểm tra sự tồn tại của `AuthrId` trên `Book` ngay lúc biên dịch và báo lỗi **CS0117** vì thuộc tính đó chưa từng được khai báo.

### 2.1 Cấu hình quan hệ N-N (nhiều-nhiều)

**Định nghĩa:** quan hệ N-N là quan hệ trong đó mỗi bản ghi của bảng A có thể liên kết với nhiều bản ghi của bảng B, và ngược lại — trong database quan hệ, nó luôn cần một **bảng trung gian** (join table) chứa hai khoá ngoại; từ EF Core 5 trở đi, bạn có thể khai báo N-N trực tiếp bằng hai navigation property dạng tập hợp ở cả hai phía mà không cần tự viết entity cho bảng trung gian.

Ví dụ tối thiểu — một `Book` có nhiều `Tag` (thẻ phân loại), và mỗi `Tag` có thể gắn cho nhiều `Book`:

```csharp title="C#"
// test:skip cần EF Core, không tự-compile bằng BCL
public class Book
{
    public int Id { get; set; }
    public string Title { get; set; } = "";

    public List<Tag> Tags { get; set; } = new();   // N-N: 1 Book -> nhiều Tag
}

public class Tag
{
    public int Id { get; set; }
    public string Name { get; set; } = "";

    public List<Book> Books { get; set; } = new();   // N-N: 1 Tag -> nhiều Book
}
```

Với khai báo này, EF Core tự tạo (bằng migration) một bảng trung gian ẩn tên `BookTag` chứa hai cột khoá ngoại `BooksId` và `TagsId` — bạn không cần tự viết entity cho bảng đó trừ khi cần thêm cột khác (ví dụ `DateTagged`) vào chính quan hệ này, lúc đó phải khai báo entity trung gian tường minh (nằm ngoài phạm vi tối thiểu ở đây).

**Dùng sai:** khai báo navigation property tập hợp chỉ ở **một phía** (ví dụ chỉ `Book.Tags`, không có `Tag.Books`) rồi kỳ vọng EF Core tự hiểu đây là N-N hai chiều — EF Core vẫn build được, nhưng nó hiểu đây là quan hệ **một chiều** (unidirectional), khiến bạn không thể truy vấn "tag này thuộc những sách nào" qua navigation property mà phải viết `Where` thủ công.

```csharp title="C#"
// test:skip cần EF Core; minh hoạ hiểu sai N-N một chiều thành hai chiều
public class Tag
{
    public int Id { get; set; }
    public string Name { get; set; } = "";
    // thiếu: public List<Book> Books { get; set; } = new();
}

// Cố truy cập chiều ngược lại (không tồn tại):
var tag = await db.Tags.FirstAsync(t => t.Id == 1);
var sachCuaTag = tag.Books;   // CS1061: 'Tag' does not contain a definition for 'Books'
```

Đây là lỗi **CS1061** (không tìm thấy thành viên), xảy ra ngay lúc biên dịch — vì `Tag` chưa từng khai báo thuộc tính `Books`, không phải lỗi runtime của EF Core. Bài học: quan hệ N-N hai chiều cần khai báo navigation property tập hợp ở **cả hai** entity tham gia.

### 2.2 Quan hệ bắt buộc (required) vs tuỳ chọn (optional) và hành vi xoá

**Định nghĩa:** một quan hệ 1-N là **bắt buộc** (required) nếu phía "nhiều" không thể tồn tại mà thiếu phía "1" (khoá ngoại không cho phép `NULL`), và là **tuỳ chọn** (optional) nếu phía "nhiều" có thể tồn tại độc lập, không gắn với bản ghi cha nào (khoá ngoại cho phép `NULL`); đi kèm với đó, `OnDelete(...)` chỉ định database phải làm gì với các bản ghi con khi bản ghi cha bị xoá — ví dụ `DeleteBehavior.Cascade` (xoá luôn con) hay `DeleteBehavior.Restrict` (chặn xoá cha nếu còn con).

Ví dụ tối thiểu — cấu hình `Book.AuthorId` là bắt buộc (mọi sách phải có tác giả) và chặn xoá tác giả nếu còn sách:

```csharp title="C#"
// test:skip cần EF Core, không tự-compile bằng BCL
protected override void OnModelCreating(ModelBuilder modelBuilder)
{
    modelBuilder.Entity<Book>()
        .HasOne(b => b.Author)
        .WithMany(a => a.Books)
        .HasForeignKey(b => b.AuthorId)
        .IsRequired()                          // AuthorId không được NULL
        .OnDelete(DeleteBehavior.Restrict);    // chặn xoá Author nếu còn Book tham chiếu
}
```

`IsRequired()` khiến EF Core sinh cột `"AuthorId"` với ràng buộc `NOT NULL` khi tạo bảng qua migration; `OnDelete(DeleteBehavior.Restrict)` khiến PostgreSQL từ chối câu lệnh `DELETE` trên `Authors` nếu còn dòng `Books` nào tham chiếu tới `Id` đó, thay vì mặc định `Cascade` (xoá tác giả sẽ tự động xoá luôn mọi sách của người đó).

**Dùng sai:** đặt `OnDelete(DeleteBehavior.Restrict)` nhưng vẫn cố xoá một `Author` đang còn `Book` tham chiếu — không lỗi biên dịch, nhưng PostgreSQL từ chối thao tác lúc runtime bằng lỗi vi phạm khoá ngoại.

```csharp title="C#"
// test:skip cần EF Core; minh hoạ DbUpdateException khi vi phạm ràng buộc khoá ngoại
var author = await db.Authors.FirstAsync(a => a.Id == 1);   // author này còn sách
db.Authors.Remove(author);
await db.SaveChangesAsync();
// Microsoft.EntityFrameworkCore.DbUpdateException: An error occurred while saving
// the entity changes. See the inner exception for details.
//  ---> Npgsql.PostgresException: 23503: update or delete on table "Authors"
//       violates foreign key constraint "FK_Books_Authors_AuthorId" on table "Books"
```

Mã lỗi PostgreSQL **`23503`** (foreign_key_violation) được Npgsql ném lên, EF Core bọc nó trong `DbUpdateException` khi `SaveChangesAsync()` gửi câu `DELETE` xuống — vì `DeleteBehavior.Restrict` đã cấu hình đúng ý "không cho xoá cha khi còn con", database chặn thao tác này để bảo toàn tính toàn vẹn dữ liệu, thay vì âm thầm để lại các dòng `Books` mồ côi (`AuthorId` trỏ tới một `Author` không còn tồn tại).

## 3. Include() để eager load

**Định nghĩa:** `Include()` là một phương thức LINQ mở rộng riêng của EF Core, chỉ định rằng khi truy vấn được thực thi, EF Core phải **nạp sẵn** (eager load) dữ liệu của navigation property được chỉ định cùng lúc với entity chính, thay vì để nó trống — kết quả là chỉ **một** lượt truy vấn (thường một câu `SELECT` với `JOIN`) mang về cả entity cha lẫn dữ liệu con liên quan.

Ví dụ tối thiểu — lấy danh sách tác giả **kèm theo** sách của từng người, dùng `Author`/`Book` đã khai báo ở mục 1:

```csharp title="C#"
// test:skip cần EF Core, minh hoạ Include
var authors = await db.Authors
    .Include(a => a.Books)     // nạp sẵn navigation property "Books"
    .ToListAsync();

foreach (var author in authors)
{
    Console.WriteLine($"{author.Name}: {author.Books.Count} cuốn sách");
    // author.Books đã có sẵn dữ liệu -- KHÔNG cần truy vấn thêm
}
```

SQL EF Core sinh ra (xấp xỉ, dialect PostgreSQL — dùng `LEFT JOIN` để không mất tác giả chưa có sách nào):

```sql title="SQL"
SELECT a."Id", a."Name", b."Id", b."Title", b."AuthorId"
FROM "Authors" AS a
LEFT JOIN "Books" AS b ON a."Id" = b."AuthorId"
ORDER BY a."Id";
```

Chỉ **một** lượt truy vấn (một round-trip tới database) được gửi đi, bất kể có bao nhiêu tác giả — đây chính là điểm khác biệt cốt lõi so với vấn đề N+1 sẽ minh hoạ ở mục 4.

**Dùng sai:** quên `Include()` rồi vẫn truy cập navigation property, kỳ vọng nó tự có dữ liệu — không lỗi biên dịch, không exception, nhưng dữ liệu **rỗng** một cách âm thầm.

```csharp title="C#"
// test:skip cần EF Core; minh hoạ collection rỗng âm thầm khi quên Include
var authors = await db.Authors.ToListAsync();   // KHÔNG có .Include(a => a.Books)

foreach (var author in authors)
{
    Console.WriteLine($"{author.Name}: {author.Books.Count} cuốn sách");
    // In ra "0 cuốn sách" cho MỌI tác giả, dù họ thật sự có sách trong database
}
```

Vì không `Include()` và không bật lazy loading, EF Core chỉ nạp các cột thuộc bảng `Authors`; thuộc tính `Books` giữ nguyên giá trị khởi tạo mặc định là `List<Book>` rỗng (từ `= new()` ở mục 1) — không phải `null` gây exception, mà là **rỗng nhưng sai**, dễ bị bỏ sót vì chương trình chạy "bình thường" và không báo lỗi gì.

### 3.1 ThenInclude() cho quan hệ nhiều cấp

**Định nghĩa:** `ThenInclude()` là phương thức nối tiếp ngay sau `Include()`, dùng để nạp sẵn thêm một navigation property **của chính entity vừa được `Include()`** — cho phép nạp sâu nhiều cấp quan hệ (ví dụ: tác giả → sách → thẻ phân loại của từng sách) trong cùng một truy vấn.

Ví dụ tối thiểu — dùng `Book.Tags` đã khai báo ở mục 2.1, nạp tác giả kèm sách kèm thẻ phân loại của mỗi sách:

```csharp title="C#"
// test:skip cần EF Core, minh hoạ ThenInclude
var authors = await db.Authors
    .Include(a => a.Books)             // cấp 1: Author -> Books
        .ThenInclude(b => b.Tags)      // cấp 2: mỗi Book -> Tags
    .ToListAsync();
```

`ThenInclude` luôn phải theo ngay sau `Include` (hoặc sau một `ThenInclude` khác), vì nó nạp tiếp navigation property của **kết quả của lệnh nạp liền trước**, không phải của entity gốc `Author`.

**Dùng sai:** gọi `ThenInclude` mà không có `Include` liền trước nó chỉ định đúng đường đi — ví dụ cố nạp `Tags` ngay từ `Authors` mà bỏ qua bước `Books`, khi `Author` không có navigation property nào tên `Tags` trực tiếp.

```csharp title="C#"
// test:skip cần EF Core; minh hoạ lỗi CS1061 khi ThenInclude sai đường đi
var authors = await db.Authors
    .Include(a => a.Books)
    .ThenInclude(b => b.Author)      // quay lại Author -- không sai cú pháp nhưng vô nghĩa
    .ThenInclude(a => a.Tags)        // CS1061: 'Author' không có 'Tags'
    .ToListAsync();
// CS1061: 'Author' does not contain a definition for 'Tags'
```

Lỗi **CS1061** xảy ra vì kiểu trả về của `ThenInclude(b => b.Author)` là `Author` (không phải `Book`), và `Author` chưa từng khai báo thuộc tính `Tags` — trình biên dịch phát hiện ngay lúc biên dịch vì `ThenInclude` là generic, kiểu tham số suy ra từ kết quả bước trước.

## 4. Vấn đề N+1 query

**Định nghĩa:** N+1 query là một vấn đề hiệu năng xảy ra khi code chạy **1 truy vấn** để lấy danh sách N bản ghi cha, rồi sau đó chạy thêm **N truy vấn riêng biệt** (một truy vấn cho mỗi bản ghi cha) để lấy dữ liệu con liên quan — tổng cộng N+1 lượt round-trip tới database, thay vì gộp lại thành một (hoặc một vài) lượt.

Ví dụ tối thiểu — code **KHÔNG dùng `Include()`**, nhưng bật lazy loading (xem mục 5) để minh hoạ N+1 xảy ra như thế nào khi lặp qua danh sách tác giả rồi truy cập `Books` cho từng người:

```csharp title="C#"
// test:skip cần EF Core + lazy loading proxies; minh hoạ N+1 cụ thể
var authors = await db.Authors.ToListAsync();   // Truy vấn #1: lấy N tác giả

foreach (var author in authors)
{
    // Với lazy loading bật: mỗi lần truy cập author.Books lần đầu tiên
    // sẽ kích hoạt MỘT truy vấn SQL riêng để lấy sách của đúng tác giả này.
    Console.WriteLine($"{author.Name}: {author.Books.Count} cuốn sách");   // Truy vấn #2..#(N+1)
}
```

Log SQL thật sự chạy ra (giả sử có 3 tác giả — chú ý có **4** câu lệnh, không phải 1):

```sql title="SQL"
-- Truy vấn #1 (lấy danh sách tác giả)
SELECT a."Id", a."Name" FROM "Authors" AS a;

-- Truy vấn #2 (lazy load Books cho tác giả Id=1, kích hoạt khi foreach chạm tới author đầu tiên)
SELECT b."Id", b."Title", b."AuthorId" FROM "Books" AS b WHERE b."AuthorId" = 1;

-- Truy vấn #3 (lazy load Books cho tác giả Id=2)
SELECT b."Id", b."Title", b."AuthorId" FROM "Books" AS b WHERE b."AuthorId" = 2;

-- Truy vấn #4 (lazy load Books cho tác giả Id=3)
SELECT b."Id", b."Title", b."AuthorId" FROM "Books" AS b WHERE b."AuthorId" = 3;
```

Với 3 tác giả: 1 truy vấn ban đầu + 3 truy vấn lazy load = **4 truy vấn** (N+1 với N=3). Nếu bảng `Authors` có 10.000 dòng, đây sẽ là **10.001 lượt round-trip riêng biệt** tới PostgreSQL — mỗi round-trip tốn chi phí mạng cố định (latency) dù câu lệnh có đơn giản tới đâu, khiến tổng thời gian chạy chậm đi rất nhiều so với gộp lại thành một truy vấn.

**So sánh: cùng logic, nhưng dùng `Include()`** — chỉ **1** truy vấn duy nhất, bất kể có bao nhiêu tác giả:

```csharp title="C#"
// test:skip cần EF Core, minh hoạ cách Include() loại bỏ N+1
var authors = await db.Authors
    .Include(a => a.Books)      // nạp sẵn TẤT CẢ Books trong CÙNG một truy vấn
    .ToListAsync();

foreach (var author in authors)
{
    Console.WriteLine($"{author.Name}: {author.Books.Count} cuốn sách");
    // Không có truy vấn nào thêm ở đây -- Books đã có sẵn từ Include() phía trên
}
```

Log SQL thật sự chạy ra — **đúng 1 câu lệnh**, dùng `LEFT JOIN` để lấy cả tác giả lẫn sách cùng lúc:

```sql title="SQL"
SELECT a."Id", a."Name", b."Id", b."Title", b."AuthorId"
FROM "Authors" AS a
LEFT JOIN "Books" AS b ON a."Id" = b."AuthorId"
ORDER BY a."Id";
```

Đây là bản chất của việc `Include()` "giải quyết" N+1: gộp N+1 lượt round-trip nhỏ lẻ thành 1 lượt duy nhất, đánh đổi bằng việc câu `SELECT` đó trả về nhiều dữ liệu hơn trong một lần (kết quả `JOIN` có thể có dòng lặp lại cột tác giả cho mỗi sách), nhưng tổng chi phí mạng và thời gian thường thấp hơn rất nhiều so với hàng nghìn round-trip riêng lẻ.

**Dùng sai (nhận diện N+1 khi review code):** dấu hiệu điển hình của N+1 là gọi `ToListAsync()`/`ToList()` để materialize một danh sách, sau đó bên trong `foreach` truy cập bất kỳ navigation property nào của từng phần tử mà **không** có `Include()` tương ứng trước đó — điều này không gây lỗi biên dịch hay exception, chỉ gây **chậm dần khi dữ liệu tăng lên**, nên rất dễ lọt qua trong môi trường phát triển (ít dữ liệu, ít nhận ra) rồi mới lộ ra ở production.

```csharp title="C#"
// test:skip cần EF Core; mẫu code điển hình chứa N+1, cần bắt khi review
var orders = await db.Orders.ToListAsync();          // 1 truy vấn
foreach (var order in orders)
{
    var soLuongSanPham = order.Items.Count;          // N truy vấn nếu Items không được Include
}
// Không lỗi biên dịch, không exception -- chỉ chậm dần theo số lượng "orders".
```

Cách phát hiện đáng tin cậy nhất không phải "đọc code rồi đoán", mà là **bật log SQL** (`options.LogTo(Console.WriteLine)` khi cấu hình `DbContext`) và đếm số câu lệnh thật sự chạy ra khi thực thi đoạn code nghi ngờ — nếu số câu lệnh tỉ lệ thuận với số dòng trong danh sách cha, đó chính là N+1.

## 5. Lazy loading vs eager loading vs explicit loading

**Định nghĩa chung:** đây là ba **thời điểm khác nhau** mà navigation property được nạp dữ liệu từ database — khác nhau ở chỗ *ai* ra lệnh nạp và *khi nào*.

- **Eager loading** (`Include()`/`ThenInclude()`, đã học ở mục 3): dữ liệu liên quan được nạp **ngay trong truy vấn ban đầu**, tường minh trong code, cùng lúc với entity chính — dùng khi bạn *biết trước* chắc chắn sẽ cần dữ liệu con ngay sau đó (ví dụ: trang danh sách tác giả luôn hiển thị kèm số lượng sách).
- **Lazy loading**: dữ liệu liên quan được nạp **tự động, ngầm định**, đúng vào thời điểm code lần đầu truy cập navigation property đó (như minh hoạ N+1 ở mục 4) — cần cài thêm gói `Microsoft.EntityFrameworkCore.Proxies`, bật `UseLazyLoadingProxies()`, **và khai báo navigation property là `virtual`** (`public virtual List<Book> Books { get; set; }`) — cơ chế proxy hoạt động bằng cách EF Core tự sinh một class con override property đó để chèn logic tải dữ liệu, nên nếu thiếu `virtual`, property chỉ trả về giá trị rỗng có sẵn (không lỗi, không tự tải, N+1 cũng không xảy ra — nhưng dữ liệu con luôn trống); dùng thận trọng vì dễ vô tình gây N+1 như vừa thấy, chỉ phù hợp khi việc truy cập navigation property là hiếm và không nằm trong vòng lặp.
- **Explicit loading** (`Entry(...).Collection(...).LoadAsync()` hoặc `.Reference(...).LoadAsync()`): dữ liệu liên quan được nạp **theo yêu cầu tường minh, riêng lẻ**, gọi rõ ràng bằng code sau khi đã có entity chính — dùng khi bạn *chỉ đôi khi* cần dữ liệu con (ví dụ: chỉ tải `Books` khi người dùng bấm mở rộng một tác giả cụ thể trên giao diện), tránh phải `Include()` sẵn cho mọi trường hợp.

Ví dụ tối thiểu — explicit loading, chỉ tải `Books` cho **một** tác giả cụ thể, sau khi đã có entity đó:

```csharp title="C#"
// test:skip cần EF Core, minh hoạ explicit loading
var author = await db.Authors.FirstAsync(a => a.Id == 1);   // chưa có Books

await db.Entry(author)
    .Collection(a => a.Books)     // chỉ định rõ navigation property cần tải
    .LoadAsync();                 // tự chạy truy vấn riêng để tải Books cho author này

Console.WriteLine(author.Books.Count);   // giờ đã có dữ liệu
```

SQL EF Core sinh ra khi gọi `LoadAsync()` (một truy vấn riêng, chạy đúng lúc gọi, không sớm hơn):

```sql title="SQL"
SELECT b."Id", b."Title", b."AuthorId"
FROM "Books" AS b
WHERE b."AuthorId" = 1;
```

**Dùng sai:** bật `UseLazyLoadingProxies()` toàn cục cho tiện, rồi vô tình viết đúng mẫu code như mục 4 (truy cập navigation property bên trong `foreach` của một danh sách lớn) — không lỗi, nhưng đây chính là cách phổ biến nhất N+1 lọt vào production, vì lazy loading khiến N+1 "vô hình" trong code (không có dòng nào trông đáng ngờ, IntelliSense không cảnh báo).

```csharp title="C#"
// test:skip cần EF Core + Proxies; minh hoạ vì sao lazy loading dễ gây N+1 "vô hình"
// Program.cs: builder.Services.AddDbContext<LibraryContext>(o => o
//     .UseNpgsql(connStr)
//     .UseLazyLoadingProxies());   // bật lazy loading toàn cục

var authors = await db.Authors.ToListAsync();
foreach (var author in authors)
{
    // Nhìn qua, dòng dưới trông như chỉ đọc một thuộc tính bình thường --
    // không ai "thấy" được rằng nó âm thầm kích hoạt một truy vấn SQL mới.
    if (author.Books.Any(b => b.Title.Contains("EF Core")))
    {
        Console.WriteLine(author.Name);
    }
}
```

Không có thông báo lỗi hay cảnh báo biên dịch nào — về mặt hành vi chương trình chạy đúng, nhưng mỗi lần `author.Books` được truy cập lần đầu cho một `author` cụ thể, proxy lazy loading tự chạy một `SELECT` riêng; với danh sách lớn, đây là N+1 điển hình mà không có dòng code nào "trông giống" một truy vấn. Đây là lý do nhiều đội dự án (bao gồm chuẩn của giáo trình này) **khuyến nghị không bật lazy loading mặc định**, ưu tiên eager loading (`Include`) tường minh hoặc explicit loading có chủ đích, để mọi truy vấn SQL đều "nhìn thấy được" ngay trong code.

## Cạm bẫy & thực chiến

- **Quên `Include()` rồi navigation property âm thầm rỗng**: không lỗi, không exception — chỉ là `Count == 0` hoặc `null` sai sự thật, rất dễ bỏ sót vì chương trình "chạy được".
- **Bật lazy loading rồi quên mất nó đang chạy ngầm**: N+1 trở nên "vô hình" trong code review, vì dòng gây ra hàng nghìn truy vấn trông giống hệt một phép đọc thuộc tính bình thường (`author.Books.Count`) — luôn bật log SQL (`LogTo(Console.WriteLine)`) khi nghi ngờ để đếm số câu lệnh thật sự chạy.
- **`Include()` quá nhiều navigation property không cần dùng tới**: mỗi `Include()` làm câu `SELECT`/`JOIN` phình to hơn (nhiều cột hơn, có thể nhiều dòng lặp hơn với 1-N); chỉ `Include()` những gì thật sự sẽ dùng ngay sau đó, không "include cho chắc".
- **Khai báo N-N chỉ ở một phía**: EF Core hiểu thành quan hệ một chiều thay vì hai chiều, khiến chiều ngược lại không tồn tại như navigation property (lỗi biên dịch CS1061 nếu cố dùng) — luôn khai báo tập hợp ở cả hai entity tham gia N-N.
- **`ThenInclude` đi sai đường (nạp nhầm entity trung gian)**: `ThenInclude` luôn nạp tiếp từ kết quả của bước `Include`/`ThenInclude` liền trước, không phải từ entity gốc — viết sai thứ tự dẫn tới lỗi biên dịch CS1061 vì kiểu tham số không khớp.
- **So sánh N+1 chỉ bằng "cảm giác chậm" thay vì đo**: luôn xác nhận bằng log SQL hoặc công cụ đo (ví dụ MiniProfiler) đếm số lượt round-trip thật sự, tránh phỏng đoán chủ quan trước khi tối ưu.
- **Dùng `Include()` như một "eager load mặc định cho mọi truy vấn"**: một số truy vấn chỉ cần thông tin cha (ví dụ đếm số tác giả), `Include()` thừa ở đó chỉ tốn tài nguyên vô ích — chọn `Include()` theo đúng nhu cầu của từng truy vấn cụ thể, không phải theo entity.

## Bài tập

**Bài 1 (giàn giáo).** Cho `Author`/`Book` như mục 1, viết một phương thức chỉ đọc để trả về danh sách tên tác giả kèm số lượng sách của mỗi người, đảm bảo chỉ chạy **một** truy vấn SQL (không N+1). Điền vào chỗ trống:

```csharp title="C#"
// test:skip cần EF Core, bài tập điền chỗ trống
public async Task<List<(string Ten, int SoSach)>> GetAuthorBookCountsAsync()
{
    var authors = await _db.Authors
        ./* ? nạp sẵn Books để tránh N+1 khi đếm bên dưới */(a => a.Books)
        ./* ? chỉ đọc, không sửa gì */()
        .ToListAsync();

    return authors
        .Select(a => (a.Name, a.Books.Count))
        .ToList();
}
```

???+ success "Lời giải + giải thích"
    ```csharp title="C#"
    // test:skip cần EF Core
    public async Task<List<(string Ten, int SoSach)>> GetAuthorBookCountsAsync()
    {
        var authors = await _db.Authors
            .Include(a => a.Books)      // nạp sẵn Books trong CÙNG truy vấn với Authors
            .AsNoTracking()             // chỉ đọc để hiển thị, không cần snapshot
            .ToListAsync();

        return authors
            .Select(a => (a.Name, a.Books.Count))
            .ToList();
    }
    ```
    Vì sao: nếu thiếu `Include(a => a.Books)`, `a.Books.Count` trong `Select` phía dưới sẽ luôn trả về 0 (nếu không bật lazy loading) hoặc kích hoạt N+1 (nếu có bật) — cả hai đều sai hoặc chậm. `AsNoTracking()` phù hợp vì đây là truy vấn chỉ đọc để hiển thị, không có `SaveChanges()` sau đó.

**Bài 2 (thiết kế).** Thiết kế một phương thức `GetAuthorDetailAsync(int authorId)` dùng cho trang chi tiết một tác giả: hiển thị tên tác giả, danh sách sách của tác giả đó, và với **mỗi sách**, hiển thị luôn danh sách thẻ phân loại (`Tag`, đã khai báo ở mục 2.1). Yêu cầu: đúng một truy vấn SQL, trả `null` nếu không tìm thấy tác giả.

???+ success "Lời giải + giải thích"
    ```csharp title="C#"
    // test:skip cần EF Core
    public async Task<Author?> GetAuthorDetailAsync(int authorId)
    {
        return await _db.Authors
            .Include(a => a.Books)
                .ThenInclude(b => b.Tags)   // nạp sâu 2 cấp: Author -> Books -> Tags
            .AsNoTracking()
            .FirstOrDefaultAsync(a => a.Id == authorId);
    }
    ```
    Vì sao: đây là trang chi tiết, biết chắc sẽ cần cả `Books` lẫn `Tags` của từng sách ngay khi hiển thị — đúng tình huống nên dùng eager loading (`Include`/`ThenInclude`) thay vì lazy hay explicit loading. Dùng `FirstOrDefaultAsync` (không phải `FirstAsync`) vì "không tìm thấy tác giả" là kết quả hợp lệ cần trả `null`, không phải lỗi cần ném exception.

## Tự kiểm tra

1. Navigation property có ánh xạ tới một cột trong database không? Nếu không, quan hệ thật sự được lưu bằng gì?
2. Nếu không `Include()` và không bật lazy loading, việc truy cập một navigation property tập hợp (ví dụ `author.Books`) trả về gì?
3. Vấn đề N+1 query là gì — mô tả bằng số lượng truy vấn cụ thể với N bản ghi cha?
4. Vì sao `Include()` giúp tránh được N+1, xét về số lượt round-trip tới database?
5. `ThenInclude()` nạp tiếp navigation property của entity nào — entity gốc hay kết quả của bước `Include`/`ThenInclude` liền trước?
6. Vì sao lazy loading dễ khiến N+1 trở nên khó phát hiện hơn so với việc thiếu `Include()` (không bật lazy loading)?
7. Explicit loading khác eager loading ở điểm nào về thời điểm và cách gọi?
8. Khai báo navigation property tập hợp chỉ ở một phía của quan hệ N-N gây ra hậu quả gì?

???+ note "Đáp án"
    1. Không. Navigation property là thuộc tính C# dùng để điều hướng giữa các entity liên quan trong code; quan hệ thật sự được lưu trong database bằng cột khoá ngoại (foreign key) trên bảng phía "nhiều" (ví dụ `Book.AuthorId`).
    2. Nó là `null` hoặc một tập hợp rỗng (tuỳ vào có khởi tạo `= new()` sẵn hay không) — không có exception, chỉ là dữ liệu chưa được nạp, có thể gây hiểu nhầm là "không có dữ liệu con" dù thật ra chỉ là "chưa tải".
    3. Với N bản ghi cha: 1 truy vấn ban đầu để lấy danh sách cha, cộng thêm N truy vấn riêng biệt (mỗi cha một truy vấn) để lấy dữ liệu con — tổng cộng N+1 lượt truy vấn/round-trip.
    4. Vì `Include()` gộp việc nạp dữ liệu con vào **cùng một** truy vấn (thường dùng `JOIN`) với truy vấn lấy danh sách cha, nên chỉ tốn 1 lượt round-trip tới database bất kể có bao nhiêu bản ghi cha, thay vì N+1 lượt.
    5. Của kết quả bước `Include`/`ThenInclude` liền trước nó — không phải của entity gốc ban đầu trong truy vấn.
    6. Vì với lazy loading, dòng code truy cập navigation property (ví dụ `author.Books.Count`) trông giống hệt một phép đọc thuộc tính bình thường trong bộ nhớ — không có dấu hiệu nào trong code cho thấy nó đang âm thầm kích hoạt một truy vấn SQL mới, khiến N+1 khó nhận ra khi đọc/review code.
    7. Eager loading (`Include`) nạp dữ liệu con tường minh ngay trong truy vấn ban đầu, trước khi entity cha được trả về; explicit loading nạp dữ liệu con bằng một lệnh riêng biệt (`Entry(...).Collection(...).LoadAsync()`), gọi sau khi đã có entity cha, chỉ khi thật sự cần.
    8. EF Core hiểu đây là quan hệ N-N **một chiều** (unidirectional) thay vì hai chiều — phía không khai báo navigation property tập hợp sẽ không có cách truy cập chiều ngược lại qua code C#; cố dùng sẽ gặp lỗi biên dịch CS1061 vì thuộc tính đó không tồn tại.

??? abstract "DEEP DIVE: split query, AsSplitQuery(), và ranh giới với migration"
    - **Cartesian explosion khi `Include()` nhiều tập hợp cùng lúc**: nếu `Include()` hai navigation property dạng tập hợp trên cùng một entity gốc (ví dụ vừa `Include(a => a.Books)` vừa `Include(a => a.Awards)`), EF Core mặc định dùng một `JOIN` duy nhất, có thể sinh ra số dòng kết quả bằng tích số lượng `Books` × số lượng `Awards` cho mỗi tác giả — gây lãng phí băng thông đáng kể với dữ liệu nhiều.
    - **`AsSplitQuery()`**: một phương thức LINQ khác của EF Core, thay vì gộp mọi `Include()` vào một `JOIN` khổng lồ, tách thành **nhiều câu `SELECT` riêng biệt** (nhưng vẫn ít hơn hẳn N+1 — thường là 1 câu cho mỗi cấp `Include`, không phải 1 câu cho mỗi dòng) để tránh cartesian explosion; đánh đổi là nhiều round-trip hơn `AsSingleQuery()` (mặc định) nhưng ít dữ liệu trùng lặp hơn — cần đo thực tế để chọn, không có câu trả lời đúng tuyệt đối cho mọi trường hợp.
    - **Filtered include**: từ các bản EF Core gần đây, có thể lọc bớt dữ liệu ngay trong `Include()` (ví dụ chỉ nạp sách xuất bản sau năm 2020) bằng cú pháp `Include(a => a.Books.Where(b => b.Year > 2020))` cho quan hệ tập hợp — giúp giảm dữ liệu tải về mà vẫn giữ được một truy vấn duy nhất, tránh phải lọc lại bằng LINQ-to-Objects sau khi đã tải hết.
    - **Ranh giới với migration**: chương này giả định các bảng `Authors`/`Books`/`Tags` đã tồn tại đúng với cấu hình Fluent API; chương kế tiếp về migration sẽ chỉ ra cách EF Core sinh ra các câu lệnh `CREATE TABLE`/`ALTER TABLE` (bao gồm khoá ngoại, bảng trung gian N-N) từ chính những khai báo entity và Fluent API đã học ở đây, thông qua `dotnet ef migrations add`.
    - **Đo N+1 bằng công cụ, không chỉ bằng mắt**: ngoài `LogTo(Console.WriteLine)`, các công cụ như MiniProfiler hoặc Application Insights có thể đếm số lượt truy vấn thật sự trong một request HTTP — hữu ích để bắt N+1 tự động trong quy trình kiểm thử/CI thay vì chỉ dựa vào review code thủ công, kể cả khi review bằng hỗ trợ của mô hình AI dòng Claude 4.x.

**Tiếp theo →** [P2 · EF Core: Migration & Seeding](ef-core-migration.md)
