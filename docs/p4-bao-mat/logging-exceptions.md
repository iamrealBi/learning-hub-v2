---
tier: core
status: core
owner: core-team
verified_on: "2026-07-05"
dotnet_version: "10.0"
bloom: áp dụng
requires: [p3-error-handling]
est_minutes_fast: 32
---

# Structured Logging với ILogger

!!! info "Bạn đang ở đây"
    cần trước: bạn đã biết xử lý lỗi toàn cục (UseExceptionHandler/IExceptionHandler/ProblemDetails) — chương này không dạy lại phần đó.
    mở khoá: ghi log có cấu trúc để một hệ thống log tập trung (Seq, Elasticsearch, Loki...) có thể *tìm kiếm và lọc* được, chọn đúng log level cho từng tình huống, gắn context xuyên suốt nhiều dòng log bằng scope, và biết khi nào cần chuyển sang Serilog.

> Mục tiêu (đo được): sau chương này bạn **áp dụng** được `ILogger<T>` để ghi log có cấu trúc (không nội suy chuỗi), **phân biệt** được 6 log level theo đúng thứ tự nghiêm trọng và chọn đúng level cho từng tình huống, **giải thích** được `LoggerMessage` source generator giúp gì cho hiệu năng, **triển khai** được log scope để gắn correlation id xuyên suốt một request, và **cấu hình** được log level qua `appsettings.json`.

---

## 0. Đoán nhanh trước khi học

Bạn có hai dòng log ghi lại cùng một sự kiện: một user đăng nhập.

```text title="Hai kiểu viết log"
A) logger.LogInformation($"User {userId} logged in");
B) logger.LogInformation("User {UserId} logged in", userId);
```

Cả hai đều in ra **màn hình console** đúng một dòng giống nhau, ví dụ `User 42 logged in`. Vậy khác biệt nằm ở đâu, và tại sao nhiều công ty coi cách A là lỗi cần sửa trong code review?

??? note "Đáp án"
    Khác biệt không nằm ở console — nằm ở **những gì được lưu lại phía sau**. Cách B giữ nguyên chuỗi mẫu cố định `"User {UserId} logged in"` cộng với một trường riêng `UserId = 42`. Cách A đã "nướng chín" giá trị `42` vào ngay trong chuỗi — với hệ thống log tập trung, mỗi user khác nhau tạo ra một chuỗi văng vẳng khác nhau, không thể lọc "cho tôi mọi dòng log có `UserId = 42`". Toàn bộ chương này giải thích chi tiết vì sao và cách làm đúng.

---

## 1. `ILogger<T>` là gì, và cách inject vào service

**Định nghĩa (một câu):** `ILogger<T>` là một interface có sẵn của .NET {{ dotnet.current }} dùng để **ghi lại** những gì đang xảy ra trong chương trình khi nó chạy thật — tham số kiểu `T` không dùng để làm gì cả ngoài việc đặt tên cho "nguồn" của dòng log đó (gọi là **category**), thường chính là tên class đang log.

Bạn không tự tạo `ILogger<T>` bằng `new` — nó được **Dependency Injection (DI)** của ASP.NET Core tự cấp cho bạn khi bạn khai báo nó là một tham số constructor. Ví dụ tối thiểu, độc lập, chỉ minh hoạ đúng việc inject và gọi log — không có gì khác:

```csharp title="Program.cs"
// test:compile ILogger<T> toi thieu: inject vao mot service qua DI
var builder = WebApplication.CreateBuilder(args);

// Đăng ký service vào DI như bình thường — không cần đăng ký gì thêm cho ILogger,
// framework tự cấp sẵn (built-in logging provider Console đã có mặc định).
builder.Services.AddSingleton<GreetingService>();

var app = builder.Build();

app.MapGet("/hello/{name}", (string name, GreetingService svc) => svc.Greet(name));

app.Run();

sealed class GreetingService(ILogger<GreetingService> logger)
{
    public string Greet(string name)
    {
        // "GreetingService" — category — sẽ xuất hiện trước mỗi dòng log này,
        // cho bạn biết NGAY dòng log này phát ra từ class nào.
        logger.LogInformation("Chào {Name}", name);
        return $"Xin chào, {name}!";
    }
}
```

Gọi `GET /hello/An` sẽ in ra console một dòng tương tự:

```text title="Console output"
info: GreetingService[0]
      Chào An
```

Phần `GreetingService[0]` chính là category (`T` = `GreetingService`) và một `EventId` mặc định (`0`). Nhờ category, khi bạn có 50 class cùng ghi log, bạn luôn biết dòng nào phát ra từ đâu mà không cần đọc nội dung message.

**Nếu dùng sai — hậu quả cụ thể:** nếu bạn viết `new Logger<GreetingService>(...)` thủ công thay vì để DI cấp, bạn phải tự tay nối nó với đúng `ILoggerFactory` và mọi provider (Console, file, Seq...) đã cấu hình ở `Program.cs` — nếu nối sai hoặc thiếu, log của bạn "biến mất" không rõ lý do, trong khi log của các class khác (được DI cấp đúng) vẫn hiện bình thường. Đây là lỗi khó tìm vì code vẫn biên dịch và chạy được, chỉ thiếu output.

