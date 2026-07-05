---
tier: core
status: core
owner: core-team
verified_on: "2026-07-03"
dotnet_version: "10.0"
bloom: áp dụng
requires: [p3-middleware]
est_minutes_fast: 24
---

# Xử lý lỗi toàn cục & ProblemDetails

!!! info "Bạn đang ở đây"
    cần trước: bạn đã biết middleware là gì, viết được middleware bằng `app.Use`, và hiểu vì sao thứ tự đăng ký middleware quyết định thứ tự thực thi (chương middleware pipeline).
    mở khoá: sau chương này bạn xử lý được **mọi** exception văng ra từ endpoint tại **một chỗ duy nhất**, trả về đúng định dạng lỗi chuẩn (`ProblemDetails`) mà mọi client (web, mobile, script) đọc được, và không bao giờ để lộ stack trace ra production — nền tảng bắt buộc trước khi API của bạn chạm tay người dùng thật.

> Mục tiêu (đo được): sau chương này bạn **áp dụng** được `UseExceptionHandler` để bắt exception toàn cục thay vì try/catch rải rác, **giải thích** được `ProblemDetails` là gì và vì sao nó là chuẩn RFC cho lỗi HTTP, **triển khai** được `IExceptionHandler` để tách logic xử lý lỗi ra khỏi `Program.cs`, và **phân biệt** được lỗi mong đợi (400 validation) với lỗi không mong đợi (500 exception) để xử lý đúng cách mỗi loại.

---

## 0. Đoán nhanh trước khi học

Bạn có một endpoint sau, không có try/catch:

```csharp title="Program.cs (rút gọn, chỉ để suy luận)"
// test:skip đoạn trích rút gọn chỉ để suy luận, không phải chương trình đầy đủ
app.MapGet("/chia/{a}/{b}", (int a, int b) => a / b);
```

Khi gọi `GET /chia/10/0`, .NET ném `DivideByZeroException`. Nếu `Program.cs` **không** đăng ký gì để xử lý lỗi toàn cục, client nhận được gì?

??? note "Đáp án"
    Mặc định (môi trường Development), ASP.NET Core trả **500 Internal Server Error** kèm một trang HTML chi tiết chứa **toàn bộ stack trace** (`DeveloperExceptionPage`). Ở môi trường Production mà không cấu hình gì thêm, mặc định chỉ còn một response 500 rỗng, không có thông tin gì để client biết phải làm gì. Cả hai đều không phải là điều bạn muốn cho một API thật — chương này giải quyết chính xác vấn đề này.

---

## 1. Vì sao không nên try/catch ở từng endpoint

**Định nghĩa (một câu):** Xử lý lỗi **rải rác** nghĩa là mỗi endpoint tự viết `try/catch` riêng để bắt exception của chính nó — cách này **lặp code** ở mọi endpoint và rất dễ **để sót** endpoint không có catch.

Hãy nhìn một API có 3 endpoint, mỗi endpoint tự lo phần lỗi của mình:

```csharp title="Program.cs"
// test:compile minh hoa van de: try/catch lap lai o tung endpoint
var builder = WebApplication.CreateBuilder(args);
var app = builder.Build();

app.MapGet("/san-pham/{id}", (int id) =>
{
    try
    {
        if (id <= 0) throw new ArgumentException("Id phải lớn hơn 0");
        return Results.Ok(new { id, ten = "Ban phim" });
    }
    catch (Exception ex)
    {
        return Results.Problem(detail: ex.Message, statusCode: 500);
    }
});

app.MapGet("/don-hang/{id}", (int id) =>
{
    try
    {
        if (id <= 0) throw new ArgumentException("Id phải lớn hơn 0");
        return Results.Ok(new { id, tongTien = 100000 });
    }
    catch (Exception ex)
    {
        return Results.Problem(detail: ex.Message, statusCode: 500);
    }
});

// Endpoint thứ ba: người viết QUÊN bọc try/catch.
app.MapGet("/khach-hang/{id}", (int id) =>
{
    if (id <= 0) throw new ArgumentException("Id phải lớn hơn 0");
    return Results.Ok(new { id, ten = "Khach hang A" });
});

app.Run();
```

Hai endpoint đầu lặp lại **y hệt** khối `try/catch`. Endpoint thứ ba — vì người viết quên — sẽ để exception văng thẳng ra ngoài, trả về response mặc định của framework (không phải `ProblemDetails` nhất quán như hai endpoint kia). Càng nhiều endpoint, xác suất "quên" càng cao, và mỗi lần đổi định dạng lỗi (ví dụ thêm trường `traceId`) lại phải sửa ở **mọi nơi** đã copy đoạn `catch`.

