---
tier: core
status: core
owner: core-team
verified_on: "2026-07-03"
dotnet_version: "10.0"
bloom: "áp dụng"
requires: [p3-validation]
est_minutes_fast: 35
---

# OpenAPI & Swagger: để API tự mô tả chính nó

!!! info "Bạn đang ở đây · P3 → node `p3-openapi`"
    **cần trước:** dựng được minimal api với data annotations validation, biết endpoint trả về status code và body gì.
    **mở khoá sau bài này:** sinh sdk client tự động từ spec, tích hợp api gateway, xác thực jwt (tài liệu hoá header authorization), test tự động dựa trên contract.
    ⏱️ Fast path ~35 phút · Deep dive cuối bài (tuỳ chọn, không bắt buộc).

> **Mục tiêu (đo được):** Sau bài này bạn **giải thích** được OpenAPI là gì và khác Swagger UI ở điểm nào, **kích hoạt** được `AddOpenApi`/`MapOpenApi` có sẵn trong .NET để sinh ra file đặc tả JSON, **áp dụng** được `WithSummary`/`WithDescription`/`Produces` để làm giàu tài liệu cho từng endpoint, và **so sánh** được khi nào cần thêm Swashbuckle để có giao diện đọc trực quan.

---

## 0. Đoán nhanh (30 giây)

Bạn vừa viết xong 15 endpoint cho một API bán hàng. Đội frontend (một nhóm khác, ở múi giờ khác) cần biết: endpoint nào tồn tại, nhận body gì, trả về gì, lỗi ra sao. Bạn sẽ làm gì?

??? question "Đáp án (bấm để mở sau khi đã đoán)"
    Cách tệ nhất (nhưng rất phổ biến): viết một file Word hoặc trang Confluence liệt kê tay từng endpoint. Vấn đề: **file đó lỗi thời ngay từ commit tiếp theo** — bạn đổi tên field trong code nhưng quên cập nhật tài liệu, và không có gì báo cho bạn biết điều đó.

    Cách đúng: để chính **code** sinh ra tài liệu. Mỗi endpoint, mỗi kiểu dữ liệu, mỗi status code đã được khai báo trong C# — chỉ cần một cơ chế đọc lại các khai báo đó (qua reflection) và xuất ra một đặc tả chuẩn hoá. Đây chính là việc **OpenAPI** làm. Tài liệu không bao giờ lỗi thời vì nó **là** code, không phải một bản sao chép tay của code.

---

## 1. OpenAPI là gì: một đặc tả chuẩn để mô tả REST API

**OpenAPI** là một đặc tả (specification) dạng văn bản — thường viết ở định dạng JSON hoặc YAML — mô tả đầy đủ hình dạng của một REST API: có những endpoint nào, mỗi endpoint nhận tham số/body gì, trả về status code và body gì, cần header xác thực nào.

Nói cách khác, OpenAPI **không phải là một công cụ** hay một thư viện — nó là một **định dạng file**, giống như HTML là định dạng để mô tả một trang web. Bất kỳ công cụ nào (Swagger UI, Postman, trình sinh mã client) chỉ cần đọc được file này là hiểu toàn bộ API mà không cần con người giải thích thêm.

Dưới đây là một mẩu trích cực nhỏ từ một file OpenAPI (JSON), chỉ để thấy hình dạng — không cần hiểu hết ngay:

```json title="openapi-mau-trich.json"
{
  "openapi": "3.0.1",
  "paths": {
    "/products/{id}": {
      "get": {
        "summary": "Lấy thông tin sản phẩm theo id",
        "responses": {
          "200": { "description": "Tìm thấy sản phẩm" },
          "404": { "description": "Không tìm thấy" }
        }
      }
    }
  }
}
```

Chỉ nhìn JSON này, một công cụ (hoặc một lập trình viên frontend) đã biết: có endpoint `GET /products/{id}`, có thể trả 200 hoặc 404 — không cần hỏi ai, không cần đọc code C#.

### Vì sao cần OpenAPI: hai lý do cụ thể

