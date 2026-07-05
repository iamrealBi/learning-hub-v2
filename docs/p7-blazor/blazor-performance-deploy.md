---
tier: core
status: core
owner: core-team
verified_on: "2026-07-05"
dotnet_version: "10.0"
bloom: đánh giá
requires: [p7-jsinterop]
est_minutes_fast: 30
---

# Hiệu năng & Deploy Blazor WebAssembly

!!! info "Bạn đang ở đây"
    cần trước: component `.razor` cơ bản, data binding/event, lifecycle method (`OnInitializedAsync`...), JS Interop (`IJSRuntime`).
    mở khoá: giải thích được vì sao Blazor WebAssembly tải trang lần đầu chậm hơn web thường, viết được component tránh re-render dư thừa, và tự đóng gói + đưa một app Blazor WASM lên Internet dưới dạng static site.

> Mục tiêu (đo được): sau chương này bạn **giải thích** được vì sao Blazor WebAssembly có chi phí tải lần đầu (cold start) cao hơn một trang HTML/JS thường, **đánh giá** được khi nào nên dùng AOT compilation và đánh đổi cụ thể của nó, **viết** được một component override `ShouldRender()` để tránh re-render không cần thiết và tránh lỗi tạo lambda mới mỗi lần render, **thực hiện** được `dotnet publish -c Release` cho một dự án Blazor WASM và giải thích nội dung thư mục publish, và **liên hệ** được cách deploy static hosting với cách trang Learning Hub này đang được deploy qua GitHub Pages.

---

## 0. Đoán nhanh trước khi học

Bạn mở một trang web thường (HTML/CSS/JS tay viết, không framework) và một trang Blazor WebAssembly, cả hai deploy trên cùng một static hosting, cùng tốc độ mạng. Trang nào có khả năng **hiển thị nội dung đầu tiên chậm hơn** khi người dùng bấm vào link lần đầu (chưa có gì trong cache trình duyệt)?

??? question "Câu hỏi: vì sao lại có sự khác biệt, nếu cả hai đều chỉ là file static?"
    **Trang Blazor WebAssembly thường chậm hơn ở lần tải đầu.** Cả hai đều đúng là "chỉ file static" (HTML, CSS, JS, và với Blazor WASM thêm file `.wasm`) — nhưng trang HTML/JS thường chỉ cần trình duyệt tải file JS của nó rồi chạy ngay bằng engine JavaScript **có sẵn** trong trình duyệt. Blazor WebAssembly thì khác: trước khi chạy được **bất kỳ dòng code C# nào** của ứng dụng, trình duyệt phải tải thêm một bộ **runtime .NET biên dịch sang WebAssembly** (để hiểu và thực thi được IL — mã trung gian .NET), rồi tải các file `.dll` chứa code ứng dụng của bạn, rồi mới khởi động runtime đó. Mục 1 định nghĩa rõ và liệt cụ thể các loại tài nguyên phải tải thêm này.

Câu hỏi thứ hai, liên quan tới việc đưa ứng dụng lên môi trường thật: bạn vừa `dotnet publish -c Release` xong một dự án Blazor WebAssembly. Thư mục kết quả có cần một máy chủ chạy `dotnet` (như khi bạn `dotnet run` một Minimal API ở P3) để phục vụ nó không?

??? question "Câu hỏi: publish Blazor WebAssembly có cần server .NET chạy phía sau không?"
    **Không.** Khác với Minimal API hay Blazor Server (publish ra một chương trình cần lệnh `dotnet YourApp.dll` để chạy), thư mục publish của Blazor WebAssembly chỉ chứa file static (`.html`, `.css`, `.js`, `.wasm`, các file `.dll` đóng vai trò file tĩnh được trình duyệt tải xuống, không chạy trên server) — bất kỳ máy chủ web tĩnh nào (thậm chí mở trực tiếp qua một static file server đơn giản) cũng phục vụ được. Mục 5 và 6 giải thích chi tiết nội dung thư mục này và cách đưa nó lên Internet.

---

## 1. Vì sao Blazor WebAssembly tải lần đầu chậm hơn — định nghĩa và tài nguyên cụ thể

**Định nghĩa (một câu):** Blazor WebAssembly là một mô hình chạy Blazor trong đó **toàn bộ ứng dụng .NET (runtime + code của bạn) được tải xuống và chạy hoàn toàn trong trình duyệt qua WebAssembly (WASM)** — khác với chạy trên máy chủ, trình duyệt phải tự mình có đủ "bộ máy" để hiểu và thực thi C#, nên trước khi trang hiển thị được gì, nó phải tải xong bộ máy đó.

Cụ thể, khi trình duyệt vào một trang Blazor WebAssembly lần đầu (chưa cache), nó phải tải theo thứ tự các loại tài nguyên sau — đây không phải một file JS duy nhất như web thường:

```text title="tai nguyen dien hinh khi tai Blazor WASM lan dau"
1. index.html                     - trang HTML gốc, rất nhỏ
2. _framework/blazor.webassembly.js  - script khởi động (bootstrapper)
3. _framework/dotnet.wasm            - runtime .NET biên dịch sang WASM (thường vài MB)
4. _framework/*.dll                  - các assembly .NET: BCL (System.*) + code ứng dụng của bạn
5. _framework/blazor.boot.json       - danh sách file trên, kèm checksum để cache đúng
```

So với một trang web thường chỉ cần tải một file `.js` vài chục KB rồi chạy ngay, Blazor WebAssembly phải tải thêm mục (3) và (4) — riêng runtime .NET dạng WASM đã có thể nặng vài MB, cộng thêm các assembly BCL (thư viện lớp cơ sở .NET, như `System.Private.CoreLib.dll`) mà ứng dụng của bạn phụ thuộc vào, dù code bạn viết chỉ vài trăm dòng.

Để có cảm nhận cụ thể về độ lớn (con số minh hoạ, thay đổi theo phiên bản .NET và cấu hình trimming — không phải số cố định):

| Loại tài nguyên | Trang HTML/JS thường | Blazor WebAssembly (chưa nén) |
|---|---|---|
| HTML gốc | Vài KB | Vài KB (`index.html` rất nhỏ, gần như trống) |
| JS/logic ứng dụng | Vài chục KB đến vài trăm KB | `blazor.webassembly.js` (nhỏ) + `_framework/*.dll` (code của bạn) |
| Runtime cần tải thêm | Không có (dùng engine JS có sẵn của trình duyệt) | `dotnet.wasm` — thường 1–3 MB tối thiểu |
| Thư viện lớp cơ sở (BCL) | Không áp dụng | Nhiều `.dll` như `System.Private.CoreLib.dll`, tổng cộng thêm vài MB |
| **Tổng tải lần đầu điển hình** | **Dưới 1 MB** | **Thường 3–10 MB** (tuỳ số package tham chiếu, đã áp dụng trimming mặc định) |

Đây chính là lý do một trang landing page đơn giản không nên chọn Blazor WebAssembly nếu tiêu chí quan trọng nhất là "hiển thị nội dung đầu tiên nhanh nhất có thể" (xem lại Bài tập 4 cuối chương) — dù cùng deploy trên static hosting, khối lượng byte phải tải trước khi thấy được gì là hoàn toàn khác nhau về bản chất.

!!! warning "Đây là chi phí một lần, không lặp lại mỗi lần điều hướng trong app"
    Chi phí tải nặng này **chỉ xảy ra ở lần đầu** người dùng vào trang (hoặc khi trình duyệt xoá cache) — trình duyệt cache lại các file `.wasm`/`.dll` này, nên lần vào lại sau đó (cùng phiên, hoặc phiên sau nếu cache còn) sẽ nhanh hơn nhiều. Sau khi runtime đã khởi động xong, việc điều hướng **giữa các trang trong cùng ứng dụng Blazor WASM** (đổi route qua `NavigationManager`, không phải tải lại trình duyệt) không cần tải lại runtime hay assembly — đây chính là lý do Blazor WebAssembly, dù chậm ở màn hình đầu, thường **nhanh hơn** cho các tương tác sau đó so với việc mỗi trang phải round-trip lên server để render lại HTML.

Với Blazor Server (đã học ở chương "blazor-tong-quan") — mô hình này **không** cần tải runtime .NET xuống trình duyệt, vì code C# chạy trên server, trình duyệt chỉ nhận diff UI qua SignalR — nên tải lần đầu nhẹ hơn nhiều, nhưng đổi lại cần kết nối mạng liên tục để hoạt động (đã học ở chương trước, nhắc lại ở mục "Cạm bẫy" cuối bài).

### 1a. `blazor.boot.json` — vì sao trình duyệt biết chính xác cần tải gì

Một câu hỏi tự nhiên: trình duyệt biết cần tải đúng những file `.dll` nào, nếu mỗi dự án Blazor WASM có bộ assembly khác nhau (tuỳ dự án tham chiếu package gì)? Câu trả lời nằm ở file `blazor.boot.json` — một file JSON được `dotnet publish` tự sinh ra, đóng vai trò "danh sách mua hàng" cho script khởi động (`blazor.webassembly.js`) đọc trước, rồi mới tải đúng các file cần thiết theo danh sách đó.

```text title="blazor.boot.json (rut gon, minh hoa cau truc)"
{
  "resources": {
    "assembly": {
      "MyBlazorApp.dll": "sha256-abc123...",
      "System.Private.CoreLib.dll": "sha256-def456...",
      "Microsoft.AspNetCore.Components.dll": "sha256-ghi789..."
    },
    "wasmNative": {
      "dotnet.wasm": "sha256-jkl012..."
    }
  },
  "cacheBootResources": true
}
```

Mỗi entry là một cặp tên-file/checksum (hash `sha256`). Script khởi động dùng checksum này để quyết định: nếu trình duyệt đã có file đó trong cache **và** checksum khớp, **không tải lại** — đây chính là cơ chế cho phép lần vào lại sau (mục 1, phần "!!! warning") nhanh hơn lần đầu, vì hầu hết file không đổi giữa các lần bạn ghé trang, chỉ file nào bạn vừa deploy bản mới (checksum đổi) mới bị tải lại.

