---
tier: core
status: core
owner: core-team
verified_on: "2026-07-05"
dotnet_version: "10.0"
bloom: đánh giá
requires: [p7-routing]
est_minutes_fast: 25
---

# Quản lý State: Cascading Parameter & State Container

!!! info "Bạn đang ở đây"
    cần trước: component `.razor` cơ bản, `@page`/routing giữa các trang, `Parameter` truyền dữ liệu cha → con.
    mở khoá: chia sẻ một giá trị (như "ai đang đăng nhập") cho toàn bộ cây con mà không phải truyền qua từng cấp Parameter, và tổ chức một service chứa state chung cho các component không nằm trên cùng một nhánh cây.

> Mục tiêu (đo được): sau chương này bạn **giải thích** được vì sao truyền dữ liệu qua nhiều cấp `Parameter` (prop drilling) không thực tế khi cây component sâu, **viết** được một `CascadingValue` bọc một nhánh cây và một component con đọc giá trị đó qua `[CascadingParameter]`, **viết** được một state container service tối thiểu có event `OnChange` và tiêm nó vào nhiều component độc lập, và **đánh giá** được khi nào dùng Cascading Parameter là đủ so với khi nào cần một state container service.

---

## 0. Đoán nhanh trước khi học

Bạn có cây component sau: `App` chứa `MainLayout`, `MainLayout` chứa `NavMenu` và `<Body>` (nơi hiển thị trang hiện tại), trang hiện tại là `ProductPage`, và `ProductPage` chứa một component con `PriceTag`.

```text title="cay component (hien trang)"
App
 └─ MainLayout
     ├─ NavMenu           <- cần biết tên người dùng đang đăng nhập
     └─ ProductPage
         └─ PriceTag       <- cũng cần biết tên người dùng đang đăng nhập (hiển thị giá riêng cho VIP)
```

Giả sử thông tin "tên người dùng đang đăng nhập" chỉ được `App` biết (lấy từ cookie/token lúc khởi động). Cách duy nhất bạn từng học để đưa dữ liệu xuống là `Parameter` — cha truyền cho con qua thuộc tính đánh dấu `[Parameter]`.

??? question "Câu hỏi: bạn có truyền tên người dùng từ App xuống PriceTag chỉ bằng Parameter không?"
    **Được, nhưng phải truyền qua ĐỦ MỌI cấp trung gian** — `App` truyền `Parameter` cho `MainLayout`, `MainLayout` truyền tiếp cho `ProductPage` (dù `ProductPage` không hề dùng giá trị này, chỉ "chuyển tiếp"), rồi `ProductPage` mới truyền tiếp được cho `PriceTag`. Đây gọi là **prop drilling**: dữ liệu phải "đục xuyên" qua từng cấp component trung gian không liên quan, chỉ để tới được component thực sự cần nó.

    Vấn đề cụ thể: nếu sau này bạn thêm một component `NavMenu` cũng cần tên người dùng (như hình trên), bạn phải sửa **thêm một đường truyền Parameter khác** từ `App` xuống `NavMenu`. Nếu cây có 10 cấp và 5 component rải rác ở các nhánh khác nhau đều cần cùng một giá trị, bạn phải sửa Parameter ở **hàng chục file** trung gian — chỉ để chuyển tiếp một giá trị chúng không dùng. Mục 1 giải quyết đúng vấn đề này cho dữ liệu theo **phạm vi một cây con**; mục 2 giải quyết cho trường hợp các component **không nằm trên cùng nhánh cây** (như `NavMenu` và `PriceTag` ở trên — chúng chỉ có chung tổ tiên `MainLayout`, không phải cha-con trực tiếp với nhau).

---

## 1. `CascadingValue` & `[CascadingParameter]` — định nghĩa và ví dụ tối thiểu

**Định nghĩa (một câu):** `CascadingValue` là một component đặc biệt của Blazor cho phép bạn **chia sẻ một giá trị cho TOÀN BỘ cây con** bên trong nó — mọi component con, con của con, cháu của cháu... đều đọc được giá trị đó qua `[CascadingParameter]` **mà không cần** cha truyền `Parameter` thủ công qua từng cấp trung gian.

Ví dụ tối thiểu, độc lập — một component cha bọc một nhánh cây bằng `CascadingValue`, và một component con đọc giá trị đó:

```razor title="TenDangNhapDemo.razor"
@page "/demo-cascading"

<CascadingValue Value="tenNguoiDung">
    <ThongBaoChaoMung />
</CascadingValue>

@code {
    private string tenNguoiDung = "Lan";
}
```

```razor title="ThongBaoChaoMung.razor"
<p>Xin chào, @TenNguoiDung!</p>

@code {
    // KHÔNG có [Parameter] ở đây — component cha (TenDangNhapDemo) không
    // hề truyền Parameter trực tiếp cho ThongBaoChaoMung trong markup của nó.
    [CascadingParameter]
    public string TenNguoiDung { get; set; } = "";
}
```

Điểm mấu chốt: trong `TenDangNhapDemo.razor`, thẻ `<ThongBaoChaoMung />` **không có** thuộc tính nào truyền `tenNguoiDung` — không giống cách bạn từng viết `<ThongBaoChaoMung Ten="@tenNguoiDung" />` với `[Parameter]` thường. Giá trị `tenNguoiDung` được "thả" vào `CascadingValue`, và **bất kỳ component nào** nằm bên trong cặp thẻ `<CascadingValue>...</CascadingValue>` — dù cách bao nhiêu cấp — chỉ cần khai báo một property đánh dấu `[CascadingParameter]` cùng kiểu dữ liệu (ở đây là `string`) là tự động nhận được giá trị, không cần khai báo lại ở các component trung gian.

!!! danger "Hiểu sai phổ biến: `[CascadingParameter]` tự tìm theo TÊN, không cần `CascadingValue` bao quanh"
    Nếu `ThongBaoChaoMung` được đặt **ngoài** cặp thẻ `<CascadingValue>...</CascadingValue>` (ví dụ ở một nhánh cây khác, hoặc bạn quên bọc `CascadingValue` ở component cha), property đánh dấu `[CascadingParameter]` sẽ **không lỗi biên dịch** — code vẫn build được — nhưng lúc chạy, `TenNguoiDung` sẽ giữ giá trị mặc định của kiểu dữ liệu (`""` với `string`, `null` với kiểu tham chiếu khác, `0` với `int`). Đây là một lỗi runtime âm thầm, khó phát hiện: trang hiển thị "Xin chào, !" (rỗng) mà không có exception nào báo cho bạn biết dây cascading đã bị đứt.

---

## 2. Vấn đề `CascadingValue` KHÔNG giải quyết — component không cùng nhánh cây

Quay lại ví dụ mục 0: `NavMenu` và `PriceTag` **đều** cần tên người dùng, nhưng chúng không nằm trên cùng một nhánh cha-con — `NavMenu` là con của `MainLayout`, còn `PriceTag` là con của `ProductPage` (mà `ProductPage` mới là con của `MainLayout`). Hai component này chỉ có chung **tổ tiên xa** (`MainLayout`), không phải quan hệ cha-con trực tiếp với nhau.

Về lý thuyết, bạn **có thể** đặt `CascadingValue` ở `MainLayout` (tổ tiên chung gần nhất) để cả hai đều nhận được — cách này vẫn dùng đúng mục 1. Nhưng `CascadingValue` bắt đầu bộc lộ hạn chế rõ khi dữ liệu có thêm hai đặc điểm sau, thường gặp trong ứng dụng thật:

1. **Dữ liệu cần được SỬA từ một component con** rồi thông báo ngược lại cho các component khác cùng đọc dữ liệu đó cập nhật theo. Ví dụ: một giỏ hàng (cart) — `PriceTag` không sửa giỏ hàng, nhưng một component `AddToCartButton` (ở một nhánh cây khác) cần **thêm sản phẩm vào giỏ**, và một component `CartBadge` trên `NavMenu` (ở nhánh cây khác nữa) cần **tự cập nhật số lượng hiển thị** ngay khi giỏ hàng thay đổi — mà không có quan hệ cha-con nào giữa `AddToCartButton` và `CartBadge`.
2. **Nhiều nơi không liên quan cây UI cùng cần đọc/sửa dữ liệu**, và bạn không muốn phải "đặt đúng vị trí" `CascadingValue` ở một tổ tiên chung nào đó mỗi khi thêm một component mới cần dữ liệu này — cấu trúc cây UI có thể đổi (refactor layout) mà không nên ảnh hưởng tới việc chia sẻ dữ liệu.

