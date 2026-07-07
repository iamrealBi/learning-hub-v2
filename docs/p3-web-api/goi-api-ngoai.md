---
tier: core
status: core
owner: core-team
verified_on: "2026-07-03"
dotnet_version: "10.0"
bloom: "Apply"
requires: [p3-config]
est_minutes_fast: 28
---

# Gọi API bên ngoài với HttpClient

!!! info "Bạn đang ở đây"
    **cần trước:** configuration & options pattern (biết `IConfiguration`, `Configure<T>`, đăng ký service qua `builder.Services`).
    **mở khoá:** tích hợp dịch vụ bên thứ ba (thanh toán, gửi email, xác thực ngoài), microservices gọi lẫn nhau qua HTTP, và các chương về resilience/observability nâng cao.

> **Mục tiêu:** **Áp dụng** đúng cách đăng ký và tiêm `HttpClient` qua `IHttpClientFactory`, **thực hiện** được GET/POST kèm đọc/ghi JSON, **xử lý** timeout và lỗi HTTP đúng cách, và **giải thích** vì sao `new HttpClient()` thủ công trong mỗi request là một lỗi thiết kế nghiêm trọng.

---

## 0. Đoán nhanh trước khi học

Một đồng nghiệp viết đoạn code sau bên trong một Minimal API endpoint, và endpoint này bị gọi hàng nghìn lần mỗi phút:

```csharp title="Endpoint.cs"
// test:skip minh hoa loi thiet ke (khong phai chuong trinh day du), phan tich o muc 1
app.MapGet("/weather", async () =>
{
    var client = new HttpClient();
    var result = await client.GetStringAsync("https://api.weather.example/today");
    return result;
});
```

Sau vài giờ chạy production, server bắt đầu ném lỗi kết nối hàng loạt dù API bên ngoài vẫn hoạt động bình thường. Vì sao?

??? question "Đoán trước, đáp án ở dưới"
    Gợi ý: nghĩ về việc `HttpClient` implement `IDisposable`, và điều gì xảy ra ở tầng hệ điều hành khi một kết nối TCP bị đóng.

??? note "Đáp án"
    **Socket exhaustion** (cạn kiệt cổng TCP). Mỗi lần `new HttpClient()` tạo một client mới, nó mở một kết nối TCP (socket) riêng. Khi request kết thúc, `HttpClient` (dù được `using`/dispose đúng) không đóng socket ngay — socket chuyển sang trạng thái `TIME_WAIT` (thường 240 giây trên Windows, tương tự trên Linux) trước khi hệ điều hành thật sự giải phóng nó. Với hàng nghìn request/phút, số socket ở trạng thái `TIME_WAIT` tích luỹ nhanh hơn tốc độ hệ điều hành giải phóng, tới khi cạn hết cổng khả dụng (khoảng 16000-64000 cổng ephemeral tuỳ hệ điều hành) — request mới không mở được kết nối, ném `SocketException` dù server đích vẫn khoẻ mạnh. Mục 1 giải thích cơ chế này chi tiết hơn và mục 2 giới thiệu cách khắc phục đúng: `IHttpClientFactory`.

---

## 1. Vì sao không `new HttpClient()` mỗi request: socket exhaustion

**Định nghĩa:** Socket exhaustion là tình trạng ứng dụng cạn kiệt số cổng TCP (socket) khả dụng trên máy, xảy ra khi tạo quá nhiều kết nối mạng mới trong thời gian ngắn mà không tái sử dụng kết nối cũ, khiến các socket đã đóng bị kẹt ở trạng thái chờ (`TIME_WAIT`) và chưa được hệ điều hành thu hồi kịp.

Ví dụ tối thiểu minh hoạ đúng vấn đề (không cần chạy thật để thấy hại — chỉ cần hiểu vòng đời):

```csharp title="Program.cs"
// test:compile MO PHONG loi: new HttpClient() moi lan goi (KHONG lam theo cach nay trong production)
var builder = WebApplication.CreateBuilder(args);
var app = builder.Build();

app.MapGet("/bad-weather", async () =>
{
    // MOI request tao MOT HttpClient moi -> MOI request mo MOT socket TCP moi.
    using var client = new HttpClient();
    var result = await client.GetStringAsync("https://example.com");
    return result;
});

app.Run();
```

Đoạn code trên **biên dịch được, chạy được, và trả về kết quả đúng** cho vài request đầu tiên — đây là lý do lỗi này nguy hiểm: nó không lộ ra lúc code review hay test thủ công.

**Điều gì xảy ra khi dùng sai:** dưới tải cao (nhiều request/giây kéo dài), số socket ở trạng thái `TIME_WAIT` tăng nhanh hơn tốc độ hệ điều hành giải phóng chúng. Khi cạn cổng ephemeral khả dụng, các request HTTP mới ném:

```text title="Ngoại lệ runtime khi cạn socket"
System.Net.Http.HttpRequestException: An error occurred while sending the request.
 ---> System.Net.Sockets.SocketException: Only one usage of each socket address
 (protocol/network address/port) is normally permitted.
```

