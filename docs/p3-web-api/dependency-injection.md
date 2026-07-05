---
tier: core
status: core
owner: core-team
verified_on: "2026-07-03"
dotnet_version: "10.0"
bloom: "Apply"
requires: [p3-api]
est_minutes_fast: 30
---

# Dependency Injection & Lifetime

!!! info "Bạn đang ở đây"
    **cần trước:** minimal api (biết `builder`, `app.MapGet`, chạy được một endpoint HTTP).
    **mở khoá:** ef core (DbContext luôn đăng ký qua DI), jwt/auth (các dịch vụ xác thực đều lấy qua container), và bất kỳ service nào ứng dụng của bạn cần chia sẻ hoặc thay thế được.

> **Mục tiêu:** Người học có thể **áp dụng** đúng ba lifetime (Transient/Scoped/Singleton) khi đăng ký service trong `IServiceCollection`, **giải thích** vì sao constructor injection là cách chính thay vì tự `new` hay dùng Service Locator, và **phát hiện/sửa** lỗi captive dependency khi một Singleton vô tình giữ một Scoped.

---

## 0. Đoán nhanh trước khi học

Bạn có một class `ReportService` cần gửi email. Bên trong constructor của nó, bạn viết thẳng:

```csharp title="C#"
// test:skip đoạn trích minh hoạ vấn đề, không đầy đủ để chạy độc lập
public class ReportService
{
    private readonly SmtpEmailSender _sender = new SmtpEmailSender("smtp.cong-ty.local");

    public void SendMonthlyReport(string to) => _sender.Send(to, "Báo cáo tháng");
}
```

??? question "Đoán trước: viết unit test cho `SendMonthlyReport` mà KHÔNG gửi email thật qua mạng — có làm được không? Vì sao?"
    **Không thể**, ít nhất là không dễ. `ReportService` tự `new SmtpEmailSender(...)` bên trong constructor của chính nó, nên bất kỳ ai dùng `ReportService` — kể cả unit test — đều bị buộc phải dùng luôn `SmtpEmailSender` thật, tức là luôn cố gắng kết nối SMTP thật. Không có "khe hở" nào để nhét vào một phiên bản giả (fake/mock) không gửi email thật.

    Đây chính là vấn đề gốc mà **Dependency Injection** giải quyết: để bên ngoài "tiêm" (inject) cái `ReportService` cần vào, thay vì để nó tự tạo.

---

## 1. Dependency Injection là gì và tại sao cần

**Định nghĩa (một câu):** Dependency Injection (DI) là kỹ thuật lập trình trong đó một class **nhận** những thứ nó cần (gọi là *dependency* — phụ thuộc) từ bên ngoài truyền vào, thay vì **tự tạo** (`new`) chúng bên trong chính nó.

### 1.1. Ví dụ tối thiểu: KHÔNG có DI (vấn đề gốc)

Đoạn dưới lặp lại đúng ví dụ ở mục 0 nhưng chạy độc lập, chỉ minh hoạ MỘT điều: class tự tạo dependency của chính nó.

```csharp title="Program.cs"
// test:run
var service = new ReportService();
service.SendMonthlyReport("ke-toan@congty.vn");

public class ReportService
{
    // Tự tạo SmtpEmailSender bên trong -> class này VĨNH VIỄN gắn chặt (hard-coded)
    // với SmtpEmailSender, không có cách nào thay thế nó từ bên ngoài.
    private readonly SmtpEmailSender _sender = new SmtpEmailSender("smtp.cong-ty.local");

    public void SendMonthlyReport(string to) => _sender.Send(to, "Bao cao thang");
}

public class SmtpEmailSender(string host)
{
    // Giả lập gửi mail thật (in ra console thay vì mở kết nối mạng thật).
    public void Send(string to, string subject) =>
        Console.WriteLine($"[SMTP that qua {host}] Gui '{subject}' toi {to}");
}
```

```text title="Kết quả"
[SMTP that qua smtp.cong-ty.local] Gui 'Bao cao thang' toi ke-toan@congty.vn
```

**Vấn đề cụ thể:** muốn viết unit test cho `ReportService` mà không gửi mail thật, bạn **không có cách nào** thay `SmtpEmailSender` bằng một bản giả — vì nó bị `new` cứng bên trong. Muốn đổi sang gửi qua dịch vụ khác (ví dụ SendGrid), bạn phải **sửa code bên trong** `ReportService`.

### 1.2. Ví dụ tối thiểu: CÓ DI (giải pháp)

```csharp title="Program.cs"
// test:run
// Bây giờ NGƯỜI GỌI quyết định đưa implementation nào vào -> đây là "tiêm" (inject).
IEmailSender sender = new SmtpEmailSender("smtp.cong-ty.local");
var service = new ReportService(sender);
service.SendMonthlyReport("ke-toan@congty.vn");

// Đổi sang bản giả cho test, KHÔNG sửa một dòng nào trong ReportService:
IEmailSender fakeSender = new FakeEmailSender();
var testableService = new ReportService(fakeSender);
testableService.SendMonthlyReport("test@example.com");

public interface IEmailSender
{
    void Send(string to, string subject);
}

public class SmtpEmailSender(string host) : IEmailSender
{
    public void Send(string to, string subject) =>
        Console.WriteLine($"[SMTP that qua {host}] Gui '{subject}' toi {to}");
}

public class FakeEmailSender : IEmailSender
{
    public List<string> SentTo { get; } = [];

    // Không gửi mail thật -> chỉ ghi lại để unit test kiểm tra assertion.
    public void Send(string to, string subject)
    {
        SentTo.Add(to);
        Console.WriteLine($"[FAKE] Da 'gui' (khong that) toi {to}");
    }
}

// Nhận IEmailSender qua CONSTRUCTOR -> đây là "constructor injection".
public class ReportService(IEmailSender sender)
{
    public void SendMonthlyReport(string to) => sender.Send(to, "Bao cao thang");
}
```