`CascadingValue` được thiết kế cho dữ liệu **đi theo phạm vi cây UI** (theme, văn hoá/ngôn ngữ hiển thị, thông tin xác thực chỉ-đọc cho một nhánh) — nó không có cơ chế "thông báo thay đổi" (event) tách biệt khỏi việc re-render component cha. Mục 3 giới thiệu một cách khác, giải quyết đúng hai đặc điểm trên: **state container service**.

---

## 3. State container service — định nghĩa và ví dụ tối thiểu

**Định nghĩa (một câu):** State container service là một **service C# thường** (không phải component `.razor`) được đăng ký vào DI container với lifetime `Scoped` hoặc `Singleton`, chứa dữ liệu chung (state) cùng một **event C#** để thông báo khi dữ liệu thay đổi — các component tiêm (`@inject`) service này vào, đọc dữ liệu trực tiếp qua property/method của service, và **đăng ký lắng nghe** (subscribe) event đó để tự `StateHasChanged()` khi dữ liệu đổi ở nơi khác.

Ví dụ tối thiểu, độc lập — một `CartState` service với event `OnChange`:

```csharp title="CartState.cs"
// test:run
// (Đây là service C# thuần — KHÔNG phải component .razor, không có HTML/@code,
// nên fence là csharp, không phải razor. Test chạy độc lập, không cần DI container
// hay Blazor thật, chỉ chứng minh đúng hành vi của class CartState.)
// --- Top-level statement PHẢI đứng trước mọi khai báo class/interface trong file .cs ---
var cart = new CartState();
var soLanDuocGoi = 0;

// Mô phỏng một component "subscribe" vào OnChange, giống @code trong .razor.
cart.OnChange += () => soLanDuocGoi++;

cart.ThemSanPham("Ban phim");
cart.ThemSanPham("Chuot");

Console.WriteLine($"So san pham trong cart: {cart.SanPham.Count}");
Console.WriteLine($"So lan OnChange duoc goi: {soLanDuocGoi}");

if (cart.SanPham.Count != 2) throw new Exception("Test FAIL: so san pham sai");
if (soLanDuocGoi != 2) throw new Exception("Test FAIL: OnChange phai duoc goi dung 2 lan");
Console.WriteLine("Test PASS");

public sealed class CartState
{
    private readonly List<string> _sanPham = new();

    public IReadOnlyList<string> SanPham => _sanPham;

    // Event C# thường — bất kỳ ai subscribe đều được gọi khi state đổi.
    public event Action? OnChange;

    public void ThemSanPham(string ten)
    {
        _sanPham.Add(ten);
        OnChange?.Invoke(); // thông báo cho MỌI component đang lắng nghe
    }
}
```

Kết quả kỳ vọng khi chạy:

```text title="output"
So san pham trong cart: 2
So lan OnChange duoc goi: 2
Test PASS
```

Đăng ký `CartState` vào DI container (thường ở `Program.cs`), rồi tiêm vào hai component **không cùng nhánh cây** — đúng vấn đề mục 2 nêu ra:

```csharp title="Program.cs (trich - dang ky CartState)"
// test:compile
// (Trích đoạn — minh hoạ đúng MỘT dòng đăng ký DI cần thêm, không phải file đầy đủ.
// Chỉ dùng API có sẵn trong Web SDK trần - KHÔNG using namespace Blazor riêng,
// vì project test CI là "dotnet new web", chưa cài package Blazor Components.)
var builder = WebApplication.CreateBuilder(args);

// Scoped: mỗi người dùng (Blazor Server, mỗi kết nối SignalR) hoặc mỗi lần tải
// lại trang (Blazor WebAssembly) có MỘT CartState riêng — không lẫn giỏ hàng
// giữa hai người dùng khác nhau.
builder.Services.AddScoped<CartState>();

var app = builder.Build();
app.Run();

public sealed class CartState
{
    public event Action? OnChange;
}
```

```razor title="AddToCartButton.razor"
@inject CartState Cart

<button @onclick="ThemVaoGio">Thêm vào giỏ</button>

@code {
    private void ThemVaoGio()
    {
        Cart.ThemSanPham("Ban phim");
        // KHÔNG cần gọi StateHasChanged() ở ĐÂY — component này không hiển thị
        // số lượng giỏ hàng, chỉ SỬA state. Component NÀO đọc và hiển thị mới
        // cần lắng nghe OnChange (xem CartBadge.razor bên dưới).
    }
}
```

```razor title="CartBadge.razor"
@implements IDisposable
@inject CartState Cart

<span>Giỏ hàng: @Cart.SanPham.Count</span>

@code {
    protected override void OnInitialized()
    {
        // Đăng ký lắng nghe: MỖI KHI AddToCartButton (ở nhánh cây KHÁC) gọi
        // ThemSanPham(), OnChange bắn ra, và dòng này chạy để vẽ lại số mới.
        Cart.OnChange += CapNhatLai;
    }

    private void CapNhatLai() => InvokeAsync(StateHasChanged);

    // Huỷ đăng ký khi component bị loại khỏi cây - xem "Cạm bẫy" cuối bài
    // để hiểu TẠI SAO bỏ qua bước này gây memory leak.
    public void Dispose() => Cart.OnChange -= CapNhatLai;
}
```

`AddToCartButton` và `CartBadge` **không có quan hệ cha-con** nào — chúng có thể nằm ở hai nhánh hoàn toàn khác nhau của cây component (đúng như `NavMenu`/`PriceTag` ở mục 0). Cả hai chỉ cùng tiêm (`@inject`) **một instance `CartState` giống nhau** (vì lifetime `Scoped` — cùng một người dùng luôn nhận lại đúng instance đó từ DI container). Khi `AddToCartButton` gọi `Cart.ThemSanPham(...)`, event `OnChange` bắn ra, và `CartBadge` — dù ở bất kỳ đâu trong cây, miễn đã subscribe — tự cập nhật hiển thị.

!!! warning "Vì sao gọi `InvokeAsync(StateHasChanged)` mà không gọi `StateHasChanged()` trực tiếp"
    `OnChange` có thể được bắn ra từ một luồng (thread) không phải luồng UI của Blazor đang render (ví dụ nếu `ThemSanPham` được gọi từ một callback bất đồng bộ, timer, hoặc SignalR message ở Blazor Server). Gọi `StateHasChanged()` trực tiếp từ luồng khác luồng UI có thể ném lỗi hoặc gây hành vi render không nhất quán. `InvokeAsync(...)` đảm bảo đoạn code bên trong (`StateHasChanged`) luôn chạy đúng trên luồng đồng bộ hoá của Blazor (giống `Dispatcher.Invoke` trong WPF hoặc `runOnUiThread` trong Android) — an toàn trong mọi trường hợp, dù đôi khi (gọi từ chính một sự kiện UI như `@onclick`) không bắt buộc phải bọc `InvokeAsync`.

---

## 3b. Tại sao không dùng biến `static` thay cho state container service

Trước khi đi sâu hơn, cần loại bỏ một cách "tắt" mà nhiều người mới học Blazor nghĩ tới đầu tiên: khai báo một biến `static` chứa state chung, thay vì viết một service đăng ký DI như mục 3. Nhìn qua, biến `static` cũng cho phép nhiều component đọc/sửa cùng một dữ liệu mà không cần Parameter — vậy tại sao mục 3 không dùng cách này?

```csharp title="CartStateTinh.cs (KHONG nen dung - minh hoa van de)"
// test:skip minh hoa van de - khong phai giai phap dung, chi de doi chieu
public static class CartStateTinh
{
    // static -> CHỈ MỘT bản ghi nhớ duy nhất cho TOÀN BỘ ứng dụng,
    // dùng chung bởi MỌI người dùng đang truy cập cùng lúc.
    public static List<string> SanPham { get; } = new();
}
```