hoặc trên Linux là `SocketException: Address already in use` / kết nối bị treo (timeout) vì không còn cổng nào để mở. Đây **không phải lỗi biên dịch**, không phải lỗi xảy ra ngay — nó là hành vi runtime tích luỹ dần theo thời gian và tải, khiến việc debug rất khó vì log ban đầu hoàn toàn sạch.

Có một cách "sửa nửa vời" hay bị hiểu lầm là đúng: dùng **một `HttpClient` static dùng chung suốt vòng đời ứng dụng** (`static readonly HttpClient _client = new();`). Cách này tránh được socket exhaustion (vì không tạo socket mới liên tục), nhưng lại gây một vấn đề khác — **DNS không được cập nhật**: `HttpClient` cache kết nối TCP đã mở và không tự động phát hiện khi bản ghi DNS của tên miền đích đổi (ví dụ server đích chuyển sang IP mới sau failover), khiến ứng dụng tiếp tục gọi tới IP cũ đã ngừng hoạt động cho tới khi restart ứng dụng. Mục 2 giới thiệu `IHttpClientFactory` — giải pháp giải quyết **cả hai** vấn đề cùng lúc.

---

## 2. `IHttpClientFactory` qua `AddHttpClient`: đăng ký và tiêm đúng cách

**Định nghĩa:** `IHttpClientFactory` là một service do ASP.NET Core cung cấp, quản lý một **pool** các `HttpMessageHandler` (thành phần thật sự giữ kết nối TCP) đằng sau các instance `HttpClient` mà bạn nhận được — nó tái sử dụng handler trong một khoảng thời gian, rồi luân phiên tạo handler mới, nhờ vậy vừa tránh socket exhaustion (không mở kết nối mới liên tục) vừa tránh vấn đề DNS cũ (handler cũ bị loại bỏ định kỳ, buộc kết nối mới phải resolve DNS lại).

Đăng ký bằng `AddHttpClient()` trong `Program.cs`, sau đó tiêm `IHttpClientFactory` (hoặc client đã đặt tên — xem dưới) vào nơi cần dùng:

```csharp title="Program.cs"
// test:compile dang ky IHttpClientFactory co ban va tiem vao endpoint
var builder = WebApplication.CreateBuilder(args);

// Dang ky: them IHttpClientFactory vao DI container.
builder.Services.AddHttpClient();

var app = builder.Build();

app.MapGet("/weather", async (IHttpClientFactory factory) =>
{
    // Tao mot HttpClient tu factory - factory quan ly handler ben duoi, KHONG phai ban tu new().
    var client = factory.CreateClient();
    var result = await client.GetStringAsync("https://example.com");
    return result;
});

app.Run();
```

Cách phổ biến hơn (và khuyến nghị) là đăng ký một **named client** hoặc **typed client** để cấu hình sẵn `BaseAddress`, header mặc định, hoặc timeout tại một chỗ duy nhất:

```csharp title="Program.cs"
// test:compile named client: dang ky mot lan, cau hinh san BaseAddress, dung o nhieu noi
var builder = WebApplication.CreateBuilder(args);

// "WeatherApi" la ten dinh danh client nay - dat cau hinh mot lan, dung nhieu lan.
builder.Services.AddHttpClient("WeatherApi", client =>
{
    client.BaseAddress = new Uri("https://api.weather.example/");
});

var app = builder.Build();

app.MapGet("/weather", async (IHttpClientFactory factory) =>
{
    // CreateClient("WeatherApi") tra ve client da co san BaseAddress o tren.
    var client = factory.CreateClient("WeatherApi");
    var result = await client.GetStringAsync("today"); // ket hop voi BaseAddress -> full URL
    return result;
});

app.Run();
```

**Điều gì xảy ra khi dùng sai:** nếu bạn gọi `factory.CreateClient("TenSai")` với một tên chưa từng đăng ký bằng `AddHttpClient("TenSai", ...)`, bạn **không** nhận được exception — `IHttpClientFactory` âm thầm trả về một `HttpClient` **mặc định, không có cấu hình gì** (không `BaseAddress`, không header). Endpoint vẫn chạy nhưng `client.GetStringAsync("today")` (URL tương đối, không có `BaseAddress`) ném:

```text title="Ngoại lệ runtime khi thiếu BaseAddress"
System.InvalidOperationException: An invalid request URI was provided. Either the
request URI must be an absolute URI or BaseAddress must be set.
```

Đây là lỗi runtime cụ thể, xảy ra ngay khi gọi, không phải lỗi biên dịch — vì tên client chỉ là chuỗi (magic string), không được kiểm tra lúc biên dịch.

---

## 3. Gọi GET và đọc JSON qua `GetFromJsonAsync`

**Định nghĩa:** `GetFromJsonAsync<T>` là phương thức mở rộng (extension method) của `HttpClient` (trong namespace `System.Net.Http.Json`), thực hiện một request `GET`, rồi tự động **deserialize** phần thân JSON của response thành kiểu `T` bạn chỉ định — gộp hai bước (gọi HTTP + parse JSON) thành một lời gọi duy nhất.

