---
tier: core
status: core
owner: core-team
verified_on: "2026-07-03"
dotnet_version: "10.0"
bloom: áp dụng
requires: [p7-state]
est_minutes_fast: 30
---

# Gọi API Backend từ Blazor WASM

!!! info "Bạn đang ở đây"
    cần trước: state container service/`CascadingValue` để chia sẻ dữ liệu giữa component, `HttpClient`/`GetFromJsonAsync`/`PostAsJsonAsync` đã học ở phần backend (gọi API bên ngoài từ ASP.NET Core).
    mở khoá: component Blazor WASM hiển thị dữ liệu thật lấy từ một backend API riêng, xử lý đúng trạng thái đang tải/lỗi khi gọi bất đồng bộ, và nền tảng để học JWT authentication (đính token vào `HttpClient` mỗi request) ở chương sau.

> Mục tiêu (đo được): sau chương này bạn **áp dụng** được `HttpClient` đã học ở backend để gọi API từ một component Blazor WASM, **giải thích** được vì sao CORS chặn request nếu backend chưa cấu hình, **đăng ký** được `HttpClient` có `BaseAddress` trong `Program.cs` của dự án Blazor WASM, và **viết** được một component fetch danh sách có xử lý `isLoading`/lỗi đúng cách, không gọi API trực tiếp trong phần render.

---

## 0. Đoán nhanh trước khi học

Bạn đã có một backend ASP.NET Core (học ở phần P3) chạy ở `https://localhost:5001`, có endpoint `GET /api/products` trả về danh sách sản phẩm dạng JSON. Bạn viết một component Blazor WASM sau, chạy ở `https://localhost:5002` (một project khác, một cổng khác):

```razor title="DanhSachSanPham.razor (chua chay dung)"
@page "/san-pham"
@inject HttpClient Http

<ul>
    @foreach (var sp in sanPhams)
    {
        <li>@sp.Ten</li>
    }
</ul>

@code {
    private List<SanPham> sanPhams = new();

    protected override async Task OnInitializedAsync()
    {
        sanPhams = await Http.GetFromJsonAsync<List<SanPham>>("https://localhost:5001/api/products") ?? new();
    }
}
```

Bạn mở trang, danh sách không hiện ra, và console của browser (F12) in ra một dòng lỗi màu đỏ nhắc tới "CORS policy". Backend của bạn **không hề sập** — bạn có thể gọi đúng URL đó bằng Postman hoặc trực tiếp trên thanh địa chỉ browser và thấy JSON trả về bình thường. Vì sao gọi từ Postman được nhưng gọi từ component Blazor WASM lại lỗi?

??? question "Đoán trước, đáp án ở dưới"
    Gợi ý: Blazor WASM chạy ở đâu (browser hay server), và trình duyệt có áp dụng luật riêng cho request JavaScript/WASM gọi sang một **origin khác** (domain/cổng khác) không?

??? note "Đáp án"
    Đây là lỗi **CORS bị chặn** — mục 2 giải thích chi tiết. Postman và thanh địa chỉ browser không bị luật CORS áp dụng (CORS chỉ áp dụng cho request phát ra từ code JavaScript/WASM chạy **trong** một trang web), nhưng `HttpClient` trong Blazor WASM chạy hoàn toàn trong browser, nên mọi request nó gửi đều đi qua đúng cơ chế bảo mật CORS của browser như một request `fetch()` bình thường trong JavaScript. Vì backend (`:5001`) và Blazor WASM (`:5002`) là hai origin khác nhau (khác cổng), và backend **chưa cấu hình** cho phép origin `:5002` gọi tới, browser tự chặn response trước khi trả về cho code Blazor — dù backend đã xử lý và trả JSON thành công. Mục 1 nhắc lại nhanh vì sao cách gọi `HttpClient` này giống hệt những gì bạn đã học ở backend, và mục 2-3 sửa đúng lỗi CORS này.

---

## 1. `HttpClient` trong Blazor WASM là ĐÚNG API bạn đã học ở backend — chỉ khác nơi chạy

Bạn đã học `HttpClient`, `GetFromJsonAsync<T>`, `PostAsJsonAsync<T>`, `IsSuccessStatusCode`, xử lý timeout bằng `TaskCanceledException` ở phần backend (gọi API bên ngoài từ một ASP.NET Core service) — **toàn bộ các API đó dùng lại nguyên vẹn** trong Blazor WASM, không có method mới nào cần học. Sự khác biệt duy nhất về mặt code là: bạn `@inject HttpClient Http` vào component `.razor` thay vì tiêm qua `IHttpClientFactory` vào một endpoint hoặc service backend.

Sự khác biệt thật sự quan trọng không nằm ở API C#, mà ở **nơi code này thực thi**: một `HttpClient` gọi từ backend ASP.NET Core chạy trên **server**, gửi request trực tiếp qua mạng, không bị luật CORS của browser chi phối (CORS là luật của browser, backend-tới-backend không đi qua browser). Một `HttpClient` gọi từ Blazor WASM chạy **hoàn toàn trong browser** (như đã học ở chương tổng quan Blazor) — mọi request nó gửi đi đều bị browser áp dụng đúng luật bảo mật như bất kỳ request JavaScript nào khác, bao gồm CORS. Mục 2 định nghĩa CORS và minh hoạ cụ thể lỗi ở mục 0.

---

## 2. CORS — định nghĩa và lỗi cụ thể khi backend chưa cấu hình

**Định nghĩa (một câu):** CORS (Cross-Origin Resource Sharing) là một cơ chế bảo mật của **browser** (không phải của .NET hay của backend) yêu cầu server đích phải **chủ động cho phép rõ ràng** (qua header response `Access-Control-Allow-Origin`) trước khi browser chuyển kết quả response về cho code JavaScript/WASM đang chạy ở một **origin khác** (khác domain, hoặc khác cổng, hoặc khác giao thức http/https) so với origin của server đó.

Trong ví dụ mục 0: Blazor WASM chạy ở origin `https://localhost:5002`, gọi API ở origin `https://localhost:5001` — hai cổng khác nhau tính là **hai origin khác nhau** dù cùng chạy trên máy bạn (`localhost`). Nếu backend `:5001` không khai báo rằng nó chấp nhận request từ origin `:5002`, browser sẽ **thực sự gửi request đi** (bạn có thể thấy nó trong tab Network của DevTools, kèm status 200), nhưng browser **chặn không cho code Blazor đọc response đó** — đây là lý do dễ gây nhầm lẫn: request "có vẻ" đã chạy, nhưng kết quả không bao giờ tới tay component.

**Điều gì xảy ra khi dùng sai (lỗi cụ thể trong console browser):**

```text title="Console loi CORS trong browser (F12)"
Access to fetch at 'https://localhost:5001/api/products' from origin
'https://localhost:5002' has been blocked by CORS policy: No
'Access-Control-Allow-Origin' header is present on the requested resource.
```

