---
tier: core
status: core
owner: core-team
verified_on: "2026-07-03"
dotnet_version: "10.0"
bloom: "Apply"
requires: [p8-caching]
est_minutes_fast: 30
---

# Rate Limiting: chống lạm dụng API

!!! info "Bạn đang ở đây"
    **cần trước:** caching (biết vì sao `IMemoryCache` chỉ sống trong tiến trình, và phân biệt in-process cache với distributed cache).
    **mở khoá:** bảo vệ API khỏi brute-force đăng nhập, chống một client chiếm hết tài nguyên server, và các chương observability/health-check nâng cao cần biết cách hệ thống phản ứng dưới tải.
    **liên hệ trực tiếp:** cùng thuộc nhóm "production hardening" với caching (chương trước) — cả hai đều đối mặt vấn đề in-process vs distributed khi ứng dụng scale ra nhiều instance, chi tiết ở DEEP DIVE cuối bài.

> **Mục tiêu:** **Áp dụng** đúng cách đăng ký `AddRateLimiter` cho một endpoint, **phân biệt** được 4 thuật toán giới hạn tốc độ có sẵn trong .NET và biết khi nào dùng loại nào, **giải thích** được response 429 kèm header `Retry-After` nghĩa là gì, và **thiết kế** được rate limit theo IP hoặc theo user-id tuỳ tình huống.
>
> Chương này giả định bạn đã biết cách đăng ký service qua `builder.Services` và cách thêm middleware qua `app.Use...()` (đã học ở các chương Web API trước) — trọng tâm ở đây là hiểu đúng bản chất của **4 thuật toán giới hạn tốc độ** và cách áp dụng chúng đúng ngữ cảnh, không lặp lại kiến thức pipeline/middleware cơ bản.

---

## 0. Đoán nhanh trước khi học

Một API đăng nhập (`POST /login`) không có bất kỳ giới hạn nào về số lần gọi. Một kẻ tấn công viết script gọi endpoint này 5000 lần/giây, mỗi lần thử một mật khẩu khác nhau cho cùng một username.

??? question "Đoán trước, đáp án ở dưới"
    Gợi ý: nghĩ về việc server xử lý được bao nhiêu request/giây, và việc thử mật khẩu tự động có tên gọi kỹ thuật là gì.
    Gợi ý thêm: hậu quả không chỉ là rủi ro với riêng tài khoản bị dò mật khẩu — nghĩ tới việc 5000 request/giây đó còn tiêu tốn tài nguyên gì khác của server.

??? note "Đáp án"
    Đây là **brute-force attack** (dò mật khẩu bằng cách thử liên tục) — vì endpoint không giới hạn số lần gọi, kẻ tấn công có thể thử hàng triệu mật khẩu trong vài phút. Ngoài rủi ro bị chiếm tài khoản, 5000 request/giây dồn vào một endpoint còn làm quá tải CPU/database (mỗi lần đăng nhập thường phải hash mật khẩu và query database), có thể khiến server sập cho **toàn bộ người dùng khác**, không chỉ nạn nhân bị dò mật khẩu. Mục 1 giải thích rõ vấn đề này và mục 2 giới thiệu `AddRateLimiter` — công cụ có sẵn trong .NET để chặn kiểu lạm dụng này.

---

## 1. Vấn đề gốc: một client gọi API liên tục làm quá tải hoặc lạm dụng hệ thống

**Định nghĩa:** Rate limiting (giới hạn tốc độ) là kỹ thuật giới hạn **số lượng request** mà một nguồn gọi (một địa chỉ IP, một user, hoặc toàn hệ thống) được phép gửi tới API trong một khoảng thời gian nhất định, nhằm ngăn một client chiếm dụng quá nhiều tài nguyên server hoặc lợi dụng API để làm điều có hại.

Có hai nhóm hậu quả cụ thể khi API không có rate limiting:

1. **Quá tải vô ý hoặc cố ý (Denial of Service):** một client (do lỗi code, do vòng lặp vô hạn, hoặc do cố ý tấn công) gọi API hàng nghìn lần/giây, chiếm hết CPU, kết nối database, hoặc băng thông — khiến API **chậm hoặc sập cho tất cả người dùng khác**, không riêng client đó.
2. **Lạm dụng logic nghiệp vụ (cheat hệ thống):** ví dụ brute-force dò mật khẩu ở endpoint đăng nhập (thử hàng triệu tổ hợp mật khẩu), dò mã giảm giá bằng cách thử tuần tự, hoặc gọi API gửi OTP (mã xác thực qua SMS) liên tục để tiêu tốn ngân sách gửi SMS của công ty.

Không có rate limiting, **không có gì cản** một request thứ 2 gọi ngay sau request thứ 1, dù client đó là một script tự động chạy vô hạn.

**Điều gì xảy ra khi thiếu rate limiting (hậu quả production cụ thể):** ngoài rủi ro brute-force đăng nhập ở trên, một endpoint gọi API bên thứ ba trả phí (ví dụ dịch vụ gửi SMS OTP, giá 500 đồng/lần gửi) mà không giới hạn, kẻ tấn công có thể gọi endpoint đó hàng chục nghìn lần trong vài phút, khiến **chi phí hạ tầng tăng vọt bất ngờ** trong hoá đơn cuối tháng, dù không có dữ liệu nào bị đánh cắp.

Một hậu quả thứ ba, ít được nhắc tới nhưng thực tế thường gặp: **cạn kết nối database**. Mỗi request tới một endpoint đọc dữ liệu thường mở một kết nối tới database (hoặc mượn một kết nối từ connection pool có kích thước hạn chế, ví dụ pool mặc định của SQL Server thường giới hạn khoảng 100 kết nối đồng thời). Nếu một client (hoặc một con bot lỗi vô tình gọi lặp vô hạn) gửi hàng nghìn request/giây tới một endpoint truy vấn database, toàn bộ connection pool có thể bị chiếm hết trong vài giây — không chỉ endpoint đó bị chậm, mà **mọi endpoint khác trong cùng ứng dụng cũng không mượn được kết nối database**, dẫn tới lỗi hàng loạt (`InvalidOperationException: Timeout expired. The timeout period elapsed prior to obtaining a connection from the pool`) lan ra toàn hệ thống dù nguyên nhân gốc chỉ nằm ở một endpoint.

Điều quan trọng cần phân biệt: rate limiting không phải là công cụ chống mọi loại tấn công. Nó chống **lạm dụng về số lượng/tần suất gọi**, khác với xác thực (authentication — xác minh bạn là ai), phân quyền (authorization — bạn được làm gì), hay validation (kiểm tra dữ liệu đầu vào hợp lệ). Một request có thể có JWT hợp lệ, đúng quyền, dữ liệu hợp lệ, và **vẫn** cần bị chặn nếu nó được gửi quá nhiều lần trong thời gian ngắn — đây chính là lớp bảo vệ riêng mà rate limiting bổ sung, không thay thế các lớp bảo vệ khác.

Một cách hình dung khác giúp phân biệt rõ hơn: hãy coi rate limiting giống như một "vòi nước hạn chế lưu lượng" đặt trước cửa vào của toà nhà. Nó không kiểm tra bạn là ai (đó là việc của bảo vệ ở cổng — authentication), không kiểm tra bạn được vào phòng nào (đó là việc của thẻ ra vào — authorization), và không kiểm tra bạn có mang đúng giấy tờ hợp lệ không (đó là việc của lễ tân — validation). Nó chỉ đơn giản đếm số người đi qua cửa trong một khoảng thời gian, và nếu vượt quá sức chứa an toàn, nó chặn người tiếp theo lại — bất kể người đó có hợp lệ về mọi mặt khác hay không. Vì lý do này, rate limiting luôn được đặt sớm trong pipeline xử lý request (thường ngay sau các middleware hạ tầng như logging, trước khi vào routing và các middleware nghiệp vụ) — chặn sớm để tránh lãng phí tài nguyên xử lý các bước sau cho những request đã biết sẽ bị từ chối.

---

## 2. `AddRateLimiter`: bật rate limiting có sẵn trong .NET

