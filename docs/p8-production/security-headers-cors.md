---
tier: core
status: core
owner: core-team
verified_on: "2026-07-03"
dotnet_version: "10.0"
bloom: áp dụng
requires: [p8-resilience]
est_minutes_fast: 26
---

# CORS & Security Headers

!!! info "bạn đang ở đây"
    cần trước: bạn đã biết pipeline middleware là các lớp lồng nhau và biết vị trí gọi `app.Use...()` trong `Program.cs` quyết định thứ tự thực thi (chương middleware), và đã nghe giới thiệu ngắn về Polly ở chương gọi api bên ngoài rồi vừa học sâu retry/circuit breaker ở chương resilience patterns.
    mở khoá: sau chương này bạn hiểu đúng vì sao frontend gọi API bị chặn bởi lỗi CORS trong console trình duyệt (không phải lỗi server), biết cấu hình `AddCors` đúng cách, và biết thêm các HTTP header bảo mật cơ bản — nền tảng để triển khai API production phục vụ được frontend chạy trên domain khác.

> **Mục tiêu (đo được):** sau chương này bạn **giải thích** được vì sao CORS là cơ chế của trình duyệt (không phải server), **phân biệt** được khi nào hai request có "origin khác nhau", **áp dụng** đúng `AddCors`/`UseCors` với policy `WithOrigins`, **nhận diện** được sai lầm `AllowAnyOrigin()` kết hợp `AllowCredentials()`, và **thêm** được các security header cơ bản (HSTS, `X-Content-Type-Options`, giới thiệu CSP) vào pipeline.
>
> Chương này không dạy lại `app.Use(...)`/thứ tự middleware từ đầu — bạn đã học kỹ điều đó ở chương middleware. Trọng tâm ở đây là hiểu đúng **bản chất** của CORS (một cơ chế phía trình duyệt, dễ bị hiểu nhầm là lỗi server) và biết dùng đúng các công cụ có sẵn (`AddCors`, `UseCors`, `UseHsts`) để cấu hình cho tình huống thực tế — một API phục vụ frontend chạy trên domain/port khác.

---

## 0. Đoán nhanh trước khi học

Bạn có một frontend React chạy tại `http://localhost:3000` gọi `fetch("http://localhost:5000/api/products")` tới một API ASP.NET Core đang chạy tại `http://localhost:5000`. API hoạt động hoàn toàn bình thường — bạn test bằng Postman, request trả về `200 OK` với đúng dữ liệu JSON. Nhưng khi gọi từ code JavaScript trong trình duyệt, console báo lỗi đỏ dạng "has been blocked by CORS policy", và code JavaScript không nhận được dữ liệu.

??? question "Đoán trước, đáp án ở dưới"
    Gợi ý: Postman không phải trình duyệt. Nghĩ về việc ai đang thực sự chặn request này — có phải API của bạn trả lỗi không, hay có một thứ khác đứng giữa can thiệp?

??? note "Đáp án"
    API của bạn **không hề trả lỗi** — nếu bạn xem tab Network của trình duyệt, request vẫn có thể thấy status `200 OK` với đúng dữ liệu JSON trả về từ server. Thứ chặn ở đây là **chính trình duyệt** — nó nhận được response nhưng **từ chối giao dữ liệu đó cho code JavaScript** đang chạy trên trang `localhost:3000`, vì API tại `localhost:5000` không có header nào nói rằng nó "cho phép" origin `localhost:3000` đọc response. Postman không bị chặn vì Postman không phải trình duyệt và không thực thi chính sách CORS — đây là lý do "test bằng Postman OK nhưng frontend vẫn lỗi" là tình huống rất phổ biến khiến người mới nhầm là lỗi ở server. Mục 1 giải thích chính xác cơ chế này, mục 2 định nghĩa "origin", và mục 3 giới thiệu `AddCors` — công cụ để server "cho phép tường minh" đúng origin cần được phép.

---

## 1. CORS là gì: cơ chế của trình duyệt, không phải của server

**Định nghĩa:** CORS (Cross-Origin Resource Sharing — chia sẻ tài nguyên giữa các origin khác nhau) là một cơ chế bảo mật được **trình duyệt** (Chrome, Firefox, Edge...) thực thi, mặc định **chặn** code JavaScript đang chạy trên một trang web đọc response từ một API có **origin khác** với chính trang web đó — trừ khi API đó trả về header tường minh cho phép origin gọi tới nó.

Điểm quan trọng nhất cần khắc đúng ngay từ đầu: **CORS không phải là một lớp bảo mật của server**, và nó **không** ngăn được kẻ tấn công gọi trực tiếp API của bạn bằng công cụ như Postman, `curl`, hay một script Python. Tất cả các công cụ đó không thực thi chính sách CORS vì chúng không phải trình duyệt đang chạy trang web của bên khác. CORS chỉ giải quyết đúng một bài toán: **ngăn code JavaScript của một trang web A lặng lẽ đọc dữ liệu từ API của trang web B mà B không đồng ý**, thường để bảo vệ người dùng khỏi các trang web độc hại âm thầm gọi API ngân hàng/mạng xã hội bằng cookie đăng nhập sẵn có của người dùng trong trình duyệt.

Quay lại ví dụ ở mục 0: khi frontend `localhost:3000` gọi API `localhost:5000` bằng `fetch(...)`, trình tự thực tế diễn ra như sau:

1. Trình duyệt gửi request HTTP thật tới `localhost:5000/api/products`.
2. Server (API của bạn) xử lý bình thường, trả về `200 OK` kèm dữ liệu JSON — **server hoàn toàn không biết gì về CORS trừ khi bạn cấu hình**.
3. Trình duyệt **nhận được** response đầy đủ, nhưng trước khi giao dữ liệu đó cho đoạn code JavaScript đang `await fetch(...)`, nó kiểm tra: response có header `Access-Control-Allow-Origin` khớp với origin `localhost:3000` không?
4. Nếu **không có** header đó (vì server chưa cấu hình CORS), trình duyệt **âm thầm giữ lại response**, ném lỗi cho code JavaScript, và in dòng đỏ vào console — dù dữ liệu đã thực sự tới trình duyệt.

**Điều gì xảy ra khi thiếu cấu hình CORS (hậu quả cụ thể):** với một API thực sự dự định phục vụ frontend chạy trên domain khác (ví dụ SPA React deploy ở `https://app.congty.com` gọi API ở `https://api.congty.com`), thiếu `AddCors` khiến **toàn bộ chức năng của frontend ngừng hoạt động** ngay khi lên production — mọi lời gọi API từ trình duyệt đều bị chặn ở bước 3-4 trên, dù bản thân API hoàn toàn khoẻ mạnh và trả dữ liệu đúng. Đây là lớp lỗi đặc biệt khó debug cho người mới, vì log server hoàn toàn sạch (server đã trả `200 OK` thành công), lỗi chỉ xuất hiện ở console trình duyệt phía client — nhiều người tưởng nhầm là lỗi mạng hoặc lỗi server và đi debug sai hướng.

Sơ đồ dưới đây minh hoạ lại đúng bốn bước trên, làm rõ vị trí trình duyệt "chặn" nằm ở **sau** khi response đã về, không phải trước khi request được gửi đi:

```mermaid title="Trinh tu CORS: trinh duyet chan sau khi da nhan response"
sequenceDiagram
    participant JS as JavaScript (localhost:3000)
    participant TD as Trinh duyet
    participant API as API (localhost:5000)

    JS->>TD: fetch("http://localhost:5000/api/products")
    TD->>API: Gui request HTTP thuc su
    API->>TD: 200 OK + du lieu JSON (KHONG co header CORS)
    TD->>TD: Kiem tra: co header Access-Control-Allow-Origin khop khong?
    TD--xJS: KHONG giao du lieu - nem loi CORS vao console
```

**So sánh với trường hợp không có CORS tham gia (same-origin, cùng origin):** nếu frontend và API cùng chạy trên một origin (ví dụ cả hai đều phục vụ từ `https://app.congty.com`, API nằm ở path `/api/...` của cùng domain), trình duyệt **không** thực hiện bước kiểm tra ở bước 3-4 trên — mọi request tới cùng origin luôn được coi là an toàn theo mặc định (same-origin policy — chính sách gốc mà CORS được thiết kế để "nới lỏng có kiểm soát"). Đây là lý do nhiều ứng dụng nhỏ (frontend và API deploy chung một domain, chỉ khác path) không bao giờ gặp lỗi CORS — không phải vì họ cấu hình đúng, mà vì tình huống của họ không bao giờ chạm tới cơ chế CORS.

### 1.1 Một tình huống thực tế: "chỉ một số người dùng bị lỗi CORS, không phải tất cả"

Một biến thể khó debug hơn ví dụ ở mục 0: giả sử đội của bạn đã cấu hình CORS đúng cho origin `https://app.congty.com`, hoạt động tốt trong nhiều tháng. Bất ngờ, một số người dùng báo lỗi CORS trong console, nhưng đội QA thử lại trên máy của họ thì không tái hiện được lỗi. Nguyên nhân thường gặp trong tình huống này (không phải danh sách đầy đủ, chỉ là các khả năng phổ biến nhất cần kiểm tra theo thứ tự):