```text title="Kết quả"
[SMTP that qua smtp.cong-ty.local] Gui 'Bao cao thang' toi ke-toan@congty.vn
[FAKE] Da 'gui' (khong that) toi test@example.com
```

**Điểm cốt lõi:** `ReportService` giờ chỉ biết `IEmailSender` (một interface — abstraction), không biết `SmtpEmailSender` hay `FakeEmailSender` là gì. Ai gọi `new ReportService(...)` mới là người quyết định implementation cụ thể nào được dùng. Đây là nguyên tắc **Nghịch đảo phụ thuộc** (Dependency Inversion): code cấp cao (`ReportService`) phụ thuộc vào abstraction, không phụ thuộc chi tiết cụ thể.

### 1.3. Điều gì xảy ra nếu vẫn cố tự tạo dependency bên trong

Đây không phải lỗi biên dịch — code ở mục 1.1 **biên dịch và chạy bình thường**. Cái sai là ở **thiết kế**, hậu quả xuất hiện sau, khi dự án lớn lên:

- Muốn unit test `ReportService` mà không đụng mạng thật → **không làm được** vì không có chỗ nào để nhét fake vào.
- Muốn đổi nhà cung cấp email (SMTP → SendGrid) → phải **sửa code bên trong** `ReportService`, vi phạm nguyên tắc "đóng với sửa đổi, mở với mở rộng" (Open/Closed).
- Nhiều class khác cũng tự `new SmtpEmailSender(...)` riêng lẻ → cấu hình host bị lặp lại rải rác, sửa một chỗ quên chỗ khác.

DI không tạo ra tính năng mới — nó thay đổi **ai chịu trách nhiệm tạo object**, và nhờ đó code trở nên thay thế được và test được.

### 1.4. DI Container trong ASP.NET Core là gì

Viết `new ReportService(new SmtpEmailSender(...))` thủ công ở mọi nơi vẫn rất cồng kềnh khi ứng dụng có hàng chục dependency lồng nhau. ASP.NET Core cung cấp sẵn một **DI container** (hiện thực của `IServiceProvider`) để tự động hoá việc này: bạn **đăng ký** (register) một lần "khi cần `IEmailSender`, dùng `SmtpEmailSender`", rồi container tự tạo và tiêm đúng chỗ.

```csharp title="Program.cs"
// test:compile
var builder = WebApplication.CreateBuilder(args);

// Đăng ký: "khi ai đó cần IEmailSender, cấp một SmtpEmailSender".
builder.Services.AddSingleton<IEmailSender, SmtpEmailSender>();

var app = builder.Build();

// Container TỰ tạo SmtpEmailSender và tiêm vào tham số "sender" của handler.
app.MapPost("/reports/send", (string to, IEmailSender sender) =>
{
    sender.Send(to, "Bao cao thang");
    return Results.Ok();
});

app.Run();

public interface IEmailSender
{
    void Send(string to, string subject);
}

public class SmtpEmailSender : IEmailSender
{
    public void Send(string to, string subject) =>
        Console.WriteLine($"Gui '{subject}' toi {to}");
}
```

Nếu bạn yêu cầu một type mà **chưa đăng ký**, container sẽ ném lỗi ngay khi resolve — ví dụ nếu dòng `AddSingleton<IEmailSender, SmtpEmailSender>()` bị xoá nhưng handler vẫn yêu cầu `IEmailSender`, request sẽ trả về lỗi 500 với thông điệp runtime dạng:

```text title="Lỗi runtime nếu quên đăng ký"
System.InvalidOperationException: Unable to resolve service for type
'IEmailSender' while attempting to activate '...'.
```

---

## 2. Ba lifetime: Transient, Scoped, Singleton

**Định nghĩa (một câu):** *Lifetime* (vòng đời) là quy tắc container dùng để quyết định **khi nào tạo instance mới** và **khi nào tái dùng instance cũ** mỗi khi có ai yêu cầu một service đã đăng ký.

Ba phương thức đăng ký tương ứng ba lifetime trên `IServiceCollection`:

| Phương thức | Số instance được tạo | Instance sống đến khi nào |
|---|---|---|
| `AddTransient<T>()` | Một instance **mới mỗi lần** được yêu cầu | Bị giải phóng ngay sau khi nơi yêu cầu dùng xong |
| `AddScoped<T>()` | Một instance **cho mỗi scope** (mặc định: mỗi request HTTP) | Sống suốt một request, `Dispose` khi request kết thúc |
| `AddSingleton<T>()` | Đúng **một instance duy nhất** cho cả vòng đời ứng dụng | Sống từ lúc tạo lần đầu đến khi ứng dụng tắt |

### 2.1. Transient — ví dụ minh hoạ vòng đời bằng code in ra thứ tự tạo/huỷ

Container DI thật của ASP.NET Core nằm trong gói `Microsoft.Extensions.DependencyInjection`. Để thấy đúng cơ chế "tạo mới mỗi lần yêu cầu" mà không cần thêm package ngoài, đoạn dưới tự dựng một mini-container tối giản (chỉ dùng BCL) mô phỏng đúng hành vi Transient:

```csharp title="Program.cs"
// test:run
// Mini-container tự dựng (chỉ BCL) để mô phỏng đúng hành vi Transient của DI thật:
// mỗi lần "resolve" là một lần gọi factory -> luôn tạo instance MỚI.
Func<Worker> resolveTransient = () => new Worker();

Console.WriteLine("-- Lay Worker trong cung 1 'scope' --");
var a = resolveTransient();
var b = resolveTransient();
Console.WriteLine($"a va b co phai cung 1 instance? {ReferenceEquals(a, b)}");
a.Dispose();
b.Dispose();

public class Worker : IDisposable
{
    private static int _counter = 0;
    private readonly int _id;

    public Worker()
    {
        _id = ++_counter;
        Console.WriteLine($"  [TAO] Worker #{_id}");
    }

    public void Dispose() => Console.WriteLine($"  [HUY] Worker #{_id}");
}
```

```text title="Kết quả"
-- Lay Worker trong cung 1 'scope' --
  [TAO] Worker #1
  [TAO] Worker #2
a va b co phai cung 1 instance? False
  [HUY] Worker #1
  [HUY] Worker #2
```

**Quan sát:** hai lần "resolve" liên tiếp tạo **hai instance khác nhau** (`#1` và `#2`) — đúng nghĩa Transient: mới mỗi lần được yêu cầu, kể cả khi được gọi ở cùng một chỗ trong cùng một request. Trong DI container thật của ASP.NET Core (`AddTransient<Worker>()`), hành vi giống hệt: mỗi `GetRequiredService<Worker>()` (kể cả trong cùng một request/scope) trả về một instance mới, và container tự `Dispose` mọi Transient nó tạo ra khi scope chứa chúng kết thúc.

> Lưu ý kỹ thuật: đoạn trên dùng gói `Microsoft.Extensions.DependencyInjection` (namespace `Microsoft.Extensions.DependencyInjection`) — đây là gói lõi bên dưới, được ASP.NET Core Web SDK tham chiếu sẵn nên biên dịch được như một console app thuần khi có gói NuGet đó. Nếu môi trường của bạn không có sẵn, hãy xem lại ví dụ ASP.NET Core đầy đủ ở mục 2.4.

### 2.2. Scoped — một instance cho mỗi request

```csharp title="Program.cs"
// test:compile
var builder = WebApplication.CreateBuilder(args);

builder.Services.AddScoped<RequestTracker>();

var app = builder.Build();

// Cùng một request gọi 2 lần -> phải nhận CÙNG một RequestTracker (Scoped).
app.MapGet("/trace", (RequestTracker t1, RequestTracker t2) =>
    Results.Ok(new { CungInstance = ReferenceEquals(t1, t2), IdT1 = t1.Id, IdT2 = t2.Id }));

app.Run();

public class RequestTracker
{
    private static int _counter = 0;
    public int Id { get; } = ++_counter;
}
```

Khi gọi `GET /trace`, cả `t1` và `t2` được resolve trong **cùng một request** nên container trả về **cùng một instance** `RequestTracker` — response trả `CungInstance: true`. Nếu gọi `/trace` một lần nữa (request mới), `Id` sẽ tăng lên vì đó là một scope (request) khác, tạo instance mới.

### 2.3. Singleton — một instance cho cả ứng dụng

```csharp title="Program.cs"
// test:compile
var builder = WebApplication.CreateBuilder(args);

builder.Services.AddSingleton<AppStartClock>();

var app = builder.Build();

// Gọi endpoint này bao nhiêu lần, bao nhiêu request khác nhau -> vẫn CÙNG một
// StartedAt, vì AppStartClock chỉ được tạo đúng MỘT lần khi container cần lần đầu.
app.MapGet("/uptime", (AppStartClock clock) =>
    Results.Ok(new { clock.StartedAt }));

app.Run();

public class AppStartClock
{
    public DateTime StartedAt { get; } = DateTime.UtcNow;
}
```

Gọi `/uptime` nhiều lần (kể cả từ nhiều client khác nhau, đồng thời) luôn trả về **cùng một** `StartedAt`, vì `AppStartClock` chỉ được khởi tạo một lần duy nhất — khác hẳn Scoped (khác nhau theo request) và Transient (khác nhau mỗi lần gọi).

### 2.4. Điều gì xảy ra khi chọn SAI lifetime

Sai lifetime thường **không phải lỗi biên dịch** — mã vẫn build và chạy, nhưng cho hành vi runtime sai:

- Đăng ký `DbContext` (vốn phải Scoped, xem chương EF Core) là **Singleton**: mọi request dùng chung một instance `DbContext`. `DbContext` không an toàn đa luồng, nên hai request chạy đồng thời có thể ném `InvalidOperationException: A second operation was started on this context instance before a previous operation completed`, hoặc âm thầm trộn dữ liệu của request A vào response của request B.
- Đăng ký một service có trạng thái đếm/giỏ hàng theo người dùng là **Singleton** thay vì **Scoped**: mọi người dùng vô tình **dùng chung một giỏ hàng** — dữ liệu rò rỉ giữa các phiên làm việc khác nhau.
- Đăng ký một service rẻ, vô hại là **Transient** dù đáng lẽ **Singleton** (ví dụ một class đọc file cấu hình lớn): không sai dữ liệu, nhưng **tốn hiệu năng** vì tạo lại object nặng mỗi lần dùng một cách không cần thiết.