**Định nghĩa:** `AddRateLimiter` là phương thức mở rộng của `IServiceCollection` (namespace `Microsoft.AspNetCore.RateLimiting`, có sẵn từ .NET 7, không cần cài package ngoài) dùng để đăng ký middleware giới hạn tốc độ vào pipeline ứng dụng — bạn định nghĩa các "policy" (chính sách) đặt tên, rồi gắn từng policy vào endpoint cụ thể qua `.RequireRateLimiting("tên-policy")`.

Ví dụ tối thiểu: giới hạn một endpoint chỉ nhận tối đa 5 request mỗi 10 giây (dùng thuật toán Fixed Window — mục 3 giải thích chi tiết thuật toán này):

```csharp title="Program.cs"
// test:compile dang ky AddRateLimiter co ban, ap dung cho 1 endpoint
using System.Threading.RateLimiting;
using Microsoft.AspNetCore.RateLimiting;

var builder = WebApplication.CreateBuilder(args);

builder.Services.AddRateLimiter(options =>
{
    // Dinh nghia mot policy ten "fixed", dung thuat toan Fixed Window.
    options.AddFixedWindowLimiter("fixed", limiterOptions =>
    {
        limiterOptions.PermitLimit = 5;                     // toi da 5 request
        limiterOptions.Window = TimeSpan.FromSeconds(10);    // moi 10 giay
    });
});

var app = builder.Build();

// PHAI goi UseRateLimiter() de middleware thuc su kiem tra request.
app.UseRateLimiter();

app.MapGet("/data", () => "OK")
   .RequireRateLimiting("fixed"); // gan policy "fixed" cho endpoint nay

app.Run();
```

**Điều gì xảy ra khi dùng sai:** nếu bạn gọi `AddRateLimiter` và định nghĩa policy nhưng **quên gọi `app.UseRateLimiter()`**, middleware không được thêm vào pipeline — mọi request đi qua như thể không có rate limiting nào tồn tại, dù code đăng ký "trông có vẻ đúng" và biên dịch bình thường. Đây là lỗi runtime âm thầm, không có exception, chỉ phát hiện được khi kiểm thử tải (load test) hoặc khi bị tấn công thật.

Một lỗi khác thường gặp: nếu endpoint **không** gọi `.RequireRateLimiting("fixed")`, endpoint đó hoàn toàn không bị giới hạn — mỗi policy chỉ áp dụng cho endpoint được gán rõ ràng, không tự động áp dụng toàn cục trừ khi bạn cấu hình `options.GlobalLimiter`.

**Vì sao mặc định không giới hạn theo khoá phân vùng (partition key) nào cả:** trong ví dụ trên, `AddFixedWindowLimiter("fixed", ...)` tạo **một bộ đếm duy nhất, dùng chung cho TẤT CẢ client** — nghĩa là nếu client A gọi hết 5 request trong 10 giây, client B (dù là một người dùng hoàn toàn khác, gọi lần đầu) cũng bị chặn theo cùng bộ đếm đó. Đây có thể là hành vi mong muốn (giới hạn tổng năng lực xử lý của server, không phân biệt ai gọi), nhưng thường KHÔNG phải điều bạn muốn cho hầu hết tình huống thực tế — mục 8 giới thiệu `AddPolicy` với khoá phân vùng theo IP hoặc user-id để mỗi client có bộ đếm riêng, không ảnh hưởng tới nhau.

---

## 3. Fixed Window: giới hạn cố định theo khung giờ

**Định nghĩa:** Fixed Window (khung cố định) là thuật toán chia thời gian thành các khung có độ dài cố định (ví dụ mỗi 60 giây là một khung mới), và trong mỗi khung, một nguồn gọi chỉ được phép gửi tối đa N request — khi khung kết thúc, bộ đếm reset về 0 bất kể request trước đó gọi lúc nào trong khung.

Ví dụ: giới hạn 100 request/60 giây cho toàn bộ API bằng một named policy:

```csharp title="Program.cs"
// test:compile fixed window: 100 request co dinh moi 60 giay
using System.Threading.RateLimiting;
using Microsoft.AspNetCore.RateLimiting;

var builder = WebApplication.CreateBuilder(args);

builder.Services.AddRateLimiter(options =>
{
    options.AddFixedWindowLimiter("api-fixed", limiterOptions =>
    {
        limiterOptions.PermitLimit = 100;
        limiterOptions.Window = TimeSpan.FromSeconds(60);
        limiterOptions.QueueLimit = 0; // khong cho request cho hang doi, tu choi ngay khi vuot
    });
});

var app = builder.Build();
app.UseRateLimiter();

app.MapGet("/products", () => "danh sach san pham")
   .RequireRateLimiting("api-fixed");

app.Run();
```

**Nhược điểm cần biết (không phải lỗi dùng sai, mà là bản chất thuật toán):** Fixed Window có vấn đề ở **ranh giới giữa hai khung**. Ví dụ khung là "0-60s" và "60-120s": một client có thể gửi 100 request vào giây thứ 59 (cuối khung 1) và 100 request nữa vào giây thứ 61 (đầu khung 2) — tổng cộng 200 request trong vòng chỉ 2 giây thực tế, dù mỗi khung riêng lẻ đều "hợp lệ" theo giới hạn 100/khung. Đây là lý do mục 4 giới thiệu Sliding Window — thuật toán khắc phục đúng vấn đề này.

---

## 4. Sliding Window: chính xác hơn ở ranh giới thời gian

**Định nghĩa:** Sliding Window (khung trượt) là thuật toán chia mỗi khung lớn thành nhiều khung nhỏ (segment), và khi tính số request đã dùng, nó cộng dồn có trọng số các segment gần nhất — nhờ vậy tránh được hiện tượng "dồn cục ở ranh giới" của Fixed Window, cho kết quả chính xác hơn về số request thực sự xảy ra trong bất kỳ khoảng 60 giây liên tục nào (không chỉ tính theo khung cố định 0-60, 60-120...).

```csharp title="Program.cs"
// test:compile sliding window: 100 request/60s, chia thanh 6 segment 10s de tinh chinh xac hon
using System.Threading.RateLimiting;
using Microsoft.AspNetCore.RateLimiting;

var builder = WebApplication.CreateBuilder(args);

builder.Services.AddRateLimiter(options =>
{
    options.AddSlidingWindowLimiter("api-sliding", limiterOptions =>
    {
        limiterOptions.PermitLimit = 100;
        limiterOptions.Window = TimeSpan.FromSeconds(60);
        limiterOptions.SegmentsPerWindow = 6; // chia 60s thanh 6 segment 10s
        limiterOptions.QueueLimit = 0;
    });
});

var app = builder.Build();
app.UseRateLimiter();

app.MapGet("/orders", () => "danh sach don hang")
   .RequireRateLimiting("api-sliding");

app.Run();
```

Đánh đổi: Sliding Window tốn nhiều bộ nhớ và tính toán hơn Fixed Window (vì phải theo dõi nhiều segment thay vì một bộ đếm duy nhất), nhưng loại bỏ được lỗ hổng dồn cục ở ranh giới khung đã nêu ở mục 3. Dùng Sliding Window khi độ chính xác quan trọng (ví dụ API trả phí theo lượt gọi); dùng Fixed Window khi cần đơn giản, nhẹ, và chấp nhận sai số nhỏ ở ranh giới.

---

## 5. Token Bucket: cho phép burst ngắn hạn

**Định nghĩa:** Token Bucket (giỏ token) là thuật toán mô phỏng một "giỏ" chứa tối đa N token; mỗi request tiêu tốn 1 token, giỏ được "nạp lại" (replenish) một số token cố định sau mỗi khoảng thời gian — nhờ vậy client có thể gửi một **loạt request dồn (burst)** ngay lập tức nếu giỏ đang đầy, miễn là tổng lượng request về lâu dài không vượt tốc độ nạp lại.

