---
tier: core
status: core
owner: security-expert
verified_on: "2026-07-05"
dotnet_version: "10.0"
bloom: áp dụng
requires: [p3-di]
risk_tier: T3
est_minutes_fast: 30
---

# JWT: cấp & kiểm token an toàn

!!! info "Bạn đang ở đây"
    cần trước: dependency injection, cấu hình service trong asp.net core, đăng ký middleware theo đúng thứ tự.
    mở khoá: cấp token đăng nhập đúng chuẩn, kiểm token ở mọi request được bảo vệ, hiểu vì sao JWT không phải "mã hoá" mà chỉ là "ký", và biết dùng refresh token để giữ phiên đăng nhập dài hạn mà không phải hy sinh bảo mật.

> Mục tiêu (đo được): sau chương này bạn **áp dụng** được `JwtSecurityTokenHandler` để cấp token với đúng các claim chuẩn trên .NET {{ dotnet.current }}, **cấu hình** được `AddJwtBearer` với `TokenValidationParameters` đầy đủ để kiểm token, **giải thích** được vì sao payload của JWT ai cũng đọc được nhưng không ai sửa được, và **thiết kế** được luồng access token + refresh token cho một API thật.

---

## 0. Đoán nhanh trước khi học

Bạn nhận được một JWT từ đồng nghiệp để debug:

```text title="Một JWT mẫu (rút gọn để dễ nhìn)"
eyJhbGciOiJIUzI1NiJ9.eyJzdWIiOiJ1c2VyLTQyIiwicm9sZSI6ImFkbWluIn0.4f8a...
```

Không cần chạy code, không cần biết secret key — chỉ nhìn chuỗi này.

??? question "Câu hỏi: bạn có đọc được `role` của user này không? Sửa được không?"
    **Đọc được** — phần payload (đoạn giữa) chỉ là Base64URL, không phải mã hoá, ai cũng decode được bằng tay hoặc bằng devtools trình duyệt, thấy ngay `"role":"admin"`.

    **Sửa được nội dung nhưng không sửa được token hợp lệ.** Nếu bạn đổi `"admin"` thành `"superadmin"` rồi encode lại, chuỗi Base64URL của payload sẽ đổi, nhưng chữ ký (phần thứ ba, tính từ payload gốc + secret key) sẽ **không khớp** với payload mới. Server kiểm chữ ký trước khi tin bất cứ claim nào — mục 3 sẽ giải thích chính xác vì sao.

Mục 1 sẽ chứng minh điều này bằng cách decode thật, từng byte, không cần code.

---

## 1. JWT là gì — cấu trúc 3 phần

**Định nghĩa (một câu):** JWT (JSON Web Token) là một **chuỗi văn bản gồm 3 phần** — `Header.Payload.Signature`, mỗi phần được mã hoá Base64URL và nối bằng dấu chấm — dùng để một server **khẳng định** ("tôi đã xác thực người này") mà bên nhận có thể **tự kiểm tra** mà không cần hỏi lại server gốc.

Ba phần đó là:

| Phần | Chứa gì | Mục đích |
|------|---------|----------|
| **Header** | Thuật toán ký (ví dụ `HS256`) và loại token (`JWT`) | Cho biết cách kiểm chữ ký |
| **Payload** | Các *claim* — thông tin về người dùng (`sub`, `exp`, `role`...) | Dữ liệu thực server muốn "khẳng định" |
| **Signature** | Kết quả ký mật mã của `Header.Payload` bằng secret key | Chứng minh payload chưa bị sửa và do đúng server phát hành |

### Decode thủ công — không cần code

Base64URL là một cách biểu diễn byte thành chữ, **không phải mã hoá** — ai cũng đảo ngược được, không cần khoá bí mật. Lấy phần payload từ token mẫu ở mục 0:

```text title="Payload gốc (Base64URL)"
eyJzdWIiOiJ1c2VyLTQyIiwicm9sZSI6ImFkbWluIn0
```

Base64URL giống Base64 chuẩn nhưng thay `+` → `-`, `/` → `_`, và bỏ dấu `=` đệm cuối. Decode bằng tay (hoặc dán vào bất kỳ công cụ Base64 online nào, thêm lại dấu `=` nếu cần):

```text title="Kết quả decode — chỉ là JSON thuần"
{"sub":"user-42","role":"admin"}
```

Không cần secret key, không cần server, không cần chạy .NET — chỉ cần biết Base64URL là đảo được **hai chiều tự do**. Đây chính là lý do mục 0 trả lời "đọc được": payload chỉ là JSON được mã hoá hiển thị, **không phải bí mật**.