**Vấn đề cụ thể:** một biến `static` sống ở cấp độ `AppDomain`/process .NET — nó không biết gì về khái niệm "một người dùng" hay "một phiên làm việc". Trong Blazor Server, nếu người dùng A và người dùng B cùng mở ứng dụng (hai kết nối SignalR khác nhau, chạy trên cùng một process server), cả hai **đọc và ghi vào đúng CÙNG MỘT** `CartStateTinh.SanPham` — người dùng A thêm sản phẩm vào giỏ, người dùng B lập tức nhìn thấy sản phẩm đó trong giỏ của mình, dù họ chưa từng thêm gì. Đây là lỗi rò rỉ dữ liệu nghiêm trọng giữa hai người dùng khác nhau, không phải hành vi "may mắn không xảy ra" — nó **luôn** xảy ra khi có từ hai người dùng cùng lúc.

So sánh với `CartState` (mục 3) đăng ký `AddScoped<CartState>()`: DI container tự tạo **một instance riêng cho mỗi Scoped** (mỗi kết nối SignalR ở Blazor Server, tương ứng một người dùng) — người dùng A và người dùng B nhận về hai instance `CartState` hoàn toàn khác nhau, dù cùng là class `CartState`. Đây là lý do state container service **phải** đi kèm đăng ký DI với lifetime đúng, không phải chỉ là "một class chứa state chung" bất kỳ.

!!! danger "`static` chỉ an toàn khi dữ liệu THẬT SỰ chung cho mọi người dùng"
    Có những trường hợp `static` (hoặc `Singleton` — về bản chất tương tự, chỉ khác cách quản lý vòng đời qua DI container) là **đúng**: ví dụ một cache cấu hình đọc từ file, danh sách tỉnh/thành cố định, hoặc một bộ đếm tổng số request toàn hệ thống — những dữ liệu này **nên** chung cho mọi người dùng. Vấn đề chỉ xảy ra khi dùng `static`/`Singleton` cho dữ liệu **riêng theo người dùng** (giỏ hàng, thông tin đăng nhập, filter đang chọn) — đúng loại lỗi bài này đang cảnh báo. Mục 5 và phần "Cạm bẫy" cuối bài nhắc lại chi tiết này ở góc nhìn lifetime DI (`Scoped` vs `Singleton`).

---

## 4. Nếu quên `Dispose` — memory leak cụ thể

Đoạn code mục 3 có dòng `Cart.OnChange -= CapNhatLai;` trong `Dispose()`. Nếu bạn **xoá dòng này** (hoặc quên implement `IDisposable` hoàn toàn), điều gì xảy ra cụ thể?

```razor title="CartBadge.razor (THIEU Dispose - co van de)"
@inject CartState Cart

<span>Giỏ hàng: @Cart.SanPham.Count</span>

@code {
    protected override void OnInitialized()
    {
        Cart.OnChange += CapNhatLai; // đăng ký...
    }

    private void CapNhatLai() => InvokeAsync(StateHasChanged);

    // ...KHÔNG CÓ Dispose() nào huỷ đăng ký này.
}
```

Kịch bản cụ thể gây lỗi: người dùng điều hướng qua lại giữa trang có `CartBadge` và trang khác nhiều lần (ví dụ 20 lần). Mỗi lần `CartBadge` được tạo lại (component mới), `OnInitialized()` chạy lại, thêm **một** đăng ký `CapNhatLai` mới vào `Cart.OnChange` — nhưng vì `CartState` có lifetime `Scoped` (sống suốt phiên người dùng, không mất khi rời trang), nó **giữ lại tham chiếu tới TẤT CẢ 20 instance `CartBadge` cũ** thông qua danh sách delegate bên trong `OnChange` — dù các `CartBadge` cũ đó đã bị Blazor loại khỏi cây UI từ lâu, garbage collector **không thể** thu hồi bộ nhớ của chúng vì `Cart.OnChange` vẫn còn giữ tham chiếu sống tới chúng. Đây chính là memory leak.

Hậu quả quan sát được: (1) bộ nhớ tăng dần theo số lần điều hướng, không giảm; (2) mỗi lần `ThemSanPham` được gọi, `CapUpdate` chạy **20 lần** thay vì 1 lần — 19 lần trong số đó gọi `StateHasChanged()` trên các component đã "chết" (không còn trên màn hình), gây lãng phí CPU và có thể ném `ObjectDisposedException` tuỳ phiên bản Blazor nếu component cố render lại phần UI đã bị gỡ.

!!! danger "Dấu hiệu nhận ra memory leak dạng này khi debug"
    Nếu bạn thêm một `Console.WriteLine` trong `CapNhatLai()` và thấy số lần in ra **tăng dần** mỗi lần bạn thao tác thêm-vào-giỏ, dù số component `CartBadge` đang hiển thị trên màn hình không đổi (luôn là 1) — đó chính xác là dấu hiệu của việc quên `Dispose()`/huỷ đăng ký event. Cách sửa duy nhất đúng: implement `IDisposable`, huỷ đăng ký (`-=`) đúng delegate đã đăng ký (`+=`) trong `Dispose()`, như ví dụ mục 3.

---

## 5. Khi nào dùng Cascading Parameter vs. khi nào dùng State container service

Sau khi đã thấy cả hai cơ chế và hậu quả cụ thể khi dùng sai, đây là tiêu chí quyết định thực dụng:

| | `CascadingValue`/`[CascadingParameter]` | State container service (`CartState`...) |
|---|---|---|
| Phạm vi chia sẻ | Một **cây con** cụ thể (từ nơi đặt `CascadingValue` xuống) | Toàn ứng dụng — bất kỳ component nào tiêm được service, không phụ thuộc vị trí trong cây |
| Tần suất dữ liệu đổi | Ít đổi (theme, ngôn ngữ hiển thị, thông tin xác thực chỉ-đọc) | Đổi thường xuyên, do hành động người dùng (thêm vào giỏ, cập nhật trạng thái) |
| Cần thông báo ngược (event) khi đổi? | Không có cơ chế riêng — dựa vào re-render tự nhiên của component cha giữ giá trị | Có — event C# (`OnChange`) cho phép nhiều nơi độc lập tự cập nhật |
| Component liên quan có cùng nhánh cây không? | Phải cùng nhánh (con/cháu của nơi đặt `CascadingValue`) | Không cần — inject service ở bất kỳ đâu, không phụ thuộc cấu trúc cây UI |
| Chi phí thiết lập | Thấp — chỉ 1 component bọc + `[CascadingParameter]` ở nơi cần | Cần đăng ký DI, viết class service, mỗi component đọc phải tự subscribe/unsubscribe đúng (rủi ro memory leak nếu quên) |
| Ví dụ thực tế | Theme (sáng/tối) áp cho toàn bộ trang, thông tin văn hoá (locale) cho một khu vực UI | Giỏ hàng, trạng thái đăng nhập cần cập nhật UI ngay khi đổi, thông báo (notification) toàn cục |

Quy tắc thực dụng ngắn: nếu dữ liệu **ít đổi** và mọi component cần nó đều **nằm trong một cây con rõ ràng**, dùng `CascadingValue` — chi phí thấp, không cần quản lý subscribe/unsubscribe. Nếu dữ liệu **đổi thường xuyên do hành động người dùng** và các component cần nó **rải rác không theo cấu trúc cây** (đúng vấn đề mục 2 nêu ra), dùng state container service — chấp nhận chi phí cao hơn (phải nhớ `Dispose()`) để đổi lại khả năng thông báo chủ động và không bị ràng buộc theo cây UI.

!!! warning "Hai cơ chế không loại trừ nhau — có thể dùng CẢ HAI trong một ứng dụng"
    Một ứng dụng Blazor thực tế thường dùng `CascadingValue` cho theme/xác thực (thông tin `AuthenticationStateProvider` cung cấp thực chất cũng cascade xuống toàn cây qua `CascadingAuthenticationState`/`AuthorizeView`) **và** dùng một hoặc vài state container service cho giỏ hàng, thông báo, trạng thái filter đang chọn. Không có quy tắc "chỉ chọn một cách cho toàn app" — quyết định theo **từng loại dữ liệu**, dựa vào bảng trên.

---

