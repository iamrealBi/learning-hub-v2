---
tier: core
status: core
owner: core-team
verified_on: "2026-07-03"
dotnet_version: "10.0"
bloom: "Áp dụng"
requires: [p7-component]
est_minutes_fast: 40
---

# Routing & Navigation trong Blazor

!!! info "bạn đang ở đây · p7 → node `p7-routing`"
    **cần trước:** đã biết cách viết một component `.razor` cơ bản (HTML trộn `@code{}`), biết `[Parameter]` là gì để nhận dữ liệu từ component cha.
    **mở khoá:** gán URL cho component qua `@page`, nhận dữ liệu từ chính URL đó (route parameter, query string), điều hướng bằng link (`NavLink`) hoặc bằng code (`NavigationManager`) — bốn thứ cộng lại là toàn bộ cơ chế "một trang Blazor biết mình đang ở URL nào, và biết cách chuyển sang URL khác".

> **Mục tiêu:** **Áp dụng** được `@page` để gán route cho component, route parameter và `[SupplyParameterFromQuery]` để nhận dữ liệu từ URL, `NavLink` để tạo menu điều hướng tự nhận diện trang hiện tại, và `NavigationManager` để chuyển trang bằng code sau một hành động (submit form, đăng nhập) — đồng thời **giải thích** được vai trò của `Router` trong `App.razor` như điểm khai báo routing toàn cục.

---

## 0. Đoán nhanh trước khi đọc

Trước khi xem đáp án, hãy tự trả lời (desirable difficulty — đoán sai vẫn giúp nhớ lâu hơn):

1. Một component `.razor` không có dòng `@page` nào — nó có thể truy cập trực tiếp qua URL (ví dụ gõ `/gio-hang` trên thanh địa chỉ) không?
2. `@page "/products/{id:int}"` và route Minimal API `app.MapGet("/products/{id:int}", ...)` ở P3 — cú pháp `{id:int}` có cùng ý nghĩa không?
3. Dùng `<a href="/gio-hang">` thường và dùng `<NavLink href="/gio-hang">` — khác biệt quan trọng nhất khi người dùng **đang ở đúng trang** `/gio-hang` là gì?
4. `NavigationManager.NavigateTo("/thanh-cong")` gọi trong nút `<button onclick="...">` HTML thuần (không dùng `@onclick`) — có chuyển trang được không?
5. Query string `?trang=2` trong URL và route parameter `{id:int}` khác nhau ở điểm nào — dùng cái nào cho "trang phân trang", cái nào cho "ID sản phẩm"?
6. Nếu một URL khớp được **hai** `@page` khác nhau (một chung, một cụ thể hơn) — Router chọn route nào?
7. `NavigateTo(url, forceLoad: true)` khác `NavigateTo(url)` (không truyền `forceLoad`) ở điểm gì?

??? note "Đáp án"
    1. **Không** — component không có `@page` không có route, gõ URL bất kỳ vào nó sẽ không tìm thấy, `Router` trả về nội dung "not found". Component đó chỉ dùng được khi được **nhúng** vào một component khác đã có `@page` (giống một `<partial>`).
    2. **Có** — cùng cú pháp route template và route constraint đã học ở Minimal API: `{id:int}` nghĩa là đoạn đó phải là số nguyên, nếu không khớp thì không vào được route này.
    3. `NavLink` tự động thêm CSS class `active` vào chính nó khi URL hiện tại khớp với `href` — `<a>` thường không có hành vi này, bạn phải tự viết code so sánh URL để tô sáng menu.
    4. **Không đáng tin** — `onclick` HTML thuần chạy JavaScript, không gọi được C# trực tiếp; phải dùng `@onclick` (cú pháp Blazor) để trình xử lý C# chạy và có thể gọi `NavigationManager.NavigateTo(...)`.
    5. Route parameter (`{id:int}`) là phần **bắt buộc, định danh chính** của URL (thiếu là không khớp route); query string (`?trang=2`) là phần **tuỳ chọn, bổ sung** (thiếu vẫn vào được trang, chỉ là thiếu tham số lọc/phân trang). ID sản phẩm dùng route parameter, số trang phân trang dùng query string.
    6. Router chọn route **cụ thể hơn** (khớp chặt hơn, ví dụ có route constraint) — tương tự cách route "chi tiết hơn" luôn được ưu tiên so với route "chung", không phụ thuộc thứ tự khai báo `@page`.
    7. `NavigateTo(url)` mặc định điều hướng phía client, không tải lại trang, giữ nguyên state trong bộ nhớ. `NavigateTo(url, forceLoad: true)` buộc trình duyệt **tải lại toàn bộ trang** từ server, mất mọi state đang giữ trong bộ nhớ (giống bấm F5 rồi chuyển trang).

---

## 1. `@page` — gán URL cho component

### 1.1 Định nghĩa

**`@page` là một directive (chỉ thị) đặt ở đầu file `.razor`, gán một URL route cho component đó** — khi người dùng vào đúng URL này (bằng gõ địa chỉ, click link, hoặc code chuyển trang), Blazor Router sẽ render component này ra màn hình.

### 1.2 Ví dụ tối thiểu

```razor title="Products.razor"
@page "/products"

<h3>Danh sách sản phẩm</h3>
<p>Đây là trang sản phẩm, tại URL /products.</p>
```

Chỉ cần dòng `@page "/products"` ở trên cùng file, không cần khai báo gì thêm ở nơi khác — component này lập tức có thể truy cập qua `https://tenapp.com/products`. Không có file cấu hình trung tâm nào liệt kê "route nào ứng với file nào" (khác với một số framework khác dùng file routing riêng) — Blazor quét toàn bộ assembly lúc khởi động, tìm mọi `@page` và tự lập bản đồ route.

### 1.3 Điều gì xảy ra khi dùng sai

Nếu bạn **quên** `@page`, component vẫn compile bình thường (không lỗi build) — nhưng gõ URL tương ứng vào trình duyệt sẽ không tìm thấy trang, `Router` hiển thị nội dung "not found" mặc định (khai báo trong `App.razor`, xem mục 6):

```text title="Hành vi khi thiếu @page — không phải lỗi build, mà là lỗi runtime lúc điều hướng"
Sorry, there's nothing at this address.
```

Đây là lỗi hay gặp nhất với người mới: copy một component đã hoạt động, đổi tên file, quên thêm/sửa `@page` — trang mới không bao giờ vào được vì Router không biết URL nào ứng với nó. Vì đây là lỗi runtime (không phải build), bug này thường chỉ bị phát hiện khi có người **thực sự click vào link** dẫn tới trang đó trong lúc test tay — CI biên dịch code vẫn "xanh" bình thường.

Một component **có thể có nhiều `@page`** (nhiều URL khác nhau cùng render một component) — mỗi dòng `@page` là một route riêng:

```razor title="Products.razor — một component, hai URL"
@page "/products"
@page "/san-pham"

<h3>Danh sách sản phẩm</h3>
```

Cả hai URL `/products` và `/san-pham` đều render đúng component này — hữu ích khi cần giữ URL cũ hoạt động (không phá link cũ) trong lúc đổi sang URL mới, hoặc hỗ trợ song song URL tiếng Anh và tiếng Việt.