**Nếu dùng sai — hậu quả cụ thể:** với endpoint `/khach-hang/{id}` bị quên catch, gọi `GET /khach-hang/0` sẽ làm `ArgumentException` văng thẳng ra khỏi handler; ASP.NET Core xử lý exception không được catch bằng cơ chế mặc định (không phải `ProblemDetails` nhất quán như hai endpoint kia), tạo ra sự **không nhất quán**: client nhận hai định dạng lỗi khác nhau tuỳ endpoint có nhớ catch hay không — rất khó để client viết code xử lý lỗi chung.

Giải pháp đúng: xử lý lỗi tại **một điểm duy nhất** trong pipeline, áp dụng cho **mọi** endpoint tự động, không cần mỗi endpoint tự nhớ. Đó chính là chủ đề của mục 2.

---

## 2. `UseExceptionHandler`: bắt exception toàn cục

**Định nghĩa (một câu):** `app.UseExceptionHandler(...)` là một middleware bọc **toàn bộ phần còn lại của pipeline** trong một khối try/catch ngầm — bất kỳ exception nào văng ra từ middleware hoặc endpoint phía sau nó đều bị bắt tại đây, thay vì văng thẳng ra client.

Vì middleware thực thi theo cơ chế lồng nhau (đã học ở chương middleware), `UseExceptionHandler` phải được đăng ký **gần đầu pipeline nhất có thể** — nó chỉ bắt được exception từ middleware đăng ký **sau** nó (những middleware nó "bọc"), không bắt được exception từ middleware đăng ký **trước** nó.

Ví dụ tối thiểu, độc lập, chỉ minh hoạ đúng khái niệm này:

```csharp title="Program.cs"
// test:compile UseExceptionHandler toi thieu, dat dau pipeline
var builder = WebApplication.CreateBuilder(args);
var app = builder.Build();

// Phải đăng ký GẦN ĐẦU pipeline để bọc được mọi middleware/endpoint phía sau.
app.UseExceptionHandler(handlerApp =>
{
    handlerApp.Run(async context =>
    {
        context.Response.StatusCode = StatusCodes.Status500InternalServerError;
        context.Response.ContentType = "text/plain";
        await context.Response.WriteAsync("Da co loi xay ra phia server.");
    });
});

app.MapGet("/loi", () =>
{
    throw new InvalidOperationException("Loi gia lap de kiem tra exception handler");
});

app.Run();
```

Giải thích từng phần:

- `app.UseExceptionHandler(handlerApp => ...)` nhận vào một delegate cấu hình một **pipeline con** — pipeline này chỉ chạy khi có exception xảy ra ở pipeline chính.
- `handlerApp.Run(async context => ...)` là middleware kết thúc (terminal) của pipeline con đó — nó set status code `500` và viết response thay thế cho exception.
- Endpoint `/loi` cố tình ném `InvalidOperationException` để kiểm chứng: gọi `GET /loi` sẽ **không** làm ứng dụng crash hay trả trang lỗi mặc định — thay vào đó nhận đúng response `500` do bạn kiểm soát.

Khi gọi `GET /loi`:

```text title="Response"
HTTP/1.1 500 Internal Server Error
Content-Type: text/plain

Da co loi xay ra phia server.
```

**Nếu đặt sai vị trí — hành vi cụ thể:** nếu bạn đăng ký một middleware khác **trước** `UseExceptionHandler`, và middleware đó tự ném exception, `UseExceptionHandler` sẽ **không bắt được** exception đó — vì middleware bọc theo thứ tự đăng ký (chương trước đã học), middleware đứng trước không nằm "bên trong" lớp bảo vệ của `UseExceptionHandler`. Kết quả: exception văng thẳng ra ngoài, ứng dụng trả response lỗi mặc định của Kestrel (kết nối bị đóng đột ngột hoặc 500 rỗng không có nội dung bạn kiểm soát), hoàn toàn không nhất quán với các lỗi khác trong hệ thống.

---

## 3. `ProblemDetails`: chuẩn RFC cho lỗi HTTP

**Định nghĩa (một câu):** `ProblemDetails` là một **định dạng JSON chuẩn hoá** cho response lỗi HTTP (nguồn gốc từ RFC 7807, được cập nhật bởi RFC 9457), gồm các trường cố định (`type`, `title`, `status`, `detail`, `instance`) để **mọi client** — web, mobile, script — đọc và xử lý lỗi theo cùng một cấu trúc, thay vì mỗi API tự bịa ra định dạng riêng.

Thay vì middleware ở mục 2 tự viết chuỗi `text/plain`, hãy để nó trả đúng `ProblemDetails`:

```csharp title="Program.cs"
// test:compile tra ProblemDetails chuan tu UseExceptionHandler
var builder = WebApplication.CreateBuilder(args);
var app = builder.Build();

app.UseExceptionHandler(handlerApp =>
{
    handlerApp.Run(async context =>
    {
        context.Response.StatusCode = StatusCodes.Status500InternalServerError;
        await Results.Problem(
            title: "Da co loi khong mong doi xay ra",
            statusCode: StatusCodes.Status500InternalServerError,
            instance: context.Request.Path
        ).ExecuteAsync(context);
    });
});

app.MapGet("/loi", () =>
{
    throw new InvalidOperationException("Loi gia lap de kiem tra ProblemDetails");
});

app.Run();
```