1. **Người dùng bị lỗi đang truy cập qua một domain/subdomain khác** với domain đã khai báo trong `WithOrigins` — ví dụ họ gõ `https://www.app.congty.com` (có `www.`) trong khi policy chỉ khai báo `https://app.congty.com` (không có `www.`) — đúng như mục 2.2 đã giải thích, đây là hai origin khác nhau về mặt chuỗi ký tự.
2. **Một tầng CDN/reverse proxy trung gian đang cache response cũ** (đã có `Access-Control-Allow-Origin` cho một origin khác) và phục vụ nhầm response đó cho origin hiện tại — liên quan tới header `Vary: Origin` được nhắc ở phần DEEP DIVE cuối bài.
3. **Server đang chạy nhiều instance phía sau load balancer, và một trong các instance đó đang chạy phiên bản code cũ** (chưa deploy đủ, hoặc deploy bị lỗi rolling update) chưa có cấu hình CORS mới nhất — người dùng bị điều hướng ngẫu nhiên tới instance cũ sẽ gặp lỗi, người khác được điều hướng tới instance mới thì không.

Việc liệt kê các khả năng theo thứ tự kiểm tra (thay vì đoán ngẫu nhiên) giúp thu hẹp phạm vi debug nhanh hơn — kiểm tra khả năng (1) đầu tiên vì dễ xác minh nhất (chỉ cần hỏi người dùng bị lỗi họ đang gõ URL nào), rồi mới tới các khả năng phức tạp hơn về hạ tầng.

---

## 2. Origin là gì: scheme + domain + port, đổi một trong ba là khác origin

**Định nghĩa:** Origin (nguồn gốc) của một URL được xác định bởi **ba phần**: scheme (giao thức, ví dụ `http` hoặc `https`), domain (tên miền, ví dụ `example.com`), và port (cổng, ví dụ `3000`, `443`) — chỉ cần **một trong ba phần này khác nhau**, trình duyệt coi đó là **hai origin khác nhau**, dù domain nhìn có vẻ "giống nhau" theo cảm nhận thông thường.

Bảng ví dụ cụ thể, so sánh với origin gốc `http://localhost:3000`:

| URL so sánh | Cùng scheme? | Cùng domain? | Cùng port? | Cùng origin? |
|---|---|---|---|---|
| `http://localhost:3000/products` | có | có | có | **CÙNG** (chỉ khác path, path không tính vào origin) |
| `http://localhost:5000` | có | có | không (5000 ≠ 3000) | **KHÁC** (port khác) |
| `https://localhost:3000` | không (https ≠ http) | có | có | **KHÁC** (scheme khác) |
| `http://127.0.0.1:3000` | có | không (`127.0.0.1` ≠ `localhost`, dù cùng trỏ tới máy) | có | **KHÁC** (domain khác về mặt chuỗi ký tự, dù cùng máy vật lý) |
| `http://app.example.com:3000` | có | không (`app.example.com` ≠ `localhost`) | có | **KHÁC** (domain khác) |
| `http://localhost:3000?tab=2` | có | có | có | **CÙNG** (chỉ khác query string, cũng không tính vào origin) |

**Điều gì xảy ra khi hiểu sai khái niệm origin:** một lỗi rất phổ biến là nghĩ `localhost:3000` và `127.0.0.1:3000` là "cùng một nơi" (vì cả hai đều trỏ tới máy của chính bạn khi phát triển) — trình duyệt coi đây là **hai origin khác nhau về mặt chuỗi ký tự**, dù về mặt mạng chúng trỏ tới đúng một máy. Nếu bạn cấu hình CORS chỉ cho phép `http://localhost:3000` nhưng đồng nghiệp mở frontend bằng `http://127.0.0.1:3000`, request của họ vẫn bị chặn CORS — dù "về mặt vật lý" đúng là cùng một máy đang gọi.

Path (đường dẫn sau domain, ví dụ `/products`, `/api/orders`) và query string (`?id=1`) **không** tính vào origin — hai URL chỉ khác path nhưng cùng scheme+domain+port vẫn là cùng một origin, không bị CORS chặn vì lý do path.

### 2.1 Port ẩn (mặc định) vẫn là một phần của origin, dù không nhìn thấy trong URL

Một điểm dễ bỏ qua: `https://example.com` (không ghi số port trong URL) và `https://example.com:443` là **cùng một origin** — vì `443` là port mặc định cho `https`, trình duyệt tự hiểu port là `443` dù bạn không gõ ra. Tương tự, `http://example.com` mặc định là port `80`. Nhưng `https://example.com:8443` (port khác mặc định) là **origin khác** với `https://example.com`, dù cùng domain và scheme — vì port thực tế khác nhau (443 ngầm định so với 8443 ghi rõ). Đây là lý do nhiều API deploy ở một port tuỳ chỉnh (ví dụ `:5001` cho môi trường staging) cần khai báo `WithOrigins` với **đúng cả số port đó**, không thể chỉ ghi domain và giả định trình duyệt "sẽ tự hiểu".

### 2.2 Subdomain là origin khác domain gốc, trừ khi khai báo tường minh

`https://app.example.com` và `https://example.com` (không có `app.`) là **hai origin khác nhau** — subdomain được tính là một domain riêng theo đúng chuỗi ký tự, dù cả hai đều thuộc "cùng công ty" về mặt tổ chức. Tương tự, `https://api.example.com` và `https://admin.example.com` cũng là hai origin khác nhau với nhau, dù cùng thuộc domain gốc `example.com`. Nếu ứng dụng của bạn có kiến trúc nhiều subdomain (ví dụ `app.example.com` cho frontend chính, `admin.example.com` cho trang quản trị, `api.example.com` cho API), CORS policy trên API phải khai báo **từng subdomain cụ thể** cần được phép — không có cách nào để một dòng `WithOrigins("https://example.com")` tự động "bao gồm luôn" các subdomain của nó.

---

## 3. `AddCors` + policy: cho phép tường minh đúng origin cần được phép

**Định nghĩa:** `AddCors` là phương thức mở rộng của `IServiceCollection` (namespace `Microsoft.AspNetCore.Cors`, có sẵn trong ASP.NET Core, không cần cài package ngoài) dùng để đăng ký một hoặc nhiều "CORS policy" (chính sách CORS) đặt tên — mỗi policy khai báo rõ những origin, method HTTP, và header nào được phép gọi API — sau đó middleware `UseCors(...)` (bạn đã biết cách middleware chiếm một vị trí cụ thể trong pipeline từ chương middleware) sẽ tự động thêm đúng header `Access-Control-Allow-Origin` vào response khi request khớp policy.

Ví dụ tối thiểu: cho phép đúng origin `http://localhost:3000` gọi API, chỉ với method `GET` và `POST`:

```csharp title="Program.cs"
// test:compile AddCors co ban voi WithOrigins + WithMethods, dung UseCors dung vi tri trong pipeline
var builder = WebApplication.CreateBuilder(args);

builder.Services.AddCors(options =>
{
    options.AddPolicy("FrontendMacDinh", policy =>
    {
        policy.WithOrigins("http://localhost:3000")   // CHI origin nay duoc phep, khong phai "moi noi"
              .WithMethods("GET", "POST")              // CHI 2 method nay duoc phep qua CORS
              .WithHeaders("Content-Type");            // CHI header nay duoc client gui kem
    });
});

var app = builder.Build();

// UseCors phai dat truoc UseRouting/MapGet de ap dung cho toan bo endpoint phia sau,
// giong nguyen tac thu tu middleware da hoc: dang ky truoc = boc ngoai, ap dung cho ca pipeline con lai.
app.UseCors("FrontendMacDinh");

app.MapGet("/api/products", () => new[] { "Ao", "Quan", "Giay" });

app.Run();
```

Khi frontend `http://localhost:3000` gọi `GET /api/products`, trình duyệt gửi kèm header `Origin: http://localhost:3000` trong request; middleware `UseCors` kiểm tra origin này có khớp policy `"FrontendMacDinh"` không, nếu khớp thì thêm header `Access-Control-Allow-Origin: http://localhost:3000` vào response — trình duyệt thấy header này khớp với origin đang gọi, nên **cho phép** code JavaScript đọc dữ liệu.

**Điều gì xảy ra khi dùng sai:** nếu bạn gọi `AddCors` và định nghĩa policy nhưng **quên gọi `app.UseCors("FrontendMacDinh")`**, middleware không được thêm vào pipeline — mọi request từ trình duyệt vẫn bị chặn CORS như thể không cấu hình gì cả, dù code đăng ký "trông có vẻ đúng" và biên dịch bình thường (giống lỗi quên `app.UseRateLimiter()` đã học ở chương rate limiting — thiếu bước bật middleware là lỗi runtime âm thầm, không phải lỗi biên dịch). Một lỗi khác thường gặp: gọi `app.UseCors(...)` **sau** `app.MapGet(...)`/`UseRouting()` — theo đúng nguyên tắc "thứ tự đăng ký quyết định thứ tự thực thi" đã học, nếu `UseCors` nằm sau endpoint đã match, header CORS có thể không được thêm đúng lúc cho một số kịch bản (đặc biệt request preflight `OPTIONS` — xem phần cuối mục này), khiến CORS "chập chờn hoạt động" tuỳ endpoint.

