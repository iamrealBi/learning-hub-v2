---
tier: core
status: core
owner: core-team
verified_on: "2026-07-05"
dotnet_version: "10.0"
bloom: áp dụng
requires: [p7-httpclient, p4-jwt]
est_minutes_fast: 30
---

# Authentication trong Blazor: lưu JWT & bảo vệ Route

!!! info "Bạn đang ở đây"
    cần trước: JWT là gì và server cấp/kiểm token ra sao (P4), gọi API bằng `HttpClient` từ component Blazor.
    mở khoá: lưu token JWT lại giữa các lần tải trang trong Blazor WebAssembly, cho Blazor biết "ai đang đăng nhập" qua `AuthenticationStateProvider`, hiển thị UI khác nhau tuỳ trạng thái đăng nhập bằng `AuthorizeView`, và chặn truy cập cả trang bằng `[Authorize]`.

> Mục tiêu (đo được): sau chương này bạn **giải thích** được vì sao Blazor WebAssembly cần một nơi lưu token riêng (khác với server lưu session), **viết** được một `AuthenticationStateProvider` tối thiểu đọc token đã lưu và giải mã claim, **áp dụng** được `<AuthorizeView>` để hiện UI khác nhau theo trạng thái đăng nhập, **áp dụng** được `[Authorize]` để chặn truy cập một trang chưa đăng nhập, và **thực hiện** đúng luồng đăng xuất gồm xoá token và báo lại cho toàn cây component.

---

## 0. Đoán nhanh trước khi học

Bạn vừa học xong P4: server cấp một JWT sau khi người dùng đăng nhập đúng mật khẩu, và mọi request API sau đó gắn JWT vào header `Authorization: Bearer ...` để server kiểm.

Giờ hình dung: người dùng đăng nhập thành công trên một trang Blazor WebAssembly, nhận về JWT. Họ **nhấn F5** (tải lại trang) hoặc đóng tab rồi mở lại.

??? question "Câu hỏi: JWT đó còn không sau khi tải lại trang? Vì sao?"
    **Không, nếu bạn chỉ giữ JWT trong một biến C# thường** (ví dụ `private string? _token;` trong một service hoặc component). Blazor WebAssembly chạy hoàn toàn trong trình duyệt qua WASM runtime — khi người dùng tải lại trang, **toàn bộ chương trình .NET trong bộ nhớ trình duyệt bị xoá và khởi động lại từ đầu**, giống việc tắt và mở lại một ứng dụng desktop. Bất kỳ biến C# nào chỉ sống trong bộ nhớ (RAM) của lần chạy đó sẽ mất theo, kể cả JWT vừa nhận được.

    Vấn đề cụ thể: người dùng vừa đăng nhập xong, nhấn F5, bị đẩy về trạng thái "chưa đăng nhập" — dù JWT còn hạn (`exp` chưa hết), không có gì sai với token, chỉ là **chương trình không còn giữ nó nữa**. Mục 1 giải quyết đúng vấn đề này: cần một nơi lưu token **sống sót qua việc tải lại trang**, khác với bộ nhớ RAM của chương trình .NET.

---

## 1. Lưu JWT trong Blazor WebAssembly — vì sao cần `localStorage`

**Định nghĩa (một câu):** `localStorage` là một vùng lưu trữ **của trình duyệt** (không phải của chương trình .NET) gắn với từng domain, dữ liệu ghi vào đó **tồn tại qua việc tải lại trang, đóng tab, hoặc tắt trình duyệt** — Blazor WebAssembly gọi được `localStorage` thông qua **JS Interop** (`IJSRuntime`), vì `localStorage` là một API của JavaScript/trình duyệt, không phải API có sẵn trong .NET.

Trước khi xem code, cần phân biệt rõ hai thứ hay bị nhầm:

| | Biến C# thường (`private string? _token`) | `localStorage` |
|---|---|---|
| Sống ở đâu | Bộ nhớ (heap) của chương trình .NET đang chạy trong WASM | Bộ nhớ của **trình duyệt**, gắn với domain, ngoài vòng đời chương trình .NET |
| Sống sót qua F5 (tải lại trang)? | Không — mất hoàn toàn | Có — còn nguyên sau khi tải lại |
| Ai đọc/ghi được | Chỉ code C# trong process đó | JavaScript trực tiếp, hoặc C# qua JS Interop (`IJSRuntime`) |
| Dùng cho | State tạm trong một lần dùng (một lượt nhập form...) | Dữ liệu cần nhớ **giữa các lần** người dùng mở lại trang (JWT, tuỳ chọn giao diện...) |

Vì `localStorage` chỉ là API của JavaScript, C# muốn dùng phải gọi qua `IJSRuntime` — "cầu nối" cho C# gọi hàm JavaScript và nhận kết quả về (khái niệm JS Interop). Ví dụ tối thiểu, độc lập — một service C# bọc quanh `localStorage` bằng JS Interop:

```razor title="LuuTruTokenDemo.razor"
@page "/demo-luu-token"
@inject IJSRuntime JS

<button @onclick="Luu">Lưu token giả</button>
<button @onclick="Doc">Đọc lại token</button>
<p>Token hiện tại: @tokenDaDoc</p>

@code {
    private string tokenDaDoc = "(chưa đọc)";

    private async Task Luu()
    {
        // InvokeVoidAsync: gọi một hàm JavaScript KHÔNG cần giá trị trả về.
        // "localStorage.setItem" là hàm JavaScript có sẵn của trình duyệt.
        await JS.InvokeVoidAsync("localStorage.setItem", "jwt", "token-gia-abc123");
    }

    private async Task Doc()
    {
        // InvokeAsync<string?>: gọi hàm JavaScript CÓ giá trị trả về,
        // kiểu trả về khai báo trong <T> (ở đây là string?, vì key có thể chưa tồn tại).
        tokenDaDoc = await JS.InvokeAsync<string?>("localStorage.getItem", "jwt") ?? "(không có)";
    }
}
```

Điểm mấu chốt: `InvokeVoidAsync` dùng khi hàm JavaScript không trả về gì bạn cần dùng lại (ví dụ `setItem`), `InvokeAsync<T>` dùng khi cần nhận kết quả về C# (ví dụ `getItem` trả về `string?`). Tên hàm (`"localStorage.setItem"`) là một **chuỗi** — Blazor không kiểm được tên này lúc biên dịch, vì nó chỉ là JavaScript được gọi lúc chạy.

```csharp title="TokenLuuTru.cs (minh hoa - can du an Blazor WASM thuc te)"
// test:skip can du an Blazor WASM rieng (dotnet new blazorwasm), khong compile trong dotnet new web
// (Minh hoa cach dong goi JS Interop vao mot service C# thuong, thay vi
// goi IJSRuntime rai rac trong tung component - de doi mot noi khi doi cach luu tru.)
public sealed class TokenLuuTru
{
    private readonly IJSRuntime _js;
    private const string Key = "jwt";

    public TokenLuuTru(IJSRuntime js) => _js = js;

    public async Task<string?> DocTokenAsync()
        => await _js.InvokeAsync<string?>("localStorage.getItem", Key);

    public async Task LuuTokenAsync(string token)
        => await _js.InvokeVoidAsync("localStorage.setItem", Key, token);

    public async Task XoaTokenAsync()
        => await _js.InvokeVoidAsync("localStorage.removeItem", Key);
}
```

!!! danger "Điều gì xảy ra khi hiểu sai — tưởng `localStorage` an toàn tuyệt đối cho dữ liệu nhạy cảm"
    `localStorage` không có cơ chế bảo vệ khỏi JavaScript độc hại chạy trên cùng trang (tấn công XSS) — nếu một đoạn script lạ chèn được vào trang (qua lỗ hổng XSS ở nơi khác của ứng dụng), nó đọc được **toàn bộ** `localStorage` của domain đó, bao gồm JWT bạn lưu. Đây không phải lỗi của việc "dùng `localStorage` sai cách" — mà là hạn chế cố hữu của cơ chế lưu trữ này. DEEP DIVE cuối bài nói thêm về `HttpOnly` cookie như một lựa chọn thay thế giảm rủi ro này; trong phạm vi chương này (và phần lớn ứng dụng học tập/demo), `localStorage` qua JS Interop là cách phổ biến nhất để bắt đầu.