---

## 2. Sáu log level, theo đúng thứ tự nghiêm trọng

**Định nghĩa (một câu):** Log level là một **con số mức độ quan trọng** gắn với mỗi dòng log, dùng để bạn **lọc** — ví dụ ở production chỉ muốn xem log từ `Information` trở lên, bỏ qua các dòng `Debug`/`Trace` quá chi tiết.

.NET định nghĩa đúng 6 mức, theo thứ tự nghiêm trọng **tăng dần**:

```text title="Thứ tự nghiêm trọng (thấp -> cao)"
Trace < Debug < Information < Warning < Error < Critical
```

Mỗi mức có một tình huống dùng riêng biệt:

- **`Trace`** — chi tiết vụn vặt nhất, thường chỉ bật khi đang soi một bug cụ thể. Ví dụ: `logger.LogTrace("Vào hàm TinhGia với input={Input}", input);` — ghi lại từng bước tính toán nội bộ.
- **`Debug`** — thông tin hữu ích khi phát triển/debug, nhưng quá nhiều để giữ lại ở production. Ví dụ: `logger.LogDebug("Cache miss cho key {Key}, sẽ query DB", key);`.
- **`Information`** — các sự kiện **bình thường**, đáng để ghi lại như một mốc trong luồng nghiệp vụ. Ví dụ: `logger.LogInformation("Đơn hàng {OrderId} đã được tạo", orderId);`.
- **`Warning`** — có gì đó **bất thường nhưng chưa gây lỗi**, hệ thống vẫn tiếp tục chạy được. Ví dụ: `logger.LogWarning("API bên thứ ba trả chậm ({Ms}ms), đã dùng cache thay thế", elapsedMs);`.
- **`Error`** — một **hành động cụ thể thất bại** (một request, một job), nhưng ứng dụng vẫn sống, có thể tiếp tục xử lý các việc khác. Ví dụ: `logger.LogError(ex, "Gửi email xác nhận cho đơn {OrderId} thất bại", orderId);`.
- **`Critical`** — sự cố nghiêm trọng khiến **toàn bộ ứng dụng hoặc một phần lớn** không hoạt động được nữa, cần người vận hành can thiệp ngay. Ví dụ: `logger.LogCritical(ex, "Không kết nối được tới database khi khởi động, ứng dụng sẽ dừng");`.

Ví dụ tối thiểu, tự chứa (chạy bằng BCL thuần, không cần web) minh hoạ việc gọi đúng phương thức tương ứng với mỗi level và cách chọn level theo tình huống:

```csharp title="C#"
// test:compile minh hoa 6 log level qua ILoggerFactory don gian, khong can ASP.NET Core
using Microsoft.Extensions.Logging;

using var factory = LoggerFactory.Create(builder =>
{
    builder.AddConsole();
    builder.SetMinimumLevel(LogLevel.Trace); // cho phép in cả Trace ở demo này
});

var logger = factory.CreateLogger("DemoLogLevel");

logger.LogTrace("Bắt đầu tính giá cho sản phẩm {Sku}", "SKU-01");
logger.LogDebug("Đã lấy giá gốc từ cache: {GiaGoc}", 100000);
logger.LogInformation("Đơn hàng {OrderId} đã được tạo thành công", 42);
logger.LogWarning("Kho chỉ còn {SoLuong} sản phẩm, dưới ngưỡng cảnh báo", 3);
logger.LogError("Không thể trừ kho cho đơn {OrderId}: hết hàng", 42);
logger.LogCritical("Mất kết nối database, dừng nhận đơn hàng mới");
```

Output (mỗi dòng có tiền tố mức độ, viết hoa):

```text title="Console output"
trce: DemoLogLevel[0]
      Bắt đầu tính giá cho sản phẩm SKU-01
dbug: DemoLogLevel[0]
      Đã lấy giá gốc từ cache: 100000
info: DemoLogLevel[0]
      Đơn hàng 42 đã được tạo thành công
warn: DemoLogLevel[0]
      Kho chỉ còn 3 sản phẩm, dưới ngưỡng cảnh báo
fail: DemoLogLevel[0]
      Không thể trừ kho cho đơn 42: hết hàng
crit: DemoLogLevel[0]
      Mất kết nối database, dừng nhận đơn hàng mới
```

**Nếu dùng sai — hậu quả cụ thể:** nếu bạn ghi **mọi thứ** bằng `LogInformation` (kể cả lỗi thật sự), khi có sự cố production, đội vận hành lọc theo `Error`/`Critical` để tìm vấn đề sẽ **không tìm thấy gì** — dòng log lỗi bị "chìm" chung với hàng nghìn dòng thông tin bình thường cùng level. Ngược lại, nếu bạn ghi **mọi thứ** bằng `LogTrace`/`LogDebug` ở production mà quên nâng minimum level, hệ thống log tập trung sẽ **tràn dung lượng lưu trữ** vì lượng dòng log tăng gấp hàng chục-hàng trăm lần so với mức cần thiết, có thể gây tốn phí lưu trữ hoặc mất log quan trọng khi hệ thống tự động xoá log cũ để giải phóng chỗ.

---

## 3. Structured logging: message template khác gì string interpolation