Kèm theo đó, code C# phía Blazor nhận được một exception khi `await`:

```text title="Exception trong OnInitializedAsync khi CORS chan"
System.Net.Http.HttpRequestException: Error while copying content to a stream.
```

hoặc tuỳ phiên bản browser/runtime, một `TaskCanceledException`/lỗi mạng chung — điểm quan trọng cần nhớ: **không có exception nào nói rõ chữ "CORS"** ở phía C#. Chữ "CORS" chỉ xuất hiện trong console của browser (F12 → tab Console), không xuất hiện trong log/exception .NET. Đây là lý do nhiều người mới học tưởng backend bị lỗi hoặc code C# sai, trong khi thực chất backend chạy hoàn toàn đúng — chỉ thiếu một dòng cấu hình `AddCors`, xem mục 3.

!!! danger "Nhầm lẫn phổ biến: nghĩ do sai URL hoặc backend chưa chạy"
    Vì exception phía C# không nhắc tới CORS, người mới học thường đi kiểm tra sai hướng: thử lại URL, restart backend, kiểm tra route — tất cả đều đúng và không phải nguyên nhân. Luôn mở tab Console của browser (F12) **trước** khi kết luận nguyên nhân khi component Blazor WASM gọi API mà không nhận được dữ liệu — nếu dòng chữ "CORS policy" xuất hiện ở đó, nguyên nhân chắc chắn là backend chưa cho phép origin của Blazor WASM.

---

## 3. Cấu hình `AddCors` ở backend để cho phép Blazor WASM gọi

Lỗi CORS ở mục 2 được sửa ở phía **backend** (nơi bạn kiểm soát được), không phải phía Blazor WASM — Blazor WASM không có cách nào "vượt qua" CORS từ phía client, vì đây là luật browser áp dụng dựa trên header do server đích trả về.

Ví dụ tối thiểu — thêm `AddCors` vào backend ASP.NET Core (project riêng, khác project Blazor WASM):

```csharp title="Program.cs (backend - cho phep origin cua Blazor WASM)"
// test:compile cau hinh AddCors toi thieu cho phep 1 origin cu the goi API
var builder = WebApplication.CreateBuilder(args);

// Dat ten policy - dung lai ten nay khi ap dung o duoi.
builder.Services.AddCors(options =>
{
    options.AddPolicy("ChoPhepBlazorWasm", policy =>
    {
        // Origin ĐÚNG của project Blazor WASM (goc URL — khong co duong dan/API o sau).
        policy.WithOrigins("https://localhost:5002")
              .AllowAnyMethod()
              .AllowAnyHeader();
    });
});

var app = builder.Build();

// PHAI goi UseCors TRUOC khi map endpoint, va dung DUNG ten policy da dat o tren.
app.UseCors("ChoPhepBlazorWasm");

app.MapGet("/api/products", () => new[]
{
    new { Id = 1, Ten = "Ban phim" },
    new { Id = 2, Ten = "Chuot" }
});

app.Run();
```

**Điều gì xảy ra khi dùng sai:**

- **Quên gọi `app.UseCors(...)`** (chỉ đăng ký `AddCors` ở `builder.Services` nhưng không `app.UseCors`): policy được khai báo nhưng **không bao giờ áp dụng** — lỗi CORS ở mục 2 vẫn xảy ra nguyên vẹn, dễ gây nhầm lẫn vì code "trông như đã cấu hình CORS".
- **Gọi `app.UseCors(...)` sau `app.MapGet(...)`/sau khi map endpoint:** thứ tự middleware trong ASP.NET Core quan trọng — `UseCors` phải nằm **trước** các lời gọi map endpoint mà bạn muốn áp dụng CORS, nếu không endpoint sẽ chạy mà không đi qua middleware CORS, gây lỗi tương tự như quên gọi hoàn toàn.
- **Sai origin trong `WithOrigins` (ví dụ gõ nhầm `http://` thay vì `https://`, hoặc thiếu/dư số cổng):** browser so khớp origin **chính xác từng ký tự** (giao thức + domain + cổng) — chỉ khác một trong ba phần này (ví dụ Blazor WASM thực chạy ở `:5002` nhưng bạn khai báo `:5003`), CORS vẫn báo lỗi giống hệt mục 2, dù bạn đã viết `AddCors` đầy đủ.

!!! warning "`AllowAnyOrigin()` chỉ dùng khi phát triển cục bộ, không dùng cho production"
    Có một cách "tắt" hay bị lạm dụng: `policy.AllowAnyOrigin()` cho phép **mọi** origin gọi tới — hết lỗi CORS ngay, không cần khai báo đúng origin. Cách này chấp nhận được khi đang phát triển cục bộ (localhost) để tiết kiệm thời gian, nhưng **nguy hiểm cho production**: bất kỳ trang web nào trên Internet cũng có thể gọi API của bạn từ browser của người dùng khác (nếu API có thao tác ghi dữ liệu và người dùng đã đăng nhập, đây mở đường cho tấn công CSRF-like qua CORS). Luôn khai báo `WithOrigins` với đúng domain thật của frontend khi lên production, không dùng `AllowAnyOrigin()`.

---

## 4. Đăng ký `HttpClient` trong `Program.cs` của Blazor WASM

Component ở mục 0 dùng `@inject HttpClient Http` — để điều này hoạt động, `HttpClient` phải được đăng ký vào DI container của project Blazor WASM, kèm `BaseAddress` để không phải viết URL đầy đủ (`https://localhost:5001/...`) ở mỗi component.

**Định nghĩa (một câu):** trong `Program.cs` của một project Blazor WASM, `builder.Services.AddScoped(sp => new HttpClient { BaseAddress = ... })` đăng ký một `HttpClient` với địa chỉ gốc cố định vào DI container, để mọi component chỉ cần `@inject HttpClient Http` và gọi đường dẫn tương đối (`Http.GetFromJsonAsync<T>("api/products")`) thay vì lặp lại URL đầy đủ ở mỗi nơi.

Ví dụ tối thiểu — `Program.cs` của project Blazor WASM (khác hoàn toàn project backend ở mục 3):

```razor title="Program.cs (Blazor WASM)"
var builder = WebAssemblyHostBuilder.CreateDefault(args);
builder.RootComponents.Add<App>("#app");

// Dang ky HttpClient co san BaseAddress - moi component inject se dung CHUNG instance nay.
builder.Services.AddScoped(sp => new HttpClient
{
    BaseAddress = new Uri("https://localhost:5001/")
});

await builder.Build().RunAsync();
```

Với `BaseAddress` đã đặt, component ở mục 0 chỉ cần sửa lại đường dẫn tương đối:

```razor title="DanhSachSanPham.razor (dung BaseAddress da dang ky)"
@page "/san-pham"
@inject HttpClient Http

<ul>
    @foreach (var sp in sanPhams)
    {
        <li>@sp.Ten</li>
    }
</ul>

@code {
    private List<SanPham> sanPhams = new();

    protected override async Task OnInitializedAsync()
    {
        // Duong dan TUONG DOI - ket hop voi BaseAddress da dang ky -> URL day du.
        sanPhams = await Http.GetFromJsonAsync<List<SanPham>>("api/products") ?? new();
    }

    private sealed class SanPham
    {
        public int Id { get; set; }
        public string Ten { get; set; } = "";
    }
}
```

Đoạn này dùng fence `razor` (không phải `csharp`) vì `Program.cs` của Blazor WASM gọi `WebAssemblyHostBuilder`/`RootComponents` — các API chỉ tồn tại trong project Blazor WASM thật (tạo bằng `dotnet new blazorwasm`), không compile được trong project `dotnet new web` trần dùng để chạy test CI của tài liệu này.

**Điều gì xảy ra khi dùng sai:**

- **Quên đăng ký `HttpClient` hoàn toàn** (không có dòng `AddScoped(sp => new HttpClient {...})` nào trong `Program.cs`): component gọi `@inject HttpClient Http` sẽ ném lỗi ngay khi trang khởi tạo:

    ```text title="Exception khi HttpClient chua duoc dang ky vao DI"
    System.InvalidOperationException: Cannot provide a value for property 'Http'
    on type '...DanhSachSanPham'. There is no registered service of type
    'System.Net.Http.HttpClient'.
    ```

- **Đăng ký nhưng quên đặt `BaseAddress`** (`AddScoped(sp => new HttpClient())` không có `BaseAddress`): gọi `Http.GetFromJsonAsync<T>("api/products")` với đường dẫn tương đối ném đúng lỗi đã học ở backend (`InvalidOperationException: ... BaseAddress must be set`), vì `HttpClient` không biết ghép đường dẫn tương đối vào đâu.
- **Đặt `BaseAddress` sai origin (ví dụ trỏ nhầm về chính origin của Blazor WASM thay vì backend):** không lỗi ngay lúc đăng ký — request vẫn gửi đi, nhưng tới nhầm địa chỉ, thường nhận về 404 Not Found (vì route `api/products` không tồn tại ở origin sai đó) hoặc HTML của chính trang Blazor WASM (nếu origin đó có cấu hình fallback route) — dẫn tới `JsonException` khi cố parse HTML thành JSON, giống lỗi đã học ở mục 3-4 chương gọi API backend.

---

## 5. Trạng thái loading/error khi gọi API bất đồng bộ trong UI

**Định nghĩa (một câu):** pattern loading/error là cách quản lý trạng thái hiển thị của một component trong lúc chờ một lời gọi bất đồng bộ (như gọi API) hoàn tất — dùng một biến `bool isLoading` để hiện thông báo "Đang tải..." thay cho dữ liệu chưa có, và một biến chuỗi lỗi (hoặc `try/catch`) để hiện thông báo rõ ràng thay vì để trang trắng hoặc crash khi API thất bại.

Nếu component ở mục 4 gọi API mà không có `isLoading`, người dùng nhìn thấy danh sách **trống** (vì `sanPhams` khởi tạo là `new()`, rỗng) trong khoảng thời gian chờ response — không có gì báo cho họ biết trang đang tải hay đã tải xong nhưng không có dữ liệu. Nếu API lỗi (mất mạng, backend sập, CORS như mục 2), người dùng cũng thấy đúng một danh sách trống, không có thông báo lỗi nào — họ không biết nên thử lại hay đây là kết quả đúng (không có sản phẩm nào).

Ví dụ tối thiểu — component fetch danh sách với đầy đủ `isLoading` + xử lý lỗi:

```razor title="DanhSachSanPham.razor (co isLoading + xu ly loi)"
@page "/san-pham"
@inject HttpClient Http

@if (isLoading)
{
    <p>Đang tải...</p>
}
else if (thongBaoLoi is not null)
{
    <p style="color:red">Lỗi: @thongBaoLoi</p>
}
else
{
    <ul>
        @foreach (var sp in sanPhams)
        {
            <li>@sp.Ten</li>
        }
    </ul>
}

@code {
    private List<SanPham> sanPhams = new();
    private bool isLoading = true;
    private string? thongBaoLoi;

    protected override async Task OnInitializedAsync()
    {
        try
        {
            var response = await Http.GetAsync("api/products");

            if (!response.IsSuccessStatusCode)
            {
                thongBaoLoi = $"API trả về {(int)response.StatusCode}.";
                return;
            }

            sanPhams = await response.Content.ReadFromJsonAsync<List<SanPham>>() ?? new();
        }
        catch (HttpRequestException ex)
        {
            // Bao gom truong hop CORS chan (muc 2) - browser thuong bien thanh
            // HttpRequestException phia C#, khong co chu "CORS" trong message.
            thongBaoLoi = "Không thể kết nối tới API. Kiểm tra CORS hoặc backend có đang chạy không.";
        }
        finally
        {
            // finally DAM BAO isLoading tro ve false CA KHI thanh cong LAN khi loi -
            // thieu dong nay, thong bao "Dang tai..." se ket dinh mai neu co exception.
            isLoading = false;
        }
    }

    private sealed class SanPham
    {
        public int Id { get; set; }
        public string Ten { get; set; } = "";
    }
}
```

Ba trạng thái hiển thị (`isLoading = true` → "Đang tải...", `thongBaoLoi != null` → thông báo lỗi màu đỏ, còn lại → danh sách thật) loại trừ nhau rõ ràng qua `@if/else if/else` — người dùng luôn thấy đúng một trong ba trạng thái, không bao giờ thấy trang trống mơ hồ.

**Điều gì xảy ra khi dùng sai:**

- **Đặt `isLoading = false` ngay sau lời gọi `GetAsync`, không dùng `finally`:** nếu `GetAsync` ném exception (mất mạng, CORS), dòng `isLoading = false` (nằm sau lời gọi, cùng nhánh `try`) **không bao giờ chạy được** — component bị kẹt vĩnh viễn ở trạng thái "Đang tải...", dù thực chất đã lỗi từ lâu. Người dùng thấy loading không bao giờ kết thúc, không có cách nào biết đã xảy ra lỗi.
- **Không có `catch` nào cả** (bỏ hẳn `try/catch`): nếu API gọi thất bại (mất mạng, CORS, timeout), exception ném ra từ `OnInitializedAsync` không được xử lý — Blazor WASM log lỗi ra console browser nhưng **UI không hiển thị gì cho người dùng biết có lỗi**, và tuỳ phiên bản, có thể để trang ở trạng thái nửa-render (một số phần tử hiện, một số không), gây trải nghiệm khó hiểu.

---

