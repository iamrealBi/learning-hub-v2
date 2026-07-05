---
tier: core
status: core
owner: core-team
verified_on: "2026-07-05"
dotnet_version: "10.0"
bloom: phân tích
requires: [p7-auth]
est_minutes_fast: 25
---

# JS Interop & Component Lifecycle nâng cao

!!! info "Bạn đang ở đây"
    cần trước: component `.razor` cơ bản, lifecycle `OnInitialized`/`OnInitializedAsync`, `Parameter`, `@inject`, state container service (`event`/`IDisposable`).
    mở khoá: gọi được JavaScript từ C# (và ngược lại) khi Blazor chưa có API cho một tính năng browser, biết đúng lúc thao tác DOM an toàn (`OnAfterRenderAsync`), tham chiếu đúng phần tử DOM của từng instance (`ElementReference`), gọi ngược vào đúng instance component (`DotNetObjectReference`), và tránh hai lỗi runtime âm thầm phổ biến nhất khi danh sách hiển thị re-render (thiếu `@key`) và khi component bị gỡ khỏi cây (quên `Dispose`).

> Mục tiêu (đo được): sau chương này bạn **giải thích** được vì sao Blazor cần một cơ chế JS Interop dù đã có sẵn rất nhiều API C#, **viết** được một lệnh gọi `IJSRuntime.InvokeVoidAsync` từ C# sang JavaScript và một lệnh gọi ngược JavaScript sang C# qua `[JSInvokable]`, **phân biệt** được đúng lúc dùng `OnAfterRenderAsync` so với `OnInitializedAsync` dựa trên tham số `firstRender`, và **phân tích** được hai kịch bản lỗi cụ thể (memory leak do quên `Dispose`, mất trạng thái input do thiếu `@key`) để nhận diện chúng khi debug một ứng dụng thật.

---

## 0. Đoán nhanh trước khi học

Bạn đã biết Blazor có nhiều API C# sẵn có: `NavigationManager` để điều hướng, `IJSRuntime`... khoan, đó chính là thứ hôm nay học. Thử tình huống sau trước: bạn cần focus (đưa con trỏ nhập liệu) vào một `<input>` ngay khi trang vừa hiển thị, giống hiệu ứng "tự động click vào ô tìm kiếm" mà nhiều trang web vẫn làm.

```razor title="TimKiem.razor (thieu mot thu)"
@page "/tim-kiem"

<input id="o-tim-kiem" placeholder="Nhập từ khoá..." />

@code {
    protected override void OnInitialized()
    {
        // Bạn muốn: "focus vào input có id=o-tim-kiem ngay bây giờ".
        // Nhưng .NET/Blazor không có class nào tên là `Input.Focus("o-tim-kiem")`.
    }
}
```

??? question "Câu hỏi: tại sao Blazor — một framework C# đầy đủ — lại không có sẵn API để focus vào một ô input?"
    Vì "focus vào một phần tử HTML" là một hành vi của **trình duyệt** (browser), không phải của .NET runtime. Component Blazor (dù chạy ở WebAssembly trong trình duyệt, hay chạy trên server và gửi UI qua SignalR) rốt cuộc chỉ **mô tả** cây HTML cần hiển thị — việc "thật sự" gọi hàm `.focus()` trên một phần tử DOM là việc của JavaScript, ngôn ngữ gốc của trình duyệt. Blazor có sẵn một số API C# bọc sẵn các hành vi JavaScript **phổ biến** (`NavigationManager.NavigateTo` bọc `window.location`, ví dụ), nhưng không thể bọc sẵn **mọi** API JavaScript đang tồn tại (focus, clipboard, localStorage, Web Audio, canvas...) — số lượng quá lớn và luôn có API mới. Mục 1 giới thiệu cơ chế cho phép bạn **tự** gọi bất kỳ hàm JavaScript nào từ C#, không cần đợi Blazor bọc sẵn.

---

## 1. JS Interop là gì — định nghĩa và ví dụ tối thiểu

**Định nghĩa (một câu):** JS Interop (JavaScript Interoperability) là cơ chế cho phép code C# trong một component Blazor **gọi một hàm JavaScript** đang có trong trang (và ngược lại, JavaScript gọi lại một method C# — xem mục 2), dùng khi Blazor **chưa có API C# sẵn** cho một hành vi của trình duyệt.

Ví dụ tối thiểu, độc lập — gọi `console.log` (một hàm JavaScript có sẵn trong mọi trình duyệt, không cần viết thêm file JS nào) từ C#:

```razor title="GoiConsoleLog.razor"
@page "/demo-console-log"
@inject IJSRuntime JS

<button @onclick="InVaoConsole">In ra Console trình duyệt</button>

@code {
    private async Task InVaoConsole()
    {
        // Gọi hàm JavaScript "console.log", truyền một chuỗi làm tham số -
        // giống việc bạn gõ console.log("Xin chao tu C#!") trong DevTools.
        await JS.InvokeVoidAsync("console.log", "Xin chao tu C#!");
    }
}
```

Điểm mấu chốt: `IJSRuntime` là một service Blazor có sẵn (tiêm qua `@inject` như mọi service khác đã học), và `InvokeVoidAsync(tenHam, thamSo...)` nhận **tên hàm JavaScript dưới dạng chuỗi** (`"console.log"`) cùng các tham số cần truyền — Blazor tự chuyển các tham số C# sang JSON, gửi qua "cầu nối" giữa .NET và JavaScript (WASM runtime nếu là Blazor WebAssembly, hoặc kết nối SignalR nếu là Blazor Server), và trình duyệt thực thi đúng lệnh `console.log("Xin chao tu C#!")`. `InvokeVoidAsync` dùng khi hàm JavaScript **không trả về giá trị** cần dùng lại (giống `void` trong C#); nếu cần lấy kết quả trả về, dùng `InvokeAsync<T>` (xem ví dụ mục 3).

Chi phí thật của một lệnh JS Interop khác nhau tuỳ mô hình hosting bạn học ở chương tổng quan Blazor: với **Blazor WebAssembly**, cầu nối .NET-JavaScript nằm hoàn toàn trong cùng một trình duyệt (WASM runtime gọi trực tiếp API JavaScript của chính trang đó, không qua mạng) nên chi phí chỉ là chi phí chuyển đổi dữ liệu trong bộ nhớ; với **Blazor Server**, mọi lệnh `InvokeVoidAsync`/`InvokeAsync<T>` phải đi qua kết nối SignalR thật giữa server và trình duyệt — nghĩa là có độ trễ mạng thật, dù nhỏ (thường vài chục milliseconds trên mạng tốt), nhưng cộng dồn nếu gọi JS Interop quá nhiều lần liên tiếp (đúng lý do "Cạm bẫy" cuối bài cảnh báo gộp nhiều lệnh nhỏ thành một lệnh lớn khi có thể).