!!! note "Blazored.LocalStorage — thư viện đóng gói sẵn thao tác trên"
    Thay vì tự viết JS Interop thủ công như `TokenLuuTru` ở trên, một lựa chọn phổ biến trong ứng dụng thật là cài package NuGet `Blazored.LocalStorage` — thư viện này đã viết sẵn các hàm tương tự (`GetItemAsync<T>`, `SetItemAsync`, `RemoveItemAsync`) với tiện ích thêm (tự serialize/deserialize JSON, không cần bạn tự gọi `InvokeAsync` thủ công). Bản chất bên dưới vẫn là JS Interop gọi `localStorage` giống ví dụ trên — thư viện chỉ giúp code gọn hơn, không thay đổi khái niệm cốt lõi vừa học.

---

## 2. `AuthenticationStateProvider` — lớp trung tâm trả lời "ai đang đăng nhập"

**Định nghĩa (một câu):** `AuthenticationStateProvider` là một lớp trừu tượng (abstract class) có sẵn trong Blazor, đóng vai trò **nguồn sự thật duy nhất** cho câu hỏi "người dùng hiện tại là ai, đã đăng nhập chưa" — mọi component trong cây (qua `<AuthorizeView>`, `[Authorize]`, hoặc tự tiêm) đều hỏi **đúng một nơi này**, và bạn phải **tự kế thừa** nó, override phương thức `GetAuthenticationStateAsync()` để dạy nó cách tìm ra danh tính (ở đây: đọc token đã lưu, giải mã claim).

Trước khi viết code, cần hiểu `AuthenticationState` chứa gì: nó bọc một `ClaimsPrincipal` — một đối tượng .NET chuẩn đại diện "một người dùng và các claim của họ" (tên, vai trò...), **không phụ thuộc riêng vào JWT** — `ClaimsPrincipal` cũng được dùng trong ASP.NET Core MVC, Windows Identity, hay bất kỳ cơ chế xác thực .NET nào khác. Việc của `AuthenticationStateProvider` là: đọc JWT đã lưu → giải mã claim trong payload → dựng một `ClaimsPrincipal` từ các claim đó → trả về bọc trong `AuthenticationState`.

Ví dụ tối thiểu, độc lập — phần **giải mã claim từ JWT** (không cần Blazor thật, chỉ cần hiểu payload JWT là JSON, đúng như đã học ở P4):

```csharp title="GiaiMaJwtDemo.cs"
// test:run
// --- Top-level statement PHẢI đứng trước mọi khai báo class/interface trong file .cs ---
// Payload JWT chỉ là JSON được encode Base64URL (đã học ở chương JWT, P4) - đoạn
// dưới đây mô phỏng ĐÚNG bước "giải mã claim" mà AuthenticationStateProvider
// thật (mục 2b) sẽ làm với token đọc từ localStorage.
string payloadBase64Url = "eyJzdWIiOiJ1c2VyLTQyIiwibmFtZSI6IkxhbiIsInJvbGUiOiJhZG1pbiJ9";

var claims = GiaiMaClaims(payloadBase64Url);

foreach (var kv in claims)
    Console.WriteLine($"{kv.Key} = {kv.Value}");

if (claims["name"] != "Lan") throw new Exception("Test FAIL: claim 'name' sai");
if (claims["role"] != "admin") throw new Exception("Test FAIL: claim 'role' sai");
Console.WriteLine("Test PASS");

static Dictionary<string, string> GiaiMaClaims(string payloadBase64Url)
{
    // Base64URL -> Base64 chuan: thay '-' -> '+', '_' -> '/', them '=' dem cho du 4 ky tu.
    string base64 = payloadBase64Url.Replace('-', '+').Replace('_', '/');
    switch (base64.Length % 4)
    {
        case 2: base64 += "=="; break;
        case 3: base64 += "="; break;
    }

    byte[] bytes = Convert.FromBase64String(base64);
    string json = System.Text.Encoding.UTF8.GetString(bytes);

    var doc = System.Text.Json.JsonDocument.Parse(json);
    var ketQua = new Dictionary<string, string>();
    foreach (var prop in doc.RootElement.EnumerateObject())
        ketQua[prop.Name] = prop.Value.ToString();
    return ketQua;
}
```

```text title="output"
sub = user-42
name = Lan
role = admin
Test PASS
```

!!! warning "`AuthenticationStateProvider` KHÔNG kiểm chữ ký JWT — chỉ đọc claim để hiển thị UI"
    Điểm dễ hiểu nhầm nghiêm trọng: code trên chỉ **giải mã** payload để biết "hiển thị UI ra sao" (tên người dùng, có phải admin để hiện nút admin hay không) — nó **không** kiểm chữ ký (signature), vì phía trình duyệt không có secret key để kiểm (đúng như P4 đã giải thích: chỉ server giữ secret key). Điều này có nghĩa: `AuthenticationStateProvider` ở client **không phải** lớp bảo vệ dữ liệu — nó chỉ quyết định **hiển thị** gì. Bảo vệ **thật** (kiểm chữ ký, từ chối request) luôn phải nằm ở server, thông qua `AddJwtBearer`/`[Authorize]` trên API mà bạn đã học ở P4. `[Authorize]` trên component Blazor (mục 4) chỉ ẩn UI phía trình duyệt — không thay thế được việc server kiểm token trên mọi API endpoint.

### 2b. Tự kế thừa `AuthenticationStateProvider`

Ghép `TokenLuuTru` (mục 1) và cách giải mã claim (trên) vào một `AuthenticationStateProvider` thật:

```csharp title="JwtAuthStateProvider.cs (minh hoa - can du an Blazor WASM thuc te)"
// test:skip can du an Blazor WASM rieng (dotnet new blazorwasm), khong compile trong dotnet new web
// (AuthenticationStateProvider, AuthenticationState, ClaimsPrincipal la kieu cua
// Microsoft.AspNetCore.Components.Authorization / System.Security.Claims - can
// package Blazor WASM day du, khong co san trong "dotnet new web" tran.)
public sealed class JwtAuthStateProvider : AuthenticationStateProvider
{
    private readonly TokenLuuTru _tokenLuuTru;

    public JwtAuthStateProvider(TokenLuuTru tokenLuuTru) => _tokenLuuTru = tokenLuuTru;

    // PHẢI override đúng phương thức này - đây là nơi DUY NHẤT Blazor gọi
    // để hỏi "người dùng hiện tại là ai". Mọi AuthorizeView/[Authorize] trong
    // toàn app đều đi qua đúng method này, không có đường tắt nào khác.
    public override async Task<AuthenticationState> GetAuthenticationStateAsync()
    {
        var token = await _tokenLuuTru.DocTokenAsync();

        if (string.IsNullOrWhiteSpace(token))
        {
            // Chưa có token -> ClaimsPrincipal "rỗng" (không danh tính) ->
            // AuthorizeView sẽ hiểu là "chưa đăng nhập".
            var rong = new ClaimsPrincipal(new ClaimsIdentity());
            return new AuthenticationState(rong);
        }

        var claims = GiaiMaClaimsTuJwt(token);
        // "jwt" ở đây chỉ là TÊN loại xác thực (authenticationType) - báo cho
        // ClaimsIdentity biết "danh tính này ĐÃ được xác thực", không phải
        // rỗng/anonymous. Không liên quan tới việc kiểm chữ ký (xem cảnh báo trên).
        var identity = new ClaimsIdentity(claims, authenticationType: "jwt");
        var user = new ClaimsPrincipal(identity);
        return new AuthenticationState(user);
    }

    private static IEnumerable<Claim> GiaiMaClaimsTuJwt(string jwt)
    {
        var payloadBase64Url = jwt.Split('.')[1]; // JWT = Header.Payload.Signature
        string base64 = payloadBase64Url.Replace('-', '+').Replace('_', '/');
        base64 = base64.PadRight(base64.Length + (4 - base64.Length % 4) % 4, '=');
        var json = System.Text.Encoding.UTF8.GetString(Convert.FromBase64String(base64));
        var doc = System.Text.Json.JsonDocument.Parse(json);

        foreach (var prop in doc.RootElement.EnumerateObject())
            yield return new Claim(prop.Name, prop.Value.ToString());
    }
}
```

Đăng ký vào DI (Program.cs của project Blazor WASM):