**Lý do 1 — tài liệu sống thay vì tài liệu chết.** Một file Word hay trang wiki mô tả API là "tài liệu chết": viết tay, không liên kết với code, và **im lặng lỗi thời** — không có cảnh báo nào khi code đổi mà tài liệu không đổi theo. Ngược lại, file OpenAPI được **sinh ra từ chính code** (qua reflection đọc route, kiểu tham số, kiểu trả về) mỗi lần ứng dụng khởi động. Đổi code là tài liệu tự đổi theo — không có khái niệm "quên cập nhật".

**Lý do 2 — sinh code client tự động.** Khi có file đặc tả chuẩn hoá, các công cụ như `openapi-generator` hoặc `NSwag` có thể đọc file đó và **tự viết ra** class C#, TypeScript, hay Kotlin tương ứng với từng endpoint — đội frontend không cần gõ tay `fetch("/products/" + id)` và tự đoán field trả về là gì; họ gọi một hàm `GetProductById(id)` đã được sinh sẵn, đúng kiểu dữ liệu, báo lỗi biên dịch ngay nếu server đổi contract.

!!! danger "Hiểu lầm phổ biến: OpenAPI và Swagger là một thứ"
    Sai, và đây là nhầm lẫn phổ biến nhất trong mục này — sẽ được làm rõ ở mục 3. Ghi nhớ tạm thời: **OpenAPI là cái đặc tả** (file JSON/YAML mô tả API), còn **Swagger là tên một bộ công cụ** đọc đặc tả đó. Có OpenAPI không bắt buộc phải có Swagger; có nhiều công cụ khác cũng đọc được OpenAPI.

---

## 2. `AddOpenApi`/`MapOpenApi`: sinh đặc tả JSON, package chính chủ Microsoft

Từ .NET 9, Microsoft cung cấp package `Microsoft.AspNetCore.OpenApi` với hai phương thức để tự động sinh file OpenAPI từ các endpoint Minimal API đã khai báo:

- `builder.Services.AddOpenApi()` — đăng ký dịch vụ sinh đặc tả OpenAPI (đọc route, tham số, kiểu trả về qua reflection lúc khởi động).
- `app.MapOpenApi()` — mở một endpoint HTTP (mặc định `/openapi/v1.json`) để **trả về** file đặc tả đó dưới dạng JSON khi có ai gọi.

`Microsoft.AspNetCore.OpenApi` **vẫn là một package NuGet riêng** — không phải một phần "lõi" nằm cứng trong Web SDK. Sở dĩ nhiều người tưởng "không cần cài gì cả" là vì từ .NET 9, template `dotnet new webapi` tự động thêm sẵn `<PackageReference Include="Microsoft.AspNetCore.OpenApi" />` vào file `.csproj` khi scaffold — cảm giác như có sẵn, nhưng thực ra package đã được thêm hộ bạn. Nếu bạn tạo project bằng template `dotnet new web` (trần, không phải bản `webapi`), hoặc thêm OpenAPI vào một project có sẵn, bạn phải tự cài:

```bash
dotnet add package Microsoft.AspNetCore.OpenApi
```

Thiếu package này, gọi `AddOpenApi()`/`MapOpenApi()` sẽ lỗi biên dịch **CS1061** ("không chứa định nghĩa cho `AddOpenApi`") — không phải lỗi runtime, mà là lỗi ngay lúc build.

Ví dụ tối thiểu, độc lập, chỉ minh hoạ đúng hai phương thức này (giả định project đã có package `Microsoft.AspNetCore.OpenApi`, xem trên):

```csharp title="Program.cs"
// test:compile AddOpenApi/MapOpenApi cần package Microsoft.AspNetCore.OpenApi (dotnet new webapi tự thêm từ .NET 9+, dotnet new web trần thì phải "dotnet add package" thủ công)
var builder = WebApplication.CreateBuilder(args);
builder.Services.AddOpenApi();

var app = builder.Build();
app.MapOpenApi();

app.MapGet("/products/{id}", (int id) => Results.Ok(new { Id = id, Name = "Bàn phím cơ" }));

app.Run();
```