!!! danger "Nếu hiểu sai — hậu quả bảo mật cụ thể"
    Nếu bạn nhét dữ liệu nhạy cảm (số thẻ tín dụng, mật khẩu, số CMND) vào claim của JWT vì nghĩ "nó được mã hoá rồi, an toàn" — **sai hoàn toàn**. Bất kỳ ai chặn được token (qua log, qua proxy, qua devtools trình duyệt) đều đọc được nguyên văn dữ liệu đó chỉ bằng một lệnh decode Base64URL, không cần phá bất kỳ thứ gì. JWT bảo vệ tính **toàn vẹn** (không ai sửa được mà không bị phát hiện), **không** bảo vệ tính **bí mật** (ai cũng đọc được).

---

## 2. Claim chuẩn — payload nói gì

**Định nghĩa (một câu):** *Claim* là một cặp `key: value` bên trong payload, mô tả một sự thật về token hoặc về chủ thể (ai được cấp token) — một số claim có **tên chuẩn hoá** theo RFC 7519 mà hầu hết thư viện JWT (bao gồm .NET) hiểu và xử lý đặc biệt.

| Claim | Ý nghĩa (một câu mỗi claim) |
|-------|------------------------------|
| `sub` | *Subject* — định danh chủ thể của token, thường là user ID. |
| `exp` | *Expiration* — thời điểm token **hết hạn**, tính bằng Unix timestamp **giây** (số giây kể từ 1970-01-01 UTC). |
| `iat` | *Issued At* — thời điểm token **được cấp**, cùng đơn vị Unix timestamp giây. |
| `nbf` | *Not Before* — thời điểm token **bắt đầu có hiệu lực**; token dùng trước mốc này bị coi là chưa hợp lệ. |
| `iss` | *Issuer* — ai (hệ thống nào) đã cấp token này, dùng để bên kiểm tra biết token có đến từ nguồn tin cậy. |
| `aud` | *Audience* — token này **dành cho** hệ thống/API nào; một API chỉ nên chấp nhận token có `aud` khớp với chính nó. |

!!! warning "Đơn vị của `exp`/`iat`/`nbf` — bẫy dễ nhầm"
    Ba claim thời gian này là **Unix timestamp tính bằng giây**, không phải millisecond (khác với `Date.now()` của JavaScript, vốn trả về millisecond). Nếu bạn tự tay ghép JSON payload và lấy nhầm giá trị millisecond nhét vào `exp`, con số sẽ lớn gấp 1000 lần thời điểm thật — thư viện JWT sẽ hiểu token này hết hạn vào một thời điểm cách xa hàng nghìn năm trong tương lai (token coi như *không bao giờ* hết hạn), một lỗ hổng bảo mật nghiêm trọng. Trong .NET bạn hiếm khi tự ghép số này bằng tay — `JwtSecurityToken` tự tính từ `DateTime` bạn truyền vào (xem mục 4) — nhưng nếu có ngày cần đọc/ghi claim thô, phải nhớ đơn vị là **giây**.

---

## 3. JWT không mã hoá — chỉ ký

**Định nghĩa (một câu):** "Ký" (signing) nghĩa là server dùng một khoá bí mật để tính ra một giá trị (chữ ký) **phụ thuộc toàn bộ** vào nội dung `Header.Payload`; bất kỳ ai có khoá đúng đều tính lại được chữ ký này để **so khớp**, nhưng không ai — kể cả người có token — tính ra được chữ ký hợp lệ cho một payload đã bị sửa nếu không biết khoá bí mật.

Đây là điểm hay bị nhầm nhất khi học JWT lần đầu: "ký" và "mã hoá" là hai việc **khác nhau hoàn toàn**.

| | Mã hoá (encryption) | Ký (signing) — cái JWT làm |
|---|---|---|
| Ai đọc được nội dung? | Chỉ người có khoá giải mã | **Bất kỳ ai** (Base64URL đảo ngược tự do) |
| Mục đích | Giữ **bí mật** | Chứng minh **toàn vẹn** + **nguồn gốc** |
| Sửa nội dung mà không bị phát hiện? | Không đọc được để mà sửa có ý nghĩa | Sửa được payload, nhưng chữ ký cũ sẽ **không khớp** payload mới |

Chứng minh bằng tay, tiếp nối ví dụ decode ở mục 1: giả sử bạn (kẻ tấn công không biết secret key) sửa payload đã decode từ `{"sub":"user-42","role":"admin"}` thành `{"sub":"user-42","role":"superadmin"}`, rồi encode lại thành Base64URL và ghép vào vị trí payload cũ, giữ nguyên chữ ký gốc. Khi server nhận token này, nó tính lại chữ ký từ `Header.<payload mới>` bằng secret key nó có, ra một chuỗi **khác hoàn toàn** so với chữ ký bạn giữ nguyên từ token gốc — server phát hiện ngay và từ chối, **không cần** biết bạn đã sửa gì.