## 6. Ví dụ tổng hợp — dùng CẢ HAI cơ chế trong cùng một ứng dụng nhỏ

Mục này ghép lại mọi khái niệm đã học (mục 1, 3, 5) vào một ví dụ liền mạch, gần với một ứng dụng thật hơn: một trang bán hàng có (a) tên người dùng đang đăng nhập — dữ liệu ít đổi, dùng `CascadingValue`; và (b) giỏ hàng — dữ liệu đổi thường xuyên, dùng state container service.

```csharp title="CartState.cs (ban day du hon, dung lai o muc 6)"
// test:run
// --- Top-level statement PHẢI đứng trước mọi khai báo class/interface trong file .cs ---
var cart = new CartState();
var lanCapNhatCuoi = "";

// Mô phỏng HAI "component" độc lập subscribe cùng một CartState -
// giống AddToCartButton (ghi) và CartBadge (đọc + subscribe) ở mục 3.
cart.OnChange += () => lanCapNhatCuoi = $"Da co {cart.SoLuong} san pham, tong {cart.TongTien:N0}d";

cart.Them("Ban phim", 250_000m);
Console.WriteLine(lanCapNhatCuoi);

cart.Them("Chuot", 150_000m);
Console.WriteLine(lanCapNhatCuoi);

if (cart.SoLuong != 2) throw new Exception("Test FAIL: so luong sai");
if (cart.TongTien != 400_000m) throw new Exception("Test FAIL: tong tien sai");
Console.WriteLine("Test PASS");

public sealed class CartState
{
    private readonly List<(string Ten, decimal Gia)> _items = new();

    public int SoLuong => _items.Count;
    public decimal TongTien => _items.Sum(i => i.Gia);

    public event Action? OnChange;

    public void Them(string ten, decimal gia)
    {
        _items.Add((ten, gia));
        OnChange?.Invoke();
    }
}
```

Kết quả kỳ vọng:

```text title="output"
Da co 1 san pham, tong 250,000d
Da co 2 san pham, tong 400,000d
Test PASS
```

Phần Razor tương ứng — `MainLayout` cascading tên người dùng, `NavMenu` (đọc cascading + hiển thị giỏ hàng qua state container), và `ProductPage` (nút thêm vào giỏ, không cùng nhánh với `NavMenu`):

```razor title="MainLayout.razor (tong hop)"
@inherits LayoutComponentBase

<CascadingValue Value="tenNguoiDung">
    <NavMenu />
    <div class="content">
        @Body
    </div>
</CascadingValue>

@code {
    // Trong ứng dụng thật, giá trị này thường lấy từ AuthenticationStateProvider
    // ở OnInitializedAsync — ở đây gán cứng để giữ ví dụ độc lập, tập trung
    // đúng vào CascadingValue, không trộn thêm khái niệm xác thực (auth) mới.
    private string tenNguoiDung = "Lan";
}
```

```razor title="NavMenu.razor (tong hop)"
@implements IDisposable
@inject CartState Cart

<p>Xin chào, @TenNguoiDung — Giỏ hàng: @Cart.SoLuong sản phẩm (@Cart.TongTien.ToString("N0")đ)</p>

@code {
    // (a) đọc dữ liệu ÍT ĐỔI qua CascadingValue - không cần subscribe/Dispose.
    [CascadingParameter]
    public string TenNguoiDung { get; set; } = "";

    // (b) đọc dữ liệu ĐỔI THƯỜNG XUYÊN qua state container - PHẢI subscribe + Dispose.
    protected override void OnInitialized() => Cart.OnChange += CapNhat;
    private void CapNhat() => InvokeAsync(StateHasChanged);
    public void Dispose() => Cart.OnChange -= CapNhat;
}
```

```razor title="ProductPage.razor (tong hop)"
@page "/san-pham"
@inject CartState Cart

<button @onclick='() => Cart.Them("Ban phim", 250_000m)'>Thêm Bàn phím vào giỏ</button>

@code {
    // Component này KHÔNG cần [CascadingParameter] TenNguoiDung (không hiển thị nó),
    // và KHÔNG cần subscribe OnChange (chỉ GHI vào Cart, không đọc/hiển thị số lượng).
}
```

Quan sát mấu chốt để phân biệt rõ hai cơ chế trong cùng một ví dụ: `NavMenu` dùng **cả hai** — `TenNguoiDung` qua `[CascadingParameter]` (không cần `Dispose`, vì cascading không có subscribe) và `Cart` qua `@inject` + subscribe `OnChange` (bắt buộc `Dispose`, vì có subscribe event). `ProductPage` chỉ cần `@inject CartState` để **ghi** — nó không hiển thị số lượng giỏ hàng nên không cần subscribe gì cả. Đây chính là điểm khác biệt cốt lõi mục 3 đã nêu: chỉ component nào **đọc và hiển thị** dữ liệu thay đổi mới cần subscribe `OnChange`; component chỉ **ghi** (như `ProductPage`) không cần.

!!! note "Vì sao `ProductPage` không cần cascading `TenNguoiDung` trong ví dụ này"
    Đây không phải thiếu sót — `ProductPage` trong ví dụ này không hiển thị gì liên quan tên người dùng, nên không khai báo `[CascadingParameter]`. Nếu sau này `ProductPage` (hoặc bất kỳ component con nào của nó) cần hiển thị "Xin chào, {tên}" khi thêm hàng thành công, chỉ cần thêm đúng property `[CascadingParameter]` — vì `ProductPage` cũng nằm trong `@Body`, tức bên trong `CascadingValue` của `MainLayout`, giá trị đã sẵn ở đó, không cần sửa gì ở `MainLayout` hay các component trung gian khác.

---

## 7. Chi phí re-render của `CascadingValue` — vì sao không nên dùng cho dữ liệu đổi liên tục

Mục 2 đã nói ngắn: `CascadingValue` "không có cơ chế thông báo thay đổi tách biệt khỏi việc re-render component cha". Mục này giải thích cụ thể cơ chế đó, và vì sao nó ảnh hưởng tới quyết định chọn cơ chế ở mục 5.

**Định nghĩa (một câu) — hành vi re-render mặc định của `CascadingValue`:** mỗi khi giá trị được truyền vào thuộc tính `Value` của `CascadingValue` thay đổi (component cha gọi `StateHasChanged()` sau khi sửa biến đó), Blazor mặc định **re-render lại toàn bộ cây con** nằm bên trong `CascadingValue` đó — không chỉ riêng những component thực sự đọc giá trị qua `[CascadingParameter]`, mà cả những component con khác không liên quan đến giá trị này cũng bị buộc render lại theo.

Ví dụ tối thiểu minh hoạ hậu quả — nếu bạn (sai) dùng `CascadingValue` để chia sẻ số lượng giỏ hàng (dữ liệu đổi liên tục, đúng loại mục 2/5 đã cảnh báo không nên dùng cascading):

```razor title="MainLayout.razor (SAI - dung CascadingValue cho du lieu doi lien tuc)"
@inherits LayoutComponentBase

<CascadingValue Value="soLuongGioHang">
    <NavMenu />          @* Component A: THỰC SỰ cần hiển thị soLuongGioHang *@
    <BannerKhuyenMai />  @* Component B: KHÔNG liên quan gì đến giỏ hàng *@
    <div class="content">
        @Body            @* Component C, D, E...: cũng KHÔNG liên quan *@
    </div>
</CascadingValue>

@code {
    private int soLuongGioHang = 0;

    // Giả sử phương thức này được gọi mỗi khi người dùng thêm sản phẩm
    // (ví dụ qua một callback từ ProductPage) - đổi liên tục theo hành động dùng.
    private void CapNhatGioHang(int soLuongMoi)
    {
        soLuongGioHang = soLuongMoi;
        // StateHasChanged() ở ĐÂY khiến CascadingValue re-render lại
        // TOÀN BỘ nhánh cây bên trong - kể cả BannerKhuyenMai và mọi thứ
        // trong @Body không hề đọc soLuongGioHang.
        StateHasChanged();
    }
}
```