Chạy ứng dụng này rồi gọi `GET /openapi/v1.json`, bạn nhận về một file JSON đầy đủ mô tả endpoint `/products/{id}` — không cần viết thêm một dòng mô tả nào, vì thông tin (route, kiểu tham số `int`, kiểu trả về) đã có sẵn ngay trong khai báo `MapGet`.

```text title="Gọi thử"
GET /openapi/v1.json

→ 200 OK, Content-Type: application/json
{
  "openapi": "3.0.1",
  "info": { "title": "...", "version": "1.0.0" },
  "paths": {
    "/products/{id}": {
      "get": {
        "parameters": [
          { "name": "id", "in": "path", "required": true, "schema": { "type": "integer" } }
        ],
        "responses": { "200": { "description": "OK" } }
      }
    }
  }
}
```

### Nếu quên `MapOpenApi()`

Nếu bạn gọi `AddOpenApi()` (đăng ký dịch vụ) nhưng **quên** gọi `app.MapOpenApi()` (mở endpoint để lấy kết quả), ứng dụng vẫn build và chạy bình thường — không có lỗi biên dịch, không có exception lúc khởi động. Nhưng khi gọi `GET /openapi/v1.json`, bạn nhận về **404 Not Found**, vì chưa có route nào được đăng ký để phục vụ đường dẫn đó. Đây là lỗi cấu hình im lặng: dễ tưởng nhầm là "OpenAPI chưa hoạt động" trong khi thực ra chỉ thiếu một dòng map endpoint.

Ngược lại, nếu bạn gọi `app.MapOpenApi()` mà **quên** `builder.Services.AddOpenApi()` ở trên, ứng dụng sẽ ném exception ngay lúc khởi động (`InvalidOperationException`, thiếu dịch vụ cần thiết đã được `MapOpenApi` yêu cầu từ DI container) — lỗi này ồn ào hơn, dễ phát hiện hơn lỗi thiếu `MapOpenApi()`.

---

## 3. Swagger UI: một giao diện web để đọc đặc tả OpenAPI, không phải bản thân đặc tả

**Swagger UI** là một trang web (HTML/CSS/JavaScript) đọc một file đặc tả OpenAPI và hiển thị nó dưới dạng giao diện có thể bấm được: danh sách endpoint xổ xuống, nút "Try it out" để gọi thử API ngay trên trình duyệt, xem trước response mẫu.

Điểm cần phân biệt rõ, đúng như đã hẹn ở mục 1:

| | OpenAPI | Swagger UI |
|---|---|---|
| Bản chất | Một **đặc tả** (định dạng file JSON/YAML) | Một **công cụ** (trang web đọc đặc tả) |
| Vai trò | Định nghĩa API trông như thế nào | Hiển thị định nghĩa đó cho con người đọc/bấm thử |
| Có thể thay thế bằng gì | Không — đây là chuẩn ngành (trước đây gọi "Swagger specification", từ 2016 đổi tên thành "OpenAPI Specification" khi được Linux Foundation tiếp quản) | Có — Redoc, Postman, hoặc trình sinh code client khác cũng đọc được cùng file OpenAPI |
| Sinh ra bởi | `AddOpenApi()`/`MapOpenApi()` (mục 2) | Package riêng, ví dụ Swashbuckle (mục 5) |

Nói ngắn gọn: **OpenAPI là dữ liệu, Swagger UI là một cách hiển thị dữ liệu đó**. Bạn có thể có OpenAPI mà không có Swagger UI (dùng `MapOpenApi()` thuần, chỉ trả JSON, không có giao diện) — vẫn hữu ích cho việc sinh code client tự động, chỉ là con người không có giao diện đẹp để bấm thử trực tiếp.

---

## 4. Làm giàu tài liệu endpoint: `WithSummary`, `WithDescription`, `Produces`

Chỉ khai báo `MapGet("/products/{id}", ...)` cho ra một đặc tả OpenAPI **đúng** nhưng **cụt lủn** — tên endpoint, kiểu tham số, nhưng không giải thích gì bằng lời cho người đọc. ASP.NET Core cung cấp sẵn ba phương thức mở rộng (extension method) để thêm mô tả, gắn trực tiếp sau lời gọi `Map...`.

