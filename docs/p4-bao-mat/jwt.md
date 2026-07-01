---
tier: core
status: core
owner: security-expert
risk_tier: T3            # bảo mật → BẮT BUỘC expert ký + Semgrep xanh mới merge
verified_on: "2026-07-01"
dotnet_version: "10.0"
concept_owner: jwt        # TRANG CANONICAL DUY NHẤT về JWT — nơi khác chỉ được link về đây
bloom: "Apply"
requires: [p3-di]
est_minutes_fast: 20
---

# JWT: Xác thực an toàn (trang canonical)

!!! info "Bạn đang ở đây · P4 → node `p4-jwt` · Rủi ro T3 (bảo mật)"
    **Cần trước:** Dependency Injection *(chương draft — v0.2)*.
    Đây là **nơi duy nhất** giải thích JWT. Mọi bài khác cần JWT phải **link về trang này**, không giải thích lại (chống trùng lặp như bản cũ giải thích JWT ở 4 file).

> **Mục tiêu:** **Áp dụng** cấp/kiểm JWT đúng chuẩn bảo mật trên .NET {{ dotnet.current }} — tránh 4 lỗi phổ biến: dùng giờ local, secret hardcode, thiếu HTTPS, và bỏ qua ClockSkew.

---

## 1. JWT là gì (đủ để dùng)

Một token gồm 3 phần `Header.Payload.Signature` (Base64URL), server ký bằng khoá bí mật. Client gửi kèm `Authorization: Bearer <token>`; server **kiểm chữ ký** để tin payload mà **không cần truy vấn DB** mỗi request.

!!! warning "Đánh đổi bảo mật phải dạy đúng"
    - Cookie → rủi ro **CSRF**.
    - JWT lưu trong `localStorage` → rủi ro **XSS** (token bị đánh cắp qua script). Đây là rủi ro thực tế lớn hơn, tài liệu kém hay bỏ sót. Cân nhắc cookie `HttpOnly`+`SameSite` cho web app.

---

## 2. Cấp token — code ĐÚNG

```csharp title="TokenService.cs"
// test:compile
using System.IdentityModel.Tokens.Jwt;
using System.Security.Claims;
using System.Text;
using Microsoft.IdentityModel.Tokens;

public sealed class TokenService(IConfiguration config)
{
    public string Create(string userId, string email)
    {
        // ✅ Secret LẤY TỪ CẤU HÌNH (env var / user-secrets / Key Vault) — KHÔNG hardcode.
        var secret = config["Jwt:Secret"]
            ?? throw new InvalidOperationException("Thiếu Jwt:Secret");
        var key = new SymmetricSecurityKey(Encoding.UTF8.GetBytes(secret));

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
            // ✅ Dùng UtcNow: exp của JWT là mốc UTC. Giá trị UTC tường minh tránh mọi
            //    mơ hồ về DateTimeKind (xem cảnh báo bên dưới).
            expires: DateTime.UtcNow.AddMinutes(15),
            signingCredentials: new SigningCredentials(key, SecurityAlgorithms.HmacSha256));

        return new JwtSecurityTokenHandler().WriteToken(token);
    }
}
```

!!! warning "Đính chính một hiểu lầm phổ biến về `DateTime.Now`"
    Nhiều tài liệu nói `DateTime.Now.AddMinutes(15)` làm token "lệch 7 giờ" ở VN — **không đúng** với code này. `JwtSecurityToken` tự gọi `ToUniversalTime()` cho giá trị có `Kind=Local`, nên `DateTime.Now` và `DateTime.UtcNow` cho **cùng một `exp`**; token hết hạn đúng lúc trong cả hai trường hợp.

    Bẫy **thật** là `DateTime` có `Kind=Unspecified` (đến từ `DateTime.Parse` một chuỗi, hoặc đọc từ DB không kèm Kind): thư viện coi nó **là UTC** và có thể lệch giờ âm thầm. ⇒ Luôn truyền giá trị **UTC tường minh** (`DateTime.UtcNow`) để không phụ thuộc `Kind` — đó mới là lý do đúng.