!!! danger "Nếu dùng sai — hậu quả cụ thể"
    Nếu code kiểm token của bạn **bỏ qua** bước kiểm chữ ký (ví dụ tự decode JSON bằng tay để "lấy nhanh" claim mà không gọi qua handler kiểm chữ ký chuẩn), bạn sẽ tin **mọi** payload — kể cả payload bị sửa tuỳ ý bởi client. Đây chính là lỗ hổng nghiêm trọng nhất của JWT khi triển khai sai: kẻ tấn công tự cấp cho mình `"role":"admin"` và server tin ngay vì không ai kiểm chữ ký. Mục 4–5 dùng đúng `JwtSecurityTokenHandler`/`AddJwtBearer`, các API này **luôn** kiểm chữ ký trước khi trả claim — không được tự viết code decode tay để lấy claim trong production.

---

## 4. Cấp token — `JwtSecurityTokenHandler`

**Định nghĩa (một câu):** Cấp token nghĩa là server tạo một `JwtSecurityToken` mới (điền claim, thời hạn, thuật toán ký) rồi dùng `JwtSecurityTokenHandler.WriteToken(...)` để chuyển nó thành chuỗi `Header.Payload.Signature` gửi về client — thường thực hiện ngay sau khi xác thực username/password thành công.

Từng thành phần cần có, đúng thứ tự lắp ráp:

- **`SymmetricSecurityKey`** — bọc secret key (mảng byte) thành object khoá mà thư viện hiểu.
- **`SigningCredentials`** — ghép khoá đó với một thuật toán ký cụ thể (ví dụ `HmacSha256`).
- **Danh sách `Claim`** — các cặp key-value sẽ nằm trong payload (dùng đúng tên chuẩn ở mục 2 khi có thể).
- **`JwtSecurityToken`** — object token hoàn chỉnh: issuer, audience, claims, thời điểm hết hạn, credentials ký.
- **`JwtSecurityTokenHandler().WriteToken(...)`** — serialize object đó thành chuỗi 3 phần thật sự gửi đi.

```csharp title="TokenService.cs"
// test:compile
using System.IdentityModel.Tokens.Jwt;
using System.Security.Claims;
using System.Text;
using Microsoft.IdentityModel.Tokens;

public sealed class TokenService(IConfiguration config)
{
    public string CapToken(string userId, string email)
    {
        // Secret LẤY TỪ CẤU HÌNH (user-secrets / biến môi trường / Key Vault) — KHÔNG hardcode.
        var secret = config["Jwt:Secret"]
            ?? throw new InvalidOperationException("Thiếu Jwt:Secret trong cấu hình");
        var key = new SymmetricSecurityKey(Encoding.UTF8.GetBytes(secret));
        var credentials = new SigningCredentials(key, SecurityAlgorithms.HmacSha256);

        var claims = new[]
        {
            new Claim(JwtRegisteredClaimNames.Sub, userId),
            new Claim(JwtRegisteredClaimNames.Email, email),
            new Claim(JwtRegisteredClaimNames.Jti, Guid.NewGuid().ToString()),
        };

        var token = new JwtSecurityToken(
            issuer: config["Jwt:Issuer"],
            audience: config["Jwt:Audience"],
            claims: claims,
            notBefore: DateTime.UtcNow,
            // DateTime.UtcNow cho exp: JwtSecurityToken tự chuyển giá trị bạn truyền sang UTC
            // trước khi tính "exp" (Unix timestamp giây). DateTime.Now cũng được tự-convert đúng,
            // nhưng UtcNow là thói quen đúng để tránh lỗi DateTimeKind.Unspecified khi giá trị
            // đến từ nguồn khác (DateTime.Parse một chuỗi, hoặc đọc từ DB không kèm Kind).
            expires: DateTime.UtcNow.AddMinutes(15),
            signingCredentials: credentials);

        return new JwtSecurityTokenHandler().WriteToken(token);
    }
}
```

Giải thích từng bước theo đúng thứ tự lắp ráp ở trên: `secret` được đọc từ `IConfiguration` (không hardcode trong source); `key` bọc secret thành `SymmetricSecurityKey`; `credentials` ghép khoá đó với thuật toán `HmacSha256`; `claims` là mảng các claim chuẩn (`sub`, `email`, `jti` — `jti` là ID duy nhất của chính token, hữu ích để thu hồi từng token riêng lẻ); `token` gói tất cả lại kèm `issuer`/`audience`/`notBefore`/`expires`; và `WriteToken` biến object đó thành chuỗi 3 phần thật.