```csharp title="Program.cs"
// test:compile token bucket: giu toi 20 token, nap lai 5 token moi 10 giay -> cho phep burst ngan han
using System.Threading.RateLimiting;
using Microsoft.AspNetCore.RateLimiting;

var builder = WebApplication.CreateBuilder(args);

builder.Services.AddRateLimiter(options =>
{
    options.AddTokenBucketLimiter("api-token-bucket", limiterOptions =>
    {
        limiterOptions.TokenLimit = 20;                          // dung luong gio toi da
        limiterOptions.TokensPerPeriod = 5;                      // nap lai 5 token
        limiterOptions.ReplenishmentPeriod = TimeSpan.FromSeconds(10); // moi 10 giay
        limiterOptions.QueueLimit = 0;
    });
});

var app = builder.Build();
app.UseRateLimiter();

app.MapGet("/search", (string q) => $"ket qua tim kiem cho: {q}")
   .RequireRateLimiting("api-token-bucket");

app.Run();
```

Khác biệt cốt lõi so với Fixed/Sliding Window: hai thuật toán đó giới hạn **tổng số request trong một khung thời gian cố định**, còn Token Bucket cho phép client "tích trữ" token khi không gọi, rồi xả hết một lúc (ví dụ người dùng mở app sau một đêm không dùng, giỏ đầy 20 token, gọi 20 request liên tiếp ngay lập tức vẫn hợp lệ) — phù hợp với các API mà hành vi người dùng thực tế thường dồn cục (ví dụ tìm kiếm gõ nhanh nhiều ký tự), thay vì trải đều tuyệt đối theo thời gian.

---

## 6. Concurrency Limiter: giới hạn số request đang xử lý đồng thời

**Định nghĩa:** Concurrency Limiter (giới hạn đồng thời) là thuật toán khác biệt hoàn toàn về bản chất so với ba thuật toán trên — nó **không** đếm số request theo thời gian, mà giới hạn **số lượng request đang được xử lý cùng một lúc** (đang chiếm một "slot" xử lý); khi một request hoàn tất và giải phóng slot, request tiếp theo trong hàng đợi mới được nhận slot đó.

Ví dụ: một endpoint gọi tới một tác vụ nặng (xử lý ảnh, export báo cáo), chỉ cho phép tối đa 3 request xử lý đồng thời, các request thêm vào phải chờ hoặc bị từ chối:

```csharp title="Program.cs"
// test:compile concurrency limiter: toi da 3 request DANG XU LY dong thoi, khong lien quan so luong theo thoi gian
using System.Threading.RateLimiting;
using Microsoft.AspNetCore.RateLimiting;

var builder = WebApplication.CreateBuilder(args);

builder.Services.AddRateLimiter(options =>
{
    options.AddConcurrencyLimiter("heavy-task", limiterOptions =>
    {
        limiterOptions.PermitLimit = 3;   // toi da 3 request dong thoi
        limiterOptions.QueueLimit = 2;    // them 2 request duoc cho trong hang doi
    });
});

var app = builder.Build();
app.UseRateLimiter();

app.MapPost("/export-report", async () =>
{
    await Task.Delay(TimeSpan.FromSeconds(5)); // mo phong tac vu nang, chiem slot 5 giay
    return "bao cao da xuat";
})
   .RequireRateLimiting("heavy-task");

app.Run();
```

**Phân biệt rõ với 3 thuật toán trước:** Fixed Window/Sliding Window/Token Bucket đều trả lời câu hỏi "trong khoảng thời gian X, được gọi bao nhiêu lần?" — chúng không quan tâm request trước đã xử lý xong hay chưa. Concurrency Limiter trả lời câu hỏi khác hẳn: "ngay lúc này, có bao nhiêu request đang chạy song song?" — một request chạy 10 giây vẫn chỉ chiếm 1 slot suốt 10 giây đó, bất kể có bao nhiêu request khác đã gọi trước hay sau nó theo thời gian. Dùng Concurrency Limiter khi tài nguyên hạn chế là **khả năng xử lý song song** (ví dụ số kết nối tới một API ngoài, số worker xử lý ảnh), không phải tần suất gọi.

**`QueueLimit` và `QueueProcessingOrder`: điều gì xảy ra với request vượt giới hạn trước khi bị từ chối.** Cả 4 thuật toán đều có tuỳ chọn `QueueLimit` — số request được phép **xếp hàng chờ** (không xử lý ngay, cũng không bị từ chối ngay) khi đã đạt giới hạn. Với `QueueLimit = 0` (giá trị đã dùng ở các ví dụ mục 3-5), request vượt giới hạn bị từ chối (429) **ngay lập tức**, không chờ. Với `QueueLimit > 0` (như ví dụ Concurrency Limiter ở trên, `QueueLimit = 2`), request vượt giới hạn được giữ trong hàng đợi, chờ tới khi có slot trống — chỉ bị từ chối nếu hàng đợi cũng đầy. Tham số `QueueProcessingOrder` quyết định thứ tự xử lý hàng đợi: `OldestFirst` (mặc định, request chờ lâu nhất được xử lý trước — công bằng theo thứ tự đến) hoặc `NewestFirst` (request mới nhất được xử lý trước — ưu tiên phản hồi nhanh cho request gần đây, chấp nhận request cũ có thể bị timeout ở phía client trước khi tới lượt).

**Điều gì xảy ra khi dùng sai `QueueLimit`:** đặt `QueueLimit` quá lớn cho một Concurrency Limiter bảo vệ tác vụ nặng (ví dụ `QueueLimit = 10000`) không thực sự bảo vệ được server — request vẫn được chấp nhận và giữ trong hàng đợi (tốn bộ nhớ để giữ context của từng request đang chờ), chỉ trì hoãn thời điểm quá tải thay vì ngăn nó; nếu tất cả 10000 request trong hàng đợi cuối cùng đều tới lượt xử lý gần như đồng thời (ví dụ khi các slot đang chạy đột ngột giải phóng cùng lúc), server vẫn có thể bị quá tải như không có giới hạn nào.

---

## 7. Response 429 và header `Retry-After`

**Định nghĩa:** `429 Too Many Requests` là mã trạng thái HTTP chuẩn báo cho client biết request bị từ chối **vì vượt quá giới hạn tốc độ**, không phải vì lỗi dữ liệu (4xx khác) hay lỗi server (5xx); kèm theo đó, header `Retry-After` (tuỳ chọn) cho client biết **nên chờ bao nhiêu giây** trước khi thử lại.

Middleware `UseRateLimiter()` của .NET tự động trả 429 khi vượt giới hạn — bạn có thể tuỳ biến nội dung response và thêm header `Retry-After`:

```csharp title="Program.cs"
// test:compile tuy bien response 429 kem header Retry-After
using System.Threading.RateLimiting;
using Microsoft.AspNetCore.RateLimiting;

var builder = WebApplication.CreateBuilder(args);

builder.Services.AddRateLimiter(options =>
{
    // Ma status tra ve khi vuot gioi han (mac dinh da la 429, ghi ro de minh hoa).
    options.RejectionStatusCode = StatusCodes.Status429TooManyRequests;

    options.OnRejected = async (context, cancellationToken) =>
    {
        // Bao client cho 15 giay truoc khi goi lai.
        context.HttpContext.Response.Headers.RetryAfter = "15";
        await context.HttpContext.Response.WriteAsync(
            "Ban da vuot gioi han so luong request. Vui long thu lai sau 15 giay.",
            cancellationToken);
    };

    options.AddFixedWindowLimiter("fixed", limiterOptions =>
    {
        limiterOptions.PermitLimit = 5;
        limiterOptions.Window = TimeSpan.FromSeconds(10);
    });
});

var app = builder.Build();
app.UseRateLimiter();

app.MapGet("/data", () => "OK").RequireRateLimiting("fixed");

app.Run();
```

**Điều gì xảy ra khi dùng sai:** nếu API trả 429 nhưng **không** kèm `Retry-After`, client (đặc biệt là các thư viện tự động retry) không biết nên chờ bao lâu — nhiều client sẽ retry ngay lập tức, làm tăng thêm số request bị từ chối, tạo ra một vòng lặp request-bị-từ-chối-rồi-retry-ngay liên tục, tự làm nặng thêm chính vấn đề mà rate limiting muốn giải quyết.