## 6. Không bao giờ gọi API ngay trong phần render — chỉ gọi trong `OnInitializedAsync`/event handler

Điểm cuối cùng, dễ mắc phải khi mới quen `@code`/markup Razor lồng nhau: đường ranh giới giữa "gọi API ở đâu là đúng" và "gọi API ở đâu là sai" trong một component.

Ví dụ minh hoạ đúng vấn đề — gọi API **trực tiếp trong markup** (phần render), không phải trong `OnInitializedAsync`:

```razor title="DanhSachSanPhamSai.razor (SAI - goi API ngay trong render)"
@page "/san-pham-sai"
@inject HttpClient Http

<ul>
    @* SAI: Http.GetFromJsonAsync duoc goi moi lan Blazor render lai component nay *@
    @foreach (var sp in await Http.GetFromJsonAsync<List<SanPham>>("api/products") ?? new())
    {
        <li>@sp.Ten</li>
    }
</ul>

@code {
    private sealed class SanPham
    {
        public int Id { get; set; }
        public string Ten { get; set; } = "";
    }
}
```

Đoạn này thực ra **không biên dịch được** ở dạng này — cú pháp Razor không cho phép `await` trực tiếp trong markup như trên (đây là lỗi build cụ thể, không phải hành vi runtime sai). Nhưng cùng ý tưởng sai này thường len vào dưới một dạng biên dịch được, khó nhận ra hơn — gọi API bên trong một **property/method không async** được markup gọi lại mỗi lần render:

```razor title="DanhSachSanPhamSai2.razor (SAI - goi qua property duoc goi moi lan render)"
@page "/san-pham-sai-2"
@inject HttpClient Http

<ul>
    @foreach (var ten in LayTenSanPham())
    {
        <li>@ten</li>
    }
</ul>

@code {
    // SAI: LayTenSanPham() nam trong markup, nen chay LAI mot Blazor
    // re-render component nay - vi du sau moi lan StateHasChanged() tu bat ky nguon nao.
    private List<string> LayTenSanPham()
    {
        var response = Http.GetAsync("api/products").GetAwaiter().GetResult(); // block thread!
        var sanPhams = response.Content.ReadFromJsonAsync<List<SanPham>>()
            .GetAwaiter().GetResult() ?? new();
        return sanPhams.ConvertAll(sp => sp.Ten);
    }

    private sealed class SanPham
    {
        public int Id { get; set; }
        public string Ten { get; set; } = "";
    }
}
```

**Điều gì xảy ra khi dùng sai:** `LayTenSanPham()` được gọi lại **mỗi lần Blazor render component này** — không chỉ một lần lúc trang mở, mà mỗi khi bất kỳ điều gì kích hoạt `StateHasChanged()` (người dùng gõ vào một ô input khác trên cùng trang, một timer, một event không liên quan). Mỗi lần đó, một request HTTP **mới** được gửi tới backend — với danh sách sản phẩm, người dùng gõ vài chữ vào một ô tìm kiếm trên cùng trang có thể vô tình kích hoạt **hàng chục request trùng lặp** tới API trong vài giây, gây tải không cần thiết lên backend và UI giật do mỗi request chặn luồng (`GetAwaiter().GetResult()` block thread UI của WASM — vốn chỉ có một luồng, gây toàn bộ trang đứng hình trong lúc chờ response).

Cách đúng — như mục 4-5 đã làm: gọi API **đúng một lần** trong lifecycle method `OnInitializedAsync()` (chạy một lần khi component khởi tạo, đã học ở chương lifecycle) hoặc trong một **event handler** (như `@onclick`, chỉ chạy khi người dùng chủ động bấm) — không bao giờ đặt lời gọi API trực tiếp trong một biểu thức/method được markup (`@foreach`, `@if`, hoặc bất kỳ chỗ nào trong phần HTML của `.razor`) gọi tới, vì phần đó chạy lại theo lịch render của Blazor, không theo ý định của bạn.

!!! danger "Dấu hiệu nhận biết: method gọi API nhưng KHÔNG async, được gọi từ markup"
    Nếu bạn thấy một method không trả `Task`/không có `async`, được gọi trực tiếp trong `@foreach`/`@if`/biểu thức markup, và bên trong nó có `.Result`, `.GetAwaiter().GetResult()`, hoặc bất kỳ cách "block" một Task bất đồng bộ thành đồng bộ — đây gần như luôn là dấu hiệu của lỗi gọi API trong render. Cách sửa đúng: chuyển lời gọi API vào `OnInitializedAsync()`, lưu kết quả vào một field (như `sanPhams` ở mục 4-5), và để markup chỉ **đọc** field đó, không tự gọi API.

---

## 6b. Gọi API lại theo hành động người dùng — event handler, không phải render

Mục 6 đã nói event handler (như `@onclick`) là nơi **đúng thứ hai** để gọi API, ngoài `OnInitializedAsync()`. Đây là tình huống rất thường gặp: một nút "Tải lại" hoặc "Tìm kiếm" cần gọi lại API theo đúng lúc người dùng bấm — không phải lúc component khởi tạo, và tuyệt đối không phải lúc render như mục 6 vừa cảnh báo.

Ví dụ tối thiểu — mở rộng đúng component mục 5, thêm một nút "Tải lại" gọi lại API qua event handler, dùng lại **cùng logic** đã viết trong `OnInitializedAsync()` bằng cách tách ra một method riêng:

```razor title="DanhSachSanPham.razor (them nut Tai lai qua event handler)"
@page "/san-pham"
@inject HttpClient Http

@if (isLoading)
{
    <p>Đang tải...</p>
}
else if (thongBaoLoi is not null)
{
    <p style="color:red">Lỗi: @thongBaoLoi</p>
    <button @onclick="TaiDuLieu">Tải lại</button>
}
else
{
    <ul>
        @foreach (var sp in sanPhams)
        {
            <li>@sp.Ten</li>
        }
    </ul>
    <button @onclick="TaiDuLieu">Tải lại</button>
}

@code {
    private List<SanPham> sanPhams = new();
    private bool isLoading = true;
    private string? thongBaoLoi;

    // OnInitializedAsync chi GOI method nay - khong tu viet lai logic o day.
    protected override async Task OnInitializedAsync() => await TaiDuLieu();

    // Method nay duoc goi TU HAI noi: (1) mot lan luc khoi tao, (2) moi lan
    // nguoi dung bam nut "Tai lai" qua @onclick - CA HAI deu la noi HOP LE
    // theo muc 6, khong phai goi tu markup/@foreach/@if.
    private async Task TaiDuLieu()
    {
        isLoading = true;
        thongBaoLoi = null;

        try
        {
            var response = await Http.GetAsync("api/products");

            if (!response.IsSuccessStatusCode)
            {
                thongBaoLoi = $"API trả về {(int)response.StatusCode}.";
                return;
            }

            sanPhams = await response.Content.ReadFromJsonAsync<List<SanPham>>() ?? new();
        }
        catch (HttpRequestException)
        {
            thongBaoLoi = "Không thể kết nối tới API. Kiểm tra CORS hoặc backend có đang chạy không.";
        }
        finally
        {
            isLoading = false;
        }
    }

    private sealed class SanPham
    {
        public int Id { get; set; }
        public string Ten { get; set; } = "";
    }
}
```