!!! danger "Lỗi runtime nếu gọi sai tên hàm hoặc gọi khi chưa có DOM"
    Nếu bạn gõ sai tên hàm (ví dụ `"console.logg"` — thừa một chữ `g`), code **build được bình thường** (chuỗi `"console.logg"` là một chuỗi hợp lệ về mặt C#), nhưng lúc chạy sẽ ném `JSException` với thông báo dạng `"console.logg is not a function"` — vì Blazor không kiểm tra được tên hàm JavaScript có tồn tại hay không lúc biên dịch (khác với gọi một method C# sai tên, vốn báo lỗi biên dịch ngay). Ngoài ra, nếu bạn gọi `InvokeVoidAsync` nhắm vào một phần tử DOM (như ví dụ mục 4, gọi `focus()` trên input) **trong `OnInitialized()`** — tức là **trước khi** Blazor vẽ xong HTML lần đầu — trình duyệt chưa có phần tử đó trong DOM, và lệnh gọi JavaScript sẽ thất bại hoặc không có tác dụng gì. Mục 4 giải thích đúng thời điểm an toàn để gọi JS Interop cần thao tác DOM.

---

## 2. Gọi ngược JavaScript → C# qua `[JSInvokable]` — định nghĩa và ví dụ tối thiểu

Mục 1 đi một chiều: C# gọi JavaScript. Nhưng có tình huống ngược lại — một sự kiện xảy ra **bên JavaScript** (ví dụ trình duyệt báo "người dùng vừa cuộn tới cuối trang", hoặc một thư viện JS bên thứ ba bắn ra một callback) và bạn cần **C# biết** để xử lý tiếp (cập nhật state, gọi API...).

**Định nghĩa (một câu):** `[JSInvokable]` là một attribute đánh dấu lên một method C# `public` (thường là `static`, hoặc method thường trên một instance được đăng ký qua `DotNetObjectReference`), cho phép JavaScript **gọi ngược lại** đúng method đó bằng tên, giống cách C# gọi JavaScript qua tên chuỗi ở mục 1 nhưng theo chiều ngược lại.

Ví dụ tối thiểu, độc lập — C# expose một method tĩnh cho JavaScript gọi vào:

```razor title="NhanThongBaoTuJs.razor"
@page "/demo-js-goi-nguoc"
@inject IJSRuntime JS

<p>Thông báo mới nhất từ JavaScript: @thongBaoMoiNhat</p>
<button @onclick="MoPhongJsGoiNguoc">Mô phỏng JS gọi ngược (bấm thử)</button>

@code {
    private string thongBaoMoiNhat = "(chưa có)";

    // [JSInvokable] cho phép JavaScript gọi ĐÚNG method này bằng tên chuỗi
    // "NhanThongBao" - giống InvokeVoidAsync("tenHam", ...) ở mục 1, nhưng
    // theo chiều JS -> C#. Method PHẢI là public và static để gọi qua kiểu
    // đơn giản này (không cần DotNetObjectReference cho method instance).
    [JSInvokable]
    public static Task<string> NhanThongBao(string noiDung)
    {
        return Task.FromResult($"Da nhan: {noiDung}");
    }

    private async Task MoPhongJsGoiNguoc()
    {
        // Trong ứng dụng thật, đoạn "gọi ngược" này nằm trong một file .js,
        // viết dạng: DotNet.invokeMethodAsync('TenAssembly', 'NhanThongBao', 'xin chao').
        // Ở đây ta gọi console.log kèm chuỗi minh hoạ, KHÔNG viết file .js
        // riêng, để giữ ví dụ độc lập - tập trung đúng vào [JSInvokable].
        thongBaoMoiNhat = await NhanThongBao("nguoi dung vua bam nut");
        await JS.InvokeVoidAsync("console.log", "C# da xu ly xong: " + thongBaoMoiNhat);
    }
}
```

Trong một ứng dụng thật, phía JavaScript (một file `.js` được nạp vào trang) sẽ gọi ngược vào đúng method `NhanThongBao` bằng cú pháp cố định của Blazor:

```text title="wwwroot/site.js (minh hoa cu phap goi nguoc - khong chay trong vi du nay)"
// DotNet.invokeMethodAsync('TenAssembly', 'NhanThongBao', 'du lieu tu JS')
//   - 'TenAssembly': tên assembly .NET chứa method (thường là tên project).
//   - 'NhanThongBao': đúng tên method đã đánh dấu [JSInvokable].
//   - 'du lieu tu JS': tham số truyền vào, khớp kiểu string của method C#.
window.addEventListener('scroll', function () {
    DotNet.invokeMethodAsync('TenAssembly', 'NhanThongBao', 'nguoi dung da cuon trang');
});
```

!!! warning "Tên method trong `[JSInvokable]` phải khớp CHÍNH XÁC chuỗi JavaScript gọi tới, và tên assembly cũng phải đúng"
    Blazor tìm method C# để gọi bằng cách so khớp **chuỗi tên** (`'NhanThongBao'`) — không có kiểm tra lúc biên dịch giữa file `.js` và method C#, vì JavaScript và C# là hai file riêng biệt, không "biết" về nhau lúc build. Nếu bạn đổi tên method C# (ví dụ refactor `NhanThongBao` thành `XuLyThongBao`) mà quên sửa chuỗi trong file `.js`, code C# vẫn build thành công (không ai báo lỗi), nhưng lúc chạy, `DotNet.invokeMethodAsync` bên JS sẽ ném lỗi JavaScript dạng "Could not find method" — một lỗi chỉ phát hiện được khi thực sự bấm thử trong trình duyệt, không phải lúc build hay lúc unit test C# thông thường.

`'TenAssembly'` trong `DotNet.invokeMethodAsync('TenAssembly', ...)` chính là tên assembly (`.dll`) chứa project Blazor của bạn — mặc định trùng tên thư mục project (ví dụ project tên `MyApp.Client` thì chuỗi cần truyền là `"MyApp.Client"`, không phải tên namespace hay tên class). Nếu gõ sai tên assembly, lỗi cũng chỉ xuất hiện lúc chạy, cùng dạng "Could not find" — cách xác nhận chắc chắn tên đúng là mở file `.csproj` của project chứa method `[JSInvokable]`, xem `<AssemblyName>` nếu có khai báo tường minh, hoặc dùng đúng tên file `.csproj` (bỏ đuôi `.csproj`) nếu không khai báo `<AssemblyName>` riêng.

---

## 3. `OnAfterRenderAsync` — định nghĩa, ví dụ, và phân biệt với `OnInitialized`

Bây giờ quay lại đúng vấn đề mục 0: focus vào input **sau khi** nó đã thực sự tồn tại trên DOM.

**Định nghĩa (một câu):** `OnAfterRenderAsync` (và bản đồng bộ `OnAfterRender`) là một lifecycle method của `ComponentBase` chạy **sau khi** Blazor đã vẽ xong HTML của component ra DOM thật của trình duyệt — khác với `OnInitializedAsync`/`OnInitialized`, chạy **trước** lần render đầu tiên, lúc DOM của component **chưa tồn tại**.

Ví dụ tối thiểu, độc lập — focus vào input đúng lúc DOM đã có:

```razor title="TimKiem.razor (da sua dung OnAfterRenderAsync)"
@page "/tim-kiem-dung"
@inject IJSRuntime JS

<input id="o-tim-kiem" placeholder="Nhập từ khoá..." />

@code {
    protected override async Task OnAfterRenderAsync(bool firstRender)
    {
        if (firstRender)
        {
            // Tại ĐÂY, <input id="o-tim-kiem"> đã tồn tại thật trong DOM
            // của trình duyệt - vì OnAfterRenderAsync chạy SAU khi Blazor
            // vẽ xong HTML lần đầu. Gọi JS Interop nhắm vào DOM ở đây an toàn.
            // Dùng "eval" (một hàm JavaScript có sẵn trên window, giống
            // console.log ở mục 1) để chạy nguyên chuỗi lệnh JS làm THAM SỐ -
            // InvokeVoidAsync không thể nhận trực tiếp một chuỗi định danh
            // chứa lệnh gọi hàm lồng bên trong như "getElementById('x').focus".
            await JS.InvokeVoidAsync("eval", "document.getElementById('o-tim-kiem').focus()");
        }
    }
}
```

Bảng đối chiếu trực tiếp hai lifecycle method — đúng điều mục 0 cần phân biệt:

| | `OnInitializedAsync`/`OnInitialized` | `OnAfterRenderAsync`/`OnAfterRender` |
|---|---|---|
| Chạy khi nào | **Trước** lần render đầu tiên | **Sau** mỗi lần render (kể cả lần đầu và mọi lần re-render sau) |
| DOM thật của component đã tồn tại chưa | **Chưa** — component chỉ mới "được tạo" trong bộ nhớ .NET | **Đã có** — HTML thật đã được trình duyệt vẽ ra |
| Dùng để làm gì | Nạp dữ liệu ban đầu (gọi API, đọc `Parameter`), gán giá trị mặc định | Thao tác DOM trực tiếp qua JS Interop (focus, đo kích thước phần tử, khởi tạo thư viện JS bên thứ ba như chart/map) |
| Gọi JS Interop nhắm vào DOM ở đây có an toàn? | **Không** — phần tử chưa tồn tại, JS Interop sẽ lỗi hoặc vô tác dụng | **Có** — đây chính là lifecycle được thiết kế cho việc này |
| Chạy lại khi nào | Một lần (`OnInitialized`) khi component được tạo | `OnAfterRender` chạy lại **mỗi lần render**, `OnInitialized` không chạy lại |

!!! danger "Gọi JS Interop nhắm DOM trong `OnInitializedAsync` — lỗi runtime cụ thể"
    Nếu bạn viết `await JS.InvokeVoidAsync("eval", "document.getElementById('o-tim-kiem').focus()")` **trong `OnInitializedAsync`** (thay vì `OnAfterRenderAsync`), lúc chạy trong trình duyệt, JavaScript sẽ thực thi `document.getElementById('o-tim-kiem')` **trước khi** Blazor vẽ input đó ra DOM — kết quả trả về là `null` (không tìm thấy phần tử), và gọi tiếp `.focus()` trên `null` ném `JSException` với thông báo dạng "Cannot read properties of null". Đây là lỗi runtime xảy ra **mỗi lần** trang tải, không phải lỗi ngẫu nhiên — nguyên nhân luôn là gọi sai lifecycle, không phải lỗi cú pháp JS Interop.

---

## 4. Tham số `firstRender` — vì sao quan trọng

Ví dụ mục 3 có dòng `if (firstRender)`. Mục này giải thích cụ thể tại sao thiếu dòng kiểm tra đó gây lỗi.

**Định nghĩa (một câu):** `firstRender` là tham số `bool` của `OnAfterRenderAsync(bool firstRender)`, có giá trị `true` **chỉ đúng một lần** — ở lần gọi đầu tiên sau khi component render lần đầu — và `false` ở **mọi lần gọi sau đó** (mỗi khi component re-render vì state đổi, parameter đổi...).

Nếu bạn bỏ điều kiện `if (firstRender)` khỏi ví dụ mục 3:

```razor title="TimKiem.razor (THIEU kiem tra firstRender - co van de)"
@page "/tim-kiem-loi"
@inject IJSRuntime JS

<input id="o-tim-kiem" placeholder="Nhập từ khoá..." @oninput="XuLyGoTim" />
<p>Kết quả: @ketQua</p>

@code {
    private string ketQua = "";

    protected override async Task OnAfterRenderAsync(bool firstRender)
    {
        // THIẾU "if (firstRender)" - dòng focus() này chạy LẠI mỗi lần
        // component render lại, tức là MỖI LẦN người dùng gõ một chữ.
        await JS.InvokeVoidAsync("eval", "document.getElementById('o-tim-kiem').focus()");
    }

    private void XuLyGoTim(ChangeEventArgs e) => ketQua = $"Đang tìm: {e.Value}";
}
```

**Hậu quả runtime cụ thể:** mỗi khi người dùng gõ một chữ vào ô input (`@oninput` bắn ra, `ketQua` đổi, Blazor re-render component, `OnAfterRenderAsync` chạy lại), lệnh `focus()` bị gọi lại — với input đơn giản này hậu quả nhỏ (focus vào chính ô đang gõ, có vẻ "vô hại" vì nó vốn đã đang có focus), nhưng nếu logic bên trong `OnAfterRenderAsync` nặng hơn (ví dụ khởi tạo lại một thư viện JS biểu đồ, gắn lại một event listener JavaScript), việc chạy lại **mỗi lần render** thay vì chỉ một lần sẽ gây khởi tạo trùng lặp — với thư viện biểu đồ, thường thấy biểu đồ bị vẽ đè nhiều lần, event listener bị gắn nhiều lần khiến một hành động của người dùng bắn ra nhiều lần xử lý trùng nhau. Luôn kiểm tra `if (firstRender)` khi logic trong `OnAfterRenderAsync` chỉ nên chạy **đúng một lần** trong đời component.

!!! note "Khi nào CẦN logic chạy lại ở MỌI lần render, không chỉ lần đầu"
    Không phải mọi thứ trong `OnAfterRenderAsync` cần bọc `if (firstRender)`. Ví dụ: nếu bạn cần đo lại chiều cao một phần tử **mỗi khi nội dung đổi** (nội dung dài ra/ngắn lại sau mỗi lần render), bạn **muốn** logic đo chạy lại mỗi lần render — chỉ bỏ `if (firstRender)` cho phần thao tác này. Quy tắc: hỏi "hành động này có nên lặp lại mỗi lần UI vẽ lại, hay chỉ cần làm đúng một lần khi component vừa xuất hiện" — câu trả lời quyết định có bọc `if (firstRender)` hay không, không phải một quy tắc máy móc "luôn luôn bọc".

---

## 5. `IDisposable` trên component — định nghĩa và ví dụ memory leak cụ thể

Phần này áp dụng lại khái niệm `IDisposable` đã gặp ở chương state management, nhưng cho một nguồn rò rỉ khác: `System.Timers.Timer` chạy nội bộ trong chính component, không qua state container service.

**Định nghĩa (một câu):** một component implement `IDisposable` khi nó tạo ra một tài nguyên **sống độc lập với vòng đời component** (timer, subscription tới event của service khác, kết nối mạng riêng) — Blazor tự động gọi `Dispose()` khi component bị loại khỏi cây (người dùng điều hướng sang trang khác), và trong `Dispose()` bạn phải chủ động dừng/huỷ tài nguyên đó, nếu không nó tiếp tục chạy dù component đã "biến mất" khỏi UI.

Ví dụ cụ thể lỗi — một component đếm giờ dùng `System.Timers.Timer`, KHÔNG huỷ khi bị gỡ:

```razor title="DongHo.razor (THIEU Dispose - memory leak)"
@page "/dong-ho-loi"
@using System.Timers

<p>Đã trôi qua: @soGiay giây</p>

@code {
    private int soGiay = 0;
    private Timer? bomHenGio;

    protected override void OnInitialized()
    {
        bomHenGio = new Timer(1000); // bắn Elapsed mỗi 1000ms
        bomHenGio.Elapsed += (sender, e) =>
        {
            soGiay++;
            InvokeAsync(StateHasChanged);
        };
        bomHenGio.Start();

        // KHÔNG CÓ Dispose() nào gọi bomHenGio.Stop()/bomHenGio.Dispose().
    }
}
```

**Kịch bản cụ thể gây lỗi:** người dùng mở trang `/dong-ho-loi`, rồi điều hướng sang trang khác (component `DongHo` bị Blazor loại khỏi cây UI, không còn hiển thị). Nhưng `bomHenGio` là một `System.Timers.Timer` **chạy trên luồng riêng của .NET runtime**, hoàn toàn độc lập với việc component còn hiển thị hay không — nó **tiếp tục chạy**, mỗi giây vẫn bắn `Elapsed`, vẫn gọi `InvokeAsync(StateHasChanged)` trên một component đã bị gỡ. Nếu người dùng lặp lại việc mở/rời trang này 10 lần, có **10 timer** đang chạy song song trong bộ nhớ, không cái nào bị dừng — mỗi giây, 10 callback chạy, gây lãng phí CPU tăng dần, và tuỳ phiên bản Blazor, gọi `StateHasChanged()` trên component đã gỡ có thể ném lỗi lúc runtime.

Cách sửa đúng — implement `IDisposable`, dừng và huỷ timer:

```razor title="DongHo.razor (da sua - co Dispose)"
@page "/dong-ho-dung"
@implements IDisposable
@using System.Timers

<p>Đã trôi qua: @soGiay giây</p>

@code {
    private int soGiay = 0;
    private Timer? bomHenGio;

    protected override void OnInitialized()
    {
        bomHenGio = new Timer(1000);
        bomHenGio.Elapsed += TangGiay;
        bomHenGio.Start();
    }

    private void TangGiay(object? sender, ElapsedEventArgs e)
    {
        soGiay++;
        InvokeAsync(StateHasChanged);
    }

    // Blazor tự gọi Dispose() khi component bị loại khỏi cây - dừng VÀ
    // giải phóng timer ở đây để nó không chạy "ma" sau khi trang đã rời đi.
    public void Dispose()
    {
        bomHenGio?.Stop();
        bomHenGio?.Dispose();
    }
}
```

!!! danger "Dấu hiệu nhận ra lỗi này khi debug"
    Nếu bạn thêm `Console.WriteLine` vào callback của timer và thấy số dòng in ra **tăng theo cấp số nhân** mỗi lần mở lại cùng một trang (2 timer sau lần 2, 3 timer sau lần 3...), dù trang hiện tại chỉ hiển thị một đồng hồ, đó chính xác là dấu hiệu quên `Dispose()` một `Timer`. Đây là cùng một loại lỗi với "quên huỷ đăng ký `OnChange` của state container service" đã học trước — chỉ khác nguồn rò rỉ là một `Timer` nội bộ của component, không phải một service dùng chung.

!!! note "`IDisposable` (đồng bộ) hay `IAsyncDisposable` (bất đồng bộ) — chọn theo việc dọn dẹp có cần `await` hay không"
    Ví dụ `DongHo.razor` dùng `IDisposable` với `Dispose()` đồng bộ vì `bomHenGio.Stop()`/`bomHenGio.Dispose()` là các lệnh chạy ngay, không cần chờ (`await`) gì cả. Nếu việc dọn dẹp cần gọi một API bất đồng bộ (ví dụ mục 8 sau đây, cần `await moduleJs.InvokeVoidAsync(...)` để báo cho JavaScript dừng lắng nghe trước khi huỷ), phải implement `IAsyncDisposable` với method `DisposeAsync()` (trả về `ValueTask`) thay vì `IDisposable`/`Dispose()` — Blazor tự nhận diện và gọi đúng phương thức tương ứng khi component bị gỡ, tuỳ interface nào được implement. Một component có thể implement cả hai nếu có cả tài nguyên dọn dẹp đồng bộ và bất đồng bộ, nhưng phần lớn trường hợp chỉ cần một trong hai.

---

## 6. `@key` — định nghĩa và ví dụ mất trạng thái input cụ thể

**Định nghĩa (một câu):** `@key` là một directive đặt trên phần tử HTML hoặc component **trong một danh sách được render bằng vòng lặp** (`@foreach`), giúp Blazor nhận diện đúng "phần tử nào tương ứng với phần tử nào" giữa hai lần render — nếu không có `@key`, Blazor mặc định so khớp phần tử theo **vị trí (index)** trong danh sách, dễ gán nhầm trạng thái khi danh sách bị sắp xếp lại, thêm/xoá ở giữa.

Ví dụ cụ thể lỗi — một danh sách người dùng có ô input riêng cho từng dòng (ví dụ ghi chú), KHÔNG có `@key`:

```razor title="DanhSachNguoiDung.razor (THIEU @key - mat trang thai input)"
@page "/danh-sach-loi"

@foreach (var nguoiDung in danhSach)
{
    <div>
        <span>@nguoiDung.Ten</span>
        <input placeholder="Ghi chú riêng cho người này" />
    </div>
}
<button @onclick="XoaNguoiDauTien">Xoá người đầu tiên khỏi danh sách</button>

@code {
    private List<NguoiDung> danhSach = new()
    {
        new NguoiDung { Id = 1, Ten = "An" },
        new NguoiDung { Id = 2, Ten = "Binh" },
        new NguoiDung { Id = 3, Ten = "Chi" },
    };

    private void XoaNguoiDauTien() => danhSach.RemoveAt(0);

    private class NguoiDung
    {
        public int Id { get; set; }
        public string Ten { get; set; } = "";
    }
}
```

**Kịch bản cụ thể gây lỗi:** người dùng gõ "Khách VIP" vào ô input của dòng "Binh" (dòng thứ 2, index 1). Sau đó bấm nút "Xoá người đầu tiên" — danh sách còn lại là `Binh` (giờ ở index 0), `Chi` (index 1). Không có `@key`, Blazor mặc định so khớp phần tử `<input>` ở **index 0** của lần render mới với `<input>` ở **index 0** của lần render cũ — tức là nó coi ô input của "An" (đã bị xoá) và ô input của "Binh" (dòng còn lại, giờ nhảy lên index 0) là "cùng một phần tử", nên **giữ nguyên DOM cũ** (bao gồm nội dung "Khách VIP" đã gõ) nhưng đổi tên hiển thị bên cạnh thành "Binh". Kết quả: dòng "Binh" hiển thị đúng tên, nhưng ô input lại mang chữ "Khách VIP" — mà thực ra bạn đã gõ chữ đó cho dòng "Binh" **trước khi** xoá, chỉ là chữ đó vốn "thuộc về" vị trí index 1 (dòng Binh cũ), giờ bị Blazor hiểu nhầm là dữ liệu của index 0. Với danh sách phức tạp hơn (sắp xếp lại nhiều dòng), việc lệch trạng thái giữa "tên hiển thị" và "nội dung input" trở nên khó đoán và có thể hiển thị nhầm dữ liệu của người dùng khác vào ô input của người này.

Cách sửa đúng — thêm `@key` bằng một giá trị **ổn định, duy nhất** cho mỗi phần tử (ví dụ `Id`, không dùng index):

```razor title="DanhSachNguoiDung.razor (da sua - co @key)"
@page "/danh-sach-dung"

@foreach (var nguoiDung in danhSach)
{
    <div @key="nguoiDung.Id">
        <span>@nguoiDung.Ten</span>
        <input placeholder="Ghi chú riêng cho người này" />
    </div>
}
<button @onclick="XoaNguoiDauTien">Xoá người đầu tiên khỏi danh sách</button>

@code {
    private List<NguoiDung> danhSach = new()
    {
        new NguoiDung { Id = 1, Ten = "An" },
        new NguoiDung { Id = 2, Ten = "Binh" },
        new NguoiDung { Id = 3, Ten = "Chi" },
    };

    private void XoaNguoiDauTien() => danhSach.RemoveAt(0);

    private class NguoiDung
    {
        public int Id { get; set; }
        public string Ten { get; set; } = "";
    }
}
```

Với `@key="nguoiDung.Id"`, Blazor so khớp phần tử theo **giá trị `Id`** (1, 2, 3) giữa hai lần render, không theo vị trí trong danh sách. Khi "An" (Id=1) bị xoá, Blazor nhận ra đúng: phần tử có `@key=1` không còn trong danh sách mới, nên **loại bỏ hẳn** DOM của dòng đó (kể cả nội dung input, nếu có gõ gì cho dòng "An" thì cũng mất theo, đúng như kỳ vọng vì dòng đó đã bị xoá) — còn phần tử `@key=2` ("Binh") và `@key=3` ("Chi") được **giữ nguyên DOM và trạng thái input**, vì Blazor xác định đúng chúng là "cùng phần tử cũ", chỉ đổi vị trí hiển thị.

!!! warning "`@key` không phải chỉ để tối ưu hiệu năng — nó ảnh hưởng ĐÚNG/SAI dữ liệu"
    Nhiều tài liệu giới thiệu `@key` như một cách "tối ưu render" (giúp Blazor tính diff nhanh hơn) — điều này đúng, nhưng chưa đủ. Như ví dụ trên cho thấy, thiếu `@key` trong một danh sách có **trạng thái riêng theo từng dòng** (input, checkbox đang chọn, trạng thái mở/đóng của một accordion) có thể gây ra **dữ liệu hiển thị sai lệch** — không chỉ là vấn đề tốc độ. Quy tắc thực dụng: bất kỳ `@foreach` nào render ra phần tử có khả năng bị **thêm/xoá/sắp xếp lại ở giữa danh sách** (không chỉ luôn thêm vào cuối) và phần tử đó có trạng thái riêng (input, focus, animation đang chạy) — luôn thêm `@key` bằng một giá trị định danh ổn định (thường là khoá chính từ database), không dùng index của vòng lặp làm `@key` (dùng index làm `@key` tương đương với KHÔNG có `@key` — vẫn so khớp theo vị trí).

`@key` không chỉ đặt được trên phần tử HTML thường (`<div>`, `<input>` như ví dụ trên) — nó cũng đặt được trên **component con** trong một `@foreach`, ví dụ `<HangHoaCard @key="sanPham.Id" SanPham="sanPham" />`. Nguyên tắc giống hệt: nếu `HangHoaCard` tự giữ state riêng bên trong nó (ví dụ một biến `daMoRong` để bung/thu gọn chi tiết sản phẩm), thiếu `@key` khi danh sách `sanPham` bị sắp xếp lại sẽ khiến trạng thái `daMoRong` "dính" sai vào sản phẩm khác, đúng bản chất lỗi đã thấy với `<input>` ở trên — chỉ khác nơi xảy ra là state nội bộ của một component, không phải nội dung một `<input>`.

---

## 7. `ElementReference` — tham chiếu phần tử DOM không cần biết `id`

Ví dụ mục 3, 4 dùng `document.getElementById("o-tim-kiem")` để tìm phần tử. Cách này có một hạn chế cụ thể: nếu component `TimKiem` được **dùng nhiều lần** trên cùng một trang (ví dụ hai ô tìm kiếm ở hai khu vực khác nhau), cả hai instance đều render ra `<input id="o-tim-kiem">` — **trùng `id`** — và `document.getElementById(...)` chỉ trả về phần tử **đầu tiên** tìm thấy trong toàn trang, khiến instance thứ hai không bao giờ focus đúng vào input của chính nó.

**Định nghĩa (một câu):** `ElementReference` là một kiểu dữ liệu Blazor cho phép bạn giữ tham chiếu tới **đúng phần tử HTML cụ thể** mà component của bạn vừa render ra — gán qua directive `@ref` trên phần tử HTML, sau đó truyền biến đó (không phải một chuỗi `id`) vào `IJSRuntime.InvokeVoidAsync`/`InvokeAsync<T>` để JavaScript nhận đúng phần tử đó, không phụ thuộc `id` có bị trùng giữa nhiều instance hay không.

Ví dụ tối thiểu, độc lập — sửa lại ví dụ mục 3 để dùng `ElementReference` thay cho `id` cố định:

```razor title="TimKiemDocLap.razor"
@page "/tim-kiem-doc-lap"
@inject IJSRuntime JS

<input @ref="oInput" placeholder="Nhập từ khoá..." />

@code {
    // Khai báo biến kiểu ElementReference, gắn vào phần tử qua @ref ở trên.
    // KHÔNG cần đặt "id" cố định nào cho input này.
    private ElementReference oInput;

    protected override async Task OnAfterRenderAsync(bool firstRender)
    {
        if (firstRender)
        {
            // Truyền THẲNG biến oInput (không phải chuỗi "id") - Blazor tự
            // biết chính xác phần tử DOM nào, dù trang có bao nhiêu instance
            // của component này với cùng cấu trúc HTML.
            await JS.InvokeVoidAsync("focusPhanTu", oInput);
        }
    }
}
```

```text title="wwwroot/site.js (minh hoa - can mot ham JS nhan ElementReference)"
// Khi truyền ElementReference từ C#, phía JavaScript nhận được ĐÚNG phần tử
// DOM đó (Blazor tự chuyển đổi), gọi hàm .focus() trực tiếp lên nó - không
// cần document.getElementById nào cả.
window.focusPhanTu = function (phanTu) {
    phanTu.focus();
};
```

Điểm khác biệt cụ thể so với mục 3: `ElementReference` chỉ có giá trị hợp lệ **sau khi** component đã render lần đầu (đúng lý do vẫn phải dùng `OnAfterRenderAsync`, không phải `OnInitializedAsync` — `oInput` là một `struct` "trống" nếu bạn cố dùng nó trước khi render xảy ra). Khác với `id` chuỗi, `ElementReference` không thể bị "trùng" giữa nhiều instance component, vì mỗi lần một component render, Blazor tạo một `ElementReference` riêng biệt gắn đúng với phần tử DOM thật của **instance đó**.

!!! note "`ElementReference` không tự có method — nó chỉ là một 'tấm thẻ định danh' để gửi cho JavaScript"
    Khác với một số framework có sẵn API C# để gọi trực tiếp trên tham chiếu phần tử (như `element.Focus()` không cần qua JS Interop), Blazor không cấp method C# nào để thao tác trực tiếp trên `ElementReference` — bạn vẫn **phải** đi qua `IJSRuntime` để thực sự gọi `.focus()`/đọc kích thước/v.v., như ví dụ trên. `ElementReference` chỉ giải quyết đúng một vấn đề: "định danh chính xác phần tử DOM nào" để truyền qua cầu nối JS Interop, không thay thế được JS Interop.

---

## 8. Ví dụ tổng hợp — JS Interop + `OnAfterRenderAsync` + `IDisposable` trong một component thật

Mục này ghép các khái niệm mục 1, 3, 4, 5 vào một tình huống gần với thực tế hơn: một component `BoDemThoiGianODau.razor` dùng một hàm JavaScript để theo dõi việc người dùng **rời khỏi tab trình duyệt** (sự kiện `visibilitychange`, một sự kiện JavaScript, Blazor không có API C# sẵn cho nó — đúng lý do cần JS Interop ở mục 1), và cần dọn dẹp đúng cách khi component bị gỡ.

```razor title="BoDemThoiGianODau.razor"
@page "/bo-dem-thoi-gian"
@implements IAsyncDisposable
@inject IJSRuntime JS

<p>Trạng thái tab: @trangThaiTab</p>

@code {
    private string trangThaiTab = "(đang chờ trình duyệt báo)";
    private IJSObjectReference? moduleJs;
    private DotNetObjectReference<BoDemThoiGianODau>? thamChieuChoJs;

    protected override async Task OnAfterRenderAsync(bool firstRender)
    {
        if (firstRender)
        {
            // (1) Bọc CHÍNH instance component này để JS gọi ngược vào một
            // method INSTANCE (không phải static như ví dụ mục 2) - cần cho
            // trường hợp nhiều instance của component này cùng tồn tại,
            // mỗi instance phải nhận đúng callback của riêng mình.
            thamChieuChoJs = DotNetObjectReference.Create(this);

            // (2) Nạp một module JS riêng (xem DEEP DIVE) và gọi hàm trong
            // module đó, truyền tham chiếu instance để JS gọi ngược lại.
            moduleJs = await JS.InvokeAsync<IJSObjectReference>(
                "import", "./js/theo-doi-tab.js");
            await moduleJs.InvokeVoidAsync("batDauTheoDoi", thamChieuChoJs);
        }
    }

    // (3) JS gọi ngược vào ĐÚNG instance này qua thamChieuChoJs - khác ví dụ
    // mục 2 (method static, không gắn với instance cụ thể nào).
    [JSInvokable]
    public void KhiTabDoiTrangThai(bool dangAn)
    {
        trangThaiTab = dangAn ? "Người dùng đã rời tab" : "Người dùng đang xem tab";
        InvokeAsync(StateHasChanged);
    }

    // (4) Dọn dẹp CẢ HAI tài nguyên khi component bị gỡ - module JS (gọi
    // huỷ theo dõi bên JS) VÀ chính DotNetObjectReference (nếu không huỷ,
    // JS vẫn giữ được một tham chiếu "sống" tới instance C# đã bị gỡ khỏi
    // cây - một dạng memory leak khác với Timer ở mục 5, nhưng cùng bản
    // chất: tài nguyên sống ngoài vòng đời component, phải tự tay huỷ).
    public async ValueTask DisposeAsync()
    {
        if (moduleJs is not null)
        {
            await moduleJs.InvokeVoidAsync("dungTheoDoi");
            await moduleJs.DisposeAsync();
        }
        thamChieuChoJs?.Dispose();
    }
}
```

```text title="wwwroot/js/theo-doi-tab.js (minh hoa module JS tuong ung)"
let doiTuongDotNet = null;
let hamXuLy = null;

export function batDauTheoDoi(thamChieuDotNet) {
    doiTuongDotNet = thamChieuDotNet;
    hamXuLy = function () {
        // Gọi ngược vào ĐÚNG instance C# đã truyền qua DotNetObjectReference -
        // dùng invokeMethodAsync trên chính đối tượng đó, không phải
        // DotNet.invokeMethodAsync(tenAssembly, ...) như ví dụ mục 2 (method static).
        doiTuongDotNet.invokeMethodAsync('KhiTabDoiTrangThai', document.hidden);
    };
    document.addEventListener('visibilitychange', hamXuLy);
}

export function dungTheoDoi() {
    document.removeEventListener('visibilitychange', hamXuLy);
}
```

Quan sát mấu chốt: `DisposeAsync()` dọn dẹp theo đúng thứ tự ngược với lúc khởi tạo — gọi `dungTheoDoi()` bên JS **trước** (để `removeEventListener` chạy trong lúc `DotNetObjectReference` vẫn còn hợp lệ), rồi mới `DisposeAsync()` module và `Dispose()` tham chiếu C#. Nếu đảo ngược thứ tự (huỷ `thamChieuChoJs` trước khi báo cho JS dừng lắng nghe), có một khoảng thời gian rất ngắn nơi `visibilitychange` có thể bắn ra và JS cố gọi `invokeMethodAsync` trên một `DotNetObjectReference` đã bị huỷ — ném lỗi runtime dạng "There is no tracked object with id ...".

!!! danger "Quên `Dispose()` trên `DotNetObjectReference` — memory leak khác với Timer nhưng cùng nguyên nhân gốc"
    Nếu bạn bỏ dòng `thamChieuChoJs?.Dispose()`, tình huống tương tự mục 5 xảy ra nhưng ở phía "cầu nối" JS Interop: `DotNetObjectReference.Create(this)` đăng ký instance component vào một bảng theo dõi nội bộ của Blazor để JavaScript có thể gọi ngược vào — nếu không `Dispose()`, bảng theo dõi đó **vẫn giữ tham chiếu sống** tới component đã bị gỡ khỏi cây UI, ngăn garbage collector thu hồi, đúng bản chất memory leak đã học ở mục 5 (một tài nguyên sống ngoài vòng đời component, không được huỷ chủ động), chỉ khác nguồn rò rỉ là "bảng theo dõi JS Interop" thay vì "một `Timer`".

---

## Cạm bẫy & thực chiến

- **Gọi JS Interop thao tác DOM trong `OnInitializedAsync` thay vì `OnAfterRenderAsync`:** như mục 3 đã chỉ ra, DOM của component chưa tồn tại lúc `OnInitializedAsync` chạy — mọi lệnh JS Interop nhắm vào một phần tử cụ thể (focus, đo kích thước, khởi tạo thư viện JS gắn vào một `id`) sẽ thất bại với `JSException` hoặc không có tác dụng.
- **Quên bọc `if (firstRender)` trong `OnAfterRenderAsync` khi logic chỉ nên chạy một lần:** như mục 4, logic khởi tạo (focus lần đầu, khởi tạo thư viện chart) chạy lại ở **mọi** lần render nếu thiếu điều kiện này, gây khởi tạo trùng lặp, event listener JavaScript bị gắn nhiều lần.
- **Tên method C# trong `[JSInvokable]` không khớp chuỗi bên file JavaScript gọi tới:** như mục 2, không có kiểm tra lúc biên dịch giữa hai phía — lỗi chỉ hiện ra lúc chạy thật trong trình duyệt, dạng "Could not find method", dễ bị bỏ sót nếu chỉ chạy unit test C# thông thường (không chạm tới trình duyệt).
- **Tạo `Timer`/subscription trong component nhưng không implement `IDisposable`:** như mục 5, tài nguyên đó sống độc lập với vòng đời component — tiếp tục chạy "ma" sau khi component đã bị gỡ khỏi cây, gây lãng phí CPU tăng dần và có thể ném lỗi khi cố `StateHasChanged()` trên component đã gỡ.
- **Dùng index của `@foreach` (biến đếm vòng lặp) làm giá trị cho `@key`:** về hình thức có `@key`, nhưng dùng index nghĩa là giá trị `@key` vẫn đổi theo **vị trí**, không theo **danh tính** phần tử — tương đương hoàn toàn không có `@key`, không giải quyết được vấn đề mục 6. Luôn dùng một giá trị định danh ổn định (khoá chính, `Guid`), không phụ thuộc vị trí trong danh sách.
- **Gọi quá nhiều lệnh `InvokeVoidAsync`/`InvokeAsync` rời rạc cho nhiều thao tác DOM liên quan:** mỗi lệnh JS Interop là một lượt round-trip qua "cầu nối" .NET-JavaScript (với Blazor Server, còn thêm một lượt qua kết nối SignalR mạng thật) — gọi 10 lệnh JS Interop nhỏ liên tiếp (đọc 10 giá trị DOM khác nhau) chậm hơn đáng kể so với viết **một** hàm JavaScript làm hết việc rồi trả về **một** kết quả tổng hợp qua `InvokeAsync<T>`. Với Blazor Server, chi phí này còn rõ hơn vì có độ trễ mạng thật, không chỉ là chi phí trong bộ nhớ như Blazor WebAssembly.
- **Gán cứng `id` cho một phần tử HTML rồi dùng `document.getElementById` khi component có thể được dùng nhiều lần trên cùng trang:** như mục 7, hai instance cùng render ra cùng `id` khiến `getElementById` luôn trả về phần tử của instance **đầu tiên** — instance thứ hai thao tác nhầm lên DOM của instance khác. Dùng `ElementReference` + `@ref` để mỗi instance luôn tham chiếu đúng phần tử DOM của chính nó.
- **Quên `Dispose()` một `DotNetObjectReference` đã tạo qua `DotNetObjectReference.Create(this)`:** như mục 8, đây là một nguồn memory leak khác — Blazor giữ một bảng theo dõi nội bộ tham chiếu tới instance component để JavaScript gọi ngược vào được; nếu không `Dispose()` khi component bị gỡ, instance đó không được garbage collector thu hồi, và JavaScript có thể cố gọi ngược vào một instance đã "chết", ném lỗi "There is no tracked object with id ...".

---

## Bài tập

**Bài 1 (giàn giáo):** Viết một component `HienThiChieuRong.razor` dùng `IJSRuntime` để lấy chiều rộng cửa sổ trình duyệt (`window.innerWidth`) và hiển thị lên trang, gọi đúng lifecycle để đảm bảo DOM đã sẵn sàng trước khi gọi.

??? success "Lời giải + vì sao"
    ```razor title="HienThiChieuRong.razor"
    @page "/chieu-rong"
    @inject IJSRuntime JS

    <p>Chiều rộng cửa sổ: @chieuRong px</p>

    @code {
        private int chieuRong = 0;

        protected override async Task OnAfterRenderAsync(bool firstRender)
        {
            if (firstRender)
            {
                // InvokeAsync<int> (khác InvokeVoidAsync) vì cần LẤY giá trị
                // trả về từ JavaScript, không chỉ gọi rồi bỏ qua kết quả.
                chieuRong = await JS.InvokeAsync<int>("eval", "window.innerWidth");
                StateHasChanged(); // vẽ lại UI với giá trị vừa lấy được
            }
        }
    }
    ```

    **Vì sao đúng:** dùng `OnAfterRenderAsync` với `if (firstRender)` — đúng lifecycle mục 3/4 chỉ ra, chạy sau khi DOM đã render và chỉ chạy đúng một lần (lấy chiều rộng một lần lúc trang tải là đủ cho ví dụ này). Dùng `InvokeAsync<int>` (không phải `InvokeVoidAsync`) vì cần giá trị trả về. Gọi `StateHasChanged()` sau khi có giá trị mới, vì gán `chieuRong` bên trong `OnAfterRenderAsync` không tự động kích hoạt render lại (khác với gán trong một event handler như `@onclick`).

**Bài 2 (thiết kế — chọn đúng cơ chế):** Bạn có một component `BieuDoDoanhThu.razor` cần dùng một thư viện JavaScript vẽ biểu đồ (giả sử hàm JS có sẵn tên `veBieuDo(idPhanTu, duLieu)`, nhận id của một `<div>` và một mảng số). Viết phần Razor gọi đúng hàm này tại đúng lifecycle, giải thích vì sao chọn lifecycle đó.

??? success "Lời giải + vì sao"
    ```razor title="BieuDoDoanhThu.razor"
    @page "/bieu-do"
    @inject IJSRuntime JS

    <div id="vung-ve-bieu-do"></div>

    @code {
        private int[] duLieu = { 10, 25, 15, 40 };

        protected override async Task OnAfterRenderAsync(bool firstRender)
        {
            if (firstRender)
            {
                // "vung-ve-bieu-do" PHẢI đã tồn tại thật trong DOM trước khi
                // thư viện JS thao tác lên nó - đúng lý do dùng OnAfterRenderAsync,
                // không phải OnInitializedAsync (lúc đó div này chưa được vẽ ra).
                await JS.InvokeVoidAsync("veBieuDo", "vung-ve-bieu-do", duLieu);
            }
        }
    }
    ```

    **Vì sao đúng:** hàm `veBieuDo` cần một `<div>` **đã có thật trong DOM** để thư viện JS "gắn" biểu đồ vào (thao tác kiểu này gần như luôn đòi hỏi DOM tồn tại — vẽ canvas, đo kích thước phần tử cha...). `OnInitializedAsync` chạy trước khi div này được render, gọi ở đó sẽ lỗi giống ví dụ mục 3. Bọc `if (firstRender)` vì việc khởi tạo biểu đồ chỉ nên làm một lần — nếu component re-render vì lý do khác (không phải do đổi `duLieu`), không cần vẽ lại biểu đồ từ đầu.

**Bài 3 (sửa lỗi — nhận diện trùng `id` và thiếu dọn dẹp):** Đoạn code sau có component `OTimKiemNoi.razor` được dùng **hai lần** trên cùng một trang (ví dụ ở đầu trang và trong sidebar). Tìm lỗi cụ thể và sửa lại bằng các khái niệm đã học ở mục 7 và mục 8.

```razor title="OTimKiemNoi.razor (co loi - tim va sua)"
@inject IJSRuntime JS

<input id="o-tim-kiem-noi" placeholder="Tìm..." />

@code {
    protected override async Task OnAfterRenderAsync(bool firstRender)
    {
        if (firstRender)
        {
            await JS.InvokeVoidAsync("eval", "document.getElementById('o-tim-kiem-noi').focus()");
        }
    }
}
```

??? success "Lời giải + vì sao"
    **Lỗi:** `id="o-tim-kiem-noi"` được gán cứng — nếu component này xuất hiện hai lần trên trang, cả hai `<input>` đều có cùng `id`, và `document.getElementById(...)` luôn trả về phần tử **đầu tiên** trong DOM. Instance thứ hai (ví dụ ở sidebar) gọi `focus()` nhưng thực tế lại focus vào input của instance **đầu tiên** (ở đầu trang) — một lỗi runtime khó nhận ra vì không có exception, chỉ là "focus sai chỗ".

    **Sửa lại — dùng `ElementReference` (mục 7), gọi qua hàm `focusPhanTu` đã định nghĩa trong `wwwroot/site.js` ở mục 7:**

    ```razor title="OTimKiemNoi.razor (da sua)"
    @inject IJSRuntime JS

    <input @ref="oInput" placeholder="Tìm..." />

    @code {
        private ElementReference oInput;

        protected override async Task OnAfterRenderAsync(bool firstRender)
        {
            if (firstRender)
            {
                await JS.InvokeVoidAsync("focusPhanTu", oInput);
            }
        }
    }
    ```

    **Vì sao đúng:** `ElementReference` gắn qua `@ref` luôn tham chiếu đúng phần tử DOM của **chính instance đó**, không phụ thuộc `id` (thậm chí không cần đặt `id` nào cả) — dù trang có bao nhiêu instance của `OTimKiemNoi`, mỗi instance tự focus đúng vào input của chính nó. Đây không liên quan đến mục 8 (`DotNetObjectReference`) vì ví dụ này không cần JavaScript gọi ngược lại C# — chỉ cần sửa đúng cách C# tham chiếu tới phần tử DOM.

---

## Tự kiểm tra

1. Vì sao Blazor cần JS Interop, dù đã là một framework C# đầy đủ?

    ??? note "Đáp án"
        Vì nhiều hành vi (focus phần tử, clipboard, localStorage, thư viện JS bên thứ ba...) là hành vi của trình duyệt, thực thi bởi JavaScript — Blazor không thể bọc sẵn API C# cho mọi hành vi trình duyệt đang tồn tại (số lượng quá lớn, luôn có API mới). JS Interop cho phép gọi trực tiếp bất kỳ hàm JavaScript nào từ C#, không cần đợi Blazor hỗ trợ sẵn.

2. `InvokeVoidAsync` và `InvokeAsync<T>` khác nhau ở điểm nào, khi nào dùng cái nào?

    ??? note "Đáp án"
        `InvokeVoidAsync` dùng khi hàm JavaScript không cần trả về giá trị để dùng lại trong C# (giống gọi một method `void`). `InvokeAsync<T>` dùng khi cần lấy kết quả trả về từ JavaScript, chuyển đổi (deserialize) thành kiểu `T` trong C#.

3. Nếu gọi `InvokeVoidAsync` với tên hàm JavaScript sai (không tồn tại), lỗi xảy ra ở giai đoạn nào — biên dịch hay lúc chạy?

    ??? note "Đáp án"
        Lúc chạy (runtime). Tên hàm là một chuỗi, C# không kiểm tra được hàm đó có thật hay không lúc biên dịch — code build thành công, nhưng khi thực thi sẽ ném `JSException` dạng "không phải là một hàm/không tìm thấy".

4. `[JSInvokable]` dùng để làm gì, và JavaScript gọi vào method đó bằng cú pháp nào?

    ??? note "Đáp án"
        `[JSInvokable]` đánh dấu một method C# public để JavaScript có thể gọi ngược lại bằng tên. Phía JavaScript gọi qua `DotNet.invokeMethodAsync('TenAssembly', 'TenMethod', thamSo...)`, với `TenMethod` phải khớp chính xác tên method đã đánh dấu `[JSInvokable]`.

5. `OnAfterRenderAsync` khác `OnInitializedAsync` ở điểm nào về thời điểm chạy so với DOM thật?

    ??? note "Đáp án"
        `OnInitializedAsync` chạy trước lần render đầu tiên — DOM thật của component chưa tồn tại. `OnAfterRenderAsync` chạy sau khi Blazor đã vẽ xong HTML ra DOM thật (kể cả lần đầu và mọi lần re-render sau) — an toàn để thao tác DOM hoặc gọi JS Interop nhắm vào một phần tử cụ thể.

6. Tham số `firstRender` của `OnAfterRenderAsync` có giá trị gì ở lần gọi đầu tiên và các lần gọi sau, và tại sao cần kiểm tra nó?

    ??? note "Đáp án"
        `firstRender` là `true` chỉ ở lần gọi đầu tiên (sau lần render đầu của component), và `false` ở mọi lần gọi sau (mỗi lần component re-render). Cần kiểm tra `if (firstRender)` khi logic bên trong chỉ nên chạy đúng một lần (như focus lúc khởi tạo, khởi tạo thư viện JS) — nếu không, logic đó chạy lại ở mọi lần re-render, gây khởi tạo trùng lặp hoặc gắn lại event listener nhiều lần.

7. Nếu một component tạo `System.Timers.Timer` trong `OnInitialized()` nhưng không implement `IDisposable`, hậu quả cụ thể là gì khi người dùng điều hướng rời trang?

    ??? note "Đáp án"
        Timer đó vẫn tiếp tục chạy độc lập với vòng đời component, dù component đã bị Blazor loại khỏi cây UI — mỗi lần điều hướng lại vào/ra trang đó tạo thêm một timer mới không bị huỷ, gây rò rỉ bộ nhớ và lãng phí CPU tăng dần, có thể ném lỗi khi timer cố gọi `StateHasChanged()` trên component đã gỡ.

8. `@key` giải quyết vấn đề gì khi render một danh sách bằng `@foreach`?

    ??? note "Đáp án"
        `@key` giúp Blazor nhận diện đúng phần tử nào trong lần render mới tương ứng với phần tử nào ở lần render cũ, dựa theo một giá trị định danh ổn định — thay vì mặc định so khớp theo vị trí (index) trong danh sách, dễ gán nhầm trạng thái (như nội dung input) khi danh sách được thêm/xoá/sắp xếp lại ở giữa.

9. Nếu thiếu `@key` trong một `@foreach` render các `<input>` có trạng thái riêng, và một phần tử ở giữa danh sách bị xoá, hậu quả cụ thể là gì?

    ??? note "Đáp án"
        Blazor so khớp các `<input>` theo vị trí (index), không theo danh tính phần tử thật — sau khi xoá, các phần tử phía sau "dồn lên" một vị trí, khiến Blazor giữ nguyên DOM/trạng thái input cũ ở đúng index đó nhưng gán nhãn/tên hiển thị mới cho nó — nội dung input bị "lệch", hiển thị sai lệch giữa tên/dữ liệu hiển thị và nội dung người dùng đã nhập trước đó.

10. Dùng index của vòng lặp `@foreach` làm giá trị cho `@key` có giải quyết được vấn đề ở câu 9 không? Vì sao?

    ??? note "Đáp án"
        Không. Dùng index làm `@key` nghĩa là giá trị `@key` vẫn thay đổi theo vị trí trong danh sách (giống hoàn toàn việc không có `@key`) — không phải theo danh tính ổn định của từng phần tử, nên không giải quyết được vấn đề mất/lệch trạng thái khi danh sách bị thêm/xoá/sắp xếp lại ở giữa.

11. Vì sao gọi nhiều lệnh JS Interop nhỏ liên tiếp (ví dụ đọc 10 giá trị DOM riêng lẻ) thường chậm hơn một lệnh JS Interop gọi một hàm JavaScript tổng hợp trả về một kết quả duy nhất?

    ??? note "Đáp án"
        Mỗi lệnh JS Interop là một lượt round-trip qua cầu nối .NET-JavaScript (thêm cả một lượt qua kết nối SignalR mạng thật với Blazor Server) — gọi 10 lệnh rời rạc nghĩa là 10 lượt round-trip, trong khi một hàm JavaScript làm hết việc rồi trả về một kết quả tổng hợp chỉ cần một lượt, giảm chi phí giao tiếp qua lại đáng kể.

12. `ElementReference` giải quyết vấn đề gì mà `document.getElementById("id-co-dinh")` không giải quyết được?

    ??? note "Đáp án"
        Khi một component được dùng nhiều lần trên cùng một trang, mỗi instance render ra cùng một `id` cố định (nếu gán cứng trong markup) — `getElementById` chỉ tìm được phần tử đầu tiên trong toàn trang, khiến các instance khác thao tác nhầm lên DOM của instance đầu. `ElementReference` (gắn qua `@ref`) luôn tham chiếu đúng phần tử DOM của chính instance đó, không phụ thuộc `id`, nên không bị nhầm lẫn giữa nhiều instance.

13. `DotNetObjectReference.Create(this)` dùng để làm gì, và tại sao cần `Dispose()` nó?

    ??? note "Đáp án"
        Dùng để bọc chính instance component (hoặc một object C# khác) thành một tham chiếu mà JavaScript có thể gọi ngược vào đúng method instance của nó (khác với method `static` ở mục 2, không gắn với instance cụ thể). Cần `Dispose()` khi component bị gỡ vì Blazor giữ instance đó trong một bảng theo dõi nội bộ để JavaScript gọi ngược được — nếu không huỷ, bảng theo dõi vẫn giữ tham chiếu sống tới instance đã "chết", ngăn garbage collector thu hồi (một dạng memory leak khác với Timer ở mục 5, nhưng cùng nguyên nhân gốc: tài nguyên sống ngoài vòng đời component).

14. Trong ví dụ mục 8, vì sao `DisposeAsync()` gọi `dungTheoDoi()` bên JavaScript **trước khi** huỷ `thamChieuChoJs`, không phải ngược lại?

    ??? note "Đáp án"
        Nếu huỷ `thamChieuChoJs` trước, có một khoảng thời gian rất ngắn nơi sự kiện `visibilitychange` bên JavaScript vẫn có thể bắn ra và cố gọi `invokeMethodAsync` trên một `DotNetObjectReference` đã bị huỷ, ném lỗi runtime dạng "There is no tracked object with id ...". Gọi `dungTheoDoi()` (huỷ `removeEventListener`) trước đảm bảo JavaScript không còn cố gọi ngược vào C# nữa, rồi mới an toàn huỷ tham chiếu.

---

??? abstract "DEEP DIVE — nâng cao (ngoài fast path)"
    - **`IJSObjectReference` khi hàm JavaScript trả về một đối tượng cần giữ lại:** ví dụ mục 8 đã dùng `IJSObjectReference` cho module JS. Ngoài module, một hàm JavaScript có thể trả về một đối tượng bất kỳ (ví dụ một instance biểu đồ) mà bạn cần gọi tiếp các method trên nó nhiều lần sau đó (`.update(duLieuMoi)`) — giữ lại `IJSObjectReference` đó (thay vì gọi lại toàn bộ hàm khởi tạo mỗi lần cần cập nhật) tránh phải "tìm lại" đối tượng JS từ đầu.
    - **Module JavaScript cách ly (`import`) thay vì gắn hàm vào `window` toàn cục:** ví dụ mục 8 đã dùng `JS.InvokeAsync<IJSObjectReference>("import", "./js/theo-doi-tab.js")` — đây là cách nạp JS Interop theo **module ES6**, cách ly các hàm trong phạm vi module riêng, không rò ra `window` toàn cục như các ví dụ đơn giản ở mục 1-6 (viết trực tiếp `window.tenHam = ...`). Đây là cách được khuyến nghị cho thư viện Blazor component dùng lại nhiều nơi, tránh trùng tên hàm giữa các thư viện/phần khác nhau của ứng dụng.
    - **`OnAfterRender` không hỗ trợ ngăn Blazor render tiếp bằng cách trả về giá trị:** khác với một số framework khác cho phép lifecycle "sau render" can thiệp vào việc có render tiếp hay không, `OnAfterRenderAsync` trong Blazor chỉ là nơi "quan sát và phản ứng" sau khi render đã xảy ra — không có cách nào dùng nó để huỷ hoặc thay đổi kết quả render đã vẽ ra; muốn kiểm soát có render lại hay không, dùng `ShouldRender()` (một lifecycle riêng, chạy trước khi quyết định có re-render).
    - **Thứ tự các lifecycle khi component vừa được tạo:** đầy đủ hơn bảng ở mục 3, thứ tự thật là: constructor → gán `[Parameter]` → `OnInitialized`/`OnInitializedAsync` → `OnParametersSet`/`OnParametersSetAsync` → render lần đầu (vẽ ra DOM) → `OnAfterRender`/`OnAfterRenderAsync` (với `firstRender=true`). Ở các lần render sau (do parameter đổi hoặc `StateHasChanged()`), thứ tự lặp lại từ `OnParametersSet` (bỏ qua `OnInitialized`, vì đó chỉ chạy đúng một lần) tới `OnAfterRender` (với `firstRender=false`).
    - **Thư viện JS Interop bậc cao đóng gói sẵn (ví dụ Blazor.LocalStorage, Blazored.Modal):** viết JS Interop tay cho các tác vụ phổ biến (localStorage, hộp thoại modal, clipboard) lặp đi lặp lại giữa nhiều dự án — một số thư viện NuGet cộng đồng đóng gói sẵn cả phần C# (API gọn) và phần JavaScript tương ứng, giúp bạn không phải tự viết lại module JS cho các tác vụ đã quá phổ biến. Vẫn cần hiểu cơ chế JS Interop thô (mục 1-8) trước khi dùng các thư viện này, để đọc hiểu được chúng "làm gì bên dưới" khi cần debug.

Tiếp theo -> authorization & policy-based access