```csharp title="Program.cs (trich - dang ky AuthenticationStateProvider)"
// test:skip can du an Blazor WASM rieng (dotnet new blazorwasm), khong compile trong dotnet new web
// AddAuthorizationCore: dang ky dich vu authorization TOI THIEU cho Blazor
// (khac AddAuthorization cua ASP.NET Core MVC/API - Blazor WASM khong co
// pipeline middleware server-side de dung ban day du).
builder.Services.AddAuthorizationCore();
builder.Services.AddScoped<TokenLuuTru>();
// Đăng ký ĐÚNG lớp con (JwtAuthStateProvider) dưới kiểu lớp CHA (AuthenticationStateProvider)
// - đây là điểm mà [Authorize]/AuthorizeView tìm tới khi cần hỏi trạng thái đăng nhập.
builder.Services.AddScoped<AuthenticationStateProvider, JwtAuthStateProvider>();
```

!!! danger "Nếu quên `AddAuthorizationCore()` — lỗi cụ thể lúc chạy"
    Nếu bạn dùng `<AuthorizeView>` hoặc `[Authorize]` (mục 3, 4) mà quên gọi `builder.Services.AddAuthorizationCore()`, ứng dụng sẽ ném exception lúc khởi động dạng "Cannot provide a value for property ... There is no registered service of type Microsoft.AspNetCore.Authorization.IAuthorizationPolicyProvider" — vì `AuthorizeView`/`[Authorize]` cần các dịch vụ authorization nền (policy provider) mà `AddAuthorizationCore()` mới là nơi đăng ký chúng; chỉ đăng ký `AuthenticationStateProvider` riêng lẻ là không đủ.

---

## 3. `<AuthorizeView>` — hiện UI khác nhau tuỳ trạng thái đăng nhập

**Định nghĩa (một câu):** `<AuthorizeView>` là một component có sẵn của Blazor, tự động gọi `GetAuthenticationStateAsync()` (mục 2) và hiển thị **một trong hai** khối nội dung con tương ứng — `<Authorized>` nếu người dùng đã đăng nhập, `<NotAuthorized>` nếu chưa — bạn không tự viết `if/else` kiểm tra trạng thái, `AuthorizeView` tự làm việc đó.

Ví dụ tối thiểu, độc lập:

```razor title="ThanhDangNhap.razor"
<AuthorizeView>
    <Authorized>
        <p>Xin chào, @context.User.Identity?.Name!</p>
        <button @onclick="DangXuat">Đăng xuất</button>
    </Authorized>
    <NotAuthorized>
        <p>Bạn chưa đăng nhập.</p>
        <a href="/dang-nhap">Đăng nhập ngay</a>
    </NotAuthorized>
</AuthorizeView>

@code {
    private void DangXuat()
    {
        // Xem đầy đủ luồng đăng xuất ở mục 5.
    }
}
```

Điểm mấu chốt: bên trong `<Authorized>`, biến ngầm `context` (kiểu `AuthenticationState`) tự có sẵn — không cần bạn khai báo `[CascadingParameter]` hay tự inject gì thêm — `context.User` chính là `ClaimsPrincipal` mà `GetAuthenticationStateAsync()` trả về ở mục 2b. `@context.User.Identity?.Name` đọc claim tên `Name` chuẩn (`ClaimTypes.Name`) — nếu JWT của bạn không có claim tên đúng dạng chuẩn này, giá trị sẽ là `null`, cần map đúng tên claim khi dựng `ClaimsIdentity` (xem "Cạm bẫy" cuối bài).

!!! danger "Nếu quên bọc `<AuthorizeView>` — hoặc gọi sai vị trí — lỗi cụ thể lúc build/chạy"
    Nếu bạn viết `<Authorized>` hoặc `context.User` **ngoài** cặp thẻ `<AuthorizeView>...</AuthorizeView>` (ví dụ quên thẻ mở), Razor sẽ báo lỗi biên dịch dạng "The tag helper 'Authorized' is not valid" hoặc "context does not exist in the current context" — vì `context` chỉ tồn tại **bên trong** phạm vi mà `AuthorizeView` tạo ra (giống biến lặp chỉ tồn tại trong thân `foreach`). Đây là lỗi build rõ ràng, khác với lỗi runtime âm thầm của `[CascadingParameter]` thiếu `CascadingValue` (đã học ở chương state management) — bạn sẽ biết ngay lúc build, không phải đợi tới lúc chạy mới phát hiện.

---

## 4. `[Authorize]` — chặn truy cập cả một trang

**Định nghĩa (một câu):** `[Authorize]` là một attribute đặt trên khai báo `@page` của một component, báo cho Blazor **chặn hiển thị toàn bộ trang** đó nếu người dùng chưa đăng nhập (theo `AuthenticationStateProvider` đang đăng ký) — khác với `<AuthorizeView>` (mục 3) chỉ ẩn/hiện **một phần** UI trong một trang vẫn hiển thị được.

Ví dụ tối thiểu, độc lập — một trang chỉ xem được khi đã đăng nhập:

```razor title="TrangCaNhan.razor"
@page "/ca-nhan"
@attribute [Authorize]

<h3>Thông tin cá nhân</h3>
<p>Chỉ người đã đăng nhập mới thấy được trang này.</p>
```

Để `[Authorize]` thực sự chặn được (thay vì chỉ hiện trang trắng/lỗi), Blazor cần một component bọc quanh `<RouteView>` biết xử lý "trang này bị chặn thì làm gì" — component đó là `<AuthorizeRouteView>`, thường đặt trong `App.razor`:

```razor title="App.razor (trich)"
<Router AppAssembly="@typeof(Program).Assembly">
    <Found Context="routeData">
        <AuthorizeRouteView RouteData="@routeData" DefaultLayout="@typeof(MainLayout)">
            <NotAuthorized>
                <p>Bạn cần đăng nhập để xem trang này.</p>
                <a href="/dang-nhap">Đăng nhập</a>
            </NotAuthorized>
        </AuthorizeRouteView>
    </Found>
    <NotFound>
        <p>Không tìm thấy trang.</p>
    </NotFound>
</Router>
```

`AuthorizeRouteView` đóng vai trò tương tự `AuthorizeView` (mục 3) nhưng ở cấp **toàn trang**: nó tự gọi `GetAuthenticationStateAsync()`, kiểm `[Authorize]` có trên trang đang điều hướng tới hay không, và hiện `<NotAuthorized>` thay cho nội dung trang nếu chưa đăng nhập — bạn không cần tự viết logic kiểm tra này trong từng trang.

!!! danger "Điều gì xảy ra khi hiểu sai — tưởng `[Authorize]` trên component Blazor bảo vệ được API"
    Đây là hiểu sai nghiêm trọng nhất trong chương này: `[Authorize]` trên `TrangCaNhan.razor` chỉ ngăn **hiển thị trang** phía trình duyệt — nếu người dùng (hoặc một script/công cụ như Postman) gọi **trực tiếp** API backend mà trang này lẽ ra gọi (ví dụ `GET /api/ho-so-ca-nhan`) mà **không qua trình duyệt hiển thị trang**, và API đó **không** có `[Authorize]` riêng ở phía server (theo đúng `AddJwtBearer` đã học ở P4), request đó vẫn thành công, trả dữ liệu, dù trang Blazor tương ứng "bị chặn". Vì toàn bộ code Blazor WASM (kể cả logic `[Authorize]`) **chạy trong trình duyệt của người dùng** — người dùng có toàn quyền sửa, bỏ qua, hoặc gọi thẳng API bằng công cụ khác, hoàn toàn không đi qua code Blazor bạn viết. `[Authorize]` phía Blazor chỉ là **trải nghiệm người dùng tốt hơn** (ẩn UI không cần thiết); bảo vệ **dữ liệu thật** luôn luôn phải nằm ở server, qua `[Authorize]`/`AddJwtBearer` trên từng API endpoint, không có ngoại lệ.

---

## 5. Đăng xuất — xoá token & báo lại cho toàn cây component

**Định nghĩa (một câu):** Đăng xuất trong kiến trúc này gồm **hai bước bắt buộc theo đúng thứ tự** — (1) xoá token khỏi nơi lưu (`localStorage`, qua `TokenLuuTru.XoaTokenAsync()` ở mục 1), và (2) gọi một phương thức báo cho `AuthenticationStateProvider` biết trạng thái đăng nhập đã đổi (`NotifyAuthenticationStateChanged`), để **toàn bộ** `AuthorizeView`/`[Authorize]` trong cây component tự động render lại theo trạng thái mới — bỏ qua bước (2) khiến UI hiển thị sai (vẫn "tưởng" đã đăng nhập) dù token đã bị xoá thật.

