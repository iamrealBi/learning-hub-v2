---
tier: core
status: core
owner: core-team
verified_on: "2026-07-05"
dotnet_version: "10.0"
bloom: áp dụng
requires: [p8-health]
est_minutes_fast: 26
---

# Background Jobs: IHostedService & BackgroundService

!!! info "bạn đang ở đây"
    cần trước: bạn đã biết health check phân biệt Live/Ready (app còn chạy khác app sẵn sàng nhận traffic) và biết `builder.Services` là gì.
    mở khoá: chạy được một tác vụ tốn thời gian (gửi email, xử lý file lớn, dọn dữ liệu định kỳ) mà không chặn request HTTP nào, và biết tắt tác vụ đó đúng cách khi app shutdown — nền tảng để sau này ghép với message queue thực sự (đã học ở P6) làm hệ thống xử lý nền hoàn chỉnh.

> **Mục tiêu (đo được):** sau chương này bạn **giải thích** được vì sao một request HTTP không nên tự làm việc tốn thời gian; **áp dụng** đúng `BackgroundService` để chạy một worker nền; **tôn trọng** `CancellationToken` để app tắt đúng lúc, không bị "treo"; **đăng ký** worker qua `AddHostedService<T>()`; và **phân biệt** được hàng đợi trong-tiến-trình (`Channel<T>`) với message queue thực sự (RabbitMQ/Azure Service Bus).

---

## 0. Đoán nhanh trước khi học

Một endpoint xử lý đăng ký người dùng mới như sau:

```csharp title="Endpoint.cs"
// test:skip minh hoa loi thiet ke (khong phai chuong trinh day du), phan tich o muc 1
app.MapPost("/register", async (RegisterRequest request, IEmailSender emailSender) =>
{
    // 1. Luu user vao database (gia lap, luon thanh cong o day)
    var userId = 42;

    // 2. Gui email chao mung - gia su viec nay ton 4-6 giay (SMTP cham, hoac API email ngoai cham).
    await emailSender.SendWelcomeEmailAsync(userId);

    return Results.Ok(new { userId });
});
```

Người dùng bấm "Đăng ký" và phải đợi 5-6 giây mới thấy trang tiếp theo hiện ra, dù tài khoản của họ đã được tạo thành công ngay từ bước 1. Tệ hơn, vào giờ cao điểm, một số request `/register` bắt đầu trả lỗi timeout dù database hoàn toàn khỏe mạnh. Vì sao?

??? question "Đoán trước, đáp án ở dưới"
    Gợi ý: nghĩ về việc request HTTP có một giới hạn thời gian chờ (timeout) mặc định, và việc "gửi email" có liên quan gì đến việc "tài khoản đã tạo thành công" hay không.

??? note "Đáp án"
    Request `/register` đang **chờ đồng bộ** cho một việc không cần thiết phải hoàn tất ngay: gửi email. Việc tạo tài khoản (bước 1) đã xong, nhưng client vẫn phải đợi bước 2 (gửi email, 4-6 giây) trước khi nhận được response. Nếu server SMTP hoặc API email bên ngoài chậm hơn bình thường (ví dụ 15-20 giây), request sẽ chạm timeout mặc định của trình duyệt/reverse proxy (thường 30-100 giây tùy cấu hình) và trả lỗi — dù tài khoản **đã** được tạo thành công. Mục 1 phân tích cụ thể vấn đề này, và mục 2-3 giới thiệu `IHostedService`/`BackgroundService` — cách chạy việc gửi email này **nền**, không chặn request.

---

## 1. Vấn đề gốc: việc tốn thời gian không nên chặn request HTTP

**Định nghĩa:** một request HTTP là một cuộc trao đổi có giới hạn thời gian — client gửi request, chờ response, và cả client (trình duyệt, ứng dụng mobile) lẫn các thành phần hạ tầng ở giữa (reverse proxy, load balancer) đều áp một khoảng timeout; nếu server giữ request quá lâu để làm một việc **không cần hoàn tất ngay** mới trả response, request đó sẽ chậm không cần thiết hoặc bị hủy giữa đường.

Quan sát lại ví dụ ở mục 0: request `/register` có hai việc rất khác nhau về bản chất.

- **Việc 1 — lưu user vào database:** đây là việc **client cần biết kết quả ngay** (tài khoản có tạo được hay không, để hiển thị đúng cho người dùng).
- **Việc 2 — gửi email chào mừng:** đây là việc **client không cần biết kết quả ngay**. Người dùng không cần đợi email gửi xong mới được chuyển sang trang tiếp theo — họ chỉ cần biết tài khoản đã tạo, email sẽ tới sau vài giây/vài phút cũng không sao.

**Điều gì xảy ra khi dùng sai (hậu quả cụ thể):** khi việc 2 bị làm **đồng bộ** trong request như ví dụ mục 0:

```text title="Hậu quả thực tế khi request timeout giữa lúc chờ gửi email"
Request /register nhận lúc 10:00:00.000
--> Lưu user thành công lúc 10:00:00.050 (50ms)
--> Gọi SendWelcomeEmailAsync(), API email ngoài đang chậm bất thường (15 giây)
--> Reverse proxy (timeout 30s) hoặc client (timeout 10-20s tùy app) HỦY request lúc 10:00:15
--> Người dùng thấy lỗi "Request timeout" / màn hình trắng
--> NHƯNG tài khoản đã tạo thành công từ 10:00:00.050 - người dùng KHÔNG biết,
    có thể bấm "Đăng ký" lại -> tạo tài khoản trùng (nếu thiếu kiểm tra) hoặc gặp lỗi
    "email đã tồn tại" gây khó hiểu.
```

Đây là hậu quả production cụ thể: **thời gian phản hồi của cả hệ thống bị kéo dài bởi một việc phụ**, và khi việc phụ đó (gọi ra ngoài, gửi email, xử lý file) chậm bất thường, nó có thể làm **cả những request không liên quan** cũng bị ảnh hưởng — vì thread xử lý request đó bị giữ lại (không trả về pool) suốt thời gian chờ, dưới tải cao, số thread bị giữ tăng dần có thể làm cạn resource xử lý của toàn ứng dụng.

Vấn đề còn tồi tệ hơn khi nhìn ở quy mô: giả sử API email bên ngoài bình thường phản hồi trong 200ms, nhưng đang gặp sự cố tạm thời và chậm tới 10 giây cho **mọi** request. Nếu ứng dụng của bạn nhận 100 request `/register` mỗi giây trong lúc đó, sẽ có tới `100 requests/giây × 10 giây = 1000` request đang cùng lúc "kẹt" chờ email — mỗi request giữ một thread xử lý trong suốt 10 giây đó. Với số thread có sẵn trong thread pool là hữu hạn, tình huống này nhanh chóng dẫn tới **thread pool exhaustion** (cạn thread xử lý) — không chỉ request `/register` bị ảnh hưởng, mà **mọi endpoint khác** của ứng dụng (kể cả những endpoint không liên quan gì tới email) cũng bắt đầu chậm hoặc treo, vì không còn thread rỗi nào để xử lý chúng. Đây là lý do một sự cố nhỏ ở một dịch vụ phụ (email) có thể lan ra thành sự cố toàn hệ thống nếu không tách việc phụ đó ra khỏi luồng xử lý request chính.