`Results.Problem(...)` là helper có sẵn của Minimal API, tự tạo ra một object `ProblemDetails` và serialize thành JSON đúng chuẩn. Gọi `GET /loi` trả về:

```json title="Response body (500)"
{
  "type": "https://tools.ietf.org/html/rfc9110#section-15.6.1",
  "title": "Da co loi khong mong doi xay ra",
  "status": 500,
  "instance": "/loi"
}
```

Ý nghĩa từng trường:

- **`type`** — một URI (thường trỏ tới tài liệu HTTP status) mô tả **loại** lỗi; mặc định ASP.NET Core tự điền URI của mã status tương ứng.
- **`title`** — mô tả ngắn, **cố định** cho một loại lỗi (không nên chứa dữ liệu động của từng request).
- **`status`** — mã HTTP status, lặp lại giá trị đã có trong dòng status của response (tiện cho client đọc trực tiếp từ body JSON).
- **`instance`** — thường là path của request gây ra lỗi, giúp debug biết chính xác request nào lỗi.
- **`detail`** — mô tả **cụ thể** cho lỗi này (không bắt buộc) — mục 5 sẽ nói rõ vì sao trường này nguy hiểm nếu dùng sai.

**Nếu dùng sai:** nếu bạn tự tay viết JSON lỗi theo cấu trúc riêng (ví dụ `{ "error": "..." }`) thay vì dùng `ProblemDetails`, mỗi API trong hệ thống có thể trả một hình dạng lỗi khác nhau — client (đặc biệt là code dùng chung giữa nhiều API) không thể viết một hàm xử lý lỗi tổng quát, phải đoán hoặc viết riêng cho từng API. Đây không phải lỗi biên dịch hay runtime — là lỗi **thiết kế API** khiến hệ thống khó tích hợp và khó bảo trì lâu dài.

---

## 4. `IExceptionHandler`: tách logic xử lý lỗi ra class riêng

**Định nghĩa (một câu):** `IExceptionHandler` (giới thiệu từ .NET 8) là một **interface chuẩn** của ASP.NET Core cho phép bạn viết logic xử lý exception trong một **class riêng** (thay vì lambda inline trong `Program.cs`), được đăng ký qua DI và tự động được `UseExceptionHandler()` gọi tới khi có exception.

Interface này có đúng một phương thức cần cài đặt:

```csharp title="Chữ ký IExceptionHandler (tham khảo)"
// test:skip chi trich chu ky interface de doc, khong phai chuong trinh day du
public interface IExceptionHandler
{
    ValueTask<bool> TryHandleAsync(
        HttpContext httpContext,
        Exception exception,
        CancellationToken cancellationToken);
}
```

`TryHandleAsync` trả về `true` nếu handler này **đã xử lý xong** exception (viết response rồi); trả `false` nghĩa là "tôi không xử lý được lỗi này, nhường cho handler tiếp theo (nếu có) hoặc để hành vi mặc định chạy".

Ví dụ tối thiểu, độc lập: một `IExceptionHandler` viết `ProblemDetails` và ghi log, tách hẳn khỏi `Program.cs`:

```csharp title="Program.cs"
// test:compile IExceptionHandler tach logic xu ly loi ra class rieng
using Microsoft.AspNetCore.Diagnostics;

var builder = WebApplication.CreateBuilder(args);

// Đăng ký handler qua DI — có thể inject ILogger, IConfiguration... vào constructor.
builder.Services.AddExceptionHandler<GlobalExceptionHandler>();
builder.Services.AddProblemDetails();

var app = builder.Build();

// Khi có IExceptionHandler đã đăng ký, UseExceptionHandler() không cần lambda —
// nó tự gọi TryHandleAsync của mọi handler đã đăng ký theo thứ tự.
app.UseExceptionHandler();

app.MapGet("/loi", () =>
{
    throw new InvalidOperationException("Loi gia lap de kiem tra IExceptionHandler");
});

app.Run();

sealed class GlobalExceptionHandler(ILogger<GlobalExceptionHandler> logger) : IExceptionHandler
{
    public async ValueTask<bool> TryHandleAsync(
        HttpContext httpContext,
        Exception exception,
        CancellationToken cancellationToken)
    {
        logger.LogError(exception, "Loi khong mong doi tai {Path}", httpContext.Request.Path);

        httpContext.Response.StatusCode = StatusCodes.Status500InternalServerError;

        await httpContext.Response.WriteAsJsonAsync(new
        {
            type = "https://tools.ietf.org/html/rfc9110#section-15.6.1",
            title = "Da co loi khong mong doi xay ra",
            status = 500,
            instance = httpContext.Request.Path.Value
        }, cancellationToken);

        return true; // đã xử lý xong — không cần handler nào khác chạy tiếp
    }
}
```