**`WithSummary`** — thêm một dòng tóm tắt ngắn cho endpoint, hiển thị làm tiêu đề trong Swagger UI.

```csharp title="Program.cs"
// test:compile WithSummary thêm tóm tắt ngắn cho endpoint
var builder = WebApplication.CreateBuilder(args);
builder.Services.AddOpenApi();
var app = builder.Build();
app.MapOpenApi();

app.MapGet("/products/{id}", (int id) => Results.Ok(new { Id = id, Name = "Bàn phím cơ" }))
   .WithSummary("Lấy thông tin một sản phẩm theo id");

app.Run();
```

**`WithDescription`** — thêm đoạn mô tả dài hơn, giải thích chi tiết hành vi (khác `WithSummary` ở độ dài và mục đích: tóm tắt một dòng vs. giải thích đầy đủ).

```csharp title="Program.cs"
// test:compile WithDescription thêm mô tả chi tiết cho endpoint
var builder = WebApplication.CreateBuilder(args);
builder.Services.AddOpenApi();
var app = builder.Build();
app.MapOpenApi();

app.MapGet("/products/{id}", (int id) => Results.Ok(new { Id = id, Name = "Bàn phím cơ" }))
   .WithDescription("Trả về thông tin chi tiết một sản phẩm dựa trên id. " +
                     "Nếu id không tồn tại trong hệ thống, trả về 404 Not Found.");

app.Run();
```

**`Produces`** — khai báo rõ endpoint này trả về kiểu dữ liệu gì và với status code nào, giúp đặc tả OpenAPI mô tả chính xác **hình dạng response** (không chỉ "có trả JSON" chung chung).

```csharp title="Program.cs"
// test:compile Produces khai báo kiểu response và status code cho OpenAPI
var builder = WebApplication.CreateBuilder(args);
builder.Services.AddOpenApi();
var app = builder.Build();
app.MapOpenApi();

app.MapGet("/products/{id}", (int id) =>
    id == 1
        ? Results.Ok(new ProductDto(1, "Bàn phím cơ"))
        : Results.NotFound())
   .Produces<ProductDto>(StatusCodes.Status200OK)
   .Produces(StatusCodes.Status404NotFound);

app.Run();

public record ProductDto(int Id, string Name);
```

Với `Produces<ProductDto>(200)`, đặc tả OpenAPI sinh ra sẽ mô tả chính xác **schema** của `ProductDto` (có field `Id` kiểu số, `Name` kiểu chuỗi) cho response 200 — đây chính là thông tin mà trình sinh code client (nói ở mục 1) cần để tạo ra class tương ứng phía frontend. Không gọi `Produces`, framework vẫn suy luận được kiểu trả về ở nhiều trường hợp đơn giản qua kiểu generic của `Results.Ok<T>`, nhưng khai báo tường minh giúp đặc tả chính xác hơn với các trường hợp phức tạp (nhiều status code khác kiểu nhau, như ví dụ trên: 200 có body kiểu `ProductDto`, 404 không có body).

Ba phương thức này có thể gắn liên tiếp trên cùng một endpoint (method chaining), vì mỗi phương thức đều trả về chính `RouteHandlerBuilder` để gọi tiếp:

```csharp title="Program.cs"
// test:compile kết hợp WithSummary, WithDescription, Produces trên cùng một endpoint
var builder = WebApplication.CreateBuilder(args);
builder.Services.AddOpenApi();
var app = builder.Build();
app.MapOpenApi();

app.MapGet("/products/{id}", (int id) =>
    id == 1
        ? Results.Ok(new ProductDto(1, "Bàn phím cơ"))
        : Results.NotFound())
   .WithSummary("Lấy sản phẩm theo id")
   .WithDescription("Trả 200 kèm chi tiết sản phẩm nếu tìm thấy, 404 nếu không.")
   .Produces<ProductDto>(StatusCodes.Status200OK)
   .Produces(StatusCodes.Status404NotFound);

app.Run();

public record ProductDto(int Id, string Name);
```