Điểm mấu chốt: `TaiDuLieu()` đặt lại `isLoading = true` và `thongBaoLoi = null` **ở đầu** method, mỗi lần được gọi — kể cả khi gọi lại từ nút "Tải lại" sau khi đã lỗi lần trước. Nếu thiếu bước reset này, bấm "Tải lại" sau một lần lỗi sẽ giữ nguyên `thongBaoLoi` cũ (thông báo lỗi vẫn hiện) cho tới khi request mới hoàn tất — không sai nghiêm trọng, nhưng gây khó hiểu nếu request mới cũng đang chạy mà UI vẫn hiện lỗi cũ như thể chưa thử lại.

**Điều gì xảy ra khi dùng sai:** nếu bạn viết `@onclick="async () => sanPhams = await Http.GetFromJsonAsync<List<SanPham>>(\"api/products\")"` trực tiếp trong markup (không tách thành method riêng, không có `isLoading`/`try-catch`), nút bấm vẫn "chạy được" khi mạng ổn định, nhưng mất hoàn toàn khả năng xử lý lỗi — nếu API lỗi giữa lúc người dùng bấm, exception ném ra từ lambda ẩn danh trong `@onclick` không có `catch` nào bắt, biến `isLoading` không tồn tại nên không có phản hồi "đang tải" nào cho người dùng biết nút đã được bấm nhận, dễ khiến người dùng bấm lại nhiều lần liên tiếp tưởng nút "không phản hồi" — gây gọi API trùng lặp không kiểm soát.

!!! note "Vì sao gọi API trong event handler KHÔNG vi phạm quy tắc mục 6"
    Quy tắc mục 6 cấm gọi API trong phần code **được markup tự động gọi lại theo lịch render** (`@foreach`, `@if`, hoặc property/method nằm trong luồng render). `@onclick="TaiDuLieu"` khác hẳn về bản chất: Blazor chỉ gọi `TaiDuLieu()` đúng **một lần cho mỗi lần người dùng bấm** — đây là một sự kiện rời rạc, có chủ đích, không phải một phần của quá trình tính toán render. Cùng một method `TaiDuLieu()` vừa hợp lệ khi gọi từ `OnInitializedAsync()` (mục 4-5), vừa hợp lệ khi gọi từ `@onclick` (mục này) — điều **không** hợp lệ là đặt lời gọi API ngay trong biểu thức `@foreach(...)`/`@if(...)` như mục 6 đã minh hoạ.

---

## Cạm bẫy & thực chiến

- **Không mở tab Console (F12) khi component không nhận được dữ liệu:** lỗi CORS (mục 2) chỉ hiện chữ "CORS policy" trong console browser, không xuất hiện trong exception .NET — luôn kiểm tra console trước khi nghi ngờ sai hướng (URL, backend chưa chạy).
- **Gọi `app.UseCors(...)` sau khi map endpoint, hoặc quên gọi hoàn toàn:** policy CORS được khai báo nhưng không áp dụng — thứ tự middleware trong `Program.cs` (backend) quan trọng, `UseCors` phải đứng trước các lời gọi map endpoint cần áp dụng.
- **Dùng `AllowAnyOrigin()` để "cho nhanh hết lỗi" rồi quên đổi lại khi lên production:** mở API cho mọi origin gọi được, rủi ro bảo mật thật với API có thao tác ghi dữ liệu — luôn khai báo đúng origin cụ thể (`WithOrigins`) ngoài môi trường phát triển cục bộ.
- **Đặt `isLoading = false` trong nhánh `try` (không dùng `finally`):** nếu exception xảy ra, `isLoading` không bao giờ về `false` — UI kẹt ở "Đang tải..." vĩnh viễn dù đã lỗi từ lâu.
- **Gọi API trong một method/property được `@foreach`/`@if` gọi lại trong markup:** method đó chạy lại mỗi lần Blazor render component, gây request trùng lặp không kiểm soát và có thể block thread UI nếu dùng `.GetAwaiter().GetResult()` thay vì `await` đúng cách — luôn gọi API trong `OnInitializedAsync()` hoặc event handler, lưu kết quả vào field, để markup chỉ đọc field đó.
- **Viết logic gọi API + xử lý lỗi trực tiếp trong lambda ẩn danh của `@onclick`, không tách thành method riêng:** khó thêm `isLoading`/`try-catch` gọn gàng (mục 6b), và nếu cần gọi lại cùng logic từ `OnInitializedAsync()` (tải lần đầu) lẫn từ nút bấm (tải lại), bạn phải chép logic hai lần thay vì gọi lại một method chung — dễ để hai nơi lệch nhau khi sửa lỗi sau này.
- **Quên reset `thongBaoLoi = null` (hoặc trạng thái lỗi cũ) ở đầu method gọi lại khi người dùng bấm "Tải lại":** nếu request mới đang chạy nhưng UI vẫn hiện thông báo lỗi của lần gọi trước, người dùng dễ hiểu lầm là nút "Tải lại" không hoạt động, dù thực chất request mới đang chạy bình thường phía sau.

---

## Bài tập

**Bài 1 (giàn giáo):** Đoạn code sau gọi API lấy danh sách đơn hàng nhưng không có `isLoading`/xử lý lỗi. Sửa lại theo pattern mục 5: thêm `isLoading`, hiện "Đang tải..." khi đang chờ, và hiện thông báo lỗi nếu `GetAsync` thất bại hoặc status không thành công.

```razor title="DonHangList.razor (chua co isLoading/loi)"
@page "/don-hang"
@inject HttpClient Http

<ul>
    @foreach (var dh in donHangs)
    {
        <li>@dh.MaDon</li>
    }
</ul>

@code {
    private List<DonHang> donHangs = new();

    protected override async Task OnInitializedAsync()
    {
        donHangs = await Http.GetFromJsonAsync<List<DonHang>>("api/orders") ?? new();
    }

    private sealed class DonHang
    {
        public string MaDon { get; set; } = "";
    }
}
```