**Tính `Retry-After` động, chính xác theo thời gian còn lại của khung, thay vì hằng số cố định.** Ví dụ ở mục trên hard-code giá trị `"15"` cho mọi trường hợp bị chặn — điều này không chính xác, vì thời gian còn lại tới khi khung reset (hoặc token được nạp lại) thay đổi liên tục tuỳ vào lúc client bị chặn rơi vào đâu trong khung. `RateLimitLease` (đối tượng trả về từ mỗi lần kiểm tra giới hạn) có sẵn `Metadata` chứa `RetryAfter` do chính thuật toán tính toán:

```csharp title="Program.cs"
// test:compile tinh Retry-After dong tu RateLimitLease.Metadata, chinh xac hon hang so cung
using System.Threading.RateLimiting;
using Microsoft.AspNetCore.RateLimiting;

var builder = WebApplication.CreateBuilder(args);

builder.Services.AddRateLimiter(options =>
{
    options.OnRejected = async (context, cancellationToken) =>
    {
        // context.Lease chua thong tin ve lan kiem tra gioi han vua bi tu choi.
        if (context.Lease.TryGetMetadata(MetadataName.RetryAfter, out var retryAfter))
        {
            // Gia tri nay do CHINH THUAT TOAN tinh, phan anh dung thoi gian con lai thuc te.
            context.HttpContext.Response.Headers.RetryAfter =
                ((int)retryAfter.TotalSeconds).ToString();
        }

        context.HttpContext.Response.StatusCode = StatusCodes.Status429TooManyRequests;
        await context.HttpContext.Response.WriteAsync(
            "Vuot gioi han so luong request.", cancellationToken);
    };

    options.AddFixedWindowLimiter("fixed", limiterOptions =>
    {
        limiterOptions.PermitLimit = 5;
        limiterOptions.Window = TimeSpan.FromSeconds(10);
    });
});

var app = builder.Build();
app.UseRateLimiter();

app.MapGet("/data", () => "OK").RequireRateLimiting("fixed");

app.Run();
```

**Vì sao cách này tốt hơn hằng số cố định:** nếu client bị chặn ngay ở giây đầu tiên của khung 10 giây, họ cần chờ gần 10 giây; nếu bị chặn ở giây thứ 9, họ chỉ cần chờ khoảng 1 giây. Hằng số cố định `"15"` (như ví dụ trước) luôn sai theo một hướng — hoặc bắt client chờ lâu hơn cần thiết (lãng phí), hoặc chờ chưa đủ (client retry sớm, vẫn bị 429 lần nữa). Đọc `Metadata` từ `context.Lease` cho giá trị chính xác theo trạng thái thật của thuật toán tại thời điểm từ chối.

**Phân biệt 429 với các mã lỗi 4xx khác dễ nhầm:** một lỗi phổ biến khi mới thiết kế API là trả `400 Bad Request` hoặc `403 Forbidden` khi client vượt giới hạn tốc độ — cả hai đều SAI về ngữ nghĩa. `400` nghĩa là dữ liệu request không hợp lệ (ví dụ thiếu field bắt buộc); `403` nghĩa là client bị từ chối vĩnh viễn cho request này (không phải vì thời điểm, mà vì không có quyền). `429` mang ý nghĩa khác hẳn hai mã trên: request về bản chất **hợp lệ và được phép**, chỉ đơn giản là **đến quá sớm** — client hoàn toàn có thể thử lại thành công sau khi chờ đúng thời gian ở `Retry-After`. Phân biệt đúng ba mã này giúp client (và cả người debug) hiểu đúng bản chất lỗi mà không cần đọc thêm tài liệu.

---

## 8. Rate limit theo IP vs theo user-id đã đăng nhập

**Định nghĩa:** giới hạn theo IP nghĩa là bộ đếm request được tính riêng cho từng **địa chỉ IP** gửi request tới; giới hạn theo user-id nghĩa là bộ đếm được tính riêng cho từng **tài khoản đã xác thực** (dựa trên claim trong JWT hoặc cookie session), bất kể tài khoản đó gọi từ IP nào.

Cách chọn "partition key" (khoá phân vùng bộ đếm) bằng `PartitionedRateLimiter`:

```csharp title="Program.cs"
// test:compile phan biet gioi han theo IP (chua dang nhap) va theo user-id (da dang nhap)
using System.Threading.RateLimiting;

var builder = WebApplication.CreateBuilder(args);

builder.Services.AddRateLimiter(options =>
{
    // Endpoint dang nhap: CHUA co user-id (dang co gang dang nhap) -> phai gioi han theo IP.
    options.AddPolicy("login-by-ip", httpContext =>
    {
        var ip = httpContext.Connection.RemoteIpAddress?.ToString() ?? "unknown";
        return RateLimitPartition.GetFixedWindowLimiter(ip, _ => new FixedWindowRateLimiterOptions
        {
            PermitLimit = 5,
            Window = TimeSpan.FromMinutes(1)
        });
    });

    // Endpoint da dang nhap: dung user-id lam khoa -> moi user co bo dem rieng, khong bi anh huong
    // boi nguoi khac dung chung IP (vi du nhieu nhan vien trong cung mot cong ty, cung NAT/IP).
    options.AddPolicy("api-by-user", httpContext =>
    {
        var userId = httpContext.User.FindFirst("sub")?.Value ?? "anonymous";
        return RateLimitPartition.GetFixedWindowLimiter(userId, _ => new FixedWindowRateLimiterOptions
        {
            PermitLimit = 100,
            Window = TimeSpan.FromMinutes(1)
        });
    });
});

var app = builder.Build();
app.UseRateLimiter();

app.MapPost("/login", () => "dang nhap").RequireRateLimiting("login-by-ip");
app.MapGet("/me/orders", () => "don hang cua toi").RequireRateLimiting("api-by-user");

app.Run();
```

**Trường hợp trung gian: user-id có nhưng chưa đăng nhập ổn định (ví dụ mobile app dùng device-id).** Một số hệ thống dùng một định danh thiết bị (device-id, sinh ngẫu nhiên khi cài app lần đầu, lưu trong local storage) làm khoá phân vùng thay cho cả IP và user-id, đặc biệt cho các endpoint được gọi trước khi người dùng đăng nhập (ví dụ xem danh sách sản phẩm công khai trên app di động). Cách này tránh được nhược điểm NAT chung của giới hạn theo IP (mỗi thiết bị có device-id riêng dù dùng chung wifi), nhưng đổi lại yêu cầu client phải sinh và gửi kèm device-id ổn định ở mọi request — nếu client không tuân thủ đúng (ví dụ tạo device-id mới mỗi lần khởi động app), giới hạn theo device-id trở nên vô nghĩa vì mỗi request lại có một khoá khác nhau.

**Khi nào dùng loại nào:**

- **Theo IP:** dùng cho endpoint **chưa xác thực được ai đang gọi** — điển hình là `/login`, `/register`, `/forgot-password` (chính client đang cố chứng minh danh tính, nên chưa có user-id đáng tin để dùng làm khoá). Nhược điểm: nhiều người dùng hợp lệ đứng sau cùng một IP công cộng (NAT của công ty, wifi quán cà phê) sẽ **chia sẻ chung một bộ đếm**, một người dùng gọi nhiều có thể khiến đồng nghiệp cùng IP bị chặn oan.
- **Theo user-id:** dùng cho endpoint **đã xác thực** (có JWT/session hợp lệ) — mỗi tài khoản có bộ đếm riêng, công bằng hơn vì không bị ảnh hưởng bởi người khác dùng chung mạng. Nhược điểm: không áp dụng được cho request chưa đăng nhập, và nếu một tài khoản bị chiếm quyền, kẻ tấn công vẫn được hưởng nguyên hạn mức của tài khoản đó cho tới khi bị phát hiện.