!!! danger "Secret phải đủ dài"
    HS256 yêu cầu khoá **≥ 256 bit (32 byte)** entropy cao. `Jwt:Secret` ngắn hơn sẽ ném `IDX10653` lúc ký. Sinh bằng `openssl rand -base64 48` rồi để trong `dotnet user-secrets` / biến môi trường.

    **Gói NuGet cần:** `Microsoft.AspNetCore.Authentication.JwtBearer` và `System.IdentityModel.Tokens.Jwt`.

---

## 3. Kiểm token — cấu hình ĐÚNG trong `Program.cs`

```csharp title="Program.cs (trích)"
// test:compile
using System.Text;
using Microsoft.AspNetCore.Authentication.JwtBearer;
using Microsoft.IdentityModel.Tokens;

var builder = WebApplication.CreateBuilder(args);
var jwt = builder.Configuration.GetSection("Jwt");

builder.Services
    .AddAuthentication(JwtBearerDefaults.AuthenticationScheme)   // ✅ nêu rõ scheme mặc định
    .AddJwtBearer(options =>
    {
        // Lưu ý: cờ này chỉ chi phối việc TẢI METADATA qua HTTP (khi dùng Authority).
        // Nó KHÔNG tự ép HTTPS cho traffic token — HTTPS truyền tải phải do
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
            // ✅ Ghim thuật toán → chống alg-confusion (defense in depth).
            ValidAlgorithms = new[] { SecurityAlgorithms.HmacSha256 },
            // ✅ Mặc định ClockSkew = 5 phút. Nêu rõ để không "bất ngờ" khi test hạn token.
            ClockSkew = TimeSpan.FromSeconds(30),
        };
    });

builder.Services.AddAuthorization();

var app = builder.Build();
app.UseHttpsRedirection();  // ✅ ép HTTPS ở tầng truyền tải (RequireHttpsMetadata KHÔNG làm việc này)
app.UseAuthentication();    // ✅ PHẢI trước UseAuthorization (thứ tự middleware quan trọng)
app.UseAuthorization();
app.Run();
```

!!! tip "Checklist bảo mật (T3 phải xanh hết)"
    - [ ] Secret từ cấu hình, ≥ 32 byte, không nằm trong source (`dotnet user-secrets` khi dev).
    - [ ] `expires` dùng giá trị **UTC tường minh** (`DateTime.UtcNow`).
    - [ ] Ép HTTPS truyền tải bằng `UseHttpsRedirection()`/HSTS ở production.
    - [ ] Ghim thuật toán (`ValidAlgorithms`) + nêu rõ `ClockSkew`.
    - [ ] `UseAuthentication()` đứng **trước** `UseAuthorization()`.

---

## 4. Tự kiểm tra

1. Vì sao nên dùng `DateTime.UtcNow` cho `expires` — và vì sao câu "`DateTime.Now` lệch 7 giờ" là **sai**?
2. JWT trong `localStorage` dính lỗ hổng nào, khác gì cookie?

??? note "Đáp án"
    1. `exp` là mốc UTC. Thư viện tự chuyển `DateTime.Now` (`Kind=Local`) sang UTC nên nó **không** lệch 7 giờ — cho **cùng `exp`** như `UtcNow`. Bẫy thật là `DateTime` `Kind=Unspecified` (từ `Parse`/DB) bị coi là UTC → lệch âm thầm. Dùng `UtcNow` để luôn tường minh, không phụ thuộc `Kind`.
    2. `localStorage` → **XSS** (script chèn được có thể đọc token). Cookie → **CSRF** (nhưng chặn được bằng `SameSite`/anti-forgery, và `HttpOnly` khiến JS không đọc được token).

**Tiếp theo →** Tải file an toàn · Dependency Injection *(các chương draft — mở trong v0.2)*