**Preflight request (`OPTIONS`) — một khái niệm liên quan cần biết tên:** với các request "không đơn giản" (ví dụ có header `Content-Type: application/json`, hoặc method `PUT`/`DELETE`), trình duyệt tự động gửi **một request `OPTIONS` dò hỏi trước** ("bạn có cho phép tôi gửi request thật này không?") trước khi gửi request thật. `UseCors` của ASP.NET Core tự động xử lý và trả lời đúng request `OPTIONS` này mà bạn không cần viết endpoint riêng cho nó — chỉ cần đảm bảo `UseCors` được gọi đúng vị trí (trước khi request preflight bị middleware khác chặn hoặc trả lỗi 404).

### 3.1 Policy mặc định (`UseCors()` không tên) vs nhiều policy đặt tên cho từng endpoint

Ví dụ ở trên chỉ định nghĩa **một** policy tên `"FrontendMacDinh"` và gọi `UseCors("FrontendMacDinh")` — mọi endpoint trong ứng dụng đều dùng chung policy này vì `UseCors` được gọi ở cấp toàn ứng dụng (application-level), áp dụng cho toàn bộ pipeline phía sau nó. Trong thực tế, một API thường cần **nhiều policy khác nhau cho các nhóm endpoint khác nhau** — ví dụ một nhóm endpoint công khai (đọc danh mục sản phẩm) cho phép mọi origin đọc thoải mái, còn một nhóm endpoint nội bộ (dashboard quản trị) chỉ cho phép đúng origin của trang quản trị nội bộ.

`AddCors` hỗ trợ một **policy mặc định** (gọi `options.AddDefaultPolicy(...)` thay vì `AddPolicy` có tên) — nếu bạn gọi `app.UseCors()` **không** kèm tên, ASP.NET Core tự áp dụng policy mặc định này cho toàn bộ endpoint chưa được gán policy riêng:

```csharp title="Program.cs"
// test:compile policy mac dinh (khong ten) + policy rieng cho tung nhom endpoint qua RequireCors
var builder = WebApplication.CreateBuilder(args);

builder.Services.AddCors(options =>
{
    // Policy mac dinh: ap dung cho endpoint KHONG khai bao RequireCors rieng.
    options.AddDefaultPolicy(policy =>
    {
        policy.WithOrigins("https://shop.example.com")
              .AllowAnyMethod()
              .AllowAnyHeader();
    });

    // Policy rieng, chi ap dung khi endpoint goi RequireCors("AdminOnly") tuong minh.
    options.AddPolicy("AdminOnly", policy =>
    {
        policy.WithOrigins("https://admin.internal.example.com")
              .AllowAnyMethod()
              .AllowAnyHeader();
    });
});

var app = builder.Build();

// Goi UseCors() KHONG ten -> ap dung policy mac dinh cho toan bo endpoint phia sau
// (tru endpoint tu goi RequireCors voi ten policy khac).
app.UseCors();

app.MapGet("/api/products", () => new[] { "Ao", "Quan" }); // dung policy mac dinh

app.MapGet("/api/admin/thong-ke", () => "So lieu quan tri")
   .RequireCors("AdminOnly"); // override, dung policy "AdminOnly" thay vi mac dinh

app.Run();
```

**Điều gì xảy ra khi dùng sai:** nếu bạn có nhiều policy nhưng gọi `app.UseCors("SaiTen")` với một tên **không khớp** bất kỳ policy nào đã đăng ký, ASP.NET Core ném `InvalidOperationException: No CORS policy found with the name 'SaiTen'` ngay khi request đầu tiên chạm middleware này — đây là lỗi phát hiện được ngay ở runtime đầu tiên (không âm thầm như lỗi quên `UseCors()` hoàn toàn), nhưng vẫn dễ xảy ra khi đổi tên policy ở một nơi mà quên đổi theo ở `UseCors(...)`/`RequireCors(...)`.

### 3.2 `[EnableCors]`/`RequireCors` ở cấp endpoint: thu hẹp hoặc mở rộng CORS cho một nhóm nhỏ

Ngoài áp dụng CORS ở cấp toàn ứng dụng qua `app.UseCors(...)`, ASP.NET Core còn cho phép gán policy CORS **riêng cho từng endpoint hoặc từng controller**, ghi đè lên policy mặc định — đã thấy `RequireCors("AdminOnly")` ở ví dụ trên cho minimal API; với controller-based API, tương đương là attribute `[EnableCors("AdminOnly")]` gắn trên class controller hoặc action method cụ thể. Cách tiếp cận theo endpoint này hữu ích khi phần lớn API dùng một policy chung, nhưng một vài endpoint nhạy cảm (ví dụ endpoint xuất báo cáo tài chính) cần một danh sách origin hẹp hơn hẳn, hoặc ngược lại một vài endpoint công khai (ví dụ endpoint kiểm tra health, danh mục công khai) cần mở rộng hơn policy mặc định đang khá chặt của toàn ứng dụng.

### 3.3 Kiểm tra CORS đúng cách: vì sao test bằng `curl`/Postman không phát hiện được lỗi CORS

Một sai lầm thường gặp khi kiểm thử là dùng `curl` hoặc Postman để "xác nhận CORS đã hoạt động" — như đã nhắc ở mục 0 và mục 1, các công cụ này **không thực thi chính sách CORS**, nên chúng luôn nhận được response thành công bất kể server có cấu hình `AddCors` đúng hay không. `curl` có thể dùng để kiểm tra **header trả về có đúng giá trị mong đợi hay chưa** (một bước hữu ích, dù không mô phỏng đúng hành vi chặn của trình duyệt):

```bash title="Kiem tra header CORS bang curl (khong mo phong hanh vi chan cua trinh duyet)"
curl -i -H "Origin: http://localhost:3000" http://localhost:5000/api/products
```

Lệnh trên gửi kèm header `Origin` giả lập trình duyệt, và bạn có thể xem output có chứa `Access-Control-Allow-Origin: http://localhost:3000` hay không — nếu **có**, nghĩa là server đã cấu hình đúng, phần còn lại (trình duyệt có chấp nhận hay không) sẽ hoạt động đúng khi test thật từ frontend. Nếu **không có** header đó trong response, đây là dấu hiệu chắc chắn rằng `AddCors`/`UseCors` chưa được cấu hình đúng cho origin đó — nhưng cách kiểm tra chắc chắn nhất để phát hiện lỗi CORS thật sự vẫn là mở **DevTools của trình duyệt thật** (tab Console và tab Network), vì chỉ trình duyệt mới thực thi đầy đủ logic chặn/preflight như mô tả ở mục 1 và mục 3.

---

## 4. Sai lầm phổ biến: `AllowAnyOrigin()` + `AllowCredentials()` bị chặn bởi trình duyệt

**Định nghĩa:** `AllowAnyOrigin()` là tuỳ chọn cấu hình CORS cho phép **mọi origin** (không chỉ định danh sách cụ thể) gọi API; `AllowCredentials()` là tuỳ chọn cho phép request gửi kèm **thông tin xác thực** (cookie, header `Authorization`, hoặc chứng chỉ client) và cho phép JavaScript đọc response khi cookie được gửi kèm. Hai tuỳ chọn này **không thể dùng cùng lúc** — nếu bạn cấu hình cả hai, trình duyệt sẽ **tự chặn** request, và ASP.NET Core thậm chí ném exception ngay khi cấu hình sai cú pháp theo một số cách viết.

```csharp title="Program.cs"
// test:compile vi du SAI - AllowAnyOrigin + AllowCredentials cung luc, trinh duyet se chan
var builder = WebApplication.CreateBuilder(args);

builder.Services.AddCors(options =>
{
    options.AddPolicy("CauHinhSai", policy =>
    {
        policy.AllowAnyOrigin()      // cho phep MOI origin
              .AllowCredentials();    // NHUNG cung cho phep gui cookie/Authorization
        // Hai dong nay MAU THUAN nhau - trinh duyet se tu chan, khong phai loi code C# bien dich sai.
    });
});

var app = builder.Build();
app.UseCors("CauHinhSai");
app.MapGet("/api/du-lieu", () => "OK");
app.Run();
```

**Vì sao đây là giới hạn CHỦ ĐÍCH của trình duyệt, không phải bug:** nếu trình duyệt cho phép "mọi origin nào cũng được gửi cookie của người dùng và đọc response", điều này tương đương mở toang cửa cho **bất kỳ trang web độc hại nào trên Internet** mượn cookie đăng nhập có sẵn của người dùng (ví dụ cookie session ngân hàng) để gọi API thay người dùng và đọc kết quả — đúng chính xác kiểu tấn công CSRF/session-riding mà CORS được thiết kế ra để ngăn. Vì vậy các trình duyệt hiện đại (Chrome, Firefox, Edge) đều **cố ý** từ chối tổ hợp "mọi origin + cho phép credentials", buộc bạn phải khai báo **danh sách origin cụ thể** nếu muốn dùng credentials — đây không phải một hạn chế kỹ thuật tình cờ có thể "vượt qua" bằng cách nào đó, mà là một quyết định bảo mật cố ý ở tầng chuẩn web (W3C Fetch specification).