Bảng tổng hợp khi nào dùng lifetime nào (chỉ tổng hợp SAU khi đã hiểu rõ từng loại ở trên):

| Tình huống | Lifetime phù hợp | Vì sao |
|---|---|---|
| `DbContext` và repository bọc nó | Scoped | Theo dõi thay đổi và kết nối phải giới hạn trong một request, không chia sẻ đa luồng |
| Cache trong bộ nhớ, cấu hình đọc một lần, `IHttpClientFactory` | Singleton | Không có trạng thái theo người dùng, tạo một lần dùng lại rẻ và an toàn đa luồng |
| Validator, mapper, class tiện ích không giữ trạng thái | Transient | Nhẹ, không cần tái dùng, tránh vô tình giữ trạng thái giữa các lần gọi |
| Giỏ hàng / trạng thái theo phiên người dùng trong một request | Scoped | Mỗi request (người dùng) phải có instance riêng, không lẫn với người khác |

---

## 3. Constructor injection là cách chính — vì sao không dùng Service Locator

**Định nghĩa (một câu):** *Constructor injection* là việc khai báo dependency như tham số của constructor để container tự nhận diện và tiêm vào khi tạo object; ngược lại, *Service Locator* là việc tự gọi `IServiceProvider.GetService<T>()` (hoặc `GetRequiredService<T>()`) ngay bên trong logic nghiệp vụ để "tự đi lấy" dependency mình cần.

### 3.1. Ví dụ constructor injection (đúng cách)

```csharp title="Program.cs"
// test:compile
var builder = WebApplication.CreateBuilder(args);
builder.Services.AddSingleton<IClock, SystemClock>();
builder.Services.AddScoped<GreetingService>();

var app = builder.Build();

// Minimal API cũng dùng CONSTRUCTOR INJECTION cho tham số handler:
// container thấy handler cần GreetingService -> tự resolve toàn bộ cây phụ thuộc.
app.MapGet("/greet", (GreetingService svc) => Results.Ok(svc.BuildGreeting()));

app.Run();

public interface IClock
{
    DateTime Now { get; }
}

public class SystemClock : IClock
{
    public DateTime Now => DateTime.UtcNow;
}

// GreetingService khai báo rõ ràng nó cần IClock qua constructor.
// Nhìn chữ ký constructor là biết NGAY class này phụ thuộc vào gì -> dễ đọc, dễ test.
public class GreetingService(IClock clock)
{
    public string BuildGreeting() => $"Bay gio la {clock.Now:HH:mm} UTC";
}
```

### 3.2. Ví dụ Service Locator (cách nên tránh) và vì sao nó tệ hơn

```csharp title="Program.cs"
// test:compile
var builder = WebApplication.CreateBuilder(args);
builder.Services.AddSingleton<IClock, SystemClock>();

var app = builder.Build();

// Tiêm thẳng IServiceProvider rồi tự "đi lấy" bên trong -> đây là Service Locator.
app.MapGet("/greet-locator", (IServiceProvider sp) =>
{
    var clock = sp.GetRequiredService<IClock>(); // ẩn dependency thật sự bên trong thân hàm
    return Results.Ok($"Bay gio la {clock.Now:HH:mm} UTC");
});

app.Run();

public interface IClock
{
    DateTime Now { get; }
}

public class SystemClock : IClock
{
    public DateTime Now => DateTime.UtcNow;
}
```

Cả hai đoạn trên **đều chạy đúng** — Service Locator không gây lỗi runtime ở ví dụ nhỏ này. Vấn đề là về **thiết kế và khả năng bảo trì**:

- Với constructor injection (3.1), chỉ cần đọc chữ ký `GreetingService(IClock clock)` là biết ngay class này cần gì — dependency được khai báo **tường minh**.
- Với Service Locator (3.2), dependency thật sự (`IClock`) bị **giấu bên trong thân hàm**. Muốn biết handler cần gì phải đọc toàn bộ code, không thể nhìn chữ ký mà đoán được.
- Service Locator khiến lỗi "quên đăng ký" bị đẩy từ **lúc khởi động/biên dịch** sang **lúc runtime** ở một dòng sâu bên trong logic, khó phát hiện hơn khi test.
- Ngoại lệ hợp lệ hiếm hoi để dùng `IServiceProvider` trực tiếp: khi cần **tạo scope thủ công** bên trong một Singleton (xem mục 4.2) — đó không phải Service Locator theo nghĩa xấu, vì mục đích là quản lý vòng đời, không phải để né khai báo dependency.

---

## 4. Captive dependency: khi Singleton "giam" một Scoped

**Định nghĩa (một câu):** *Captive dependency* là lỗi thiết kế khi một service sống lâu hơn (ví dụ Singleton) giữ tham chiếu trực tiếp tới một service sống ngắn hơn (ví dụ Scoped) qua constructor injection, khiến service ngắn hạn đó bị "giam cầm" và sống sai vòng đời của nó.

### 4.1. Tái hiện lỗi cụ thể