```csharp title="JwtAuthStateProvider.cs (bo sung phuong thuc dang xuat)"
// test:skip can du an Blazor WASM rieng (dotnet new blazorwasm), khong compile trong dotnet new web
public sealed class JwtAuthStateProvider : AuthenticationStateProvider
{
    private readonly TokenLuuTru _tokenLuuTru;

    public JwtAuthStateProvider(TokenLuuTru tokenLuuTru) => _tokenLuuTru = tokenLuuTru;

    public override Task<AuthenticationState> GetAuthenticationStateAsync()
        => throw new NotImplementedException("xem day du o muc 2b");

    // Gọi khi đăng nhập THÀNH CÔNG: lưu token rồi báo trạng thái đổi.
    public async Task DangNhapAsync(string token)
    {
        await _tokenLuuTru.LuuTokenAsync(token);
        // NotifyAuthenticationStateChanged nhận vào MỘT Task<AuthenticationState> -
        // gọi lại đúng GetAuthenticationStateAsync() để Blazor có giá trị MỚI,
        // rồi tự thông báo cho mọi AuthorizeView/[Authorize] đang lắng nghe.
        NotifyAuthenticationStateChanged(GetAuthenticationStateAsync());
    }

    // Gọi khi đăng xuất: xoá token RỒI MỚI báo trạng thái đổi - đúng thứ tự.
    public async Task DangXuatAsync()
    {
        await _tokenLuuTru.XoaTokenAsync();
        NotifyAuthenticationStateChanged(GetAuthenticationStateAsync());
    }
}
```

```razor title="ThanhDangNhap.razor (hoan chinh voi dang xuat)"
@inject AuthenticationStateProvider AuthProvider

<AuthorizeView>
    <Authorized>
        <p>Xin chào, @context.User.Identity?.Name!</p>
        <button @onclick="DangXuat">Đăng xuất</button>
    </Authorized>
    <NotAuthorized>
        <a href="/dang-nhap">Đăng nhập ngay</a>
    </NotAuthorized>
</AuthorizeView>

@code {
    private async Task DangXuat()
    {
        // Ep kieu ve dung lop con da dang ky (xem mục 2b: AddScoped<AuthenticationStateProvider, JwtAuthStateProvider>())
        // de goi duoc DangXuatAsync() - phuong thuc nay khong co tren lop cha truu tuong.
        if (AuthProvider is JwtAuthStateProvider jwtProvider)
        {
            await jwtProvider.DangXuatAsync();
        }
    }
}
```

Trình tự cụ thể xảy ra sau khi nhấn "Đăng xuất": `XoaTokenAsync()` chạy trước (xoá khỏi `localStorage`) → `NotifyAuthenticationStateChanged(...)` chạy sau, truyền vào kết quả **mới** của `GetAuthenticationStateAsync()` (lúc này đọc `localStorage` sẽ ra `null`, vì đã xoá) → Blazor nhận thông báo này và tự động re-render **mọi** `AuthorizeView`/`AuthorizeRouteView` đang có trên màn hình, không cần bạn tự gọi `StateHasChanged()` ở từng nơi.

!!! danger "Nếu quên gọi `NotifyAuthenticationStateChanged` — lỗi runtime cụ thể"
    Giả sử bạn viết `DangXuatAsync()` chỉ có một dòng `await _tokenLuuTru.XoaTokenAsync();`, thiếu dòng `NotifyAuthenticationStateChanged(...)`. Token **đã bị xoá thật** khỏi `localStorage` — nếu bạn tải lại trang (F5) ngay sau đó, `GetAuthenticationStateAsync()` sẽ đọc lại và thấy đúng "chưa đăng nhập". Nhưng **nếu không tải lại trang**, `<AuthorizeView>` đang hiển thị trên màn hình **không hề biết** gì đã đổi — nó chỉ gọi `GetAuthenticationStateAsync()` một lần lúc khởi tạo, không tự động polling kiểm tra lại. Kết quả: người dùng vẫn nhìn thấy "Xin chào, Lan!" và nút "Đăng xuất" y như trước khi bấm, dù token đã mất — họ tưởng đăng xuất không hoạt động, phải tự F5 mới thấy đúng trạng thái. Đây là lỗi runtime âm thầm, không có exception, chỉ phát hiện được khi test thủ công bằng cách quan sát UI có tự đổi ngay sau khi bấm nút hay không.

---

## 6. Kiểm tra token hết hạn (`exp`) ngay ở client — vì sao cần thêm bước này

Mục 2b đã dựng `GetAuthenticationStateAsync()` chỉ đọc token và giải mã claim, **không** kiểm claim `exp` (thời điểm hết hạn, đã học ở P4 — một số Unix timestamp tính bằng giây). Mục này giải thích cụ thể tại sao thiếu bước này gây trải nghiệm người dùng tệ, và cách thêm đúng.

**Định nghĩa (một câu):** Kiểm `exp` ở client là việc `GetAuthenticationStateAsync()` tự so sánh claim `exp` giải mã được với thời điểm hiện tại (`DateTimeOffset.UtcNow`), và nếu token đã hết hạn, **coi như chưa đăng nhập** (trả về `ClaimsPrincipal` rỗng) dù token vẫn còn tồn tại trong `localStorage` — đây chỉ là kiểm tra để **quyết định hiển thị UI đúng sớm hơn**, không phải một lớp bảo mật (bảo mật thật vẫn là server từ chối token hết hạn qua `AddJwtBearer`, đã học ở P4).

Nếu **không** thêm kiểm tra này, kịch bản cụ thể xảy ra: người dùng đăng nhập lúc 9:00, token có `exp` là 9:15 (15 phút). Họ để tab mở, không tương tác, tới 9:20 mới bấm một nút gọi API. `AuthenticationStateProvider` (theo mục 2b, chưa kiểm `exp`) vẫn báo "đã đăng nhập" — `<AuthorizeView>` vẫn hiện `<Authorized>`, nút bấm được vẫn hiện bình thường. Nhưng khi request gọi tới server, `AddJwtBearer` (P4) kiểm `exp` và trả về `401 Unauthorized` — người dùng thấy hành động của họ "im lặng thất bại" hoặc một lỗi khó hiểu, dù UI trước đó vẫn khẳng định họ "đã đăng nhập".

Ví dụ tối thiểu, độc lập — hàm kiểm `exp` từ claim đã giải mã:

```csharp title="KiemHanTokenDemo.cs"
// test:run
// --- Top-level statement PHẢI đứng trước mọi khai báo class/interface trong file .cs ---
long expConHan = DateTimeOffset.UtcNow.AddMinutes(10).ToUnixTimeSeconds();
long expDaHetHan = DateTimeOffset.UtcNow.AddMinutes(-5).ToUnixTimeSeconds();

Console.WriteLine($"Token con han: {ConHanSuDung(expConHan)}");
Console.WriteLine($"Token da het han: {ConHanSuDung(expDaHetHan)}");

if (!ConHanSuDung(expConHan)) throw new Exception("Test FAIL: token con han phai tra ve true");
if (ConHanSuDung(expDaHetHan)) throw new Exception("Test FAIL: token het han phai tra ve false");
Console.WriteLine("Test PASS");

static bool ConHanSuDung(long expUnixSeconds)
{
    // Claim "exp" trong JWT luôn là SỐ GIÂY tính từ 1/1/1970 UTC (Unix timestamp) -
    // không phải chuỗi ngày giờ thông thường - đây là quy ước của chuẩn JWT (P4).
    var thoiDiemHetHan = DateTimeOffset.FromUnixTimeSeconds(expUnixSeconds);
    return thoiDiemHetHan > DateTimeOffset.UtcNow;
}
```

```text title="output"
Token con han: True
Token da het han: False
Test PASS
```

Ghép vào `GetAuthenticationStateAsync()` của mục 2b — chỉ thêm đúng một bước kiểm tra sau khi giải mã claim, trước khi dựng `ClaimsPrincipal`:

```csharp title="JwtAuthStateProvider.cs (bo sung kiem exp)"
// test:skip can du an Blazor WASM rieng (dotnet new blazorwasm), khong compile trong dotnet new web
public override async Task<AuthenticationState> GetAuthenticationStateAsync()
{
    var token = await _tokenLuuTru.DocTokenAsync();
    var rong = new AuthenticationState(new ClaimsPrincipal(new ClaimsIdentity()));

    if (string.IsNullOrWhiteSpace(token)) return rong;

    var claims = GiaiMaClaimsTuJwt(token).ToList();

    // Bước MỚI: tìm claim "exp", nếu hết hạn hoặc claim không tồn tại
    // (token dựng sai/thiếu) -> coi như chưa đăng nhập, KHÔNG dựng ClaimsPrincipal
    // từ claim còn lại - tránh hiển thị "đã đăng nhập" cho một token đã chết.
    var expClaim = claims.FirstOrDefault(c => c.Type == "exp");
    if (expClaim is null || !long.TryParse(expClaim.Value, out var expUnix))
        return rong;

    var hetHanLuc = DateTimeOffset.FromUnixTimeSeconds(expUnix);
    if (hetHanLuc <= DateTimeOffset.UtcNow)
    {
        // Token hết hạn thật - dọn luôn khỏi localStorage, tránh lần
        // GetAuthenticationStateAsync() sau lại phải kiểm lại từ đầu.
        await _tokenLuuTru.XoaTokenAsync();
        return rong;
    }

    var identity = new ClaimsIdentity(claims, authenticationType: "jwt");
    return new AuthenticationState(new ClaimsPrincipal(identity));
}
```

!!! warning "Kiểm `exp` ở client KHÔNG thay được việc server từ chối token hết hạn"
    Giống cảnh báo ở mục 2, việc kiểm `exp` này chạy hoàn toàn trong trình duyệt — một người dùng cố tình có thể sửa code JavaScript/WASM đã tải xuống để bỏ qua bước kiểm này (dù hiếm ai làm vậy một cách tình cờ). Mục đích của bước kiểm `exp` ở client **không phải bảo mật** — nó chỉ giúp UI phản ánh đúng trạng thái thực tế **sớm hơn**, tránh người dùng thấy "đã đăng nhập" nhưng gọi API lại bị `401`. Server **vẫn phải** tự kiểm `exp` độc lập (qua `TokenValidationParameters.ValidateLifetime`, đã học ở P4) — đây là lớp bảo vệ thật, không được bỏ qua dù client đã kiểm.

---

## 7. So sánh nơi đặt kiểm tra đăng nhập — `<AuthorizeView>`, `[Authorize]`, và kiểm tra thủ công trong `@code`

Sau khi đã học ba cách "biết ai đang đăng nhập" (mục 3, mục 4, và tiêm trực tiếp `AuthenticationStateProvider` để tự gọi `GetAuthenticationStateAsync()` trong `@code` như mục 5 đã làm để gọi `DangXuatAsync()`), cần một tiêu chí chọn đúng công cụ cho đúng tình huống — dùng sai không gây lỗi biên dịch, nhưng gây code khó đọc hoặc dư thừa.

| | `<AuthorizeView>` | `[Authorize]` trên `@page` | Tự gọi `AuthenticationStateProvider` trong `@code` |
|---|---|---|---|
| Phạm vi chặn | Một phần UI trong trang (trang vẫn hiển thị được) | Toàn bộ trang (cả trang bị thay bằng `<NotAuthorized>`) | Không tự chặn gì — chỉ đọc dữ liệu, bạn tự quyết định làm gì với nó |
| Cách dùng | Khai báo trong markup (`.razor`), không viết C# logic | Attribute trên `@page`, không viết C# logic | Tiêm (`@inject`) rồi gọi `await AuthProvider.GetAuthenticationStateAsync()` trong `@code` |
| Khi nào dùng | Một trang có phần công khai + phần chỉ người đăng nhập thấy (ví dụ trang chủ có banner "Xin chào" khác nhau) | Cả trang chỉ có ý nghĩa khi đã đăng nhập (trang cá nhân, trang quản trị) | Cần **logic tuỳ biến** dựa trên trạng thái đăng nhập — ví dụ gọi API khác nhau, hoặc như mục 5, gọi phương thức riêng của lớp con (`DangXuatAsync()`) không có trên `AuthorizeView` |
| Chi phí viết | Thấp — chỉ markup | Thấp nhất — một attribute | Cao hơn — tự viết code C# xử lý, tự quyết định khi nào gọi lại |

Ví dụ cụ thể phân biệt cột thứ ba với hai cột đầu — một trang sản phẩm có phần công khai (ai cũng xem giá) và phần riêng (chỉ thành viên thấy giá ưu đãi), **và** cần gọi một API khác hẳn tuỳ trạng thái đăng nhập (không chỉ ẩn/hiện UI):

```razor title="TrangSanPham.razor"
@page "/san-pham/{Id:int}"
@inject AuthenticationStateProvider AuthProvider
@inject HttpClient Http

<h3>Sản phẩm #@Id</h3>

<AuthorizeView>
    <Authorized>
        <p>Giá ưu đãi thành viên: @giaHienThi</p>
    </Authorized>
    <NotAuthorized>
        <p>Giá niêm yết: @giaHienThi (đăng nhập để xem giá ưu đãi)</p>
    </NotAuthorized>
</AuthorizeView>

@code {
    [Parameter] public int Id { get; set; }
    private decimal giaHienThi;

    protected override async Task OnInitializedAsync()
    {
        var state = await AuthProvider.GetAuthenticationStateAsync();
        bool daDangNhap = state.User.Identity?.IsAuthenticated ?? false;

        // Logic KHÁC HẲN tuỳ trạng thái - không chỉ ẩn/hiện UI, mà gọi
        // HAI endpoint API khác nhau. AuthorizeView không làm được việc
        // "chọn API để gọi" - đây là lý do cần tự gọi AuthProvider trong @code.
        var url = daDangNhap ? $"/api/san-pham/{Id}/gia-uu-dai" : $"/api/san-pham/{Id}/gia-niem-yet";
        giaHienThi = await Http.GetFromJsonAsync<decimal>(url);
    }
}
```

Điểm mấu chốt: `<AuthorizeView>` trong ví dụ trên **chỉ** quyết định hiển thị dòng chữ nào (UI) — nó không giúp gì cho việc **chọn API để gọi** trong `OnInitializedAsync()`. Vì `OnInitializedAsync()` là code C# thuần (không phải markup), muốn biết trạng thái đăng nhập ở đó buộc phải tự gọi `await AuthProvider.GetAuthenticationStateAsync()` — không có phiên bản "markup" nào thay thế được cho nhu cầu này.

!!! note "`state.User.Identity?.IsAuthenticated` — cách kiểm tra đăng nhập chuẩn, không dựa vào `Name` khác `null`"
    Nhiều người mới học kiểm tra "đã đăng nhập chưa" bằng cách xem `Identity?.Name != null` — cách này **sai** nếu token có claim khác nhưng thiếu đúng claim tên (như cảnh báo mục 2b về map sai `ClaimTypes.Name`), vì lúc đó `Name` là `null` dù người dùng **đã** đăng nhập hợp lệ. Cách đúng, không phụ thuộc claim nào có mặt: `Identity?.IsAuthenticated` — thuộc tính này được `ClaimsIdentity` tự tính dựa trên việc `authenticationType` (tham số truyền vào constructor, xem mục 2b: `authenticationType: "jwt"`) có được gán hay không, hoàn toàn độc lập với việc claim `Name` có tồn tại hay không.

---

## 8. Phân quyền theo vai trò (Role) — `[Authorize(Roles = "...")]` và `AuthorizeView Roles="..."`

Mọi mục trước chỉ phân biệt hai trạng thái: "đã đăng nhập" hay "chưa đăng nhập". Thực tế nhiều ứng dụng cần thêm một mức nữa: đã đăng nhập **và** có đúng vai trò (role) mới được vào một trang/thấy một phần UI — ví dụ trang quản trị chỉ cho `admin`, không cho `user` thường (dù cả hai đều đã đăng nhập hợp lệ).

**Định nghĩa (một câu):** Phân quyền theo vai trò là việc `[Authorize]`/`<AuthorizeView>` kiểm tra **thêm** một claim cụ thể (thường có type chuẩn `ClaimTypes.Role`, hoặc `"role"` nếu bạn tự chỉ định `roleClaimType` khi tạo `ClaimsIdentity`) có khớp với một trong các vai trò được liệt kê trong thuộc tính `Roles` hay không — chỉ cần **một** vai trò khớp là đủ, không cần khớp hết.

Trước tiên, `ClaimsIdentity` cần biết claim nào là "vai trò" — tương tự cách nó cần biết claim nào là "tên" (`nameType`, đã nhắc ở mục 2b/"Cạm bẫy"). Bổ sung `roleClaimType` khi dựng identity trong `JwtAuthStateProvider`:

```csharp title="JwtAuthStateProvider.cs (bo sung roleClaimType)"
// test:skip can du an Blazor WASM rieng (dotnet new blazorwasm), khong compile trong dotnet new web
// Tham số thứ ba (roleClaimType) báo cho ClaimsIdentity biết claim có TYPE
// là chuỗi "role" (khớp đúng tên claim trong payload JWT, xem mục 2b) chính
// là claim vai trò - từ đây, mọi API kiểm Role (IsInRole, [Authorize(Roles=...)])
// đều tìm đúng claim này, không cần biết gì thêm về cấu trúc JWT gốc.
var identity = new ClaimsIdentity(
    claims,
    authenticationType: "jwt",
    nameType: "name",
    roleClaimType: "role");
```

Với `roleClaimType` đã khai đúng, `[Authorize(Roles = "...")]` trên `@page` chặn theo vai trò, tương tự `[Authorize]` (mục 4) nhưng chặt hơn:

```razor title="TrangQuanTriRieng.razor"
@page "/quan-tri-rieng"
@attribute [Authorize(Roles = "admin")]

<h3>Khu vực chỉ dành cho admin</h3>
```

Và `<AuthorizeView Roles="...">` làm tương tự `<AuthorizeView>` (mục 3) nhưng chỉ hiện `<Authorized>` khi khớp đúng vai trò — người đã đăng nhập nhưng **sai** vai trò sẽ rơi vào `<NotAuthorized>`, giống như chưa đăng nhập:

```razor title="MenuQuanTri.razor"
<AuthorizeView Roles="admin">
    <Authorized>
        <a href="/quan-tri-rieng">Trang quản trị</a>
    </Authorized>
    <NotAuthorized>
        <p>Bạn không có quyền admin.</p>
    </NotAuthorized>
</AuthorizeView>
```

!!! danger "Nếu quên khai `roleClaimType` — lỗi runtime cụ thể, không phải lỗi biên dịch"
    Nếu `ClaimsIdentity` được dựng **không** khai `roleClaimType` (như ví dụ gốc ở mục 2b, chỉ có `authenticationType`), `[Authorize(Roles = "admin")]` và `<AuthorizeView Roles="admin">` sẽ **luôn luôn** coi như không khớp vai trò nào — dù payload JWT có đúng `"role":"admin"` và người dùng **đã** đăng nhập hợp lệ, họ vẫn bị đẩy vào `<NotAuthorized>`/trang bị chặn. Nguyên nhân: `ClaimsIdentity` mặc định tìm vai trò theo type chuẩn `ClaimTypes.Role` (chuỗi dài `"http://schemas.microsoft.com/ws/2008/06/identity/claims/role"`) — nếu claim trong `Claims` của bạn có type là `"role"` (chuỗi ngắn, khớp key JSON gốc) mà không khai `roleClaimType: "role"` để báo lệch chuẩn này, `ClaimsIdentity.IsInRole(...)` (được `[Authorize(Roles=...)]` gọi ngầm) sẽ không tìm thấy claim nào khớp, luôn trả `false`. Đây là lỗi runtime âm thầm y hệt dạng lỗi `Identity.Name` trả `null` đã học ở mục 2b — chỉ khác claim bị ảnh hưởng là vai trò thay vì tên.

---

## Cạm bẫy & thực chiến

- **Tưởng token còn sau khi F5 nếu chỉ lưu trong biến C#:** như mục 0 đã chỉ ra, Blazor WebAssembly khởi động lại hoàn toàn khi tải lại trang — mọi biến C# trong bộ nhớ RAM mất theo. Chỉ dữ liệu ghi vào `localStorage` (hoặc cookie, IndexedDB) mới sống sót qua F5.
- **Tưởng `AuthenticationStateProvider`/`[Authorize]` phía Blazor bảo vệ được dữ liệu API:** như mục 4 đã cảnh báo cụ thể, toàn bộ logic này chạy trong trình duyệt của chính người dùng — họ có toàn quyền bỏ qua nó. Bảo vệ thật luôn nằm ở `[Authorize]`/`AddJwtBearer` trên server (P4), không có ngoại lệ.
- **Quên `NotifyAuthenticationStateChanged` sau khi đăng nhập/đăng xuất:** UI hiển thị trạng thái cũ dù dữ liệu (token) đã đổi thật — như mục 5 đã chỉ ra cụ thể, chỉ phát hiện được bằng quan sát UI, không có exception nào báo.
- **Quên `AddAuthorizationCore()` khi đăng ký DI:** ném exception lúc khởi động app ("no registered service of type IAuthorizationPolicyProvider") ngay khi `AuthorizeView`/`[Authorize]` đầu tiên chạy — như mục 2b đã nêu cụ thể thông báo lỗi.
- **Map sai tên claim khi dựng `ClaimsIdentity`, khiến `context.User.Identity?.Name` trả `null`:** `Identity.Name` mặc định đọc claim có type chuẩn `ClaimTypes.Name` (chuỗi dài `"http://schemas.xmlsoap.org/ws/2005/05/identity/claims/name"`), không phải chuỗi `"name"` ngắn bạn thấy trong payload JWT. Nếu dựng `new Claim("name", "Lan")` (dùng chuỗi ngắn) như ví dụ mục 2b, `Identity.Name` sẽ là `null` — cần map đúng: `new Claim(ClaimTypes.Name, "Lan")`, hoặc truyền tên type claim khi tạo `ClaimsIdentity` (tham số `nameType`) để nó biết claim nào là "tên".
- **Lưu dữ liệu nhạy cảm khác (không chỉ JWT) vào `localStorage` vì nghĩ nó "riêng tư":** như mục 1 đã cảnh báo, `localStorage` không chống được JavaScript độc hại đọc cùng domain (rủi ro XSS) — chỉ lưu những gì cần cho việc xác thực (token), không lưu thêm dữ liệu nhạy cảm không cần thiết ở phía client.
- **Không kiểm token đã hết hạn (`exp`) ở phía client trước khi coi là "đã đăng nhập":** ví dụ mục 2b không kiểm `exp` — nếu token còn trong `localStorage` nhưng đã hết hạn thật, `GetAuthenticationStateAsync()` vẫn trả về "đã đăng nhập" (UI hiển thị sai), và request API tiếp theo mới bị server từ chối (401). Mục 6 chỉ ra cách kiểm `exp` ngay trong `GetAuthenticationStateAsync()` (so với `DateTimeOffset.UtcNow`) và coi như "chưa đăng nhập" nếu đã hết hạn, tránh gọi API rồi mới phát hiện lỗi.
- **Tưởng kiểm `exp` ở client thay được việc server kiểm `exp`:** như mục 6 đã cảnh báo, kiểm `exp` ở client chỉ chạy trong trình duyệt của người dùng — họ có thể bỏ qua nó. `ValidateLifetime` trong `TokenValidationParameters` ở server (P4) vẫn là lớp bảo vệ bắt buộc, không phải "đã kiểm ở client rồi nên server có thể lược bớt".
- **Dùng `<AuthorizeView>` ở nơi cần logic tuỳ biến theo trạng thái đăng nhập (không chỉ ẩn/hiện UI):** như mục 7 đã chỉ ra, `<AuthorizeView>` chỉ chọn khối markup nào hiển thị — nếu bạn cần **chọn API để gọi**, **chuyển hướng trang**, hay bất kỳ logic C# nào khác tuỳ trạng thái đăng nhập trong `@code`, phải tự tiêm `AuthenticationStateProvider` và gọi `GetAuthenticationStateAsync()`, không có cách nào lấy được kết quả đó ra ngoài markup của `<AuthorizeView>`.
- **Kiểm tra đăng nhập bằng `Identity?.Name != null` thay vì `Identity?.IsAuthenticated`:** như mục 7 đã cảnh báo, `Name` phụ thuộc vào việc claim tên có được map đúng `ClaimTypes.Name` hay không (xem cạm bẫy về map sai claim ở trên) — một người dùng đã đăng nhập hợp lệ nhưng thiếu đúng claim tên sẽ bị code kiểm tra sai là "chưa đăng nhập". `IsAuthenticated` không phụ thuộc claim nào, luôn là cách kiểm tra đúng.
- **Dùng `[Authorize(Roles = "...")]`/`<AuthorizeView Roles="...">` mà quên khai `roleClaimType` khi dựng `ClaimsIdentity`:** như mục 8 đã chỉ ra cụ thể, thiếu `roleClaimType` khiến mọi kiểm tra vai trò luôn trả `false` — người dùng đúng vai trò vẫn bị chặn, dù JWT có đúng claim `role`, không có exception nào báo lỗi này.