**Hậu quả cụ thể:** mỗi lần người dùng thêm một sản phẩm (có thể xảy ra nhiều lần liên tiếp khi họ mua sắm), `BannerKhuyenMai` và toàn bộ cây con trong `@Body` (có thể là một trang phức tạp với hàng chục component) đều bị Blazor tính toán lại (diff lại render tree) — dù nội dung của chúng **không hề thay đổi**. Với một trang nhỏ, chi phí này không đáng kể; với một trang lớn (bảng dữ liệu nhiều dòng, nhiều biểu đồ), người dùng có thể cảm nhận được độ trễ (giật, chậm phản hồi) mỗi lần thêm sản phẩm — dù về mặt hiển thị, chỉ có phần số lượng giỏ hàng ở `NavMenu` thực sự cần đổi.

So sánh với dùng state container service (đúng như mục 3/5 khuyến nghị cho dữ liệu đổi liên tục): chỉ component **đã subscribe** `OnChange` (như `NavMenu` — xem lại mục 3, 6) mới gọi `StateHasChanged()` cho chính nó. `BannerKhuyenMai` không tiêm `CartState`, không subscribe gì, nên hoàn toàn không bị ảnh hưởng, không render lại — đây chính là lợi ích hiệu năng cụ thể giải thích tại sao mục 5 xếp "dữ liệu đổi thường xuyên" vào cột state container service, không phải chỉ là một quy tắc suông.

!!! warning "`IsFixed=\"true\"` không phải cách sửa vấn đề này"
    Bạn có thể nghĩ đặt `IsFixed="true"` trên `CascadingValue` sẽ giảm chi phí re-render — đúng, nhưng `IsFixed="true"` báo cho Blazor biết **giá trị sẽ không đổi sau lần render đầu tiên**, nghĩa là dùng nó cho `soLuongGioHang` (một giá trị **cố ý** đổi liên tục) sẽ khiến các component con **không bao giờ nhận được giá trị mới** — `NavMenu` sẽ hiển thị số lượng giỏ hàng sai (đứng yên ở giá trị lúc render đầu). `IsFixed="true"` chỉ đúng cho giá trị thực sự tĩnh sau khi component cha khởi tạo (xem thêm ở DEEP DIVE cuối bài) — không phải một "công tắc tối ưu" dùng được cho mọi `CascadingValue`.

---

## 8. State container nên đóng gói dữ liệu — không để `List<T>`/setter công khai bị sửa từ ngoài

Mọi ví dụ `CartState` từ mục 3 đến mục 6 đều expose dữ liệu qua property **chỉ đọc** (`IReadOnlyList<string> SanPham`, hoặc `int SoLuong`/`decimal TongTien` tính toán qua `get`-only) và chỉ cho sửa qua **method** (`Them(...)`). Mục này giải thích tại sao thiết kế này quan trọng, không phải ngẫu nhiên.

**Định nghĩa (một câu) — đóng gói (encapsulation) trong state container:** là nguyên tắc chỉ cho phép sửa state của service **thông qua các method công khai của chính service đó** (nơi có thể gọi `OnChange?.Invoke()` sau khi sửa), tuyệt đối không expose trực tiếp collection có thể sửa (`List<T>` public, `set` công khai) ra ngoài, vì bất kỳ đoạn code ngoài service — nằm trong một component `.razor` bất kỳ — sửa trực tiếp vào collection đó sẽ làm state đổi mà **không có ai gọi `OnChange`**, khiến các component khác đang subscribe không hề biết để cập nhật UI.

Ví dụ cụ thể lỗi này xảy ra nếu thiết kế `CartState` sai — expose `List<string>` công khai, sửa được từ ngoài:

```csharp title="CartStateSai.cs (SAI - expose List co the sua tu ngoai)"
// test:skip minh hoa van de - khong nen viet the nay
public sealed class CartStateSai
{
    // SAI: List<string> công khai (public), AI CŨNG sửa được trực tiếp
    // (Add/Remove/Clear) mà không đi qua method nào của CartStateSai.
    public List<string> SanPham { get; } = new();

    public event Action? OnChange;

    public void Them(string ten)
    {
        SanPham.Add(ten);
        OnChange?.Invoke(); // chỉ được gọi khi sửa qua METHOD này
    }
}
```

```razor title="MotComponentBatKy.razor (loi ro rang nhung KHONG bi bao)"
@inject CartStateSai Cart

<button @onclick="ThemLen">Thêm lén, không qua Them()</button>

@code {
    private void ThemLen()
    {
        // Sửa TRỰC TIẾP vào List công khai - KHÔNG gọi Cart.Them(...).
        // Biên dịch OK (SanPham là List<string> public, Add() luôn hợp lệ),
        // nhưng OnChange KHÔNG được bắn - mọi component khác đang subscribe
        // (như CartBadge ở mục 3) sẽ KHÔNG cập nhật UI, dù dữ liệu đã đổi.
        Cart.SanPham.Add("San pham lach luat");
    }
}
```

**Hậu quả cụ thể:** sản phẩm vẫn được thêm vào (`Cart.SanPham.Count` tăng lên thật), nhưng `CartBadge` (hoặc bất kỳ component nào subscribe `OnChange`) sẽ **không** re-render, vì không ai gọi `OnChange?.Invoke()` — số lượng hiển thị trên UI vẫn cũ, sai lệch với dữ liệu thật trong bộ nhớ. Đây là một lỗi runtime rất khó phát hiện: không exception, không lỗi biên dịch, chỉ là "UI không cập nhật đúng lúc" — dễ bị nhầm là lỗi ở nơi khác (như tưởng `CartBadge` quên subscribe).

Cách sửa đúng — như `CartState` gốc ở mục 3: expose `IReadOnlyList<string>` (không có `Add`/`Remove`/`Clear` nào khả dụng từ ngoài — interface này chỉ đọc), và cách **duy nhất** để thêm dữ liệu là gọi method `Them(...)` của service — method này đảm bảo **luôn** gọi `OnChange` ngay sau khi sửa dữ liệu, không có đường tắt nào bỏ qua bước thông báo.

!!! danger "`IReadOnlyList<T>` chỉ chặn được lời gọi qua INTERFACE đó — không tạo bản sao"
    Cần hiểu đúng: `IReadOnlyList<string> SanPham => _sanPham;` không tạo ra một **bản sao** dữ liệu — nó chỉ trả về **cùng một** `List<string>` bên dưới, nhưng thông qua một kiểu tham chiếu (interface) không có method sửa đổi. Nếu code gọi cố tình ép kiểu ngược (`(List<string>)Cart.SanPham`) rồi gọi `Add()` trên đó, C# **cho phép** (vì bản chất vẫn là cùng một `List<string>`), và lỗi ở trên vẫn xảy ra. `IReadOnlyList<T>` là một hàng rào **quy ước tốt** (che method sửa khỏi IntelliSense/API công khai, khiến lập trình viên khác khó vô tình gọi sai), không phải một hàng rào **bảo mật tuyệt đối** chống ép kiểu cố ý — nhưng trong thực tế, việc ép kiểu ngược để "lách" là rất hiếm vì không ai làm vậy một cách tình cờ.

---

## Cạm bẫy & thực chiến