**Điều gì xảy ra khi dùng sai:** nếu bạn áp dụng giới hạn theo **user-id** cho endpoint `/login`, kẻ tấn công brute-force chỉ cần đổi username thử ở mỗi lần gọi (không có user-id cố định để giới hạn, vì chưa đăng nhập thành công) — giới hạn theo user-id ở đây **hoàn toàn không có hiệu lực** chống brute-force, vì kẻ tấn công không bị ràng buộc vào bất kỳ user-id nào cả. Đây là lý do endpoint đăng nhập bắt buộc phải giới hạn theo IP (hoặc theo username đang thử, một biến thể khác), không phải theo user-id.

Một biến thể đáng cân nhắc cho `/login`: giới hạn theo **cặp (IP, username đang thử)** thay vì chỉ theo IP đơn thuần. Cách này giảm rủi ro chặn oan nhiều người dùng hợp lệ đứng sau cùng NAT (vì mỗi cặp IP+username có bộ đếm riêng), đồng thời vẫn chặn được kẻ tấn công dò nhiều mật khẩu cho **cùng một username** từ cùng một IP. Tuy vậy cách này không chặn được kẻ tấn công dò **nhiều username khác nhau** từ cùng một IP (credential stuffing) — trường hợp đó vẫn cần thêm một giới hạn theo IP thuần ở mức lỏng hơn, chạy song song.

---

## 9. So sánh 4 thuật toán: chọn đúng công cụ cho đúng bài toán

Sau khi đã hiểu riêng lẻ từng thuật toán (mục 3-6), phần này không giới thiệu khái niệm mới — chỉ tổng hợp lại để chọn nhanh khi thiết kế thực tế, tránh nhầm lẫn giữa các lựa chọn có vẻ tương tự nhau ở bề ngoài. Bảng dưới đây liệt kê lại 4 thuật toán theo cùng thứ tự đã học:

| Thuật toán | Đơn vị đo | Ưu điểm chính | Nhược điểm chính | Ví dụ tình huống phù hợp |
|---|---|---|---|---|
| Fixed Window | Số request / khung thời gian cố định | Đơn giản, nhẹ, tốn ít bộ nhớ (một bộ đếm/khoá) | Dồn cục ở ranh giới khung (có thể gấp đôi giới hạn thực tế trong thời gian ngắn) | Giới hạn chung cho toàn API khi sai số nhỏ chấp nhận được |
| Sliding Window | Số request / khung trượt liên tục | Chính xác hơn ở ranh giới, không cho dồn cục | Tốn nhiều bộ nhớ/tính toán hơn (nhiều segment) | API tính phí theo lượt gọi, cần độ chính xác cao |
| Token Bucket | Token tích luỹ + tốc độ nạp lại | Cho phép burst ngắn hạn hợp lý, phản ánh hành vi người dùng thực tế | Cấu hình phức tạp hơn (2 tham số: dung lượng giỏ + tốc độ nạp) | Tìm kiếm, gõ phím nhanh, hành vi tự nhiên dồn cục |
| Concurrency Limiter | Số request đang xử lý song song | Bảo vệ đúng tài nguyên xử lý đồng thời (CPU, kết nối), không phụ thuộc thời gian | Không giới hạn được tổng số lần gọi trong ngày | Export báo cáo, xử lý ảnh, gọi API ngoài giới hạn kết nối |

Ba thuật toán đầu (Fixed Window, Sliding Window, Token Bucket) đều trả lời câu hỏi **"trong một khoảng thời gian, được gọi tối đa bao nhiêu lần?"** — khác nhau ở cách đo khoảng thời gian đó chính xác đến đâu. Concurrency Limiter trả lời một câu hỏi hoàn toàn khác: **"ngay lúc này, có tối đa bao nhiêu request được phép chạy song song?"**. Vì hai nhóm câu hỏi khác nhau, chúng không loại trừ nhau — một endpoint xử lý nặng có thể cần **cả hai**: Fixed Window để giới hạn tổng lượt gọi/ngày, và Concurrency Limiter để giới hạn số worker chạy song song tại một thời điểm.

Một câu hỏi thường gặp khi mới học: "vậy mặc định nên chọn thuật toán nào nếu chưa chắc?" Câu trả lời thực tế: bắt đầu với **Fixed Window** cho hầu hết endpoint thông thường (đơn giản, đủ dùng, dễ giải thích cho đồng nghiệp), chỉ chuyển sang Sliding Window khi đã đo được vấn đề dồn cục ở ranh giới khung gây hậu quả thật (ví dụ khách hàng phàn nàn bị tính phí sai do gọi vượt hạn mức ở ranh giới), chuyển sang Token Bucket khi hành vi người dùng thực tế rõ ràng có tính dồn cục tự nhiên (tìm kiếm, gõ phím), và luôn cân nhắc thêm Concurrency Limiter song song bất cứ khi nào endpoint chạy tác vụ nặng, tốn tài nguyên xử lý lâu — không phải để thay thế giới hạn theo thời gian, mà để bổ sung lớp bảo vệ tài nguyên đồng thời mà ba thuật toán kia không đảm nhiệm được.

Kết hợp nhiều policy cho cùng một endpoint được thực hiện bằng cách gọi liên tiếp nhiều lần `.RequireRateLimiting` trên cùng một endpoint (ASP.NET Core áp dụng tất cả policy được liệt kê, request phải vượt qua toàn bộ):

```csharp title="Program.cs"
// test:compile ket hop 2 loai policy khac nhau cho CUNG mot endpoint: gioi han theo ngay + gioi han dong thoi
using System.Threading.RateLimiting;
using Microsoft.AspNetCore.RateLimiting;

var builder = WebApplication.CreateBuilder(args);

builder.Services.AddRateLimiter(options =>
{
    // Gioi han theo thoi gian: toi da 50 lan export/ngay cho toan server (don gian hoa, khong phan vung theo user).
    options.AddFixedWindowLimiter("export-daily", limiterOptions =>
    {
        limiterOptions.PermitLimit = 50;
        limiterOptions.Window = TimeSpan.FromDays(1);
    });

    // Gioi han dong thoi: toi da 4 export CHAY SONG SONG tai mot thoi diem.
    options.AddConcurrencyLimiter("export-concurrent", limiterOptions =>
    {
        limiterOptions.PermitLimit = 4;
        limiterOptions.QueueLimit = 10;
    });
});

var app = builder.Build();
app.UseRateLimiter();

app.MapGet("/reports/export", async () =>
{
    await Task.Delay(TimeSpan.FromSeconds(8));
    return "bao cao da xuat";
})
   .RequireRateLimiting("export-daily")
   .RequireRateLimiting("export-concurrent"); // ca hai policy deu phai duoc thoa man

app.Run();
```

**Điều gì xảy ra khi dùng sai:** nếu bạn nghĩ chỉ cần MỘT trong hai policy trên là đủ, hai rủi ro khác nhau vẫn còn nguyên: chỉ dùng `export-daily` (Fixed Window) không ngăn được 50 người dùng cùng bấm export **đồng thời trong một giây** (server vẫn sập vì tài nguyên xử lý song song, dù tổng số lượt/ngày vẫn trong hạn mức 50); chỉ dùng `export-concurrent` (Concurrency Limiter) không ngăn được một người dùng export liên tục 500 lần trong ngày miễn là họ chờ mỗi lần export cũ hoàn tất trước khi gọi lần mới (không có giới hạn tổng số lượt/ngày). Cần cả hai để bảo vệ đúng cả hai loại rủi ro.

---

## Cạm bẫy & thực chiến

