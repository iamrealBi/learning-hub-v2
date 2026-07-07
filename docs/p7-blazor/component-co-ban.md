---
tier: core
status: core
owner: core-team
verified_on: "2026-07-03"
dotnet_version: "10.0"
bloom: áp dụng
requires: [p7-overview]
est_minutes_fast: 45
---

# Component cơ bản: .razor, Parameter, Lifecycle

!!! info "bạn đang ở đây · p7 → node `p7-component`"
    cần trước: bạn đã biết HTML/CSS cơ bản và C# (từ P1), và bạn vừa biết Blazor là gì ở mức tổng quan (chương `p7-overview`) — Blazor Server chạy trên server dùng SignalR gửi UI diff qua browser (cần kết nối mạng liên tục, không chạy offline), Blazor WebAssembly chạy hoàn toàn trong browser qua WASM runtime (không cần server sau khi tải xong, trừ khi gọi API). Chương này **chưa** dạy cách chạy dự án Blazor hay khác biệt Server/WebAssembly sâu hơn — chương này dạy đơn vị nhỏ nhất bên trong mọi trang Blazor, dùng chung cho cả hai mô hình host: **component**.
    mở khoá: năng lực viết một component `.razor` nhận dữ liệu từ cha qua `[Parameter]`, nhúng nội dung tuỳ ý qua `ChildContent`, và biết đúng thời điểm nào code của bạn chạy trong vòng đời component — nền tảng bắt buộc trước khi học data binding, form, routing, hay JS Interop ở các chương sau (những chương đó đều giả định bạn đã đọc được và viết được một component `.razor` cơ bản).

> **Mục tiêu (đo được):** sau chương này bạn **viết** được một component `.razor` độc lập nhận một hoặc nhiều `[Parameter]`, **áp dụng** được `ChildContent`/`RenderFragment` để bọc nội dung tuỳ ý từ component cha, **giải thích** được đúng thứ tự gọi giữa `OnInitializedAsync` và `OnParametersSetAsync`, **nhận diện** được lỗi cụ thể khi gọi API bất đồng bộ trong constructor thay vì `OnInitializedAsync`, và **phân biệt** được khi nào một thuộc tính cần `[Parameter]` với khi nào chỉ cần một field/thuộc tính nội bộ bình thường.

---

## 0. Đoán nhanh trước khi học

Cho component sau:

```razor title="Đoán.razor"
<h3>@Title</h3>
```

```csharp title="Đoán.razor @code (trích riêng để đọc)"
// test:skip trich @code cua component .razor de doc rieng, khong phai file .cs doc lap
[Parameter]
public string Title { get; set; } = "";
```

Component cha gọi nó bằng `<Doan Title="Xin chào" />`. Giả sử bạn xoá dòng `[Parameter]` phía trên `Title`, chỉ giữ lại `public string Title { get; set; } = "";`. Chuyện gì xảy ra khi build?

??? note "Đáp án"
    Build **lỗi**. Thuộc tính `Title` không tự động trở thành nơi nhận dữ liệu từ cha chỉ vì nó là `public` — Blazor cần đúng attribute `[Parameter]` để biết thuộc tính đó là "cổng vào" hợp lệ từ bên ngoài. Compiler kiểm tra việc này ngay tại thời điểm build (không đợi tới runtime): mọi attribute bạn gán trên tag component (`Title="Xin chào"`) phải khớp với một thuộc tính có `[Parameter]` trong component đó — thiếu attribute, build báo lỗi dạng "Object of type 'Doan' does not have a property matching the name 'Title'". Đây chính là khái niệm mục 2 của chương này.

Một câu đố thứ hai, nhỏ hơn, để làm rõ ranh giới giữa "component" và "file HTML thường": giả sử bạn tạo một file tên `dashboard-panel.razor` (chữ thường, có gạch ngang) trong cùng thư mục với các component khác, rồi thử dùng nó ở nơi khác bằng `<dashboard-panel />`. Điều gì xảy ra?

??? note "Đáp án"
    Không dùng được như một component qua cú pháp tag PascalCase quen thuộc — Blazor sinh ra tên class C# từ tên file, và C# không cho phép tên class chứa dấu gạch ngang hay bắt đầu bằng chữ thường theo quy ước thông thường; thực tế trình biên dịch Razor sẽ báo lỗi hoặc buộc bạn phải viết lại tên file đúng quy ước. Quy ước bắt buộc: tên file `.razor` phải viết hoa chữ đầu mỗi từ (PascalCase), không dấu gạch ngang, ví dụ `DashboardPanel.razor` — khi đó gọi bằng `<DashboardPanel />` mới hợp lệ.

---

## 1. Component là gì