---

## Bài tập

**Bài 1 (giàn giáo):** Viết một component `TrangQuanTri.razor` tại route `/quan-tri`, chỉ hiển thị được khi đã đăng nhập, dùng đúng attribute đã học ở mục 4.

??? success "Lời giải + vì sao"
    ```razor title="TrangQuanTri.razor"
    @page "/quan-tri"
    @attribute [Authorize]

    <h3>Trang quản trị</h3>
    <p>Chỉ người đã đăng nhập mới truy cập được.</p>
    ```

    **Vì sao đúng:** `@attribute [Authorize]` đặt ngay dưới `@page` báo cho `AuthorizeRouteView` (đã cấu hình trong `App.razor` — xem mục 4) chặn hiển thị nội dung trang này nếu `GetAuthenticationStateAsync()` trả về người dùng chưa xác thực, tự động chuyển sang hiện `<NotAuthorized>` đã định nghĩa ở `App.razor` — không cần viết `if/else` thủ công trong từng trang.

**Bài 2 (thiết kế — sửa lỗi thứ tự đăng xuất):** Đoạn code sau có lỗi logic, dù không lỗi biên dịch. Tìm lỗi, giải thích hậu quả runtime cụ thể, và sửa lại.

```csharp title="JwtAuthStateProvider.cs (co loi thu tu)"
// test:skip doan trich mot method, khong phai class day du - can du an Blazor WASM thuc te
public async Task DangXuatAsync()
{
    NotifyAuthenticationStateChanged(GetAuthenticationStateAsync());
    await _tokenLuuTru.XoaTokenAsync();
}
```

??? success "Lời giải + vì sao"
    **Lỗi:** thứ tự bị đảo — `NotifyAuthenticationStateChanged(GetAuthenticationStateAsync())` được gọi **trước** khi token bị xoá. `GetAuthenticationStateAsync()` (được gọi ngay tại dòng này, làm tham số) sẽ đọc token **vẫn còn trong `localStorage`** (vì `XoaTokenAsync()` chưa chạy), nên trả về đúng trạng thái "đã đăng nhập" **cũ** — `NotifyAuthenticationStateChanged` báo cho toàn cây một trạng thái không đổi gì, `AuthorizeView` không có lý do để render lại với trạng thái mới.

    **Hậu quả runtime cụ thể:** người dùng bấm "Đăng xuất", token bị xoá khỏi `localStorage` thật (dòng thứ hai vẫn chạy), nhưng UI **không đổi** — vẫn hiện "Xin chào, ..." như trước, giống hệt hậu quả đã mô tả ở cảnh báo cuối mục 5, dù ở đây nguyên nhân là sai **thứ tự** chứ không phải **thiếu** lời gọi.

    **Sửa lại — xoá token trước, thông báo sau:**

    ```csharp title="JwtAuthStateProvider.cs (da sua thu tu)"
    // test:skip doan trich mot method, khong phai class day du - can du an Blazor WASM thuc te
    public async Task DangXuatAsync()
    {
        await _tokenLuuTru.XoaTokenAsync();
        NotifyAuthenticationStateChanged(GetAuthenticationStateAsync());
    }
    ```

    **Vì sao đúng:** `XoaTokenAsync()` chạy xong trước, nên khi `GetAuthenticationStateAsync()` được gọi làm tham số cho `NotifyAuthenticationStateChanged`, nó đọc `localStorage` và thấy token đã **thực sự** không còn — trả về đúng trạng thái "chưa đăng nhập" mới, và `AuthorizeView` nhận thông báo với giá trị đúng, re-render đúng UI.

**Bài 3 (áp dụng — chọn đúng công cụ):** Bạn cần một trang `/gio-hang` hiển thị được cho **cả** người chưa đăng nhập (xem giỏ hàng dạng khách, không lưu server) **và** người đã đăng nhập (giỏ hàng đồng bộ server) — nhưng nếu chưa đăng nhập, ẩn nút "Thanh toán" và hiện thay bằng liên kết "Đăng nhập để thanh toán". Toàn trang không được chặn hoàn toàn với người chưa đăng nhập (họ vẫn cần xem giỏ hàng dạng khách). Chọn `<AuthorizeView>` hay `[Authorize]`, giải thích bằng tiêu chí mục 7.

??? success "Lời giải + vì sao"
    **Dùng `<AuthorizeView>`, không dùng `[Authorize]`.** Theo mục 7: `[Authorize]` chặn **toàn bộ trang**, thay hẳn nội dung bằng `<NotAuthorized>` của `AuthorizeRouteView` khi chưa đăng nhập — không phù hợp ở đây, vì đề bài yêu cầu người chưa đăng nhập **vẫn xem được** giỏ hàng (dạng khách), chỉ riêng nút "Thanh toán" mới cần ẩn. `<AuthorizeView>` đúng vì nó chỉ chặn **một phần** UI (đúng cột đầu của bảng mục 7) trong khi phần còn lại của trang (danh sách sản phẩm trong giỏ) vẫn hiển thị bình thường, nằm ngoài `<AuthorizeView>`.

    ```razor title="TrangGioHang.razor"
    @page "/gio-hang"

    <h3>Giỏ hàng của bạn</h3>
    <p>(Danh sách sản phẩm hiển thị cho mọi người, không cần AuthorizeView)</p>

    <AuthorizeView>
        <Authorized>
            <button>Thanh toán</button>
        </Authorized>
        <NotAuthorized>
            <a href="/dang-nhap">Đăng nhập để thanh toán</a>
        </NotAuthorized>
    </AuthorizeView>
    ```

---

## Tự kiểm tra

1. Vì sao lưu JWT trong một biến C# thường (không dùng `localStorage`) không sống sót qua việc tải lại trang (F5) trong Blazor WebAssembly?

    ??? note "Đáp án"
        Vì Blazor WebAssembly chạy hoàn toàn trong trình duyệt qua WASM runtime — khi tải lại trang, toàn bộ chương trình .NET trong bộ nhớ bị xoá và khởi động lại từ đầu, giống tắt/mở lại một ứng dụng. Mọi biến C# chỉ sống trong RAM của lần chạy đó sẽ mất theo. `localStorage` là bộ nhớ của trình duyệt (gắn với domain), tồn tại độc lập với vòng đời chương trình .NET, nên còn nguyên sau khi tải lại.

2. `AuthenticationStateProvider` là gì, và tại sao bạn phải tự kế thừa nó (không dùng trực tiếp lớp cha)?

    ??? note "Đáp án"
        Là lớp trừu tượng của Blazor đóng vai trò nguồn sự thật duy nhất cho câu hỏi "ai đang đăng nhập" — mọi `AuthorizeView`/`[Authorize]` trong app đều hỏi qua nó. Phải tự kế thừa vì lớp cha không biết cách tìm ra danh tính trong ứng dụng cụ thể của bạn (đọc token ở đâu, giải mã ra sao) — bạn override `GetAuthenticationStateAsync()` để dạy nó cách làm điều đó, cụ thể ở đây là đọc token từ `localStorage` rồi giải mã claim.

3. `AuthenticationStateProvider` phía Blazor WASM có kiểm chữ ký (signature) của JWT không? Vì sao có/không, và điều này ảnh hưởng gì tới việc bảo vệ dữ liệu?

    ??? note "Đáp án"
        Không kiểm chữ ký, vì trình duyệt không có secret key để kiểm (chỉ server giữ secret key, theo đúng kiến trúc JWT đã học ở P4). Nó chỉ giải mã payload để quyết định hiển thị UI gì. Vì vậy `AuthenticationStateProvider`/`[Authorize]` phía Blazor không phải cơ chế bảo vệ dữ liệu — bảo vệ thật (kiểm chữ ký, từ chối request) luôn phải nằm ở server, qua `AddJwtBearer`/`[Authorize]` trên API.

4. `<AuthorizeView>` khác `[Authorize]` trên `@page` như thế nào về phạm vi tác động?

    ??? note "Đáp án"
        `<AuthorizeView>` chỉ ẩn/hiện một phần UI bên trong một trang vẫn hiển thị được (dùng `<Authorized>`/`<NotAuthorized>` làm hai nhánh nội dung con). `[Authorize]` trên `@page` chặn hiển thị toàn bộ trang đó nếu chưa đăng nhập — cần `AuthorizeRouteView` trong `App.razor` để thực sự thực thi việc chặn này ở cấp route.