**Định nghĩa (một câu):** Structured logging nghĩa là bạn ghi log bằng một **message template cố định** (chuỗi có các chỗ trống đặt tên `{TenTruong}`) cộng với các **giá trị tham số truyền riêng** — thay vì tự nối/nội suy giá trị thẳng vào chuỗi — để hệ thống log lưu lại cả template và từng trường dữ liệu dưới dạng có thể truy vấn.

So sánh trực tiếp hai cách viết cho cùng một sự kiện:

```csharp title="C#"
// test:compile so sanh truc tiep: string interpolation (SAI) vs structured logging (DUNG)
using Microsoft.Extensions.Logging;

using var factory = LoggerFactory.Create(builder => builder.AddConsole());
var logger = factory.CreateLogger("SoSanh");

int userId = 42;
int orderId = 1001;

// SAI: nội suy chuỗi ($"") — giá trị bị "nướng chín" vào chuỗi ngay lập tức.
logger.LogInformation($"User {userId} đặt đơn {orderId}");

// ĐÚNG: message template + tham số có tên riêng biệt.
logger.LogInformation("User {UserId} đặt đơn {OrderId}", userId, orderId);
```

Cả hai in ra console **giống nhau về mặt hiển thị**:

```text title="Console output (hiển thị giống nhau)"
info: SoSanh[0]
      User 42 đặt đơn 1001
info: SoSanh[0]
      User 42 đặt đơn 1001
```

Nhưng phía sau, provider log (Console formatter mặc định chỉ hiện text, nhưng Seq/Elasticsearch/Application Insights... lưu ở dạng có cấu trúc) nhận được hai thứ hoàn toàn khác nhau:

| Cách viết | Template lưu lại | Trường dữ liệu lưu lại |
|---|---|---|
| `$"User {userId} đặt đơn {orderId}"` | `"User 42 đặt đơn 1001"` (đã là chuỗi cuối, không còn template) | Không có — giá trị đã hoà vào chuỗi, không tách được nữa |
| `"User {UserId} đặt đơn {OrderId}", userId, orderId` | `"User {UserId} đặt đơn {OrderId}"` (giữ nguyên) | `UserId = 42`, `OrderId = 1001` (hai trường độc lập, có tên) |

**Vì sao mất khả năng query cụ thể:** với hệ thống log tập trung, câu hỏi vận hành thường gặp là "cho tôi mọi lỗi liên quan tới `UserId = 42` trong 7 ngày qua" hoặc "đếm số đơn hàng có `OrderId` xuất hiện trong log Error". Với cách B, đây là một truy vấn field đơn giản (`UserId:42` hoặc `where UserId = 42`) vì trường `UserId` được lưu tách biệt, có kiểu dữ liệu riêng. Với cách A, hệ thống chỉ còn lại chuỗi phẳng `"User 42 đặt đơn 1001"` — để tìm theo `userId = 42`, bạn phải làm full-text search trên chuỗi (chậm hơn, dễ trúng nhầm ví dụ chuỗi `"User 421..."` chứa `"42"`), và **không thể** gộp/thống kê theo trường vì hệ thống không biết `42` ở vị trí đó là `UserId` hay là bất kỳ số nào khác trong câu.

**Nếu dùng sai — hậu quả cụ thể:** một hệ thống ghi hàng triệu dòng log bằng `$"..."` mỗi ngày; khi cần điều tra "user nào gây ra lỗi X nhiều nhất", đội vận hành không có cách nào lọc theo `UserId` một cách chính xác — phải viết regex phức tạp trên full-text, chạy chậm trên tập dữ liệu lớn, và vẫn có rủi ro khớp nhầm giá trị. Cùng câu hỏi đó với structured logging là một dòng truy vấn field, chạy tức thời.

---

## 4. `LoggerMessage` source generator: log hiệu năng cao

**Định nghĩa (một câu):** `LoggerMessage` là một cơ chế **source generator** (sinh code tại thời điểm compile, không phải runtime) cho phép bạn khai báo một phương thức log qua attribute `[LoggerMessage]`, và compiler tự sinh ra code ghi log được **tối ưu hiệu năng** — tránh chi phí boxing tham số và kiểm tra level lặp lại mà cách gọi `logger.LogInformation(...)` thông thường phải trả.

Cách gọi `LogInformation(...)` thông thường vẫn hoạt động đúng, nhưng với ứng dụng ghi log ở tần suất **rất cao** (hàng chục nghìn dòng/giây), chi phí nhỏ mỗi lần gọi (boxing các tham số kiểu value type thành `object[]`) cộng dồn lại đáng kể. `LoggerMessage` sinh sẵn code không cần boxing, kiểm tra level trước khi làm bất cứ việc gì khác.

Ví dụ tối thiểu, độc lập:

```csharp title="C#"
// test:compile LoggerMessage source generator toi thieu, tu chua bang BCL
using Microsoft.Extensions.Logging;

using var factory = LoggerFactory.Create(builder => builder.AddConsole());
var logger = factory.CreateLogger<DonHangService>();

var service = new DonHangService(logger);
service.TaoDon(orderId: 42, userId: 7);

public sealed partial class DonHangService(ILogger<DonHangService> logger)
{
    public void TaoDon(int orderId, int userId)
    {
        LogDonHangDaTao(orderId, userId);
    }

    // Attribute [LoggerMessage] khiến compiler SINH RA phần cài đặt của phương thức
    // partial này — bạn chỉ viết chữ ký, không viết thân hàm.
    [LoggerMessage(Level = LogLevel.Information, Message = "Đơn hàng {OrderId} đã được tạo bởi user {UserId}")]
    private partial void LogDonHangDaTao(int orderId, int userId);
}
```

Output:

```text title="Console output"
info: DonHangService[0]
      Đơn hàng 42 đã được tạo bởi user 7
```

Giải thích: bạn khai báo class là `partial`, viết một phương thức `partial void` (không thân) đánh dấu `[LoggerMessage(...)]`. Tại thời điểm compile, source generator đọc attribute và **tự viết phần thân** của phương thức đó (bạn có thể xem code sinh ra trong thư mục `obj/`) — phần thân đó gọi `ILogger` theo cách tối ưu, kiểm tra `IsEnabled(LogLevel.Information)` trước khi làm bất kỳ việc gì khác, tránh lãng phí khi level đó đang bị tắt.

**Nếu dùng sai — hậu quả cụ thể:** nếu bạn quên từ khoá `partial` trên class hoặc trên phương thức, code sẽ **không biên dịch được** — lỗi CS0751 (`A partial method must be declared within a partial type`) hoặc lỗi tương tự về thiếu phần cài đặt, vì source generator không tìm được nơi để "gắn" code nó sinh ra. Đây không phải lỗi runtime âm thầm — bạn phát hiện ngay lúc build.

Với hầu hết ứng dụng ở mức bình thường (không phải hệ thống log hàng chục nghìn dòng/giây), gọi trực tiếp `logger.LogInformation(...)` là đủ và dễ đọc hơn. `LoggerMessage` là công cụ dành riêng cho đường dẫn nóng (hot path) cần tối ưu.

---

## 5. Log scope (`BeginScope`): gắn context xuyên suốt nhiều dòng log

**Định nghĩa (một câu):** Log scope là một **vùng gắn thêm dữ liệu context** vào mọi dòng log được ghi bên trong nó — bạn mở scope bằng `logger.BeginScope(...)`, và từ lúc đó tới khi scope bị `Dispose()`, mọi dòng log (dù ghi từ bất kỳ đâu trong cùng luồng xử lý) đều tự động mang theo dữ liệu đó.

Tình huống điển hình: bạn muốn mọi dòng log của **cùng một request HTTP** đều mang theo một `CorrelationId` — để khi tra log, bạn lọc theo đúng `CorrelationId` đó và thấy **toàn bộ** các dòng log liên quan tới request đó, dù chúng được ghi ở nhiều class khác nhau (controller, service, repository).

Ví dụ tối thiểu, độc lập, minh hoạ đúng khái niệm scope (không cần HTTP thật):

```csharp title="C#"
// test:compile BeginScope toi thieu: gan CorrelationId cho nhieu dong log trong 1 "request" gia lap
using Microsoft.Extensions.Logging;

using var factory = LoggerFactory.Create(builder =>
{
    builder.AddSimpleConsole(options => options.IncludeScopes = true); // BẮT BUỘC để scope hiện ra console
});

var logger = factory.CreateLogger("XuLyDonHang");

string correlationId = Guid.NewGuid().ToString("N")[..8];

// Mọi dòng log ghi TRONG khối using này đều tự động mang theo CorrelationId.
using (logger.BeginScope("CorrelationId:{CorrelationId}", correlationId))
{
    logger.LogInformation("Bắt đầu xử lý đơn hàng");
    logger.LogInformation("Kiểm tra kho: còn hàng");
    logger.LogInformation("Đơn hàng đã hoàn tất");
}

// Ngoài khối using — scope đã Dispose, KHÔNG còn CorrelationId đi kèm.
logger.LogInformation("Log này không thuộc request nào cụ thể");
```

Output (chú ý phần `=> CorrelationId:...` chỉ xuất hiện ở 3 dòng đầu):

```text title="Console output"
info: XuLyDonHang[0]
      => CorrelationId:a1b2c3d4
      Bắt đầu xử lý đơn hàng
info: XuLyDonHang[0]
      => CorrelationId:a1b2c3d4
      Kiểm tra kho: còn hàng
info: XuLyDonHang[0]
      => CorrelationId:a1b2c3d4
      Đơn hàng đã hoàn tất
info: XuLyDonHang[0]
      Log này không thuộc request nào cụ thể
```

Trong một API thật, cách dùng phổ biến nhất là mở scope ngay từ một middleware ở đầu pipeline, lấy `CorrelationId` từ header (hoặc tự sinh nếu client không gửi), rồi mọi log của toàn bộ request — kể cả log phát ra từ các service phía sau — tự động mang theo nó, không cần truyền tay `correlationId` qua từng tham số phương thức. Ví dụ một middleware thật gắn scope cho toàn bộ request:

```csharp title="Program.cs"
// test:compile middleware gan CorrelationId qua BeginScope cho toan bo 1 request thuc
var builder = WebApplication.CreateBuilder(args);
builder.Logging.AddSimpleConsole(options => options.IncludeScopes = true);

builder.Services.AddSingleton<DonHangService>();

var app = builder.Build();

// Middleware này chạy ĐẦU TIÊN cho mọi request — mở một scope bao trọn
// toàn bộ phần còn lại của pipeline (await next()).
app.Use(async (context, next) =>
{
    var logger = context.RequestServices
        .GetRequiredService<ILoggerFactory>()
        .CreateLogger("CorrelationMiddleware");

    // Lấy CorrelationId từ header client gửi lên, hoặc tự sinh nếu không có.
    var correlationId = context.Request.Headers.TryGetValue("X-Correlation-Id", out var v)
        ? v.ToString()
        : Guid.NewGuid().ToString("N")[..8];

    using (logger.BeginScope("CorrelationId:{CorrelationId}", correlationId))
    {
        // Toàn bộ code chạy TRONG await next() — bao gồm mọi middleware,
        // endpoint, và service phía sau — đều nằm trong scope này.
        await next();
    }
});

app.MapPost("/don-hang", (DonHangService svc) => svc.TaoDon(orderId: 42));

app.Run();

sealed class DonHangService(ILogger<DonHangService> logger)
{
    public IResult TaoDon(int orderId)
    {
        // Dòng log này KHÔNG hề biết gì về CorrelationId — nhưng vì nó chạy
        // bên trong scope mở ở middleware, CorrelationId vẫn tự động đi kèm.
        logger.LogInformation("Đơn hàng {OrderId} đã được tạo", orderId);
        return Results.Ok();
    }
}
```

Điểm quan trọng: `DonHangService` không nhận `correlationId` qua tham số nào cả — nó chỉ log bình thường bằng `ILogger<DonHangService>` như mọi nơi khác. Scope mở ở middleware "xuyên" qua toàn bộ lời gọi bên trong `await next()`, nên log của `DonHangService` vẫn tự động mang `CorrelationId` của đúng request đang xử lý nó.

**Nếu dùng sai — hậu quả cụ thể:** nếu bạn gọi `logger.BeginScope(...)` nhưng **không** đặt trong khối `using` (không gọi `Dispose()`), scope sẽ không kết thúc đúng lúc — dữ liệu context có thể "dính" theo vào các dòng log không liên quan được ghi sau đó, gây nhiễu, sai lệch thông tin khi tra log (một dòng log của request B lại hiện `CorrelationId` của request A). Một lỗi khác thường gặp: nếu provider console/formatter không cấu hình `IncludeScopes = true` (hoặc provider không hỗ trợ hiển thị scope), toàn bộ dữ liệu bạn gắn vào `BeginScope` sẽ **không hiện ra ở đâu cả** — code chạy không lỗi, chỉ là thông tin scope "biến mất" một cách âm thầm.

---

## 6. Cấu hình log level qua `appsettings.json`

**Định nghĩa (một câu):** Mục `Logging:LogLevel` trong `appsettings.json` là nơi bạn khai báo **mức log tối thiểu** cho từng category (hoặc mặc định cho toàn hệ thống) mà **không cần sửa code** — cùng một binary có thể chạy với mức log khác nhau ở Development và Production chỉ bằng cách đổi file cấu hình tương ứng.

```json title="appsettings.json"
{
  "Logging": {
    "LogLevel": {
      "Default": "Information",
      "Microsoft.AspNetCore": "Warning",
      "MyApp.Services.DonHangService": "Debug"
    }
  }
}
```

Ý nghĩa từng dòng:

- **`"Default": "Information"`** — mọi category không được liệt kê riêng sẽ dùng mức tối thiểu `Information` (bỏ qua `Trace`/`Debug`).
- **`"Microsoft.AspNetCore": "Warning"`** — mọi log có category bắt đầu bằng `Microsoft.AspNetCore` (ví dụ log routing, log middleware nội bộ của framework) chỉ hiện từ `Warning` trở lên — cắt bớt lượng log nội bộ rất nhiều của framework mà bạn thường không cần xem hàng ngày.
- **`"MyApp.Services.DonHangService": "Debug"`** — ghi đè riêng cho đúng một class: khi bạn đang điều tra một bug cụ thể trong `DonHangService`, bạn tạm hạ mức xuống `Debug` chỉ cho class đó, không ảnh hưởng phần còn lại của hệ thống.

Cấu hình theo môi trường thường tách riêng file: `appsettings.Development.json` có thể đặt `"Default": "Debug"` (xem nhiều hơn khi code trên máy dev), còn `appsettings.Production.json` giữ `"Default": "Information"` hoặc cao hơn (giảm nhiễu và chi phí lưu trữ ở production). ASP.NET Core tự động chọn đúng file theo biến môi trường `ASPNETCORE_ENVIRONMENT`.

**Nếu dùng sai — hậu quả cụ thể:** nếu bạn để `"Default": "Trace"` ở file `appsettings.Production.json` (ví dụ do copy nhầm từ file Development rồi quên đổi lại), hệ thống production sẽ ghi log ở mức chi tiết nhất cho **mọi** request thật — lượng log tăng vọt, có thể làm đầy disk hoặc vượt hạn mức (quota) của dịch vụ log tập trung, kéo theo mất log ở đúng lúc cần nó nhất (khi hệ thống bị quá tải), hoặc tốn chi phí lưu trữ vượt dự tính mà không mang lại giá trị tương xứng.