---

## 5. Swashbuckle: lựa chọn thay thế có giao diện Swagger UI phong phú hơn

`MapOpenApi()` (mục 2) chỉ sinh ra **file JSON thô** — hữu ích cho máy đọc (trình sinh code client), nhưng không có giao diện để con người bấm thử trực tiếp trên trình duyệt. **Swashbuckle.AspNetCore** là một package ngoài phổ biến, đóng gói sẵn cả việc sinh đặc tả OpenAPI **lẫn** một trang Swagger UI đầy đủ, cho phép bấm "Try it out" gọi thử endpoint ngay trên trình duyệt mà không cần Postman.

```csharp title="Program.cs"
// test:skip cần package ngoài Swashbuckle.AspNetCore, không có sẵn trong dotnet new web trần
using Microsoft.OpenApi.Models;

var builder = WebApplication.CreateBuilder(args);

builder.Services.AddEndpointsApiExplorer();
builder.Services.AddSwaggerGen(options =>
{
    options.SwaggerDoc("v1", new OpenApiInfo { Title = "Product API", Version = "v1" });
});

var app = builder.Build();

if (app.Environment.IsDevelopment())
{
    app.UseSwagger();
    app.UseSwaggerUI(); // giao diện tại /swagger, có nút "Try it out"
}

app.MapGet("/products/{id}", (int id) => Results.Ok(new { Id = id, Name = "Bàn phím cơ" }));

app.Run();
```

Khi nào chọn Swashbuckle thay vì `AddOpenApi`/`MapOpenApi` thuần: khi đội của bạn **cần giao diện trực quan** để nhân viên QA hoặc lập trình viên frontend tự gọi thử API mà không cần công cụ ngoài (Postman), hoặc khi dự án đã quen thuộc với hệ sinh thái Swashbuckle từ các phiên bản .NET cũ hơn (trước .NET 9, `AddOpenApi()` chưa tồn tại, Swashbuckle từng là lựa chọn phổ biến nhất để có OpenAPI trong ASP.NET Core). Nhược điểm: thêm một package ngoài cần theo dõi cập nhật, so với `AddOpenApi()` được bảo trì trực tiếp trong Web SDK.

---

## Cạm bẫy & thực chiến

- **Quên `app.MapOpenApi()` sau khi đã `AddOpenApi()`.** Ứng dụng chạy bình thường, không lỗi lúc khởi động, nhưng gọi `/openapi/v1.json` trả về **404** — dễ nhầm tưởng toàn bộ tính năng OpenAPI "không hoạt động" trong khi chỉ thiếu một dòng map endpoint (đã nói ở mục 2).
- **Tưởng nhầm OpenAPI và Swagger là một.** Dẫn tới việc tìm sai từ khóa khi debug ("tại sao Swagger của tôi không chạy" trong khi thực ra bạn chỉ dùng `MapOpenApi()` thuần, không có Swashbuckle nào cả) — luôn hỏi lại: đang nói về **đặc tả** (OpenAPI) hay **giao diện đọc đặc tả đó** (Swagger UI, Redoc, ...).
- **Để `MapOpenApi()`/Swagger UI mở công khai ở production mà không cân nhắc.** File đặc tả OpenAPI liệt kê **toàn bộ** route nội bộ, kiểu dữ liệu, và đôi khi cả comment mô tả nghiệp vụ nhạy cảm — với API công khai cho đối tác thì hợp lý, nhưng với API nội bộ, nên cân nhắc chỉ bật ở môi trường Development (`if (app.Environment.IsDevelopment())`, xem cách Swashbuckle thường làm ở mục 5), tránh lộ bản đồ toàn bộ hệ thống cho người ngoài dò quét.
- **Không khai báo `Produces` cho các nhánh lỗi (400, 404, 409...).** Đặc tả OpenAPI khi đó chỉ mô tả "đường vui" (happy path) — trình sinh code client phía frontend sẽ không biết trước các trường hợp lỗi có thể xảy ra, dẫn tới code frontend không xử lý lỗi đúng cách (ví dụ không có nhánh `catch` cho 404 vì "tài liệu đâu có nói sẽ trả 404").
- **Tin rằng OpenAPI tự sinh luôn chính xác 100% mà không kiểm tra lại.** Cơ chế suy luận kiểu qua reflection hoạt động tốt với các trường hợp đơn giản, nhưng với `IResult` trả về từ nhiều nhánh khác kiểu nhau (như `Results.Ok<T>` hoặc `Results.NotFound()` tùy điều kiện `if`), nếu không khai báo tường minh bằng `Produces`, đặc tả sinh ra có thể chỉ ghi nhận nhánh mà framework "đoán" được — luôn kiểm tra lại file `/openapi/v1.json` thực tế sau khi thêm endpoint mới, đừng mặc định nó đúng.