- **Dùng `CascadingValue` cho dữ liệu đổi liên tục (như số lượng giỏ hàng):** mỗi lần giá trị `CascadingValue` đổi, Blazor re-render **toàn bộ cây con** bên trong nó theo mặc định (trừ khi bạn tối ưu bằng `IsFixed="true"` — chỉ dùng khi chắc chắn giá trị không đổi sau lần render đầu). Với dữ liệu đổi thường xuyên, việc này gây re-render dư thừa nhiều component không thực sự cần cập nhật — dùng state container service với subscribe có chọn lọc (chỉ component thực sự hiển thị dữ liệu mới subscribe) hiệu quả hơn.
- **Quên huỷ đăng ký `OnChange` trong `Dispose()`:** gây memory leak và gọi callback trên component đã bị gỡ khỏi cây, như mục 4 đã chỉ ra cụ thể — luôn implement `IDisposable` khi một component subscribe event của service.
- **Đăng ký state container service là `Singleton` trong Blazor Server (nhiều người dùng cùng lúc):** `Singleton` nghĩa là **một instance duy nhất cho toàn bộ ứng dụng**, chia sẻ giữa **mọi người dùng** đang kết nối — giỏ hàng của người dùng A sẽ lẫn với giỏ hàng của người dùng B. Với Blazor Server, dùng `Scoped` (một instance mỗi kết nối SignalR, tương đương một người dùng) cho state riêng-theo-người-dùng; chỉ dùng `Singleton` cho state thực sự chung cho mọi người (như cấu hình toàn app, cache dữ liệu tĩnh).
- **Đặt `CascadingValue` ở gốc `App` cho MỌI thứ "để chắc ăn":** làm mất khả năng kiểm soát phạm vi (mọi component trong toàn app đều nhận, dù không cần), và không giải quyết được nhu cầu thông báo-khi-đổi cho dữ liệu động — nếu thấy mình đặt `CascadingValue` chỉ để "phòng trường hợp con nào cần", đó là dấu hiệu nên dùng state container service thay vì lạm dụng cascading.
- **Quên rằng component nhận `[CascadingParameter]` không tự re-render khi KHÔNG có `CascadingValue` cha bao quanh:** như mục 1 đã cảnh báo, đây là lỗi âm thầm lúc runtime (giá trị mặc định, không exception) — luôn kiểm tra bằng cách render thử và xem giá trị hiển thị có đúng như kỳ vọng không, đừng chỉ tin vào việc code build thành công.
- **Trộn state container service với gọi trực tiếp API mỗi lần cần dữ liệu:** nếu mỗi component tiêm `CartState` nhưng lại tự gọi HTTP API riêng để lấy giỏ hàng (bỏ qua state đã cache trong service), bạn mất toàn bộ lợi ích của state container — nhiều lần gọi API dư thừa, dữ liệu hiển thị không đồng bộ giữa các component. Service nên là nguồn dữ liệu **duy nhất** trong bộ nhớ mà mọi component đọc, còn việc gọi API để nạp/lưu dữ liệu nên nằm bên trong chính service đó (một nơi), không rải ra từng component.
- **Expose `List<T>`/property có `set` công khai trong state container, để component ngoài sửa trực tiếp không qua method:** như mục 8 đã chỉ ra cụ thể, sửa dữ liệu mà bỏ qua method của service khiến `OnChange` không được gọi — UI hiển thị sai lệch với dữ liệu thật mà không có exception nào cảnh báo. Luôn expose dữ liệu qua kiểu chỉ-đọc (`IReadOnlyList<T>`, property chỉ có `get`) và bắt buộc sửa đổi đi qua method của service.
- **Dùng biến `static` (thay vì `Scoped` qua DI) để "tiện", nghĩ rằng ứng dụng của mình chỉ có một người dùng lúc test:** đúng khi chạy thử một mình trên máy dev, nhưng sai ngay khi lên môi trường có nhiều người dùng thật — như mục 3b đã chỉ ra, đây là loại lỗi chỉ xuất hiện khi có ≥ 2 người dùng đồng thời, dễ bị bỏ sót trong giai đoạn phát triển và test đơn lẻ.

---

## Bài tập

**Bài 1 (giàn giáo):** Bạn có `MainLayout` chứa `NavMenu` và nội dung trang. Viết một `CascadingValue` ở `MainLayout` chia sẻ một `string TenChuDe` (ví dụ "sang" hoặc "toi") cho toàn bộ cây con, và một component `ThongBaoChuDe` (đặt ở bất kỳ đâu bên trong) hiển thị "Đang dùng chủ đề: {TenChuDe}".

??? success "Lời giải + vì sao"
    ```razor title="MainLayout.razor"
    @inherits LayoutComponentBase

    <CascadingValue Value="tenChuDe">
        <NavMenu />
        <ThongBaoChuDe />
        <div class="content">
            @Body
        </div>
    </CascadingValue>

    @code {
        private string tenChuDe = "sang";
    }
    ```

    ```razor title="ThongBaoChuDe.razor"
    <p>Đang dùng chủ đề: @TenChuDe</p>

    @code {
        [CascadingParameter]
        public string TenChuDe { get; set; } = "";
    }
    ```

    **Vì sao đúng:** `ThongBaoChuDe` không cần `[Parameter]` truyền tay từ `MainLayout` — nó chỉ cần đứng bên trong cặp thẻ `<CascadingValue>...</CascadingValue>` và khai báo `[CascadingParameter]` cùng tên biến giá trị (`string`), Blazor tự nối dây. `@Body` (nội dung trang hiện tại, ví dụ `ProductPage`) cũng nằm bên trong `CascadingValue`, nên bất kỳ component nào trong `ProductPage` muốn đọc `TenChuDe` cũng làm tương tự — không cần sửa `ProductPage` để "chuyển tiếp" giá trị.

**Bài 2 (thiết kế — chọn đúng cơ chế):** Bạn có hai nhu cầu trong cùng một ứng dụng: (a) hiển thị tên người dùng đang đăng nhập ở khắp mọi trang (dữ liệu không đổi trong suốt phiên làm việc); (b) một component `NotificationBell` (chuông thông báo, ở `NavMenu`) cần tự tăng số đếm ngay khi một component `OrderForm` (ở một trang hoàn toàn khác, không cùng nhánh cây với `NavMenu`) gửi đơn hàng thành công. Chọn cơ chế cho mỗi nhu cầu, giải thích bằng tiêu chí mục 5.

??? success "Lời giải + vì sao"
    **(a) Dùng `CascadingValue`/`[CascadingParameter]`.** Tên người dùng đăng nhập không đổi trong suốt phiên (ít đổi), và mọi trang đều nằm trong cùng cây con dưới `MainLayout`/`App` — đặt `CascadingValue` một lần ở gốc layout, mọi trang con đọc được, không cần cơ chế thông báo-khi-đổi phức tạp.

    **(b) Dùng state container service** (ví dụ `NotificationState` với event `OnChange`). `OrderForm` và `NotificationBell` không nằm trên cùng nhánh cây — đúng trường hợp mục 2 chỉ ra `CascadingValue` không giải quyết tốt. Dữ liệu (số thông báo) cũng thay đổi do hành động người dùng (gửi đơn hàng), cần cơ chế event để `NotificationBell` **tự cập nhật ngay** mà không phải đợi re-render từ một tổ tiên chung nào đó. `OrderForm` gọi `NotificationState.TangThongBao()`, `NotificationBell` subscribe `OnChange` trong `OnInitialized()` và huỷ đăng ký trong `Dispose()`.

**Bài 3 (sửa lỗi — nhận diện memory leak):** Đoạn code sau có một component `DonHangCounter` subscribe vào `OrderState.OnChange` để hiển thị tổng số đơn hàng. Tìm lỗi cụ thể, giải thích hậu quả runtime (không phải lỗi biên dịch), và sửa lại.

```razor title="DonHangCounter.razor (co loi - tim va sua)"
@inject OrderState Orders

<p>Tổng đơn hàng: @Orders.SoDon</p>

@code {
    protected override void OnInitialized()
    {
        Orders.OnChange += () => InvokeAsync(StateHasChanged);
    }
}
```

??? success "Lời giải + vì sao"
    **Lỗi:** component không implement `IDisposable` và không huỷ đăng ký khi bị loại khỏi cây. Tệ hơn, đăng ký ở đây dùng một **lambda ẩn danh** (`() => InvokeAsync(StateHasChanged)`) — dù có thêm `Dispose()`, bạn **không thể** viết `Orders.OnChange -= (cái lambda đó)` một cách chính xác, vì mỗi lần `OnInitialized()` chạy, lambda ẩn danh tạo ra một delegate **mới**, không phải cùng một tham chiếu để trừ (`-=`) đúng cái đã cộng (`+=`) trước đó.

    **Hậu quả runtime cụ thể:** không lỗi biên dịch. Mỗi lần `DonHangCounter` được tạo lại (điều hướng qua lại trang chứa nó), một lambda mới được thêm vào `OnChange`, và vì không thể huỷ đăng ký đúng cách, số lượng delegate trong `OnChange` tăng dần mãi — đúng dạng memory leak đã học ở mục 4, nhưng ở đây còn khó sửa hơn vì cách viết bằng lambda ẩn danh.

    **Sửa lại — dùng một method có tên, không dùng lambda ẩn danh cho việc subscribe cần huỷ:**

    ```razor title="DonHangCounter.razor (da sua)"
    @implements IDisposable
    @inject OrderState Orders

    <p>Tổng đơn hàng: @Orders.SoDon</p>

    @code {
        protected override void OnInitialized() => Orders.OnChange += CapNhat;

        private void CapNhat() => InvokeAsync(StateHasChanged);

        // Trừ ĐÚNG method CapNhat đã cộng ở trên - method có tên tạo ra
        // CÙNG MỘT tham chiếu delegate mỗi lần, nên -= hoạt động chính xác.
        public void Dispose() => Orders.OnChange -= CapNhat;
    }
    ```

    **Vì sao đúng:** `CapNhat` là một method có tên cố định — mỗi lần bạn viết `Orders.OnChange += CapNhat` hoặc `Orders.OnChange -= CapNhat`, C# tạo ra delegate trỏ tới **cùng một method**, nên `-=` tìm và loại bỏ đúng đăng ký đã thêm. Đây là quy tắc chung cần nhớ: khi subscribe một event mà sẽ cần huỷ đăng ký sau, luôn dùng method có tên (hoặc field lưu lambda), không dùng lambda viết trực tiếp tại chỗ gọi `+=`.