---

## 7. Serilog: một lựa chọn thay thế phổ biến hơn

**Định nghĩa (một câu):** Serilog là một **thư viện logging của bên thứ ba** (không phải built-in của .NET) cho .NET, phổ biến hơn logging mặc định ở nhiều dự án thực tế vì hỗ trợ cấu hình linh hoạt và có hệ sinh thái lớn các **sink** — nơi log được ghi tới.

**Sink** là khái niệm trung tâm của Serilog: một sink là **đích đến** cụ thể mà log chảy tới — ví dụ Console, một file trên đĩa, hoặc một dịch vụ tập trung như Seq, Elasticsearch, Application Insights. Bạn có thể cấu hình **nhiều sink cùng lúc** cho cùng một dòng log (ví dụ vừa ghi Console để xem lúc dev, vừa ghi Seq để tra cứu sau).

Serilog vẫn tương thích với `ILogger<T>` — bạn viết code gọi `logger.LogInformation(...)` giống hệt các mục trước, chỉ khác ở **cách khởi tạo/cấu hình** trong `Program.cs`. Vì Serilog là package ngoài (không có sẵn trong `dotnet new web`), đoạn minh hoạ dưới đây đánh dấu skip:

```csharp title="Program.cs"
// test:skip can package ngoai Serilog.AspNetCore + sink (vi du Serilog.Sinks.Seq), khong co san trong `dotnet new web`
using Serilog;

var builder = WebApplication.CreateBuilder(args);

// Thay thế toàn bộ logging mặc định của ASP.NET Core bằng Serilog.
builder.Host.UseSerilog((context, services, configuration) => configuration
    .MinimumLevel.Information()
    .WriteTo.Console()                                   // sink 1: console
    .WriteTo.Seq("http://localhost:5341")                // sink 2: Seq — hệ thống log tập trung
    .Enrich.WithProperty("Application", "MyApp"));

var app = builder.Build();

app.MapGet("/hello/{name}", (string name, ILogger<Program> logger) =>
{
    // Vẫn dùng ILogger<T> như bình thường — Serilog "đứng sau" xử lý việc ghi.
    logger.LogInformation("Chào {Name}", name);
    return $"Xin chào, {name}!";
});

app.Run();
```

Điểm khác biệt cốt lõi so với logging built-in: logging built-in (`builder.Logging.AddConsole()`...) đủ dùng cho ứng dụng nhỏ hoặc khi chỉ cần xem log ở console/debug output; Serilog mạnh hơn khi bạn cần **nhiều đích ghi log cùng lúc**, cần **enrich** (gắn thêm trường cố định như tên ứng dụng, phiên bản, môi trường vào mọi dòng log), hoặc cần format output theo chuẩn riêng (JSON có cấu trúc để hệ thống log tập trung parse dễ hơn).

**Nếu dùng sai — hậu quả cụ thể:** nếu bạn cấu hình sink Seq với địa chỉ sai hoặc Seq server không chạy, nhưng không cấu hình thêm sink Console dự phòng, ứng dụng của bạn sẽ **mất toàn bộ log** mà không có cảnh báo lỗi biên dịch hay lỗi runtime rõ ràng — Serilog theo mặc định "nuốt" lỗi ghi log nội bộ để tránh làm crash ứng dụng chính, nên bạn chỉ phát hiện ra khi cần tra log và thấy hoàn toàn trống.

---

## Cạm bẫy & thực chiến

- **Dùng string interpolation (`$"..."`) thay vì message template:** nhìn console giống nhau, nhưng phá vỡ khả năng truy vấn theo trường của hệ thống log tập trung — không thể lọc chính xác theo `UserId`, `OrderId`... chỉ còn full-text search kém chính xác.
- **Ghi mọi thứ bằng `LogInformation`, kể cả lỗi thật:** khi cần lọc `Error`/`Critical` lúc có sự cố, dòng log lỗi bị chìm chung với hàng nghìn dòng thông tin bình thường cùng level — mất thời gian điều tra đúng lúc cần nhanh nhất.
- **Để `"Default": "Trace"` hoặc `"Debug"` sót lại ở `appsettings.Production.json`:** log tăng vọt ở production, tốn disk/chi phí lưu trữ, có thể làm log tập trung tự xoá log cũ (kể cả log quan trọng) để giải phóng chỗ.
- **Gọi `BeginScope(...)` mà không đặt trong `using`, hoặc quên cấu hình `IncludeScopes = true`:** dữ liệu context (như correlation id) không được giải phóng đúng lúc, hoặc hoàn toàn không hiện ra ở output — âm thầm mất thông tin cần để nối log giữa các dòng của cùng một request.
- **Log dữ liệu nhạy cảm (mật khẩu, token, số thẻ tín dụng) vào message hoặc tham số:** dù dùng structured logging đúng cách, nếu tham số truyền vào là `password` hay `creditCardNumber`, nó vẫn bị lưu lại nguyên văn trong hệ thống log — hệ thống log tập trung thường có quyền truy cập rộng hơn database chính, biến nó thành một điểm rò rỉ dữ liệu nhạy cảm.
- **Dùng `LoggerMessage` source generator cho code không nằm trên đường dẫn nóng:** tăng độ phức tạp code (phải thêm `partial`, viết attribute) mà không mang lại lợi ích hiệu năng đáng kể — chỉ nên dùng khi đã đo được logging là điểm nghẽn hiệu năng thật sự.