- **Quên gọi `app.UseRateLimiter()`:** đăng ký policy trong `AddRateLimiter` không tự động bật middleware — thiếu dòng `app.UseRateLimiter()` khiến toàn bộ rate limiting bị bỏ qua âm thầm, không có exception, request nào cũng lọt qua.
- **Quên gắn `.RequireRateLimiting("ten-policy")` cho endpoint:** định nghĩa policy xong nhưng không gán vào endpoint cụ thể nghĩa là endpoint đó không bị giới hạn gì cả — mỗi policy chỉ có hiệu lực ở nơi được gán rõ ràng.
- **Dùng Fixed Window cho endpoint nhạy cảm về chính xác (API trả phí theo lượt gọi cho khách hàng):** lỗ hổng dồn cục ở ranh giới khung (mục 3) có thể cho phép khách hàng gọi gấp đôi hạn mức trong thời gian ngắn quanh ranh giới khung — dùng Sliding Window nếu độ chính xác quan trọng.
- **Nhầm giới hạn theo IP là đủ để chống brute-force khi client đứng sau NAT chung:** nhiều công ty/trường học/ISP dùng NAT khiến hàng trăm người dùng chia sẻ một IP công cộng — giới hạn quá chặt theo IP có thể chặn oan người dùng hợp lệ; cần cân nhắc kết hợp thêm giới hạn theo username đang thử đăng nhập.
- **Nhầm Concurrency Limiter với Fixed Window:** Concurrency Limiter không đếm theo thời gian, nó đếm số request **đang chạy song song ngay lúc này**. Dùng nhầm Fixed Window cho một endpoint xử lý nặng (ví dụ export báo cáo) không bảo vệ được server nếu 5 request được phép trong khung đều là request chạy lâu và chạy chồng lên nhau — cần Concurrency Limiter để giới hạn đúng tài nguyên (số worker xử lý đồng thời).
- **Không trả `Retry-After` khi trả 429:** khiến client tự động retry ngay lập tức, làm nặng thêm chính vấn đề tải mà rate limiting đang cố ngăn.
- **Đặt `PermitLimit` quá thấp cho một API nội bộ được nhiều service khác gọi liên tục (service-to-service):** nếu nhiều microservice trong cùng hệ thống gọi qua chung một API Gateway và tất cả bị tính chung vào một bộ đếm IP (vì đứng sau NAT nội bộ hoặc cùng load balancer), một service gọi nhiều có thể khiến các service khác bị 429 oan — cần cân nhắc giới hạn theo API key hoặc service-id riêng cho traffic nội bộ, tách biệt khỏi traffic từ người dùng cuối.
- **Test policy rate limit bằng cách gọi tay từng request một, chờ giữa các lần gọi:** cách này không bao giờ chạm ngưỡng giới hạn thật, vì mỗi lần gọi cách nhau vài giây do người kiểm thử gõ lệnh — phải viết test tự động gọi liên tiếp nhanh (ví dụ vòng lặp `for` gọi `HttpClient` liền nhau) để thực sự kiểm chứng hành vi 429 xảy ra đúng ở request thứ N+1.
- **Giả định bộ đếm rate limit dùng chung được giữa nhiều instance khi scale-out:** `AddRateLimiter` mặc định lưu bộ đếm trong bộ nhớ tiến trình (in-process, giống `IMemoryCache`) — nếu ứng dụng chạy nhiều instance đằng sau load balancer, mỗi instance đếm độc lập, khiến giới hạn thật sự bị nhân lên theo số instance (chi tiết ở phần DEEP DIVE cuối bài). Đừng phát hiện điều này lần đầu khi debug một sự cố production.
- **Đặt `PermitLimit` giống nhau cho mọi endpoint bất kể mức độ nhạy cảm:** endpoint đăng nhập (rủi ro brute-force cao) cần giới hạn chặt hơn nhiều so với endpoint đọc dữ liệu công khai (rủi ro thấp) — dùng một hằng số `PermitLimit` chung cho toàn API bỏ qua sự khác biệt về mức độ rủi ro giữa các endpoint.

---

## Bài tập

**Bài 1 (áp dụng).** Viết policy `AddRateLimiter` giới hạn endpoint `POST /otp/send` (gửi mã OTP qua SMS, mỗi lần gửi tốn tiền) tối đa 3 lần/giờ theo số điện thoại (giả sử số điện thoại được truyền qua query string `?phone=...`), dùng Fixed Window.

??? success "Lời giải + vì sao"
    ```csharp title="Program.cs"
    // test:compile bai 1 - gioi han gui OTP theo so dien thoai, 3 lan/gio
    using System.Threading.RateLimiting;

    var builder = WebApplication.CreateBuilder(args);

    builder.Services.AddRateLimiter(options =>
    {
        options.AddPolicy("otp-by-phone", httpContext =>
        {
            var phone = httpContext.Request.Query["phone"].ToString();
            var key = string.IsNullOrEmpty(phone) ? "unknown" : phone;

            return RateLimitPartition.GetFixedWindowLimiter(key, _ => new FixedWindowRateLimiterOptions
            {
                PermitLimit = 3,
                Window = TimeSpan.FromHours(1)
            });
        });
    });

    var app = builder.Build();
    app.UseRateLimiter();

    app.MapPost("/otp/send", (string phone) => $"da gui OTP toi {phone}")
       .RequireRateLimiting("otp-by-phone");

    app.Run();
    ```

    **Vì sao:** dùng số điện thoại làm khoá phân vùng (không phải IP) vì mục tiêu là chống lạm dụng **chi phí gửi SMS cho một số điện thoại cụ thể**, không phải chống một IP gọi nhiều — kẻ tấn công có thể đổi IP dễ dàng (dùng proxy) nhưng số điện thoại mục tiêu là cố định. Fixed Window đủ dùng ở đây vì sai số nhỏ ở ranh giới khung (ví dụ 6 lần gửi trong 2 giờ thay vì đúng 3 lần/giờ) không gây hậu quả nghiêm trọng như với API tính phí chính xác.

**Bài 2 (thiết kế).** Một endpoint `GET /reports/export` chạy tác vụ nặng (mất 8-10 giây, dùng nhiều CPU để tạo file Excel). Bạn muốn đảm bảo server không bị quá tải nếu nhiều người cùng export đồng thời, nhưng KHÔNG muốn giới hạn số lần một người có thể export trong một khoảng thời gian dài (họ có thể export nhiều lần miễn là không có quá nhiều request chạy song song). Chọn thuật toán nào và vì sao? Viết cấu hình.

??? success "Lời giải + vì sao"
    ```csharp title="Program.cs"
    // test:compile bai 2 - concurrency limiter cho tac vu nang, khong gioi han theo thoi gian
    using System.Threading.RateLimiting;
    using Microsoft.AspNetCore.RateLimiting;

    var builder = WebApplication.CreateBuilder(args);

    builder.Services.AddRateLimiter(options =>
    {
        options.AddConcurrencyLimiter("report-export", limiterOptions =>
        {
            limiterOptions.PermitLimit = 4;  // toi da 4 export chay dong thoi tren toan server
            limiterOptions.QueueLimit = 10;  // them 10 request duoc xep hang cho, qua so nay bi 429
        });
    });

    var app = builder.Build();
    app.UseRateLimiter();

    app.MapGet("/reports/export", async () =>
    {
        await Task.Delay(TimeSpan.FromSeconds(8)); // mo phong tac vu tao file Excel nang
        return Results.File(new byte[] { }, "application/vnd.ms-excel", "report.xlsx");
    })
       .RequireRateLimiting("report-export");

    app.Run();
    ```

    **Vì sao:** yêu cầu đề bài đúng nghĩa là "giới hạn số lượng request đang xử lý đồng thời", không phải "giới hạn số lần gọi trong một khung thời gian" — đây chính là định nghĩa của Concurrency Limiter (mục 6), khác hẳn Fixed/Sliding Window/Token Bucket (đều đếm theo thời gian). Một người dùng có thể export 20 lần trong một ngày (không bị chặn vì thời gian), nhưng nếu tại một thời điểm đã có 4 export khác đang chạy trên toàn server, request thứ 5 phải chờ trong hàng đợi (`QueueLimit`) hoặc bị từ chối nếu hàng đợi cũng đầy.

**Bài 3 (phân biệt IP vs user-id, kết hợp bảng so sánh mục 9).** Một API công khai `GET /api/weather` cho phép cả người dùng chưa đăng nhập (giới hạn nhẹ, 20 request/giờ theo IP) và người dùng đã đăng nhập, trả phí (giới hạn rộng hơn, 1000 request/giờ theo user-id) cùng gọi vào **một endpoint duy nhất**. Thiết kế policy đáp ứng cả hai trường hợp.