Điểm khác biệt so với mục 2 và 3:

- `GlobalExceptionHandler` là một **class thường**, có thể nhận `ILogger`, `IConfiguration`, hay bất kỳ service nào khác qua constructor — điều lambda inline trong `Program.cs` làm được nhưng khó đọc/khó test khi logic phức tạp.
- `builder.Services.AddExceptionHandler<GlobalExceptionHandler>()` đăng ký handler vào DI container.
- `app.UseExceptionHandler()` **không tham số** — nó tự tìm mọi `IExceptionHandler` đã đăng ký và gọi lần lượt `TryHandleAsync` cho tới khi một handler trả `true`.
- `builder.Services.AddProblemDetails()` bật cơ chế `ProblemDetails` mặc định của framework cho các lỗi khác (như lỗi routing, 404) — nên gọi cùng với `IExceptionHandler` để nhất quán toàn hệ thống.

**Nếu dùng sai:** nếu bạn quên `builder.Services.AddExceptionHandler<GlobalExceptionHandler>()` nhưng vẫn gọi `app.UseExceptionHandler()` không tham số, sẽ không có handler nào được gọi khi exception xảy ra — hành vi rơi về **mặc định của framework** (trang lỗi Development hoặc 500 rỗng ở Production), không có log, không có `ProblemDetails` như bạn mong đợi. Đây là lỗi câm: code biên dịch bình thường, không có cảnh báo, chỉ lộ ra khi bạn thực sự gọi endpoint lỗi và thấy response không giống thiết kế.

---

## 5. Lỗi mong đợi (400) và lỗi không mong đợi (500): xử lý khác nhau

**Định nghĩa (một câu):** Lỗi **mong đợi** là lỗi do **client** gửi dữ liệu sai (thiếu trường, sai định dạng) — framework/bạn đã lường trước và trả `400 Bad Request` với thông tin rõ ràng để client tự sửa; lỗi **không mong đợi** là lỗi do **bug hoặc sự cố phía server** (NullReferenceException, mất kết nối DB) — trả `500 Internal Server Error` và **không** để lộ chi tiết kỹ thuật.

Hai loại lỗi này cần được xử lý ở hai nơi khác nhau trong pipeline:

- **400 (mong đợi):** đã được validation tự động xử lý **trước khi** vào tới handler (xem chương Validation) — đây không phải là exception, mà là một response được trả sớm, có cấu trúc (`errors` theo từng field) để client biết chính xác trường nào sai.
- **500 (không mong đợi):** là **exception thật sự**, văng ra giữa lúc code đang chạy — đây chính là loại `UseExceptionHandler`/`IExceptionHandler` ở mục 2–4 xử lý.

Ví dụ minh hoạ rõ ràng hai luồng khác nhau trong cùng một ứng dụng:

```csharp title="Program.cs"
// test:compile phan biet 400 (mong doi) vs 500 (khong mong doi) trong cung mot app
using Microsoft.AspNetCore.Diagnostics;

var builder = WebApplication.CreateBuilder(args);
builder.Services.AddExceptionHandler<GlobalExceptionHandler>();
builder.Services.AddProblemDetails();

var app = builder.Build();
app.UseExceptionHandler();

// Loại 1 — lỗi MONG ĐỢI: kiểm tra thủ công, chủ động trả 400, KHÔNG phải exception.
app.MapGet("/san-pham/{id}", (int id) =>
{
    if (id <= 0)
    {
        return Results.ValidationProblem(new Dictionary<string, string[]>
        {
            ["id"] = ["Id phải lớn hơn 0"]
        });
    }
    return Results.Ok(new { id, ten = "Ban phim" });
});

// Loại 2 — lỗi KHÔNG MONG ĐỢI: bug thật sự (giả lập chia cho 0), văng ra như exception.
app.MapGet("/thong-ke/{tongDon}/{soNgay}", (int tongDon, int soNgay) =>
{
    var trungBinhMoiNgay = tongDon / soNgay; // soNgay = 0 -> DivideByZeroException
    return Results.Ok(new { trungBinhMoiNgay });
});

app.Run();

sealed class GlobalExceptionHandler(ILogger<GlobalExceptionHandler> logger) : IExceptionHandler
{
    public async ValueTask<bool> TryHandleAsync(
        HttpContext httpContext, Exception exception, CancellationToken cancellationToken)
    {
        logger.LogError(exception, "Loi khong mong doi tai {Path}", httpContext.Request.Path);
        httpContext.Response.StatusCode = StatusCodes.Status500InternalServerError;
        await httpContext.Response.WriteAsJsonAsync(new
        {
            title = "Da co loi khong mong doi xay ra",
            status = 500,
            instance = httpContext.Request.Path.Value
        }, cancellationToken);
        return true;
    }
}
```

So sánh hai response:

```json title="GET /san-pham/0 -> 400 (mong doi, KHONG phai exception)"
{
  "title": "One or more validation errors occurred.",
  "status": 400,
  "errors": {
    "id": ["Id phải lớn hơn 0"]
  }
}
```

```json title="GET /thong-ke/100/0 -> 500 (khong mong doi, exception that)"
{
  "title": "Da co loi khong mong doi xay ra",
  "status": 500,
  "instance": "/thong-ke/100/0"
}
```

Khác biệt cốt lõi: response `400` **biết chính xác** trường nào sai và tại sao (vì code chủ động kiểm tra và mô tả), còn response `500` **cố tình mơ hồ** — không nói `DivideByZeroException` xảy ra ở đâu trong code, vì đó là chi tiết nội bộ, không phải thứ client cần (hoặc nên) biết.

**Nếu nhầm lẫn hai loại — hậu quả cụ thể:** nếu bạn dùng exception (throw) để báo lỗi validation (ví dụ `throw new ArgumentException("Id không hợp lệ")` rồi để `IExceptionHandler` bắt và trả `500`), client sẽ hiểu nhầm đây là **lỗi server** trong khi thực chất là **lỗi dữ liệu họ gửi** — client sẽ không biết cần sửa request, có thể retry vô ích hoặc báo cáo nhầm cho đội vận hành thay vì tự sửa dữ liệu. Ngược lại, nếu bạn cố "validate" một exception thật sự (như lỗi kết nối DB) bằng cách trả `400`, client sẽ nghĩ **họ** gửi sai trong khi lỗi hoàn toàn nằm ở server — che giấu sự cố thật cần đội vận hành xử lý.

---

## 6. Không bao giờ để lộ chi tiết exception ra production

**Định nghĩa (một câu):** Lộ chi tiết exception (message kỹ thuật, stack trace, tên bảng/cột SQL) ra response production là một **lỗ hổng bảo mật** — nó cho kẻ tấn công biết cấu trúc nội bộ hệ thống (tên class, đường dẫn file, phiên bản thư viện, thậm chí một phần câu lệnh SQL) để khai thác.

So sánh hai cách viết `IExceptionHandler` — một sai, một đúng:

```csharp title="Snippet.cs (SAI — rò rỉ chi tiết exception)"
// test:compile phan doi chieu: CACH SAI, khong dung trong production
using Microsoft.AspNetCore.Diagnostics;

sealed class LeakyExceptionHandler : IExceptionHandler
{
    public async ValueTask<bool> TryHandleAsync(
        HttpContext httpContext, Exception exception, CancellationToken cancellationToken)
    {
        httpContext.Response.StatusCode = StatusCodes.Status500InternalServerError;
        // SAI: exception.ToString() chứa stack trace đầy đủ, tên file, số dòng nội bộ.
        await httpContext.Response.WriteAsJsonAsync(new
        {
            title = "Loi server",
            status = 500,
            detail = exception.ToString() // <-- lộ toàn bộ stack trace ra client
        }, cancellationToken);
        return true;
    }
}
```

```csharp title="Snippet.cs (ĐÚNG — log chi tiết nội bộ, trả message chung cho client)"
// test:compile phan doi chieu: CACH DUNG, tach log noi bo va response cong khai
using Microsoft.AspNetCore.Diagnostics;

sealed class SafeExceptionHandler(ILogger<SafeExceptionHandler> logger) : IExceptionHandler
{
    public async ValueTask<bool> TryHandleAsync(
        HttpContext httpContext, Exception exception, CancellationToken cancellationToken)
    {
        // Chi tiết đầy đủ (bao gồm stack trace) chỉ đi vào LOG nội bộ, không vào response.
        logger.LogError(exception, "Loi khong mong doi tai {Path}", httpContext.Request.Path);

        httpContext.Response.StatusCode = StatusCodes.Status500InternalServerError;
        await httpContext.Response.WriteAsJsonAsync(new
        {
            title = "Da co loi khong mong doi xay ra, doi ky thuat da duoc thong bao",
            status = 500,
            instance = httpContext.Request.Path.Value
            // Không có trường "detail" chứa exception.Message/ToString() ở đây.
        }, cancellationToken);
        return true;
    }
}
```

Nguyên tắc: **stack trace và message kỹ thuật đi vào log (`ILogger`), không bao giờ đi vào response JSON trả cho client** ở môi trường Production. Nếu cần phân biệt hành vi giữa Development (tiện debug) và Production (an toàn), dùng `IHostEnvironment.IsDevelopment()` để quyết định có include `detail` hay không — nhưng mặc định an toàn nhất là **không bao giờ** trả `exception.ToString()` hay `exception.StackTrace` ra ngoài, bất kể môi trường nào, để tránh quên đổi cấu hình khi deploy.