Ví dụ tối thiểu — chỉ minh hoạ GET + đọc JSON, không trộn xử lý lỗi:

```csharp title="Program.cs"
// test:compile GetFromJsonAsync<T> - GET + deserialize JSON trong mot loi goi
var builder = WebApplication.CreateBuilder(args);

builder.Services.AddHttpClient("WeatherApi", client =>
{
    client.BaseAddress = new Uri("https://api.weather.example/");
});

var app = builder.Build();

app.MapGet("/weather-today", async (IHttpClientFactory factory) =>
{
    var client = factory.CreateClient("WeatherApi");

    // GetFromJsonAsync<T>: goi GET "today", parse body JSON thanh WeatherReport.
    var report = await client.GetFromJsonAsync<WeatherReport>("today");

    return report;
});

app.Run();

// Ten thuoc tinh phai khop (khong phan biet hoa/thuong) voi field JSON tra ve tu API ngoai.
sealed record WeatherReport(string City, double TemperatureCelsius);
```

Nếu API `https://api.weather.example/today` trả về `{"city": "Hanoi", "temperatureCelsius": 32.5}`, `report` sẽ là `WeatherReport("Hanoi", 32.5)` — `System.Text.Json` (bộ deserializer mặc định) tự động khớp tên không phân biệt hoa/thường.

**Điều gì xảy ra khi dùng sai:** nếu response trả về body **rỗng** hoặc không phải JSON hợp lệ (ví dụ server trả HTML trang lỗi 500 thay vì JSON), `GetFromJsonAsync<T>` ném:

```text title="Ngoại lệ runtime khi body khong phai JSON hop le"
System.Text.Json.JsonException: The input does not contain any JSON tokens.
Expected the input to start with a valid JSON token, when isFinalBlock is true.
```

Đây cũng là lý do quan trọng: `GetFromJsonAsync` **giả định** response thành công (status 2xx) và có JSON hợp lệ — nó không tự kiểm tra status code trước khi parse. Mục 5 (xử lý lỗi HTTP) giải thích cách kiểm tra status code **trước** khi tin tưởng body là JSON.

---

## 4. Gửi POST và đọc JSON trả về qua `PostAsJsonAsync`

**Định nghĩa:** `PostAsJsonAsync<T>` là phương thức mở rộng thực hiện request `POST`, tự động **serialize** một object C# thành JSON để làm body của request — kết hợp với `ReadFromJsonAsync<T>` trên response để đọc kết quả trả về, gộp "serialize request + gửi + deserialize response" thành các bước rõ ràng.

Ví dụ tối thiểu — chỉ minh hoạ POST + đọc JSON trả về:

```csharp title="Program.cs"
// test:compile PostAsJsonAsync - serialize object C# thanh JSON, gui POST, doc JSON tra ve
var builder = WebApplication.CreateBuilder(args);

builder.Services.AddHttpClient("OrderApi", client =>
{
    client.BaseAddress = new Uri("https://api.orders.example/");
});

var app = builder.Build();

app.MapPost("/place-order", async (IHttpClientFactory factory, OrderRequest order) =>
{
    var client = factory.CreateClient("OrderApi");

    // PostAsJsonAsync: serialize "order" thanh JSON, gui POST toi "orders".
    var response = await client.PostAsJsonAsync("orders", order);

    // ReadFromJsonAsync<T>: doc body cua response, deserialize thanh OrderConfirmation.
    var confirmation = await response.Content.ReadFromJsonAsync<OrderConfirmation>();

    return confirmation;
});

app.Run();

sealed record OrderRequest(string ProductId, int Quantity);
sealed record OrderConfirmation(string OrderId, string Status);
```

Gọi `POST /place-order` với body `{"productId": "SKU-1", "quantity": 2}` sẽ gửi đúng JSON đó tới `https://api.orders.example/orders`, rồi đọc JSON server trả về (ví dụ `{"orderId": "ORD-99", "status": "Confirmed"}`) thành `OrderConfirmation`.

**Điều gì xảy ra khi dùng sai:** nếu bạn gọi `response.Content.ReadFromJsonAsync<OrderConfirmation>()` nhưng API đích trả về lỗi (ví dụ 400 Bad Request với body `{"error": "Invalid product"}` — cấu trúc **khác** `OrderConfirmation`), việc deserialize vẫn **có thể chạy** nhưng tạo ra object với các thuộc tính rỗng/mặc định (`OrderId = null, Status = null`) thay vì ném lỗi rõ ràng — vì cấu trúc JSON `{"error": "..."}` không khớp thuộc tính nào của `OrderConfirmation`, `System.Text.Json` không báo lỗi, chỉ để nguyên giá trị mặc định. Đây là lỗi âm thầm nguy hiểm: code tưởng đơn hàng thành công nhưng thực ra server đã từ chối. Luôn kiểm tra `response.IsSuccessStatusCode` **trước** khi đọc JSON — xem mục 6.

---

## 5. Xử lý timeout: định nghĩa và cấu hình `Timeout`