!!! note "Không cần tự tay sửa `blazor.boot.json`"
    File này do `dotnet publish` tự sinh, bạn không chỉnh sửa tay — biết tên và cấu trúc của nó chỉ giúp bạn đọc hiểu đúng khi mở tab Network của trình duyệt lúc debug lỗi tải chậm hoặc lỗi 404 (mục 6 sẽ quay lại đúng file này khi debug lỗi deploy GitHub Pages).

---

## 2. AOT compilation — định nghĩa và đánh đổi

**Định nghĩa (một câu):** AOT (Ahead-Of-Time) compilation là một tuỳ chọn build biên dịch code C# của bạn **thành mã máy native của WebAssembly ngay lúc `dotnet publish`**, thay vì đóng gói dưới dạng IL (mã trung gian) để trình duyệt **interpret (diễn giải) từng dòng lúc runtime** — cách mặc định khi không dùng AOT.

Để dễ liên hệ: bình thường, khi bạn `dotnet run` một ứng dụng .NET trên máy chủ/máy dev, CLR (Common Language Runtime) dùng **JIT** (Just-In-Time compilation) — biên dịch từng phần IL sang mã máy **ngay trước khi chạy lần đầu**, rồi cache lại kết quả để các lần gọi sau nhanh hơn. Blazor WebAssembly (không AOT) đi xa hơn JIT một bước theo hướng **chậm hơn**: trình duyệt chủ yếu **interpret** (diễn giải IL trực tiếp, không biên dịch trước) vì môi trường WASM có nhiều hạn chế hơn để JIT đầy đủ như CLR trên desktop/server. AOT giải quyết đúng điểm chậm này bằng cách chuyển hẳn việc biên dịch sang **lúc build** (`dotnet publish`), để lúc chạy trong trình duyệt không còn bước diễn giải hay biên dịch nào nữa — đổi lại, kết quả biên dịch sẵn đó (mã native WASM) chiếm nhiều byte hơn IL gốc, nên file tải xuống nặng hơn.

Bật AOT bằng một dòng cấu hình trong file project (`.csproj`) của dự án Blazor WASM:

```text title="ProjectName.csproj (trich - bat AOT)"
<PropertyGroup>
  <RunAOTCompilation>true</RunAOTCompilation>
</PropertyGroup>
```

**Đánh đổi cụ thể — không có lựa chọn nào "toàn thắng":**

| | Không AOT (mặc định — interpret IL) | Có AOT (biên dịch sẵn sang native WASM) |
|---|---|---|
| Kích thước file tải xuống | Nhỏ hơn | **Lớn hơn đáng kể** (thường gấp 2–3 lần, vì mã native WASM chi tiết hơn IL) |
| Thời gian tải lần đầu | Nhanh hơn (ít byte hơn) | **Chậm hơn** (nhiều byte hơn phải tải) |
| Tốc độ thực thi code sau khi đã tải xong | Chậm hơn (mỗi lệnh IL phải diễn giải lúc chạy) | **Nhanh hơn đáng kể** (chạy thẳng mã native, không cần diễn giải) |
| Thời gian build (`dotnet publish`) | Nhanh | Chậm hơn nhiều (phải biên dịch native cho toàn bộ code) |
| Trường hợp nên dùng | Ứng dụng CRUD thông thường, ưu tiên tải nhanh | Ứng dụng tính toán nặng (xử lý ảnh, game logic, thuật toán phức tạp) chạy ngay trong trình duyệt, chấp nhận tải chậm hơn để đổi lấy tốc độ chạy |

!!! note "Mục này chỉ cần hiểu khái niệm, không cần thực hành sâu"
    AOT là một quyết định cấu hình build, không phải kỹ năng viết code hàng ngày — bạn không cần tự tay đo benchmark AOT ở giai đoạn học này. Điều cần nhớ: khi nghe "app Blazor WASM của tôi load hơi lâu nhưng chạy rất nhanh" hoặc ngược lại, đó thường là dấu hiệu của quyết định AOT (có/không) đằng sau, không phải một lỗi code. Quyết định này thường chỉ đáng cân nhắc **sau khi** đã tối ưu các phần dễ hơn ở mục 3–4 dưới đây.

!!! danger "Hiểu sai phổ biến: AOT giúp TẢI nhanh hơn"
    Một hiểu nhầm thường gặp: "AOT = tối ưu hoá = mọi thứ nhanh hơn, kể cả tải". **Sai một nửa.** AOT chỉ tối ưu **tốc độ thực thi** (chạy code sau khi đã tải xong), không tối ưu **tốc độ tải**. Ngược lại, vì mã native WASM chi tiết hơn IL (mỗi lệnh IL có thể sinh ra nhiều lệnh máy native tương ứng), file `.wasm` sau khi AOT thường **nặng hơn**, khiến bước tải (mục 1) **chậm hơn**, không nhanh hơn. Nếu mục tiêu của bạn là "trang hiển thị nhanh hơn ở lần đầu", AOT đi ngược lại mục tiêu đó — bạn cần các kỹ thuật ở mục 1 (trimming, compression, deep dive) hoặc đơn giản là giảm số lượng package phụ thuộc, không phải bật AOT.

### 2a. Kiểm tra một dự án đã bật AOT hay chưa

Vì AOT là cấu hình ẩn trong `.csproj`, cách nhanh nhất để xác nhận một dự án Blazor WASM có bật AOT hay không (ví dụ khi nhận code từ đồng nghiệp) là kiểm tra đúng dòng cấu hình đã nêu ở trên, hoặc quan sát kích thước file sau publish:

```text title="dau hieu nhan biet qua kich thuoc file (khong phai cach chinh xac tuyet doi, chi la kinh nghiem)"
Khong AOT: _framework/dotnet.wasm thuong tu 1-3 MB (tuy phien ban .NET)
Co AOT:    _framework/dotnet.wasm + cac module native khac co the len toi
           vai chuc MB, tuy do lon code ung dung
```

Cách chính xác hơn là mở `ProjectName.csproj` và tìm dòng `<RunAOTCompilation>true</RunAOTCompilation>` — nếu không có dòng này (hoặc có với giá trị `false`), dự án build theo mặc định (không AOT, interpret IL lúc runtime).

---

## 3. `ShouldRender()` — định nghĩa và ví dụ tối thiểu

**Định nghĩa (một câu):** `ShouldRender()` là một phương thức bạn có thể **override** trong component kế thừa `ComponentBase`, được Blazor gọi **mỗi khi** component sắp render lại (sau khi state đổi) để hỏi "component này có thực sự cần vẽ lại không" — nếu bạn trả về `false`, Blazor **bỏ qua** lần render đó hoàn toàn, không tính toán lại render tree cho component này.

Ví dụ tối thiểu, độc lập — một component chỉ render lại khi giá trị thực sự đổi (bỏ qua nếu gọi lại với đúng giá trị cũ):

```razor title="BoDemChiRenderKhiDoi.razor"
<p>Giá trị hiện tại: @giaTri</p>
<button @onclick="TangLen">Tăng</button>
<button @onclick="GanLaiGiaTriCu">Gán lại giá trị CŨ (không đổi)</button>

@code {
    private int giaTri = 0;
    private int giaTriDaRenderLanCuoi = 0;

    private void TangLen() => giaTri++;

    // Cố tình gọi lại với giá trị KHÔNG đổi - để minh hoạ ShouldRender chặn render dư.
    private void GanLaiGiaTriCu() => giaTri = giaTri;

    protected override bool ShouldRender()
    {
        // Chỉ cho phép render nếu giá trị thực sự khác lần render trước.
        if (giaTri == giaTriDaRenderLanCuoi) return false;
        giaTriDaRenderLanCuoi = giaTri;
        return true;
    }
}
```

Mỗi lần `@onclick` được bấm (dù là nút "Tăng" hay nút "Gán lại giá trị CŨ"), Blazor phát hiện có sự kiện xảy ra và **luôn** gọi `ShouldRender()` để hỏi ý kiến trước khi thực sự vẽ lại. Với nút "Gán lại giá trị CŨ", `giaTri` không đổi, `ShouldRender()` trả `false`, Blazor bỏ qua — component không tính toán lại render tree, dù sự kiện `@onclick` đã chạy xong bình thường.

!!! danger "Điều gì xảy ra khi override sai — quên cập nhật biến theo dõi"
    Nếu bạn quên dòng `giaTriDaRenderLanCuoi = giaTri;` bên trong `ShouldRender()`, biến theo dõi **không bao giờ cập nhật**, khiến `ShouldRender()` luôn so sánh với giá trị ban đầu (`0`) mãi mãi. Hậu quả cụ thể: sau lần tăng đầu tiên (`giaTri = 1`), `ShouldRender()` trả `true` đúng một lần (vì `1 != 0`) — nhưng vì quên cập nhật, `giaTriDaRenderLanCuoi` vẫn là `0`, nên `giaTri = 2` ở lần tăng tiếp theo vẫn có `2 != 0`, vẫn render — nhìn qua có vẻ "vẫn đúng". Vấn đề rõ hơn khi bạn dùng `ShouldRender()` để chặn theo điều kiện khác phức tạp hơn (ví dụ chỉ render khi có ít nhất 5 lượt đổi) — quên đồng bộ biến theo dõi khiến điều kiện chặn sai lệch dần, component render nhiều hơn hoặc ít hơn ý định, một lỗi khó phát hiện vì UI "trông vẫn đúng" phần lớn thời gian, chỉ sai ở các trường hợp biên.

### 3a. `ShouldRender()` với component nhận nhiều `[Parameter]` từ cha