### 1.4 `@page` không phải nơi để đặt logic nghiệp vụ

Một điểm dễ nhầm với người mới: `@page` chỉ **gán route**, không giới hạn hay kiểm tra gì về quyền truy cập, dữ liệu, hay điều kiện nghiệp vụ. Đặt `@page "/admin/orders"` không tự động nghĩa là "chỉ admin mới vào được" — bất kỳ ai biết URL này đều vào được nếu không có thêm cơ chế kiểm tra quyền (ví dụ `[Authorize]`, học ở bài khác về Authentication trong Blazor). Đây không phải nội dung của bài này, nhưng cần nhớ: **routing quyết định "URL nào render component nào", không quyết định "ai được phép xem"**.

---

## 2. Route parameter — nhận dữ liệu từ chính URL

### 2.1 Định nghĩa

**Route parameter là một đoạn URL được đánh dấu bằng `{ }` trong `@page`, giống hệt route parameter của Minimal API đã học ở P3** (ví dụ `{id:int}`) — giá trị đoạn đó thay đổi theo từng request, và Blazor tự động gán vào một property đánh dấu `[Parameter]` cùng tên trong component.

### 2.2 Ví dụ tối thiểu

```razor title="ProductDetail.razor"
@page "/products/{id:int}"

<h3>Chi tiết sản phẩm số @Id</h3>

@code {
    [Parameter]
    public int Id { get; set; }
}
```

Vào URL `/products/7` sẽ render component này với `Id = 7`. Cú pháp `{id:int}` có hai phần đúng như ở Minimal API: `id` là tên (phải khớp — không phân biệt hoa/thường — với tên property `[Parameter]`), `:int` là **route constraint**, chỉ khớp khi đoạn đó thật sự là số nguyên.

### 2.3 Điều gì xảy ra khi dùng sai

Nếu client vào `/products/abc` (không phải số nguyên), route này **không khớp** — giống hệt hành vi Minimal API ở P3, Router coi như không tìm thấy route phù hợp, hiển thị "not found":

```text title="Vào /products/abc với route @page "/products/{id:int}""
Sorry, there's nothing at this address.
```

Lỗi khác thường gặp: **tên property không khớp tên route parameter**. Nếu route là `{id:int}` nhưng property đặt tên `ProductId`:

```razor title="ProductDetail.razor — SAI, tên không khớp"
@page "/products/{id:int}"

<h3>Chi tiết sản phẩm số @ProductId</h3>

@code {
    [Parameter]
    public int ProductId { get; set; } // SAI: route parameter tên "id", property tên "ProductId" — không khớp
}
```

Đây không phải lỗi build — component compile được — nhưng `ProductId` sẽ luôn là `0` (giá trị mặc định), không bao giờ nhận được giá trị `7` từ URL `/products/7`. Đây là lỗi runtime im lặng, khó phát hiện bằng mắt vì không có exception, chỉ hiển thị sai dữ liệu.

### 2.4 Route parameter tuỳ chọn — dấu `?`

Giống Minimal API, Blazor cũng hỗ trợ route parameter **tuỳ chọn** bằng dấu `?` sau tên, cho phép route khớp cả khi thiếu đoạn đó:

```razor title="ProductDetail.razor — route parameter tuỳ chọn"
@page "/products"
@page "/products/{id:int?}"

<h3>@(Id.HasValue ? $"Chi tiết sản phẩm số {Id}" : "Danh sách sản phẩm")</h3>

@code {
    [Parameter]
    public int? Id { get; set; }
}
```

Với `{id:int?}`, cả `/products` (không có `id`) và `/products/7` (có `id = 7`) đều khớp cùng một `@page` — nhưng property `Id` phải khai báo là **kiểu nullable** (`int?`), vì khi thiếu đoạn đó, Blazor gán `null`, không phải `0`. Nếu bạn khai báo `Id` là `int` (không nullable) với route parameter tuỳ chọn, ứng dụng ném lỗi runtime khi vào `/products` (thiếu `id`) vì không thể gán `null` vào `int`.

### 2.5 Nhiều route parameter trong một `@page`

Một `@page` có thể có nhiều route parameter, mỗi đoạn `{ }` ứng với một property riêng — ví dụ trang xem đánh giá của một sản phẩm cụ thể theo `productId` và `reviewId`:

```razor title="ProductReview.razor"
@page "/products/{productId:int}/reviews/{reviewId:int}"

<h3>Đánh giá số @ReviewId của sản phẩm số @ProductId</h3>

@code {
    [Parameter]
    public int ProductId { get; set; }

    [Parameter]
    public int ReviewId { get; set; }
}
```

Vào `/products/7/reviews/42` → `ProductId = 7`, `ReviewId = 42`. Cả hai đoạn đều bắt buộc và đều có route constraint `:int` — thiếu bất kỳ đoạn nào, hoặc một trong hai không phải số nguyên, route này không khớp.

### 2.6 Các route constraint khác ngoài `:int`

`:int` chỉ là một trong nhiều route constraint có sẵn — cùng ý tưởng "ràng buộc kiểu dữ liệu của đoạn URL đó" áp dụng cho các kiểu khác:

```razor title="OrderDetail.razor — route constraint :guid"
@page "/orders/{orderId:guid}"

<h3>Đơn hàng @OrderId</h3>

@code {
    [Parameter]
    public Guid OrderId { get; set; }
}
```

Vào `/orders/3fa85f64-5717-4562-b3fc-2c963f66afa6` (đúng định dạng GUID) sẽ khớp và gán vào `Guid OrderId`; vào `/orders/abc` (không đúng định dạng GUID) sẽ "not found" giống mọi trường hợp constraint không khớp khác. Các constraint phổ biến khác gồm `:bool`, `:datetime`, `:decimal`, `:double`, `:guid`, `:long` — nguyên tắc chung giống nhau: **tên constraint khớp đúng kiểu dữ liệu của property `[Parameter]`**, sai kiểu ở một trong hai phía (route constraint hoặc property) đều dẫn tới lỗi (không khớp route, hoặc lỗi build nếu kiểu không tương thích hoàn toàn).

---

## 3. `NavLink` — link tự nhận diện trang hiện tại

### 3.1 Định nghĩa

**`NavLink` là một component Blazor có sẵn, render ra một thẻ `<a>` HTML bình thường, nhưng tự động thêm CSS class `active` vào chính nó khi URL hiện tại của trình duyệt khớp với `href`** — dùng để làm menu điều hướng biết "đang ở trang nào" mà không cần tự viết code so sánh.

### 3.2 Ví dụ tối thiểu

```razor title="NavMenu.razor"
<nav>
    <NavLink href="/products" Match="NavLinkMatch.All">
        Sản phẩm
    </NavLink>
    <NavLink href="/gio-hang" Match="NavLinkMatch.All">
        Giỏ hàng
    </NavLink>
</nav>
```

Khi URL hiện tại là `/products`, thẻ `<a>` tương ứng với `NavLink href="/products"` sẽ tự có thêm `class="active"` trong HTML render ra — bạn chỉ cần viết CSS cho class `.active` (ví dụ đổi màu chữ) để menu tự "tô sáng" đúng trang đang xem.

### 3.3 Điều gì xảy ra khi dùng sai