**Định nghĩa:** Timeout trong HTTP client là khoảng thời gian tối đa client chờ phản hồi từ server trước khi **tự huỷ** request và báo lỗi, thay vì chờ vô thời hạn — cần thiết vì server bên ngoài có thể treo, mạng có thể chậm bất thường, và một request treo mãi sẽ chiếm tài nguyên (thread, kết nối) của ứng dụng bạn.

Cấu hình `Timeout` khi đăng ký named client, rồi bắt lỗi khi hết hạn:

```csharp title="Program.cs"
// test:compile cau hinh Timeout va bat loi khi het han
var builder = WebApplication.CreateBuilder(args);

builder.Services.AddHttpClient("SlowApi", client =>
{
    client.BaseAddress = new Uri("https://api.slow.example/");
    client.Timeout = TimeSpan.FromSeconds(5); // qua 5 giay khong co response -> huy request
});

var app = builder.Build();

app.MapGet("/slow-data", async (IHttpClientFactory factory) =>
{
    var client = factory.CreateClient("SlowApi");
    try
    {
        var data = await client.GetStringAsync("data");
        return Results.Ok(data);
    }
    catch (TaskCanceledException)
    {
        // Timeout cua HttpClient bieu hien qua TaskCanceledException (khong phai TimeoutException).
        return Results.Problem(
            detail: "API bên ngoài không phản hồi trong 5 giây.",
            statusCode: StatusCodes.Status504GatewayTimeout);
    }
});

app.Run();
```

**Điều gì xảy ra khi dùng sai:**

- **Không đặt `Timeout` gì cả:** giá trị mặc định của `HttpClient.Timeout` là **100 giây**. Với một API đích bị treo, request của bạn (và thread/tài nguyên xử lý nó) bị giữ tới gần 2 phút trước khi có phản hồi lỗi — đủ lâu để làm nghẽn cả hệ thống nếu nhiều request cùng gọi API treo đó cùng lúc.
- **Bắt sai loại exception:** khi `HttpClient.Timeout` hết hạn, .NET ném `TaskCanceledException` (kế thừa từ `OperationCanceledException`), **không phải** `TimeoutException`. Nếu code chỉ `catch (TimeoutException)`, exception timeout thật sự sẽ **không bị bắt**, lọt ra ngoài như một lỗi chưa xử lý (unhandled exception), khiến endpoint trả về lỗi 500 chung chung thay vì phản hồi 504 có ý nghĩa như ví dụ trên.
- **Nhầm lẫn với hủy do client ngắt kết nối:** `TaskCanceledException` cũng được ném khi chính **caller** (trình duyệt, client gọi API của bạn) đóng kết nối giữa chừng (ví dụ người dùng đóng tab) — thông qua `HttpContext.RequestAborted`. Để phân biệt hai trường hợp, kiểm tra `exception.CancellationToken == cancellationTokenCuaTimeout` hoặc dùng `CancellationTokenSource` riêng cho timeout thay vì chỉ dựa vào `HttpClient.Timeout` mặc định.

---

## 6. Xử lý lỗi HTTP: `IsSuccessStatusCode` và `EnsureSuccessStatusCode`

**Định nghĩa:** `IsSuccessStatusCode` là thuộc tính `bool` trên `HttpResponseMessage` cho biết status code trả về có nằm trong khoảng 200-299 hay không, còn `EnsureSuccessStatusCode()` là phương thức **ném exception ngay** nếu status code **không** thành công — hai công cụ để kiểm tra kết quả HTTP **trước khi** tin tưởng và đọc body response.

Ví dụ tối thiểu — kiểm tra thủ công bằng `IsSuccessStatusCode`:

```csharp title="Program.cs"
// test:compile kiem tra IsSuccessStatusCode truoc khi doc body
var builder = WebApplication.CreateBuilder(args);

builder.Services.AddHttpClient("OrderApi", client =>
{
    client.BaseAddress = new Uri("https://api.orders.example/");
});

var app = builder.Build();

app.MapGet("/order-status/{id}", async (string id, IHttpClientFactory factory) =>
{
    var client = factory.CreateClient("OrderApi");
    var response = await client.GetAsync($"orders/{id}");

    // Kiem tra TRUOC khi doc JSON - khong tin tuong body neu status khong thanh cong.
    if (!response.IsSuccessStatusCode)
    {
        return Results.Problem(
            detail: $"API bên ngoài trả về {(int)response.StatusCode}.",
            statusCode: (int)response.StatusCode);
    }

    var order = await response.Content.ReadFromJsonAsync<OrderConfirmation>();
    return Results.Ok(order);
});

app.Run();

sealed record OrderConfirmation(string OrderId, string Status);
```

Cách thứ hai — `EnsureSuccessStatusCode()` khi bạn muốn coi lỗi HTTP là **exception** (phù hợp khi lỗi này nên chặn luồng xử lý ngay, không cần xử lý riêng từng status code):