---

## Bài tập

### Bài 1 — Có giàn giáo: thêm mô tả OpenAPI cho endpoint tạo sản phẩm

Hoàn thiện endpoint `POST /products` sao cho đặc tả OpenAPI của nó có: tóm tắt ngắn, mô tả chi tiết, và khai báo đúng hai status code có thể trả về (201 khi tạo thành công, 400 khi dữ liệu sai — giả định đã có validation tự động từ chương trước). Điền vào chỗ `// TODO`.

```csharp title="Program.cs"
// test:compile bài tập thêm mô tả OpenAPI cho endpoint tạo sản phẩm
var builder = WebApplication.CreateBuilder(args);
builder.Services.AddOpenApi();
var app = builder.Build();
app.MapOpenApi();

app.MapPost("/products", (CreateProductRequest request) =>
        Results.Created($"/products/1", new ProductDto(1, request.Name)))
    // TODO 1: thêm tóm tắt ngắn "Tạo sản phẩm mới"
    // TODO 2: thêm mô tả chi tiết giải thích 201 kèm Location, 400 nếu Name rỗng
    // TODO 3: khai báo Produces cho 201 (kiểu ProductDto) và 400
    ;

app.Run();

public record CreateProductRequest(string Name);
public record ProductDto(int Id, string Name);
```

??? success "Lời giải + giải thích"
    ```csharp title="Program.cs"
    // test:compile bài tập thêm mô tả OpenAPI cho endpoint tạo sản phẩm
    var builder = WebApplication.CreateBuilder(args);
    builder.Services.AddOpenApi();
    var app = builder.Build();
    app.MapOpenApi();

    app.MapPost("/products", (CreateProductRequest request) =>
            Results.Created($"/products/1", new ProductDto(1, request.Name)))
        .WithSummary("Tạo sản phẩm mới")
        .WithDescription("Trả 201 kèm header Location trỏ tới sản phẩm vừa tạo. " +
                          "Trả 400 nếu Name rỗng hoặc thiếu.")
        .Produces<ProductDto>(StatusCodes.Status201Created)
        .Produces(StatusCodes.Status400BadRequest);

    app.Run();

    public record CreateProductRequest(string Name);
    public record ProductDto(int Id, string Name);
    ```

    - `WithSummary` là dòng tóm tắt hiển thị làm tiêu đề trong công cụ đọc OpenAPI (Swagger UI hay tương đương); `WithDescription` là đoạn giải thích dài hơn, thường xuất hiện khi người đọc bấm mở rộng chi tiết endpoint.
    - `Produces<ProductDto>(201)` khai báo rõ status 201 có body kiểu `ProductDto` — khớp với `Results.Created` trả về đối tượng đó.
    - `Produces(400)` không kèm generic vì response lỗi validation không có kiểu cố định đơn giản — chỉ cần khai báo status code để đặc tả biết nhánh lỗi này tồn tại.

### Bài 2 — Thiết kế: quyết định chiến lược tài liệu cho hai loại API khác nhau

Công ty bạn có hai API:

- **API nội bộ** dùng giữa các service trong cùng hệ thống (chỉ đội backend gọi lẫn nhau), không có UI, không có bên thứ ba nào truy cập.
- **API công khai** cho đối tác bên ngoài tích hợp vào hệ thống của họ, đối tác cần tự đọc tài liệu và tự viết code gọi API mà không cần hỏi trực tiếp đội của bạn.