Nếu dùng `<a href="/products">` thẻ HTML thuần thay vì `NavLink`, link vẫn **điều hướng đúng** (vì đây vẫn là `<a>` HTML hợp lệ) — nhưng nó **không bao giờ có class `active`**, menu sẽ không tô sáng trang hiện tại, dù về mặt điều hướng không có lỗi gì cả. Đây là lỗi thẩm mỹ dễ bỏ qua vì không crash, không throw exception, chỉ là menu "trông chết" không phản hồi trang đang xem.

Ngoài ra, `Match="NavLinkMatch.All"` (khớp chính xác toàn URL) và không khai báo `Match` (mặc định là `NavLinkMatch.Prefix` — khớp khi URL hiện tại **bắt đầu bằng** `href`) cho hành vi khác nhau: với `href="/products"` và không khai báo `Match`, cả `/products` và `/products/7` đều làm `NavLink` này có class `active` (vì `/products/7` bắt đầu bằng `/products`) — nếu bạn chỉ muốn "active đúng khi ở chính trang `/products`, không phải trang con", phải khai báo rõ `Match="NavLinkMatch.All"`.

### 3.4 So sánh `NavLinkMatch.Prefix` và `NavLinkMatch.All` bằng ví dụ cụ thể

```razor title="NavMenu.razor — so sánh hai chế độ Match"
<nav>
    <!-- Prefix (mặc định): active ở CẢ /products VÀ /products/7 -->
    <NavLink href="/products">Sản phẩm (prefix)</NavLink>

    <!-- All: active CHỈ khi URL đúng là /products, không active ở /products/7 -->
    <NavLink href="/products" Match="NavLinkMatch.All">Sản phẩm (all)</NavLink>
</nav>
```

Quy tắc thực dụng: dùng `NavLinkMatch.All` cho các link menu cấp cao nhất (như "Trang chủ", "Giỏ hàng") — nơi bạn chỉ muốn active đúng một trang cụ thể; dùng mặc định `Prefix` (không cần khai báo `Match`) khi bạn muốn cả trang cha và mọi trang con đều tô sáng cùng một mục menu (ví dụ mục menu "Sản phẩm" vẫn active dù đang xem `/products` hay `/products/7`).

### 3.5 `NavLink` với CSS class tuỳ chỉnh

Mặc định, class được thêm là `active`. Có thể đổi tên class qua `ActiveClass`, hữu ích khi dự án đã có sẵn class CSS khác (ví dụ dùng Bootstrap với class `.selected`):

```razor title="NavMenu.razor — đổi tên class active"
<NavLink href="/products" ActiveClass="selected">
    Sản phẩm
</NavLink>
```

Khi active, thẻ `<a>` render ra sẽ có `class="selected"` thay vì `class="active"` — CSS trong stylesheet phải viết đúng theo tên class này, viết `.active { ... }` sẽ không có tác dụng gì nếu đã đổi `ActiveClass`.

### 3.6 `NavLink` vẫn nhận mọi attribute HTML thông thường

Vì `NavLink` render ra một thẻ `<a>` chuẩn, mọi attribute HTML khác (`target`, `title`, class CSS cố định thêm vào cùng `active`...) vẫn hoạt động bình thường, không bị `NavLink` chặn hay ghi đè:

```razor title="NavMenu.razor — NavLink với attribute HTML khác"
<NavLink href="/products" class="menu-item" title="Xem danh sách sản phẩm">
    Sản phẩm
</NavLink>
```

Khi active, class cuối cùng trên thẻ `<a>` render ra sẽ là `class="menu-item active"` (Blazor **nối thêm** `active`, không thay thế class đã khai báo) — đây là hành vi hữu ích, cho phép bạn giữ class layout cố định (`menu-item`) và chỉ dùng CSS con `.menu-item.active` để style riêng trạng thái đang chọn.

---

## 4. `NavigationManager` — chuyển trang bằng code

### 4.1 Định nghĩa

**`NavigationManager` là một dịch vụ (service) được Blazor đăng ký sẵn trong DI container, tiêm vào component qua `@inject`, cho phép chuyển trang bằng code** (không cần người dùng click link) — dùng khi cần điều hướng sau một hành động, ví dụ chuyển sang trang "đặt hàng thành công" sau khi submit form xong.

### 4.2 Ví dụ tối thiểu

```razor title="Checkout.razor"
@page "/checkout"
@inject NavigationManager Navigation

<button @onclick="SubmitOrder">Đặt hàng</button>

@code {
    private void SubmitOrder()
    {
        // Giả sử lưu đơn hàng thành công ở đây...
        Navigation.NavigateTo("/order-success");
    }
}
```

Nhấn nút, `SubmitOrder` chạy, gọi `Navigation.NavigateTo("/order-success")` — trình duyệt chuyển sang URL `/order-success` ngay lập tức, không cần người dùng click bất kỳ `<a>` nào.

### 4.3 Điều gì xảy ra khi dùng sai

Nếu bạn gọi `NavigateTo` từ một trình xử lý gắn bằng `onclick` HTML thuần (không phải `@onclick` của Blazor):

```razor title="Checkout.razor — SAI, dùng onclick HTML thuần"
@page "/checkout"
@inject NavigationManager Navigation

<button onclick="SubmitOrder()">Đặt hàng</button>

@code {
    private void SubmitOrder()
    {
        Navigation.NavigateTo("/order-success");
    }
}
```

`onclick` (không có `@`) là thuộc tính HTML chuẩn, trình duyệt hiểu nó là **JavaScript**, sẽ tìm một hàm JavaScript tên `SubmitOrder` — không tìm thấy vì `SubmitOrder` là phương thức C#, không phải hàm JS toàn cục. Kết quả: click nút không làm gì cả, và console trình duyệt báo lỗi:

```text title="Console lỗi khi dùng onclick thay vì @onclick"
Uncaught ReferenceError: SubmitOrder is not defined
    at HTMLButtonElement.onclick
```

Phải dùng `@onclick="SubmitOrder"` (có `@`) để Blazor gắn trình xử lý event vào đúng phương thức C# trong `@code{}`.

Một điểm quan trọng khác: nếu `NavigateTo` được gọi ngay trong `OnInitializedAsync` **không kiểm tra điều kiện** (ví dụ luôn redirect sang trang khác mỗi khi component khởi tạo), có thể tạo ra **vòng lặp điều hướng vô hạn** nếu trang đích cũng tự động redirect ngược lại — trình duyệt sẽ đứng ở trạng thái loading liên tục, không bao giờ hiển thị nội dung. Luôn đặt điều kiện rõ ràng trước khi gọi `NavigateTo` trong lifecycle method.

### 4.4 `forceLoad` — chọn giữa điều hướng client và tải lại toàn trang

`NavigateTo` có tham số tuỳ chọn thứ hai, `forceLoad`, mặc định là `false`:

```razor title="Checkout.razor — forceLoad: true"
@code {
    private void GoToExternalLogin()
    {
        // forceLoad: true — buộc tải lại toàn bộ trang, không chỉ điều hướng phía client.
        Navigation.NavigateTo("/external-login", forceLoad: true);
    }
}
```