```csharp title="Program.cs"
// test:compile
var builder = WebApplication.CreateBuilder(args);

// RequestState: PHẢI Scoped vì nó đại diện dữ liệu của một request cụ thể.
builder.Services.AddScoped<RequestState>();

// AuditLogger: đăng ký Singleton (vì lầm tưởng "ghi log thì rẻ, singleton cho nhanh")
// nhưng constructor lại nhận RequestState (Scoped) -> CAPTIVE DEPENDENCY.
builder.Services.AddSingleton<AuditLogger>();

var app = builder.Build(); // <-- container VALIDATE ngay tại đây

app.MapGet("/", (AuditLogger logger) => Results.Ok());
app.Run();

public class RequestState
{
    public Guid RequestId { get; } = Guid.NewGuid();
}

public class AuditLogger(RequestState state)
{
    public void Log(string message) => Console.WriteLine($"[{state.RequestId}] {message}");
}
```

**Hành vi runtime cụ thể:** dòng `builder.Build()` sẽ **ném ngoại lệ ngay khi khởi động ứng dụng** (không phải khi có request tới), vì ASP.NET Core bật `ValidateScopes = true` mặc định trong môi trường Development:

```text title="Ngoại lệ khi builder.Build()"
System.AggregateException: Some services are not able to be constructed
 ---> System.InvalidOperationException: Cannot consume scoped service
'RequestState' from singleton 'AuditLogger'.
```

Nếu validate bị tắt (một số cấu hình production cũ), ứng dụng vẫn khởi động được nhưng hậu quả còn nguy hiểm hơn: `AuditLogger` chỉ được tạo **một lần duy nhất**, "chụp" đúng một `RequestState` (của request đầu tiên) và **dùng lại `RequestId` đó cho mọi request sau** — log kiểm toán sẽ sai lệch hoàn toàn, mọi request đều bị gán nhầm `RequestId` của request đầu tiên.

### 4.2. Cách sửa đúng

Cách 1 — hạ lifetime của `AuditLogger` xuống Scoped nếu nó thật sự chỉ cần dùng trong phạm vi một request:

```csharp title="Program.cs"
// test:compile
var builder = WebApplication.CreateBuilder(args);
builder.Services.AddScoped<RequestState>();
builder.Services.AddScoped<AuditLogger>(); // đổi Singleton -> Scoped: hết captive
var app = builder.Build();
app.MapGet("/", (AuditLogger logger) => Results.Ok());
app.Run();

public class RequestState
{
    public Guid RequestId { get; } = Guid.NewGuid();
}

public class AuditLogger(RequestState state)
{
    public void Log(string message) => Console.WriteLine($"[{state.RequestId}] {message}");
}
```

Cách 2 — nếu `AuditLogger` **thật sự cần** là Singleton (ví dụ nó giữ một buffer ghi log dùng chung, tốn kém để tạo lại), không tiêm `RequestState` trực tiếp mà tiêm `IServiceScopeFactory` và tự mở scope mỗi khi cần:

```csharp title="Program.cs"
// test:compile
var builder = WebApplication.CreateBuilder(args);
builder.Services.AddScoped<RequestState>();
builder.Services.AddSingleton<AuditLogger>(); // vẫn Singleton, nhưng không giam Scoped nữa

var app = builder.Build();
app.MapGet("/", (AuditLogger logger) =>
{
    logger.LogCurrentRequest("Xu ly request");
    return Results.Ok();
});
app.Run();

public class RequestState
{
    public Guid RequestId { get; } = Guid.NewGuid();
}

// Nhận IServiceScopeFactory (an toàn cho Singleton) thay vì RequestState trực tiếp.
public class AuditLogger(IServiceScopeFactory scopeFactory)
{
    public void LogCurrentRequest(string message)
    {
        // Mở một scope RIÊNG mỗi lần gọi -> lấy đúng RequestState của scope hiện tại,
        // rồi Dispose ngay sau khi dùng xong. Không giữ tham chiếu Scoped lâu dài.
        using var scope = scopeFactory.CreateScope();
        var state = scope.ServiceProvider.GetRequiredService<RequestState>();
        Console.WriteLine($"[{state.RequestId}] {message}");
    }
}
```

**Vì sao cách 2 an toàn:** `AuditLogger` không còn giữ `RequestState` như một field cố định. Mỗi lần `LogCurrentRequest` được gọi, nó tự mở một `IServiceScope` mới, lấy `RequestState` **hợp lệ của đúng scope đó**, dùng xong thì `Dispose` — không có instance Scoped nào bị "giam" bên trong Singleton.

---

## 5. Resolve service trong Minimal API handler qua tham số hàm

**Định nghĩa (một câu):** Trong Minimal API, bạn không cần gọi `GetService` thủ công — chỉ cần khai báo service cần dùng như một **tham số của delegate handler**, container tự nhận diện type đó đã đăng ký và tiêm vào trước khi handler chạy.

```csharp title="Program.cs"
// test:compile
var builder = WebApplication.CreateBuilder(args);

builder.Services.AddScoped<IOrderRepository, InMemoryOrderRepository>();

var app = builder.Build();

// "repo" là tham số bình thường về mặt cú pháp, nhưng vì kiểu IOrderRepository đã
// đăng ký trong DI, framework tự hiểu đây KHÔNG phải route/query parameter mà là
// một service cần inject -> tự gọi GetRequiredService<IOrderRepository>() giúp bạn.
app.MapGet("/orders/{id:int}", (int id, IOrderRepository repo) =>
{
    var order = repo.FindById(id);
    return order is not null ? Results.Ok(order) : Results.NotFound();
});

app.Run();

public interface IOrderRepository
{
    string? FindById(int id);
}

public class InMemoryOrderRepository : IOrderRepository
{
    private readonly Dictionary<int, string> _orders = new() { [1] = "Don hang #1" };
    public string? FindById(int id) => _orders.GetValueOrDefault(id);
}
```