**Bài 4 (viết từ đầu — đóng gói đúng cách):** Viết một `FavoriteState` service (state container) quản lý danh sách tên sản phẩm "yêu thích" của người dùng, thoả: (1) chỉ expose dữ liệu qua kiểu chỉ-đọc; (2) có method `ThemYeuThich(string ten)` và `XoaYeuThich(string ten)`, cả hai đều bắn `OnChange`; (3) viết một đoạn test tay (không cần Blazor thật) chứng minh `OnChange` được gọi đúng số lần khi thêm 2 sản phẩm rồi xoá 1.

??? success "Lời giải + vì sao"
    ```csharp title="FavoriteState.cs"
    // test:run
    var favorites = new FavoriteState();
    var soLanOnChange = 0;
    favorites.OnChange += () => soLanOnChange++;

    favorites.ThemYeuThich("Ban phim");
    favorites.ThemYeuThich("Chuot");
    favorites.XoaYeuThich("Chuot");

    Console.WriteLine($"Danh sach yeu thich: {string.Join(", ", favorites.DanhSach)}");
    Console.WriteLine($"So lan OnChange: {soLanOnChange}");

    if (favorites.DanhSach.Count != 1 || favorites.DanhSach[0] != "Ban phim")
        throw new Exception("Test FAIL: danh sach sai sau khi them/xoa");
    if (soLanOnChange != 3)
        throw new Exception("Test FAIL: OnChange phai duoc goi DUNG 3 lan (2 them + 1 xoa)");
    Console.WriteLine("Test PASS");

    public sealed class FavoriteState
    {
        private readonly List<string> _danhSach = new();

        // (1) Chỉ expose qua kiểu chỉ-đọc - không AI sửa được trực tiếp từ ngoài.
        public IReadOnlyList<string> DanhSach => _danhSach;

        public event Action? OnChange;

        // (2) Mọi thay đổi CHỈ đi qua hai method này, cả hai đều bắn OnChange.
        public void ThemYeuThich(string ten)
        {
            _danhSach.Add(ten);
            OnChange?.Invoke();
        }

        public void XoaYeuThich(string ten)
        {
            _danhSach.Remove(ten);
            OnChange?.Invoke();
        }
    }
    ```

    Kết quả kỳ vọng:

    ```text title="output"
    Danh sach yeu thich: Ban phim
    So lan OnChange: 3
    Test PASS
    ```

    **Vì sao đúng:** `DanhSach` trả về `IReadOnlyList<string>` (đúng nguyên tắc mục 8) — component ngoài chỉ đọc được, không `Add`/`Remove` trực tiếp. Cả `ThemYeuThich` và `XoaYeuThich` đều gọi `OnChange?.Invoke()` ngay sau khi sửa `_danhSach`, đảm bảo mọi component subscribe đều được thông báo cho **cả hai loại thay đổi** (thêm và xoá) — không chỉ riêng một trong hai, một lỗi dễ mắc nếu chỉ nhớ bắn event ở method thêm mà quên ở method xoá.

---

## Tự kiểm tra

1. Prop drilling là gì, và vì sao nó trở thành vấn đề thực tế khi cây component sâu hoặc nhiều nhánh cùng cần một dữ liệu?

    ??? note "Đáp án"
        Prop drilling là việc truyền dữ liệu qua nhiều cấp `Parameter` trung gian chỉ để "chuyển tiếp" tới component thực sự cần, dù các cấp trung gian không dùng dữ liệu đó. Vấn đề: mỗi khi thêm một component mới cần dữ liệu, phải sửa Parameter ở tất cả các cấp trung gian trên đường đi — với cây sâu hoặc nhiều nhánh, số nơi phải sửa tăng nhanh, dễ sai và khó duy trì.

2. `CascadingValue` giải quyết prop drilling như thế nào, khác gì so với `[Parameter]` thông thường?

    ??? note "Đáp án"
        `CascadingValue` chia sẻ một giá trị cho toàn bộ cây con bên trong nó — bất kỳ component con/cháu nào khai báo `[CascadingParameter]` cùng kiểu dữ liệu đều tự nhận được giá trị, không cần các component trung gian khai báo `[Parameter]` và truyền tay qua từng cấp như cách thông thường.

3. Nếu một component khai báo `[CascadingParameter]` nhưng không nằm bên trong `CascadingValue` nào, điều gì xảy ra — lỗi biên dịch hay lỗi khác?

    ??? note "Đáp án"
        Không lỗi biên dịch. Lúc chạy, property đó giữ giá trị mặc định của kiểu dữ liệu (ví dụ chuỗi rỗng với `string`) — một lỗi runtime âm thầm, không có exception báo, chỉ phát hiện được khi quan sát dữ liệu hiển thị sai.

4. State container service là gì, và nó có gì mà `CascadingValue` không có, giúp giải quyết trường hợp `NavMenu`/`PriceTag` không cùng nhánh cây?

    ??? note "Đáp án"
        Là một service C# (đăng ký DI, không phải component) chứa state chung cùng một event (như `OnChange`) để thông báo khi state đổi. Vì là service tiêm qua DI, nó không phụ thuộc vị trí trong cây component — bất kỳ component nào ở bất kỳ nhánh nào cũng tiêm và đọc/subscribe được, khác với `CascadingValue` chỉ chia sẻ theo phạm vi cây con.

5. Nếu một component subscribe vào `OnChange` của state container service nhưng không implement `IDisposable` để huỷ đăng ký, hậu quả cụ thể là gì?

    ??? note "Đáp án"
        Memory leak: mỗi lần component được tạo lại (ví dụ điều hướng qua lại), một đăng ký mới được thêm vào `OnChange` mà không bao giờ bị huỷ, nên service (sống lâu hơn component) giữ tham chiếu tới toàn bộ các instance component cũ, ngăn garbage collector thu hồi. Hậu quả quan sát được: bộ nhớ tăng dần, và callback bị gọi nhiều lần dư thừa (một lần cho mỗi component cũ còn đăng ký) mỗi khi state đổi.

6. Vì sao nên gọi `InvokeAsync(StateHasChanged)` thay vì gọi trực tiếp `StateHasChanged()` khi xử lý sự kiện `OnChange` từ một state container service?

    ??? note "Đáp án"
        Vì `OnChange` có thể được bắn từ một luồng không phải luồng UI của Blazor (ví dụ từ callback bất đồng bộ hoặc SignalR ở Blazor Server). `InvokeAsync(...)` đảm bảo `StateHasChanged()` luôn chạy trên đúng luồng đồng bộ hoá của Blazor, tránh lỗi hoặc hành vi render không nhất quán khi gọi từ luồng khác.

7. Nếu đăng ký một state container service là `Singleton` trong một ứng dụng Blazor Server có nhiều người dùng cùng lúc, vấn đề gì xảy ra?

    ??? note "Đáp án"
        `Singleton` tạo một instance duy nhất chia sẻ cho toàn bộ ứng dụng, nghĩa là mọi người dùng đang kết nối cùng đọc/ghi chung một state — dữ liệu riêng theo người dùng (như giỏ hàng) sẽ bị lẫn giữa các người dùng khác nhau. Cần dùng `Scoped` để mỗi kết nối (mỗi người dùng) có một instance riêng.