```csharp title="Program.cs"
// test:compile EnsureSuccessStatusCode - nem exception ngay neu status khong thanh cong
var builder = WebApplication.CreateBuilder(args);

builder.Services.AddHttpClient("OrderApi", client =>
{
    client.BaseAddress = new Uri("https://api.orders.example/");
});

var app = builder.Build();

app.MapGet("/order-status/{id}", async (string id, IHttpClientFactory factory) =>
{
    var client = factory.CreateClient("OrderApi");
    var response = await client.GetAsync($"orders/{id}");

    // Neu status khong phai 2xx, ném HttpRequestException ngay tai day.
    response.EnsureSuccessStatusCode();

    var order = await response.Content.ReadFromJsonAsync<OrderConfirmation>();
    return Results.Ok(order);
});

app.Run();

sealed record OrderConfirmation(string OrderId, string Status);
```

**Điều gì xảy ra khi dùng sai:**

- **Bỏ qua kiểm tra hoàn toàn** (gọi thẳng `GetFromJsonAsync` hoặc `ReadFromJsonAsync` không kiểm tra status trước — như cảnh báo ở mục 3 và 4): nếu API trả về lỗi 500 với body HTML (trang lỗi mặc định của server), việc parse JSON ném `JsonException` gây nhầm lẫn — lỗi thật sự là "API đích lỗi 500", nhưng thông báo lại là "JSON không hợp lệ", khiến việc debug đi sai hướng.
- **`EnsureSuccessStatusCode()` khi status không thành công** ném:

    ```text title="Ngoại lệ runtime tu EnsureSuccessStatusCode"
    System.Net.Http.HttpRequestException: Response status code does not indicate
    success: 404 (Not Found).
    ```

    Exception này chứa `StatusCode` (thuộc tính `HttpRequestException.StatusCode` từ .NET 5 trở lên) — có thể đọc lại để trả response phù hợp cho client gọi tới ứng dụng của bạn, nhưng nếu không `catch` exception này ở đâu đó, nó lọt ra thành lỗi 500 chung chung ở endpoint của bạn dù lỗi gốc là 404 từ API bên ngoài — sai lệch ngữ nghĩa REST (client của bạn nên biết đó là 404, không phải 500 do server bạn lỗi).
- **Đọc `response.Content` hai lần:** `HttpContent` là một stream chỉ đọc được **một lần**. Gọi `ReadFromJsonAsync` hoặc `ReadAsStringAsync` lần thứ hai trên cùng một `response.Content` (ví dụ để log rồi lại parse) ném lỗi hoặc trả về chuỗi rỗng tuỳ implementation — nếu cần dùng lại, đọc một lần thành `string` hoặc `byte[]` rồi xử lý từ biến đó.

---

## 7. Giới thiệu ngắn Polly cho retry và circuit breaker

**Định nghĩa:** Polly là một thư viện .NET chuyên xử lý **resilience** (khả năng phục hồi) cho các lời gọi có thể thất bại tạm thời — cung cấp sẵn các "chính sách" (policy) như **retry** (thử lại tự động khi thất bại), **circuit breaker** (tạm ngừng gọi hẳn một API đang lỗi liên tục, tránh dồn thêm tải vào một dịch vụ đã sập), và **timeout** — tích hợp trực tiếp vào `IHttpClientFactory` qua gói `Microsoft.Extensions.Http.Polly`.

```csharp title="Program.cs"
// test:skip minh hoa khai niem Polly - can package ngoai Microsoft.Extensions.Http.Polly, khong co san trong `dotnet new web` tran
var builder = WebApplication.CreateBuilder(args);

builder.Services.AddHttpClient("OrderApi", client =>
{
    client.BaseAddress = new Uri("https://api.orders.example/");
})
// Retry: thu lai 3 lan, cho tang dan (exponential backoff) giua moi lan, khi request that bai tam thoi.
.AddTransientHttpErrorPolicy(policy => policy.WaitAndRetryAsync(
    3, attempt => TimeSpan.FromSeconds(Math.Pow(2, attempt))))
// Circuit breaker: sau 5 loi lien tiep, "mo mach" - tam ngung goi API nay trong 30 giay,
// tra loi ngay lap tuc thay vi tiep tuc thu (tranh don them tai vao dich vu dang sap).
.AddTransientHttpErrorPolicy(policy => policy.CircuitBreakerAsync(
    5, TimeSpan.FromSeconds(30)));

var app = builder.Build();
app.Run();
```

**Vì sao cần cả hai chính sách này thay vì tự viết vòng lặp `try/catch` thủ công:**