Với `forceLoad: false` (mặc định), Blazor chỉ đổi phần nội dung `Router` render ra, **giữ nguyên** mọi service/state đang có trong bộ nhớ (client-side routing, không có request HTTP tải lại trang). Với `forceLoad: true`, trình duyệt **tải lại hoàn toàn** trang từ server — giống hệt gõ URL mới vào thanh địa chỉ rồi Enter — mọi state trong bộ nhớ (biến, service scoped) bị **mất hoàn toàn**, phải khởi tạo lại từ đầu.

**Điều gì xảy ra khi dùng sai `forceLoad`:** nếu bạn dùng `forceLoad: true` cho một điều hướng nội bộ đơn giản (ví dụ chuyển từ `/products` sang `/products/7`), người dùng sẽ thấy **toàn bộ trang nhấp nháy trắng rồi tải lại** (giống load trang web truyền thống) — trải nghiệm chậm hơn hẳn so với điều hướng phía client mượt mà mà Blazor vốn có, dù về chức năng không sai. Chỉ dùng `forceLoad: true` khi thật sự cần buộc reset toàn bộ state (ví dụ sau khi đổi ngôn ngữ ứng dụng, hoặc chuyển sang một URL ngoài phạm vi ứng dụng Blazor).

### 4.5 Đọc URL hiện tại qua `NavigationManager.Uri`

Ngoài `NavigateTo`, `NavigationManager` còn cho đọc URL hiện tại qua property `Uri` — hữu ích khi cần biết "đang ở đâu" mà không dựa vào `NavLink`:

```razor title="CurrentUrlDisplay.razor"
@inject NavigationManager Navigation

<p>URL hiện tại: @Navigation.Uri</p>
```

`Navigation.Uri` trả về URL đầy đủ (bao gồm domain), ví dụ `https://tenapp.com/products?page=2`. Nếu chỉ cần phần đường dẫn tương đối, phải tự cắt chuỗi hoặc dùng `Navigation.ToBaseRelativePath(Navigation.Uri)`.

---

## 5. Query string qua `[SupplyParameterFromQuery]`

### 5.1 Định nghĩa

**`[SupplyParameterFromQuery]` là attribute đánh dấu một property `[Parameter]` để Blazor tự động gán giá trị từ query string trên URL** (đoạn sau dấu `?`, ví dụ `?trang=2`) — khác với route parameter, query string là phần **tuỳ chọn**, thiếu vẫn vào được trang.

### 5.2 Ví dụ tối thiểu

```razor title="ProductList.razor"
@page "/products"

<h3>Trang số @Page</h3>

@code {
    [Parameter]
    [SupplyParameterFromQuery]
    public int Page { get; set; } = 1;
}
```

Vào `/products` (không có query string) → `Page = 1` (giá trị mặc định). Vào `/products?page=2` → `Page = 2`, Blazor tự đọc query string `page` và gán vào property.

### 5.3 Điều gì xảy ra khi dùng sai

Nếu bạn quên gắn `[Parameter]` mà chỉ có `[SupplyParameterFromQuery]`:

```razor title="ProductList.razor — SAI, thiếu [Parameter]"
@code {
    [SupplyParameterFromQuery]
    public int Page { get; set; } = 1; // SAI: thiếu [Parameter], Blazor không nhận diện đây là parameter cần bind
}
```

Đây báo lỗi ngay lúc build (không phải runtime), vì `[SupplyParameterFromQuery]` bắt buộc phải đi kèm `[Parameter]` — Blazor coi đây là cấu hình sai, không phải một property tự động lấy giá trị được:

```text title="Lỗi build khi thiếu [Parameter] đi kèm [SupplyParameterFromQuery]"
error RZ10012: Found markup element with unexpected name 'Page'.
```

(thông báo lỗi cụ thể có thể khác theo phiên bản SDK, nhưng bản chất luôn là: analyzer từ chối compile property có `[SupplyParameterFromQuery]` mà không có `[Parameter]` đi cùng).

Query string cũng **không có route constraint** như `{id:int}` — nếu URL là `?page=abc` (không phải số), giá trị gán vào property `int Page` sẽ **giữ nguyên giá trị mặc định** (`1`) một cách im lặng, không throw exception — khác hẳn route parameter (`{id:int}` không khớp thì cả route "not found" luôn). Đừng nhầm hai hành vi lỗi này khi debug.

### 5.4 Đặt tên query string khác tên property qua `Name`

Mặc định, tên query string phải khớp tên property (không phân biệt hoa/thường). Nếu muốn tên query string trên URL khác tên property trong code (ví dụ URL dùng `q` ngắn gọn, code dùng tên rõ nghĩa `SearchTerm`), dùng tham số `Name`:

```razor title="SearchPage.razor — query string tên khác property"
@page "/search"

<h3>Tìm kiếm: @SearchTerm</h3>

@code {
    [Parameter]
    [SupplyParameterFromQuery(Name = "q")]
    public string? SearchTerm { get; set; }
}
```

Vào `/search?q=ao-thun` → `SearchTerm = "ao-thun"`. Nếu quên khai báo `Name = "q"` mà URL vẫn dùng `?q=...`, property `SearchTerm` sẽ **không nhận được giá trị** (vì Blazor tìm query string tên `searchterm`, không tìm thấy `q`) — lại là một lỗi im lặng khác, không exception, chỉ property giữ giá trị mặc định (`null`).

### 5.5 Nhiều query string cùng lúc, kiểu dữ liệu khác nhau

Một trang có thể nhận nhiều query string cùng lúc, mỗi cái một property riêng, kiểu dữ liệu tuỳ ý (không giới hạn `int`/`string`):

```razor title="ProductList.razor — nhiều query string"
@page "/products"

<h3>Trang @Page, sắp xếp theo @SortBy, chỉ hàng còn @(InStockOnly ? "còn hàng" : "tất cả")</h3>

@code {
    [Parameter]
    [SupplyParameterFromQuery]
    public int Page { get; set; } = 1;

    [Parameter]
    [SupplyParameterFromQuery]
    public string SortBy { get; set; } = "name";

    [Parameter]
    [SupplyParameterFromQuery]
    public bool InStockOnly { get; set; } = false;
}
```

Vào `/products?page=2&sortby=price&instockonly=true` → cả ba property được gán đúng giá trị tương ứng. Mỗi query string là độc lập — thiếu bất kỳ cái nào, property đó chỉ dùng giá trị mặc định, các property khác không bị ảnh hưởng (khác route parameter, nơi thiếu một đoạn bắt buộc làm toàn route "not found").

---

## 6. `App.razor` và `Router` — nơi khai báo routing toàn cục

Toàn bộ cơ chế `@page` ở các mục trên chỉ hoạt động vì có một component gốc tên `App.razor`, chứa component `<Router>` — đây là nơi Blazor **quét tất cả `@page` trong assembly, khớp với URL hiện tại, và quyết định render component nào**. Bạn hiếm khi phải sửa file này (framework đã tạo sẵn khi `dotnet new blazor`), nhưng cần biết nó tồn tại để hiểu "not found" ở mục 1.3 và 2.3 lấy nội dung từ đâu:

```razor title="App.razor — cấu trúc điển hình (framework tạo sẵn, giới thiệu để biết nó ở đâu)"
<Router AppAssembly="@typeof(Program).Assembly">
    <Found Context="routeData">
        <RouteView RouteData="@routeData" DefaultLayout="@typeof(MainLayout)" />
    </Found>
    <NotFound>
        <PageTitle>Không tìm thấy</PageTitle>
        <p>Sorry, there's nothing at this address.</p>
    </NotFound>
</Router>
```

`<Found>` render khi URL khớp một `@page` nào đó (dùng `RouteView` để hiển thị đúng component + layout); `<NotFound>` render khi không khớp route nào — chính là nội dung đã thấy ở mục 1.3 và 2.3. Bài này chỉ giới thiệu ngắn để bạn biết "not found" từ đâu ra — không đi sâu tuỳ biến `Router`.

`AppAssembly="@typeof(Program).Assembly"` là dòng quan trọng nhất trong `Router`: nó nói cho Blazor biết "quét `@page` trong assembly nào" — mặc định là assembly của chính ứng dụng. Nếu bạn có component `@page` nằm trong một **class library riêng** (không phải project chính), phải thêm assembly đó vào `AdditionalAssemblies` để `Router` biết quét thêm, nếu không các `@page` trong library đó sẽ không bao giờ được tìm thấy (giống lỗi "quên `@page`" ở mục 1.3, nhưng nguyên nhân khác — route có tồn tại, chỉ là `Router` không biết để quét).

### 6.1 `<NotFound>` không phải chỉ có văn bản tĩnh

`<NotFound>` là một `RenderFragment` (một đoạn markup) như bất kỳ nội dung Razor khác — có thể chứa layout, `PageTitle`, hoặc cả một component riêng, không giới hạn ở một dòng chữ tĩnh:

```razor title="App.razor — NotFound có layout riêng"
<Router AppAssembly="@typeof(Program).Assembly">
    <Found Context="routeData">
        <RouteView RouteData="@routeData" DefaultLayout="@typeof(MainLayout)" />
    </Found>
    <NotFound>
        <LayoutView Layout="@typeof(MainLayout)">
            <PageTitle>404 — Không tìm thấy trang</PageTitle>
            <h1>404</h1>
            <p>Trang bạn tìm không tồn tại. <a href="/">Về trang chủ</a>.</p>
        </LayoutView>
    </NotFound>
</Router>
```

`LayoutView` cho phép trang "not found" vẫn hiển thị cùng layout chung (menu, footer) như các trang bình thường khác — mặc định (không có `LayoutView`) thì `<NotFound>` render "trần", không có menu hay footer bao quanh, có thể gây cảm giác trang lỗi bị "vỡ layout" nếu không cấu hình.

### 6.1a `MainLayout` và `@Body` — nơi nội dung route được chèn vào

`DefaultLayout="@typeof(MainLayout)"` trong `<Router>` (mục 6) trỏ tới một component layout dùng chung cho mọi trang — bên trong `MainLayout.razor` có một điểm đánh dấu `@Body` để Blazor biết "chèn nội dung của trang hiện tại vào đây":

```razor title="MainLayout.razor — cấu trúc điển hình"
@inherits LayoutComponentBase

<div class="page">
    <NavMenu />
    <main>
        @Body
    </main>
</div>
```

`@Body` chính là nơi component ứng với route hiện tại (ví dụ `Products.razor` khi ở `/products`) được render vào — `NavMenu` (chứa các `NavLink` đã học ở mục 3) nằm ngoài `@Body`, nên **luôn hiển thị ở mọi trang**, không đổi theo route, chỉ có phần trong `@Body` mới thay đổi mỗi lần điều hướng. Đây là lý do vì sao menu không "chớp tắt" khi chuyển trang trong Blazor — chỉ có nội dung `@Body` được thay, layout xung quanh giữ nguyên.

### 6.2 Vì sao hiếm khi cần sửa `App.razor`

Trong phần lớn dự án CRUD thông thường, bạn sẽ viết rất nhiều component có `@page`, nhưng **hiếm khi động vào `App.razor`** — vì mọi route mới tự động được `Router` nhận diện ngay khi bạn thêm dòng `@page` vào component, không cần đăng ký gì thêm ở `App.razor`. Đây là điểm khác biệt lớn so với một số framework yêu cầu khai báo route tập trung ở một file cấu hình — Blazor dùng cách tiếp cận "route đi theo component" (co-location), giúp dễ tìm route của một trang (chỉ cần mở đúng file `.razor` đó) nhưng đổi lại không có một nơi duy nhất để nhìn toàn bộ danh sách route của ứng dụng (muốn xem toàn bộ, phải tự tìm bằng cách grep `@page` trong toàn bộ project).

---

## 7. Tổng hợp: bốn khái niệm cùng làm việc trong một luồng thực tế

Sau khi đã hiểu riêng từng khái niệm, đây là bảng tổng hợp vai trò của từng thứ trong một luồng điều hướng điển hình — người dùng bấm menu, xem chi tiết sản phẩm, lọc theo trang, rồi submit form và được chuyển trang:

| Khái niệm | Vai trò trong luồng | Ở đâu trong URL |
|-----------|---------------------|------------------|
| `@page` | Gán URL cho từng component, không có thì không route được | Định nghĩa cả URL (không phải một phần) |
| Route parameter (`{id:int}`) | Nhận dữ liệu **bắt buộc**, là một phần định danh chính của route | Đoạn giữa hai dấu `/`, ví dụ `/products/7` |
| Query string (`[SupplyParameterFromQuery]`) | Nhận dữ liệu **tuỳ chọn**, bổ sung (lọc, phân trang, tìm kiếm) | Sau dấu `?`, ví dụ `?page=2` |
| `NavLink` | Tạo menu điều hướng, tự biết đang ở trang nào để tô sáng | Không xuất hiện trong URL, chỉ là UI menu |
| `NavigationManager` | Chuyển trang bằng code sau một hành động, không cần người dùng click link | Không xuất hiện trong URL, là hành động runtime |

Ví dụ luồng cụ thể ghép cả bốn khái niệm: người dùng click `NavLink` dẫn tới `/products` (route cơ bản), sau đó thêm `?page=2` vào URL khi bấm "trang sau" (query string qua `[SupplyParameterFromQuery]`), click vào một sản phẩm chuyển sang `/products/7` (route parameter `{id:int}`), rồi bấm "Thêm vào giỏ" — xử lý xong, code gọi `NavigationManager.NavigateTo("/cart")` để tự động chuyển sang trang giỏ hàng, không cần người dùng tự click thêm.

```razor title="ProductDetail.razor — ghép route parameter + NavigationManager"
@page "/products/{id:int}"
@inject NavigationManager Navigation

<h3>Sản phẩm số @Id</h3>
<button @onclick="AddToCart">Thêm vào giỏ</button>

@code {
    [Parameter]
    public int Id { get; set; }

    private void AddToCart()
    {
        // Giả sử đã thêm vào giỏ hàng thành công ở đây...
        Navigation.NavigateTo("/cart");
    }
}
```