Cách sửa đúng — thay `AllowAnyOrigin()` bằng danh sách origin cụ thể qua `WithOrigins`:

```csharp title="Program.cs"
// test:compile vi du DUNG - WithOrigins cu the + AllowCredentials, trinh duyet chap nhan
var builder = WebApplication.CreateBuilder(args);

builder.Services.AddCors(options =>
{
    options.AddPolicy("ChoPhepCredentials", policy =>
    {
        policy.WithOrigins("https://app.congty.com")  // origin CU THE, khong phai "moi noi"
              .AllowCredentials()                       // gio moi hop le vi da biet ro origin nao
              .AllowAnyHeader()
              .AllowAnyMethod();
    });
});

var app = builder.Build();
app.UseCors("ChoPhepCredentials");
app.MapGet("/api/du-lieu", () => "OK");
app.Run();
```

**Điều gì xảy ra khi dùng sai:** với cấu hình sai ở ví dụ đầu, request từ frontend vẫn "được gửi" ra mạng (server nhận và xử lý bình thường), nhưng trình duyệt sẽ chặn ở bước đọc response phía client, in lỗi console dạng "The value of the 'Access-Control-Allow-Origin' header in the response must not be the wildcard '*' when the request's credentials mode is 'include'" — thông báo lỗi này thường khiến người mới nhầm là "server trả sai header", trong khi nguyên nhân gốc là **kết hợp cấu hình mâu thuẫn về bản chất**, không phải một giá trị sai đơn lẻ có thể sửa bằng cách đổi một tham số.

### 4.1 Phía frontend cũng phải "xin phép" gửi credentials — không chỉ server

Cấu hình `AllowCredentials()` ở server chỉ là **một nửa** của điều kiện — phía frontend (code JavaScript) cũng phải chủ động khai báo muốn gửi kèm credentials khi gọi `fetch`, bằng tuỳ chọn `credentials: "include"`:

```javascript title="frontend.js (minh hoa - khong phai C#)"
// Neu KHONG co credentials: "include", trinh duyet se KHONG gui cookie
// di kem, du server co AllowCredentials() dung cach.
fetch("https://api.congty.com/api/account/profile", {
  method: "GET",
  credentials: "include" // bat buoc de trinh duyet gui kem cookie session
});
```

Nếu server đã cấu hình đúng `WithOrigins(...).AllowCredentials()` nhưng frontend **quên** `credentials: "include"`, request vẫn được gửi và có thể trả về `200 OK`, nhưng **không có cookie nào được gửi kèm** — endpoint yêu cầu xác thực qua cookie session sẽ nhận request như một người dùng **chưa đăng nhập** (thường trả `401`), dù người dùng thực tế đã đăng nhập từ trước ở một tab khác của cùng trình duyệt. Đây là một lớp lỗi khác hẳn với lỗi CORS ở mục 4 — không có dòng đỏ nào trong console báo lỗi CORS (vì cấu hình CORS phía server hoàn toàn đúng), chỉ là cookie đơn giản không được gửi đi, khiến việc debug dễ đi sai hướng nếu không biết cả hai phía (server và frontend) đều cần khai báo credentials một cách độc lập với nhau.

---

## 5. Security header cơ bản: mỗi header giải quyết một rủi ro cụ thể

Ngoài CORS (kiểm soát ai được đọc response từ JavaScript), có ba HTTP response header phổ biến khác giúp trình duyệt tự bảo vệ người dùng theo những cách khác nhau. Ba mục dưới đây chỉ **giới thiệu** mức khái niệm — mỗi header một câu định nghĩa, không đi sâu cấu hình chi tiết như CSP (là chủ đề đủ lớn để có chương riêng).

**HSTS (HTTP Strict Transport Security):** là header (`Strict-Transport-Security`) báo cho trình duyệt biết "từ giờ, mọi lần truy cập domain này (kể cả người dùng gõ nhầm `http://` hoặc bấm vào link cũ) đều phải tự động đổi thành `https://`, không thử `http://` nữa trong một khoảng thời gian" — giúp ngăn kiểu tấn công **downgrade** (kẻ tấn công đứng giữa mạng ép trình duyệt dùng kết nối `http://` không mã hoá để nghe trộm dữ liệu).

**`X-Content-Type-Options: nosniff`:** là header báo cho trình duyệt "đừng tự đoán loại file dựa trên nội dung, hãy tin đúng giá trị header `Content-Type` mà server đã khai báo" — giúp chặn một kiểu tấn công trong đó kẻ tấn công upload một file trông giống ảnh (`.jpg`) nhưng thực chất chứa mã HTML/JavaScript độc hại; nếu không có header này, một số trình duyệt cũ có thể "đoán sai" và **thực thi** nội dung đó như HTML/script thay vì hiển thị như ảnh.

**Content-Security-Policy (CSP) — giới thiệu khái niệm ngắn:** là header cho phép server khai báo **những nguồn nào** (domain nào) được phép cung cấp script, ảnh, CSS, font... cho trang web, giúp chặn kiểu tấn công **XSS** (Cross-Site Scripting — chèn script lạ vào trang, ví dụ qua một ô nhập liệu không được lọc kỹ) vì dù script lạ có lọt được vào HTML, trình duyệt vẫn **từ chối thực thi** nó nếu nguồn của script đó không nằm trong danh sách CSP cho phép. CSP có cú pháp cấu hình khá rộng (nhiều tuỳ chọn theo từng loại tài nguyên: script, ảnh, font, iframe...) — chương này chỉ giới thiệu để bạn nhận diện đúng tên và mục đích, không đi sâu viết policy CSP chi tiết.

`UseHsts()` là middleware **có sẵn** trong ASP.NET Core (namespace `Microsoft.AspNetCore.Builder`, không cần cài package ngoài) tự động thêm header HSTS vào mọi response:

```csharp title="Program.cs"
// test:compile UseHsts co san, khong can package ngoai; kem X-Content-Type-Options thu cong
var builder = WebApplication.CreateBuilder(args);
var app = builder.Build();

// UseHsts them header Strict-Transport-Security vao response,
// bao trinh duyet luon dung HTTPS cho domain nay trong nhung lan truy cap sau.
app.UseHsts();

// Middleware tuy chinh: them header chan trinh duyet tu doan sai loai file.
app.Use(async (context, next) =>
{
    context.Response.Headers["X-Content-Type-Options"] = "nosniff";
    await next();
});

app.MapGet("/", () => "Xin chao");

app.Run();
```

**Điều gì xảy ra khi thiếu các header này (hậu quả production cụ thể):** thiếu HSTS, một người dùng gõ nhầm `http://tenmien.com` (quên chữ `s`) hoặc bấm vào một link cũ dùng `http://` sẽ có một khoảng thời gian ngắn dữ liệu đi qua kết nối **không mã hoá**, đủ để kẻ tấn công đứng giữa mạng (ví dụ wifi công cộng không an toàn) chặn và đọc được thông tin nhạy cảm trước khi redirect sang `https://` kịp xảy ra; thiếu `X-Content-Type-Options: nosniff`, một file người dùng upload (tưởng là ảnh đại diện) có thể bị trình duyệt cũ thực thi như HTML/script nếu nội dung file được chế tạo khéo léo, mở đường cho tấn công XSS thông qua chức năng upload file tưởng như vô hại.

**`UseHsts()` chỉ nên chạy trong production, không phải môi trường phát triển local:** vì HSTS buộc trình duyệt **nhớ** và tự động ép `https://` cho domain đó trong một khoảng thời gian (mặc định 30 ngày), nếu bạn bật `UseHsts()` khi đang chạy `localhost` bằng `http://` để phát triển, trình duyệt có thể "nhớ nhầm" và từ chối kết nối `http://localhost` ở những lần chạy sau — đây là lý do code mẫu của ASP.NET Core thường bọc `UseHsts()` trong điều kiện `if (!app.Environment.IsDevelopment())`.

### 5.1 Tham số của HSTS: `MaxAge`, `IncludeSubDomains`, `Preload`

`UseHsts()` mặc định dùng các giá trị hợp lý, nhưng có thể tuỳ biến qua `AddHsts` trong `builder.Services` trước khi gọi `UseHsts()` ở pipeline:

```csharp title="Program.cs"
// test:compile tuy bien tham so HSTS qua AddHsts, chi bat trong production
var builder = WebApplication.CreateBuilder(args);

builder.Services.AddHsts(options =>
{
    options.MaxAge = TimeSpan.FromDays(365);   // trinh duyet "nho" trong 365 ngay
    options.IncludeSubDomains = true;            // ap dung ca cho subdomain (vd api.tenmien.com)
    options.Preload = true;                      // cho phep dang ky vao danh sach preload cua trinh duyet
});

var app = builder.Build();

// Chi bat HSTS o production - localhost dung http:// khi phat trien khong nen bi ep https://.
if (!app.Environment.IsDevelopment())
{
    app.UseHsts();
}

app.MapGet("/", () => "Xin chao");

app.Run();
```