??? success "Lời giải + vì sao"
    ```csharp title="Program.cs"
    // test:compile bai 3 - mot endpoint, policy chon khoa khac nhau tuy da dang nhap hay chua
    using System.Threading.RateLimiting;

    var builder = WebApplication.CreateBuilder(args);

    builder.Services.AddRateLimiter(options =>
    {
        options.AddPolicy("weather-tiered", httpContext =>
        {
            var userId = httpContext.User.FindFirst("sub")?.Value;

            if (!string.IsNullOrEmpty(userId))
            {
                // Da dang nhap: gioi han theo user-id, han muc rong hon (da tra phi).
                return RateLimitPartition.GetFixedWindowLimiter($"user:{userId}", _ => new FixedWindowRateLimiterOptions
                {
                    PermitLimit = 1000,
                    Window = TimeSpan.FromHours(1)
                });
            }

            // Chua dang nhap: gioi han theo IP, han muc chat hon (dung thu mien phi).
            var ip = httpContext.Connection.RemoteIpAddress?.ToString() ?? "unknown";
            return RateLimitPartition.GetFixedWindowLimiter($"ip:{ip}", _ => new FixedWindowRateLimiterOptions
            {
                PermitLimit = 20,
                Window = TimeSpan.FromHours(1)
            });
        });
    });

    var app = builder.Build();
    app.UseRateLimiter();

    app.MapGet("/api/weather", () => "du lieu thoi tiet")
       .RequireRateLimiting("weather-tiered");

    app.Run();
    ```

    **Vì sao:** `AddPolicy` cho phép chọn khoá phân vùng **động, dựa trên nội dung request** — ở đây policy kiểm tra `httpContext.User` để quyết định dùng khoá `user:{userId}` (nếu đã đăng nhập) hay `ip:{ip}` (nếu chưa), và mỗi nhóm có hạn mức khác nhau phù hợp với mô hình kinh doanh (miễn phí giới hạn thấp, trả phí giới hạn cao). Tiền tố `user:`/`ip:` trong khoá tránh việc một user-id trùng tình cờ với một chuỗi IP nào đó gây nhiễu bộ đếm giữa hai nhóm.

---

## Tự kiểm tra

1. Rate limiting giải quyết vấn đề gốc nào, với ví dụ cụ thể?

    ??? note "Đáp án"
        Ngăn một client gọi API quá nhiều lần trong thời gian ngắn, gây quá tải server (CPU, database, băng thông) hoặc lạm dụng logic nghiệp vụ — ví dụ cụ thể: brute-force dò mật khẩu ở endpoint đăng nhập bằng cách thử hàng nghìn tổ hợp mật khẩu liên tục.

2. Phải gọi thêm phương thức nào ngoài `AddRateLimiter` để middleware thực sự hoạt động, và điều gì xảy ra nếu quên?

    ??? note "Đáp án"
        Phải gọi `app.UseRateLimiter()`. Nếu quên, các policy đã đăng ký không có hiệu lực — mọi request đều lọt qua như không có rate limiting nào tồn tại, không có exception hay cảnh báo nào báo lỗi này.

3. Fixed Window và Sliding Window khác nhau ở điểm nào, và tại sao Sliding Window "chính xác hơn" ở ranh giới thời gian?

    ??? note "Đáp án"
        Fixed Window reset bộ đếm về 0 mỗi khi bắt đầu khung mới, khiến client có thể gửi gấp đôi giới hạn trong khoảng thời gian ngắn quanh ranh giới hai khung (ví dụ 100 request vào cuối khung 1 và 100 request vào đầu khung 2, tổng 200 request trong vài giây). Sliding Window chia khung lớn thành nhiều segment nhỏ và tính tổng có trọng số các segment gần nhất, phản ánh đúng số request trong bất kỳ khoảng 60 giây liên tục nào, không chỉ theo ranh giới khung cố định.

4. Token Bucket khác Fixed/Sliding Window ở điểm cốt lõi nào?

    ??? note "Đáp án"
        Token Bucket cho phép client "tích trữ" token khi không gọi, rồi xả hết một lúc thành một loạt request dồn (burst) ngay lập tức nếu giỏ đang đầy — miễn là tốc độ trung bình lâu dài không vượt tốc độ nạp lại token. Fixed/Sliding Window giới hạn cứng tổng số request trong mỗi khung, không cho phép "tích trữ" từ khung trước sang khung sau.

5. Concurrency Limiter khác biệt về bản chất thế nào so với ba thuật toán còn lại?

    ??? note "Đáp án"
        Ba thuật toán khác (Fixed Window, Sliding Window, Token Bucket) đều đếm số request theo THỜI GIAN. Concurrency Limiter không quan tâm thời gian — nó giới hạn số lượng request ĐANG được xử lý đồng thời tại một thời điểm; một request chạy lâu vẫn chỉ chiếm một slot suốt thời gian chạy, bất kể có bao nhiêu request khác gọi trước hoặc sau nó.

6. Status code 429 nghĩa là gì, và header `Retry-After` dùng để làm gì?

    ??? note "Đáp án"
        429 Too Many Requests báo cho client biết request bị từ chối vì vượt quá giới hạn tốc độ (không phải lỗi dữ liệu hay lỗi server). Header `Retry-After` cho client biết nên chờ bao nhiêu giây trước khi gọi lại, giúp tránh client retry ngay lập tức và làm nặng thêm vấn đề tải.

7. Vì sao endpoint `/login` phải giới hạn theo IP (hoặc theo username đang thử) chứ không thể giới hạn theo user-id?

    ??? note "Đáp án"
        Vì tại thời điểm gọi `/login`, hệ thống chưa xác thực được người gọi là ai — chưa có user-id đáng tin cậy để dùng làm khoá phân vùng. Kẻ tấn công brute-force chưa đăng nhập thành công lần nào, nên giới hạn theo user-id sẽ không có hiệu lực chống lại kiểu tấn công này.

8. Nhược điểm của giới hạn theo IP là gì, và khi nào giới hạn theo user-id khắc phục được nhược điểm đó?

    ??? note "Đáp án"
        Nhiều người dùng hợp lệ có thể đứng sau cùng một địa chỉ IP công cộng (NAT của công ty, wifi chung), khiến họ chia sẻ chung một bộ đếm — một người gọi nhiều có thể khiến người khác cùng IP bị chặn oan. Giới hạn theo user-id khắc phục được vì mỗi tài khoản đã xác thực có bộ đếm riêng, không phụ thuộc vào IP nguồn, nhưng chỉ áp dụng được cho endpoint đã đăng nhập.

9. Một endpoint export báo cáo cần vừa giới hạn tổng số lần gọi/ngày, vừa giới hạn số request chạy song song tại một thời điểm. Có thể dùng một thuật toán duy nhất để đáp ứng cả hai yêu cầu này không? Vì sao?

    ??? note "Đáp án"
        Không. Bốn thuật toán trả lời hai loại câu hỏi khác nhau: Fixed Window/Sliding Window/Token Bucket trả lời "trong một khoảng thời gian, được gọi bao nhiêu lần?", còn Concurrency Limiter trả lời "ngay lúc này, có bao nhiêu request đang chạy song song?". Đáp ứng cả hai yêu cầu cần kết hợp **hai policy khác loại** — ví dụ Fixed Window cho giới hạn theo ngày và Concurrency Limiter cho giới hạn đồng thời — không có thuật toán đơn lẻ nào phủ được cả hai khái niệm.

10. Khi một endpoint được gán hai policy khác loại qua hai lần gọi `.RequireRateLimiting` liên tiếp (ví dụ Fixed Window + Concurrency Limiter ở mục 9), request phải thoả điều kiện nào để được xử lý?

    ??? note "Đáp án"
        Request phải vượt qua **cả hai** policy — ASP.NET Core áp dụng tất cả policy được liệt kê qua các lần gọi `.RequireRateLimiting`, không phải chỉ một trong số đó. Nếu request vượt quá giới hạn của bất kỳ policy nào (ví dụ đã hết hạn mức Fixed Window theo ngày, hoặc đã đủ số request chạy đồng thời của Concurrency Limiter), request đó bị từ chối (429), bất kể policy còn lại có còn hạn mức hay không.