??? success "Lời giải + vì sao"
    ```razor title="DonHangList.razor (da sua)"
    @page "/don-hang"
    @inject HttpClient Http

    @if (isLoading)
    {
        <p>Đang tải...</p>
    }
    else if (thongBaoLoi is not null)
    {
        <p style="color:red">Lỗi: @thongBaoLoi</p>
    }
    else
    {
        <ul>
            @foreach (var dh in donHangs)
            {
                <li>@dh.MaDon</li>
            }
        </ul>
    }

    @code {
        private List<DonHang> donHangs = new();
        private bool isLoading = true;
        private string? thongBaoLoi;

        protected override async Task OnInitializedAsync()
        {
            try
            {
                var response = await Http.GetAsync("api/orders");

                if (!response.IsSuccessStatusCode)
                {
                    thongBaoLoi = $"API trả về {(int)response.StatusCode}.";
                    return;
                }

                donHangs = await response.Content.ReadFromJsonAsync<List<DonHang>>() ?? new();
            }
            catch (HttpRequestException)
            {
                thongBaoLoi = "Không thể kết nối tới API đơn hàng.";
            }
            finally
            {
                isLoading = false;
            }
        }

        private sealed class DonHang
        {
            public string MaDon { get; set; } = "";
        }
    }
    ```

    **Vì sao đúng:** `isLoading` khởi tạo `true` (đang tải ngay từ đầu), chỉ chuyển `false` trong `finally` — đảm bảo về `false` dù thành công hay lỗi (không kẹt "Đang tải..." vĩnh viễn). `try/catch (HttpRequestException)` bắt đúng lỗi mạng/CORS, `IsSuccessStatusCode` kiểm tra trước khi tin tưởng đọc JSON — cả hai đúng pattern đã học ở mục 5 và ở chương gọi API bên ngoài của backend.

**Bài 2 (tìm lỗi CORS + sửa cấu hình):** Một đồng nghiệp báo bug: component Blazor WASM (chạy ở `https://localhost:5002`) gọi API backend (`https://localhost:5001/api/customers`) và nhận toàn danh sách trống, dù test bằng Postman thấy API trả JSON đầy đủ. Console browser hiện dòng chữ có "CORS policy". Đồng nghiệp đã có đoạn `Program.cs` backend sau — tìm lỗi cấu hình CORS cụ thể và sửa lại.

```csharp title="Program.cs (backend - co loi CORS)"
// test:compile bai 2 - co loi thu tu middleware, tim va sua
var builder = WebApplication.CreateBuilder(args);

builder.Services.AddCors(options =>
{
    options.AddPolicy("ChoPhepBlazorWasm", policy =>
    {
        policy.WithOrigins("https://localhost:5002")
              .AllowAnyMethod()
              .AllowAnyHeader();
    });
});

var app = builder.Build();

app.MapGet("/api/customers", () => new[] { new { Id = 1, Ten = "Khach A" } });

// UseCors dat SAI vi tri - o day, SAU khi da MapGet.
app.UseCors("ChoPhepBlazorWasm");

app.Run();
```

??? success "Lời giải + vì sao"
    **Lỗi:** `app.UseCors("ChoPhepBlazorWasm")` được gọi **sau** `app.MapGet(...)`. Middleware trong ASP.NET Core chạy theo đúng thứ tự khai báo — endpoint `/api/customers` đã được map và xử lý request **trước khi** middleware CORS có cơ hội thêm header `Access-Control-Allow-Origin` vào response, nên browser vẫn chặn response dù policy đã được đăng ký đúng nội dung (đúng origin `:5002`, đúng tên policy dùng lại).

    ```csharp title="Program.cs (backend - da sua thu tu)"
    // test:compile bai 2 da sua - UseCors dat truoc MapGet
    var builder = WebApplication.CreateBuilder(args);

    builder.Services.AddCors(options =>
    {
        options.AddPolicy("ChoPhepBlazorWasm", policy =>
        {
            policy.WithOrigins("https://localhost:5002")
                  .AllowAnyMethod()
                  .AllowAnyHeader();
        });
    });

    var app = builder.Build();

    // UseCors PHAI dat truoc MapGet/cac lenh map endpoint can ap dung CORS.
    app.UseCors("ChoPhepBlazorWasm");

    app.MapGet("/api/customers", () => new[] { new { Id = 1, Ten = "Khach A" } });

    app.Run();
    ```

    **Vì sao đúng:** đặt `app.UseCors(...)` trước `app.MapGet(...)` đảm bảo middleware CORS xử lý và gắn đúng header `Access-Control-Allow-Origin: https://localhost:5002` vào response **trước khi** response được trả về browser — browser thấy header khớp với origin đang gọi (`:5002`) nên cho phép code Blazor WASM đọc dữ liệu, không còn chặn nữa.

**Bài 3 (tìm lỗi trong component — vi phạm quy tắc mục 6):** Component sau hiển thị số lượng tồn kho của một sản phẩm, cập nhật lại **mỗi khi** người dùng gõ vào một ô tìm kiếm không liên quan (`tuKhoa`) trên cùng trang. Tìm chỗ vi phạm quy tắc "không gọi API trong render", giải thích hậu quả cụ thể quan sát được, và sửa lại.

```razor title="TonKho.razor (co loi - vi pham quy tac muc 6)"
@page "/ton-kho"
@inject HttpClient Http

<input @bind="tuKhoa" @bind:event="oninput" placeholder="Tìm sản phẩm khác..." />

<p>Tồn kho sản phẩm SKU-1: @LaySoLuongTonKho() cái</p>

@code {
    private string tuKhoa = "";

    private int LaySoLuongTonKho()
    {
        var response = Http.GetAsync("api/inventory/SKU-1").GetAwaiter().GetResult();
        var ketQua = response.Content.ReadFromJsonAsync<TonKhoResponse>()
            .GetAwaiter().GetResult();
        return ketQua?.SoLuong ?? 0;
    }

    private sealed class TonKhoResponse
    {
        public int SoLuong { get; set; }
    }
}
```