!!! danger "Nếu dùng sai — lỗi cụ thể"
    Nếu secret ngắn hơn 32 byte (256 bit) cho `HmacSha256`, `SigningCredentials` sẽ ném `SecurityTokenInvalidSigningKeyException` với mã lỗi **`IDX10653`** ngay tại thời điểm ký, không phải lúc kiểm — bạn phát hiện lỗi này ngay khi cấp token đầu tiên, không phải khi client gửi token lên. Sinh secret đủ dài bằng `openssl rand -base64 48`, lưu trong `dotnet user-secrets` (dev) hoặc biến môi trường/Key Vault (production) — không bao giờ hardcode chuỗi trong source.

    **Gói NuGet cần:** `Microsoft.AspNetCore.Authentication.JwtBearer` và `System.IdentityModel.Tokens.Jwt` (cả hai đã có sẵn khi `dotnet new web`, chỉ cần `dotnet add package` nếu tạo project trống).

---

## 5. Kiểm token — `AddJwtBearer` + `TokenValidationParameters`

**Định nghĩa (một câu):** Kiểm token nghĩa là, với mỗi request có header `Authorization: Bearer <token>`, ASP.NET Core tự động (qua middleware `UseAuthentication`) tính lại chữ ký, so khớp với chữ ký trong token, và kiểm tra thêm các điều kiện bạn cấu hình trong `TokenValidationParameters` — chỉ khi **tất cả** điều kiện đúng, request mới được coi là đã xác thực.

Mỗi thuộc tính của `TokenValidationParameters` kiểm một điều riêng biệt:

- **`ValidateIssuerSigningKey` / `IssuerSigningKey`** — kiểm chữ ký có khớp khoá bạn cung cấp không. Đây là bước quan trọng nhất (chính là cơ chế chống sửa payload ở mục 3).
- **`ValidateIssuer` / `ValidIssuer`** — kiểm claim `iss` trong token có khớp giá trị bạn kỳ vọng không (chặn token cấp từ hệ thống khác dù ký đúng khoá).
- **`ValidateAudience` / `ValidAudience`** — kiểm claim `aud` có khớp không (chặn token cấp cho API khác bị dùng nhầm ở đây).
- **`ValidateLifetime`** — kiểm `exp` (chưa hết hạn) và `nbf` (đã tới hiệu lực) so với thời gian hiện tại.
- **`ClockSkew`** — độ lệch giờ **cho phép** giữa server cấp token và server kiểm token, khi so `exp`/`nbf` với giờ hệ thống hiện tại.

!!! warning "`ClockSkew` mặc định là 5 phút, KHÔNG PHẢI 0"
    Nếu bạn không set `ClockSkew`, Microsoft.IdentityModel mặc định dùng **5 phút** (`TimeSpan.FromMinutes(5)`), không phải `TimeSpan.Zero` như nhiều người tưởng. Nghĩa là một token có `exp` đã qua **4 phút trước** vẫn được coi là **còn hợp lệ**, vì nằm trong biên độ lệch giờ cho phép. Đây không phải lỗi — là thiết kế chủ ý để bù sai lệch đồng hồ giữa các máy chủ — nhưng nếu bạn viết test kỳ vọng token hết hạn **ngay tức khắc** tại đúng giây `exp`, test sẽ fail một cách khó hiểu vì token "vẫn sống" thêm gần 5 phút. Nếu cần hành vi hết hạn chính xác đến giây (ví dụ trong test), set `ClockSkew = TimeSpan.Zero` tường minh.