Cách giải quyết đúng: **tách việc 2 ra khỏi vòng đời của request** — request chỉ cần "giao việc" rồi trả response ngay, việc thật sự được một tiến trình khác (chạy nền, bên trong cùng ứng dụng) xử lý sau. Đây chính là vai trò của `IHostedService` và `BackgroundService`.

---

## 2. `IHostedService` là gì

**Định nghĩa:** `IHostedService` là một interface trong ASP.NET Core định nghĩa hai phương thức — `StartAsync(CancellationToken)` và `StopAsync(CancellationToken)` — mà **chính .NET tự động gọi** đúng lúc: `StartAsync` được gọi khi ứng dụng khởi động (ngay sau khi pipeline sẵn sàng), và `StopAsync` được gọi khi ứng dụng bắt đầu tắt (shutdown) — bạn không tự gọi hai phương thức này, host của ASP.NET Core quản lý vòng đời đó.

```csharp title="C#"
// test:compile Web SDK tran - dinh nghia y interface IHostedService (khong tu viet lai, .NET co san)
public interface IHostedService
{
    Task StartAsync(CancellationToken cancellationToken);
    Task StopAsync(CancellationToken cancellationToken);
}
```

Đây chỉ là **hình dạng interface có sẵn** trong `Microsoft.Extensions.Hosting` (đã có sẵn trong Web SDK, không cần cài package ngoài) — bạn không cần copy đoạn trên vào code của mình, nó chỉ để thấy rõ interface có đúng hai phương thức nào.

Một chi tiết quan trọng của cách host quản lý `IHostedService`: mọi class đăng ký kiểu này được host coi là có lifetime tương đương **Singleton** — nghĩa là host chỉ tạo **đúng một** instance của class đó, dùng nó suốt vòng đời ứng dụng (từ `StartAsync` tới `StopAsync`), không tạo instance mới cho mỗi request như các service `Scoped` bạn thường thấy trong endpoint. Đây là điểm cần nhớ khi worker của bạn cần dùng tới các service khác chỉ tồn tại trong phạm vi một request (như `DbContext` của Entity Framework Core) — deep dive cuối chương giải thích cách xử lý đúng tình huống này qua `IServiceScopeFactory`.

**Điều gì xảy ra khi dùng sai:** nếu bạn tự implement trực tiếp `IHostedService` (thay vì dùng `BackgroundService` ở mục 3), bạn phải tự viết logic quản lý một vòng lặp nền bên trong `StartAsync` — nhưng `StartAsync` **phải trả về nhanh** (không block), vì .NET chờ `StartAsync` hoàn tất trước khi coi ứng dụng đã khởi động xong. Nếu vô tình viết `StartAsync` chạy một vòng lặp `while (true)` vô hạn ngay trong thân của nó (không tách task riêng), ứng dụng sẽ **treo ngay lúc khởi động**, không bao giờ tới được trạng thái sẵn sàng nhận request — đây là lý do hầu như không ai tự implement `IHostedService` trực tiếp; mục 3 giới thiệu `BackgroundService`, lớp trừu tượng đã xử lý đúng chi tiết này sẵn.

---

## 3. `BackgroundService`: lớp trừu tượng tiện lợi hơn

**Định nghĩa:** `BackgroundService` là một lớp trừu tượng (abstract class) có sẵn trong .NET, đã cài đặt đúng `IHostedService` cho bạn — nó tự chạy phương thức `ExecuteAsync(CancellationToken)` (bạn override) trong một Task riêng ngay khi `StartAsync` được gọi, và `StartAsync` trả về **ngay lập tức** (không đợi `ExecuteAsync` chạy xong) — nhờ vậy bạn chỉ cần viết vòng lặp nền bên trong `ExecuteAsync` mà không phải tự lo việc "không được block `StartAsync`" như mục 2 đã cảnh báo.

Ví dụ tối thiểu — một worker log ra console mỗi 10 giây:

```csharp title="C#"
// test:compile Web SDK tran - BackgroundService toi thieu, log moi 10 giay
using Microsoft.Extensions.Hosting;

public class HeartbeatWorker : BackgroundService
{
    private readonly ILogger<HeartbeatWorker> _logger;

    public HeartbeatWorker(ILogger<HeartbeatWorker> logger) => _logger = logger;

    protected override async Task ExecuteAsync(CancellationToken stoppingToken)
    {
        // Vong lap nen: chay LIEN TUC trong suot vong doi cua app, cho toi khi app tat.
        while (!stoppingToken.IsCancellationRequested)
        {
            _logger.LogInformation("Heartbeat luc {Time}", DateTimeOffset.Now);

            // Delay(..., stoppingToken): CHO 10 giay, nhung dung NGAY neu app dang shutdown.
            await Task.Delay(TimeSpan.FromSeconds(10), stoppingToken);
        }
    }
}
```

Đăng ký worker này (xem chi tiết mục 5) rồi chạy ứng dụng, log console sẽ hiện đúng một dòng mỗi 10 giây, độc lập hoàn toàn với việc có request HTTP nào đang xử lý hay không:

```text title="Log console khi chạy app"
info: HeartbeatWorker[0]
      Heartbeat lúc 2026-07-05T10:00:00+07:00
info: HeartbeatWorker[0]
      Heartbeat lúc 2026-07-05T10:00:10+07:00
info: HeartbeatWorker[0]
      Heartbeat lúc 2026-07-05T10:00:20+07:00
```

**Điều gì xảy ra khi dùng sai:** nếu bạn quên override `ExecuteAsync` là phương thức **bảo vệ (protected)**, không phải public, và cố gọi nó trực tiếp từ bên ngoài (`myWorker.ExecuteAsync(...)`) sẽ gặp lỗi biên dịch vì không truy cập được — đây là thiết kế có chủ đích: chỉ `BackgroundService` (thông qua cơ chế `StartAsync` nội bộ) được phép gọi `ExecuteAsync`, đảm bảo bạn không vô tình chạy vòng lặp nền hai lần hoặc chạy nó ngoài vòng đời quản lý của host.

So sánh nhanh với mục 2 để thấy rõ `BackgroundService` giúp bạn tránh đúng lỗi nào: nếu tự implement `IHostedService` trực tiếp, bạn phải **tự nhớ** viết `StartAsync` sao cho không block (thường phải tự gọi `Task.Run(...)` để tách vòng lặp ra một Task riêng, rồi tự lưu lại `Task` đó để `StopAsync` có thể chờ nó kết thúc đúng cách). `BackgroundService` làm sẵn toàn bộ phần "hạ tầng" này — bạn chỉ cần tập trung viết đúng logic nghiệp vụ bên trong `ExecuteAsync`, không cần lo về việc quản lý Task nền thủ công.