- **Retry** giải quyết lỗi **tạm thời** (transient) — ví dụ mất gói tin mạng thoáng qua, server đích quá tải trong 1 giây rồi hồi phục. Tự viết vòng lặp retry thủ công dễ quên các chi tiết quan trọng: thời gian chờ tăng dần (backoff) để tránh dồn tải, giới hạn số lần thử, và **chỉ** retry với lỗi tạm thời (không retry với lỗi 400 Bad Request — request sai thì thử lại bao nhiêu lần cũng sai).
- **Circuit breaker** giải quyết vấn đề khác: khi API đích đã **thật sự sập** (không phải lỗi thoáng qua), tiếp tục retry chỉ làm chậm ứng dụng của bạn (mỗi request đều phải chờ hết chuỗi retry trước khi báo lỗi) và dồn thêm tải vào một dịch vụ đang cố phục hồi. Circuit breaker "ngắt mạch" tạm thời — trả lỗi ngay lập tức mà không gọi mạng — cho tới khi hết thời gian chờ, rồi thử lại một lần để xem dịch vụ đã hồi phục chưa.
- Không dùng Polly, bạn phải tự code cả hai cơ chế này bằng tay cho **mỗi** `HttpClient` trong ứng dụng — dễ sai (đặc biệt là thời gian backoff và ngưỡng circuit breaker), khó bảo trì, và không có sẵn observability (Polly có thể log mỗi lần retry/circuit mở qua các event callback tích hợp sẵn).

Chương này không đi sâu cấu hình Polly chi tiết (đó là nội dung của chương resilience nâng cao) — mục tiêu ở đây chỉ là nhận biết **khi nào** cần nó: bất kỳ lúc nào ứng dụng của bạn gọi một API bên ngoài mà bạn không kiểm soát được độ ổn định (mạng, dịch vụ bên thứ ba, microservice khác).

---

## Cạm bẫy & thực chiến

- **`new HttpClient()` trong mỗi request/mỗi lần gọi:** gây socket exhaustion dưới tải cao (mục 1). Luôn dùng `IHttpClientFactory` qua `AddHttpClient`.
- **`static readonly HttpClient` dùng chung toàn app mà không qua factory:** tránh được socket exhaustion nhưng gây vấn đề DNS cũ — kết nối bị cache mãi mãi, không phát hiện khi server đích đổi IP. `IHttpClientFactory` giải quyết cả hai vấn đề nhờ luân phiên handler định kỳ.
- **Gọi `GetFromJsonAsync`/`ReadFromJsonAsync` mà không kiểm tra status code trước:** nếu API trả lỗi (thường kèm body không phải JSON hợp lệ hoặc cấu trúc JSON khác), bạn nhận `JsonException` gây nhầm lẫn, hoặc tệ hơn — nhận một object với toàn giá trị mặc định mà tưởng là dữ liệu thật.
- **Bắt `TimeoutException` thay vì `TaskCanceledException`:** timeout của `HttpClient` ném `TaskCanceledException`, không phải `TimeoutException` — bắt sai loại khiến exception lọt ra ngoài thành lỗi 500 không kiểm soát.
- **Đọc `response.Content` nhiều lần:** `HttpContent` là stream một-lần-dùng — đọc lần hai gây lỗi hoặc dữ liệu rỗng.
- **Quên đặt `BaseAddress` và gọi `CreateClient("TenSai")` với tên chưa đăng ký:** nhận `HttpClient` mặc định không cấu hình, ném `InvalidOperationException` khi gọi với URL tương đối.
- **Dùng `Timeout` mặc định 100 giây cho mọi API bên ngoài:** với API quan trọng, đặt timeout ngắn hơn (vài giây) để tránh giữ tài nguyên quá lâu khi dịch vụ đích treo.

---

## Bài tập

**Bài 1 (có giàn giáo).** Đoạn dưới gọi một API thời tiết nhưng không xử lý trường hợp API trả lỗi. Sửa để trả về `Results.Problem` với đúng status code khi thất bại, thay vì để exception lọt ra ngoài không kiểm soát.

```csharp title="Program.cs"
// test:compile bai 1 - can sua: chua kiem tra loi HTTP
var builder = WebApplication.CreateBuilder(args);

builder.Services.AddHttpClient("WeatherApi", client =>
{
    client.BaseAddress = new Uri("https://api.weather.example/");
});

var app = builder.Build();

app.MapGet("/weather-today", async (IHttpClientFactory factory) =>
{
    var client = factory.CreateClient("WeatherApi");
    var report = await client.GetFromJsonAsync<WeatherReport>("today");
    return Results.Ok(report);
});

app.Run();

sealed record WeatherReport(string City, double TemperatureCelsius);
```

Gợi ý giàn giáo: đổi `GetFromJsonAsync` (không kiểm tra status) thành `GetAsync` + kiểm tra `IsSuccessStatusCode` trước khi đọc JSON.

??? success "Lời giải + vì sao"
    ```csharp title="Program.cs"
    // test:compile bai 1 da sua - kiem tra IsSuccessStatusCode truoc khi doc JSON
    var builder = WebApplication.CreateBuilder(args);

    builder.Services.AddHttpClient("WeatherApi", client =>
    {
        client.BaseAddress = new Uri("https://api.weather.example/");
    });

    var app = builder.Build();

    app.MapGet("/weather-today", async (IHttpClientFactory factory) =>
    {
        var client = factory.CreateClient("WeatherApi");
        var response = await client.GetAsync("today");

        if (!response.IsSuccessStatusCode)
        {
            return Results.Problem(
                detail: $"API thời tiết trả về {(int)response.StatusCode}.",
                statusCode: (int)response.StatusCode);
        }

        var report = await response.Content.ReadFromJsonAsync<WeatherReport>();
        return Results.Ok(report);
    });

    app.Run();

    sealed record WeatherReport(string City, double TemperatureCelsius);
    ```

    **Vì sao:** `GetFromJsonAsync` giả định response luôn thành công và luôn là JSON hợp lệ — nếu API thời tiết trả về 503 Service Unavailable, `GetFromJsonAsync` sẽ ném `JsonException` khó hiểu thay vì cho bạn cơ hội trả về đúng status 503 cho client của bạn. Đổi sang `GetAsync` + kiểm tra `IsSuccessStatusCode` cho phép bạn kiểm soát chính xác điều gì xảy ra ở từng nhánh kết quả.