8. Cho một dữ liệu ít đổi, chỉ cần chia sẻ trong phạm vi một cây con (như theme sáng/tối) — nên chọn `CascadingValue` hay state container service? Vì sao?

    ??? note "Đáp án"
        `CascadingValue` — vì dữ liệu ít đổi (không cần cơ chế thông báo-khi-đổi phức tạp của event) và phạm vi dùng nằm trong một cây con rõ ràng, chi phí thiết lập của `CascadingValue` thấp hơn nhiều so với việc viết và đăng ký một service riêng.

9. Vì sao dùng một biến `static` chứa giỏ hàng chung cho toàn ứng dụng là sai, trong khi `AddScoped<CartState>()` lại đúng?

    ??? note "Đáp án"
        Biến `static` chỉ có đúng một bản duy nhất cho toàn bộ process, không phân biệt người dùng nào đang truy cập — nếu nhiều người dùng cùng lúc, dữ liệu (giỏ hàng) của họ sẽ lẫn vào nhau. `AddScoped<CartState>()` để DI container tạo một instance riêng cho mỗi Scoped (mỗi kết nối/người dùng ở Blazor Server, mỗi lần tải trang ở Blazor WebAssembly), nên mỗi người dùng có giỏ hàng độc lập.

10. Nếu bạn subscribe một event bằng lambda ẩn danh viết trực tiếp tại chỗ gọi `+=` (ví dụ `Orders.OnChange += () => InvokeAsync(StateHasChanged);`), tại sao viết `Orders.OnChange -= (cùng lambda đó)` trong `Dispose()` không hoạt động đúng?

    ??? note "Đáp án"
        Mỗi lần dòng code chứa lambda ẩn danh chạy, C# tạo ra một delegate mới, khác tham chiếu với delegate được tạo ở lần chạy trước — nên `-=` với một lambda viết lại (dù giống hệt về nội dung) không khớp được với delegate đã `+=` trước đó, không huỷ đăng ký được. Cách đúng là subscribe bằng một method có tên (hoặc một field lưu sẵn lambda), để `+=` và `-=` luôn tham chiếu tới đúng cùng một delegate.

11. Trong ví dụ tổng hợp ở mục 6, vì sao `ProductPage` không cần subscribe `Cart.OnChange` dù nó cũng tiêm (`@inject`) `CartState`?

    ??? note "Đáp án"
        Vì `ProductPage` chỉ **ghi** vào `CartState` (gọi `Cart.Them(...)`), không hiển thị số lượng hay tổng tiền giỏ hàng lên UI của chính nó. Chỉ component nào **đọc và hiển thị** dữ liệu cần cập nhật theo thời gian thực (như `NavMenu` hiển thị số lượng) mới cần subscribe `OnChange` và gọi `StateHasChanged()` — subscribe khi không cần chỉ tạo thêm rủi ro quên `Dispose()` mà không mang lại lợi ích gì.

12. Vì sao dùng `CascadingValue` cho dữ liệu đổi liên tục (như số lượng giỏ hàng) gây lãng phí hiệu năng, cụ thể ở đâu?

    ??? note "Đáp án"
        Mỗi lần giá trị trong `CascadingValue` đổi, Blazor mặc định re-render lại toàn bộ cây con bên trong nó — kể cả các component không hề đọc giá trị đó qua `[CascadingParameter]`. Với dữ liệu đổi liên tục, việc này buộc toàn bộ nhánh cây (có thể rất lớn) tính toán lại không cần thiết, trong khi dùng state container service chỉ khiến đúng những component đã subscribe `OnChange` re-render.

13. Nếu một state container service expose dữ liệu qua `List<T>` công khai (có thể `Add`/`Remove` trực tiếp từ ngoài) thay vì qua method riêng, hậu quả cụ thể khi một component sửa trực tiếp vào `List<T>` đó là gì?

    ??? note "Đáp án"
        Dữ liệu vẫn thay đổi thật (vì cùng một `List<T>` bên dưới), nhưng vì không đi qua method của service, `OnChange` không được gọi — mọi component khác đang subscribe `OnChange` sẽ không biết để `StateHasChanged()`, khiến UI hiển thị dữ liệu cũ, sai lệch với dữ liệu thật trong bộ nhớ, mà không có exception hay lỗi biên dịch nào báo.

---

??? abstract "DEEP DIVE — nâng cao (ngoài fast path)"
    - **`CascadingValue` với `Name`, dùng nhiều giá trị cùng kiểu:** nếu bạn cần cascading nhiều giá trị **cùng kiểu dữ liệu** (ví dụ hai chuỗi khác nghĩa) trong cùng một cây, `[CascadingParameter]` mặc định chỉ khớp theo **kiểu dữ liệu** nên dễ nhận nhầm giá trị. Đặt `Name="..."` trên `CascadingValue` và `[CascadingParameter(Name = "...")]` ở nơi nhận để phân biệt tường minh, tránh nhận sai giá trị khi có nhiều `CascadingValue` cùng kiểu lồng nhau.
    - **`IsFixed="true"` — khi nào thực sự an toàn:** mục 7 đã cảnh báo không dùng `IsFixed="true"` cho giá trị đổi liên tục. Trường hợp nó an toàn và có lợi: một giá trị được gán **đúng một lần** trong `OnInitialized()` của component cha và không bao giờ gán lại sau đó (ví dụ một `TenantId` xác định lúc khởi tạo trang, không đổi trong suốt vòng đời trang đó) — Blazor bỏ hẳn việc theo dõi thay đổi cho giá trị này ở mọi component con, giảm chi phí runtime nhỏ nhưng tích lũy có ý nghĩa với cây rất lớn. Nếu không chắc chắn 100% giá trị không đổi sau lần render đầu, an toàn hơn là không đặt `IsFixed` (chấp nhận chi phí re-render mặc định) hoặc chuyển hẳn sang state container service như mục 5 khuyến nghị.
    - **Thư viện quản lý state chuyên dụng (Fluxor, Blazor-State):** khi ứng dụng có nhiều state phức tạp, nhiều action làm thay đổi state theo các luật rõ ràng, tự viết nhiều state container service rời rạc có thể trở nên khó theo dõi (state nào đổi khi nào, do action nào). Các thư viện theo mô hình Flux/Redux như Fluxor mang lại cấu trúc rõ ràng hơn (Action, Reducer, Effect, DevTools debug time-travel) — đánh đổi lại là thêm một tầng khái niệm mới cần học, chỉ đáng đầu tư khi state container service tự viết đã bắt đầu khó quản lý (nhiều service, nhiều event chồng chéo khó dò).
    - **`AuthenticationStateProvider` — một CascadingValue có sẵn của framework:** thông tin đăng nhập (`ClaimsPrincipal`) trong Blazor được cung cấp cho toàn cây qua `CascadingAuthenticationState` (hoặc tự động trong template mới hơn) — về bản chất đây chính là một `CascadingValue` được framework viết sẵn, và `AuthorizeView`/`[CascadingParameter] Task<AuthenticationState>` là cách bạn đọc nó. Hiểu cơ chế `CascadingValue` ở mục 1 giúp bạn hiểu đúng bản chất của `AuthenticationStateProvider` thay vì coi nó là một "hộp đen" riêng biệt.
    - **Kết hợp state container với `IObservable`/`IAsyncEnumerable` thay vì `event Action`:** với ứng dụng phức tạp hơn (cần throttle, debounce, hoặc kết hợp nhiều nguồn thay đổi), một số codebase thay `event Action? OnChange` bằng `IObservable<T>` (Reactive Extensions - Rx.NET) để tận dụng các operator có sẵn (`Throttle`, `DistinctUntilChanged`, `CombineLatest`). Đây là một lựa chọn nâng cao, chỉ đáng dùng khi logic thông báo thay đổi thực sự phức tạp hơn một `event Action` đơn giản có thể xử lý gọn.

**Tiếp theo →** [P7 · Gọi API Backend](goi-api-tu-blazor.md)