Ba tham số này lần lượt trả lời ba câu hỏi khác nhau: `MaxAge` — "trình duyệt nhớ quy tắc này trong bao lâu trước khi phải kiểm tra lại?"; `IncludeSubDomains` — "quy tắc ép `https://` có áp dụng luôn cho mọi subdomain (ví dụ `api.tenmien.com`, `cdn.tenmien.com`) hay chỉ đúng domain chính?"; `Preload` — "domain này có muốn được đưa vào danh sách preload cứng sẵn trong chính mã nguồn trình duyệt không, để ngay cả **lần truy cập đầu tiên** (trước khi trình duyệt từng nhận được header HSTS nào từ domain này) cũng đã tự động dùng `https://`?". `Preload` yêu cầu đăng ký thủ công vào danh sách công khai do các hãng trình duyệt duy trì (nằm ngoài phạm vi cấu hình code) — chỉ đặt `Preload = true` nếu bạn thực sự có ý định hoàn tất bước đăng ký đó, vì tự đặt cờ này trong code không tự động "kích hoạt" preload.

### 5.2 CSP với ví dụ cụ thể: khai báo nguồn cho script và ảnh

Mục 5 chỉ giới thiệu khái niệm CSP ở mức tên gọi và mục đích; phần này minh hoạ một cấu hình CSP tối thiểu bằng cách thêm trực tiếp header, để bạn thấy hình dạng thật của policy (không nhằm dạy toàn bộ cú pháp CSP — chủ đề đó xứng đáng một chương riêng với đủ bốn bước dạy-từ-đầu):

```csharp title="Program.cs"
// test:compile minh hoa header CSP toi thieu - chi gioi thieu hinh dang, khong day sau cu phap
var builder = WebApplication.CreateBuilder(args);
var app = builder.Build();

app.Use(async (context, next) =>
{
    // default-src 'self': moi tai nguyen (script, anh, css...) CHI duoc tai tu chinh domain nay,
    // tru khi co chi dinh rieng khac (vi du script-src cho phep them mot domain CDN cu the).
    context.Response.Headers["Content-Security-Policy"] =
        "default-src 'self'; script-src 'self' https://cdn.example.com; img-src 'self' data:;";
    await next();
});

app.MapGet("/", () => "Xin chao");

app.Run();
```

Đọc policy trên theo từng phần: `default-src 'self'` là quy tắc **mặc định** cho mọi loại tài nguyên chưa được khai báo riêng — chỉ cho phép tải từ chính domain đang phục vụ trang (`'self'`); `script-src 'self' https://cdn.example.com` **ghi đè** riêng cho script, cho phép thêm domain CDN cụ thể ngoài chính domain gốc; `img-src 'self' data:` cho phép ảnh tải từ domain gốc hoặc dữ liệu nhúng trực tiếp dạng `data:` (ví dụ ảnh base64 nhúng trong HTML). Nếu một trang bị chèn được một thẻ `<script src="https://tan-cong.evil.com/steal.js">` (qua lỗ hổng XSS ở một ô nhập liệu không lọc kỹ), trình duyệt sẽ **từ chối tải** script đó vì domain `evil.com` không nằm trong danh sách `script-src` cho phép — dù đoạn HTML độc hại đã lọt được vào trang, CSP vẫn chặn được hành động thực thi cuối cùng.

**Điều gì xảy ra khi cấu hình CSP quá lỏng hoặc quá chặt:** đặt `script-src *` (cho phép mọi domain) khiến CSP **mất tác dụng bảo vệ XSS gần như hoàn toàn** — bất kỳ domain nào cũng được phép cung cấp script, quay lại đúng tình trạng như không có CSP; ngược lại đặt CSP quá chặt (ví dụ quên khai báo domain CDN thực sự đang được dùng để tải font/thư viện JS) khiến các tài nguyên hợp lệ bị chặn nhầm — trang web có thể hiển thị lỗi font, thiếu icon, hoặc một thư viện JavaScript thiết yếu (ví dụ Google Analytics, thư viện thanh toán) không tải được, gây lỗi chức năng thực sự dù không phải do bug trong code JavaScript.

### 5.3 `Content-Security-Policy-Report-Only`: thử nghiệm CSP an toàn trước khi thực sự chặn

Vì cấu hình CSP sai có thể vô tình chặn tài nguyên hợp lệ (như đã nêu ở trên), có một biến thể header dùng để **thử nghiệm** policy mà không thực sự chặn gì: `Content-Security-Policy-Report-Only`. Với header này, trình duyệt **vẫn tải mọi tài nguyên như bình thường** (không chặn), nhưng ghi lại (và có thể gửi báo cáo tới một endpoint bạn chỉ định qua chỉ thị `report-uri`/`report-to`) mọi trường hợp **lẽ ra** sẽ bị chặn nếu policy này là thật:

```csharp title="Program.cs"
// test:compile minh hoa Content-Security-Policy-Report-Only - thu nghiem khong chan thuc su
var builder = WebApplication.CreateBuilder(args);
var app = builder.Build();

app.Use(async (context, next) =>
{
    // Report-Only: KHONG chan tai nguyen nao ca, chi de "thu" xem policy nay
    // se chan gi neu duoc ap dung thuc su - an toan de thu nghiem tren production.
    context.Response.Headers["Content-Security-Policy-Report-Only"] =
        "default-src 'self'; script-src 'self' https://cdn.example.com;";
    await next();
});

app.MapGet("/", () => "Xin chao");

app.Run();
```

Quy trình thực chiến khuyến nghị khi triển khai CSP lần đầu cho một ứng dụng đã chạy production: (1) bật `Content-Security-Policy-Report-Only` với policy dự kiến, theo dõi báo cáo/log trong một khoảng thời gian (vài ngày tới vài tuần tuỳ lưu lượng) để phát hiện những tài nguyên hợp lệ đang bị "đánh dấu" là sẽ bị chặn; (2) điều chỉnh policy cho tới khi không còn tài nguyên hợp lệ nào bị đánh dấu chặn nhầm; (3) chỉ khi đó mới đổi header thành `Content-Security-Policy` (bỏ `-Report-Only`) để **thực sự** kích hoạt việc chặn. Bỏ qua bước Report-Only và bật CSP thật ngay từ đầu là nguyên nhân phổ biến khiến một tính năng đang hoạt động tốt (ví dụ widget chat hỗ trợ khách hàng tải từ một domain thứ ba) bất ngờ ngừng hoạt động ngay sau khi đội bảo mật triển khai CSP mà không kiểm thử kỹ trước.

---

## 6. So sánh CORS với security header: cùng nằm ở tầng trình duyệt, giải quyết bài toán khác nhau

Sau khi đã hiểu riêng lẻ CORS (mục 1-4) và ba security header cơ bản (mục 5), phần này không giới thiệu khái niệm mới — chỉ tổng hợp lại để tránh nhầm lẫn giữa các cơ chế có vẻ "cùng nhóm bảo mật phía trình duyệt" nhưng thực chất giải quyết những rủi ro hoàn toàn khác nhau:

| Cơ chế | Ai thực thi | Bảo vệ khỏi rủi ro gì | Không bảo vệ khỏi |
|---|---|---|---|
| CORS (`AddCors`/`UseCors`) | Trình duyệt | Trang web độc hại A đọc trộm response API của trang B qua JavaScript, lợi dụng cookie có sẵn của người dùng | Gọi trực tiếp API bằng `curl`/Postman/script (không phải trình duyệt) |
| HSTS (`UseHsts`) | Trình duyệt | Tấn công downgrade — ép dùng `http://` không mã hoá để nghe trộm dữ liệu trên đường truyền | Tấn công đã diễn ra ở lần truy cập đầu tiên trước khi trình duyệt từng thấy header HSTS (trừ khi đã đăng ký `Preload`) |
| `X-Content-Type-Options: nosniff` | Trình duyệt | Trình duyệt tự "đoán sai" loại file và thực thi nội dung độc hại giả trang làm file vô hại (ảnh, font) | Nội dung độc hại được khai đúng `Content-Type` từ đầu (header này không kiểm tra nội dung thực có khớp loại khai báo hay không) |
| CSP (`Content-Security-Policy`) | Trình duyệt | Script/tài nguyên lạ (đã lọt vào HTML qua lỗ hổng XSS) bị chặn thực thi vì nguồn không nằm trong danh sách cho phép | Lỗ hổng XSS gốc vẫn tồn tại trong code (CSP là lớp phòng thủ bổ sung, không thay thế việc lọc/encode dữ liệu đầu vào đúng cách) |

Điểm chung quan trọng của cả bốn cơ chế: **tất cả đều được trình duyệt thực thi, không phải server**, và tất cả đều là các lớp phòng thủ **bổ sung** (defense in depth) — chúng không thay thế cho các biện pháp bảo mật nền tảng khác như xác thực (authentication), phân quyền (authorization), validate/encode dữ liệu đầu vào đúng cách, hay mã hoá dữ liệu nhạy cảm ở tầng lưu trữ. Một hệ thống bật đủ cả bốn cơ chế này nhưng vẫn để lộ endpoint không xác thực, hoặc không lọc dữ liệu người dùng nhập trước khi hiển thị lại (nguyên nhân gốc của XSS), vẫn hoàn toàn có thể bị khai thác qua những đường khác mà bốn cơ chế trên không được thiết kế để chặn.