---

## 4. `CancellationToken` trong `ExecuteAsync` PHẢI được tôn trọng

**Định nghĩa:** `CancellationToken` được truyền vào `ExecuteAsync` (đặt tên `stoppingToken` theo quy ước) là tín hiệu báo "ứng dụng đang bắt đầu tắt" — khi host gọi `StopAsync` (mục 2), token này chuyển sang trạng thái đã yêu cầu hủy (`IsCancellationRequested = true`), và vòng lặp nền của bạn **phải kiểm tra** tín hiệu đó để kết thúc đúng hạn, không phải chạy mãi bất chấp.

Đây là quy tắc quan trọng nhất của chương này: mọi `BackgroundService` bạn viết, dù đơn giản hay phức tạp, đều phải tự hỏi "nếu app cần tắt ngay bây giờ, vòng lặp của tôi có kết thúc kịp không?" — câu trả lời chỉ có thể là "có" khi bạn kiểm tra và truyền đúng `stoppingToken` vào mọi điểm chờ trong vòng lặp.

Ví dụ cụ thể về sai — **không** kiểm tra token đúng cách:

```csharp title="C#"
// test:skip minh hoa LOI: khong ton trong CancellationToken, khong phai chuong trinh day du
protected override async Task ExecuteAsync(CancellationToken stoppingToken)
{
    while (true) // SAI: khong bao gio kiem tra stoppingToken.IsCancellationRequested
    {
        await ProcessNextItemAsync(); // gia su viec nay khong nhan token, chay bao lau cung duoc
        await Task.Delay(TimeSpan.FromSeconds(10)); // SAI: khong truyen stoppingToken vao Delay
    }
}
```

**Điều gì xảy ra khi dùng sai (hậu quả cụ thể lúc shutdown):** khi ứng dụng nhận lệnh tắt (ví dụ deploy phiên bản mới, hoặc `docker stop`), .NET gọi `StopAsync`, đợi worker tự kết thúc trong một khoảng thời gian ân hạn (mặc định 5 giây, cấu hình qua `HostOptions.ShutdownTimeout`). Vì vòng lặp trên **không hề kiểm tra** `stoppingToken`, nó tiếp tục chạy như không có gì xảy ra — hết 5 giây ân hạn, .NET **buộc kill tiến trình**, cắt ngang `ProcessNextItemAsync()` giữa lúc đang xử lý (có thể đang giữa việc ghi file, gửi email — dữ liệu dở dang, không đảm bảo toàn vẹn). Trong môi trường container/Kubernetes, việc app không tắt đúng hạn còn khiến rolling update bị chậm hoặc treo, vì orchestrator phải đợi hết timeout rồi mới forcibly kill container cũ.

Sửa đúng — truyền `stoppingToken` vào **mọi** điểm chờ, và cho vòng lặp kết thúc đúng hạn:

```csharp title="C#"
// test:compile Web SDK tran - TON TRONG CancellationToken dung cach
using Microsoft.Extensions.Hosting;

public class FileCleanupWorker : BackgroundService
{
    private readonly ILogger<FileCleanupWorker> _logger;

    public FileCleanupWorker(ILogger<FileCleanupWorker> logger) => _logger = logger;

    protected override async Task ExecuteAsync(CancellationToken stoppingToken)
    {
        // Kiem tra token trong dieu kien vong lap - vong lap TU KET THUC khi token bao huy.
        while (!stoppingToken.IsCancellationRequested)
        {
            try
            {
                _logger.LogInformation("Dọn file tạm...");
                await Task.Delay(TimeSpan.FromSeconds(30), stoppingToken); // truyen token vao Delay
            }
            catch (OperationCanceledException)
            {
                // Task.Delay bi huy giua luc cho vi app dang shutdown - day la HANH VI DUNG,
                // khong phai loi can bat/log nhu mot exception bat thuong.
                break;
            }
        }

        _logger.LogInformation("FileCleanupWorker đã dừng đúng cách.");
    }
}
```

Điểm mấu chốt cần nhớ: `Task.Delay(TimeSpan, CancellationToken)` khi nhận được tín hiệu hủy sẽ ném `OperationCanceledException` **ngay lập tức** (không đợi hết 30 giây) — đây chính là cơ chế giúp vòng lặp "tỉnh dậy" sớm để kiểm tra điều kiện và kết thúc, thay vì phải đợi hết khoảng delay hiện tại rồi mới nhận ra cần dừng.

---

## 5. Đăng ký worker qua `AddHostedService<T>()`

**Định nghĩa:** `AddHostedService<T>()` là phương thức mở rộng của `IServiceCollection` đăng ký một class kế thừa `BackgroundService` (hoặc implement `IHostedService`) vào DI container, đồng thời báo cho host biết class đó cần được `StartAsync`/`StopAsync` tự động theo đúng vòng đời ứng dụng.

```csharp title="C#"
// test:compile Web SDK tran - dang ky BackgroundService qua AddHostedService<T>()
var builder = WebApplication.CreateBuilder(args);

// Dang ky HeartbeatWorker (dinh nghia o muc 3) - .NET tu goi StartAsync luc app khoi dong.
builder.Services.AddHostedService<HeartbeatWorker>();

var app = builder.Build();

app.MapGet("/", () => "App dang chay, HeartbeatWorker dang log nen.");

app.Run();

public class HeartbeatWorker : BackgroundService
{
    private readonly ILogger<HeartbeatWorker> _logger;

    public HeartbeatWorker(ILogger<HeartbeatWorker> logger) => _logger = logger;

    protected override async Task ExecuteAsync(CancellationToken stoppingToken)
    {
        while (!stoppingToken.IsCancellationRequested)
        {
            _logger.LogInformation("Heartbeat lúc {Time}", DateTimeOffset.Now);
            await Task.Delay(TimeSpan.FromSeconds(10), stoppingToken);
        }
    }
}
```

Có thể gọi `AddHostedService<T>()` **nhiều lần** với các worker khác nhau — mỗi worker chạy độc lập, trong Task riêng của nó:

```csharp title="C#"
// test:skip doan trich rut gon chi de minh hoa dang ky nhieu worker, khong phai chuong trinh day du
builder.Services.AddHostedService<HeartbeatWorker>();
builder.Services.AddHostedService<FileCleanupWorker>();
```

Khi ứng dụng khởi động, host gọi `StartAsync` của **cả hai** worker này — theo đúng thứ tự bạn đăng ký (`HeartbeatWorker` trước, `FileCleanupWorker` sau) — nhưng cả hai đều chạy **song song, độc lập** ngay sau đó, không worker nào chờ worker khác chạy xong mới bắt đầu (vì bản chất `BackgroundService` chạy `ExecuteAsync` trong Task riêng, đã nêu ở mục 3).