```csharp title="Program.cs (trích)"
// test:compile
using System.Text;
using Microsoft.AspNetCore.Authentication.JwtBearer;
using Microsoft.IdentityModel.Tokens;

var builder = WebApplication.CreateBuilder(args);
var jwt = builder.Configuration.GetSection("Jwt");

builder.Services
    .AddAuthentication(JwtBearerDefaults.AuthenticationScheme)
    .AddJwtBearer(options =>
    {
        // Cờ này chỉ chi phối việc TẢI METADATA qua HTTP khi dùng Authority (OIDC).
        // Nó KHÔNG tự ép HTTPS cho traffic mang token — HTTPS truyền tải phải do
        // app.UseHttpsRedirection()/HSTS đảm nhiệm (xem dưới).
        options.RequireHttpsMetadata = !builder.Environment.IsDevelopment();
        options.TokenValidationParameters = new TokenValidationParameters
        {
            ValidateIssuer = true,
            ValidateAudience = true,
            ValidateLifetime = true,
            ValidateIssuerSigningKey = true,
            ValidIssuer = jwt["Issuer"],
            ValidAudience = jwt["Audience"],
            IssuerSigningKey = new SymmetricSecurityKey(
                Encoding.UTF8.GetBytes(jwt["Secret"]!)),
            // Ghim thuật toán -> chống alg-confusion attack (kẻ tấn công đổi header
            // sang thuật toán yếu hơn hoặc "none" để qua mặt kiểm chữ ký).
            ValidAlgorithms = new[] { SecurityAlgorithms.HmacSha256 },
            // Mặc định của thư viện là 5 phút — nêu rõ tường minh để không "bất ngờ"
            // khi viết test hoặc khi cần siết chặt hơn mặc định.
            ClockSkew = TimeSpan.FromSeconds(30),
        };
    });

builder.Services.AddAuthorization();

var app = builder.Build();
app.UseHttpsRedirection();  // ép HTTPS ở tầng truyền tải — RequireHttpsMetadata KHÔNG làm việc này
app.UseAuthentication();    // PHẢI đứng trước UseAuthorization (thứ tự middleware quan trọng)
app.UseAuthorization();
app.Run();
```

!!! danger "Nếu dùng sai — hậu quả cụ thể"
    Nếu bạn set `ValidateIssuerSigningKey = false` (hoặc bỏ hẳn dòng đó và để mặc định sai), ASP.NET Core sẽ chấp nhận **bất kỳ** token có cấu trúc 3 phần đúng hình thức, bất kể chữ ký có khớp hay không — bất kỳ ai tự tạo một token với `"role":"admin"` cũng đăng nhập được. Nếu bạn quên `app.UseAuthentication()` (hoặc đặt nó **sau** `app.UseAuthorization()`), `HttpContext.User` sẽ luôn rỗng ngay cả khi client gửi token hợp lệ — mọi request bị từ chối `401` một cách khó hiểu vì authorization chạy trước khi authentication có cơ hội điền thông tin user.

---

## 6. Refresh token — vì sao cần và lưu ở đâu

**Định nghĩa (một câu):** *Refresh token* là một token **riêng biệt**, sống **lâu hơn** access token (thường vài ngày đến vài tuần) và **không** dùng để gọi API trực tiếp — nó chỉ dùng để đổi lấy một access token mới khi access token cũ hết hạn, mà không buộc người dùng đăng nhập lại bằng username/password.

Vấn đề refresh token giải quyết: access token ở mục 4 sống **ngắn** (15 phút) — đây là chủ ý, không phải thiếu sót. Access token càng ngắn hạn, nếu bị đánh cắp (qua XSS, qua log rò rỉ), kẻ tấn công chỉ lợi dụng được trong khoảng thời gian ngắn đó. Nhưng nếu access token ngắn mà không có gì thay thế, người dùng phải đăng nhập lại (nhập password) mỗi 15 phút — trải nghiệm không chấp nhận được.

| | Access token | Refresh token |
|---|---|---|
| Thời hạn | Ngắn (phút — giờ) | Dài (ngày — tuần) |
| Dùng để | Gửi kèm mỗi request gọi API (`Authorization: Bearer`) | Chỉ gửi tới **một** endpoint riêng (`/auth/refresh`) để đổi access token mới |
| Nếu bị đánh cắp | Kẻ tấn công lợi dụng được trong thời gian ngắn còn lại | Kẻ tấn công lợi dụng được **lâu dài** — vì vậy phải lưu cẩn trọng hơn access token |
| Nơi lưu phía client | Bộ nhớ tạm (biến JS, không persist) | Cookie `HttpOnly` + `Secure` + `SameSite` (JS không đọc được, giảm rủi ro XSS) |

Vì refresh token sống lâu và có quyền "sinh ra" access token mới, nó phải được đối xử như một bí mật quan trọng hơn access token: lưu trong cookie `HttpOnly` (script phía client không đọc được, giảm thiệt hại nếu có XSS), gắn với một bản ghi phía server (để có thể **thu hồi** — vô hiệu hoá một refresh token cụ thể khi người dùng logout hoặc khi phát hiện bị đánh cắp, điều access token dạng JWT thuần *không* làm được vì server không tra cứu gì khi kiểm access token).