Framework phân biệt "tham số route/query" và "tham số service tiêm" dựa trên: nếu type khớp với route template (`{id:int}`) hoặc là kiểu nguyên thuỷ lấy từ query string, nó được bind từ HTTP request; nếu type đã được đăng ký trong `IServiceCollection` (thường là interface hoặc class phức tạp), nó được **resolve từ DI container**. Bạn có thể trộn cả hai loại tham số tự do trong cùng một handler, như ví dụ trên (`int id` từ route, `IOrderRepository repo` từ DI).

Nếu `IOrderRepository` **chưa** được đăng ký nhưng handler vẫn yêu cầu nó, request tới `/orders/1` sẽ trả về **500 Internal Server Error** với thông điệp runtime tương tự mục 1.4 (`Unable to resolve service for type 'IOrderRepository'`) — lỗi này KHÔNG xuất hiện lúc biên dịch, chỉ xuất hiện khi có request thật gọi tới handler đó.

---

## Cạm bẫy & thực chiến

- **Captive dependency (chi tiết ở mục 4):** Singleton tiêm thẳng Scoped qua constructor. Container ném lỗi ngay `builder.Build()` nếu `ValidateScopes` bật (mặc định Development) — đừng tắt validate này để "cho qua", hãy sửa lifetime.
- **Quên đăng ký:** yêu cầu resolve một type chưa `Add...` trong `IServiceCollection` → `InvalidOperationException: Unable to resolve service for type ...` xảy ra ở **runtime khi có request**, không phải lúc biên dịch. Luôn kiểm tra `Program.cs` đã đăng ký đủ trước khi chạy thử endpoint mới.
- **Đăng ký cùng interface nhiều lần:** ví dụ gọi `AddScoped<IEmailSender, SmtpEmailSender>()` rồi sau đó lại `AddScoped<IEmailSender, FakeEmailSender>()` — khi resolve **một** instance (`GetRequiredService<IEmailSender>()`), đăng ký **cuối cùng thắng** (`FakeEmailSender`). Muốn lấy TẤT CẢ implementation đã đăng ký, tiêm `IEnumerable<IEmailSender>` thay vì `IEmailSender`.
- **Tự `Dispose` service do container quản lý:** container tự gọi `Dispose()` cho mọi Scoped/Transient implement `IDisposable` mà nó tạo ra, đúng lúc scope kết thúc. Nếu bạn tự thêm code `Dispose` thủ công cho một service được inject vào, có thể gây `ObjectDisposedException` cho request khác vẫn đang dùng chung instance đó (với Singleton) hoặc double-dispose.
- **Transient "tưởng an toàn tuyệt đối" nhưng vẫn bị giam:** nếu một Singleton tiêm một Transient có giữ trạng thái hoặc implement `IDisposable`, Transient đó **vẫn chỉ được tạo một lần** (vì Singleton chỉ khởi tạo cây phụ thuộc của nó một lần) — lifetime thực tế của một service bị giới hạn bởi lifetime **dài nhất** trong chuỗi phụ thuộc chứa nó, không phải bởi cách chính nó được đăng ký.
- **Đăng ký service cần cấu hình động bằng factory nhưng lại dùng `Add...<T>()` không tham số:** nếu constructor cần một giá trị chỉ biết được lúc runtime (đọc từ `IConfiguration`), phải dùng overload nhận factory: `AddSingleton<IClock>(sp => ...)`, không thể chỉ viết `AddSingleton<IClock, SystemClock>()` nếu `SystemClock` cần tham số ngoài những gì DI tự resolve được.

---

## Bài tập

**Bài 1 (giàn giáo).** Đoạn dưới đăng ký sai lifetime khiến `builder.Build()` ném lỗi. Hãy tìm dòng sai và sửa theo MỘT trong hai cách đã học ở mục 4.2.

```csharp title="Program.cs (có lỗi — cần sửa)"
// test:skip khung bài tập, cố ý còn lỗi thiết kế để người học sửa
var builder = WebApplication.CreateBuilder(args);

builder.Services.AddScoped<ShoppingCart>();
builder.Services.AddSingleton<CheckoutService>(); // CheckoutService(ShoppingCart cart)

var app = builder.Build();
app.MapPost("/checkout", (CheckoutService svc) => Results.Ok(svc.Total()));
app.Run();

public class ShoppingCart
{
    public decimal Total { get; set; } = 100_000m;
}

public class CheckoutService(ShoppingCart cart)
{
    public decimal Total() => cart.Total;
}
```

??? success "Lời giải"
    Cách đơn giản nhất: `CheckoutService` xử lý một giỏ hàng theo từng request/người dùng, nên bản chất nó **cũng phải Scoped**, không có lý do gì để là Singleton:

    ```csharp title="Program.cs"
    // test:compile
    var builder = WebApplication.CreateBuilder(args);

    builder.Services.AddScoped<ShoppingCart>();
    builder.Services.AddScoped<CheckoutService>(); // Singleton -> Scoped: hết captive

    var app = builder.Build();
    app.MapPost("/checkout", (CheckoutService svc) => Results.Ok(svc.Total()));
    app.Run();

    public class ShoppingCart
    {
        public decimal Total { get; set; } = 100_000m;
    }

    public class CheckoutService(ShoppingCart cart)
    {
        public decimal Total() => cart.Total;
    }
    ```

    **Vì sao đúng:** `ShoppingCart` mang dữ liệu riêng của từng request (từng người dùng), nên nó phải Scoped. `CheckoutService` sử dụng trực tiếp `ShoppingCart` qua constructor nên lifetime của nó bị giới hạn theo `ShoppingCart` — hạ xuống Scoped loại bỏ hoàn toàn captive dependency mà không cần `IServiceScopeFactory` phức tạp, vì bản thân `CheckoutService` không có lý do nghiệp vụ nào để sống lâu hơn một request.