11. Trả `403 Forbidden` khi client vượt giới hạn tốc độ có đúng ngữ nghĩa HTTP không? Vì sao?

    ??? note "Đáp án"
        Không đúng. `403` nghĩa là client bị từ chối vĩnh viễn cho request này vì không có quyền, còn `429` nghĩa là request hợp lệ và được phép nhưng đến quá sớm — client có thể thử lại thành công sau khi chờ đúng thời gian. Dùng nhầm `403` khiến client (và người debug) hiểu sai rằng họ không bao giờ được phép gọi endpoint đó, thay vì chỉ cần chờ và thử lại.

---

??? abstract "DEEP DIVE: kết hợp rate limiting với caching, và giới hạn toàn cục (global limiter)"
    Rate limiting và caching (chương trước) thường đi cùng nhau trong thiết kế phòng thủ API: nếu một endpoint đọc dữ liệu tốn kém (query database phức tạp) được cache lại (ví dụ qua `IMemoryCache` hoặc distributed cache), rate limiting vẫn cần thiết vì nó bảo vệ **trước khi** request chạm tới logic cache-hay-không — một client gọi 10.000 request/giây vẫn tiêu tốn CPU để xử lý request, kiểm tra cache, và trả response, dù mọi request đều là cache hit. Rate limiting chặn ở tầng ngoài cùng của pipeline (trước khi vào logic nghiệp vụ), còn caching tối ưu hoá phần logic nghiệp vụ đó — hai kỹ thuật bổ trợ, không thay thế nhau.

    Ngoài các policy gán riêng cho từng endpoint qua `.RequireRateLimiting`, `AddRateLimiter` còn hỗ trợ `options.GlobalLimiter` — một giới hạn áp dụng cho **toàn bộ request** vào ứng dụng, bất kể endpoint nào, thường dùng làm lớp bảo vệ cuối cùng chống các cuộc tấn công tổng thể (ví dụ giới hạn 10.000 request/giây cho toàn server, bất kể phân bổ giữa các endpoint):

    ```csharp title="Program.cs"
    // test:compile global limiter - lop bao ve cuoi cung cho toan bo ung dung
    using System.Threading.RateLimiting;

    var builder = WebApplication.CreateBuilder(args);

    builder.Services.AddRateLimiter(options =>
    {
        options.GlobalLimiter = PartitionedRateLimiter.Create<HttpContext, string>(httpContext =>
        {
            var ip = httpContext.Connection.RemoteIpAddress?.ToString() ?? "unknown";
            return RateLimitPartition.GetFixedWindowLimiter(ip, _ => new FixedWindowRateLimiterOptions
            {
                PermitLimit = 1000,
                Window = TimeSpan.FromMinutes(1)
            });
        });
    });

    var app = builder.Build();
    app.UseRateLimiter();

    app.MapGet("/", () => "OK");

    app.Run();
    ```

    Global limiter và named policy (`.RequireRateLimiting`) hoạt động **độc lập và cộng dồn** — một request phải vượt qua CẢ HAI để được xử lý: nếu endpoint có policy riêng giới hạn 100/phút VÀ global limiter giới hạn 1000/phút theo IP, request bị chặn nếu vượt bất kỳ giới hạn nào trong hai giới hạn đó, tuỳ giới hạn nào chặt hơn với tình huống cụ thể. Thiết kế phân lớp này (global limiter lỏng hơn, làm lớp bảo vệ tổng thể; named policy chặt hơn ở từng endpoint nhạy cảm) là mẫu hình phổ biến trong hệ thống production.

    **Kiểm thử rate limiter đúng cách:** một sai lầm phổ biến khi viết test là gọi endpoint vài lần rồi kỳ vọng thấy 429 ngay, nhưng nếu test chạy tuần tự với độ trễ (ví dụ do log hoặc I/O giữa các lần gọi), có thể chưa bao giờ chạm ngưỡng `PermitLimit` thật. Cách kiểm thử đáng tin cậy hơn là gọi **liên tiếp không chờ** bằng cách tạo nhiều `Task` cùng lúc rồi `Task.WhenAll`, để đảm bảo các request thực sự nằm trong cùng một khung/giỏ token khi tính giới hạn:

    ```csharp title="RateLimiterTests.cs"
    // test:skip vi du minh hoa cach kiem thu, can WebApplicationFactory (goi ngoai pham vi bai nay)
    var client = factory.CreateClient();

    var tasks = Enumerable.Range(0, 10)
        .Select(_ => client.GetAsync("/data"))
        .ToArray();

    var responses = await Task.WhenAll(tasks);

    var tooManyRequestsCount = responses.Count(r => r.StatusCode == System.Net.HttpStatusCode.TooManyRequests);
    // Voi PermitLimit = 5, ky vong it nhat 5 response la 429.
    Assert.True(tooManyRequestsCount >= 5);
    ```

    **Lưu ý khi đọc kết quả test kiểu `Task.WhenAll`:** vì các request gửi đồng thời có thể tới middleware rate limiter theo thứ tự không hoàn toàn xác định (phụ thuộc lịch trình của thread pool), số lượng response chính xác là 429 so với 200 có thể lệch đi một chút giữa các lần chạy test (ví dụ 5 hoặc 6 response 429 trong 10 request, thay vì luôn đúng 5) — đây là lý do assertion nên dùng `>=` (ít nhất N response bị chặn) thay vì `==` (chính xác N), để test không bị "flaky" (đôi khi pass đôi khi fail) do sai khác nhỏ về thời điểm thực thi, vốn không phải lỗi của rate limiter.

    Ngoài `AddRateLimiter` (tích hợp sẵn với middleware ASP.NET Core), namespace `System.Threading.RateLimiting` còn cung cấp các lớp `RateLimiter` (ví dụ `FixedWindowRateLimiter`, `TokenBucketRateLimiter`) có thể dùng **độc lập, không cần middleware** — hữu ích khi bạn cần giới hạn tốc độ cho một tác vụ nội bộ không liên quan tới HTTP request, ví dụ giới hạn số lần một `BackgroundService` gọi ra một API bên ngoài mỗi phút. Việc `AddRateLimiter` chỉ là lớp tích hợp các `RateLimiter` này vào pipeline HTTP giúp giải thích vì sao cả 4 thuật toán đều có sẵn ngay trong BCL (Base Class Library) của .NET mà không cần cài thêm package nào.

    **Giới hạn quan trọng cần biết trước khi triển khai thật: bộ đếm của `AddRateLimiter` mặc định là in-process — giống hệt vấn đề của `IMemoryCache` đã học ở chương trước.** Mỗi bộ đếm (Fixed Window, Sliding Window, Token Bucket, hay slot của Concurrency Limiter) được lưu **trong bộ nhớ của tiến trình ứng dụng**, không dùng chung được giữa nhiều instance. Hậu quả cụ thể: nếu bạn deploy ứng dụng với 3 instance chạy song song đằng sau một load balancer (một kiến trúc scale-out rất phổ biến), và policy giới hạn "5 request/10 giây" cho một client, thì client đó thực tế có thể gọi **tới 15 request/10 giây** (5 request lọt qua mỗi instance, vì mỗi instance đếm độc lập, không biết instance khác đã đếm bao nhiêu) — giới hạn thật sự bị nhân lên theo số instance, dù cấu hình "trông có vẻ đúng".

    Để giới hạn đúng nghĩa **trên toàn cụm** (tổng số request cộng dồn từ mọi instance), bộ đếm phải được lưu ở một nơi **dùng chung được giữa các instance** — đây chính là vai trò của distributed cache (ví dụ Redis) đã học ở chương caching: thay vì mỗi instance giữ bộ đếm riêng trong bộ nhớ, tất cả instance cùng đọc/ghi một bộ đếm duy nhất lưu trên Redis. .NET không có sẵn một `AddRateLimiter` tích hợp Redis trong BCL — cần dùng thư viện ngoài (ví dụ các thư viện community implement `PartitionedRateLimiter` backed bởi Redis) để đạt được rate limiting phân tán thực sự chính xác trên nhiều instance.

Tiếp theo -> health checks: phân biệt live và ready