Ví dụ mục 3 tự quản lý state bên trong chính component. Trường hợp thường gặp hơn trong thực tế: một component con nhận dữ liệu qua `[Parameter]` từ cha, và cha gọi lại `StateHasChanged()` thường xuyên (ví dụ mỗi giây, từ một `Timer`) — nhưng chỉ MỘT trong nhiều `[Parameter]` đó thực sự ảnh hưởng tới hiển thị của component con này.

```razor title="ThongTinSanPham.razor (component con - nhan nhieu Parameter)"
<p>Sản phẩm: @TenSanPham — Giá: @Gia.ToString("N0")đ</p>

@code {
    [Parameter] public string TenSanPham { get; set; } = "";
    [Parameter] public decimal Gia { get; set; }

    // Component cha còn truyền thêm ThoiGianHienTai (đổi mỗi giây, do Timer),
    // nhưng ThongTinSanPham KHÔNG hiển thị gì liên quan tới nó.
    [Parameter] public DateTime ThoiGianHienTai { get; set; }

    private string tenDaRenderLanCuoi = "";
    private decimal giaDaRenderLanCuoi;

    protected override bool ShouldRender()
    {
        // Chỉ quan tâm hai Parameter thực sự ảnh hưởng hiển thị -
        // bỏ qua hoàn toàn ThoiGianHienTai dù nó đổi mỗi giây.
        bool coDoi = TenSanPham != tenDaRenderLanCuoi || Gia != giaDaRenderLanCuoi;
        if (!coDoi) return false;

        tenDaRenderLanCuoi = TenSanPham;
        giaDaRenderLanCuoi = Gia;
        return true;
    }
}
```

Nếu component cha có một `Timer` cập nhật `ThoiGianHienTai` mỗi giây và gọi `StateHasChanged()` (để một đồng hồ hiển thị ở nơi khác trên trang chạy đúng), **mọi** component con nhận Parameter từ cha đó — bao gồm `ThongTinSanPham` — đều bị Blazor gọi lại `OnParametersSet`/xét render theo mặc định, dù `TenSanPham` và `Gia` không đổi gì. Override `ShouldRender()` như trên giúp `ThongTinSanPham` "lọc" đúng, chỉ render lại khi hai giá trị nó thực sự hiển thị đổi, bất kể cha có gọi lại bao nhiêu lần vì lý do khác.

!!! warning "`ShouldRender()` không chặn được lần render ĐẦU TIÊN"
    Blazor luôn gọi `ShouldRender()` **sau** lần render đầu tiên của component — lần khởi tạo đầu tiên (khi component vừa được thêm vào cây UI) luôn render, không hỏi `ShouldRender()`. Điều này đúng theo thiết kế: bạn không thể "chặn" component không hiển thị gì lần đầu bằng `ShouldRender()`, nó chỉ có tác dụng cho các lần render **sau đó** (khi component đã tồn tại và có sự kiện/Parameter mới kích hoạt render lại).

---

## 4. Tránh tạo object mới không cần trong method render

**Định nghĩa (một câu):** mỗi lần component render, **mọi biểu thức nằm trực tiếp trong markup `.razor`** (bao gồm lambda truyền cho `@onclick`, hay object/mảng khởi tạo tại chỗ) đều được **đánh giá lại và tạo ra một instance mới** — nếu component con nhận giá trị đó qua `[Parameter]`, Blazor coi đây là "giá trị khác với lần trước" (vì tham chiếu khác nhau) và buộc component con **render lại theo**, dù dữ liệu bên trong có giống hệt nội dung cũ.

Ví dụ cụ thể gây re-render con không cần thiết — lambda tạo lambda mới mỗi lần cha render:

```razor title="DanhSachSanPham.razor (SAI - tao lambda moi moi lan render)"
@foreach (var sp in danhSachSanPham)
{
    @* SAI: mỗi lần DanhSachSanPham render (dù chỉ vì MỘT dòng khác đổi),
       toàn bộ vòng lặp này chạy lại, và MỖI lambda "() => ChonSanPham(sp)"
       được TẠO MỚI cho mỗi sản phẩm - dù nội dung logic giống hệt lần trước. *@
    <DongSanPham TenSanPham="@sp" OnChon="() => ChonSanPham(sp)" />
}

@code {
    private List<string> danhSachSanPham = new() { "Bàn phím", "Chuột", "Màn hình" };

    private void ChonSanPham(string ten) => Console.WriteLine($"Đã chọn: {ten}");
}
```

`DongSanPham` là một component con nhận `OnChon` qua `[Parameter]` (kiểu `EventCallback` hoặc `Action`). Vì lambda `() => ChonSanPham(sp)` được viết **trực tiếp trong markup**, mỗi lần `DanhSachSanPham` render lại (vì bất kỳ lý do gì — có thể chỉ một dòng chữ khác trên trang đổi, không liên quan gì tới danh sách sản phẩm), C# tạo ra **các đối tượng delegate mới hoàn toàn** cho từng `sp` trong vòng lặp, khiến Blazor thấy `OnChon` của mọi `DongSanPham` "đổi" (tham chiếu mới) và buộc **toàn bộ** các `DongSanPham` con render lại theo — dù nội dung hiển thị của chúng không có gì thay đổi.

Cách giảm chi phí này — dùng method có tên thay lambda ẩn danh, kết hợp `@key` để Blazor nhận diện đúng từng phần tử trong danh sách khi vòng lặp thay đổi thứ tự/số lượng:

```razor title="DanhSachSanPham.razor (TOT HON)"
@foreach (var sp in danhSachSanPham)
{
    @* @key giúp Blazor khớp đúng DongSanPham cũ với sp cũ khi danh sách
       thay đổi (thêm/xoá/sắp xếp lại) - tránh việc Blazor hiểu nhầm và
       tạo lại toàn bộ DongSanPham thay vì chỉ cập nhật đúng phần tử đổi. *@
    <DongSanPham @key="sp" TenSanPham="@sp" OnChon="ChonSanPhamTheoDong" />
}

@code {
    private List<string> danhSachSanPham = new() { "Bàn phím", "Chuột", "Màn hình" };

    // Method có tên - Blazor build ra CÙNG một EventCallback logic mỗi lần
    // (khác lambda ẩn danh luôn tạo instance mới), giảm nguyên nhân gây
    // "Parameter trông như đổi" ở component con.
    private void ChonSanPhamTheoDong(string ten) => Console.WriteLine($"Đã chọn: {ten}");
}
```

!!! warning "Đây là tối ưu — không phải quy tắc \"cấm tuyệt đối\" lambda trong markup"
    Với danh sách nhỏ (vài chục phần tử) hoặc component con rất rẻ để render lại, chi phí tạo lambda mới mỗi lần thường **không đáng lo** — đừng viết code khó đọc chỉ để né lambda trong mọi trường hợp. Tối ưu này đáng làm khi: (1) danh sách lớn (hàng trăm/nghìn dòng); (2) component con bên trong nặng (chứa biểu đồ, bảng phức tạp); hoặc (3) bạn đã đo được (qua công cụ profiling của trình duyệt) rằng render con đang là điểm nghẽn thật, không phải đoán.

### 4a. Bẫy liên quan: biến vòng lặp bị "bắt" (capture) sai giá trị trong lambda

Một lỗi khác — không phải hiệu năng, nhưng thường xuất hiện cùng chỗ với lambda trong `@foreach` — là bắt nhầm biến vòng lặp. C# hiện đại (`foreach` khai báo biến mới mỗi lần lặp, từ C# 5 trở đi) đã sửa lỗi kinh điển này cho `foreach`, nhưng vẫn dễ mắc nếu bạn tự viết vòng lặp kiểu khác hoặc dùng `for` với biến chỉ số dùng lại:

```razor title="DanhSachSanPham.razor (loi capture voi for - KHONG dung for kieu nay)"
@for (int i = 0; i < danhSach.Count; i++)
{
    @* SAI: "i" là MỘT biến duy nhất dùng lại qua mọi lần lặp (khác foreach).
       Mọi lambda dưới đây đều "bắt" (capture) THAM CHIẾU tới cùng một "i" -
       lúc lambda thực sự được gọi (khi người dùng click), vòng lặp đã chạy
       xong từ lâu, "i" đã bằng danhSach.Count (giá trị cuối cùng). *@
    <button @onclick="() => Console.WriteLine(danhSach[i])">Sản phẩm số @i</button>
}

@code {
    private List<string> danhSach = new() { "Bàn phím", "Chuột", "Màn hình" };
}
```

**Hậu quả cụ thể:** bấm vào bất kỳ nút nào trong 3 nút, console đều in ra lỗi `IndexOutOfRangeException` hoặc (nếu bạn sửa điều kiện dừng) luôn in đúng sản phẩm **cuối cùng**, không phải sản phẩm tương ứng với nút đã bấm — vì tất cả 3 lambda cùng đọc **một** biến `i` dùng chung, và giá trị của nó tại thời điểm lambda thực thi (lúc click) là giá trị sau khi vòng lặp đã kết thúc, không phải giá trị lúc lambda được tạo ra.

Cách sửa — dùng `@foreach` (biến lặp là biến mới mỗi vòng, không bị lỗi này) như các ví dụ mục 4 đã dùng, hoặc nếu buộc phải dùng chỉ số, khai báo một biến cục bộ mới bên trong vòng lặp trước khi dùng trong lambda:

```razor title="DanhSachSanPham.razor (sua dung - copy bien cuc bo truoc khi dung trong lambda)"
@for (int i = 0; i < danhSach.Count; i++)
{
    var chiSoCucBo = i; // biến MỚI, riêng cho mỗi vòng lặp - lambda bắt đúng giá trị này
    <button @onclick="() => Console.WriteLine(danhSach[chiSoCucBo])">Sản phẩm số @chiSoCucBo</button>
}

@code {
    private List<string> danhSach = new() { "Bàn phím", "Chuột", "Màn hình" };
}
```