!!! danger "Nếu dùng sai — hậu quả cụ thể"
    Nếu bạn cho access token sống **dài** (ví dụ 7 ngày) để "khỏi cần refresh token cho đơn giản", một token bị đánh cắp (qua `localStorage` dính XSS, hoặc lộ trong log) sẽ hợp lệ trong suốt 7 ngày đó — không có cách nào thu hồi một JWT đã phát hành trước khi nó tự hết hạn, vì server không tra cứu gì khi kiểm chữ ký (đó chính là lợi ích "không cần hỏi lại server" ở mục 1, nhưng cũng là cái giá phải trả: **không thu hồi được từng token lẻ**). Ngược lại nếu bạn lưu refresh token trong `localStorage` giống access token, bạn đã xoá bỏ toàn bộ lợi ích của việc tách hai loại token — cùng dính rủi ro XSS, nhưng hậu quả nặng hơn vì refresh token sống lâu hơn nhiều.

---

## Cạm bẫy & bảo mật

- **Hardcode secret trong source code:** secret bị commit vào Git, lộ vĩnh viễn trong lịch sử — dùng `dotnet user-secrets` (dev) hoặc biến môi trường/Key Vault (production).
- **Secret quá ngắn:** dưới 32 byte cho `HmacSha256` ném `IDX10653` ngay lúc ký — sinh bằng `openssl rand -base64 48`.
- **Tưởng JWT được mã hoá:** payload chỉ Base64URL, ai cũng decode đọc được — không bao giờ nhét dữ liệu nhạy cảm (mật khẩu, số thẻ) vào claim.
- **Không set `ValidateIssuerSigningKey`/để sai:** chấp nhận token với chữ ký không khớp — mất hoàn toàn cơ chế chống giả mạo.
- **Quên `ValidAlgorithms`:** không ghim thuật toán mở đường cho alg-confusion attack (kẻ tấn công đổi header `alg` sang giá trị yếu hơn hoặc `none`).
- **Đặt `UseAuthentication()` sau `UseAuthorization()`:** `HttpContext.User` luôn rỗng, mọi request bị `401` dù token hợp lệ — thứ tự middleware sai.
- **Tưởng `ClockSkew` mặc định là 0:** thực tế là 5 phút — token "hết hạn" vẫn sống thêm gần 5 phút, gây nhầm lẫn khi viết test hoặc khi cần siết thời hạn chính xác.
- **Lưu access token dài hạn trong `localStorage` để "đỡ phải làm refresh token":** vừa dính rủi ro XSS, vừa không thể thu hồi khi bị đánh cắp — luôn tách access token ngắn hạn + refresh token dài hạn lưu cookie `HttpOnly`.

---

## Bài tập

**Bài 1 (giàn giáo):** Đoạn `TokenService` sau bị thiếu `notBefore` và đặt `expires` bằng phép tính sai đơn vị (nhân với 1000 tưởng là "an toàn hơn"). Tìm và sửa lỗi.

```csharp title="TokenService.cs (có lỗi)"
// test:compile bai tap 1 - co loi, can sua
using System.IdentityModel.Tokens.Jwt;
using System.Security.Claims;
using System.Text;
using Microsoft.IdentityModel.Tokens;

public sealed class TokenServiceLoi(IConfiguration config)
{
    public string CapToken(string userId)
    {
        var secret = config["Jwt:Secret"]!;
        var key = new SymmetricSecurityKey(Encoding.UTF8.GetBytes(secret));

        var claims = new[] { new Claim(JwtRegisteredClaimNames.Sub, userId) };

        var token = new JwtSecurityToken(
            issuer: config["Jwt:Issuer"],
            audience: config["Jwt:Audience"],
            claims: claims,
            // SAI: nhân 1000 vì nhầm "exp cần millisecond" — exp là Unix timestamp GIÂY.
            expires: DateTime.UtcNow.AddMinutes(15 * 1000),
            signingCredentials: new SigningCredentials(key, SecurityAlgorithms.HmacSha256));

        return new JwtSecurityTokenHandler().WriteToken(token);
    }
}
```