---

## Bài tập

**Bài 1 (giàn giáo):** Đoạn code dưới đây ghi log bằng string interpolation cho một luồng xử lý thanh toán. Hãy sửa lại thành structured logging đúng chuẩn (message template + tham số có tên), sao cho hệ thống log tập trung có thể lọc theo `PaymentId` và `Amount` riêng biệt.

```csharp title="C#"
// test:compile bai tap 1 - co loi string interpolation, can sua
using Microsoft.Extensions.Logging;

using var factory = LoggerFactory.Create(builder => builder.AddConsole());
var logger = factory.CreateLogger("ThanhToan");

int paymentId = 555;
decimal amount = 250000m;

// SAI: cần sửa thành structured logging.
logger.LogInformation($"Thanh toán {paymentId} với số tiền {amount} đã hoàn tất");
```

Gợi ý giàn giáo: message template dùng `{TenTruong}` viết hoa chữ cái đầu, tham số truyền theo **đúng thứ tự** xuất hiện trong template.

??? success "Lời giải + vì sao"
    ```csharp title="C#"
    // test:compile bai tap 1 - da sua thanh structured logging
    using Microsoft.Extensions.Logging;

    using var factory = LoggerFactory.Create(builder => builder.AddConsole());
    var logger = factory.CreateLogger("ThanhToan");

    int paymentId = 555;
    decimal amount = 250000m;

    // ĐÚNG: template cố định + tham số có tên riêng biệt.
    logger.LogInformation("Thanh toán {PaymentId} với số tiền {Amount} đã hoàn tất", paymentId, amount);
    ```

    **Vì sao:** với cách sửa này, hệ thống log tập trung lưu lại template `"Thanh toán {PaymentId} với số tiền {Amount} đã hoàn tất"` cố định, cộng với hai trường riêng `PaymentId = 555` và `Amount = 250000`. Bạn có thể truy vấn chính xác "tổng số tiền đã thanh toán qua các dòng log có `Amount > 100000`" hoặc "mọi log liên quan `PaymentId = 555`" — điều không thể làm được với chuỗi đã nội suy sẵn.

**Bài 2 (thiết kế):** Thiết kế một luồng xử lý đơn hàng gồm 3 bước log (nhận đơn, kiểm tra kho, hoàn tất), tất cả cùng thuộc một "request" giả lập. Yêu cầu: dùng `BeginScope` để gắn một `OrderId` xuyên suốt cả 3 dòng log, chọn đúng log level cho mỗi bước (bước bình thường dùng `Information`, bước phát hiện kho sắp hết dùng `Warning`).

??? success "Lời giải + vì sao"
    ```csharp title="C#"
    // test:compile bai tap 2 - thiet ke day du BeginScope + log level phu hop
    using Microsoft.Extensions.Logging;

    using var factory = LoggerFactory.Create(builder =>
    {
        builder.AddSimpleConsole(options => options.IncludeScopes = true);
    });

    var logger = factory.CreateLogger("XuLyDonHangDayDu");

    void XuLyDonHang(int orderId, int soLuongConLai)
    {
        using (logger.BeginScope("OrderId:{OrderId}", orderId))
        {
            logger.LogInformation("Đã nhận đơn hàng");

            if (soLuongConLai < 5)
            {
                // Bất thường (kho sắp hết) nhưng KHÔNG phải lỗi — vẫn xử lý được đơn.
                logger.LogWarning("Kho chỉ còn {SoLuong} sản phẩm, dưới ngưỡng cảnh báo", soLuongConLai);
            }

            logger.LogInformation("Đơn hàng đã hoàn tất");
        }
    }

    XuLyDonHang(orderId: 101, soLuongConLai: 3);
    ```

    **Vì sao thiết kế này đúng:**

    - Cả 3 dòng log nằm trong cùng một `BeginScope` — khi tra log theo `OrderId = 101`, bạn thấy đúng và đủ 3 dòng liên quan, dù chúng có thể được ghi từ nhiều phương thức/class khác nhau trong một hệ thống thật.
    - Hai bước "nhận đơn" và "hoàn tất" là luồng nghiệp vụ bình thường — đúng bản chất `Information`, không phải cảnh báo hay lỗi.
    - Bước phát hiện kho sắp hết dùng `Warning` — đây là tín hiệu cần chú ý (có thể cần nhập thêm hàng) nhưng **không** làm đơn hàng thất bại, nên không dùng `Error`.

---

## Tự kiểm tra

1. `ILogger<T>` — tham số `T` dùng để làm gì, và bạn có nên tự `new` nó thay vì để DI cấp không?

    ??? note "Đáp án"
        `T` dùng làm **category** — tên nguồn phát ra dòng log, thường là tên class. Không nên tự `new`: để DI cấp đảm bảo logger được nối đúng với mọi provider (Console, file, Seq...) đã cấu hình sẵn ở `Program.cs`; tự tạo thủ công dễ thiếu kết nối, khiến log "biến mất" mà không rõ lý do.