**Điều gì xảy ra khi trộn sai vai trò:** nếu bạn cố nhét dữ liệu tuỳ chọn (ví dụ mã giảm giá, có thể không có) vào route parameter bắt buộc (`@page "/products/{id:int}/{discountCode}"`), URL không có mã giảm giá (`/products/7`) sẽ **không khớp route này**, vì route parameter không đánh dấu `?` là bắt buộc — người dùng gặp "not found" một cách vô lý cho một tính năng lẽ ra chỉ là tuỳ chọn. Đây là lỗi thiết kế route, không phải lỗi cú pháp: phải tự hỏi "dữ liệu này bắt buộc hay tuỳ chọn" trước khi quyết định dùng route parameter hay query string.

---

## Cạm bẫy & thực chiến

- **Quên `@page`, tưởng lỗi build nhưng thực ra là lỗi điều hướng runtime:** component compile bình thường, chỉ lộ ra khi gõ đúng URL và thấy "not found" — luôn kiểm tra dòng `@page` đầu tiên khi một trang "không vào được" dù code có vẻ đúng.
- **Tên property `[Parameter]` không khớp tên route parameter (không phân biệt hoa/thường nhưng phải đúng chữ):** `{id:int}` phải khớp property tên `Id` (hoặc `id`), không thể là `ProductId` — sai tên không gây lỗi build, chỉ khiến giá trị luôn là mặc định (`0`, `null`...), rất khó phát hiện nếu không test thủ công với giá trị khác `0`.
- **Dùng `onclick` HTML thuần thay vì `@onclick` khi gọi `NavigationManager.NavigateTo`:** nút bấm "không phản hồi gì", console báo `ReferenceError` vì trình duyệt tìm hàm JavaScript không tồn tại — luôn kiểm tra có dấu `@` trước tên event handler trong Razor.
- **Nhầm route constraint (`{id:int}`, bắt buộc, sai kiểu → route "not found" toàn trang) với lỗi parse query string (`?page=abc`, im lặng giữ giá trị mặc định, không có exception, không "not found"):** hai cơ chế lỗi khác hẳn nhau — debug sai chỗ (đi tìm "not found" cho lỗi query string) sẽ mất thời gian vô ích.
- **`NavigateTo` gọi vô điều kiện trong `OnInitializedAsync`, tạo vòng lặp redirect vô hạn** nếu trang đích cũng tự động điều hướng ngược lại — trình duyệt kẹt ở trạng thái loading, không có thông báo lỗi rõ ràng trên UI (chỉ thấy network tab liên tục có request mới). Luôn có điều kiện rõ ràng (ví dụ kiểm tra trạng thái đăng nhập) trước khi gọi `NavigateTo` trong lifecycle.
- **Dùng `forceLoad: true` không cần thiết cho điều hướng nội bộ:** làm mất toàn bộ ưu điểm "chuyển trang mượt, không tải lại" của Blazor — trang nhấp nháy trắng, chậm hơn hẳn, dù chức năng vẫn đúng. Chỉ dùng khi thật sự cần buộc reset state.
- **Đặt route parameter kiểu không-nullable (`int`) cho route có dấu `?` tuỳ chọn (`{id:int?}`):** gây lỗi runtime khi vào URL thiếu đoạn đó, vì Blazor không gán được `null` vào `int` không-nullable — luôn dùng kiểu nullable (`int?`) khi route parameter có dấu `?`.
- **Quên `Name` khi tên query string trên URL khác tên property:** property giữ giá trị mặc định một cách im lặng vì Blazor tìm nhầm tên — luôn kiểm tra kỹ tên query string thực tế trên URL khớp với tên property (hoặc `Name` đã khai báo).
- **Dùng route parameter bắt buộc cho dữ liệu lẽ ra là tuỳ chọn** (đã minh hoạ ở mục 7): người dùng gặp "not found" vô lý cho một tính năng lẽ ra chỉ nên là tuỳ chọn — luôn tự hỏi "thiếu dữ liệu này thì trang còn vào được không" trước khi chọn route parameter hay query string.
- **Không cập nhật danh sách route khi refactor, vì không có nơi tập trung khai báo route:** vì Blazor dùng co-location (route nằm ngay trong file component, không có file cấu hình trung tâm), đổi URL của một trang chỉ cần sửa `@page` trong đúng file đó — nhưng nếu có `NavLink` hoặc `NavigationManager.NavigateTo` ở nơi khác đang hard-code URL cũ, chúng **không tự động đổi theo**, gây link chết. Luôn grep toàn bộ project tìm URL cũ trước khi đổi `@page`, không dựa vào build để phát hiện (vì đây không phải lỗi build).

---

## Bài tập

**Bài 1 — Route parameter + NavLink.** Viết một component `OrderDetail.razor` nhận `orderId` (kiểu `int`) từ URL dạng `/orders/{orderId}`, hiển thị dòng chữ "Đơn hàng số X". Sau đó viết một `NavLink` trong menu dẫn tới `/orders/5` bằng href cố định, chỉ active đúng khi ở chính trang đó (không active ở các đơn hàng khác).

??? success "Lời giải + vì sao"
    ```razor title="OrderDetail.razor"
    @page "/orders/{orderId:int}"

    <h3>Đơn hàng số @OrderId</h3>

    @code {
        [Parameter]
        public int OrderId { get; set; }
    }
    ```

    ```razor title="NavMenu.razor — đoạn thêm"
    <NavLink href="/orders/5" Match="NavLinkMatch.All">
        Xem đơn hàng số 5
    </NavLink>
    ```

    **Vì sao đúng:** route parameter tên `orderId` trong `@page` khớp property `OrderId` (không phân biệt hoa/thường), có `:int` để ràng buộc chỉ số nguyên mới khớp route — vào `/orders/abc` sẽ "not found" đúng như thiết kế. `NavLink` dùng `Match="NavLinkMatch.All"` để chỉ active đúng khi ở chính `/orders/5`, không active nhầm khi ở `/orders/6` (nếu dùng mặc định `Prefix`, `/orders/6` cũng làm link này active vì `/orders/6` bắt đầu bằng... thực ra không, vì `href="/orders/5"` chỉ match prefix `/orders/5`, không match `/orders/6` — nhưng nếu href chỉ là `/orders` thì mọi đơn hàng đều active, đây là lý do cần hiểu rõ Match trước khi chọn).

**Bài 2 — NavigationManager + query string.** Viết component `SearchPage.razor` tại `/search`, có property `Keyword` (kiểu `string`, mặc định rỗng) nhận từ query string `?keyword=...` qua `[SupplyParameterFromQuery]`. Thêm một nút "Tìm sản phẩm mới" dùng `NavigationManager` để chuyển sang `/products` sau khi bấm.

??? success "Lời giải + vì sao"
    ```razor title="SearchPage.razor"
    @page "/search"
    @inject NavigationManager Navigation

    <h3>Kết quả tìm kiếm cho: "@Keyword"</h3>
    <button @onclick="GoToProducts">Tìm sản phẩm mới</button>

    @code {
        [Parameter]
        [SupplyParameterFromQuery]
        public string Keyword { get; set; } = "";

        private void GoToProducts()
        {
            Navigation.NavigateTo("/products");
        }
    }
    ```

    **Vì sao đúng:** `Keyword` có cả `[Parameter]` và `[SupplyParameterFromQuery]` (thiếu `[Parameter]` sẽ báo lỗi build như đã minh hoạ ở mục 5.3); vào `/search?keyword=ao` sẽ hiển thị đúng "ao", vào `/search` (không query) hiển thị chuỗi rỗng mặc định, không lỗi. Nút dùng `@onclick` (có `@`) để gọi đúng phương thức C# `GoToProducts`, bên trong gọi `Navigation.NavigateTo` để chuyển trang bằng code, không cần người dùng click `<a>`. Không dùng `forceLoad: true` vì đây là điều hướng nội bộ đơn giản, không cần reset toàn bộ state.