??? success "Lời giải + vì sao"
    ```csharp title="TokenService.cs (đã sửa)"
    // test:compile bai tap 1 - da sua dung
    using System.IdentityModel.Tokens.Jwt;
    using System.Security.Claims;
    using System.Text;
    using Microsoft.IdentityModel.Tokens;

    public sealed class TokenServiceDung(IConfiguration config)
    {
        public string CapToken(string userId)
        {
            var secret = config["Jwt:Secret"]!;
            var key = new SymmetricSecurityKey(Encoding.UTF8.GetBytes(secret));

            var claims = new[] { new Claim(JwtRegisteredClaimNames.Sub, userId) };

            var token = new JwtSecurityToken(
                issuer: config["Jwt:Issuer"],
                audience: config["Jwt:Audience"],
                claims: claims,
                notBefore: DateTime.UtcNow,
                // ĐÚNG: 15 phút thật, không nhân thêm — JwtSecurityToken tự tính ra
                // Unix timestamp giây cho "exp", không cần bạn tự quy đổi đơn vị.
                expires: DateTime.UtcNow.AddMinutes(15),
                signingCredentials: new SigningCredentials(key, SecurityAlgorithms.HmacSha256));

            return new JwtSecurityTokenHandler().WriteToken(token);
        }
    }
    ```

    **Vì sao lỗi gốc nghiêm trọng:** `AddMinutes(15 * 1000)` = 15.000 phút ≈ 10.4 ngày — không phải bug hiển thị, mà là access token sống **10 ngày** thay vì 15 phút dự tính, xoá bỏ toàn bộ lý do access token cần ngắn hạn (mục 6). Lỗi này bắt nguồn từ nhầm lẫn "chắc phải nhân 1000 vì computer hay dùng millisecond" — nhưng `DateTime.AddMinutes` nhận **số phút thật**, không liên quan gì đến đơn vị `exp` bên trong token (đó là việc của `JwtSecurityToken`, tự quy đổi sang Unix timestamp giây khi ghi token).

**Bài 2 (thiết kế):** Thiết kế một `TokenValidationParameters` cho một API có `Issuer = "api-hoc-tap"`, `Audience = "web-client"`, cần siết chặt: không cho phép lệch giờ (dùng để test tự động cần độ chính xác cao), và phải ghim thuật toán `HmacSha256`.

??? success "Lời giải + vì sao"
    ```csharp title="Program.cs (trích)"
    // test:compile bai tap 2 - thiet ke TokenValidationParameters siet chat
    using System.Text;
    using Microsoft.AspNetCore.Authentication.JwtBearer;
    using Microsoft.IdentityModel.Tokens;

    var builder = WebApplication.CreateBuilder(args);

    builder.Services
        .AddAuthentication(JwtBearerDefaults.AuthenticationScheme)
        .AddJwtBearer(options =>
        {
            options.TokenValidationParameters = new TokenValidationParameters
            {
                ValidateIssuer = true,
                ValidateAudience = true,
                ValidateLifetime = true,
                ValidateIssuerSigningKey = true,
                ValidIssuer = "api-hoc-tap",
                ValidAudience = "web-client",
                IssuerSigningKey = new SymmetricSecurityKey(
                    Encoding.UTF8.GetBytes(builder.Configuration["Jwt:Secret"]!)),
                ValidAlgorithms = new[] { SecurityAlgorithms.HmacSha256 },
                // Yêu cầu đề bài: không cho phép lệch giờ, khác mặc định 5 phút của thư viện.
                ClockSkew = TimeSpan.Zero,
            };
        });

    var app = builder.Build();
    app.UseAuthentication();
    app.UseAuthorization();
    app.Run();
    ```

    **Vì sao đúng:** `ValidIssuer`/`ValidAudience` khớp chính xác giá trị đề bài yêu cầu — token cấp cho hệ thống khác (dù ký đúng khoá) sẽ bị từ chối vì `aud`/`iss` không khớp. `ValidAlgorithms` ghim `HmacSha256` — chống alg-confusion. `ClockSkew = TimeSpan.Zero` ghi đè tường minh mặc định 5 phút của thư viện, đáp ứng đúng yêu cầu "không cho phép lệch giờ" — điểm mấu chốt của bài tập là biết mặc định **không phải** 0 nên phải set tường minh khi cần hành vi khác mặc định.

---

## Tự kiểm tra

1. JWT gồm 3 phần nào, và phần nào chứa dữ liệu (claim) mà bất kỳ ai cũng đọc được?

    ??? note "Đáp án"
        `Header.Payload.Signature`. Phần **Payload** — nó chỉ là Base64URL (không phải mã hoá), ai cũng decode đọc được nguyên văn JSON claim bên trong.

2. Đơn vị của claim `exp`/`iat`/`nbf` là gì? Nếu nhét nhầm giá trị millisecond vào đó, hậu quả gì?

    ??? note "Đáp án"
        Unix timestamp tính bằng **giây**. Nếu nhét nhầm millisecond (lớn hơn 1000 lần), thư viện hiểu token hết hạn ở một thời điểm cách xa hàng nghìn năm sau — token coi như không bao giờ hết hạn, một lỗ hổng bảo mật.