Một câu hỏi thường gặp: "vậy nên bật cơ chế nào trước?" Với hầu hết API mới bắt đầu triển khai production, thứ tự ưu tiên thực chiến hợp lý là: (1) xác thực/phân quyền đúng đắn ở mọi endpoint nhạy cảm — đây là nền tảng, không cơ chế nào ở chương này thay thế được; (2) CORS đúng danh sách origin cụ thể nếu API được gọi từ frontend chạy trên domain khác; (3) HSTS và `X-Content-Type-Options` — cả hai đơn giản, ít rủi ro phá vỡ chức năng hiện có, nên bật sớm; (4) CSP — thường bật sau cùng và cần kiểm thử kỹ (dùng `Content-Security-Policy-Report-Only` trước, xem mục 5.3), vì cấu hình sai dễ vô tình chặn nhầm tài nguyên hợp lệ (mục 5.2) đang được trang web dùng thật.

Một cách hình dung tổng thể giúp nhớ lâu: coi bốn cơ chế này như bốn loại "biển báo" mà server dán lên response để nói chuyện với trình duyệt — CORS nói "JavaScript từ những origin này được đọc dữ liệu của tôi"; HSTS nói "hãy luôn tìm tôi qua kết nối mã hoá"; `nosniff` nói "đừng tự đoán loại file, tin đúng những gì tôi khai báo"; CSP nói "chỉ tin script/ảnh/font từ đúng những nguồn tôi liệt kê". Cả bốn biển báo này chỉ có tác dụng với trình duyệt biết đọc và tôn trọng chúng — chúng không phải khoá cửa, không phải tường lửa, và không thay thế cho việc xác thực đúng người dùng ở tầng server.

---

## Cạm bẫy & thực chiến

- **Nghĩ CORS là lỗi ở server khi thấy lỗi trong console trình duyệt:** như minh hoạ ở mục 0, server có thể trả `200 OK` hoàn toàn đúng — CORS là cơ chế trình duyệt chặn phía client, không phải lỗi xử lý ở server. Kiểm tra tab Network (không phải chỉ console) để thấy request thực ra đã có response.
- **Quên gọi `app.UseCors("ten-policy")`:** định nghĩa policy trong `AddCors` không tự động bật middleware — thiếu dòng `UseCors` khiến toàn bộ CORS bị bỏ qua âm thầm, giống lỗi quên `UseRateLimiter()` đã học ở chương rate limiting.
- **Đặt `app.UseCors(...)` sau `MapGet`/các endpoint khác trong pipeline:** vi phạm nguyên tắc thứ tự middleware đã học — CORS có thể không áp dụng đúng lúc cho một số request, đặc biệt request preflight `OPTIONS`.
- **Kết hợp `AllowAnyOrigin()` với `AllowCredentials()`:** trình duyệt chủ động chặn tổ hợp này (mục 4) — đây là giới hạn bảo mật cố ý của chuẩn web, không phải lỗi cấu hình có thể "sửa bằng cách thử tham số khác" mà không đổi bản chất (phải chuyển sang danh sách origin cụ thể).
- **Nhầm `localhost` và `127.0.0.1` là cùng origin:** hai chuỗi domain khác nhau về mặt ký tự, dù cùng trỏ tới máy local — CORS policy khai báo một trong hai không tự động áp dụng cho cái còn lại.
- **Dùng CORS như một lớp bảo mật thay cho authentication/authorization:** CORS chỉ kiểm soát trình duyệt có cho JavaScript đọc response hay không — nó **không** ngăn được ai đó gọi trực tiếp API bằng `curl`/Postman/script. Một API không xác thực (không kiểm tra JWT/API key) vẫn hoàn toàn bị lộ dữ liệu cho công cụ gọi trực tiếp, bất kể cấu hình CORS chặt tới đâu.
- **Bật `UseHsts()` khi đang phát triển trên `localhost` bằng `http://`:** trình duyệt "nhớ" và có thể ép `https://` cho `localhost` ở các lần chạy sau, gây khó chịu và khó debug môi trường local — chỉ bật HSTS trong production.
- **Cấu hình một policy CORS "tạm cho nhanh" với `AllowAnyOrigin().AllowAnyMethod().AllowAnyHeader()` rồi quên gỡ khi lên production:** đây là cấu hình phù hợp để test nhanh cục bộ, nhưng để nguyên lên production nghĩa là **mọi trang web trên Internet** đều có thể gọi API của bạn từ JavaScript (miễn không dùng credentials) — không kiểm soát được ai đang nhúng và gọi API của bạn từ trang của họ.
- **Quên `credentials: "include"` ở phía frontend dù server đã cấu hình `AllowCredentials()` đúng:** request vẫn thành công (không có lỗi CORS trong console), nhưng cookie không được gửi kèm, khiến endpoint cần xác thực qua cookie nhận nhầm là request của người dùng chưa đăng nhập (mục 4.1) — dễ gây nhầm lẫn vì không có thông báo lỗi CORS rõ ràng để lần theo.
- **Đặt `SetPreflightMaxAge` quá lớn rồi đổi policy CORS mà quên rằng trình duyệt vẫn đang cache kết quả preflight cũ:** một số client có thể tiếp tục gọi thành công theo policy cũ cho tới khi cache hết hạn, dù server đã cập nhật danh sách origin được phép — gây hiện tượng "đã sửa code nhưng lỗi vẫn còn với một số người dùng" khó lý giải nếu không biết tới cơ chế cache preflight.

---

## Bài tập

**Bài 1 (áp dụng).** Một frontend Vue chạy tại `https://shop.example.com` cần gọi API tại `https://api.example.com`, chỉ dùng method `GET` và `POST`, không cần gửi cookie/credentials. Viết cấu hình `AddCors` + `UseCors` đúng cho tình huống này.

??? success "Lời giải + vì sao"
    ```csharp title="Program.cs"
    // test:compile bai 1 - CORS cho frontend cu the, khong can credentials
    var builder = WebApplication.CreateBuilder(args);

    builder.Services.AddCors(options =>
    {
        options.AddPolicy("ShopFrontend", policy =>
        {
            policy.WithOrigins("https://shop.example.com")
                  .WithMethods("GET", "POST")
                  .AllowAnyHeader();
        });
    });

    var app = builder.Build();
    app.UseCors("ShopFrontend");

    app.MapGet("/api/products", () => new[] { "Ao", "Quan" });
    app.MapPost("/api/orders", () => "Da tao don hang");

    app.Run();
    ```

    **Vì sao:** dùng `WithOrigins` với origin cụ thể (không phải `AllowAnyOrigin`) vì đây là API dành cho một frontend cụ thể đã biết trước — không cần mở cho mọi origin. Vì không cần credentials, không cần gọi `AllowCredentials()`, tránh phức tạp hoá cấu hình không cần thiết. `WithMethods("GET", "POST")` giới hạn đúng hai method đề bài yêu cầu, thay vì `AllowAnyMethod()` cho phép cả `DELETE`/`PUT` không cần thiết.

    **Mở rộng:** nếu sau này frontend cần thêm `PUT`/`DELETE` (ví dụ thêm chức năng sửa/xoá sản phẩm), chỉ cần thêm vào danh sách `WithMethods("GET", "POST", "PUT", "DELETE")` — không cần đổi `WithOrigins` hay bất kỳ phần nào khác của policy, vì origin được phép không thay đổi, chỉ danh sách method được mở rộng thêm.

**Bài 2 (tìm lỗi).** Đội của bạn cấu hình CORS như sau cho một API cần đọc cookie session của người dùng để xác thực (`AllowCredentials()` là bắt buộc). Sau khi deploy, frontend báo lỗi CORS trong console trình duyệt dù origin đã được khai báo. Tìm lỗi và sửa.

```csharp title="Program.cs (có lỗi)"
// test:skip bai 2 - co loi, can tim va sua
var builder = WebApplication.CreateBuilder(args);

builder.Services.AddCors(options =>
{
    options.AddPolicy("CoLoi", policy =>
    {
        policy.AllowAnyOrigin()
              .AllowCredentials()
              .AllowAnyMethod()
              .AllowAnyHeader();
    });
});

var app = builder.Build();
app.UseCors("CoLoi");
app.MapGet("/api/ho-so", () => "Thong tin ho so nguoi dung");
app.Run();
```