!!! danger "Đây là lỗi runtime, không phải lỗi build — dễ bị bỏ sót khi test qua loa"
    Code cả hai phiên bản (sai và đúng) đều build thành công, không cảnh báo compiler nào. Lỗi chỉ lộ ra khi **chạy thử và bấm từng nút cụ thể** để so sánh — nếu bạn chỉ test bằng cách nhìn UI hiển thị đúng danh sách (không bấm nút), bạn sẽ không phát hiện được sự khác biệt, vì phần hiển thị (`@i`/`@chiSoCucBo` trong markup, đọc lúc render) luôn đúng — chỉ hành vi bên trong lambda (đọc lúc click, sau khi vòng lặp kết thúc) mới sai.

---

## 5. `dotnet publish -c Release` — định nghĩa và nội dung thư mục publish

**Định nghĩa (một câu):** `dotnet publish -c Release` là lệnh **đóng gói ứng dụng thành bản production**, khác với `dotnet run`/`dotnet build` (dùng để chạy/kiểm tra lúc phát triển) — với một dự án Blazor WebAssembly, lệnh này biên dịch code ở cấu hình `Release` (tối ưu hoá, không kèm thông tin debug đầy đủ) và xuất ra một thư mục chứa **toàn bộ file static** cần để chạy ứng dụng, sẵn sàng đưa lên bất kỳ máy chủ web tĩnh nào.

```text title="lenh publish (chay trong thu muc du an Blazor WASM)"
dotnet publish -c Release
```

```text title="cau truc thu muc sau khi publish (rut gon)"
bin/Release/net10.0/publish/
└── wwwroot/
    ├── index.html                     <- trang HTML gốc, điểm vào của ứng dụng
    ├── css/                           <- CSS của ứng dụng
    ├── _framework/
    │   ├── blazor.webassembly.js      <- script khởi động runtime
    │   ├── dotnet.wasm                <- runtime .NET dạng WebAssembly
    │   ├── blazor.boot.json           <- danh sách + checksum các file cần tải
    │   └── *.dll                      <- assembly BCL + code ứng dụng của bạn
    └── favicon.ico, ...
```

Điểm mấu chốt: thư mục `wwwroot` sau khi publish **không chứa gì ngoài file static** (`.html`, `.css`, `.js`, `.wasm`, `.dll` — các file `.dll` này được trình duyệt tải xuống như file tĩnh, không chạy trên server nào) — không có process ASP.NET Core nào cần chạy phía sau để phục vụ các file này. Đây chính là điểm khác biệt cốt lõi so với publish một ứng dụng ASP.NET Core thường (Minimal API, Blazor Server) — các mô hình đó publish ra một chương trình cần **chạy** (`dotnet YourApp.dll` trên server), còn Blazor WASM publish ra file **chỉ cần host tĩnh**, không cần chạy gì.

!!! note "Vì sao cần `-c Release`, không publish mặc định (`Debug`)"
    Không chỉ định `-c Release`, `dotnet publish` mặc định dùng cấu hình `Debug` — build không tối ưu hoá (code chạy chậm hơn), kèm nhiều thông tin gỡ lỗi không cần thiết cho production, khiến file lớn hơn và chạy chậm hơn so với `Release`. Luôn dùng `-c Release` khi publish bản thật sự đưa cho người dùng dùng.

### 5a. So sánh `dotnet build`, `dotnet run`, và `dotnet publish -c Release`

Ba lệnh này dễ nhầm vì đều "biên dịch code C#", nhưng phục vụ mục đích khác nhau — bảng dưới đối chiếu cụ thể để bạn chọn đúng lệnh cho đúng việc:

| | `dotnet build` | `dotnet run` | `dotnet publish -c Release` |
|---|---|---|---|
| Mục đích | Kiểm tra code có biên dịch được không | Chạy thử ứng dụng ngay trên máy dev | Đóng gói bản production để đưa lên hosting |
| Cấu hình mặc định | `Debug` | `Debug` | Cần chỉ định `-c Release` (mặc định cũng là `Debug` nếu quên) |
| Có tối ưu hoá code không | Không | Không | Có (khi dùng `-c Release`) |
| Đầu ra dùng để làm gì | Chỉ để build tiếp/test, không dùng để deploy | Chạy ngay trong terminal/trình duyệt máy dev, không dùng để deploy | Thư mục `publish/` sẵn sàng copy lên hosting thật |
| Chạy trên máy người dùng cuối được không | Không (thiếu bước đóng gói) | Không (chỉ chạy tại chỗ) | Được — đây chính là mục đích của lệnh này |

Quy tắc thực dụng: dùng `dotnet run` hàng ngày khi code và xem kết quả ngay trên máy; dùng `dotnet build` khi chỉ cần biết code có lỗi biên dịch không (nhanh hơn `run` vì không khởi động ứng dụng); và **chỉ** dùng `dotnet publish -c Release` khi thực sự chuẩn bị đưa bản build cho người dùng thật (kể cả deploy thử nghiệm lên một môi trường staging).

---

## 6. Deploy static hosting — liên hệ với cách Learning Hub này đang được deploy

**Định nghĩa (một câu):** vì thư mục `publish/wwwroot` của Blazor WebAssembly chỉ chứa file static (mục 5), bạn có thể đưa **toàn bộ nội dung thư mục đó** lên bất kỳ dịch vụ **static hosting** (máy chủ chỉ phục vụ file tĩnh, không chạy code phía server) — như GitHub Pages, Azure Static Web Apps, Netlify, Cloudflare Pages — giống hệt cách deploy một trang HTML/CSS/JS thường, không cần máy chủ ASP.NET Core nào chạy phía sau.