5. Vì sao `[Authorize]` trên một component Blazor KHÔNG bảo vệ được API mà trang đó gọi tới?

    ??? note "Đáp án"
        Vì toàn bộ code Blazor WASM (kể cả logic kiểm `[Authorize]`) chạy trong trình duyệt của chính người dùng — người dùng có toàn quyền sửa, bỏ qua, hoặc gọi thẳng API bằng công cụ khác (Postman, script) mà không đi qua trang Blazor. Nếu API backend không có `[Authorize]`/kiểm JWT riêng ở phía server, request trực tiếp tới API vẫn thành công dù trang Blazor "bị chặn".

6. Đăng xuất trong kiến trúc chương này gồm những bước nào, và vì sao phải đúng thứ tự đó?

    ??? note "Đáp án"
        Hai bước: (1) xoá token khỏi `localStorage`, (2) gọi `NotifyAuthenticationStateChanged` với kết quả `GetAuthenticationStateAsync()` mới. Phải xoá token TRƯỚC khi gọi `GetAuthenticationStateAsync()` làm tham số cho bước thông báo — nếu đảo thứ tự, `GetAuthenticationStateAsync()` sẽ đọc token còn tồn tại lúc đó, trả về trạng thái "vẫn đăng nhập" cũ, khiến UI không cập nhật đúng dù token đã xoá xong sau đó.

7. Nếu quên gọi `NotifyAuthenticationStateChanged` sau khi đăng xuất (nhưng token đã xoá đúng khỏi `localStorage`), hậu quả runtime cụ thể là gì?

    ??? note "Đáp án"
        Không có exception. Token đã bị xoá thật, nhưng `AuthorizeView`/`AuthorizeRouteView` đang hiển thị trên màn hình không được báo gì đổi (chúng chỉ gọi `GetAuthenticationStateAsync()` một lần lúc khởi tạo, không tự polling) — UI vẫn hiện như đã đăng nhập cho tới khi người dùng tự tải lại trang.

8. Vì sao `context.User.Identity?.Name` có thể trả về `null` dù `ClaimsIdentity` đã được dựng với đúng dữ liệu tên người dùng?

    ??? note "Đáp án"
        Vì `Identity.Name` mặc định đọc claim có type chuẩn `ClaimTypes.Name`, không phải một chuỗi tuỳ ý như `"name"`. Nếu claim được dựng bằng `new Claim("name", ...)` (tên ngắn, khớp với key trong JWT payload) mà không map đúng sang `ClaimTypes.Name` hoặc chỉ định `nameType` khi tạo `ClaimsIdentity`, `Identity.Name` sẽ không tìm thấy claim khớp và trả về `null`.

9. `localStorage` có bảo vệ được JWT khỏi một đoạn JavaScript độc hại chạy trên cùng trang (tấn công XSS) không?

    ??? note "Đáp án"
        Không. `localStorage` không có cơ chế phân quyền giữa các script chạy trên cùng domain — nếu một script độc hại chèn được vào trang, nó đọc được toàn bộ `localStorage` của domain đó, bao gồm JWT. Đây là hạn chế cố hữu của `localStorage`, không phải lỗi dùng sai cách.

10. Vì sao cần kiểm claim `exp` ngay trong `GetAuthenticationStateAsync()`, dù server (P4) cũng đã kiểm `exp` khi nhận request?

    ??? note "Đáp án"
        Để UI phản ánh đúng trạng thái thực tế sớm hơn — nếu không kiểm ở client, `<AuthorizeView>` vẫn hiện "đã đăng nhập" cho một token đã hết hạn, người dùng bấm hành động và chỉ phát hiện lỗi khi server trả về `401`. Đây không phải cơ chế bảo mật (client có thể bị bỏ qua) — server vẫn phải tự kiểm `exp` độc lập; kiểm ở client chỉ cải thiện trải nghiệm, giúp UI không "nói dối" trạng thái đăng nhập.

11. Khi nào bạn buộc phải tự tiêm `AuthenticationStateProvider` và gọi `GetAuthenticationStateAsync()` trong `@code`, thay vì chỉ dùng `<AuthorizeView>`?

    ??? note "Đáp án"
        Khi cần logic C# tuỳ biến theo trạng thái đăng nhập mà không chỉ là ẩn/hiện UI — ví dụ chọn gọi API nào trong `OnInitializedAsync()`, hoặc gọi một phương thức riêng của lớp con `AuthenticationStateProvider` (như `DangXuatAsync()` ở mục 5) không có sẵn trên `<AuthorizeView>`. `<AuthorizeView>` chỉ quyết định khối markup nào hiển thị, không trả kết quả ra được cho code C# khác dùng.

12. Nếu `ClaimsIdentity` được dựng mà không khai `roleClaimType`, và payload JWT có `"role":"admin"`, `[Authorize(Roles = "admin")]` sẽ cho người dùng này vào trang hay chặn lại? Vì sao?

    ??? note "Đáp án"
        Sẽ chặn lại, dù người dùng đúng có claim `role: admin` trong JWT. `ClaimsIdentity` mặc định tìm vai trò theo type chuẩn `ClaimTypes.Role`, không phải chuỗi ngắn `"role"` — nếu không khai `roleClaimType: "role"` khi dựng `ClaimsIdentity` để báo lệch chuẩn này, `IsInRole(...)` (được `[Authorize(Roles=...)]` gọi ngầm) không tìm thấy claim khớp, luôn trả `false`. Đây là lỗi runtime âm thầm, không có exception.

---



??? abstract "DEEP DIVE — nâng cao (ngoài fast path)"
    - **`HttpOnly` cookie thay cho `localStorage`:** một cách giảm rủi ro XSS đọc token là lưu JWT trong cookie có cờ `HttpOnly` — cờ này khiến JavaScript (kể cả script độc hại chèn vào trang) **không đọc được** giá trị cookie đó, chỉ trình duyệt tự động gắn cookie vào mọi request tới cùng domain. Đánh đổi: cần cấu hình CORS/CSRF cẩn thận hơn, và không hợp với kiến trúc "API + SPA hoàn toàn tách domain" một cách đơn giản như `localStorage` + header `Authorization`. Đây là lựa chọn kiến trúc, không phải "luôn luôn tốt hơn" — nhiều ứng dụng thật vẫn dùng `localStorage` chấp nhận rủi ro XSS được giảm bằng cách khác (Content Security Policy nghiêm ngặt, sanitize input kỹ).
    - **`AuthorizationMessageHandler`/tự động gắn token vào `HttpClient`:** thay vì tự tay đọc token rồi gắn `Authorization: Bearer ...` vào mỗi request `HttpClient`, Blazor WASM có `AuthorizationMessageHandler` (trong package `Microsoft.AspNetCore.Components.WebAssembly.Authentication`) tự động làm việc này cho mọi request qua một `HttpClient` đã đăng ký — tránh lặp code gắn header ở từng nơi gọi API.
    - **Refresh token trong Blazor WASM:** JWT thường có thời hạn ngắn (`exp`) để giảm rủi ro nếu bị lộ; refresh token (đã học khái niệm ở P4) cho phép xin access token mới mà không bắt người dùng đăng nhập lại. Trong Blazor WASM, refresh token cũng cần lưu (thường cùng `localStorage` hoặc `HttpOnly` cookie riêng) và logic gọi refresh thường đặt trong một `DelegatingHandler` tự động thử refresh khi gặp response 401, rồi phát lại request gốc — phức tạp hơn phạm vi fast path của chương này.
    - **`Microsoft.AspNetCore.Components.WebAssembly.Authentication` với OpenID Connect/OAuth:** khi đăng nhập qua nhà cung cấp danh tính bên thứ ba (Google, Microsoft Entra ID...) thay vì tự cấp JWT như P4, Blazor WASM có template `dotnet new blazorwasm -au SingleOrg`/`-au Individual` dựng sẵn toàn bộ luồng OAuth/OIDC, `RemoteAuthenticatorView`, và một `AuthenticationStateProvider` chuyên biệt (`RemoteAuthenticationService`) — phức tạp hơn nhiều so với JWT tự cấp của chương này, nhưng cùng dựa trên đúng khái niệm nền `AuthenticationStateProvider`/`AuthorizeView` vừa học.

Tiếp theo -> js interop & lifecycle nâng cao