**Nếu dùng sai — hậu quả bảo mật cụ thể:** một response chứa `"detail": "System.Data.SqlClient.SqlException: Invalid column name 'MatKhauHash' at TruyVanNguoiDung.cs:42"` cho kẻ tấn công biết: hệ thống dùng SQL Server, tên cột lưu mật khẩu, tên file và số dòng trong source code — đủ thông tin để dò tìm thêm lỗ hổng (SQL injection có mục tiêu rõ ràng hơn) hoặc đoán cấu trúc database để tấn công tiếp.

---

## Cạm bẫy & thực chiến

- **Đặt `UseExceptionHandler()` không phải middleware đầu tiên:** nó chỉ bắt được exception từ middleware **đăng ký sau** nó; một middleware đăng ký trước ném lỗi sẽ không được bắt, exception văng thẳng ra response mặc định của Kestrel.
- **Quên `builder.Services.AddExceptionHandler<T>()` nhưng vẫn gọi `app.UseExceptionHandler()` không tham số:** không có handler nào chạy, hành vi rơi về mặc định của framework — lỗi câm, chỉ phát hiện khi thực sự test endpoint lỗi.
- **Trả `exception.ToString()` hoặc `exception.Message` trực tiếp vào response JSON:** rò rỉ stack trace, tên bảng/cột SQL, đường dẫn file nội bộ — lỗ hổng bảo mật, không phải chỉ là "code xấu".
- **Dùng exception để báo lỗi validation (400) thay vì kiểm tra chủ động:** khiến `IExceptionHandler` (vốn chỉ nên xử lý lỗi 500 không mong đợi) trả nhầm status `500` cho lỗi thực chất là do client gửi sai dữ liệu — client hiểu nhầm ai gây ra lỗi.
- **Copy/paste `try/catch` giống hệt nhau ở mọi endpoint:** không chỉ lặp code, mà chỉ cần một endpoint mới quên copy là hệ thống có hai định dạng lỗi khác nhau tồn tại song song, rất khó phát hiện qua code review vì mỗi endpoint "trông" đều đúng.
- **Không log exception trước khi trả response chung chung:** nếu chỉ trả `"Da co loi xay ra"` mà không `logger.LogError(exception, ...)`, đội vận hành không có cách nào biết lỗi thật sự là gì để sửa — an toàn cho client nhưng vô dụng cho debug nội bộ.

---

## Bài tập

**Bài 1 (giàn giáo):** Đoạn `Program.cs` sau có `UseExceptionHandler` nhưng endpoint `/kho` vẫn không được bảo vệ — gọi lỗi vẫn thấy trang lỗi mặc định thay vì `ProblemDetails`. Tìm lỗi thứ tự và sửa.

```csharp title="Program.cs (có lỗi)"
// test:compile bai tap 1 - co loi thu tu, can sua
var builder = WebApplication.CreateBuilder(args);
var app = builder.Build();

app.Use(async (context, next) =>
{
    Console.WriteLine($"Request: {context.Request.Path}");
    await next();
});

app.MapGet("/kho", () =>
{
    throw new InvalidOperationException("Het hang trong kho");
});

// UseExceptionHandler đăng ký SAU middleware logging và SAU endpoint.
app.UseExceptionHandler(handlerApp =>
{
    handlerApp.Run(async context =>
    {
        context.Response.StatusCode = 500;
        await context.Response.WriteAsync("Loi server");
    });
});

app.Run();
```

Gợi ý giàn giáo: middleware bọc theo thứ tự đăng ký — muốn `UseExceptionHandler` bắt được exception từ middleware logging và endpoint `/kho`, nó phải đứng **trước** cả hai trong code.

??? success "Lời giải + vì sao"
    ```csharp title="Program.cs (đã sửa)"
    // test:compile bai tap 1 - da sua dung thu tu
    var builder = WebApplication.CreateBuilder(args);
    var app = builder.Build();

    // UseExceptionHandler đứng ĐẦU TIÊN để bọc mọi middleware/endpoint phía sau.
    app.UseExceptionHandler(handlerApp =>
    {
        handlerApp.Run(async context =>
        {
            context.Response.StatusCode = 500;
            await context.Response.WriteAsync("Loi server");
        });
    });

    app.Use(async (context, next) =>
    {
        Console.WriteLine($"Request: {context.Request.Path}");
        await next();
    });

    app.MapGet("/kho", () =>
    {
        throw new InvalidOperationException("Het hang trong kho");
    });

    app.Run();
    ```

    **Vì sao:** middleware là các lớp lồng nhau theo thứ tự đăng ký. `UseExceptionHandler` chỉ bảo vệ được những middleware/endpoint nằm "bên trong" nó — nghĩa là những gì được đăng ký **sau** nó trong code. Đăng ký nó sau cùng khiến nó không bọc được gì cả, vì không còn middleware nào phía sau để bảo vệ.