??? success "Lời giải + vì sao"
    **Lỗi:** `LaySoLuongTonKho()` được gọi trực tiếp trong markup (`<p>Tồn kho sản phẩm SKU-1: @LaySoLuongTonKho() cái</p>`) — đúng loại vi phạm mục 6. Vì `@bind:event="oninput"` khiến `tuKhoa` cập nhật và kích hoạt `StateHasChanged()` (re-render) **mỗi ký tự** người dùng gõ vào ô tìm kiếm, và ô tìm kiếm này **không hề liên quan** tới tồn kho SKU-1, mỗi lần gõ một chữ sẽ khiến `LaySoLuongTonKho()` chạy lại — gửi một request `GetAsync` **mới** tới backend, đồng thời `.GetAwaiter().GetResult()` block luồng UI (WASM chỉ có một luồng), khiến cả trang bị "đứng" một khoảng ngắn mỗi lần gõ một ký tự.

    **Hậu quả quan sát được cụ thể:** gõ một từ khoá 10 ký tự vào ô tìm kiếm tạo ra 10 request `GET /api/inventory/SKU-1` liên tiếp tới backend (xem tab Network của DevTools), và người dùng cảm nhận rõ độ giật/lag khi gõ, dù họ chỉ đang tìm một sản phẩm khác, không hề tương tác gì với phần tồn kho SKU-1.

    **Sửa lại — tải tồn kho một lần trong `OnInitializedAsync()`, lưu vào field, markup chỉ đọc field:**

    ```razor title="TonKho.razor (da sua)"
    @page "/ton-kho"
    @inject HttpClient Http

    <input @bind="tuKhoa" @bind:event="oninput" placeholder="Tìm sản phẩm khác..." />

    <p>Tồn kho sản phẩm SKU-1: @soLuongTonKho cái</p>

    @code {
        private string tuKhoa = "";
        private int soLuongTonKho;

        protected override async Task OnInitializedAsync()
        {
            var response = await Http.GetAsync("api/inventory/SKU-1");
            if (response.IsSuccessStatusCode)
            {
                var ketQua = await response.Content.ReadFromJsonAsync<TonKhoResponse>();
                soLuongTonKho = ketQua?.SoLuong ?? 0;
            }
        }

        private sealed class TonKhoResponse
        {
            public int SoLuong { get; set; }
        }
    }
    ```

    **Vì sao đúng:** `OnInitializedAsync()` chỉ chạy **đúng một lần** khi component khởi tạo (đã học ở chương lifecycle), không chạy lại khi `tuKhoa` đổi — gọi API đúng một lần, lưu kết quả vào field `soLuongTonKho`, và markup chỉ **đọc** field này (`@soLuongTonKho`), không tự gọi lại API. Gõ vào ô tìm kiếm vẫn kích hoạt re-render (để hiển thị `tuKhoa` mới), nhưng lần re-render đó chỉ đọc lại field có sẵn trong bộ nhớ — không gửi request nào, không block thread nào.

---

## Tự kiểm tra

1. Vì sao code `HttpClient` trong Blazor WASM dùng lại đúng các API (`GetFromJsonAsync`, `PostAsJsonAsync`, `IsSuccessStatusCode`) đã học ở phần gọi API backend, không có method mới nào?

    ??? note "Đáp án"
        `HttpClient` và các extension method của nó là một phần của .NET, không phụ thuộc việc code chạy trên server hay trong browser qua WASM. Sự khác biệt duy nhất là **nơi thực thi** — Blazor WASM chạy trong browser nên bị chi phối bởi luật bảo mật của browser (như CORS), còn backend chạy trên server không bị luật này chi phối.

2. CORS là luật của ai — .NET, backend, hay browser? Nó chặn điều gì cụ thể?

    ??? note "Đáp án"
        CORS là luật của **browser**. Nó chặn không cho code JavaScript/WASM đang chạy ở một origin đọc response từ một request gửi tới origin khác, trừ khi server đích trả về header `Access-Control-Allow-Origin` cho phép rõ ràng origin đang gọi.

3. Nếu backend chưa cấu hình CORS, lỗi hiện ra ở đâu — trong exception .NET hay trong console browser? Vì sao điều này dễ gây nhầm lẫn khi debug?

    ??? note "Đáp án"
        Chữ "CORS policy" chỉ hiện trong console browser (F12), không xuất hiện trong exception .NET (thường chỉ là `HttpRequestException` chung, không nhắc CORS). Điều này dễ gây nhầm lẫn vì người debug thường chỉ xem log/exception .NET, không nghĩ tới việc mở console browser, dẫn tới nghi sai hướng (URL sai, backend chưa chạy).

4. Hai lỗi cấu hình `AddCors`/`UseCors` phổ biến nhất khiến CORS vẫn bị chặn dù đã "có vẻ" cấu hình?

    ??? note "Đáp án"
        (1) Quên gọi `app.UseCors(...)` — chỉ đăng ký `AddCors` ở `builder.Services` nhưng không áp dụng middleware. (2) Gọi `app.UseCors(...)` **sau** khi đã map endpoint (`app.MapGet(...)` v.v.) — thứ tự middleware sai khiến endpoint xử lý request trước khi CORS gắn header vào response.

5. Dòng `builder.Services.AddScoped(sp => new HttpClient { BaseAddress = ... })` trong `Program.cs` của Blazor WASM dùng để làm gì, và nếu thiếu `BaseAddress` thì lỗi gì xảy ra khi gọi API với đường dẫn tương đối?

    ??? note "Đáp án"
        Dòng này đăng ký một `HttpClient` có sẵn địa chỉ gốc vào DI container, để component chỉ cần `@inject HttpClient Http` và gọi đường dẫn tương đối. Nếu thiếu `BaseAddress`, gọi với đường dẫn tương đối ném `InvalidOperationException: ... BaseAddress must be set` — giống lỗi đã học ở chương gọi API backend khi dùng named client sai tên.

6. Vì sao đặt `isLoading = false` trong nhánh `try` (không dùng `finally`) là một lỗi, và hậu quả cụ thể quan sát được là gì?

    ??? note "Đáp án"
        Nếu lời gọi API ném exception, dòng `isLoading = false` (nằm trong `try`, sau lời gọi) không được thực thi vì luồng code đã nhảy sang `catch` trước khi tới được dòng đó. Hậu quả: `isLoading` giữ nguyên `true` vĩnh viễn, UI kẹt ở trạng thái "Đang tải..." dù thực chất đã lỗi từ lâu — `finally` đảm bảo dòng này luôn chạy dù thành công hay lỗi.

7. Vì sao gọi API trực tiếp trong một method được `@foreach`/`@if` trong markup gọi lại là sai, dù đoạn code đó biên dịch được?

    ??? note "Đáp án"
        Blazor render lại phần markup (bao gồm mọi method được gọi trong đó) mỗi khi `StateHasChanged()` được kích hoạt bởi bất kỳ nguyên nhân nào (không chỉ lúc khởi tạo). Method gọi API trong markup sẽ chạy lại mỗi lần đó, gửi request HTTP mới không kiểm soát — gây tải dư thừa lên backend, và nếu dùng cách block đồng bộ (`.GetAwaiter().GetResult()`), còn làm đứng hình cả UI trong lúc chờ.

8. Nơi đúng để gọi API trong một component Blazor là gì, theo mục 6?

    ??? note "Đáp án"
        Trong lifecycle method `OnInitializedAsync()` (chạy đúng một lần khi component khởi tạo) hoặc trong một event handler (như `@onclick`, chỉ chạy khi người dùng chủ động kích hoạt) — kết quả lưu vào một field, và markup chỉ đọc field đó, không tự gọi API.

9. Ở mục 6b, method `TaiDuLieu()` được gọi từ hai nơi khác nhau. Đó là hai nơi nào, và vì sao cả hai đều hợp lệ theo quy tắc mục 6?

    ??? note "Đáp án"
        Hai nơi: (1) `OnInitializedAsync()`, gọi đúng một lần lúc component khởi tạo; (2) `@onclick="TaiDuLieu"` trên nút "Tải lại", gọi đúng một lần mỗi khi người dùng bấm. Cả hai hợp lệ vì đây là những lời gọi **rời rạc, có chủ đích** (một lần khởi tạo, hoặc một lần mỗi sự kiện người dùng) — khác với việc đặt lời gọi API ngay trong `@foreach`/`@if`, nơi Blazor tự động gọi lại theo lịch render, không theo ý định của người viết code.