**Bài 3 — Route parameter tuỳ chọn.** Viết component `Blog.razor` phục vụ cả URL `/blog` (danh sách bài viết) và `/blog/{slug}` (bài viết cụ thể theo slug dạng chuỗi, ví dụ `/blog/hoc-blazor`). Khi không có `slug`, hiển thị "Danh sách bài viết"; khi có, hiển thị "Bài viết: {slug}".

??? success "Lời giải + vì sao"
    ```razor title="Blog.razor"
    @page "/blog"
    @page "/blog/{slug}"

    <h3>@(string.IsNullOrEmpty(Slug) ? "Danh sách bài viết" : $"Bài viết: {Slug}")</h3>

    @code {
        [Parameter]
        public string? Slug { get; set; }
    }
    ```

    **Vì sao đúng:** dùng hai dòng `@page` riêng (không phải cú pháp `{slug?}` với dấu hỏi) vì `slug` là `string` — với `string`, cách rõ ràng và tương thích rộng nhất là khai báo hai route: một không có parameter, một có. Property `Slug` khai báo kiểu nullable (`string?`) vì route `/blog` không cung cấp giá trị này, Blazor gán `null`. Kiểm tra `string.IsNullOrEmpty(Slug)` để phân biệt hai trường hợp hiển thị.

**Bài 4 — Kết hợp route parameter và query string cùng lúc.** Viết component `OrderList.razor` tại `/orders/{customerId:int}`, nhận `customerId` bắt buộc từ route, và một query string tuỳ chọn `status` (kiểu `string`, mặc định `"all"`) để lọc theo trạng thái đơn hàng. Hiển thị dòng "Đơn hàng của khách X, lọc theo trạng thái Y".

??? success "Lời giải + vì sao"
    ```razor title="OrderList.razor"
    @page "/orders/{customerId:int}"

    <h3>Đơn hàng của khách @CustomerId, lọc theo trạng thái @Status</h3>

    @code {
        [Parameter]
        public int CustomerId { get; set; }

        [Parameter]
        [SupplyParameterFromQuery]
        public string Status { get; set; } = "all";
    }
    ```

    **Vì sao đúng:** `customerId` là dữ liệu **bắt buộc** để xác định trang này thuộc về ai — không có nó, trang không có nghĩa gì cả, nên dùng route parameter (`{customerId:int}`), thiếu nó thì đúng là phải "not found". `status` là dữ liệu **tuỳ chọn**, lọc thêm — không có vẫn xem được danh sách đầy đủ, nên dùng query string qua `[SupplyParameterFromQuery]` với giá trị mặc định `"all"`. Vào `/orders/7` (không có `status`) vẫn hoạt động bình thường, hiển thị "lọc theo trạng thái all"; vào `/orders/7?status=shipped` hiển thị đúng trạng thái đã lọc. Đây là ví dụ trực tiếp áp dụng nguyên tắc phân biệt route parameter và query string đã nêu ở mục 7.

---

## Tự kiểm tra

1. Điều gì xảy ra khi một component không có `@page` — nó có truy cập được qua URL không, và có báo lỗi build không?
2. Vì sao tên property `[Parameter]` phải khớp tên route parameter trong `@page`, và điều gì xảy ra khi sai tên (có báo lỗi build không)?
3. Khác biệt hành vi giữa `<a href="...">` và `<NavLink href="...">` khi URL hiện tại khớp chính xác href đó?
4. Vì sao nút dùng `onclick="TenHam()"` (không có `@`) không gọi được phương thức C# trong `@code{}`?
5. Query string thiếu `[Parameter]` đi kèm `[SupplyParameterFromQuery]` gây lỗi ở giai đoạn nào — build hay runtime?
6. Nêu khác biệt về cách "báo lỗi" khi route constraint `{id:int}` không khớp, so với khi query string `?page=abc` không parse được thành `int`.
7. `Router` trong `App.razor` dùng phần nào (`<Found>` hay `<NotFound>`) để hiển thị nội dung khi không có `@page` nào khớp URL hiện tại?
8. `NavigateTo(url, forceLoad: true)` khác `NavigateTo(url)` (mặc định) như thế nào — nêu ảnh hưởng cụ thể tới state trong bộ nhớ ứng dụng?
9. Trong tình huống "khách xem đơn hàng của mình, có thể lọc theo trạng thái" — vì sao `customerId` nên là route parameter còn `status` nên là query string, không phải ngược lại?