Với mỗi API, quyết định: có cần `MapOpenApi()` không, có cần thêm Swashbuckle (Swagger UI) không, có nên public route `/openapi/v1.json` ra ngoài Internet không. Giải thích lý do cho từng lựa chọn.

??? success "Lời giải + giải thích"
    **API nội bộ:**
    - Vẫn nên bật `MapOpenApi()` — dù không có UI, đặc tả JSON vẫn hữu ích để các service khác trong cùng hệ thống tự sinh code client gọi lẫn nhau (lý do 2 ở mục 1), và để chính đội backend tra cứu nhanh route nào tồn tại.
    - Không nhất thiết cần Swashbuckle/Swagger UI — vì không có nhu cầu "bấm thử trên trình duyệt" từ người ngoài, JSON thô đã đủ cho máy đọc lẫn nhau; nếu đội backend muốn xem trực quan lúc dev, có thể bật Swashbuckle **chỉ trong môi trường Development**.
    - **Không** nên public `/openapi/v1.json` ra ngoài Internet — đây là route nội bộ, lộ ra ngoài đồng nghĩa với việc lộ toàn bộ bản đồ hệ thống nội bộ cho bất kỳ ai quét được domain (đúng cạm bẫy đã nêu ở trên).

    **API công khai cho đối tác:**
    - Bắt buộc cần `MapOpenApi()` (hoặc tương đương) — đây chính là lý do cốt lõi để đối tác tự sinh code client, không cần hỏi trực tiếp đội của bạn (lý do 2, mục 1).
    - Rất nên thêm Swashbuckle/Swagger UI — đối tác thường không có sẵn tooling nội bộ để đọc JSON thô, giao diện "Try it out" giúp họ tự khám phá API mà không cần liên hệ hỗ trợ, tiết kiệm thời gian cả hai bên.
    - **Nên** public route đặc tả OpenAPI (và cả Swagger UI) một cách có kiểm soát — vì đây chính là mục đích của API công khai; tuy vậy vẫn cần rà soát để không vô tình để lộ các route nội bộ khác nằm chung ứng dụng (nếu API công khai và API nội bộ dùng chung một `WebApplication`, cần tách file đặc tả riêng cho từng nhóm, không gộp chung).

---

## Tự kiểm tra

1. OpenAPI là một công cụ hay một định dạng đặc tả? Giải thích khác biệt với Swagger UI.
2. Cần gọi hai phương thức nào để bật tính năng sinh OpenAPI có sẵn trong .NET 9+, và mỗi phương thức làm gì?
3. Nếu gọi `AddOpenApi()` nhưng quên `MapOpenApi()`, gọi `/openapi/v1.json` sẽ trả về gì?
4. `WithSummary` và `WithDescription` khác nhau ở điểm gì?
5. `Produces<T>(200)` cung cấp thông tin gì cho đặc tả OpenAPI mà nếu không gọi, framework có thể suy luận thiếu chính xác?
6. Vì sao không nên luôn để `/openapi/v1.json` và Swagger UI mở công khai ở production cho mọi loại API?
7. Khi nào nên chọn Swashbuckle thay vì `AddOpenApi`/`MapOpenApi` thuần?