**Liên hệ trực tiếp:** trang Learning Hub bạn đang đọc chương này cũng được build bằng MkDocs (một công cụ khác, không phải Blazor) thành các file HTML/CSS/JS **tĩnh**, rồi deploy lên **GitHub Pages** — đúng cùng một mô hình "build ra static files, đẩy lên static hosting" mà một dự án Blazor WebAssembly sẽ dùng. Sự khác biệt duy nhất là công cụ build (MkDocs build tài liệu Markdown thành HTML; `dotnet publish` build code C#/Razor thành HTML+JS+WASM) — bước deploy sau đó (đẩy thư mục output lên GitHub Pages) về nguyên lý là giống nhau.

```text title="vi du luong CI/CD deploy Blazor WASM len GitHub Pages (khai niem, khong chay o day)"
1. Trigger: push code lên nhánh main (giống CI của Learning Hub build khi có commit mới)
2. Bước build: dotnet publish -c Release  ->  sinh ra thư mục wwwroot (mục 5)
3. Bước deploy: copy toàn bộ nội dung wwwroot lên nhánh gh-pages (hoặc thư mục
   docs/ nếu GitHub Pages đọc từ đó) của repository
4. GitHub Pages tự động phục vụ các file static đó qua HTTPS
```

!!! danger "Riêng với GitHub Pages: cần sửa \"base path\" trong `index.html`, nếu không sẽ gặp lỗi tải file 404"
    GitHub Pages mặc định phục vụ một repository tại đường dẫn `https://<user>.github.io/<ten-repo>/`, **không phải** ở gốc domain (`/`). Blazor WebAssembly mặc định sinh `index.html` với thẻ `<base href="/" />`, giả định ứng dụng chạy ở gốc domain — nếu deploy lên GitHub Pages mà **không sửa** thành `<base href="/ten-repo/" />`, trình duyệt sẽ cố tải các file `_framework/*.wasm`, `*.dll` từ đường dẫn sai (thiếu tiền tố `/ten-repo/`), dẫn đến lỗi tải tài nguyên **404 Not Found** cụ thể trong tab Network của DevTools, và trang trắng, ứng dụng không khởi động được — dù `dotnet publish` chạy hoàn toàn không lỗi. Đây là lỗi deploy phổ biến nhất khi lần đầu đưa Blazor WASM lên GitHub Pages.

### 6a. Ví dụ cụ thể một workflow CI/CD deploy lên GitHub Pages

Nối tiếp sơ đồ khái niệm ở trên, đây là nội dung cụ thể hơn của một file workflow GitHub Actions thực hiện đúng bốn bước đó — cùng loại cơ chế mà chính trang Learning Hub bạn đang đọc dùng để tự build và deploy mỗi khi có thay đổi:

```text title=".github/workflows/deploy-blazor.yml (minh hoa cau truc, khong phai file chay thuc trong repo nay)"
name: Deploy Blazor WASM to GitHub Pages
on:
  push:
    branches: [main]

jobs:
  build-and-deploy:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4

      - name: Setup .NET
        uses: actions/setup-dotnet@v4
        with:
          dotnet-version: "10.0.x"

      - name: Publish Release
        run: dotnet publish -c Release -o publish-output

      - name: Sua base href cho dung ten repository
        run: sed -i 's/<base href="\/" \/>/<base href="\/ten-repo\/" \/>/g' publish-output/wwwroot/index.html

      - name: Deploy len GitHub Pages
        uses: peaceiris/actions-gh-pages@v3
        with:
          github_token: GITHUB_TOKEN_TU_DONG_CAP_BOI_ACTIONS
          publish_dir: publish-output/wwwroot
```

Bước "Sua base href" ở trên chính là cách **tự động hoá** việc sửa lỗi mục 6 đã nêu — thay vì phải nhớ sửa tay file `index.html` mỗi lần publish, workflow tự chạy lệnh thay thế chuỗi (`sed`) ngay trong CI, đảm bảo bản deploy luôn đúng base path, không phụ thuộc vào việc người deploy có nhớ sửa tay hay không.

!!! note "`github_token` không phải cú pháp Blazor — đây là biến bí mật (secret) của CI/CD"
    Giá trị thật của `github_token` trong YAML gốc dùng cú pháp biến riêng của GitHub Actions (khác Razor, khác Blazor hoàn toàn) để đọc secret đã lưu trong repository — ở đây viết gọn thành placeholder mô tả để tránh lẫn với cú pháp Razor. `GITHUB_TOKEN` là một token GitHub tự cấp cho mỗi lần chạy workflow, dùng để cấp quyền đẩy (push) code lên nhánh chứa bản deploy tĩnh, không cần bạn tự tạo hay lưu thủ công.

### 6b. So sánh yêu cầu hosting giữa ba mô hình đã học

Sau khi đã thấy cụ thể Blazor WebAssembly deploy như thế nào (mục 5, 6), đây là bảng đối chiếu với hai mô hình khác đã học ở các chương trước, giúp bạn chọn đúng loại hosting khi bắt đầu một dự án mới:

| | Blazor WebAssembly | Blazor Server | ASP.NET Core Minimal API (P3) |
|---|---|---|---|
| Nội dung sau `dotnet publish` | File static (`.html/.css/.js/.wasm/.dll` dùng như file tĩnh) | Một chương trình .NET cần chạy (`dotnet YourApp.dll`) | Một chương trình .NET cần chạy (`dotnet YourApp.dll`) |
| Cần process server chạy liên tục? | Không | Có (giữ kết nối SignalR) | Có (xử lý HTTP request) |
| Deploy được lên GitHub Pages/static hosting thuần? | **Được** | Không | Không |
| Cần hosting nào | Static hosting (GitHub Pages, Azure Static Web Apps, Netlify...) | Azure App Service, VPS, hoặc bất kỳ nơi chạy được ứng dụng .NET liên tục | Azure App Service, VPS, container... |
| Chi phí hosting điển hình | Thường miễn phí hoặc rất rẻ (chỉ phục vụ file tĩnh) | Cần trả phí cho máy chủ chạy liên tục | Cần trả phí cho máy chủ chạy liên tục |
| Chạy offline được (sau khi tải xong) không? | Được (phần UI/logic C#; API riêng vẫn cần mạng) | Không (luôn cần kết nối SignalR liên tục) | Không áp dụng (là API, không phải UI) |

Bảng trên gộp lại đúng các đặc điểm đã học rải rác qua nhiều chương (Blazor Server cần SignalR — chương tổng quan; ASP.NET Core Minimal API — P3; Blazor WebAssembly static hosting — mục 5, 6 chương này) vào một chỗ, giúp bạn trả lời nhanh câu hỏi "dự án này nên deploy ở đâu" dựa vào **loại công nghệ**, không phải đoán theo cảm tính.

---

## 7. Health check & caching header cơ bản cho static asset — giới thiệu ngắn

Sau khi deploy, hai cấu hình phía hosting đáng biết tên (không cần tự tay cấu hình sâu ở mức học này):

- **Caching header cho file `_framework/*`:** vì các file `.wasm`/`.dll` khá nặng (mục 1) nhưng **hiếm khi đổi** giữa các lần publish (chỉ đổi khi bạn deploy bản mới), hosting tốt nên gửi header `Cache-Control` yêu cầu trình duyệt **cache dài hạn** các file này — nhờ vậy, người dùng quay lại trang **không phải tải lại** runtime .NET mỗi lần, chỉ tải lại khi có bản deploy mới (file `blazor.boot.json` có checksum để trình duyệt tự phát hiện file nào đã đổi).
- **Health check endpoint:** khái niệm phổ biến hơn với ứng dụng có server chạy phía sau (ASP.NET Core API, Blazor Server) — một route riêng (ví dụ `/health`) trả về `200 OK` nhanh để hệ thống giám sát/load balancer biết server còn sống. Với Blazor WebAssembly thuần (không server riêng, chỉ static hosting), khái niệm này **không áp dụng trực tiếp** cho chính ứng dụng WASM — nhưng vẫn liên quan nếu ứng dụng của bạn gọi tới một Web API backend (đã học ở P3) cần giám sát riêng.

Ví dụ cụ thể một cấu hình caching header cho Azure Static Web Apps (một dịch vụ static hosting khác GitHub Pages, hỗ trợ cấu hình chi tiết hơn qua file JSON riêng):

```text title="staticwebapp.config.json (minh hoa caching header, khong phai file trong repo nay)"
{
  "routes": [
    {
      "route": "/_framework/*",
      "headers": {
        "cache-control": "public, max-age=31536000, immutable"
      }
    }
  ]
}
```

`max-age=31536000` nghĩa là trình duyệt được phép giữ file này trong cache tối đa 1 năm (31536000 giây) mà không cần hỏi lại server; `immutable` báo cho trình duyệt biết nội dung file này **sẽ không đổi** trong suốt thời gian đó — an toàn để khai báo vì Blazor build thường **đổi tên file** (kèm hash trong tên) mỗi khi nội dung thay đổi, nên file cùng tên chắc chắn cùng nội dung; nếu bạn deploy bản mới, tên file mới sẽ khác, trình duyệt tự tải file mới đó, không dùng nhầm cache cũ.

!!! note "So sánh nhanh: file `index.html` KHÔNG nên cache dài hạn như `_framework/*`"
    Khác với file trong `_framework/`, file `index.html` (điểm vào của ứng dụng) **nên** cấu hình cache ngắn hoặc `no-cache` — vì đây là file đầu tiên trình duyệt tải, nếu nó bị cache quá lâu, người dùng có thể tiếp tục nhận **phiên bản `index.html` cũ** (dù đã deploy bản mới), dẫn tới việc trang cố tải các file `_framework/*` theo tên cũ đã không còn tồn tại trên server — một dạng lỗi 404 khác, xảy ra sau một khoảng thời gian dùng ổn định rồi mới lộ ra khi bạn deploy bản mới, dễ gây nhầm lẫn khi debug vì "code mới deploy rồi mà người dùng vẫn thấy lỗi".

Ví dụ cụ thể route health check áp dụng cho Web API backend (không áp dụng cho chính app Blazor WASM tĩnh, như bullet trên đã nêu):

```csharp title="Program.cs (trich - health check cho Web API backend, KHONG phai cho Blazor WASM)"
// test:compile
// (Trích đoạn - minh hoạ đúng health check áp dụng cho BACKEND API mà Blazor
// WASM gọi tới qua HttpClient, KHÔNG áp dụng cho chính app Blazor WASM tĩnh.
// Dùng API Web SDK trần, khớp với project test CI "dotnet new web".)
var builder = WebApplication.CreateBuilder(args);
var app = builder.Build();

// Route rieng, tra 200 OK nhanh de he thong giam sat/load balancer biet
// backend con song - KHONG lien quan gi den file tinh cua Blazor WASM.
app.MapGet("/health", () => Results.Ok(new { status = "healthy" }));

app.Run();
```

!!! note "Đây là kiến thức nền, không phải kỹ năng cần thực hành ngay"
    Ở giai đoạn học này, bạn chỉ cần nhận diện đúng hai khái niệm trên khi gặp trong tài liệu deploy thực tế (ví dụ file cấu hình `staticwebapp.config.json` của Azure Static Web Apps có mục khai báo caching header) — không cần tự viết cấu hình caching chi tiết trong chương này.

---

## Cạm bẫy & thực chiến

- **Nhầm "Blazor WebAssembly chạy hoàn toàn trong trình duyệt" với "không bao giờ cần mạng":** đúng là sau khi tải xong, code C# chạy offline trong trình duyệt — nhưng nếu ứng dụng của bạn gọi Web API (lấy/lưu dữ liệu qua `HttpClient`), phần đó **vẫn cần mạng**, chỉ riêng phần chạy UI/logic C# tại chỗ là offline được. Đừng quảng cáo "app này chạy offline hoàn toàn" nếu nó còn phụ thuộc API backend.
- **Bật `RunAOTCompilation` cho một ứng dụng CRUD thông thường "để cho nhanh", không đo trước:** như mục 2 đã chỉ ra, AOT tăng đáng kể kích thước file tải xuống — với ứng dụng không có tính toán nặng, cái được (thực thi nhanh hơn) thường không bù được cái mất (tải chậm hơn ở màn hình đầu). Chỉ bật AOT sau khi đã xác định rõ ứng dụng có phần tính toán thực sự cần tốc độ native.
- **Override `ShouldRender()` nhưng quên cập nhật biến theo dõi (như mục 3 minh hoạ) hoặc viết điều kiện chặn quá chặt:** dẫn tới component "đứng hình" — state đã đổi thật nhưng UI không cập nhật, vì `ShouldRender()` luôn trả `false`. Luôn kiểm tra thủ công bằng cách đổi giá trị và quan sát UI có cập nhật đúng như kỳ vọng, đừng chỉ tin code build được là đủ.
- **Tạo lambda/object mới trong markup cho danh sách lớn mà không đo trước có đáng tối ưu hay không (mục 4):** tối ưu này thêm độ phức tạp code (method riêng, `@key`) — chỉ nên áp dụng khi danh sách đủ lớn hoặc component con đủ nặng để chi phí re-render dư thừa thực sự đáng kể; áp dụng tràn lan cho mọi vòng lặp nhỏ chỉ làm code khó đọc hơn mà không đổi lại lợi ích đo được.
- **Publish ở cấu hình `Debug` (quên `-c Release`) rồi đưa lên production:** như mục 5 đã nêu, file sẽ lớn hơn và chạy chậm hơn không cần thiết — luôn dùng `dotnet publish -c Release` cho bản deploy thật.
- **Deploy Blazor WASM lên GitHub Pages mà quên sửa `<base href>` (mục 6):** gây lỗi 404 khi tải `_framework/*`, ứng dụng hiện trang trắng — đây là lỗi deploy phổ biến nhất, luôn kiểm tra tab Network của DevTools nếu gặp trang trắng sau deploy.
- **Nhầm Blazor Server và Blazor WebAssembly khi chọn cách deploy:** Blazor Server **không** thể deploy lên static hosting thuần (GitHub Pages, Netlify tĩnh) vì nó cần một process ASP.NET Core chạy liên tục và giữ kết nối SignalR — chỉ Blazor WebAssembly (mục 5, 6) mới deploy được theo mô hình static hosting này. Nếu dự án của bạn là Blazor Server, cần một dịch vụ hosting chạy được ứng dụng .NET (Azure App Service, VPS...), không phải static hosting.
- **Dùng `for` với biến chỉ số dùng lại rồi viết lambda đọc biến đó trực tiếp trong `@onclick` (mục 4a):** đây là lỗi runtime âm thầm, không lỗi biên dịch — mọi lambda tạo trong vòng lặp đều đọc nhầm giá trị cuối cùng của biến chỉ số. Ưu tiên `@foreach` (biến lặp mới mỗi vòng) khi có thể; nếu buộc dùng `for`, luôn copy biến chỉ số vào một biến cục bộ mới trước khi dùng trong lambda.
- **Cache `index.html` quá lâu ở tầng CDN/hosting (mục 7):** khiến người dùng tiếp tục nhận `index.html` cũ tham chiếu tới các file `_framework/*` theo tên cũ, gây lỗi 404 xuất hiện **muộn**, sau khi bạn đã deploy bản mới tưởng như thành công — dễ gây nhầm lẫn vì "vừa deploy xong, log CI báo thành công, nhưng người dùng vẫn báo lỗi". Luôn cấu hình `index.html` với cache ngắn hoặc `no-cache`, chỉ cache dài hạn cho file trong `_framework/` (có tên kèm hash, đổi khi nội dung đổi).

---

## Bài tập

**Bài 1 (giàn giáo — nhận diện đúng khái niệm):** Ba phát biểu sau, phát biểu nào ĐÚNG?
(a) Blazor WebAssembly tải chậm hơn web thường ở lần đầu vì phải tải thêm runtime .NET dạng WASM.
(b) `dotnet publish -c Release` cho Blazor WASM sinh ra một chương trình cần `dotnet YourApp.dll` để chạy trên server.
(c) `ShouldRender()` trả về `false` khiến Blazor bỏ qua hoàn toàn việc tính toán lại render tree cho component đó ở lần gọi này.

??? success "Lời giải + vì sao"
    **(a) Đúng** — đúng như mục 1, phải tải thêm `dotnet.wasm` và các assembly `.dll` trước khi chạy được code C# nào.

    **(b) Sai** — đây là mô tả publish của ASP.NET Core thường (Minimal API, Blazor Server). Blazor WebAssembly publish ra **file static thuần** (`wwwroot/`), không có chương trình nào cần `dotnet` chạy trên server để phục vụ chúng (mục 5).

    **(c) Đúng** — đúng định nghĩa mục 3: trả `false` khiến Blazor bỏ qua hoàn toàn lần render đó cho component này.

**Bài 2 (sửa lỗi — tìm nguyên nhân re-render dư):** Component sau render lại toàn bộ 3 `DongSanPham` con mỗi khi `tieuDe` (không liên quan gì tới danh sách sản phẩm) đổi. Tìm nguyên nhân cụ thể và sửa.

```razor title="TrangSanPham.razor (co van de - tim va sua)"
<h3>@tieuDe</h3>
<button @onclick="DoiTieuDe">Đổi tiêu đề</button>

@foreach (var sp in danhSach)
{
    <DongSanPham TenSanPham="@sp" OnChon="() => Console.WriteLine(sp)" />
}

@code {
    private string tieuDe = "Danh sách sản phẩm";
    private List<string> danhSach = new() { "Bàn phím", "Chuột" };

    private void DoiTieuDe() => tieuDe = tieuDe == "Danh sách sản phẩm" ? "Sản phẩm nổi bật" : "Danh sách sản phẩm";
}
```

??? success "Lời giải + vì sao"
    **Nguyên nhân:** đúng vấn đề mục 4 — mỗi lần `TrangSanPham` render (kể cả chỉ vì `tieuDe` đổi, không liên quan `danhSach`), lambda `() => Console.WriteLine(sp)` trong vòng lặp được **tạo mới** cho mỗi `sp`, khiến `OnChon` của mọi `DongSanPham` "trông như đổi" (tham chiếu khác), buộc cả 3 component con render lại theo, dù `danhSach` không hề thay đổi.

    **Sửa lại — dùng method có tên:**

    ```razor title="TrangSanPham.razor (da sua)"
    <h3>@tieuDe</h3>
    <button @onclick="DoiTieuDe">Đổi tiêu đề</button>

    @foreach (var sp in danhSach)
    {
        <DongSanPham @key="sp" TenSanPham="@sp" OnChon="InLog" />
    }

    @code {
        private string tieuDe = "Danh sách sản phẩm";
        private List<string> danhSach = new() { "Bàn phím", "Chuột" };

        private void DoiTieuDe() => tieuDe = tieuDe == "Danh sách sản phẩm" ? "Sản phẩm nổi bật" : "Danh sách sản phẩm";

        private void InLog(string ten) => Console.WriteLine(ten);
    }
    ```

    `InLog` là một method có tên — Blazor không tạo delegate mới mỗi lần render cho nó, nên `OnChon` của `DongSanPham` không còn "trông như đổi" chỉ vì `tieuDe` thay đổi, giảm re-render dư thừa cho các component con không liên quan.

**Bài 3 (sửa lỗi — bẫy capture biến vòng lặp):** Đoạn code sau dùng `for` để hiển thị danh sách và log số thứ tự khi click. Chạy thử, bấm vào nút thứ 2 (chỉ số `1`) — console lại in ra `3` (giá trị `danhSach.Count`) và ném `IndexOutOfRangeException`. Giải thích nguyên nhân và sửa lại.

```razor title="DanhSachDon.razor (co loi capture - tim va sua)"
@for (int i = 0; i < danhSach.Count; i++)
{
    <button @onclick="() => Console.WriteLine($" Ban da bam so {i}: {danhSach[i]}")">
        Sản phẩm @i
    </button>
}

@code {
    private List<string> danhSach = new() { "Bàn phím", "Chuột", "Màn hình" };
}
```

??? success "Lời giải + vì sao"
    **Nguyên nhân:** đúng vấn đề mục 4a — `for` dùng lại **một** biến `i` duy nhất suốt vòng lặp, mọi lambda `() => ...` được tạo trong vòng lặp đều "bắt" (capture) tham chiếu tới cùng biến `i` đó, không phải giá trị của `i` tại thời điểm tạo lambda. Khi người dùng click (xảy ra **sau khi** vòng lặp đã chạy xong hoàn toàn, `i` đã tăng tới giá trị bằng `danhSach.Count`), mọi lambda đọc `i` đều thấy giá trị cuối cùng đó — dẫn tới `danhSach[i]` truy cập chỉ số vượt quá độ dài danh sách, ném `IndexOutOfRangeException`.

    **Sửa lại — copy `i` vào một biến cục bộ mới trong mỗi vòng lặp trước khi dùng trong lambda:**

    ```razor title="DanhSachDon.razor (da sua)"
    @for (int i = 0; i < danhSach.Count; i++)
    {
        var chiSoRieng = i;
        <button @onclick="() => Console.WriteLine($" Ban da bam so {chiSoRieng}: {danhSach[chiSoRieng]}")">
            Sản phẩm @chiSoRieng
        </button>
    }

    @code {
        private List<string> danhSach = new() { "Bàn phím", "Chuột", "Màn hình" };
    }
    ```

    Mỗi vòng lặp tạo ra một `chiSoRieng` **mới**, riêng biệt cho lần lặp đó — lambda của nút thứ 2 bắt đúng `chiSoRieng = 1` của riêng vòng lặp đó, không bị ảnh hưởng bởi các lần lặp sau. Cách đơn giản hơn nữa (khi có thể) là chuyển hẳn sang `@foreach (var sp in danhSach)` như mục 4 đã dùng — biến lặp của `foreach` vốn đã là biến mới mỗi vòng, không cần thêm bước copy tay.

**Bài 4 (thiết kế — quyết định deploy):** Nhóm bạn có hai ứng dụng: (a) một dashboard nội bộ chỉ 5 nhân viên dùng, cần hiển thị dữ liệu real-time cập nhật liên tục từ database, không quan tâm SEO; (b) một trang landing page giới thiệu sản phẩm, cần tải cực nhanh cho khách hàng lần đầu ghé, không có tương tác phức tạp. Ứng dụng nào nên chọn Blazor WebAssembly + static hosting, ứng dụng nào nên xem xét lại (không hợp với static hosting)? Giải thích bằng các tiêu chí đã học.

??? success "Lời giải + vì sao"
    **(a) Dashboard nội bộ real-time:** không hợp với Blazor WebAssembly + static hosting theo đúng nghĩa "chỉ file tĩnh" nếu dữ liệu cần **đẩy liên tục từ server xuống** (không phải client tự poll) — trường hợp này gần với đặc điểm Blazor Server hơn (cần kết nối liên tục, cập nhật UI theo thời gian thực qua SignalR), như đã học ở chương tổng quan. Nếu vẫn muốn dùng Blazor WebAssembly (chạy trong trình duyệt), ứng dụng cần tự gọi API backend định kỳ hoặc dùng SignalR/WebSocket riêng — backend đó **không** phải static hosting, cần một server chạy liên tục.

    **(b) Landing page giới thiệu sản phẩm:** đây lại là trường hợp cần **cân nhắc lại việc dùng Blazor WebAssembly**, dù nó deploy được lên static hosting — vì mục tiêu chính là "tải cực nhanh lần đầu", mà mục 1 đã chỉ rõ Blazor WebAssembly có chi phí cold start cao (phải tải runtime .NET trước khi hiển thị được gì). Với trang không cần tương tác phức tạp, một trang HTML/CSS/JS thường (hoặc dùng chính MkDocs như Learning Hub này) phù hợp hơn về mục tiêu tải nhanh, dù cũng deploy được trên cùng loại static hosting.

    **Bài học chung:** "deploy được lên static hosting" (đúng với Blazor WebAssembly) không đồng nghĩa với "luôn là lựa chọn công nghệ đúng cho mọi loại trang" — cần đối chiếu với đặc điểm dữ liệu (tĩnh hay real-time) và mục tiêu hiệu năng (tải nhanh lần đầu hay tương tác phong phú sau khi tải) trước khi chọn.

**Bài 5 (đánh giá — quyết định AOT):** Nhóm bạn đang xây một ứng dụng Blazor WebAssembly chỉnh sửa ảnh ngay trong trình duyệt (áp filter, xoay, crop — toàn bộ tính toán pixel chạy bằng C#, không gọi API nào cho phần xử lý ảnh). Người dùng phàn nàn thao tác áp filter bị giật, chậm — nhưng thời gian tải trang lần đầu (đã đo bằng DevTools) không phải vấn đề họ quan tâm, vì họ dùng lại ứng dụng này hàng ngày (đã cache). Bạn có nên bật `RunAOTCompilation` không? Giải thích bằng đúng tiêu chí đánh đổi ở mục 2.

??? success "Lời giải + vì sao"
    **Nên bật AOT.** Đối chiếu với bảng đánh đổi mục 2: đây chính xác là trường hợp "ứng dụng tính toán nặng (xử lý ảnh) chạy ngay trong trình duyệt" — cột bên phải của bảng. Hai điều kiện quan trọng đều khớp: (1) vấn đề người dùng gặp là **tốc độ thực thi** (giật khi áp filter — tính toán pixel chạy chậm), đúng thứ AOT cải thiện trực tiếp (chạy mã native thay vì diễn giải IL); (2) **thời gian tải lần đầu không phải mối quan tâm chính** (người dùng dùng lại hàng ngày, đã cache, chỉ trả giá tải nặng đúng một lần) — nghĩa là cái giá phải trả của AOT (file lớn hơn, tải chậm hơn ở lần đầu) không ảnh hưởng nhiều tới trải nghiệm thực tế của họ.

    Đây là ví dụ ngược lại với "!!! danger" ở mục 2: nếu ứng dụng là CRUD thông thường và người dùng phàn nàn về tốc độ **tải trang**, bật AOT sẽ làm vấn đề tệ hơn (tăng dung lượng tải). Nhưng ở đây, vấn đề là tốc độ **thực thi** cho một tác vụ tính toán nặng, và chi phí tải không phải điểm đau — đúng kịch bản AOT được thiết kế để giải quyết.

---

## Tự kiểm tra

1. Vì sao Blazor WebAssembly tải lần đầu chậm hơn một trang HTML/JS thường, dù cả hai đều deploy dưới dạng file static?

    ??? note "Đáp án"
        Vì trước khi chạy được bất kỳ dòng code C# nào, trình duyệt phải tải thêm một bộ runtime .NET biên dịch sang WebAssembly (`dotnet.wasm`) và các assembly `.dll` (BCL + code ứng dụng) — trang HTML/JS thường chỉ cần tải file JS và chạy ngay bằng engine JavaScript có sẵn của trình duyệt, không cần tải thêm runtime nào.

2. AOT compilation đánh đổi cái gì để lấy cái gì?

    ??? note "Đáp án"
        Đánh đổi kích thước file tải xuống lớn hơn (và thời gian tải lần đầu chậm hơn) để lấy tốc độ thực thi code nhanh hơn sau khi đã tải xong (vì code được biên dịch sẵn thành native WASM, không cần diễn giải IL lúc runtime).

3. `ShouldRender()` dùng để làm gì, và trả về `false` có nghĩa là gì cụ thể?

    ??? note "Đáp án"
        Là phương thức override để quyết định component có cần render lại hay không mỗi khi Blazor sắp render nó. Trả về `false` khiến Blazor bỏ qua hoàn toàn lần render đó — không tính toán lại render tree cho component này ở lần gọi hiện tại.

4. Vì sao viết lambda trực tiếp trong markup (ví dụ `OnChon="() => ChonSanPham(sp)"`) trong một `@foreach` có thể gây re-render dư thừa cho component con?

    ??? note "Đáp án"
        Vì mỗi lần component cha render lại, biểu thức lambda đó được đánh giá lại và tạo ra một delegate instance mới cho mỗi phần tử trong vòng lặp — component con nhận giá trị này qua `[Parameter]` sẽ thấy "giá trị đổi" (tham chiếu khác so với lần trước) và bị buộc render lại theo, dù nội dung logic không hề thay đổi.

5. `dotnet publish -c Release` cho một dự án Blazor WebAssembly sinh ra loại nội dung gì trong thư mục publish, và có cần một process nào chạy để phục vụ nó không?

    ??? note "Đáp án"
        Sinh ra một thư mục `wwwroot` chỉ chứa file static (`.html`, `.css`, `.js`, `.wasm`, `.dll` đóng vai trò file tĩnh) — không cần bất kỳ process ASP.NET Core nào chạy phía sau để phục vụ các file này, khác với publish một ứng dụng ASP.NET Core thường cần `dotnet YourApp.dll` chạy trên server.

6. Vì sao có thể deploy Blazor WebAssembly lên GitHub Pages, nhưng không thể deploy Blazor Server lên đó theo cùng cách?

    ??? note "Đáp án"
        Vì Blazor WebAssembly sau khi publish chỉ là file static, phù hợp với GitHub Pages (chỉ phục vụ file tĩnh, không chạy code phía server). Blazor Server cần một process ASP.NET Core chạy liên tục và giữ kết nối SignalR để hoạt động — GitHub Pages không hỗ trợ chạy chương trình phía server, nên không thể host Blazor Server.

7. Nếu deploy một app Blazor WebAssembly lên GitHub Pages mà gặp trang trắng, các file `_framework/*.wasm` báo lỗi 404 trong tab Network, nguyên nhân phổ biến nhất là gì?

    ??? note "Đáp án"
        Quên sửa `<base href="/" />` trong `index.html` thành đường dẫn con đúng với tên repository (`<base href="/ten-repo/" />`), vì GitHub Pages phục vụ repository tại `/ten-repo/`, không phải gốc domain — nếu không sửa, trình duyệt tải các file `_framework/*` từ đường dẫn sai, dẫn đến 404.

8. Health check endpoint có áp dụng trực tiếp cho một ứng dụng Blazor WebAssembly thuần (không có server riêng) không? Vì sao?

    ??? note "Đáp án"
        Không áp dụng trực tiếp cho chính ứng dụng WASM, vì nó không có process server nào chạy phía sau để cần kiểm tra "còn sống". Khái niệm này chỉ liên quan nếu ứng dụng gọi tới một Web API backend riêng — health check khi đó áp dụng cho backend đó, không phải cho phần WASM chạy trong trình duyệt.

9. `blazor.boot.json` dùng để làm gì, và checksum trong file này giúp giải quyết vấn đề gì cho lần người dùng ghé lại trang?

    ??? note "Đáp án"
        Đây là danh sách các file (assembly, `dotnet.wasm`...) mà script khởi động (`blazor.webassembly.js`) cần tải, kèm checksum (hash) của từng file. Checksum giúp trình duyệt so sánh với file đã có trong cache: nếu khớp, không tải lại — chỉ tải lại đúng những file nào đã đổi so với lần deploy trước, giúp lần ghé lại sau nhanh hơn lần đầu.

10. Vì sao dùng `for` với một biến chỉ số `i` dùng lại xuyên suốt vòng lặp, rồi viết lambda đọc `i` bên trong, thường gây lỗi khi lambda được gọi sau (như lúc người dùng click), khác với dùng `@foreach`?

    ??? note "Đáp án"
        Vì `for` dùng lại đúng MỘT biến `i` cho mọi lần lặp — mọi lambda tạo trong vòng lặp đều "bắt" tham chiếu tới cùng biến đó, không phải giá trị tại thời điểm tạo. Khi lambda thực sự chạy (sau khi vòng lặp đã kết thúc), `i` đã ở giá trị cuối cùng, khiến mọi lambda đọc nhầm cùng một giá trị đó. `@foreach` tạo một biến lặp mới cho mỗi vòng, nên không gặp lỗi này.

11. Tại sao file `_framework/*.wasm` nên cấu hình cache dài hạn (ví dụ 1 năm), nhưng `index.html` thì không nên?

    ??? note "Đáp án"
        File trong `_framework/` thường đổi tên (kèm hash) mỗi khi nội dung thay đổi, nên cache dài hạn là an toàn — file cùng tên chắc chắn cùng nội dung. `index.html` thì giữ tên cố định qua mọi lần deploy; nếu cache nó quá lâu, người dùng có thể tiếp tục dùng bản `index.html` cũ tham chiếu tới các file `_framework/*` theo tên cũ đã không còn tồn tại sau khi deploy bản mới, gây lỗi 404 xuất hiện muộn sau khi deploy.

12. `ShouldRender()` có chặn được lần render đầu tiên của một component mới được thêm vào cây UI không?

    ??? note "Đáp án"
        Không. Blazor luôn render component lần đầu tiên khi nó được thêm vào cây UI, không hỏi `ShouldRender()` ở lần đó. `ShouldRender()` chỉ có tác dụng cho các lần render tiếp theo, sau khi component đã tồn tại và có sự kiện hoặc Parameter mới kích hoạt render lại.

13. So sánh: nếu một ứng dụng cần cập nhật UI real-time liên tục dựa trên dữ liệu đẩy từ server (không phải client tự bấm), đặc điểm này gần với Blazor Server hay Blazor WebAssembly hơn — và điều đó ảnh hưởng gì tới lựa chọn deploy static hosting?

    ??? note "Đáp án"
        Gần với Blazor Server hơn — mô hình này vốn thiết kế để giữ kết nối liên tục (SignalR) và đẩy UI diff từ server xuống theo thời gian thực. Vì Blazor Server cần một process server chạy liên tục, nó không thể deploy lên static hosting (chỉ phục vụ file tĩnh) như Blazor WebAssembly — cần một dịch vụ hosting chạy được ứng dụng .NET.

14. Một ứng dụng Blazor WebAssembly xử lý ảnh nặng trong trình duyệt, người dùng đã cache và không quan tâm tốc độ tải lần đầu, nhưng phàn nàn thao tác chạy giật. AOT có phù hợp ở đây không? Vì sao?

    ??? note "Đáp án"
        Phù hợp. Đây đúng trường hợp AOT được thiết kế để giải quyết: vấn đề là tốc độ thực thi (tính toán ảnh chạy giật) chứ không phải tốc độ tải, và chi phí đánh đổi của AOT (file tải lớn hơn) không ảnh hưởng nhiều vì người dùng đã cache và không coi tải lần đầu là vấn đề.

15. `dotnet build`, `dotnet run`, và `dotnet publish -c Release` khác nhau ở điểm nào về mục đích sử dụng?

    ??? note "Đáp án"
        `dotnet build` chỉ kiểm tra code có biên dịch được không, không tối ưu hoá, không dùng để deploy. `dotnet run` chạy thử ứng dụng ngay trên máy dev, cũng không tối ưu hoá và không dùng để deploy. `dotnet publish -c Release` đóng gói bản production đã tối ưu hoá, sinh ra thư mục sẵn sàng đưa lên hosting thật — đây là lệnh duy nhất trong ba lệnh này phù hợp để deploy.

16. Gắn một domain riêng ở gốc cho một app Blazor WebAssembly deploy trên GitHub Pages (thay vì dùng đường dẫn `<user>.github.io/<repo>`) ảnh hưởng gì tới lỗi `base href` đã học ở mục 6?

    ??? note "Đáp án"
        Lỗi đó không còn xảy ra, vì khi dùng domain riêng ở gốc, ứng dụng thực sự chạy tại `/` — khớp đúng với giá trị mặc định `<base href="/" />` mà Blazor WebAssembly tự sinh ra, không cần sửa thành `/ten-repo/` như khi chạy dưới đường dẫn con của GitHub Pages mặc định.

---

??? abstract "DEEP DIVE — nâng cao (ngoài fast path)"
    - **Lazy loading assembly:** với ứng dụng lớn có nhiều trang ít dùng, Blazor WebAssembly hỗ trợ tải một số assembly `.dll` **theo nhu cầu** (khi người dùng vào đúng route cần nó) thay vì tải tất cả ngay từ đầu — giảm chi phí tải lần đầu cho phần code không phải ai cũng dùng ngay. Cấu hình qua thuộc tính `BlazorWebAssemblyLazyLoad` trong `.csproj`, kết hợp `Router` xử lý `OnNavigateAsync` để tải assembly đúng lúc.
    - **Trimming (cắt bớt code không dùng):** `dotnet publish -c Release` cho Blazor WASM mặc định đã áp dụng một mức trimming (loại bỏ code/assembly BCL không được tham chiếu tới) để giảm kích thước tải xuống — mức trimming có thể cấu hình chặt hơn (`<TrimMode>Full</TrimMode>`), nhưng trimming chặt có rủi ro loại bỏ nhầm code được gọi qua reflection (không thấy được qua phân tích tĩnh lúc build), cần test kỹ nếu bật mức cao.
    - **Compression (Brotli/Gzip) cho file `_framework`:** hosting tốt (bao gồm cả GitHub Pages qua cấu hình phù hợp, hoặc Azure Static Web Apps mặc định) nên phục vụ các file `.wasm`/`.dll` đã nén Brotli hoặc Gzip — `dotnet publish` tự sinh sẵn file `.br`/`.gz` song song, chỉ cần server cấu hình đúng header `Content-Encoding` để trình duyệt nhận và tự giải nén, giảm đáng kể băng thông tải lần đầu so với file thô.
    - **Service Worker & offline-first PWA:** Blazor WebAssembly có thể cấu hình thành Progressive Web App (PWA) với Service Worker cache lại toàn bộ file `_framework` — cho phép ứng dụng khởi động lại **hoàn toàn offline** ở các lần sau (không chỉ nhanh hơn nhờ cache trình duyệt thông thường, mà còn chạy được khi mất mạng hẳn), đây là lợi ích thực tế thường được nhấn mạnh khi so sánh Blazor WebAssembly với Blazor Server ở khía cạnh "chạy offline được".
    - **`RenderFragment`/`@key` với danh sách rất lớn (virtualization):** khi danh sách có hàng nghìn phần tử, dù đã tránh tạo lambda mới (mục 4) và dùng `@key` đúng (mục 4), Blazor vẫn phải giữ trong bộ nhớ (và DOM) toàn bộ phần tử nếu render hết một lần. Component có sẵn `Virtualize` (namespace `Microsoft.AspNetCore.Components.Web.Virtualization`) chỉ render các phần tử **đang hiển thị trong khung nhìn** (viewport), tải/giải phóng thêm khi người dùng cuộn — giảm đáng kể số DOM node và chi phí render cho danh sách cực lớn, một mức tối ưu sâu hơn những gì mục 3–4 đã đủ giải quyết cho danh sách kích thước vừa.
    - **`dotnet publish` với self-contained/single-file (không áp dụng cho Blazor WebAssembly):** với ứng dụng console/API .NET thông thường, bạn có thể `dotnet publish` dạng self-contained (đóng gói cả runtime .NET vào một file thực thi, không cần máy đích cài .NET). Khái niệm này **không áp dụng** cho Blazor WebAssembly theo cùng cách — trình duyệt luôn cần tải runtime WASM riêng của nó (mục 1), không có khái niệm "một file thực thi duy nhất" như ứng dụng desktop/console; đừng nhầm hai khái niệm "đóng gói runtime" này dù nghe tương tự.
    - **Đo hiệu năng thật bằng DevTools, không đoán:** trước khi áp dụng bất kỳ tối ưu nào ở mục 3–4 (hoặc AOT ở mục 2), tab **Performance** và **Network** của DevTools trình duyệt cho phép đo chính xác: thời gian tải từng file (Network), và thời gian CPU dùng để render/tính toán (Performance, ghi lại một "profile" khi bạn tương tác). Tối ưu theo cảm tính (đoán chỗ nào chậm) thường sai chỗ — luôn đo trước, sửa đúng điểm nghẽn thật, rồi đo lại để xác nhận cải thiện.
    - **Preload/prefetch tài nguyên trong `index.html`:** một số dự án thêm thẻ `<link rel="preload">` cho `dotnet.wasm` ngay trong `<head>` của `index.html`, báo trước cho trình duyệt "tài nguyên này sẽ cần sớm, bắt đầu tải song song ngay" thay vì đợi `blazor.webassembly.js` chạy xong rồi mới yêu cầu tải — có thể rút ngắn một phần nhỏ thời gian cold start bằng cách tận dụng tốt hơn các kết nối mạng song song của trình duyệt, dù không thay đổi tổng số byte cần tải (khác hẳn với trimming/compression ở trên, vốn giảm số byte thật sự).
    - **Custom domain cho GitHub Pages/Azure Static Web Apps:** cả hai dịch vụ đều cho phép gắn một domain riêng (thay vì `<user>.github.io/<repo>`) qua bản ghi DNS (CNAME) — khi dùng domain riêng ở gốc (`/`, không phải `/ten-repo/`), lỗi `base href` ở mục 6 **không còn xảy ra**, vì ứng dụng lúc đó thực sự chạy ở gốc domain, khớp với giá trị mặc định `<base href="/" />` mà Blazor WebAssembly tự sinh — một lý do thực tế khiến nhiều dự án production chọn gắn domain riêng ngay từ đầu, tránh phải nhớ sửa `base href` mỗi lần publish.

---

## Tổng kết nhanh trước khi qua chương ôn tập

Chương này khép lại chuỗi kiến thức Blazor bắt đầu từ tổng quan (mô hình Server/WebAssembly/Hybrid), qua component/binding/routing/state/JS interop, tới đúng câu hỏi cuối cùng mọi dự án thực tế đều gặp: **làm sao đưa ứng dụng này tới tay người dùng, và chạy đủ nhanh khi họ dùng nó**. Ba trục đã học:

1. **Hiểu chi phí đặc thù của mô hình** (mục 1–2): Blazor WebAssembly trả giá bằng thời gian tải lần đầu để đổi lại khả năng chạy hoàn toàn trong trình duyệt, không cần server sau đó — AOT là một nút chỉnh thêm trên trục đánh đổi này (tải chậm hơn, chạy nhanh hơn), không phải "tối ưu miễn phí".
2. **Kiểm soát re-render ở tầng component** (mục 3–4): `ShouldRender()` và tránh tạo object mới trong markup là hai công cụ cụ thể, dùng khi đã xác định đúng điểm nghẽn (deep dive nhắc lại: đo trước, đừng đoán).
3. **Đưa ứng dụng lên môi trường thật** (mục 5–7): `dotnet publish -c Release` sinh ra file static, deploy được lên bất kỳ static hosting nào theo đúng cách trang Learning Hub này đang chạy — kèm hai lỗi cụ thể cần nhớ (`base href` sai gây 404, cache `index.html` quá lâu gây lỗi 404 muộn sau khi deploy).
4. **Chọn đúng mô hình cho đúng bài toán** (bảng mục 6b, bài tập 4): "deploy được lên static hosting" chỉ đúng với Blazor WebAssembly, không đúng với Blazor Server hay ASP.NET Core Minimal API — và ngay cả khi Blazor WebAssembly deploy được, nó không phải lựa chọn tối ưu cho mọi loại trang (ví dụ landing page cần tải cực nhanh nên ưu tiên HTML/JS thường thay vì chấp nhận chi phí cold start của mục 1).

Cùng với chương JS Interop & lifecycle nâng cao đã học trước, chương này hoàn thiện bộ kỹ năng cần để không chỉ **viết** một ứng dụng Blazor chạy đúng, mà còn **vận hành** nó tốt trong tay người dùng thật — từ lúc họ bấm vào link lần đầu tới lúc bạn đẩy bản cập nhật tiếp theo lên production.

Tiếp theo -> ôn tập & tổng kết p7 blazor