10. Trong bài tập 3 (component `TonKho`), vì sao gõ vào ô tìm kiếm `tuKhoa` lại kích hoạt gọi API tới `api/inventory/SKU-1`, dù `tuKhoa` không liên quan gì tới tồn kho?

    ??? note "Đáp án"
        Vì `LaySoLuongTonKho()` được gọi trực tiếp trong markup (`@LaySoLuongTonKho()`). Mỗi lần `tuKhoa` đổi (do `@bind:event="oninput"`), Blazor gọi `StateHasChanged()` để re-render component, và việc re-render này chạy lại **toàn bộ** markup — bao gồm cả `LaySoLuongTonKho()`, dù giá trị nó tính ra không phụ thuộc gì vào `tuKhoa`. Đây chính là hệ quả cụ thể của việc gọi API trong render mà mục 6 cảnh báo.

---

??? abstract "DEEP DIVE — nâng cao (ngoài fast path)"
    - **Preflight request (`OPTIONS`) trong CORS:** với các request "không đơn giản" (ví dụ `POST` kèm header `Content-Type: application/json`, đúng như `PostAsJsonAsync` gửi), browser tự động gửi một request `OPTIONS` "dò hỏi" trước (preflight) tới server đích, hỏi xem origin/method/header này có được phép không, **trước khi** gửi request thật. Nếu bạn thấy hai request trong tab Network (một `OPTIONS`, một `POST`) cho một lời gọi `PostAsJsonAsync`, đây là hành vi preflight bình thường của CORS, không phải lỗi — nhưng nếu backend không xử lý đúng `OPTIONS` (một số middleware tuỳ biến chặn nhầm), preflight thất bại và request thật không bao giờ được gửi. Preflight chỉ xảy ra với các "non-simple request" — `GET`/`HEAD`/`POST` với `Content-Type` thuộc nhóm `text/plain`, `multipart/form-data`, `application/x-www-form-urlencoded` được coi là "simple", không cần preflight; còn `application/json` (loại `PostAsJsonAsync` luôn dùng) và các method như `PUT`/`DELETE`/`PATCH` luôn kích hoạt preflight.
    - **CORS với credentials (cookie, `Authorization` header):** mặc định, request kèm cookie hoặc `Authorization` header cần cấu hình thêm `policy.AllowCredentials()` ở backend **và** `HttpClient` phía Blazor phải bật tương ứng — kết hợp với `AllowAnyOrigin()` sẽ **không hoạt động** (browser cấm kết hợp "cho phép mọi origin" với "cho phép gửi credentials" vì lý do bảo mật), buộc phải khai báo origin cụ thể qua `WithOrigins` khi cần credentials. Đây chính là tình huống sẽ gặp ở chương JWT authentication kế tiếp — token thường gửi qua `Authorization: Bearer ...` header, không phải cookie, nên không cần `AllowCredentials()` trong trường hợp phổ biến đó, nhưng vẫn cần `AllowAnyHeader()` để browser cho phép header `Authorization` đi qua preflight.
    - **`BaseAddress` từ chính origin của Blazor WASM (`builder.HostEnvironment.BaseAddress`):** khi backend và frontend Blazor WASM được host **cùng một origin** (ví dụ ASP.NET Core serve luôn file tĩnh của Blazor WASM qua `app.UseBlazorFrameworkFiles()`/`app.MapFallbackToFile("index.html")`), bạn có thể dùng `builder.HostEnvironment.BaseAddress` làm `BaseAddress` cho `HttpClient` — trường hợp này không gặp lỗi CORS ở mục 2 vì không còn "cross-origin" nữa (cùng origin, browser không áp dụng luật CORS). Đây là lý do một số project mẫu Blazor WASM "ASP.NET Core Hosted" (cũ, trước .NET 8) không hề gặp lỗi CORS trong lúc phát triển — cả hai phần chạy dưới cùng một origin ngay từ đầu, khác với thiết lập hai project độc lập ở hai cổng như ví dụ mục 0-4 của chương này.
    - **`CancellationToken` khi component bị huỷ giữa lúc đang gọi API:** nếu người dùng điều hướng rời trang trong lúc `OnInitializedAsync()` đang chờ `await Http.GetAsync(...)`, request vẫn tiếp tục chạy tới khi hoàn tất, dù component đã bị Blazor loại khỏi cây UI — kết quả trả về (nếu gọi `StateHasChanged()`) có thể ném lỗi hoặc bị bỏ qua tuỳ phiên bản. Với các lời gọi API có thể chạy lâu, cân nhắc lưu một `CancellationTokenSource`, gọi `.Cancel()` trong `Dispose()` (đã học ở chương state management — component gọi API cũng nên `@implements IDisposable` nếu request có thể kéo dài), và truyền `cts.Token` vào overload của `GetAsync`/`GetFromJsonAsync` nhận `CancellationToken`.
    - **Cache response phía Blazor WASM để tránh gọi lại API không cần thiết:** nếu nhiều component khác nhau đều cần cùng một dữ liệu (ví dụ danh sách danh mục sản phẩm, ít đổi trong một phiên), gọi API riêng ở mỗi component gây lãng phí — đây chính là lúc kết hợp với state container service đã học ở chương trước: service gọi API **một lần**, cache kết quả trong field của service, các component khác chỉ đọc lại từ service (không tự gọi API), tương tự cách `CartState` quản lý giỏ hàng nhưng áp dụng cho dữ liệu lấy từ API thay vì dữ liệu người dùng nhập.
    - **Thư viện gọi API nâng cao (Refit, client sinh tự động từ OpenAPI):** với ứng dụng lớn, viết tay từng `GetFromJsonAsync`/`PostAsJsonAsync` cho mỗi endpoint dễ trùng lặp code (mỗi endpoint lặp lại logic try-catch, kiểm tra status). Các thư viện như Refit (định nghĩa API qua interface + attribute, tự sinh code gọi HTTP) hoặc client sinh tự động từ file OpenAPI/Swagger của backend (qua NSwag, Kiota) giúp giảm code lặp và giữ đồng bộ khi API đổi (đổi route/tham số ở backend, client tự sinh lại khớp theo) — đây là bước nâng cao chỉ đáng đầu tư khi số lượng endpoint gọi tay đã đủ nhiều để việc trùng lặp trở thành gánh nặng bảo trì thật sự, sau khi đã thành thục cách gọi thủ công như chương này.

Tiếp theo -> jwt authentication trong blazor wasm