??? success "Lời giải + vì sao"
    Lỗi nằm ở việc kết hợp `AllowAnyOrigin()` với `AllowCredentials()` (mục 4) — trình duyệt chủ động chặn tổ hợp này vì lý do bảo mật, không phải lỗi cú pháp C#. Sửa bằng cách thay `AllowAnyOrigin()` bằng danh sách origin cụ thể qua `WithOrigins`:

    ```csharp title="Program.cs (đã sửa)"
    // test:compile bai 2 - da sua, dung WithOrigins cu the thay AllowAnyOrigin
    var builder = WebApplication.CreateBuilder(args);

    builder.Services.AddCors(options =>
    {
        options.AddPolicy("DaSua", policy =>
        {
            policy.WithOrigins("https://app.congty.com")
                  .AllowCredentials()
                  .AllowAnyMethod()
                  .AllowAnyHeader();
        });
    });

    var app = builder.Build();
    app.UseCors("DaSua");
    app.MapGet("/api/ho-so", () => "Thong tin ho so nguoi dung");
    app.Run();
    ```

    **Vì sao:** khi cần gửi credentials (cookie session), chuẩn web bắt buộc server phải khai báo **rõ ràng** danh sách origin được phép, không thể dùng `*`/`AllowAnyOrigin()` — vì nếu cho phép, bất kỳ trang web độc hại nào cũng có thể mượn cookie đăng nhập sẵn có của người dùng để gọi API thay họ. Đây là giới hạn cố ý của trình duyệt, không phải một cấu hình có thể "vượt qua" bằng tham số khác mà giữ nguyên `AllowAnyOrigin()`.

    **Lưu ý thêm khi sửa lỗi này trong thực tế:** đổi `AllowAnyOrigin()` thành `WithOrigins(...)` chỉ giải quyết được đúng lỗi cấu hình mâu thuẫn — nếu sau khi sửa, frontend vẫn báo lỗi CORS, hãy kiểm tra tiếp theo đúng thứ tự đã nêu ở mục 1.1: đúng origin đang gõ trên trình duyệt (có `www.` hay không, đúng port hay không), rồi mới tới các khả năng phức tạp hơn về cache CDN hoặc rolling deploy chưa đồng bộ.

**Bài 3 (thiết kế, kết hợp nhiều khái niệm đã học).** Ứng dụng của bạn có hai nhóm endpoint: (a) `/api/public/*` — danh mục sản phẩm công khai, không cần đăng nhập, muốn cho **mọi origin** đọc được (ví dụ để các trang đối tác nhúng widget hiển thị sản phẩm); (b) `/api/account/*` — thông tin tài khoản cá nhân, cần cookie session, chỉ frontend chính thức tại `https://app.congty.com` được gọi. Đồng thời, toàn ứng dụng cần bật HSTS ở production và header `X-Content-Type-Options: nosniff` cho mọi response. Thiết kế `Program.cs` đáp ứng đủ các yêu cầu này, đúng thứ tự middleware.

??? success "Lời giải + vì sao"
    ```csharp title="Program.cs"
    // test:compile bai 3 - ket hop 2 CORS policy khac nhau + HSTS + nosniff, dung thu tu middleware
    var builder = WebApplication.CreateBuilder(args);

    builder.Services.AddCors(options =>
    {
        // Nhom (a): danh muc cong khai, cho phep MOI origin doc (khong dung credentials).
        options.AddPolicy("PublicCatalog", policy =>
        {
            policy.AllowAnyOrigin()
                  .WithMethods("GET")
                  .AllowAnyHeader();
        });

        // Nhom (b): tai khoan ca nhan, can credentials -> PHAI khai bao origin cu the.
        options.AddPolicy("AccountFrontend", policy =>
        {
            policy.WithOrigins("https://app.congty.com")
                  .AllowCredentials()
                  .AllowAnyMethod()
                  .AllowAnyHeader();
        });
    });

    builder.Services.AddHsts(options =>
    {
        options.MaxAge = TimeSpan.FromDays(365);
        options.IncludeSubDomains = true;
    });

    var app = builder.Build();

    // HSTS chi bat o production, khong ep https:// khi dang phat trien tren localhost.
    if (!app.Environment.IsDevelopment())
    {
        app.UseHsts();
    }

    // Header nosniff ap dung cho MOI response, dat truoc UseCors de chac chan luon duoc them.
    app.Use(async (context, next) =>
    {
        context.Response.Headers["X-Content-Type-Options"] = "nosniff";
        await next();
    });

    app.MapGet("/api/public/products", () => new[] { "Ao", "Quan" })
       .RequireCors("PublicCatalog");

    app.MapGet("/api/account/profile", () => "Thong tin tai khoan")
       .RequireCors("AccountFrontend");

    app.Run();
    ```

    **Vì sao:** hai nhóm endpoint có yêu cầu CORS **mâu thuẫn nhau** (một cần mở cho mọi origin, một cần credentials với origin cụ thể) — không thể dùng một policy chung cho cả hai, vì `AllowAnyOrigin()` và `AllowCredentials()` không thể kết hợp (mục 4). Giải pháp đúng là định nghĩa **hai policy riêng** và gán cho từng nhóm endpoint qua `RequireCors(...)` (mục 3.1-3.2), thay vì cố gò một policy duy nhất `app.UseCors()` áp dụng chung cho toàn ứng dụng. HSTS được bọc trong điều kiện môi trường để không ảnh hưởng `localhost` khi phát triển (mục 5.1); header `nosniff` được thêm bằng middleware tự viết vì ASP.NET Core không có sẵn một `UseXxx()` chuyên dụng riêng cho header này như đã có `UseHsts()` cho HSTS.

---

## Tự kiểm tra

1. CORS được thực thi bởi server hay trình duyệt?

    ??? note "Đáp án"
        Trình duyệt. Server chỉ trả về các header CORS (nếu được cấu hình); chính trình duyệt là bên đọc các header đó và quyết định có cho JavaScript đọc response hay không. Công cụ không phải trình duyệt (Postman, curl, script) không thực thi chính sách CORS.

2. `http://localhost:3000` và `http://localhost:5000` có cùng origin không? Vì sao?

    ??? note "Đáp án"
        Không — khác port (3000 so với 5000). Origin gồm scheme + domain + port; chỉ cần một trong ba khác là origin khác, dù domain giống nhau.

3. Điều gì xảy ra nếu quên gọi `app.UseCors("ten-policy")` sau khi đã `AddCors`?

    ??? note "Đáp án"
        Middleware CORS không được thêm vào pipeline — mọi request từ trình duyệt vẫn bị chặn CORS như thể chưa cấu hình gì, dù `AddCors` đã đăng ký policy đúng. Đây là lỗi runtime âm thầm, không có exception, không có cảnh báo lúc biên dịch.

4. Vì sao `AllowAnyOrigin()` và `AllowCredentials()` không thể dùng cùng lúc?

    ??? note "Đáp án"
        Vì nếu cho phép, bất kỳ trang web độc hại nào trên Internet cũng có thể mượn cookie/thông tin đăng nhập sẵn có của người dùng trong trình duyệt để gọi API thay người dùng và đọc kết quả — đây là giới hạn bảo mật cố ý của chuẩn web (không phải bug), buộc phải khai báo origin cụ thể qua `WithOrigins` nếu cần dùng credentials.

5. `X-Content-Type-Options: nosniff` giải quyết rủi ro gì?

    ??? note "Đáp án"
        Chặn trình duyệt tự đoán sai loại file dựa trên nội dung thay vì tin đúng `Content-Type` server khai báo — ngăn kiểu tấn công trong đó một file trông giống ảnh nhưng chứa mã HTML/script độc hại bị trình duyệt "đoán" và thực thi như HTML thay vì hiển thị như ảnh.

6. HSTS bảo vệ người dùng khỏi kiểu tấn công gì?

    ??? note "Đáp án"
        Tấn công downgrade — kẻ tấn công đứng giữa mạng ép trình duyệt dùng kết nối `http://` không mã hoá để nghe trộm dữ liệu. HSTS báo trình duyệt luôn tự động dùng `https://` cho domain đó, không thử `http://` nữa trong một khoảng thời gian.

7. Một API không có xác thực (không kiểm tra JWT/API key) nhưng có cấu hình CORS rất chặt (chỉ cho một origin cụ thể). API này có an toàn trước việc bị gọi trực tiếp bằng `curl` không?

    ??? note "Đáp án"
        Không. CORS chỉ kiểm soát việc trình duyệt có cho JavaScript đọc response hay không — nó không ngăn được việc gọi trực tiếp API bằng công cụ không phải trình duyệt (`curl`, Postman, script). Một API thiếu xác thực vẫn hoàn toàn lộ dữ liệu cho ai gọi trực tiếp, bất kể CORS được cấu hình chặt tới đâu — CORS và authentication/authorization là hai lớp bảo vệ độc lập, giải quyết hai bài toán khác nhau.

8. Vì sao không nên bật `app.UseHsts()` khi đang phát triển trên `localhost` bằng `http://`?

    ??? note "Đáp án"
        Vì HSTS khiến trình duyệt "nhớ" và tự động ép `https://` cho domain đó trong một khoảng thời gian (thường 30 ngày) — nếu bật trên `localhost` đang chạy `http://`, trình duyệt có thể từ chối kết nối `http://localhost` ở các lần chạy sau, gây khó khăn khi phát triển local. Nên bọc `UseHsts()` trong điều kiện chỉ chạy ở production (`!app.Environment.IsDevelopment()`).

9. Hai nhóm endpoint trong cùng ứng dụng cần chính sách CORS mâu thuẫn nhau (một cần mở cho mọi origin, một cần credentials với origin cụ thể). Giải pháp đúng là gì?

    ??? note "Đáp án"
        Định nghĩa hai policy riêng trong `AddCors` (ví dụ `"PublicCatalog"` và `"AccountFrontend"`), rồi gán từng policy cho đúng nhóm endpoint bằng `.RequireCors("ten-policy")` (minimal API) hoặc `[EnableCors("ten-policy")]` (controller). Không thể dùng một policy duy nhất cho cả hai vì `AllowAnyOrigin()` và `AllowCredentials()` không thể kết hợp trong cùng một policy.