**Bài 2 (thiết kế):** Thiết kế một API có hai endpoint: `GET /don-hang/{id}` trả lỗi `400` (dùng `Results.ValidationProblem`) nếu `id <= 0`, và `GET /bao-cao/{tongTien}/{soLuong}` cố tình chia `tongTien / soLuong` để minh hoạ lỗi `500` không mong đợi khi `soLuong = 0`. Dùng `IExceptionHandler` để xử lý lỗi `500`, log lại bằng `ILogger`, và không để lộ chi tiết exception ra response.

??? success "Lời giải + vì sao"
    ```csharp title="Program.cs"
    // test:compile bai tap 2 - thiet ke day du 400 vs 500 voi IExceptionHandler
    using Microsoft.AspNetCore.Diagnostics;

    var builder = WebApplication.CreateBuilder(args);
    builder.Services.AddExceptionHandler<DonHangExceptionHandler>();
    builder.Services.AddProblemDetails();

    var app = builder.Build();
    app.UseExceptionHandler();

    // Lỗi MONG ĐỢI (400): kiểm tra chủ động, không phải exception.
    app.MapGet("/don-hang/{id}", (int id) =>
    {
        if (id <= 0)
        {
            return Results.ValidationProblem(new Dictionary<string, string[]>
            {
                ["id"] = ["Id đơn hàng phải lớn hơn 0"]
            });
        }
        return Results.Ok(new { id, trangThai = "Dang xu ly" });
    });

    // Lỗi KHÔNG MONG ĐỢI (500): exception thật, IExceptionHandler xử lý.
    app.MapGet("/bao-cao/{tongTien}/{soLuong}", (int tongTien, int soLuong) =>
    {
        var donGia = tongTien / soLuong; // soLuong = 0 -> DivideByZeroException
        return Results.Ok(new { donGia });
    });

    app.Run();

    sealed class DonHangExceptionHandler(ILogger<DonHangExceptionHandler> logger) : IExceptionHandler
    {
        public async ValueTask<bool> TryHandleAsync(
            HttpContext httpContext, Exception exception, CancellationToken cancellationToken)
        {
            logger.LogError(exception, "Loi khong mong doi tai {Path}", httpContext.Request.Path);

            httpContext.Response.StatusCode = StatusCodes.Status500InternalServerError;
            await httpContext.Response.WriteAsJsonAsync(new
            {
                title = "Da co loi khong mong doi xay ra",
                status = 500,
                instance = httpContext.Request.Path.Value
            }, cancellationToken);

            return true;
        }
    }
    ```

    **Vì sao thiết kế này đúng:**

    - `/don-hang/{id}` trả `400` bằng kiểm tra chủ động (`if (id <= 0)`) — đây là lỗi client, không nên là exception, không đi qua `IExceptionHandler`.
    - `/bao-cao/{tongTien}/{soLuong}` để `DivideByZeroException` văng ra tự nhiên — đây là bug/tình huống không lường trước ở tầng tính toán, đúng bản chất lỗi `500`.
    - `DonHangExceptionHandler` log đầy đủ exception (kể cả stack trace) vào `ILogger` để đội vận hành debug được, nhưng response chỉ trả `title`/`status`/`instance` chung chung — không có trường nào chứa `exception.Message` hay `exception.ToString()`.

---

## Tự kiểm tra

1. Vì sao không nên viết `try/catch` giống nhau ở mọi endpoint thay vì xử lý lỗi toàn cục?

    ??? note "Đáp án"
        Vì nó lặp code ở mọi endpoint và rất dễ để sót — chỉ cần một endpoint mới quên copy khối catch là hệ thống có hai định dạng lỗi khác nhau tồn tại song song, khó phát hiện qua review.

2. `UseExceptionHandler` phải được đặt ở đâu trong pipeline, và vì sao?

    ??? note "Đáp án"
        Gần đầu pipeline nhất có thể. Vì middleware bọc theo thứ tự đăng ký, nó chỉ bắt được exception từ middleware/endpoint đăng ký **sau** nó — middleware đăng ký trước nó ném lỗi sẽ không được bắt.

3. `ProblemDetails` là gì và tại sao dùng nó thay vì tự bịa cấu trúc JSON lỗi riêng?

    ??? note "Đáp án"
        `ProblemDetails` là định dạng JSON chuẩn hoá cho lỗi HTTP (RFC 7807, cập nhật bởi RFC 9457), gồm các trường cố định như `title`, `status`, `detail`, `instance`. Dùng nó giúp mọi client đọc và xử lý lỗi theo cùng một cấu trúc, thay vì phải đoán hoặc viết riêng cho từng API có định dạng lỗi khác nhau.

4. `IExceptionHandler.TryHandleAsync` trả về `false` có ý nghĩa gì?

    ??? note "Đáp án"
        Nghĩa là handler này không xử lý được exception đó — nhường lại cho handler tiếp theo đã đăng ký (nếu có), hoặc để hành vi mặc định của framework chạy nếu không còn handler nào khác.