**Bài 2 (thiết kế).** Bạn cần gọi một API thanh toán bên ngoài (`https://api.payment.example/`) để xác nhận giao dịch. Yêu cầu: (a) dùng `IHttpClientFactory` với named client tên `"PaymentApi"`, (b) timeout 10 giây, (c) nếu timeout xảy ra, trả về lỗi 504 kèm thông điệp rõ ràng, (d) nếu API trả lỗi 4xx/5xx, trả về đúng status code đó kèm chi tiết. Viết đăng ký và endpoint.

??? success "Lời giải + vì sao"
    ```csharp title="Program.cs"
    // test:compile bai 2 - named client + timeout + xu ly ca hai loai loi (timeout va HTTP status)
    var builder = WebApplication.CreateBuilder(args);

    builder.Services.AddHttpClient("PaymentApi", client =>
    {
        client.BaseAddress = new Uri("https://api.payment.example/");
        client.Timeout = TimeSpan.FromSeconds(10);
    });

    var app = builder.Build();

    app.MapPost("/confirm-payment", async (IHttpClientFactory factory, PaymentRequest payment) =>
    {
        var client = factory.CreateClient("PaymentApi");

        try
        {
            var response = await client.PostAsJsonAsync("confirm", payment);

            if (!response.IsSuccessStatusCode)
            {
                var errorBody = await response.Content.ReadAsStringAsync();
                return Results.Problem(
                    detail: $"API thanh toán từ chối: {errorBody}",
                    statusCode: (int)response.StatusCode);
            }

            var confirmation = await response.Content.ReadFromJsonAsync<PaymentConfirmation>();
            return Results.Ok(confirmation);
        }
        catch (TaskCanceledException)
        {
            return Results.Problem(
                detail: "API thanh toán không phản hồi trong 10 giây.",
                statusCode: StatusCodes.Status504GatewayTimeout);
        }
    });

    app.Run();

    sealed record PaymentRequest(string TransactionId, decimal Amount);
    sealed record PaymentConfirmation(string TransactionId, string Status);
    ```

    **Vì sao:** named client `"PaymentApi"` gom `BaseAddress` và `Timeout` vào một chỗ đăng ký duy nhất (mục 2), tránh lặp lại cấu hình ở nhiều endpoint. `try/catch (TaskCanceledException)` bắt đúng loại exception mà `HttpClient.Timeout` thực sự ném (mục 5), không phải `TimeoutException`. Kiểm tra `IsSuccessStatusCode` trước khi đọc JSON (mục 6) đảm bảo lỗi từ API thanh toán (ví dụ thẻ bị từ chối, trả 402) được chuyển đúng ngữ nghĩa REST cho client gọi ứng dụng của bạn, thay vì bị nuốt thành 500 chung chung hoặc gây `JsonException` khó hiểu.

---

## Tự kiểm tra

1. Vì sao gọi `new HttpClient()` bên trong mỗi request lại nguy hiểm dưới tải cao?

    ??? note "Đáp án"
        Mỗi `new HttpClient()` mở một socket TCP riêng; sau khi đóng, socket kẹt ở trạng thái `TIME_WAIT` trong một khoảng thời gian trước khi hệ điều hành thu hồi. Dưới tải cao, số socket `TIME_WAIT` tích luỹ nhanh hơn tốc độ giải phóng, dẫn tới cạn cổng khả dụng (socket exhaustion) và ném `SocketException` dù server đích vẫn hoạt động bình thường.

2. `IHttpClientFactory` giải quyết đồng thời hai vấn đề nào so với `new HttpClient()` mỗi request và so với một `static HttpClient` dùng chung mãi mãi?

    ??? note "Đáp án"
        So với `new HttpClient()` mỗi request: tránh socket exhaustion nhờ tái sử dụng handler. So với `static HttpClient` dùng chung mãi mãi: tránh vấn đề DNS cũ (stale DNS), vì factory luân phiên loại bỏ và tạo handler mới định kỳ, buộc kết nối mới phải resolve DNS lại.

3. `GetFromJsonAsync<T>` sẽ ném exception gì nếu body response không phải JSON hợp lệ (ví dụ server trả về trang HTML lỗi)?

    ??? note "Đáp án"
        `System.Text.Json.JsonException`. Đây là lý do quan trọng phải kiểm tra `IsSuccessStatusCode` trước khi tin tưởng body là JSON hợp lệ.