10. `Content-Security-Policy` bảo vệ đúng nguyên nhân gốc của lỗ hổng XSS hay chỉ là lớp phòng thủ bổ sung?

    ??? note "Đáp án"
        Chỉ là lớp phòng thủ bổ sung (defense in depth) — CSP chặn trình duyệt **thực thi** script từ nguồn không được phép, nhưng không sửa được nguyên nhân gốc là dữ liệu người dùng nhập chưa được lọc/encode đúng trước khi hiển thị lại. Vẫn cần validate/encode dữ liệu đầu vào đúng cách; CSP chỉ giảm thiệt hại nếu lỗ hổng XSS gốc vẫn tồn tại và bị khai thác.

---

??? abstract "DEEP DIVE: `WithExposedHeaders`, CORS cho SignalR/WebSocket, cache preflight, và thứ tự CORS với các middleware khác"
    **`WithExposedHeaders`:** theo mặc định, ngay cả khi CORS cho phép đọc response, code JavaScript chỉ đọc được một số header "an toàn" cơ bản (`Content-Type`, `Content-Length`...) — các header tuỳ chỉnh do server thêm vào (ví dụ `X-Total-Count` cho phân trang) **không** tự động lộ ra cho JavaScript đọc được, trừ khi bạn khai báo tường minh qua `.WithExposedHeaders("X-Total-Count")` trong policy. Đây là một lớp giới hạn bổ sung riêng biệt với `Access-Control-Allow-Origin` — cho phép origin đọc response không tự động cho phép đọc mọi header trong response đó.

    ```csharp title="Program.cs (minh hoa WithExposedHeaders)"
    // test:compile minh hoa WithExposedHeaders - JS chi doc duoc header tuy chinh neu khai bao ro
    var builder = WebApplication.CreateBuilder(args);

    builder.Services.AddCors(options =>
    {
        options.AddPolicy("CoExposedHeaders", policy =>
        {
            policy.WithOrigins("https://shop.example.com")
                  .AllowAnyMethod()
                  .AllowAnyHeader()
                  .WithExposedHeaders("X-Total-Count"); // khong khai bao -> JS KHONG doc duoc header nay
        });
    });

    var app = builder.Build();
    app.UseCors("CoExposedHeaders");

    app.MapGet("/api/products", (HttpContext context) =>
    {
        context.Response.Headers["X-Total-Count"] = "42";
        return new[] { "Ao", "Quan" };
    });

    app.Run();
    ```

    **CORS với SignalR/WebSocket:** kết nối WebSocket (dùng bởi SignalR cho realtime) có cơ chế kiểm soát cross-origin **khác** với CORS thông thường của HTTP request — SignalR có tuỳ chọn cấu hình riêng (`options.HandshakeTimeout`, cấu hình `Origin` header trong quá trình bắt tay/handshake ban đầu) không đi qua đúng cùng pipeline `UseCors()` như các endpoint HTTP thường. Nếu ứng dụng dùng SignalR cho tính năng realtime, cấu hình CORS cho các endpoint HTTP thông thường không tự động áp dụng đúng cho hub SignalR — cần cấu hình CORS riêng cho hub đó, thuộc phạm vi chương SignalR/realtime riêng.

    **Cache preflight bằng `SetPreflightMaxAge`:** mỗi request "không đơn giản" (mục 3) khiến trình duyệt gửi thêm một request `OPTIONS` dò hỏi trước request thật — với một trang gọi API nhiều lần liên tục, việc gửi lại `OPTIONS` cho **mỗi** request thật là lãng phí một round-trip mạng không cần thiết, vì câu trả lời "origin này có được phép không" hầu như không đổi giữa các lần gọi liên tiếp. `.SetPreflightMaxAge(TimeSpan.FromMinutes(10))` báo trình duyệt **nhớ** câu trả lời preflight trong 10 phút, không cần hỏi lại `OPTIONS` cho mỗi request thật trong khoảng thời gian đó:

    ```csharp title="Program.cs (minh hoa SetPreflightMaxAge)"
    // test:compile minh hoa cache preflight - giam so lan trinh duyet phai hoi OPTIONS
    var builder = WebApplication.CreateBuilder(args);

    builder.Services.AddCors(options =>
    {
        options.AddPolicy("CoCachePreflight", policy =>
        {
            policy.WithOrigins("https://shop.example.com")
                  .AllowAnyMethod()
                  .AllowAnyHeader()
                  .SetPreflightMaxAge(TimeSpan.FromMinutes(10)); // trinh duyet nho ket qua preflight 10 phut
        });
    });

    var app = builder.Build();
    app.UseCors("CoCachePreflight");
    app.MapPost("/api/orders", () => "Da tao don hang");
    app.Run();
    ```

    Đánh đổi cần cân nhắc: giá trị `SetPreflightMaxAge` quá lớn (ví dụ vài ngày) khiến trình duyệt "nhớ" một quyết định CORS cũ lâu hơn cần thiết — nếu bạn thay đổi policy (ví dụ gỡ một origin khỏi danh sách cho phép), một số client trình duyệt đã cache preflight cũ có thể vẫn tiếp tục gọi thành công cho tới khi cache đó hết hạn, dù server đã đổi cấu hình.

    **Thứ tự `UseCors()` so với `UseAuthentication()`/`UseAuthorization()`:** nguyên tắc chung là đặt `UseCors()` **trước** `UseAuthentication()`/`UseAuthorization()` trong pipeline — vì request preflight `OPTIONS` (đã nhắc ở mục 3) thường **không** kèm thông tin xác thực (trình duyệt tự sinh ra request này, không gắn cookie/token), nếu `UseAuthorization()` chạy trước và chặn `OPTIONS` vì "thiếu xác thực", request preflight sẽ thất bại trước khi kịp tới `UseCors()` để nhận diện đúng đây là câu hỏi CORS hợp lệ, không phải một request cần xác thực. Đặt `UseCors()` sớm trong pipeline (thường ngay sau `UseRouting()`, trước `UseAuthentication()`) tránh đúng lớp lỗi này.

    **`Vary: Origin` — vì sao ASP.NET Core tự thêm header này khi CORS đang hoạt động:** khi một endpoint có thể trả về `Access-Control-Allow-Origin` với **giá trị khác nhau tuỳ origin của request** (ví dụ policy cho phép nhiều origin cụ thể, không phải `*`), ASP.NET Core tự động thêm header `Vary: Origin` vào response — báo cho các lớp cache trung gian (CDN, reverse proxy, cache của trình duyệt) biết rằng "response này có thể khác nhau tuỳ vào header `Origin` của request, đừng dùng chung một bản cache cho mọi origin". Thiếu header này, một CDN có thể vô tình phục vụ nhầm một response đã có `Access-Control-Allow-Origin: https://a.com` cho một request thực chất tới từ `https://b.com`, gây lỗi CORS khó hiểu chỉ xuất hiện khi có tầng cache trung gian tham gia — chi tiết cấu hình cache/CDN thuộc phạm vi chương hosting & deployment.

    **Một security header khác đáng biết tên (không đi sâu ở chương này): `Referrer-Policy`.** Header này kiểm soát trình duyệt gửi **bao nhiêu thông tin** về trang hiện tại (qua header `Referer` của request tiếp theo) khi người dùng bấm vào một link dẫn sang trang khác — ví dụ giá trị `strict-origin-when-cross-origin` (một giá trị phổ biến, thường được coi là mặc định an toàn hợp lý) chỉ gửi origin (không gửi path/query string chứa thông tin nhạy cảm) khi link dẫn sang một origin khác, nhưng gửi đầy đủ URL khi ở lại cùng origin. Rủi ro cụ thể nếu không kiểm soát: một trang nội bộ có URL chứa thông tin nhạy cảm trong query string (ví dụ `/reset-password?token=abc123`) mà không có `Referrer-Policy` phù hợp, nếu trang đó có một link dẫn ra ngoài (ví dụ link "Điều khoản sử dụng" trỏ tới domain khác), toàn bộ URL kèm `token=abc123` có thể bị gửi kèm trong header `Referer` tới domain đó — vô tình làm lộ token nhạy cảm cho một bên thứ ba không liên quan. Cấu hình chi tiết `Referrer-Policy` (và các giá trị khác như `no-referrer`, `same-origin`) nằm ngoài phạm vi chương này — chỉ cần biết tên và mục đích để tra cứu khi cần.

Tóm lại bốn điều cần nhớ khi mang chương này vào một dự án production thật: (1) CORS là cơ chế trình duyệt, không phải server — đừng debug sai hướng khi thấy lỗi console mà server log vẫn sạch; (2) luôn khai báo origin cụ thể qua `WithOrigins`, tránh `AllowAnyOrigin()` trừ khi bạn thực sự có ý định mở API cho mọi origin đọc mà không dùng credentials; (3) `UseCors()`/`UseHsts()` phải thực sự được gọi trong pipeline, đúng vị trí — định nghĩa policy không tự động bật middleware; (4) các security header (HSTS, `nosniff`, CSP) là lớp phòng thủ bổ sung, không thay thế cho xác thực/phân quyền đúng đắn ở tầng server.

**Tiếp theo →** [P9 · CI/CD với GitHub Actions](../p9-devops/cicd-github-actions.md)