**Điều gì xảy ra khi dùng sai:** nếu bạn chỉ đăng ký worker bằng `builder.Services.AddScoped<HeartbeatWorker>()` hoặc `AddSingleton<HeartbeatWorker>()` (thay vì `AddHostedService<T>()`), class của bạn được đăng ký vào DI container như một service **bình thường** — nhưng **không ai tự động gọi `StartAsync`/`ExecuteAsync` cho nó**. Ứng dụng biên dịch được, chạy được, nhưng vòng lặp nền **không bao giờ chạy** trừ khi bạn tự resolve và gọi nó ở đâu đó — một lỗi âm thầm rất dễ bỏ sót vì không có exception, không có log lỗi, chỉ là worker im lặng không hoạt động.

---

## 6. Giao tiếp HTTP request và background job qua `Channel<T>`

**Vấn đề cụ thể cần giải quyết:** worker ở mục 3-5 (heartbeat, cleanup) tự chạy độc lập, không cần dữ liệu từ request nào. Nhưng quay lại ví dụ mở đầu (mục 0-1): khi có request `/register` mới, làm sao **báo** cho một background worker biết "có một email cần gửi cho userId=42" — request không thể gọi trực tiếp method của worker (worker chạy trong Task riêng, không có tham chiếu trực tiếp từ endpoint).

Nói cách khác, bạn cần một "hộp thư trung gian": endpoint chỉ **đặt** thông tin (userId cần gửi email) vào hộp thư đó rồi trả response ngay, còn worker chạy nền sẽ tự **lấy** thông tin ra khỏi hộp thư đó để xử lý, vào bất kỳ lúc nào nó rảnh — hai bên không cần gọi trực tiếp lẫn nhau.

**Định nghĩa (giới thiệu ngắn, không đi sâu):** `Channel<T>` là một cấu trúc **hàng đợi bất đồng bộ trong-tiến-trình** có sẵn trong `System.Threading.Channels` (namespace có sẵn trong BCL, không cần package ngoài) — cho phép một phần code (`Writer`) ghi dữ liệu vào, và một phần code khác (`Reader`) đọc ra, an toàn khi nhiều thread cùng ghi/đọc, nhưng **chỉ hoạt động trong nội bộ một tiến trình ứng dụng đang chạy** — khác hẳn message queue thực sự (RabbitMQ/Azure Service Bus đã học ở P6), dữ liệu trong `Channel<T>` **biến mất hoàn toàn** nếu ứng dụng restart, và không thể chia sẻ giữa nhiều instance của app chạy song song.

```csharp title="C#"
// test:compile Web SDK tran - Channel<T> lam hang doi trong-tien-trinh giua request va background worker
using System.Threading.Channels;

var builder = WebApplication.CreateBuilder(args);

// Dang ky Channel<T> nhu mot Singleton - Writer va Reader deu lay tu CUNG mot Channel instance.
builder.Services.AddSingleton(Channel.CreateUnbounded<int>());
builder.Services.AddHostedService<EmailSendingWorker>();

var app = builder.Build();

app.MapPost("/register", async (RegisterRequest request, Channel<int> emailQueue) =>
{
    var userId = 42; // gia lap luu user thanh cong

    // Ghi vao Channel roi tra response NGAY - KHONG doi email gui xong.
    await emailQueue.Writer.WriteAsync(userId);

    return Results.Ok(new { userId });
});

app.Run();

public record RegisterRequest(string Email);

public class EmailSendingWorker : BackgroundService
{
    private readonly Channel<int> _emailQueue;
    private readonly ILogger<EmailSendingWorker> _logger;

    public EmailSendingWorker(Channel<int> emailQueue, ILogger<EmailSendingWorker> logger)
    {
        _emailQueue = emailQueue;
        _logger = logger;
    }

    protected override async Task ExecuteAsync(CancellationToken stoppingToken)
    {
        // ReadAllAsync: doc lien tuc tu Channel, tu dung dung luc stoppingToken bao huy.
        await foreach (var userId in _emailQueue.Reader.ReadAllAsync(stoppingToken))
        {
            _logger.LogInformation("Đang gửi email chào mừng cho userId={UserId}...", userId);
            await Task.Delay(TimeSpan.FromSeconds(5), stoppingToken); // gia lap gui email cham
            _logger.LogInformation("Đã gửi email cho userId={UserId}.", userId);
        }
    }
}
```

Với thiết kế này, request `/register` trả response **ngay** sau khi ghi vào `Channel<T>` (vài microsecond), còn việc gửi email thật sự (5 giây) xảy ra **sau đó, trong worker nền**, không ảnh hưởng gì đến thời gian phản hồi của request.

**Khi nào `Channel<T>` là đủ, khi nào cần message queue thực sự (đã học ở P6):**

| Khía cạnh | `Channel<T>` (trong-tiến-trình) | Message queue thực sự (RabbitMQ/Azure Service Bus) |
|-----------|----------------------------------|------------------------------------------------------|
| Phạm vi hoạt động | Chỉ trong một tiến trình ứng dụng đang chạy | Qua mạng, giữa nhiều tiến trình/máy chủ khác nhau |
| Dữ liệu khi app restart | **Mất hoàn toàn** (chỉ nằm trong bộ nhớ) | **Được giữ lại** (queue có cơ chế lưu bền/persist) |
| Nhiều instance app chạy song song | **Không chia sẻ được** — mỗi instance có Channel riêng | Chia sẻ được — mọi instance cùng đọc từ một queue |
| Phù hợp khi | Một service duy nhất, việc nền không quan trọng tới mức phải sống sót qua restart | Nhiều service tách rời, hoặc cần đảm bảo không mất việc dù app crash/restart |

**Điều gì xảy ra khi dùng sai:** nếu dùng `Channel<T>` cho một nghiệp vụ **quan trọng** (ví dụ xử lý thanh toán, không được mất dù app restart giữa lúc xử lý), và ứng dụng bị restart đột ngột (deploy, crash, container bị kill) ngay lúc có 50 item đang chờ trong `Channel<T>` — toàn bộ 50 item đó **biến mất vĩnh viễn**, không có cách nào lấy lại, vì `Channel<T>` chỉ tồn tại trong bộ nhớ của tiến trình đó. Đây là lý do `Channel<T>` chỉ phù hợp cho việc nền **có thể chấp nhận mất** khi app restart (ví dụ gửi email chào mừng — nếu mất, người dùng không nhận được email, không phải sự cố nghiêm trọng), còn nghiệp vụ quan trọng cần dùng message queue thực sự (đã học ở P6) với cơ chế lưu bền.