**Định nghĩa (một câu):** Component trong Blazor là **một đơn vị UI tái sử dụng được**, gói gọn cả cấu trúc hiển thị (HTML) và logic xử lý (C#) trong **một file duy nhất** có phần mở rộng `.razor`.

Khác với một trang HTML tĩnh, một component `.razor` trộn hai thứ trong cùng một file: phần trên là markup gần giống HTML (gọi là **cú pháp Razor** — cho phép chèn biểu thức C# ngay giữa HTML bằng ký hiệu `@`), phần dưới là một khối `@code { ... }` chứa C# thuần — biến, thuộc tính, phương thức. Khi build, compiler biến file `.razor` thành một class C# thật (kế thừa `ComponentBase`), rồi Blazor dùng class đó để vẽ (render) ra HTML thật hiển thị trên trình duyệt. Nói cách khác: bạn không cần tự viết class C# đó — bạn viết `.razor`, compiler tự sinh class tương ứng phía sau, bạn không thấy trực tiếp trừ khi mở thư mục build trung gian (`obj/`).

### 1.1. Ví dụ tối thiểu — một component chỉ hiển thị nội dung cố định

Ví dụ tối thiểu, độc lập, chỉ minh hoạ đúng khái niệm "component là một file `.razor` hiển thị nội dung" — chưa có `[Parameter]`, chưa có lifecycle, chưa có gì khác:

```razor title="HelloCard.razor"
<div class="card">
    <p>Xin chào từ component đầu tiên!</p>
</div>
```

Dùng lại component này ở một trang khác chỉ cần viết đúng tên tag của nó, giống một tag HTML:

```razor title="Home.razor (dùng lại HelloCard)"
@page "/"

<h1>Trang chủ</h1>
<HelloCard />
<HelloCard />
```

Kết quả: đúng một khối markup trong `HelloCard.razor` được vẽ ra **hai lần**, ở đúng hai vị trí gọi `<HelloCard />`. Đây là lợi ích cốt lõi của component — viết một lần, dùng lại nhiều lần, không copy-paste HTML.

### 1.2. Component có thể chứa cả C# đơn giản ngay trong `@code`

Một component chưa cần `[Parameter]` vẫn có thể có logic riêng, tự tính toán bên trong nó — ví dụ hiển thị giờ hiện tại lúc trang được tải:

```razor title="ClockCard.razor"
<div class="card">
    <p>Trang được tải lúc: @loadedAt.ToString("HH:mm:ss")</p>
</div>

@code {
    private DateTime loadedAt = DateTime.Now;
}
```

Ở đây `loadedAt` là một **field nội bộ** — không có `[Parameter]`, không ai từ ngoài truyền được giá trị vào nó, nó chỉ tồn tại và được dùng riêng bên trong `ClockCard`. Đây là điểm cần phân biệt rõ ngay từ đầu: không phải mọi biến trong `@code` đều cần (hoặc nên) là `[Parameter]` — chỉ những gì thật sự cần component **cha bên ngoài** truyền vào mới cần đánh dấu `[Parameter]` (mục 2 sẽ đi sâu). `loadedAt` ở đây là dữ liệu component tự quản lý bên trong nó, không liên quan gì tới cha, nên để nguyên là một field `private` bình thường là đúng.

**Nếu dùng sai — hậu quả cụ thể:** nếu bạn đặt tên file `.razor` bắt đầu bằng chữ thường (ví dụ `helloCard.razor`), Blazor **không nhận** đó là một component hợp lệ để dùng như tag — quy ước bắt buộc là tên file (và do đó tên tag) phải viết hoa chữ đầu (PascalCase), giống tên class C#, vì compiler sinh ra một class C# cùng tên từ file đó. Một hậu quả khác thường gặp: nếu bạn quên đóng đúng cặp tag HTML trong markup phía trên (ví dụ mở `<div class="card">` nhưng quên `</div>`), Razor compiler báo lỗi biên dịch cụ thể dạng "no matching closing tag" — khác với HTML thuần trong trình duyệt (trình duyệt thường tự "sửa" lỗi thẻ mở/đóng lệch mà không báo gì), Razor compiler kiểm tra nghiêm ngặt cấu trúc thẻ ngay lúc build.

---

## 2. `[Parameter]` — nhận dữ liệu từ component cha

**Định nghĩa (một câu):** `[Parameter]` là một attribute đánh dấu lên một thuộc tính `public` trong `@code`, báo cho Blazor biết thuộc tính đó là **dữ liệu component cha có thể truyền xuống** cho component con, giống tham số của một hàm.

### 2.1. Ví dụ tối thiểu — một Parameter kiểu `string`

Ví dụ tối thiểu, độc lập, chỉ minh hoạ đúng một `[Parameter]` kiểu `string`:

```razor title="Greeting.razor"
<p>Xin chào, @Title!</p>

@code {
    [Parameter]
    public string Title { get; set; } = "";
}
```

Component cha truyền giá trị vào bằng cách viết tên thuộc tính (`Title`) như một attribute HTML ngay trên tag:

```razor title="Home.razor (truyền Parameter xuống Greeting)"
@page "/"

<Greeting Title="Nam" />
<Greeting Title="Lan" />
```

Kết quả hiển thị hai dòng khác nhau: "Xin chào, Nam!" và "Xin chào, Lan!" — **cùng một component** `Greeting`, nhưng mỗi lần dùng nhận một giá trị `Title` khác nhau từ cha. Đây chính là ý nghĩa "tái sử dụng được" của component: logic hiển thị viết một lần, dữ liệu hiển thị thay đổi theo từng nơi gọi.

### 2.2. Một component có thể có nhiều Parameter, kiểu dữ liệu khác nhau

Parameter không giới hạn ở `string` — có thể là `int`, `bool`, `DateTime`, hay bất kỳ kiểu C# nào (kể cả một class tự định nghĩa). Một component có thể có nhiều Parameter cùng lúc:

```razor title="ProductCard.razor"
<div class="card">
    <h4>@Name</h4>
    <p>Giá: @Price.ToString("N0") đ</p>
    @if (InStock)
    {
        <span class="badge-ok">Còn hàng</span>
    }
    else
    {
        <span class="badge-out">Hết hàng</span>
    }
</div>

@code {
    [Parameter]
    public string Name { get; set; } = "";

    [Parameter]
    public decimal Price { get; set; }

    [Parameter]
    public bool InStock { get; set; }
}
```

Component cha truyền cả ba Parameter cùng lúc, mỗi Parameter là một attribute riêng trên tag:

```razor title="Shop.razor (truyền nhiều Parameter cùng lúc)"
@page "/shop"

<ProductCard Name="Bàn phím cơ" Price="1250000" InStock="true" />
<ProductCard Name="Chuột không dây" Price="450000" InStock="false" />
```

Chú ý cách Blazor tự chuyển đổi kiểu: attribute HTML luôn là chuỗi ký tự (`Price="1250000"`), nhưng vì thuộc tính `Price` khai báo kiểu `decimal`, Blazor tự parse chuỗi đó sang `decimal` khi gán vào Parameter. Tương tự `InStock="true"` được parse thành `bool`. Đây là cơ chế tự động, bạn không cần tự viết `decimal.Parse(...)`.

### 2.3. Parameter kiểu class tự định nghĩa — truyền cả một object

Parameter không bắt buộc chỉ nhận kiểu nguyên thuỷ (`string`, `int`, `bool`) — có thể nhận cả một object phức tạp hơn, ví dụ một `record` chứa nhiều trường:

```razor title="UserBadge.razor"
<div class="badge">
    <strong>@User.Name</strong> — @User.Role
</div>

@code {
    [Parameter]
    public UserInfo User { get; set; } = new("", "");

    public record UserInfo(string Name, string Role);
}
```

Ở đây cha không truyền qua attribute chuỗi thô mà truyền qua một biểu thức C# thật (dùng `@`) trong `@code` của cha:

```razor title="Team.razor (truyền object qua Parameter)"
@page "/team"

<UserBadge User="@(new UserBadge.UserInfo("Nam", "Quản trị viên"))" />
```

Khác với ví dụ 2.2 (chuỗi tự parse), ở đây bạn phải bọc biểu thức C# bằng `@(...)` để Razor hiểu đây là một biểu thức cần tính toán ra một object `UserInfo`, không phải một chuỗi ký tự thô.

**Nếu dùng sai — hậu quả cụ thể (đúng như câu đố mục 0):** nếu quên attribute `[Parameter]` mà chỉ để `public string Title { get; set; }` trơn, viết `<Greeting Title="Nam" />` ở component cha sẽ **lỗi biên dịch** — Blazor compiler kiểm tra tại thời điểm build rằng mọi attribute bạn gán trên tag component phải khớp với một thuộc tính có `[Parameter]` (hoặc `[CascadingParameter]`) trong component đó, không khớp thì báo lỗi ngay, không đợi tới runtime.

Một lỗi khác cũng thường gặp: gán giá trị mặc định cho Parameter bằng cách gọi một phương thức phức tạp hoặc đặt logic quan trọng trong constructor — điều này **vẫn chạy được**, nhưng giá trị mặc định đó sẽ bị **ghi đè ngay** bởi giá trị cha truyền vào (nếu có), nên đặt logic quan trọng trong constructor cho Parameter là vô nghĩa; Blazor luôn gán giá trị Parameter **sau khi** object được tạo, trước khi gọi tới `OnInitialized`. Ví dụ cụ thể: nếu bạn viết `public ProductCard() { Name = "Sản phẩm mặc định"; LogCreation(Name); }` trong constructor, `LogCreation` sẽ luôn ghi log với `"Sản phẩm mặc định"` — kể cả khi cha có truyền `Name="Bàn phím cơ"` — vì constructor chạy **trước** khi Blazor gán giá trị Parameter thật từ cha.

Một lỗi thứ ba, tinh vi hơn: quên khởi tạo giá trị mặc định cho Parameter kiểu tham chiếu (ví dụ `public string Title { get; set; }` không có `= ""`). Nếu cha quên truyền `Title`, giá trị sẽ là `null` (không phải chuỗi rỗng), và nếu markup phía trên gọi `@Title.Length` hay bất kỳ phương thức nào trên `string`, bạn nhận `NullReferenceException` ngay khi render — luôn khởi tạo giá trị mặc định an toàn (`= ""`, `= 0`, `= false`) cho Parameter, trừ khi bạn chủ động muốn Parameter đó là bắt buộc và dùng `[EditorRequired]` (xem mục 2.4).

### 2.4. `[EditorRequired]` — báo cảnh báo khi cha quên truyền Parameter bắt buộc

Một Parameter có thể được đánh dấu thêm `[EditorRequired]` để báo cho công cụ (IDE, compiler) biết Parameter này **bắt buộc phải truyền**, không phải tuỳ chọn:

```razor title="RequiredTitle.razor"
<h3>@Title</h3>

@code {
    [Parameter, EditorRequired]
    public string Title { get; set; } = "";
}
```

Nếu component cha dùng `<RequiredTitle />` mà **không** truyền `Title`, bạn nhận một cảnh báo (warning, không phải lỗi cứng chặn build) ngay trong IDE hoặc log build, nhắc bạn rằng Parameter này lẽ ra phải được truyền. `[EditorRequired]` không thay đổi hành vi runtime (Parameter vẫn nhận giá trị mặc định `""` nếu cha không truyền) — nó chỉ là một tín hiệu hỗ trợ phát hiện lỗi sớm, hữu ích khi component của bạn được nhiều người khác trong team dùng lại.

---

## 3. `ChildContent`/`RenderFragment` — nhúng nội dung tuỳ ý vào giữa component

**Định nghĩa (một câu):** `ChildContent` là một `[Parameter]` đặc biệt kiểu `RenderFragment`, cho phép component cha **nhúng bất kỳ markup/component nào** vào giữa cặp tag mở-đóng của component con, thay vì chỉ truyền được giá trị đơn giản như `string`/`int`.

### 3.1. Ví dụ tối thiểu — component bọc khung quanh nội dung tuỳ ý

Ví dụ tối thiểu, độc lập, một component `Card` chỉ làm một việc: bọc khung viền quanh **bất kỳ nội dung nào** được đặt vào giữa `<Card>` và `</Card>`:

```razor title="Card.razor"
<div class="card">
    @ChildContent
</div>

@code {
    [Parameter]
    public RenderFragment? ChildContent { get; set; }
}
```

Component cha dùng `Card` bằng cách viết nội dung tuỳ ý ngay giữa cặp tag, giống cách bạn viết nội dung giữa `<div>` và `</div>` trong HTML thuần:

```razor title="Home.razor (nhúng nội dung vào Card qua ChildContent)"
@page "/"

<Card>
    <h3>Tiêu đề bên trong Card</h3>
    <p>Đoạn văn này, và cả thẻ h3 phía trên, đều là ChildContent.</p>
</Card>
```

Cơ chế: Blazor tự động gom **toàn bộ** markup nằm giữa `<Card>` và `</Card>` thành một `RenderFragment`, rồi gán nó vào đúng thuộc tính `ChildContent` — bạn không cần tự viết dòng nào gọi `ChildContent = ...`, chỉ cần đặt tên thuộc tính đúng chính xác là `ChildContent` (viết hoa, đúng chính tả) thì Blazor mới nhận diện được cơ chế đặc biệt này.

### 3.2. `ChildContent` có thể chứa cả component khác, không chỉ HTML thô

Nội dung giữa `<Card>` và `</Card>` không giới hạn ở thẻ HTML thuần — có thể là bất kỳ component nào khác, kể cả lồng nhiều component cùng lúc:

```razor title="Dashboard.razor (Card chứa cả ProductCard bên trong)"
@page "/dashboard"

<Card>
    <p>Sản phẩm nổi bật hôm nay:</p>
    <ProductCard Name="Bàn phím cơ" Price="1250000" InStock="true" />
</Card>
```

Điều này cho thấy `RenderFragment` không phải "một đoạn văn bản" — nó là một khối UI hoàn chỉnh, có thể chứa cả logic render phức tạp (component khác, vòng lặp `@foreach`, điều kiện `@if`), Blazor vẽ lại toàn bộ khối đó đúng như bạn viết ở nơi gọi.

### 3.3. Named `RenderFragment` — nhiều "cổng nhúng" khác nhau trong cùng một component

`ChildContent` là tên quy ước cho **một** cổng nhúng duy nhất, tự động gom nội dung giữa tag. Nhưng một component có thể có **nhiều** cổng nhúng khác nhau, mỗi cổng một `RenderFragment` với tên riêng — khi đó bạn phải gán rõ ràng bằng cú pháp attribute, không còn tự động gom nữa:

```razor title="Panel.razor"
<div class="panel">
    <div class="panel-header">@Header</div>
    <div class="panel-body">@Body</div>
</div>

@code {
    [Parameter]
    public RenderFragment? Header { get; set; }

    [Parameter]
    public RenderFragment? Body { get; set; }
}
```

Component cha gán từng `RenderFragment` bằng cách viết một tag con **cùng tên thuộc tính**, lồng bên trong tag `Panel`:

```razor title="Report.razor (2 RenderFragment có tên riêng)"
@page "/report"

<Panel>
    <Header>
        <h3>Báo cáo tháng 7</h3>
    </Header>
    <Body>
        <p>Doanh thu tăng 12% so với tháng trước.</p>
    </Body>
</Panel>
```

So sánh trực tiếp với 3.1: `ChildContent` là trường hợp đặc biệt — khi component chỉ có **đúng một** `RenderFragment` tên `ChildContent`, Blazor cho phép viết nội dung **thẳng** giữa tag, không cần bọc thêm tag `<ChildContent>`. Khi có nhiều `RenderFragment` (như `Header`/`Body` ở trên), bạn phải bọc riêng từng nội dung trong tag con cùng tên để Blazor biết nội dung nào thuộc `RenderFragment` nào.

**Nếu dùng sai — hậu quả cụ thể:** nếu bạn đặt tên thuộc tính khác `ChildContent` (ví dụ `Body` hay `Content`) nhưng vẫn viết nội dung trực tiếp giữa `<Card>...</Card>` mà không bọc tag con tương ứng, sẽ **lỗi biên dịch** — Blazor chỉ tự động gom nội dung giữa hai tag vào đúng thuộc tính tên `ChildContent`; muốn dùng tên khác, bạn phải gán rõ ràng bằng cú pháp bọc tag con như 3.3, hoặc viết `<Card Body="@(...)">` với một `RenderFragment` viết tay — phức tạp hơn nhiều so với việc giữ đúng tên quy ước `ChildContent` khi component chỉ cần một cổng nhúng duy nhất.

Một lỗi khác: nếu một component có **cả** `ChildContent` **và** một `RenderFragment` tên khác (ví dụ `Header`), và bạn viết nội dung không bọc tag `<Header>` mà để lẫn thẳng ngoài, Blazor sẽ gom **toàn bộ** nội dung không được bọc tag riêng vào `ChildContent` — không tự động "đoán" bạn muốn nội dung đó thuộc `Header`. Luôn bọc rõ tag con đúng tên cho mọi `RenderFragment` không phải `ChildContent`.

---

## 4. Lifecycle: `OnInitialized`/`OnInitializedAsync`

**Định nghĩa (một câu):** `OnInitialized`/`OnInitializedAsync` là hai lifecycle method có sẵn từ `ComponentBase` (lớp cha mọi component `.razor` ngầm kế thừa), chạy **đúng một lần duy nhất** ngay sau khi component được tạo ra và các `[Parameter]` đã được gán giá trị lần đầu — đây là nơi đúng để đặt code khởi tạo, ví dụ gọi API lấy dữ liệu ban đầu.

### 4.1. Ví dụ tối thiểu — in log để thấy `OnInitializedAsync` chạy đúng một lần

Ví dụ tối thiểu, độc lập, chỉ in log để thấy `OnInitializedAsync` chạy đúng một lần khi component được tạo:

```razor title="LogInit.razor"
<p>Xem log ở console trình duyệt (F12) để thấy thứ tự gọi.</p>

@code {
    protected override async Task OnInitializedAsync()
    {
        Console.WriteLine("OnInitializedAsync chạy — component vừa được tạo.");
        await Task.Delay(100); // giả lập một lệnh gọi API bất đồng bộ
        Console.WriteLine("OnInitializedAsync xong — dữ liệu đã sẵn sàng.");
    }
}
```

Ghi đè (`override`) đúng tên phương thức này, gọi từ khoá `base.OnInitializedAsync()` nếu component cha (base class) của bạn cũng có logic khởi tạo riêng cần giữ (không cần thiết ở ví dụ trên vì `ComponentBase` mặc định không làm gì đặc biệt trong `OnInitializedAsync`).

### 4.2. Có cả bản đồng bộ (`OnInitialized`) và bất đồng bộ (`OnInitializedAsync`)

Nếu logic khởi tạo của bạn **không** cần chờ gì cả (không gọi API, không `await` bất kỳ thứ gì), bạn có thể dùng bản đồng bộ `OnInitialized` (không có `Async`, trả về `void`), đơn giản hơn:

```razor title="Counter.razor (dùng OnInitialized đồng bộ)"
<p>Giá trị khởi tạo: @count</p>

@code {
    private int count;

    protected override void OnInitialized()
    {
        count = 10; // chỉ gán giá trị, không cần await gì
    }
}
```

Quy tắc chọn: nếu logic khởi tạo có gọi bất kỳ thứ gì trả về `Task` mà bạn cần `await` (gọi `HttpClient`, đọc `localStorage` qua JS Interop, đợi một `Task.Delay`...), dùng `OnInitializedAsync`. Nếu chỉ là tính toán/gán giá trị thuần C# không cần chờ, dùng `OnInitialized` cho gọn — cả hai **không** chạy cùng lúc lần lượt, bạn chỉ override đúng một trong hai theo nhu cầu thực tế (nếu override cả hai, cả hai đều chạy, nhưng thường không cần thiết).

### 4.3. Ví dụ thực tế hơn — gọi một "service" giả lập lấy dữ liệu ban đầu

```razor title="UserProfile.razor"
<p>@(isLoading ? "Đang tải..." : userName)</p>

@code {
    private string userName = "";
    private bool isLoading = true;

    protected override async Task OnInitializedAsync()
    {
        isLoading = true;
        userName = await FakeUserApi.GetCurrentUserNameAsync();
        isLoading = false;
    }
}
```

Điểm quan trọng: trước khi `OnInitializedAsync` hoàn tất (trước dòng `await FakeUserApi.GetCurrentUserNameAsync()` trả về), Blazor **đã vẽ** component ra màn hình một lần với `isLoading = true` (hiển thị "Đang tải..."), rồi khi `OnInitializedAsync` hoàn tất, Blazor **tự động vẽ lại** component với dữ liệu mới (`userName` đã có giá trị, `isLoading = false`). Đây là lý do khuôn mẫu "cờ `isLoading`" rất phổ biến trong Blazor — cho người dùng thấy trạng thái đang tải, thay vì một màn hình trống bí ẩn trong lúc chờ API.

**Lỗi thường gặp — hậu quả cụ thể:** một lập trình viên mới quen C# thường phản xạ đặt logic khởi tạo trong **constructor** của class, giống mọi class C# thông thường. Nhưng constructor là đồng bộ (`sync`) tuyệt đối — không có khái niệm `async` constructor trong C#. Nếu bạn cố gọi một API bất đồng bộ ngay trong constructor của component (ví dụ `public MyComponent() { LoadDataAsync(); }` không `await`), hậu quả cụ thể là: component **vẽ ra màn hình trước khi** dữ liệu API trả về (vì `LoadDataAsync()` không được `await`, constructor chạy tiếp ngay, không đợi), người dùng thấy giao diện trống hoặc lỗi `NullReferenceException` khi component cố hiển thị dữ liệu chưa tồn tại. Cách đúng bắt buộc là dùng `OnInitializedAsync` — một lifecycle method Blazor **chủ động chờ** (`await`) trước khi tiếp tục vẽ giao diện.

Một biến thể của lỗi trên: gọi `LoadDataAsync()` trong constructor **có** `async void` (`public async void LoadDataAsync() { ... }` gọi trong constructor mà không `await`) — về mặt cú pháp code này build được, nhưng hậu quả runtime tương tự: exception xảy ra bên trong một `async void` method **không** được Blazor bắt và xử lý gọn gàng, có thể làm crash tiến trình (ở Blazor Server) hoặc lỗi khó truy vết trong console (ở WebAssembly), khác hẳn với exception xảy ra trong `OnInitializedAsync` (Blazor có cơ chế xử lý exception cho các lifecycle method chính thức).

---

## 5. Lifecycle: `OnParametersSet`/`OnParametersSetAsync`

**Định nghĩa (một câu):** `OnParametersSet`/`OnParametersSetAsync` là lifecycle method chạy **mỗi khi** component cha truyền giá trị `[Parameter]` mới xuống (kể cả lần đầu tiên, ngay trước `OnInitialized`, và mọi lần sau đó component cha re-render với giá trị Parameter thay đổi) — khác với `OnInitialized` chỉ chạy một lần duy nhất.

### 5.1. Ví dụ tối thiểu — in log để thấy thứ tự gọi giữa hai nhóm lifecycle

Ví dụ tối thiểu, độc lập, in log để thấy rõ **thứ tự gọi** giữa hai nhóm lifecycle:

```razor title="LogOrder.razor"
<p>UserId hiện tại: @UserId</p>

@code {
    [Parameter]
    public int UserId { get; set; }

    protected override void OnInitialized()
    {
        Console.WriteLine("1) OnInitialized — chạy đúng 1 lần khi component được tạo.");
    }

    protected override void OnParametersSet()
    {
        Console.WriteLine($"2) OnParametersSet — chạy mỗi khi Parameter đổi. UserId = {UserId}");
    }
}
```

Nếu component cha đổi `UserId` truyền xuống nhiều lần (ví dụ người dùng bấm nút chuyển từ xem hồ sơ user 1 sang user 2), log console hiện ra đúng thứ tự sau:

```text title="Thứ tự log thực tế trên console trình duyệt"
1) OnInitialized — chạy đúng 1 lần khi component được tạo.
2) OnParametersSet — chạy mỗi khi Parameter đổi. UserId = 1
2) OnParametersSet — chạy mỗi khi Parameter đổi. UserId = 2
2) OnParametersSet — chạy mỗi khi Parameter đổi. UserId = 3
```

Điểm mấu chốt: `OnInitialized` chỉ xuất hiện **một lần đầu tiên**, còn `OnParametersSet` xuất hiện **lại mỗi lần** `UserId` được cha gán giá trị mới — kể cả lần đầu (ngay sau `OnInitialized`) và mọi lần tiếp theo trong suốt đời sống component (component không bị huỷ đi tạo lại, chỉ nhận Parameter mới).

### 5.2. Ví dụ thực tế — tải lại dữ liệu đúng theo Parameter mới

```razor title="UserProfileByCard.razor (component con nhận UserId từ cha)"
<p>@(isLoading ? "Đang tải..." : userName)</p>

@code {
    [Parameter]
    public int UserId { get; set; }

    private string userName = "";
    private bool isLoading = true;

    protected override async Task OnParametersSetAsync()
    {
        isLoading = true;
        userName = await FakeUserApi.GetUserNameByIdAsync(UserId);
        isLoading = false;
    }
}
```

```razor title="TeamSwitcher.razor (component cha đổi UserId theo lựa chọn)"
@page "/team-switcher"

<button @onclick="() => selectedUserId = 1">User 1</button>
<button @onclick="() => selectedUserId = 2">User 2</button>

<UserProfileByCard UserId="selectedUserId" />

@code {
    private int selectedUserId = 1;
}
```

Mỗi lần người dùng bấm nút đổi `selectedUserId`, Blazor render lại `TeamSwitcher`, truyền `UserId` mới xuống `UserProfileByCard`, và `OnParametersSetAsync` của component con chạy lại đúng theo giá trị mới — tải lại `userName` tương ứng. Nếu đặt logic này trong `OnInitializedAsync` thay vì `OnParametersSetAsync`, bấm nút đổi user sẽ **không** cập nhật gì cả (xem 5.3 và mục Cạm bẫy).

### 5.3. Vì sao "chạy lại mỗi khi Parameter đổi" đôi khi gây lãng phí — và cách kiểm tra giá trị có thực sự đổi

Một chi tiết nâng cao nhưng quan trọng: `OnParametersSet`/`OnParametersSetAsync` chạy **mỗi khi component cha render lại và truyền Parameter xuống lần nữa** — kể cả khi giá trị Parameter đó **không hề thay đổi** so với lần trước (ví dụ cha render lại vì một lý do khác, vẫn truyền đúng `UserId="1"` như cũ). Nếu logic trong `OnParametersSetAsync` là một lệnh gọi API tốn kém (ví dụ tải cả một danh sách lớn), gọi lại API mỗi lần cha render lại — dù `UserId` không đổi — là lãng phí không cần thiết.

Cách xử lý phổ biến: tự lưu lại giá trị Parameter cũ, so sánh với giá trị mới, chỉ tải lại khi thực sự khác:

```razor title="UserProfileOptimized.razor"
<p>@(isLoading ? "Đang tải..." : userName)</p>

@code {
    [Parameter]
    public int UserId { get; set; }

    private int? loadedForUserId;
    private string userName = "";
    private bool isLoading;

    protected override async Task OnParametersSetAsync()
    {
        if (loadedForUserId == UserId)
            return; // Parameter không đổi thật, khỏi tải lại

        isLoading = true;
        userName = await FakeUserApi.GetUserNameByIdAsync(UserId);
        loadedForUserId = UserId;
        isLoading = false;
    }
}
```

Đây không phải kiến thức bắt buộc phải nhớ ngay ở chương nhập môn này, nhưng cần biết nó tồn tại: `OnParametersSet` không tự động "thông minh" biết Parameter có đổi giá trị thật hay không — nó chỉ đơn giản là "chạy mỗi khi cha truyền Parameter lại", việc kiểm tra "có đổi thật không" là trách nhiệm của code bạn viết bên trong, nếu cần tối ưu.

**Nếu dùng sai — hậu quả cụ thể:** nếu bạn đặt logic "tải dữ liệu theo `UserId`" trong `OnInitializedAsync` thay vì `OnParametersSetAsync`, dữ liệu chỉ tải **đúng một lần** cho `UserId` đầu tiên — khi component cha đổi `UserId` từ 1 sang 2 (component không bị huỷ, chỉ nhận Parameter mới), giao diện vẫn hiển thị dữ liệu cũ của user 1 vì `OnInitializedAsync` không chạy lại. Đây là lỗi hành vi runtime rất phổ biến: component "không cập nhật" khi Parameter đổi — nguyên nhân hầu như luôn là đặt sai lifecycle method, đặt logic phụ thuộc Parameter vào `OnInitialized` (chạy 1 lần) thay vì `OnParametersSet` (chạy mỗi lần đổi).

---

## 6. Kết hợp lại: một ví dụ đầy đủ dùng cả 4 khái niệm cùng lúc

Bốn khái niệm ở trên (component, `[Parameter]`, `ChildContent`, hai nhóm lifecycle) hiếm khi xuất hiện đơn lẻ trong thực chiến — một component thật thường dùng cả bốn cùng lúc. Ví dụ dưới đây gộp lại đúng những gì đã học ở mục 1-5, **không** thêm khái niệm mới nào (không `@bind`, không `@onclick` — những thứ đó thuộc chương data binding kế tiếp), để bạn thấy chúng khớp với nhau ra sao trong một component gần với thực tế hơn.

Component `UserPanel` hiển thị thông tin một user theo `UserId` do cha truyền, bọc trong khung `Card` (dùng lại `ChildContent` đã học ở mục 3), và có cả hai nhóm lifecycle:

```razor title="UserPanel.razor"
<Card>
    <h4>Hồ sơ người dùng #@UserId</h4>
    @if (isLoading)
    {
        <p>Đang tải...</p>
    }
    else
    {
        <p>Tên: @userName</p>
        <p>Phiên xem hồ sơ: @viewCount lần</p>
    }
</Card>

@code {
    [Parameter]
    public int UserId { get; set; }

    private string userName = "";
    private bool isLoading = true;
    private int viewCount; // field nội bộ, KHÔNG cần [Parameter] — chỉ component tự đếm cho riêng nó

    protected override void OnInitialized()
    {
        // Chạy đúng 1 lần — khởi tạo trạng thái không phụ thuộc UserId.
        Console.WriteLine("UserPanel được tạo lần đầu.");
    }

    protected override async Task OnParametersSetAsync()
    {
        // Chạy mỗi khi UserId đổi (kể cả lần đầu) — tải lại đúng theo UserId mới.
        isLoading = true;
        userName = await FakeUserApi.GetUserNameByIdAsync(UserId);
        viewCount++;
        isLoading = false;
    }
}
```

Soi lại đúng 4 khái niệm trong ví dụ này:

1. **Component** — cả `UserPanel` và `Card` (dùng lại từ mục 3.1) đều là component `.razor` độc lập, tái sử dụng được.
2. **`[Parameter]`** — `UserId` là cổng nhận dữ liệu duy nhất từ cha; `viewCount` **không** có `[Parameter]` vì nó là số liệu nội bộ, không ai từ ngoài cần (hoặc nên) truyền vào.
3. **`ChildContent`** — toàn bộ khối `<h4>...</h4>` và `@if/else` bên trong được Blazor tự gom thành `ChildContent` của `Card`, vẽ ra đúng vị trí `@ChildContent` trong `Card.razor`.
4. **Lifecycle** — `OnInitialized` chạy đúng 1 lần (log "được tạo lần đầu"), `OnParametersSetAsync` chạy lại mỗi khi `UserId` đổi (tải `userName` mới, tăng `viewCount`).

Component cha dùng `UserPanel` giống mọi component khác, chỉ cần truyền đúng `UserId`:

```razor title="Directory.razor (dùng UserPanel, đổi UserId theo lựa chọn)"
@page "/directory"

<button @onclick="() => currentUserId = 1">Xem user 1</button>
<button @onclick="() => currentUserId = 2">Xem user 2</button>

<UserPanel UserId="currentUserId" />

@code {
    private int currentUserId = 1;
}
```

(Cú pháp `@onclick` ở component cha trên chỉ dùng để có một cách đổi `UserId` sinh động khi bạn tự chạy thử — `@onclick` và xử lý sự kiện chi tiết là nội dung chương data binding kế tiếp, không phải trọng tâm ở đây.)

---

## Cạm bẫy & thực chiến

- **Quên `[Parameter]` trên thuộc tính public** — lỗi biên dịch ngay khi component cha gán attribute không khớp thuộc tính nào có `[Parameter]` (mục 0, mục 2). Luôn kiểm tra thuộc tính nhận dữ liệu từ cha có đúng attribute này.
- **Gọi API bất đồng bộ trong constructor** — constructor là đồng bộ tuyệt đối, không `await` được; hậu quả là component vẽ ra trước khi dữ liệu sẵn sàng, dễ gây `NullReferenceException`, hoặc tệ hơn (nếu dùng `async void`) exception không được Blazor bắt gọn gàng. Luôn dùng `OnInitializedAsync` cho khởi tạo cần `await`.
- **Đặt logic phụ thuộc Parameter vào `OnInitialized` thay vì `OnParametersSet`** — dữ liệu chỉ tải đúng lần đầu, không cập nhật khi cha đổi Parameter sau đó. Nếu logic của bạn cần chạy lại mỗi khi một Parameter cụ thể đổi, đặt nó trong `OnParametersSet`/`OnParametersSetAsync`.
- **Đặt tên khác `ChildContent` mà vẫn viết nội dung trực tiếp giữa cặp tag component, không bọc tag con** — lỗi biên dịch vì Blazor chỉ tự gom nội dung giữa tag vào đúng thuộc tính tên `ChildContent`, không phải tên tuỳ ý nào khác; muốn tên khác phải bọc tag con cùng tên (mục 3.3).
- **Đặt tên file component bắt đầu bằng chữ thường hoặc chứa gạch ngang** — Blazor không nhận diện như một tag component hợp lệ; quy ước bắt buộc PascalCase cho tên file `.razor` (đồng thời là tên tag và tên class sinh ra), vì C# không cho phép tên class chứa gạch ngang.
- **Gán giá trị "mặc định phức tạp" cho Parameter ngay trong khai báo hoặc constructor** — giá trị đó luôn bị Blazor ghi đè bằng giá trị cha truyền vào (nếu có) ngay sau khi object được tạo, trước cả `OnInitialized`; đặt logic quan trọng (ví dụ ghi log, gọi API) dựa trên giá trị "mặc định" đó trong constructor là vô nghĩa vì nó chạy trước khi giá trị thật từ cha được gán.
- **Quên khởi tạo giá trị mặc định an toàn cho Parameter kiểu tham chiếu** (ví dụ `public string Title { get; set; }` không có `= ""`) — nếu cha quên truyền, giá trị là `null`, mọi lời gọi phương thức trên nó (`Title.Length`, `Title.ToUpper()`...) gây `NullReferenceException` ngay khi render.
- **Coi `OnParametersSet` như "chỉ chạy khi giá trị thật sự đổi"** — sai; nó chạy mỗi khi cha render lại và truyền Parameter xuống lần nữa, bất kể giá trị có đổi hay không. Nếu logic bên trong tốn kém (gọi API), cần tự so sánh giá trị cũ/mới để tránh gọi lại không cần thiết (mục 5.3).

---

## Bài tập

**Bài 1 (viết component):** Viết một component `Badge.razor` nhận hai `[Parameter]`: `Text` (kiểu `string`, nội dung hiển thị) và `Color` (kiểu `string`, giá trị mặc định `"gray"` nếu cha không truyền). Hiển thị một `<span>` có `style="background-color: @Color"` chứa `@Text`.

??? success "Lời giải + vì sao"
    ```razor title="Badge.razor"
    <span style="background-color: @Color; padding: 2px 8px; border-radius: 4px;">
        @Text
    </span>

    @code {
        [Parameter]
        public string Text { get; set; } = "";

        [Parameter]
        public string Color { get; set; } = "gray";
    }
    ```

    **Vì sao:** cả `Text` và `Color` đều cần `[Parameter]` để component cha truyền được giá trị vào qua attribute trên tag (`<Badge Text="Mới" Color="red" />`). `Color` có giá trị mặc định `"gray"` ngay trong khai báo thuộc tính (`= "gray"`) — nếu cha không truyền `Color`, giá trị mặc định này giữ nguyên vì Blazor chỉ ghi đè Parameter khi cha **thực sự** gán giá trị cho nó, không gán thì giữ nguyên default.

**Bài 2 (sửa lỗi lifecycle):** Đoạn code dưới đây định hiển thị thông tin user theo `UserId` do cha truyền vào, nhưng khi cha đổi `UserId`, giao diện **không cập nhật** tên user mới — vẫn hiện tên user cũ. Tìm lỗi và sửa.

```razor title="UserCard.razor (có lỗi)"
<p>@userName</p>

@code {
    [Parameter]
    public int UserId { get; set; }

    private string userName = "";

    protected override async Task OnInitializedAsync()
    {
        userName = await FakeApi.GetUserNameAsync(UserId);
    }
}
```

??? success "Lời giải + vì sao"
    ```razor title="UserCard.razor (đã sửa)"
    <p>@userName</p>

    @code {
        [Parameter]
        public int UserId { get; set; }

        private string userName = "";

        protected override async Task OnParametersSetAsync()
        {
            userName = await FakeApi.GetUserNameAsync(UserId);
        }
    }
    ```

    **Vì sao:** lỗi gốc đặt việc tải `userName` trong `OnInitializedAsync` — method này chỉ chạy **đúng một lần** khi component được tạo, ứng với `UserId` đầu tiên cha truyền vào. Khi cha sau đó đổi `UserId` (component không bị huỷ, chỉ nhận Parameter mới), `OnInitializedAsync` **không chạy lại**, nên `userName` giữ nguyên giá trị cũ. Đổi sang `OnParametersSetAsync` — method này chạy lại mỗi khi `UserId` (hoặc bất kỳ Parameter nào) đổi giá trị, nên `userName` được tải lại đúng theo `UserId` mới mỗi lần.

**Bài 3 (thiết kế `ChildContent` có tên riêng):** Viết một component `Alert.razor` có hai vùng nội dung riêng biệt: `Icon` (một `RenderFragment` nhỏ, ví dụ một emoji hoặc icon) và `Message` (một `RenderFragment` chứa nội dung thông báo chính). Gợi ý: không dùng `ChildContent` vì có hai vùng, phải đặt tên riêng cho từng `RenderFragment`.

??? success "Lời giải + vì sao"
    ```razor title="Alert.razor"
    <div class="alert">
        <span class="alert-icon">@Icon</span>
        <span class="alert-message">@Message</span>
    </div>

    @code {
        [Parameter]
        public RenderFragment? Icon { get; set; }

        [Parameter]
        public RenderFragment? Message { get; set; }
    }
    ```

    Dùng ở component cha:

    ```razor title="Notify.razor (dùng Alert với 2 RenderFragment có tên riêng)"
    <Alert>
        <Icon>⚠️</Icon>
        <Message>
            <strong>Cảnh báo:</strong> kho hàng sắp hết.
        </Message>
    </Alert>
    ```

    **Vì sao:** vì `Alert` cần **hai** vùng nội dung tách biệt (icon và message), không thể dùng cơ chế tự động của `ChildContent` (chỉ áp dụng khi component có đúng một `RenderFragment`). Mỗi vùng phải có `[Parameter]` kiểu `RenderFragment` với tên riêng (`Icon`, `Message`), và component cha phải bọc nội dung tương ứng trong tag con cùng tên (`<Icon>`, `<Message>`) để Blazor biết chính xác nội dung nào gán vào `RenderFragment` nào.

---

## Tự kiểm tra

1. Component trong Blazor là gì, và nó tương ứng với loại file nào?

    ??? note "Đáp án"
        Là một đơn vị UI tái sử dụng được, gói cả markup (HTML/Razor) và logic C# trong một file `.razor` duy nhất — compiler biến file này thành một class C# kế thừa `ComponentBase`.

2. Vì sao chỉ khai báo `public string Title { get; set; }` mà không thêm `[Parameter]` sẽ gây lỗi biên dịch khi component cha truyền `Title="..."`?

    ??? note "Đáp án"
        Vì Blazor compiler kiểm tra tại thời điểm build rằng mọi attribute gán trên tag component phải khớp một thuộc tính có `[Parameter]` (hoặc `[CascadingParameter]`); một thuộc tính `public` trơn không đủ điều kiện, chỉ `public` không tự động là "cổng nhận dữ liệu từ cha".

3. `ChildContent` là gì, và tên thuộc tính này có bắt buộc viết đúng chính tả không? Vì sao?

    ??? note "Đáp án"
        Là một `[Parameter]` đặc biệt kiểu `RenderFragment` giữ toàn bộ nội dung cha đặt giữa cặp tag mở-đóng của component con. Bắt buộc đúng tên `ChildContent` — Blazor chỉ tự động gom nội dung giữa tag vào đúng tên thuộc tính này; đặt tên khác thì phải gán `RenderFragment` tường minh bằng cách bọc tag con cùng tên, cách gom tự động không áp dụng.

4. `OnInitializedAsync` chạy bao nhiêu lần trong đời sống một component? `OnParametersSetAsync` thì sao?

    ??? note "Đáp án"
        `OnInitializedAsync` chạy đúng **một lần**, ngay sau khi component được tạo. `OnParametersSetAsync` chạy **mỗi khi** component cha truyền giá trị Parameter mới xuống — bao gồm lần đầu (ngay sau `OnInitialized`) và mọi lần cha đổi Parameter sau đó, miễn component chưa bị huỷ.

5. Vì sao gọi một API bất đồng bộ trong constructor của component là sai, và hậu quả cụ thể là gì?

    ??? note "Đáp án"
        Vì constructor trong C# là đồng bộ tuyệt đối, không có khái niệm `async` constructor, không `await` được. Nếu cố gọi API không `await` trong constructor, component vẽ ra giao diện ngay khi constructor chạy xong, trước khi dữ liệu API trả về — dẫn tới giao diện trống hoặc `NullReferenceException` khi cố hiển thị dữ liệu chưa tồn tại. Cách đúng là dùng `OnInitializedAsync`, nơi Blazor chủ động `await` trước khi vẽ tiếp.

6. Một component không cập nhật giao diện khi cha đổi Parameter — nguyên nhân phổ biến nhất là gì?

    ??? note "Đáp án"
        Logic tải/tính dữ liệu phụ thuộc Parameter bị đặt sai trong `OnInitialized`/`OnInitializedAsync` (chỉ chạy 1 lần) thay vì `OnParametersSet`/`OnParametersSetAsync` (chạy lại mỗi khi Parameter đổi).

7. Quy ước đặt tên file `.razor` là gì, và điều gì xảy ra nếu vi phạm?

    ??? note "Đáp án"
        Phải viết hoa chữ đầu (PascalCase), ví dụ `HelloCard.razor`, không dấu gạch ngang, vì compiler sinh ra một class C# cùng tên từ file đó và tên đó cũng chính là tên tag dùng để gọi component. Vi phạm (ví dụ tên bắt đầu chữ thường, có gạch ngang) khiến Blazor không nhận diện được như một tag component hợp lệ, vì C# không cho tên class như vậy.

8. Nếu một component gán giá trị mặc định phức tạp cho một `[Parameter]` ngay trong khai báo (ví dụ gọi một phương thức tính toán), giá trị đó có giữ nguyên khi component cha KHÔNG truyền Parameter đó không? Còn khi cha CÓ truyền?

    ??? note "Đáp án"
        Nếu cha không truyền, giá trị mặc định đó giữ nguyên. Nếu cha có truyền, Blazor ghi đè giá trị mặc định bằng giá trị cha gửi xuống, ngay sau khi object được tạo và trước khi `OnInitialized` chạy — nên đặt logic quan trọng phụ thuộc vào giá trị "mặc định" đó (ví dụ trong constructor) là không an toàn nếu bạn mong nó luôn giữ nguyên.

9. `OnParametersSet` có tự động "biết" Parameter có thực sự thay đổi giá trị hay không trước khi chạy? Nếu không, hậu quả thực tế là gì khi logic bên trong là một lệnh gọi API tốn kém?

    ??? note "Đáp án"
        Không — `OnParametersSet`/`OnParametersSetAsync` chạy mỗi khi cha render lại và truyền Parameter xuống lần nữa, bất kể giá trị có đổi thật hay không. Nếu logic bên trong là một lệnh gọi API tốn kém, nó sẽ bị gọi lại lãng phí mỗi lần cha render lại dù Parameter không đổi, trừ khi bạn tự lưu giá trị cũ và so sánh trước khi tải lại.

10. Khi nào một thuộc tính trong `@code` KHÔNG cần `[Parameter]`?

    ??? note "Đáp án"
        Khi đó là dữ liệu component tự quản lý bên trong nó, không cần (và không nên) để component cha bên ngoài truyền vào — ví dụ một field đếm số lần bấm nút nội bộ, hoặc thời điểm component được tải (`loadedAt`). Chỉ những gì thật sự cần nhận từ cha mới cần `[Parameter]`.

---

??? abstract "DEEP DIVE: `OnAfterRender`/`OnAfterRenderAsync` và `ShouldRender` — kiểm soát sau khi vẽ và tần suất vẽ lại"
    Ngoài `OnInitialized(Async)` và `OnParametersSet(Async)`, `ComponentBase` còn cung cấp `OnAfterRender(Async)` — chạy **sau khi** component đã vẽ xong ra DOM (hoặc DOM ảo phía server, tuỳ mô hình host), tham số `bool firstRender` cho biết đây là lần vẽ đầu tiên hay một lần vẽ lại. Đây là nơi **duy nhất an toàn** để gọi JS Interop cần đọc/ghi trực tiếp phần tử DOM đã tồn tại thật (ví dụ lấy kích thước một `<div>`, khởi tạo một thư viện JavaScript bên thứ ba cần một DOM element có sẵn) — gọi JS Interop kiểu này trong `OnInitializedAsync` sẽ lỗi hoặc không ổn định, vì tại thời điểm đó phần tử DOM tương ứng **có thể chưa được vẽ ra** trên trang.

    ```razor title="ChartHost.razor (minh hoạ vị trí gọi JS Interop đúng, tham khảo)"
    <div id="chart-host"></div>

    @code {
        protected override async Task OnAfterRenderAsync(bool firstRender)
        {
            if (firstRender)
            {
                // Chỉ gọi đúng 1 lần, sau khi DOM #chart-host đã tồn tại thật.
                // await JS.InvokeVoidAsync("initChart", "chart-host");
            }
        }
    }
    ```

    Kiểm tra `firstRender` là bắt buộc trong hầu hết trường hợp — nếu không kiểm tra, code khởi tạo thư viện JS (ví dụ `initChart`) sẽ chạy lại **mỗi lần** component vẽ lại, có thể tạo ra nhiều instance chồng chéo của cùng một thư viện trên cùng một DOM element, gây lỗi hoặc rò rỉ tài nguyên phía trình duyệt.

    Một phương thức khác đáng biết: `ShouldRender()` (mặc định trả `true`) — override và trả `false` trong một số trường hợp cụ thể để **chặn** Blazor vẽ lại component, dùng khi bạn biết chắc trạng thái vừa đổi không ảnh hưởng gì tới giao diện hiển thị, tránh lãng phí một lượt render không cần thiết. Đây là một tối ưu hiệu năng nâng cao — dùng sai (trả `false` nhầm lúc UI thật sự cần cập nhật) gây ra lỗi hành vi khó phát hiện: người dùng thao tác nhưng giao diện "đứng yên", trong khi dữ liệu nền đã đổi đúng. Vì rủi ro này, `ShouldRender` chỉ nên override khi đã đo được vấn đề hiệu năng thật, không phải mặc định bật lên "cho chắc".

    Thứ tự đầy đủ khi một component được tạo lần đầu là: constructor (đồng bộ, không nên đặt logic khởi tạo nghiệp vụ) → gán giá trị `[Parameter]` lần đầu → `OnInitialized`/`OnInitializedAsync` (một lần) → `OnParametersSet`/`OnParametersSetAsync` (lần đầu, rồi lặp lại mỗi khi Parameter đổi sau đó) → render ra DOM → `OnAfterRender`/`OnAfterRenderAsync` (với `firstRender = true` ở lần đầu). Ở những lần render tiếp theo (ví dụ do cha đổi Parameter, hoặc do `StateHasChanged()` được gọi thủ công — xem chương data binding kế tiếp), thứ tự rút gọn lại thành: `OnParametersSet`/`OnParametersSetAsync` (nếu Parameter đổi) → render → `OnAfterRender`/`OnAfterRenderAsync` (với `firstRender = false`) — `OnInitialized` không xuất hiện lại vì nó chỉ dành cho đúng lần tạo component đầu tiên.

    Nắm đúng thứ tự này giúp trả lời chính xác "code của tôi nên đặt ở method nào" — câu hỏi nền tảng nhất khi mới học Blazor, và cũng là nguồn gốc phần lớn lỗi "component không cập nhật đúng lúc" hoặc "component gọi JS Interop bị lỗi vì DOM chưa tồn tại" gặp trong thực chiến.

**Tiếp theo →** [P7 · Data Binding & Sự kiện](data-binding-events.md)