??? note "Đáp án"
    1. Component vẫn compile được, **không báo lỗi build** — nhưng gõ URL bất kỳ vào nó sẽ không tìm thấy trang, `Router` hiển thị nội dung `<NotFound>` (mặc định "Sorry, there's nothing at this address").
    2. Blazor Router dùng đúng tên (không phân biệt hoa/thường) để gán giá trị từ URL vào property. Sai tên **không báo lỗi build** — property vẫn giữ giá trị mặc định (ví dụ `0` cho `int`), một lỗi runtime im lặng, khó phát hiện nếu không test giá trị khác mặc định.
    3. Cả hai đều điều hướng đúng, nhưng `NavLink` tự động thêm class CSS `active` vào chính nó khi khớp URL hiện tại — `<a>` thường không có hành vi này, không tự tô sáng được.
    4. `onclick` (không `@`) là thuộc tính HTML chuẩn, trình duyệt hiểu là gọi hàm **JavaScript** toàn cục — không tìm thấy hàm JS tên đó (vì đó là phương thức C#), gây lỗi console `ReferenceError`, không gọi được code C#. Phải dùng `@onclick` để Blazor gắn đúng trình xử lý event vào C#.
    5. Ở giai đoạn **build** — Blazor analyzer từ chối compile property có `[SupplyParameterFromQuery]` mà thiếu `[Parameter]` đi kèm, báo lỗi ngay khi build, không đợi tới runtime.
    6. Route constraint không khớp (`{id:int}` gặp `/products/abc`) khiến **cả route không khớp**, Router coi như không có `@page` nào phù hợp, hiển thị "not found" toàn trang. Query string không parse được (`?page=abc` cho `int Page`) thì **route vẫn khớp bình thường**, property chỉ im lặng giữ giá trị mặc định, không có thông báo lỗi nào hiển thị.
    7. `<NotFound>` — phần này render khi URL hiện tại không khớp bất kỳ `@page` nào đã khai báo trong assembly.
    8. `NavigateTo(url)` (mặc định `forceLoad: false`) điều hướng phía client, không tải lại trang, **giữ nguyên** mọi state trong bộ nhớ (biến, service scoped). `NavigateTo(url, forceLoad: true)` buộc trình duyệt tải lại toàn bộ trang từ server, giống F5 rồi vào URL mới — **mất hoàn toàn** state đang có trong bộ nhớ, phải khởi tạo lại từ đầu.
    9. `customerId` là dữ liệu **bắt buộc, định danh chính** của trang — không có nó, trang "đơn hàng của khách nào" không có nghĩa gì, thiếu nó nên là "not found" hợp lý (đúng hành vi route parameter). `status` chỉ là bộ lọc **tuỳ chọn** trên dữ liệu đã xác định — thiếu nó vẫn xem được danh sách đầy đủ (mặc định "tất cả"), không nên làm cả trang "not found" chỉ vì thiếu một bộ lọc (đúng hành vi query string).

---

??? abstract "DEEP DIVE — route order, catch-all parameter, và lazy loading route"
    **Route order không quan trọng như Minimal API tuyến tính:** ở Minimal API (P3), thứ tự `app.MapGet` đôi khi ảnh hưởng route nào khớp trước. Với Blazor `Router`, mọi `@page` trong assembly được quét và Router tự chọn route **cụ thể nhất** khớp URL (route có constraint chặt hơn được ưu tiên hơn route chung), không phụ thuộc thứ tự file hay thứ tự khai báo `@page` trong cùng file.

    **Catch-all route parameter (`{*path}`):** ngoài `{id:int}`, Blazor còn hỗ trợ cú pháp `{*segment}` để một route "bắt" toàn bộ phần còn lại của URL vào một property `string`, dùng cho các trường hợp như trang tài liệu render theo đường dẫn tuỳ ý (`/docs/huong-dan/cai-dat` → `segment = "huong-dan/cai-dat"`). Đây là tính năng nâng cao, chỉ cần biết nó tồn tại, không dùng thường xuyên với CRUD app cơ bản.

    **`[Parameter]` từ route/query vs từ component cha:** cùng một attribute `[Parameter]` được dùng cho **ba nguồn khác nhau** — (1) route parameter từ `@page "/x/{id}"`, (2) query string khi có thêm `[SupplyParameterFromQuery]`, (3) truyền trực tiếp từ component cha qua `<ComponentCon Value="5" />` (đã học ở bài component cơ bản). Blazor phân biệt ba nguồn này dựa vào **có mặt hay không của route template khớp tên, và có `[SupplyParameterFromQuery]` hay không** — không cần khai báo gì thêm để nói rõ "nguồn nào", framework tự suy luận.

    **Vì sao `NavigateTo` không làm mất trạng thái ứng dụng (khác `<a>` HTML thuần tải lại trang):** trong Blazor Server và Blazor WebAssembly, `NavigateTo` mặc định điều hướng **phía client** (client-side routing) — không tải lại toàn bộ trang từ server, chỉ đổi phần nội dung Router render ra, giữ nguyên các service/state đã khởi tạo trong bộ nhớ (trừ khi bạn gọi `NavigateTo(url, forceLoad: true)` để cố ý buộc tải lại toàn trang, ví dụ khi cần reset hoàn toàn state hoặc chuyển sang một trang ngoài ứng dụng Blazor).

    **`AdditionalAssemblies` khi routing trải trên nhiều project:** nếu ứng dụng chia thành nhiều class library (ví dụ một library chứa các trang "Admin" riêng), `Router` chỉ quét `AppAssembly` mặc định — muốn `@page` trong library khác được nhận diện, phải thêm `AdditionalAssemblies="new[] { typeof(AdminPage).Assembly }"` vào `<Router>`. Quên bước này khiến toàn bộ trang trong library đó luôn "not found" dù `@page` khai báo đúng cú pháp — một biến thể khác của lỗi "quên `@page`" nhưng nguyên nhân là Router không biết để quét, không phải thiếu directive.

    **Sự khác biệt giữa Blazor Server và Blazor WebAssembly ảnh hưởng gì tới routing:** cơ chế `@page`/`Router`/`NavLink`/`NavigationManager` **giống nhau hoàn toàn** giữa hai mô hình hosting — Blazor WebAssembly chạy hoàn toàn trong browser qua WASM runtime (không cần server sau khi tải xong, trừ khi gọi API), còn Blazor Server chạy trên server và dùng SignalR gửi UI diff qua browser (cần kết nối mạng liên tục). Sự khác biệt duy nhất liên quan tới routing là **tốc độ phản hồi khi điều hướng**: Blazor WebAssembly điều hướng client-side nhanh vì mọi thứ đã có sẵn trong browser; Blazor Server vẫn điều hướng client-side (không tải lại trang) nhưng việc render nội dung mới đòi hỏi round-trip qua SignalR tới server — nếu mất kết nối mạng giữa lúc điều hướng, Blazor Server sẽ hiển thị thông báo "đang kết nối lại", còn Blazor WebAssembly (trừ phần gọi API) vẫn điều hướng được bình thường.

    **`LocationChanged` — theo dõi mọi lần điều hướng, không chỉ trong component hiện tại:** `NavigationManager` có event `LocationChanged`, cho phép một component (thường là layout hoặc một service chạy suốt vòng đời ứng dụng) biết **mỗi khi URL đổi**, bất kể đổi bằng cách nào (click `NavLink`, gõ URL, hay gọi `NavigateTo` từ bất kỳ đâu):

    ```razor title="MainLayout.razor — lắng nghe LocationChanged để log mỗi lần điều hướng"
    @inject NavigationManager Navigation
    @implements IDisposable

    @code {
        protected override void OnInitialized()
        {
            Navigation.LocationChanged += HandleLocationChanged;
        }

        private void HandleLocationChanged(object? sender, LocationChangedEventArgs e)
        {
            Console.WriteLine($"Điều hướng tới: {e.Location}");
        }

        public void Dispose()
        {
            Navigation.LocationChanged -= HandleLocationChanged;
        }
    }
    ```

    Đây là một ví dụ điển hình của quy tắc đã nêu trong tiêu chuẩn nội dung: component đăng ký (subscribe) một event của service tiêm qua DI nên implement `IDisposable` và **hủy đăng ký (unsubscribe) trong `Dispose()`** — nếu quên dòng `Navigation.LocationChanged -= HandleLocationChanged;`, mỗi lần component này được tạo lại (ví dụ do điều hướng qua lại nhiều lần) sẽ **tích lũy thêm một trình xử lý event mới** mà cái cũ không bị gỡ, gây memory leak và khiến cùng một lần điều hướng bị log lặp lại nhiều lần theo thời gian sử dụng ứng dụng — lỗi tăng dần, không lộ ra ngay từ đầu mà chỉ rõ dần sau khi người dùng điều hướng qua nhiều trang.

    **Quan hệ giữa `NavLink`/`NavigationManager` và `AuthenticationStateProvider`:** một pattern thường gặp là kiểm tra trạng thái đăng nhập trước khi cho vào một route (ví dụ trang `/admin`). Việc này **không** nằm trong phạm vi của `@page`, `NavLink`, hay `NavigationManager` — các khái niệm ở bài này chỉ quan tâm "URL nào ứng với component nào" và "làm sao chuyển URL", còn "ai được phép xem" là trách nhiệm của `AuthenticationStateProvider` (lớp trung tâm cung cấp trạng thái đăng nhập cho toàn bộ cây component) kết hợp với attribute `[Authorize]` — một chủ đề riêng sẽ học ở bài Authentication & Authorization trong Blazor, không lấn sang phạm vi của bài này.

Tiếp theo -> quan ly state va cascading parameters trong blazor