3. `ClockSkew` mặc định của `TokenValidationParameters` là bao nhiêu? Vì sao cần biết điều này khi viết test kiểm token hết hạn?

    ??? note "Đáp án"
        Mặc định **5 phút**, không phải 0. Một token hết hạn 4 phút trước vẫn được coi là hợp lệ vì nằm trong biên độ lệch cho phép — test kỳ vọng "hết hạn ngay lập tức" sẽ fail nếu không set `ClockSkew = TimeSpan.Zero` tường minh.

4. Vì sao nói JWT "không mã hoá, chỉ ký"? Nếu một kẻ tấn công sửa claim `role` trong payload rồi gửi lại token, chuyện gì xảy ra khi server kiểm?

    ??? note "Đáp án"
        JWT dùng Base64URL (đảo ngược tự do) cho payload, không dùng thuật toán mã hoá cần khoá giải mã — ai cũng đọc được, đó là "không mã hoá". "Ký" nghĩa là chữ ký phần thứ 3 phụ thuộc toàn bộ vào payload gốc + secret key. Nếu kẻ tấn công sửa payload nhưng giữ chữ ký cũ, server tính lại chữ ký từ payload mới và secret key nó có — kết quả không khớp chữ ký cũ, server phát hiện và từ chối token.

5. Vì sao access token nên sống ngắn (phút) trong khi refresh token sống dài (ngày/tuần)? Refresh token nên lưu ở đâu phía client, và vì sao?

    ??? note "Đáp án"
        Access token ngắn hạn để giảm thiệt hại nếu bị đánh cắp — kẻ tấn công chỉ lợi dụng được trong khoảng thời gian ngắn còn lại trước khi hết hạn. Refresh token cần sống dài để người dùng không phải đăng nhập lại liên tục, nhưng chính vì thế phải lưu trong cookie `HttpOnly` + `Secure` + `SameSite` (script phía client không đọc được) để giảm rủi ro bị đánh cắp qua XSS, đồng thời gắn với bản ghi phía server để có thể thu hồi khi cần.

6. Nếu bạn quên set `ValidateIssuerSigningKey = true` (hoặc set thành `false`), điều gì có thể xảy ra?

    ??? note "Đáp án"
        Server sẽ chấp nhận token bất kể chữ ký có khớp hay không — bất kỳ ai tự tạo một token với claim tuỳ ý (ví dụ `"role":"admin"`) cũng được coi là hợp lệ. Đây là lỗ hổng nghiêm trọng nhất khi cấu hình sai `TokenValidationParameters`.

7. `app.UseAuthentication()` phải đứng trước hay sau `app.UseAuthorization()`? Nếu đặt sai thứ tự, hiện tượng cụ thể là gì?

    ??? note "Đáp án"
        Phải đứng **trước**. Nếu đặt sau, `HttpContext.User` chưa được điền thông tin khi `UseAuthorization()` chạy kiểm tra quyền — mọi request bị trả `401` dù client gửi token hợp lệ, vì lúc đó hệ thống chưa "biết" ai đang gọi.

---

??? abstract "DEEP DIVE — nâng cao (ngoài fast path)"
    - **Alg-confusion attack chi tiết hơn:** một số thư viện JWT cũ (không phải .NET hiện hành) cho phép token khai `"alg":"none"` trong header và bỏ qua kiểm chữ ký hoàn toàn, hoặc đổi từ thuật toán bất đối xứng (RS256, dùng public/private key) sang đối xứng (HS256) rồi dùng chính public key làm secret HS256 — nếu code kiểm không ghim cứng thuật toán mong đợi. `ValidAlgorithms` trong mục 5 là lớp phòng thủ chống chính xác kiểu tấn công này.
    - **Bất đối xứng (RS256/ES256) khi có nhiều dịch vụ:** với hệ thống nhiều microservice, dùng cặp khoá bất đối xứng (private key ký ở nơi cấp token, public key phân phối cho mọi service kiểm) tránh việc mọi service phải cùng giữ một secret đối xứng — giảm bề mặt rò rỉ khoá.
    - **Thu hồi access token trước hạn:** vì kiểm JWT không tra cứu server, muốn "logout ngay" một access token cụ thể cần thêm một danh sách đen (blacklist theo `jti`, lưu Redis với TTL bằng thời gian còn lại của token) — đánh đổi lại một phần lợi ích "không cần hỏi server" để có khả năng thu hồi.
    - **Rotate refresh token:** mỗi lần dùng refresh token để đổi access token mới, cấp luôn một refresh token **mới** và vô hiệu hoá refresh token cũ (refresh token rotation) — nếu một refresh token bị dùng lại sau khi đã rotate, đó là dấu hiệu token đã bị đánh cắp, hệ thống có thể chủ động thu hồi toàn bộ phiên.

Tiếp theo -> tải file an toàn