4. Khi `HttpClient.Timeout` hết hạn, loại exception nào được ném ra, và tại sao bắt nhầm `TimeoutException` là một lỗi phổ biến?

    ??? note "Đáp án"
        `TaskCanceledException` (kế thừa từ `OperationCanceledException`), không phải `TimeoutException`. Nếu code chỉ `catch (TimeoutException)`, exception timeout thật sự sẽ không được bắt và lọt ra ngoài thành lỗi chưa xử lý.

5. `EnsureSuccessStatusCode()` làm gì, và nó ném loại exception gì khi status code không phải 2xx?

    ??? note "Đáp án"
        Nó kiểm tra status code của response; nếu không nằm trong khoảng 200-299, ném `HttpRequestException` với thông điệp mô tả status code cụ thể (ví dụ "404 Not Found"). Exception này có thuộc tính `StatusCode` để đọc lại status gốc.

6. Vì sao đăng ký `AddHttpClient("PaymentApi", ...)` với `BaseAddress` sẵn lại tốt hơn gọi `factory.CreateClient()` (không tên) rồi tự set `BaseAddress` ở mỗi nơi dùng?

    ??? note "Đáp án"
        Named client gom cấu hình (BaseAddress, Timeout, header mặc định) vào **một chỗ đăng ký duy nhất**, tránh lặp lại và sai lệch cấu hình giữa các nơi dùng. Nếu quên set `BaseAddress` ở một endpoint dùng client không tên, gọi URL tương đối sẽ ném `InvalidOperationException` ngay lúc chạy.

7. Polly giải quyết vấn đề gì mà retry/circuit breaker tự viết tay dễ làm sai?

    ??? note "Đáp án"
        Retry tự viết tay dễ quên backoff tăng dần (gây dồn tải) và dễ retry nhầm cả lỗi vĩnh viễn (như 400 Bad Request). Circuit breaker tự viết tay khó cài đặt đúng ngưỡng và thời gian ngắt mạch. Polly cung cấp sẵn cả hai chính sách đã được kiểm chứng, tích hợp trực tiếp vào `IHttpClientFactory`, kèm observability qua callback.

8. `response.Content.ReadFromJsonAsync<T>()` gọi hai lần trên cùng một `response` sẽ có vấn đề gì?

    ??? note "Đáp án"
        `HttpContent` là một stream chỉ đọc được một lần. Đọc lần thứ hai sẽ gây lỗi hoặc trả về dữ liệu rỗng tuỳ implementation — nếu cần dùng lại nội dung, phải đọc một lần thành biến (`string`/`byte[]`) rồi xử lý từ biến đó.

---

??? abstract "DEEP DIVE: typed client, `HttpClientHandler` tuỳ biến, và `IHttpClientFactory` với DI phức tạp hơn"
    Ngoài named client (`CreateClient("Ten")`), `IHttpClientFactory` còn hỗ trợ **typed client** — một class C# nhận `HttpClient` qua constructor, đóng gói toàn bộ logic gọi API bên ngoài vào một service riêng thay vì rải rác trong endpoint:

    ```csharp title="Program.cs"
    // test:compile typed client - dong goi logic goi API vao mot class rieng
    var builder = WebApplication.CreateBuilder(args);

    builder.Services.AddHttpClient<WeatherApiClient>(client =>
    {
        client.BaseAddress = new Uri("https://api.weather.example/");
    });

    var app = builder.Build();

    // Tiem thang WeatherApiClient - DI tu dong tao HttpClient da cau hinh va truyen vao constructor.
    app.MapGet("/weather-today", async (WeatherApiClient weatherClient) =>
        await weatherClient.GetTodayAsync());

    app.Run();

    sealed record WeatherReport(string City, double TemperatureCelsius);

    sealed class WeatherApiClient(HttpClient httpClient)
    {
        public async Task<WeatherReport?> GetTodayAsync() =>
            await httpClient.GetFromJsonAsync<WeatherReport>("today");
    }
    ```

    Typed client được đăng ký với lifetime **Transient** theo mặc định của `AddHttpClient<T>` — mỗi lần resolve tạo một instance `WeatherApiClient` mới, nhưng `HttpMessageHandler` bên dưới vẫn được `IHttpClientFactory` tái sử dụng theo pool như named client, nên không gây socket exhaustion.

    Với các tình huống cần tuỳ biến sâu hơn (ví dụ bỏ qua kiểm tra chứng chỉ TLS trong môi trường test, hoặc thêm handler log request/response), `AddHttpClient` cho phép gắn thêm `ConfigurePrimaryHttpMessageHandler` để tuỳ biến `HttpClientHandler`, và `AddHttpMessageHandler<T>` để chèn thêm các "delegating handler" xử lý xuyên suốt (cross-cutting) như đính kèm token xác thực vào mọi request tự động — đây là nền tảng để hiểu cách các thư viện xác thực (ví dụ tự động gắn Bearer token) tích hợp với `IHttpClientFactory` mà không cần sửa code gọi API ở từng nơi.

**Tiếp theo →** [P4 · JWT (canonical)](../p4-bao-mat/jwt.md)