??? note "Đáp án"
    1. OpenAPI là một **định dạng đặc tả** (file JSON/YAML mô tả API), không phải công cụ. Swagger UI là một **công cụ** (trang web) đọc đặc tả đó và hiển thị cho con người — có OpenAPI không bắt buộc phải có Swagger UI.
    2. `builder.Services.AddOpenApi()` đăng ký dịch vụ sinh đặc tả (đọc route/kiểu dữ liệu qua reflection); `app.MapOpenApi()` mở endpoint HTTP (mặc định `/openapi/v1.json`) để trả về file đặc tả đó.
    3. Trả về **404 Not Found** — ứng dụng vẫn chạy bình thường, không có lỗi khởi động, chỉ là chưa có route nào phục vụ đường dẫn đó.
    4. `WithSummary` là dòng tóm tắt ngắn (một câu, hiển thị làm tiêu đề); `WithDescription` là đoạn mô tả dài hơn, giải thích chi tiết hành vi của endpoint.
    5. Nó khai báo tường minh **schema** (cấu trúc field, kiểu dữ liệu) của response ứng với đúng status code đó — hữu ích khi endpoint có nhiều nhánh trả về khác kiểu nhau (ví dụ 200 có body, 404 không có body) mà suy luận tự động qua kiểu generic có thể không bắt hết.
    6. Vì file đặc tả liệt kê toàn bộ route nội bộ, kiểu dữ liệu, và đôi khi thông tin nghiệp vụ nhạy cảm — với API nội bộ không phục vụ bên ngoài, để lộ đặc tả này ra Internet đồng nghĩa với việc trao bản đồ hệ thống cho người ngoài dò quét.
    7. Khi cần giao diện trực quan để người dùng (QA, frontend, đối tác) tự bấm thử API trên trình duyệt mà không cần Postman, hoặc dự án đã quen thuộc với hệ sinh thái Swashbuckle từ trước — đổi lại phải chấp nhận thêm một package ngoài cần bảo trì, so với `AddOpenApi()` có sẵn trong Web SDK.

---

??? abstract "DEEP DIVE — Versioning đặc tả, transformer tuỳ biến, và bảo mật thông tin nhạy cảm trong OpenAPI"
    **Nhiều phiên bản đặc tả cùng lúc.** `AddOpenApi()` cho phép đặt tên tài liệu (ví dụ `AddOpenApi("v1")`, `AddOpenApi("v2")`) khi ứng dụng có nhiều phiên bản API chạy song song — mỗi tên tương ứng với một route riêng (`/openapi/v1.json`, `/openapi/v2.json`), cho phép đối tác cũ vẫn dùng được `v1` trong khi bạn phát triển `v2` mà không phá vỡ hợp đồng đã ký với khách hàng hiện tại.

    **Document transformer để chỉnh sửa đặc tả trước khi xuất ra.** `AddOpenApi` hỗ trợ đăng ký một `IOpenApiDocumentTransformer` — một hook chạy **sau khi** đặc tả đã được sinh tự động nhưng **trước khi** trả về client, cho phép chỉnh sửa thủ công (ví dụ thêm mô tả tổng quan cho toàn bộ API, thêm thông tin liên hệ đội hỗ trợ, hoặc lọc bỏ một số route nội bộ không muốn công khai dù chúng chạy chung ứng dụng với các route công khai). Đây là cách xử lý đúng cho tình huống "API công khai và API nội bộ dùng chung một `WebApplication`" đã nhắc ở bài tập 2.

    **Không để lộ chi tiết bảo mật qua đặc tả.** Đặc tả OpenAPI mô tả **hình dạng** dữ liệu (tên field, kiểu), nhưng cần cẩn thận không để `Produces<T>` hoặc kiểu DTO trả về vô tình chứa các field nhạy cảm nội bộ (ví dụ trả nguyên entity Entity Framework Core có field `PasswordHash` hay `InternalNotes` thay vì một DTO đã lọc riêng) — đây là lỗi thiết kế phổ biến: entity dùng cho tầng dữ liệu và DTO dùng cho tầng API nên luôn là hai kiểu tách biệt, đặc tả OpenAPI chỉ nên phản ánh đúng những gì bạn **muốn** công khai, không phải toàn bộ những gì tồn tại bên trong code.

    **Đặc tả không thay thế được kiểm thử hợp đồng (contract testing).** Có đặc tả OpenAPI chính xác giúp sinh code client đúng, nhưng không tự động đảm bảo server **luôn tuân thủ** đặc tả đó khi code thay đổi trong tương lai — với hệ thống lớn nhiều team, nên cân nhắc thêm bước kiểm thử tự động so khớp response thực tế với đặc tả đã công bố (contract testing), nằm ngoài phạm vi chương này.

**Tiếp theo →** [P3 · Gọi API bên ngoài (HttpClient)](goi-api-ngoai.md)