Một chi tiết cấu hình dễ bỏ sót: `Channel.CreateUnbounded<T>()` (dùng ở ví dụ trên) tạo một hàng đợi **không giới hạn dung lượng** — nếu tốc độ ghi (`Writer.WriteAsync`) liên tục nhanh hơn tốc độ đọc/xử lý (`Reader`), số item chờ trong hàng đợi tăng dần **không giới hạn**, chiếm bộ nhớ ngày càng nhiều tới khi ứng dụng hết bộ nhớ (`OutOfMemoryException`). `Channel.CreateBounded<T>(capacity)` giới hạn dung lượng hàng đợi — khi đầy, `WriteAsync` sẽ **tự chờ** (không ném lỗi ngay) tới khi có chỗ trống, tạo hiệu ứng "áp lực ngược" (backpressure) buộc request phía ghi chậm lại theo đúng tốc độ xử lý thực tế của worker, thay vì để bộ nhớ phình ra không kiểm soát.

---

## 7. Xử lý exception trong `ExecuteAsync`: một lỗi không nên làm sập cả app

**Vấn đề cụ thể:** trong ví dụ `EmailSendingWorker` ở mục 6, nếu việc gửi email cho một `userId` cụ thể ném exception (ví dụ địa chỉ email sai định dạng, hoặc API email bên ngoài trả lỗi), điều gì xảy ra với worker và với phần còn lại của ứng dụng?

```csharp title="C#"
// test:skip minh hoa LOI: khong bat exception trong vong lap ExecuteAsync
protected override async Task ExecuteAsync(CancellationToken stoppingToken)
{
    await foreach (var userId in _emailQueue.Reader.ReadAllAsync(stoppingToken))
    {
        // Neu SendWelcomeEmailAsync nem exception (vi du dia chi email sai),
        // KHONG co try/catch nao o day de bat lai.
        await _emailSender.SendWelcomeEmailAsync(userId);
    }
}
```

**Điều gì xảy ra khi dùng sai (hậu quả cụ thể):** nếu `SendWelcomeEmailAsync` ném exception cho `userId=42` và không có `try/catch` nào bên trong vòng lặp, exception đó thoát ra khỏi `await foreach`, khiến toàn bộ `ExecuteAsync` **kết thúc bất thường**. Từ .NET 6 trở đi, hành vi mặc định của host khi một `BackgroundService` ném exception không được xử lý là **dừng toàn bộ ứng dụng** (không chỉ riêng worker đó) — vì host coi đây là dấu hiệu ứng dụng không còn ổn định.

```text title="Log thực tế khi ExecuteAsync ném exception không được bắt"
fail: Microsoft.Extensions.Hosting.Internal.Host[9]
      BackgroundService failed
      System.Exception: Địa chỉ email không hợp lệ cho userId=42
Hosting environment shutting down...
Application is shutting down...
```

Hậu quả production cụ thể: một lỗi nhỏ ở **một** email của **một** user (email sai định dạng) làm **toàn bộ ứng dụng dừng lại** — mọi request HTTP đang xử lý, mọi worker khác đang chạy đều bị kéo theo, dù bản thân lỗi chỉ liên quan tới đúng một item trong hàng đợi.

Sửa đúng — bọc `try/catch` **quanh từng item xử lý**, không phải quanh cả vòng lặp:

```csharp title="C#"
// test:compile Web SDK tran - bat exception cho TUNG item, khong de mot loi lam sap ca worker
using System.Threading.Channels;

public class EmailSendingWorker : BackgroundService
{
    private readonly Channel<int> _emailQueue;
    private readonly ILogger<EmailSendingWorker> _logger;

    public EmailSendingWorker(Channel<int> emailQueue, ILogger<EmailSendingWorker> logger)
    {
        _emailQueue = emailQueue;
        _logger = logger;
    }

    protected override async Task ExecuteAsync(CancellationToken stoppingToken)
    {
        await foreach (var userId in _emailQueue.Reader.ReadAllAsync(stoppingToken))
        {
            try
            {
                _logger.LogInformation("Đang gửi email cho userId={UserId}...", userId);
                await Task.Delay(TimeSpan.FromSeconds(1), stoppingToken); // gia lap gui email
            }
            catch (OperationCanceledException)
            {
                // App dang shutdown - khong phai loi nghiep vu, cho thoat vong lap tu nhien.
                throw;
            }
            catch (Exception ex)
            {
                // Loi nghiep vu (email sai, API loi...) - LOG lai, KHONG de thoat khoi vong lap.
                _logger.LogError(ex, "Gửi email thất bại cho userId={UserId}.", userId);
            }
        }
    }
}
```

Với cách sửa này, nếu `userId=42` gửi lỗi, worker chỉ log lỗi rồi **tiếp tục** vòng lặp `await foreach`, xử lý bình thường các `userId` tiếp theo trong hàng đợi — một lỗi nghiệp vụ không còn khả năng kéo sập cả ứng dụng. Chú ý điểm quan trọng: `catch (OperationCanceledException)` được xử lý **riêng** và `throw` lại — vì đây không phải lỗi nghiệp vụ, mà là tín hiệu shutdown hợp lệ (đã học ở mục 4), không nên bị nuốt bởi `catch (Exception ex)` chung.

**Điều gì xảy ra khi dùng sai theo cách khác — bắt luôn cả `OperationCanceledException` vào `catch (Exception ex)` phía trên:** nếu thứ tự `catch` bị đổi ngược hoặc chỉ có một `catch (Exception ex)` duy nhất bắt tất cả, tín hiệu shutdown (`OperationCanceledException` khi app đang tắt) sẽ bị coi như một **lỗi nghiệp vụ bình thường**, bị log là "Gửi email thất bại" và vòng lặp **tiếp tục chạy** thêm — trì hoãn việc `ExecuteAsync` thật sự kết thúc, làm chậm quá trình shutdown đúng hạn đã nhấn mạnh ở mục 4.

---

## Cạm bẫy & thực chiến