2. Sắp xếp đúng thứ tự nghiêm trọng tăng dần của 6 log level.

    ??? note "Đáp án"
        `Trace < Debug < Information < Warning < Error < Critical`.

3. Vì sao `logger.LogInformation($"User {userId} logged in")` bị coi là sai trong code review, dù console hiển thị đúng nội dung mong muốn?

    ??? note "Đáp án"
        Vì nội suy chuỗi (`$""`) hoà giá trị `userId` vào chuỗi ngay lập tức, hệ thống log tập trung không còn tách được `userId` thành một trường riêng để truy vấn (ví dụ lọc mọi log có `UserId = 42`) — chỉ còn full-text search kém chính xác trên chuỗi phẳng.

4. `LoggerMessage` source generator giải quyết vấn đề gì, và khi nào bạn NÊN cân nhắc dùng nó?

    ??? note "Đáp án"
        Nó sinh code ghi log tại thời điểm compile, tránh chi phí boxing tham số và kiểm tra level lặp lại của cách gọi `LogInformation(...)` thông thường. Nên cân nhắc dùng khi đã đo được logging là điểm nghẽn hiệu năng thật sự (log ở tần suất rất cao) — không nên dùng tràn lan cho code bình thường vì tăng độ phức tạp không cần thiết.

5. `BeginScope` dùng để làm gì, và điều gì xảy ra nếu bạn không đặt nó trong khối `using`?

    ??? note "Đáp án"
        Dùng để gắn context (ví dụ correlation id/order id) vào mọi dòng log ghi bên trong scope đó, giúp nối các dòng log của cùng một request/luồng xử lý. Nếu không đặt trong `using` (không gọi `Dispose()` đúng lúc), scope không kết thúc đúng thời điểm — dữ liệu context có thể "dính" vào các dòng log không liên quan được ghi sau đó.

6. Trong `appsettings.json`, mục `Logging:LogLevel:Default` và một mục ghi đè riêng cho một category cụ thể (ví dụ `"MyApp.Services.DonHangService": "Debug"`) khác nhau ở điểm nào?

    ??? note "Đáp án"
        `Default` áp dụng cho mọi category không được liệt kê riêng. Mục ghi đè riêng chỉ áp dụng cho đúng category đó (và các category con của nó theo namespace), cho phép hạ/nâng mức log của một phần nhỏ hệ thống mà không ảnh hưởng phần còn lại.

7. Sink trong Serilog là gì?

    ??? note "Đáp án"
        Sink là đích đến cụ thể mà log chảy tới, ví dụ Console, File, Seq, Elasticsearch. Serilog cho phép cấu hình nhiều sink cùng lúc cho cùng một dòng log.

8. Nếu bạn để `"Default": "Trace"` sót lại trong `appsettings.Production.json`, hậu quả cụ thể là gì?

    ??? note "Đáp án"
        Hệ thống production ghi log ở mức chi tiết nhất cho mọi request thật, khiến lượng log tăng vọt — có thể làm đầy disk, vượt hạn mức dịch vụ log tập trung, hoặc khiến log quan trọng bị tự động xoá sớm hơn để giải phóng chỗ, đúng lúc cần nó nhất khi hệ thống gặp sự cố.

---

??? abstract "DEEP DIVE: `IsEnabled`, `EventId`, và log ra JSON có cấu trúc thật"
    Trong code hiệu năng cao (nhưng chưa tới mức cần `LoggerMessage`), bạn có thể tự kiểm tra `logger.IsEnabled(LogLevel.Debug)` trước khi build một message tốn kém (ví dụ serialize một object lớn thành chuỗi chỉ để log ở mức `Debug`) — tránh lãng phí công tính toán nếu level đó đang bị tắt, dù bạn không dùng source generator.

    `EventId` là một số (và tên tuỳ chọn) gắn với một loại sự kiện log cụ thể, ví dụ `new EventId(1001, "DonHangDaTao")`. Khác với category (theo class), `EventId` cho phép bạn định danh **chính xác một điểm log cụ thể** trong code, hữu ích khi muốn tạo dashboard/alert theo đúng một loại sự kiện mà không phụ thuộc vào nội dung message (message có thể đổi ngôn ngữ hiển thị, nhưng `EventId` giữ nguyên).

    Ở production thật, format log phổ biến nhất không phải là dòng text như các ví dụ console trong chương này, mà là **JSON có cấu trúc** — mỗi dòng log là một object JSON với các trường `Timestamp`, `Level`, `MessageTemplate`, và mọi tham số structured logging dưới dạng field riêng. Cả logging built-in (qua `AddJsonConsole()`) và Serilog (qua `Serilog.Formatting.Compact`) đều hỗ trợ xuất JSON — đây chính là định dạng mà Seq/Elasticsearch/Loki đọc và index để bạn truy vấn theo field như các mục trước đã mô tả.

**Tiếp theo →** [P4 · Docker & Deploy](deploy-docker.md)