5. Vì sao lỗi validation (400) không nên được xử lý bằng cách throw exception rồi để `IExceptionHandler` bắt?

    ??? note "Đáp án"
        Vì `IExceptionHandler` mặc định trả `500` (lỗi không mong đợi phía server), trong khi lỗi validation là lỗi phía client (dữ liệu sai định dạng). Nếu dùng exception cho validation, client sẽ hiểu nhầm đây là lỗi server, không biết cần tự sửa request.

6. Trường nào trong `ProblemDetails` không nên chứa `exception.ToString()` hoặc `exception.StackTrace` ở production, và vì sao?

    ??? note "Đáp án"
        Trường `detail` (hoặc bất kỳ trường nào khác). Vì stack trace lộ ra cấu trúc nội bộ hệ thống (tên bảng/cột SQL, đường dẫn file, tên class) — đây là lỗ hổng bảo mật cho kẻ tấn công, không chỉ là vấn đề thẩm mỹ của response.

7. Nếu bạn gọi `app.UseExceptionHandler()` không tham số nhưng quên `builder.Services.AddExceptionHandler<T>()`, chuyện gì xảy ra khi có exception?

    ??? note "Đáp án"
        Không có handler nào được gọi — hành vi rơi về mặc định của framework (trang lỗi Development hoặc 500 rỗng ở Production). Đây là lỗi câm: không có cảnh báo lúc build, chỉ lộ ra khi thực sự test endpoint gây lỗi.

---

??? abstract "DEEP DIVE: `ExceptionHandlerOptions`, nhiều `IExceptionHandler`, và `IProblemDetailsService`"
    Ngoài cách gọi `app.UseExceptionHandler()` không tham số (dựa hoàn toàn vào `IExceptionHandler` đã đăng ký), bạn có thể cấu hình chi tiết hơn qua `ExceptionHandlerOptions`, ví dụ chỉ định route xử lý lỗi riêng biệt (`ExceptionHandlingPath`) thay vì xử lý inline — hữu ích khi muốn dùng lại một endpoint MVC/Minimal API có sẵn làm "trang lỗi" chung.

    Bạn cũng có thể đăng ký **nhiều** `IExceptionHandler` cùng lúc — chúng được gọi theo đúng **thứ tự đăng ký** cho tới khi một handler trả `true`. Cách này hữu ích để tách theo loại exception, ví dụ một handler riêng cho `TimeoutException` (trả `504 Gateway Timeout`) và một handler tổng quát cho mọi exception còn lại (trả `500`):

    ```csharp title="Program.cs"
    // test:compile nhieu IExceptionHandler, goi theo thu tu dang ky
    using Microsoft.AspNetCore.Diagnostics;

    var builder = WebApplication.CreateBuilder(args);

    // Đăng ký theo thứ tự ưu tiên: TimeoutExceptionHandler được thử TRƯỚC.
    builder.Services.AddExceptionHandler<TimeoutExceptionHandler>();
    builder.Services.AddExceptionHandler<FallbackExceptionHandler>();
    builder.Services.AddProblemDetails();

    var app = builder.Build();
    app.UseExceptionHandler();

    app.MapGet("/cham", () => { throw new TimeoutException("Qua thoi gian cho"); });
    app.MapGet("/loi-khac", () => { throw new InvalidOperationException("Loi khac"); });

    app.Run();

    sealed class TimeoutExceptionHandler : IExceptionHandler
    {
        public async ValueTask<bool> TryHandleAsync(
            HttpContext httpContext, Exception exception, CancellationToken cancellationToken)
        {
            if (exception is not TimeoutException) return false; // nhường cho handler kế tiếp

            httpContext.Response.StatusCode = StatusCodes.Status504GatewayTimeout;
            await httpContext.Response.WriteAsJsonAsync(new { title = "Qua thoi gian cho", status = 504 }, cancellationToken);
            return true;
        }
    }

    sealed class FallbackExceptionHandler : IExceptionHandler
    {
        public async ValueTask<bool> TryHandleAsync(
            HttpContext httpContext, Exception exception, CancellationToken cancellationToken)
        {
            httpContext.Response.StatusCode = StatusCodes.Status500InternalServerError;
            await httpContext.Response.WriteAsJsonAsync(new { title = "Loi khong mong doi", status = 500 }, cancellationToken);
            return true; // luôn xử lý được — đây là "lưới an toàn" cuối cùng
        }
    }
    ```

    Cuối cùng, ASP.NET Core còn có `IProblemDetailsService` — một service DI cho phép tuỳ biến **mọi** `ProblemDetails` được tạo ra trong ứng dụng (kể cả các lỗi tự động như 404 route không khớp) tại một điểm cấu hình duy nhất, qua `builder.Services.AddProblemDetails(options => options.CustomizeProblemDetails = context => { ... })`. Đây là công cụ hữu ích khi bạn muốn thêm trường tuỳ chỉnh (ví dụ `traceId` từ `Activity.Current`) vào **mọi** response lỗi trong toàn hệ thống, không chỉ lỗi từ exception.

Tiếp theo -> ef core và dbcontext