- **Làm việc tốn thời gian đồng bộ trong request HTTP (mục 1):** gửi email, xử lý file lớn, gọi API chậm bên ngoài mà không cần kết quả ngay — chặn request khiến client chờ lâu và có thể timeout dù nghiệp vụ chính đã xử lý xong.
- **Tự implement `IHostedService` trực tiếp và block `StartAsync` (mục 2):** viết vòng lặp vô hạn ngay trong `StartAsync` (không tách Task riêng) khiến ứng dụng treo ngay lúc khởi động, không bao giờ sẵn sàng nhận request. Dùng `BackgroundService` để tránh lỗi này hoàn toàn.
- **Không kiểm tra `CancellationToken` trong vòng lặp `ExecuteAsync` (mục 4):** khiến app không tắt đúng hạn lúc shutdown, bị host buộc kill tiến trình sau khi hết thời gian ân hạn (mặc định 5 giây), có thể cắt ngang dữ liệu đang xử lý dở dang và làm chậm rolling update trong container/Kubernetes.
- **Đăng ký worker bằng `AddSingleton`/`AddScoped` thay vì `AddHostedService<T>()` (mục 5):** biên dịch được, chạy được, nhưng vòng lặp nền không bao giờ tự chạy — lỗi âm thầm, không có exception hay log báo hiệu.
- **Không truyền `CancellationToken` vào `Task.Delay`/các lời gọi bất đồng bộ khác trong `ExecuteAsync` (mục 4):** dù có kiểm tra `IsCancellationRequested` ở điều kiện `while`, nếu `Task.Delay` không nhận token, vòng lặp vẫn phải đợi hết khoảng delay hiện tại (có thể vài chục giây) mới kiểm tra lại điều kiện — làm chậm quá trình shutdown không cần thiết.
- **Dùng `Channel<T>` cho nghiệp vụ không chấp nhận mất dữ liệu khi app restart (mục 6):** `Channel<T>` chỉ tồn tại trong bộ nhớ một tiến trình — mọi item đang chờ xử lý biến mất vĩnh viễn nếu app crash/restart; nghiệp vụ quan trọng cần message queue thực sự có cơ chế lưu bền.
- **Không bọc `try/catch` quanh từng item xử lý trong vòng lặp `ExecuteAsync` (mục 7):** một lỗi nghiệp vụ nhỏ (một email sai định dạng, một file hỏng) ném exception ra khỏi vòng lặp, làm `ExecuteAsync` kết thúc bất thường — mặc định .NET 6+ dừng **toàn bộ ứng dụng**, không chỉ riêng worker đó.
- **Bắt cả `OperationCanceledException` chung với lỗi nghiệp vụ (mục 7):** khiến tín hiệu shutdown hợp lệ bị hiểu nhầm thành lỗi nghiệp vụ, bị log sai và trì hoãn việc worker kết thúc đúng hạn.
- **Dùng `Channel.CreateUnbounded<T>()` khi tốc độ ghi liên tục vượt tốc độ xử lý (mục 6):** hàng đợi phình ra không giới hạn, chiếm bộ nhớ ngày càng nhiều tới khi ứng dụng hết bộ nhớ — nên dùng `Channel.CreateBounded<T>(capacity)` để tạo backpressure khi cần giới hạn.

---

## Bài tập

**Bài 1 (có giàn giáo).** Worker dưới đây có lỗi không tôn trọng `CancellationToken` đúng cách. Sửa để worker dừng đúng hạn khi app shutdown.

```csharp title="C#"
// test:skip bai 1 - can sua: khong ton trong CancellationToken dung cach
public class ReportWorker : BackgroundService
{
    protected override async Task ExecuteAsync(CancellationToken stoppingToken)
    {
        while (true)
        {
            Console.WriteLine("Đang tạo báo cáo định kỳ...");
            await Task.Delay(TimeSpan.FromMinutes(1));
        }
    }
}
```

Gợi ý giàn giáo: đổi điều kiện `while (true)` thành kiểm tra `stoppingToken`, và truyền `stoppingToken` vào `Task.Delay`.

??? success "Lời giải + vì sao"
    ```csharp title="C#"
    // test:compile bai 1 da sua - kiem tra stoppingToken dung cach
    public class ReportWorker : BackgroundService
    {
        protected override async Task ExecuteAsync(CancellationToken stoppingToken)
        {
            while (!stoppingToken.IsCancellationRequested)
            {
                Console.WriteLine("Đang tạo báo cáo định kỳ...");
                try
                {
                    await Task.Delay(TimeSpan.FromMinutes(1), stoppingToken);
                }
                catch (OperationCanceledException)
                {
                    break;
                }
            }
        }
    }
    ```

    **Vì sao:** `while (true)` không bao giờ tự kết thúc dù `stoppingToken` đã báo hủy — worker chỉ dừng khi bị host kill sau thời gian ân hạn shutdown. Đổi thành `while (!stoppingToken.IsCancellationRequested)` và truyền `stoppingToken` vào `Task.Delay` giúp vòng lặp "tỉnh dậy" ngay khi có tín hiệu hủy (thay vì đợi hết 1 phút), rồi tự kết thúc đúng hạn.

**Bài 2 (thiết kế).** Bạn cần thêm một background job xử lý ảnh đại diện người dùng vừa upload — resize ảnh về 200x200px, việc này tốn khoảng 2-3 giây. Yêu cầu: (a) endpoint `/upload-avatar` không được chờ resize xong mới trả response, (b) dùng `Channel<T>` để giao dữ liệu (đường dẫn file cần resize) từ endpoint sang một `BackgroundService`, (c) worker tôn trọng `CancellationToken` đúng cách. Viết đăng ký và code (không cần code resize ảnh thật, chỉ giả lập bằng `Task.Delay`).

??? success "Lời giải + vì sao"
    ```csharp title="C#"
    // test:compile bai 2 - Channel<T> giao du lieu tu endpoint sang BackgroundService, ton trong token
    using System.Threading.Channels;

    var builder = WebApplication.CreateBuilder(args);

    builder.Services.AddSingleton(Channel.CreateUnbounded<string>());
    builder.Services.AddHostedService<AvatarResizeWorker>();

    var app = builder.Build();

    app.MapPost("/upload-avatar", async (UploadAvatarRequest request, Channel<string> resizeQueue) =>
    {
        // Gia su file da duoc luu vao "request.FilePath" o buoc truoc (khong hien trong bai nay).
        await resizeQueue.Writer.WriteAsync(request.FilePath);

        // Tra response NGAY - khong doi resize xong.
        return Results.Ok(new { status = "uploaded", message = "Ảnh đang được xử lý." });
    });

    app.Run();

    public record UploadAvatarRequest(string FilePath);

    public class AvatarResizeWorker : BackgroundService
    {
        private readonly Channel<string> _resizeQueue;
        private readonly ILogger<AvatarResizeWorker> _logger;

        public AvatarResizeWorker(Channel<string> resizeQueue, ILogger<AvatarResizeWorker> logger)
        {
            _resizeQueue = resizeQueue;
            _logger = logger;
        }

        protected override async Task ExecuteAsync(CancellationToken stoppingToken)
        {
            await foreach (var filePath in _resizeQueue.Reader.ReadAllAsync(stoppingToken))
            {
                _logger.LogInformation("Đang resize ảnh {FilePath}...", filePath);
                await Task.Delay(TimeSpan.FromSeconds(3), stoppingToken); // gia lap resize
                _logger.LogInformation("Đã resize xong {FilePath}.", filePath);
            }
        }
    }
    ```

    **Vì sao:** endpoint chỉ ghi đường dẫn file vào `Channel<string>` rồi trả response ngay (mục 6), tách hoàn toàn thời gian resize (2-3 giây) ra khỏi thời gian phản hồi HTTP. `ReadAllAsync(stoppingToken)` (mục 4 + 6) tự động dừng đọc và kết thúc `ExecuteAsync` đúng hạn khi app shutdown, không cần vòng lặp `while` thủ công.

**Bài 3 (gỡ lỗi).** Đồng nghiệp báo cáo: "Cứ khi một khách hàng nhập email sai định dạng, cả ứng dụng của chúng ta bị crash luôn, không chỉ riêng chức năng gửi email." Đoạn code worker dưới đây là nguyên nhân. Xác định đúng dòng gây lỗi và sửa lại để một email sai không làm sập cả ứng dụng.