**Bài 2 (thiết kế).** Thiết kế một hệ thống ghi nhận lượt truy cập (`VisitCounter`) đáp ứng đủ 3 yêu cầu:
1. `VisitCounter` phải là Singleton (đếm tổng số lượt truy cập từ lúc app khởi động, dùng chung cho mọi request).
2. `VisitCounter` cần ghi log chi tiết mỗi lượt truy cập vào một `RequestLog` (Scoped, chứa `RequestId` riêng của từng request).
3. Không được có captive dependency.

Viết đăng ký DI + class `VisitCounter` + class `RequestLog` thoả cả 3 yêu cầu.

??? success "Lời giải"
    ```csharp title="Program.cs"
    // test:compile
    var builder = WebApplication.CreateBuilder(args);

    builder.Services.AddScoped<RequestLog>();
    builder.Services.AddSingleton<VisitCounter>();

    var app = builder.Build();

    app.MapGet("/visit", (VisitCounter counter) =>
    {
        counter.RecordVisit();
        return Results.Ok(new { Total = counter.Total });
    });

    app.Run();

    public class RequestLog
    {
        public Guid RequestId { get; } = Guid.NewGuid();
    }

    // Singleton -> KHÔNG được nhận RequestLog (Scoped) qua constructor.
    // Thay vào đó nhận IServiceScopeFactory để tự mở scope khi cần ghi log.
    public class VisitCounter(IServiceScopeFactory scopeFactory)
    {
        private int _total = 0;
        public int Total => _total;

        public void RecordVisit()
        {
            Interlocked.Increment(ref _total); // Singleton bị gọi đa luồng -> cần an toàn đa luồng

            using var scope = scopeFactory.CreateScope();
            var log = scope.ServiceProvider.GetRequiredService<RequestLog>();
            Console.WriteLine($"[{log.RequestId}] Luot truy cap thu {_total}");
        }
    }
    ```

    **Vì sao đúng:** `VisitCounter` giữ đúng vai trò Singleton (đếm tổng, `_total` sống suốt app) và dùng `Interlocked.Increment` vì Singleton bị nhiều request đồng thời gọi vào. Nó không tiêm `RequestLog` trực tiếp (tránh captive dependency) mà tiêm `IServiceScopeFactory` — an toàn ở mọi lifetime — rồi tự mở scope ngắn hạn mỗi lần cần một `RequestLog` đúng của request hiện tại.

---

## Tự kiểm tra

1. `AddScoped<T>()` tạo bao nhiêu instance khi CÙNG một request gọi `GetRequiredService<T>()` ba lần?

    ??? note "Đáp án"
        Đúng **1** instance — Scoped tái dùng cùng một instance trong suốt một scope (mặc định là một request HTTP), bất kể được yêu cầu bao nhiêu lần bên trong scope đó.

2. Vì sao một class tự `new` dependency của nó bên trong constructor (như `ReportService` ở mục 1.1) lại khó unit test?

    ??? note "Đáp án"
        Vì không có cách nào từ bên ngoài thay thế dependency đó bằng một bản giả/mock — class luôn dùng đúng implementation cụ thể bị `new` cứng bên trong, nên test luôn phải chạy với implementation thật (ví dụ luôn cố gửi email thật).

3. Captive dependency là gì, và ASP.NET Core mặc định phản ứng thế nào khi phát hiện nó lúc khởi động?

    ??? note "Đáp án"
        Captive dependency là khi một service sống lâu hơn (thường Singleton) giữ tham chiếu trực tiếp tới một service sống ngắn hơn (thường Scoped) qua constructor injection. Mặc định (Development, `ValidateScopes = true`), `builder.Build()` sẽ ném `InvalidOperationException` ngay khi khởi động thay vì để lỗi âm thầm xảy ra lúc runtime.

4. Cách đúng để một Singleton cần dùng một service Scoped mà không tạo captive dependency là gì?

    ??? note "Đáp án"
        Không tiêm Scoped trực tiếp qua constructor. Thay vào đó, tiêm `IServiceScopeFactory` vào Singleton, rồi mỗi khi cần dùng thì tự `CreateScope()`, lấy service Scoped bằng `GetRequiredService` từ `scope.ServiceProvider`, dùng xong `Dispose` scope đó.

5. Vì sao constructor injection được ưu tiên hơn Service Locator (tự gọi `IServiceProvider.GetService<T>()` bên trong logic nghiệp vụ)?

    ??? note "Đáp án"
        Constructor injection khai báo dependency một cách tường minh trong chữ ký constructor — chỉ cần đọc chữ ký là biết class cần gì. Service Locator giấu dependency thật sự bên trong thân hàm, khiến lỗi "quên đăng ký" chỉ lộ ra sâu bên trong lúc runtime thay vì rõ ràng ngay ở chữ ký, và khó đọc/khó test hơn.