```csharp title="C#"
// test:skip bai 3 - tim va sua loi khien mot email sai lam sap ca ung dung
public class NotificationWorker : BackgroundService
{
    private readonly Channel<string> _emailQueue;
    private readonly ILogger<NotificationWorker> _logger;

    public NotificationWorker(Channel<string> emailQueue, ILogger<NotificationWorker> logger)
    {
        _emailQueue = emailQueue;
        _logger = logger;
    }

    protected override async Task ExecuteAsync(CancellationToken stoppingToken)
    {
        await foreach (var email in _emailQueue.Reader.ReadAllAsync(stoppingToken))
        {
            ValidateEmailFormat(email); // nem exception neu email sai dinh dang
            _logger.LogInformation("Đã gửi thông báo tới {Email}.", email);
        }
    }

    private void ValidateEmailFormat(string email)
    {
        if (!email.Contains('@'))
            throw new FormatException($"Email không hợp lệ: {email}");
    }
}
```

??? success "Lời giải + vì sao"
    **Nguyên nhân:** `ValidateEmailFormat` ném `FormatException` mà không có `try/catch` nào trong vòng lặp `ExecuteAsync` bắt lại. Exception thoát khỏi `await foreach`, khiến `ExecuteAsync` kết thúc bất thường — mặc định .NET 6+ dừng toàn bộ ứng dụng khi một `BackgroundService` ném exception không được xử lý (mục 7).

    ```csharp title="C#"
    // test:compile bai 3 da sua - bat loi tung item, khong de mot email sai lam sap ca app
    public class NotificationWorker : BackgroundService
    {
        private readonly Channel<string> _emailQueue;
        private readonly ILogger<NotificationWorker> _logger;

        public NotificationWorker(Channel<string> emailQueue, ILogger<NotificationWorker> logger)
        {
            _emailQueue = emailQueue;
            _logger = logger;
        }

        protected override async Task ExecuteAsync(CancellationToken stoppingToken)
        {
            await foreach (var email in _emailQueue.Reader.ReadAllAsync(stoppingToken))
            {
                try
                {
                    ValidateEmailFormat(email);
                    _logger.LogInformation("Đã gửi thông báo tới {Email}.", email);
                }
                catch (OperationCanceledException)
                {
                    throw; // tin hieu shutdown - khong phai loi nghiep vu, cho thoat tu nhien
                }
                catch (Exception ex)
                {
                    _logger.LogError(ex, "Gửi thông báo thất bại cho {Email}.", email);
                }
            }
        }

        private void ValidateEmailFormat(string email)
        {
            if (!email.Contains('@'))
                throw new FormatException($"Email không hợp lệ: {email}");
        }
    }
    ```

    **Vì sao:** bọc `try/catch` quanh **từng item** (không phải quanh cả vòng lặp) đảm bảo một email sai chỉ bị log lỗi rồi worker tiếp tục xử lý email tiếp theo, thay vì làm `ExecuteAsync` kết thúc bất thường và kéo sập cả ứng dụng theo mặc định của host (mục 7).

---

## Tự kiểm tra

1. Vì sao gửi email đồng bộ ngay trong request `/register` là một thiết kế có vấn đề?

    ??? note "Đáp án"
        Vì việc gửi email không cần hoàn tất ngay để client biết kết quả (tài khoản đã tạo hay chưa) — chặn request để chờ nó khiến client chờ lâu không cần thiết, và nếu email chậm bất thường có thể khiến request timeout dù tài khoản đã tạo thành công.

2. `IHostedService` có hai phương thức nào, và ai gọi chúng?

    ??? note "Đáp án"
        `StartAsync(CancellationToken)` và `StopAsync(CancellationToken)`. Chính host của ASP.NET Core (.NET) tự động gọi hai phương thức này đúng lúc app khởi động và lúc app bắt đầu tắt — không phải bạn tự gọi.

3. Vì sao hầu như không ai tự implement `IHostedService` trực tiếp mà dùng `BackgroundService`?

    ??? note "Đáp án"
        Vì `StartAsync` phải trả về nhanh (không block) để host coi app đã khởi động xong; tự viết vòng lặp vô hạn trực tiếp trong `StartAsync` (quên tách Task riêng) sẽ khiến app treo ngay lúc khởi động. `BackgroundService` đã xử lý đúng việc chạy `ExecuteAsync` trong Task riêng, tránh lỗi này.

4. Điều gì xảy ra nếu vòng lặp trong `ExecuteAsync` không kiểm tra `stoppingToken.IsCancellationRequested`?

    ??? note "Đáp án"
        App sẽ không tắt đúng hạn lúc shutdown — vòng lặp tiếp tục chạy như không có gì xảy ra, host phải đợi hết thời gian ân hạn (mặc định 5 giây) rồi buộc kill tiến trình, có thể cắt ngang dữ liệu đang xử lý dở dang.

5. Đăng ký một `BackgroundService` bằng `builder.Services.AddSingleton<T>()` thay vì `AddHostedService<T>()` có chạy được không?

    ??? note "Đáp án"
        App biên dịch và chạy được, nhưng vòng lặp nền của worker đó **không bao giờ tự chạy** — vì không có gì gọi `StartAsync`/`ExecuteAsync` cho nó. Đây là lỗi âm thầm, không có exception hay log báo lỗi.

6. `Channel<T>` khác message queue thực sự (RabbitMQ/Azure Service Bus) ở điểm quan trọng nào?

    ??? note "Đáp án"
        `Channel<T>` chỉ hoạt động trong-tiến-trình (trong bộ nhớ của một app đang chạy) — dữ liệu biến mất hoàn toàn nếu app restart, và không chia sẻ được giữa nhiều instance app chạy song song. Message queue thực sự lưu bền dữ liệu và hoạt động qua mạng giữa nhiều tiến trình/máy chủ.

7. Khi nào dùng `Channel<T>` là phù hợp, khi nào nên dùng message queue thực sự?

    ??? note "Đáp án"
        `Channel<T>` phù hợp cho việc nền có thể chấp nhận mất khi app restart, trong một service duy nhất (ví dụ gửi email chào mừng không quan trọng). Message queue thực sự cần khi nghiệp vụ quan trọng không được mất dù app crash/restart, hoặc khi cần chia sẻ hàng đợi giữa nhiều service/instance khác nhau.

8. Nếu `ExecuteAsync` ném một exception không được bắt (không có `try/catch` nào xử lý), hành vi mặc định của .NET là gì?

    ??? note "Đáp án"
        Từ .NET 6 trở đi, mặc định host sẽ **dừng toàn bộ ứng dụng**, không chỉ riêng worker gây lỗi — vì host coi một `IHostedService` ném exception không xử lý là dấu hiệu ứng dụng không còn ổn định.