6. Nếu bạn resolve một type chưa được đăng ký trong `IServiceCollection` từ một Minimal API handler, điều gì xảy ra khi có request gọi tới, và lỗi đó xuất hiện ở giai đoạn nào (biên dịch hay runtime)?

    ??? note "Đáp án"
        Request đó trả về **500 Internal Server Error**, với ngoại lệ `InvalidOperationException: Unable to resolve service for type ...`. Đây là lỗi **runtime**, chỉ xảy ra khi có request thật gọi tới handler cần service đó — code vẫn biên dịch bình thường.

7. Vì sao `Interlocked.Increment` (hoặc cơ chế khoá tương đương) thường cần thiết khi một Singleton có trạng thái mutable như `VisitCounter._total`, nhưng thường không cần thiết với trạng thái tương tự trong một service Scoped?

    ??? note "Đáp án"
        Vì Singleton chỉ có **một instance duy nhất dùng chung cho mọi request đồng thời** — nhiều luồng có thể cùng đọc/ghi `_total` cùng lúc, gây race condition nếu không đồng bộ hoá. Một service Scoped có instance **riêng cho mỗi request**, nên (trừ khi chính request đó xử lý đa luồng nội bộ) không bị nhiều request khác chia sẻ cùng instance, nên rủi ro race condition giữa các request là không có.

---

??? abstract "DEEP DIVE: keyed services, đăng ký bằng factory, và validate DI trong test"
    **Keyed services** (giới thiệu từ .NET 8, vẫn dùng tốt trên .NET 10) cho phép đăng ký nhiều implementation của cùng một interface, phân biệt bằng một "khoá":

    ```csharp title="Program.cs"
    // test:compile
    var builder = WebApplication.CreateBuilder(args);

    builder.Services.AddKeyedScoped<IPaymentGateway, StripeGateway>("stripe");
    builder.Services.AddKeyedScoped<IPaymentGateway, PaypalGateway>("paypal");

    var app = builder.Build();

    app.MapPost("/pay", ([FromKeyedServices("stripe")] IPaymentGateway gateway) =>
        Results.Ok(gateway.Charge(100_000m)));

    app.Run();

    public interface IPaymentGateway
    {
        string Charge(decimal amount);
    }

    public class StripeGateway : IPaymentGateway
    {
        public string Charge(decimal amount) => $"Stripe: da tru {amount}";
    }

    public class PaypalGateway : IPaymentGateway
    {
        public string Charge(decimal amount) => $"Paypal: da tru {amount}";
    }
    ```

    **Đăng ký bằng factory** khi việc tạo object cần logic có điều kiện (đọc cấu hình, chọn nhánh) thay vì chỉ ánh xạ interface → class:

    ```csharp title="Program.cs"
    // test:compile
    var builder = WebApplication.CreateBuilder(args);

    builder.Services.AddSingleton<IClock>(sp =>
    {
        var config = sp.GetRequiredService<IConfiguration>();
        return config["UseFixedClock"] == "true"
            ? new FixedClock(DateTime.UnixEpoch)
            : new SystemClock();
    });

    var app = builder.Build();
    app.MapGet("/now", (IClock clock) => Results.Ok(clock.Now));
    app.Run();

    public interface IClock
    {
        DateTime Now { get; }
    }

    public class SystemClock : IClock
    {
        public DateTime Now => DateTime.UtcNow;
    }

    public class FixedClock(DateTime fixedValue) : IClock
    {
        public DateTime Now => fixedValue;
    }
    ```

    **Background service và captive dependency ngoài request:** `IHostedService`/`BackgroundService` được host quản lý gần như Singleton (một instance sống suốt vòng đời app). Khi nó cần dùng một service Scoped (ví dụ `DbContext` để dọn dữ liệu định kỳ), nó bắt buộc phải tự mở scope y hệt kỹ thuật ở mục 4.2 — đây là nơi captive dependency xuất hiện nhiều nhất trong thực tế, nhiều hơn cả ví dụ Minimal API vì lỗi này không luôn bị `ValidateScopes` bắt ngay lúc khởi động nếu hosted service resolve service bên trong `ExecuteAsync` thay vì constructor.

    **Kiểm chứng cấu hình DI trong test tích hợp:** có thể build thử một `ServiceProvider` độc lập với cả `ValidateScopes = true` và `ValidateOnBuild = true` để bắt lỗi lifetime ngay trong pipeline test, trước khi triển khai:

    ```csharp title="C#"
    // test:compile dùng trực tiếp Microsoft.Extensions.DependencyInjection (sẵn có trong Web SDK)
    var services = new ServiceCollection();
    services.AddScoped<RequestState>();
    services.AddSingleton<AuditLogger>(); // vẫn cố tình sai để minh hoạ

    try
    {
        using var provider = services.BuildServiceProvider(
            new ServiceProviderOptions { ValidateScopes = true, ValidateOnBuild = true });
        Console.WriteLine("Build thanh cong (khong nen xay ra voi cau hinh nay)");
    }
    catch (AggregateException)
    {
        Console.WriteLine("Bat duoc captive dependency ngay trong test, truoc khi deploy");
    }

    public class RequestState
    {
        public Guid RequestId { get; } = Guid.NewGuid();
    }

    public class AuditLogger(RequestState state)
    {
        public void Log(string message) => Console.WriteLine($"[{state.RequestId}] {message}");
    }
    ```

    ```text title="Kết quả"
    Bat duoc captive dependency ngay trong test, truoc khi deploy
    ```

Tiếp theo -> ef core và dbcontext