9. Vì sao trong vòng lặp xử lý từng item của `ExecuteAsync`, cần bắt `OperationCanceledException` riêng (rồi `throw` lại) thay vì để chung vào `catch (Exception ex)` bắt lỗi nghiệp vụ?

    ??? note "Đáp án"
        `OperationCanceledException` là tín hiệu shutdown hợp lệ (app đang tắt), không phải lỗi nghiệp vụ. Nếu bắt chung vào `catch (Exception ex)`, tín hiệu shutdown sẽ bị hiểu nhầm thành lỗi, bị log sai và trì hoãn việc worker kết thúc đúng hạn — ngược lại đúng mục tiêu tôn trọng `CancellationToken` đã nêu ở mục 4.

10. Vì sao một `BackgroundService` không thể tiêm trực tiếp một `DbContext` (Scoped) qua constructor, và cách đúng để dùng nó bên trong `ExecuteAsync` là gì?

    ??? note "Đáp án"
        `BackgroundService` được host quản lý với lifetime tương đương Singleton (một instance duy nhất, sống suốt vòng đời app), còn `DbContext` mặc định là Scoped (một instance riêng cho mỗi phạm vi, thường là mỗi request). Tiêm trực tiếp một service Scoped vào constructor của một class Singleton bị .NET chặn ngay lúc khởi động (`InvalidOperationException`). Cách đúng là tiêm `IServiceScopeFactory` (Singleton) vào worker, rồi tự tạo một scope mới bằng `_scopeFactory.CreateScope()` mỗi lần cần dùng service Scoped bên trong `ExecuteAsync` — xem chi tiết ở phần DEEP DIVE cuối chương.

---

??? abstract "DEEP DIVE: `IHostedService` nhiều instance, thứ tự start/stop, và Scoped service trong Singleton worker"
    Khi bạn gọi `AddHostedService<T>()` nhiều lần với các worker khác nhau, .NET khởi động chúng **theo thứ tự đăng ký** (worker đăng ký trước được `StartAsync` trước), nhưng lúc **shutdown**, thứ tự `StopAsync` cũng theo đúng thứ tự đăng ký đó (không đảo ngược tự động) — nếu worker B phụ thuộc vào worker A vẫn đang chạy (ví dụ B cần A dọn dẹp resource trước), bạn phải tự sắp xếp thứ tự đăng ký hoặc dùng cơ chế đồng bộ hóa riêng, .NET không tự suy luận phụ thuộc giữa các `IHostedService`.

    Một chi tiết dễ gây lỗi runtime khi worker cần dùng `DbContext` (Entity Framework Core) hoặc bất kỳ service đăng ký với lifetime **Scoped**: một `BackgroundService` được host quản lý với lifetime tương đương **Singleton** (chỉ tạo một lần, sống suốt vòng đời app), nhưng `DbContext` mặc định là **Scoped** (một instance cho mỗi "scope", thường tương ứng một request HTTP) — bạn **không thể** tiêm trực tiếp một service Scoped vào constructor của một class Singleton, .NET sẽ ném lỗi ngay lúc khởi động:

    ```text title="Loi runtime khi tiem truc tiep Scoped service vao BackgroundService"
    System.InvalidOperationException: Cannot consume scoped service
    'MyApp.Data.AppDbContext' from singleton
    'Microsoft.Extensions.Hosting.IHostedService'.
    ```

    Cách đúng là tiêm `IServiceScopeFactory` (một service có sẵn, lifetime Singleton) vào worker, rồi tự tạo một scope mới **mỗi lần cần dùng** service Scoped bên trong `ExecuteAsync`:

    ```csharp title="C#"
    // test:compile Web SDK tran - dung IServiceScopeFactory de lay Scoped service trong BackgroundService
    public class DataCleanupWorker : BackgroundService
    {
        private readonly IServiceScopeFactory _scopeFactory;

        public DataCleanupWorker(IServiceScopeFactory scopeFactory) => _scopeFactory = scopeFactory;

        protected override async Task ExecuteAsync(CancellationToken stoppingToken)
        {
            while (!stoppingToken.IsCancellationRequested)
            {
                // Tao mot scope MOI cho mot lan xu ly - giong nhu mot "request gia" tu tao ra.
                using (var scope = _scopeFactory.CreateScope())
                {
                    var repository = scope.ServiceProvider.GetRequiredService<IAuditLogRepository>();
                    await repository.DeleteOlderThanAsync(DateTime.UtcNow.AddDays(-90), stoppingToken);
                }

                await Task.Delay(TimeSpan.FromHours(24), stoppingToken);
            }
        }
    }
    ```

    Đây là lý do quan trọng khiến worker cần truy cập database (qua EF Core) không thể tiêm `DbContext` trực tiếp như một endpoint bình thường — endpoint được host trong một scope mới cho mỗi request HTTP tự động, còn `BackgroundService` chỉ có đúng một instance sống suốt vòng đời app, buộc phải tự quản lý scope bằng tay qua `IServiceScopeFactory`.

    Cuối cùng, `BackgroundService` chạy **trong cùng tiến trình** với phần Web API của ứng dụng — nếu worker của bạn cần xử lý khối lượng công việc rất nặng (CPU-bound, chiếm nhiều tài nguyên liên tục), nó sẽ **cạnh tranh tài nguyên trực tiếp** với các request HTTP đang được xử lý bởi cùng tiến trình đó, khác với việc tách hẳn ra một service/worker process riêng (deploy độc lập) — quyết định này liên quan tới kiến trúc tổng thể, không phải chi tiết kỹ thuật của riêng `BackgroundService`.

    Ba mảnh kiến thức trong deep dive này (thứ tự start/stop nhiều worker, Scoped service qua `IServiceScopeFactory`, và cạnh tranh tài nguyên cùng tiến trình) đều là những chi tiết chỉ thật sự quan trọng khi ứng dụng của bạn có **nhiều hơn một** background job đang chạy cùng lúc, hoặc khi một job cần truy cập dữ liệu qua EF Core — với một worker đơn giản chỉ log định kỳ như `HeartbeatWorker` ở mục 3, bạn chưa cần quan tâm tới bất kỳ chi tiết nào ở trên.

    Tóm lại thứ tự tư duy đúng khi thêm một background job mới vào ứng dụng: (1) xác định đây có thật là việc không cần client đợi ngay không (mục 1), (2) viết logic vào `ExecuteAsync` của một `BackgroundService` (mục 3), (3) đảm bảo vòng lặp tôn trọng `stoppingToken` ở mọi điểm chờ (mục 4), (4) đăng ký qua `AddHostedService<T>()` (mục 5), (5) nếu cần nhận dữ liệu từ request, dùng `Channel<T>` cho nhu cầu đơn giản trong-tiến-trình hoặc message queue thực sự cho nhu cầu quan trọng hơn (mục 6), và (6) luôn bọc `try/catch` quanh từng item xử lý để một lỗi nhỏ không kéo sập cả ứng dụng (mục 7).

Tiếp theo -> health checks & readiness probes
