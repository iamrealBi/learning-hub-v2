---
tier: core
status: core
owner: core-team
verified_on: "2026-07-05"
dotnet_version: "10.0"
bloom: áp dụng
requires: [p7-component]
est_minutes_fast: 30
---

# Data Binding & Xử lý sự kiện

!!! info "Bạn đang ở đây"
    cần trước: đã biết HTML/CSS cơ bản, C# từ P1 (biến, method, class), và component Blazor cơ bản (`.razor` là gì, `@code{}` block, cách một component render ra HTML) từ chương trước.
    mở khoá: cho component **phản hồi hành động người dùng** (click, gõ chữ, submit form) và **đồng bộ** giá trị giữa input HTML và biến C#, biết chính xác khi nào UI cập nhật, khi nào phải tự gọi lệnh vẽ lại, và cách một component con "báo tin" lên component cha.

> Mục tiêu (đo được): sau chương này bạn **viết** được một `@onclick` handler tăng biến đếm, **viết** được một `@bind` hai chiều giữa input text và biến C# string, **giải thích** được vì sao `@bind` mặc định chỉ cập nhật lúc mất focus (không phải lúc gõ), **áp dụng** được `@bind:event="oninput"` khi cần cập nhật ngay lúc gõ, **giải thích** được khi nào phải tự gọi `StateHasChanged()`, và **viết** được một `EventCallback<T>` tối thiểu để component con gửi dữ liệu lên component cha.

---

## 0. Đoán nhanh trước khi học

Bạn có component sau — một input text, và một đoạn hiển thị lại đúng giá trị bạn vừa gõ:

```razor title="DoanNhanh.razor"
<input value="@ten" />
<p>Xin chào, @ten!</p>

@code {
    private string ten = "";
}
```

Bạn chạy thử, gõ "An" vào input. Dòng `<p>Xin chào, @ten!</p>` có đổi theo không?

??? question "Câu hỏi: gõ vào input, dòng chào có tự cập nhật không?"
    **Không.** `value="@ten"` chỉ là **một chiều**: nó lấy giá trị của biến `ten` để hiển thị lúc render, nhưng **không có đường nào** để giá trị người dùng gõ vào input quay trở lại gán cho biến `ten` trong C#. Đây là lỗi rất phổ biến khi mới học Blazor: nhầm HTML attribute bình thường (`value="..."`) với ràng buộc hai chiều thật sự.

    Mục 2 sẽ chỉ ra: muốn input và biến C# đồng bộ **cả hai chiều** (gõ vào input → biến C# đổi, VÀ biến C# đổi bằng code → input hiển thị lại), phải dùng `@bind`, không phải `value="@..."` viết tay.

Chương trước đã học component `.razor` render ra HTML tĩnh dựa trên `@code{}` — nhưng chưa có cách nào để component **phản hồi** hành động người dùng (click, gõ chữ) hay để dữ liệu chảy **ngược** từ HTML về C#. Đây chính là hai việc chương này giải quyết: mục 1 học cách "nghe" hành động người dùng qua `@onclick` và các directive cùng họ; mục 2–4 học cách đồng bộ hai chiều giữa input và biến qua `@bind`; mục 5 học cách báo cho Blazor vẽ lại UI khi state đổi từ một nguồn nó không tự biết; mục 6 học cách một component con "nói chuyện" ngược lên component cha.

---

## 1. `@onclick` và các event handler khác — định nghĩa và ví dụ tối thiểu

**Định nghĩa (một câu):** `@onclick` (và các directive cùng họ như `@onchange`, `@oninput`, `@onsubmit`) là cách Blazor **gắn một method C# làm handler** cho một sự kiện DOM cụ thể (click chuột, thay đổi giá trị input, submit form) — khi sự kiện đó xảy ra trên trình duyệt, Blazor tự gọi method C# bạn chỉ định, không cần viết JavaScript.

Ví dụ tối thiểu, độc lập — một button tăng biến đếm mỗi lần click:

```razor title="BoDemClick.razor"
<p>Số lần click: @soLan</p>
<button @onclick="TangSoLan">Click vào đây</button>

@code {
    private int soLan = 0;

    private void TangSoLan()
    {
        soLan++;
    }
}
```

Điểm mấu chốt: `@onclick="TangSoLan"` gắn method `TangSoLan` (không kèm dấu ngoặc `()`) vào sự kiện click của `<button>`. Mỗi lần người dùng click, Blazor gọi `TangSoLan()`, method này tăng `soLan`, và **Blazor tự động vẽ lại (re-render) component** vì `soLan` thay đổi trong lúc xử lý một event do chính Blazor điều phối — đoạn `<p>Số lần click: @soLan</p>` tự cập nhật ngay, không cần bạn viết thêm gì.

`@onchange`, `@oninput`, `@onsubmit` hoạt động theo đúng nguyên lý này, chỉ khác sự kiện DOM được lắng nghe:

```razor title="CacEventKhac.razor"
<input @oninput="KhiGoChu" placeholder="Gõ gì đó..." />
<p>Bạn vừa gõ (ký tự cuối event): @kyTuCuoi</p>

<form @onsubmit="KhiSubmit">
    <button type="submit">Gửi</button>
</form>
<p>Đã submit: @daSubmit</p>

@code {
    private string kyTuCuoi = "";
    private bool daSubmit = false;

    // ChangeEventArgs chứa giá trị mới của input tại thời điểm sự kiện xảy ra.
    private void KhiGoChu(ChangeEventArgs e)
    {
        kyTuCuoi = e.Value?.ToString() ?? "";
    }

    private void KhiSubmit()
    {
        daSubmit = true;
    }
}
```

`@oninput` bắn **mỗi lần một ký tự** thay đổi trong input (gõ, xoá, paste). `@onchange` bắn khi giá trị input đổi **và** người dùng rời khỏi input (mất focus) hoặc nhấn Enter. `@onsubmit` bắn khi `<form>` được submit (click nút `type="submit"` hoặc Enter trong một input của form) — và tự động **chặn hành vi mặc định** của trình duyệt (tải lại trang), nên bạn không cần gọi `event.preventDefault()` như trong JavaScript thuần.

Handler có thể nhận **không tham số** (như `TangSoLan()` ở ví dụ đầu) hoặc nhận đúng **một tham số kiểu `EventArgs` phù hợp** với loại event đó — Blazor tự chọn kiểu tham số đúng khi bạn khai báo handler với chữ ký tương ứng:

- `@onclick` → tham số kiểu `MouseEventArgs` (có `ClientX`, `ClientY`, `ShiftKey`... nếu cần biết chi tiết vị trí/phím bấm kèm).
- `@onchange`/`@oninput` → tham số kiểu `ChangeEventArgs` (có `Value`, kiểu `object?`, cần `ToString()`/ép kiểu để dùng — như `KhiGoChu` ở ví dụ trên).
- `@onkeydown`/`@onkeyup` → tham số kiểu `KeyboardEventArgs` (có `Key`, `CtrlKey`... để biết đúng phím nào được nhấn).
- `@onsubmit` → tham số kiểu `EventArgs` (không mang thêm dữ liệu đặc thù nào).

Nếu bạn không cần thông tin chi tiết của event (chỉ cần biết "có sự kiện xảy ra"), có thể viết handler **không tham số** — như `TangSoLan()` và `KhiSubmit()` ở các ví dụ trên — Blazor không bắt buộc bạn phải khai báo tham số nếu không dùng tới nó.

!!! danger "Viết sai — thêm dấu ngoặc `()` khi gắn handler"
    Nếu bạn viết `@onclick="TangSoLan()"` (có dấu ngoặc), Blazor hiểu đây là **gọi ngay `TangSoLan()` một lần lúc render**, rồi gán **kết quả trả về** của nó (ở đây là `void`, nên lỗi build) làm handler — không phải "gắn method này làm handler chờ click". Với method trả về `void`, build báo lỗi kiểu **"cannot convert void to EventCallback"**. Nếu method trả về một giá trị hợp lệ về kiểu nhưng bạn vẫn thêm `()`, code vẫn build được nhưng hành vi runtime sai hoàn toàn: method chạy đúng **một lần khi component render**, click sau đó **không làm gì cả** — vì lúc này `@onclick` đang giữ *giá trị trả về* của lần gọi đầu, không phải một tham chiếu tới method để gọi lại. Chỉ viết tên method (`@onclick="TangSoLan"`), không kèm ngoặc, trừ khi bạn cố ý dùng lambda như `@onclick="() => TangSoLan()"` để truyền thêm tham số.

Handler cũng có thể là method `async Task` — khi đó Blazor tự `await` nó trước khi coi event đã xử lý xong, và vẫn tự vẽ lại UI sau khi `Task` hoàn tất:

```razor title="ClickBatDongBo.razor"
<p>Trạng thái: @trangThai</p>
<button @onclick="TaiDuLieu">Tải dữ liệu</button>

@code {
    private string trangThai = "Chưa tải";

    private async Task TaiDuLieu()
    {
        trangThai = "Đang tải...";
        // Blazor re-render NGAY tại đây vì đây là điểm await đầu tiên -
        // người dùng thấy "Đang tải..." trước khi Task.Delay hoàn tất.
        await Task.Delay(1000); // giả lập gọi API mất 1 giây

        trangThai = "Đã tải xong";
        // Blazor re-render LẦN NỮA sau khi method async kết thúc hoàn toàn.
    }
}
```

Điểm cần chú ý: Blazor coi mỗi lần "quay lại" sau một `await` (và lúc method async kết thúc) là một cơ hội để render lại nếu state đổi — nên `trangThai = "Đang tải..."` **thật sự hiện lên màn hình** trước khi `Task.Delay` chạy xong, không bị "gộp" lại thành chỉ một lần cập nhật cuối cùng.

### Gắn handler bằng lambda khi cần truyền thêm tham số

Đôi khi bạn cần biết **thêm thông tin** ngoài việc "có click hay không" — ví dụ một danh sách các nút, mỗi nút cần biết nó tương ứng với `Id` nào khi bị click. Vì `@onclick="TenMethod"` chỉ gắn được method không có cách truyền thêm tham số tại chỗ, dùng cú pháp lambda:

```razor title="DanhSachNutXoa.razor"
<ul>
    @foreach (var id in danhSachId)
    {
        <li>
            Mục số @id
            <button @onclick="() => Xoa(id)">Xoá</button>
        </li>
    }
</ul>

@code {
    private List<int> danhSachId = new() { 1, 2, 3 };

    private void Xoa(int id)
    {
        danhSachId.Remove(id);
    }
}
```

`@onclick="() => Xoa(id)"` tạo một lambda **không tham số** (khớp đúng kiểu `EventCallback` mà `@onclick` cần), và bên trong lambda đó gọi `Xoa(id)` với đúng `id` của dòng tương ứng trong `@foreach`. Đây chính là trường hợp "cố ý dùng lambda để truyền thêm tham số" đã nhắc ở khối cảnh báo mục 1 — khác hẳn với việc vô tình viết `@onclick="Xoa(id)"` (không có `() =>`), vốn sẽ gọi `Xoa(id)` ngay lúc render mỗi `<li>`, không chờ click nào cả.

---

## 2. `@bind` — ràng buộc hai chiều, định nghĩa và ví dụ tối thiểu

**Định nghĩa (một câu):** `@bind` là directive tạo **ràng buộc hai chiều (two-way binding)** giữa một biến C# và giá trị của một phần tử HTML — biến C# đổi thì HTML hiển thị giá trị mới, **và** người dùng đổi giá trị trên HTML thì biến C# cũng tự cập nhật, không cần bạn viết handler thủ công.

Ví dụ tối thiểu, độc lập — sửa lại đúng vấn đề mục 0 nêu ra:

```razor title="BindCoBan.razor"
<input @bind="ten" />
<p>Xin chào, @ten!</p>

@code {
    private string ten = "";
}
```

So với mục 0, chỉ đổi `value="@ten"` thành `@bind="ten"` — không thêm handler nào bằng tay. Bên dưới, `@bind="ten"` được Blazor biên dịch thành **hai thứ gộp lại**: một `value="@ten"` (hiển thị) cộng một `@onchange` tự sinh (gán giá trị input mới ngược lại vào `ten`). Đây chính là "hai chiều": bạn chỉ viết một directive, Blazor tự lo cả chiều đọc và chiều ghi.

!!! warning "`@bind` không phải phép màu — nó chỉ là viết gọn của value + onchange"
    Hiểu sai phổ biến: nghĩ `@bind` là một cơ chế đặc biệt khác hẳn `@onclick`/`@onchange` ở mục 1. Thực ra `@bind="ten"` **tương đương gần đúng** với việc bạn tự viết `value="@ten" @onchange="e => ten = e.Value?.ToString() ?? \"\""` bằng tay — `@bind` chỉ là cú pháp gọn hơn cho đúng cặp thao tác đó. Mục 3 sẽ chỉ rõ: vì bản chất `@bind` dùng `@onchange` (không phải `@oninput`) làm mặc định, nó **không** cập nhật ngay lúc gõ.

`@bind` không chỉ dùng cho `<input type="text">` — nó hoạt động với mọi phần tử form HTML, Blazor tự chọn đúng attribute và event phù hợp với từng loại phần tử:

```razor title="BindNhieuLoaiInput.razor"
<label>
    <input type="checkbox" @bind="dongY" />
    Tôi đồng ý điều khoản
</label>
<p>Đã đồng ý: @dongY</p>

<select @bind="mauYeuThich">
    <option value="Do">Đỏ</option>
    <option value="Xanh">Xanh</option>
    <option value="Vang">Vàng</option>
</select>
<p>Màu đã chọn: @mauYeuThich</p>

<input type="number" @bind="tuoi" />
<p>Tuổi (kiểu int): @tuoi</p>

@code {
    private bool dongY = false;
    private string mauYeuThich = "Do";
    private int tuoi = 0;
}
```

Với `<input type="checkbox">`, `@bind` tự dùng attribute `checked` (không phải `value`) và event `onchange`. Với `<select>`, nó dùng `value` của `<option>` được chọn. Với `<input type="number">`, Blazor **tự chuyển đổi kiểu** — chuỗi người dùng gõ được parse sang `int` (biến `tuoi` ở đây là `int`, không phải `string`) — đây là một tiện ích của `@bind`: bạn không phải tự gọi `int.Parse`/`int.TryParse` bằng tay như khi dùng `@onchange` thủ công với `ChangeEventArgs`.

Với nhóm radio button, `@bind` áp dụng trên **từng** `<input type="radio">` bằng cách so sánh `value` của nó với biến — mọi radio cùng `name` và cùng `@bind` vào **một** biến sẽ tự loại trừ nhau đúng theo hành vi radio button chuẩn của HTML:

```razor title="BindRadio.razor"
<label><input type="radio" name="goiCuoc" value="Free" @bind="goiDaChon" /> Free</label>
<label><input type="radio" name="goiCuoc" value="Pro" @bind="goiDaChon" /> Pro</label>
<p>Gói đã chọn: @goiDaChon</p>

@code {
    private string goiDaChon = "Free";
}
```

Ba ví dụ checkbox/select/radio ở trên đều dùng cùng một directive `@bind` — điểm cốt lõi cần nhớ là **cách viết luôn giống nhau** (`@bind="tenBien"`), Blazor tự nhận diện loại phần tử HTML để chọn đúng attribute/event bên dưới; bạn không cần nhớ riêng cú pháp cho mỗi loại input.

!!! warning "`@bind` với kiểu số — gõ chữ không hợp lệ thì sao?"
    Nếu người dùng gõ một giá trị không parse được sang kiểu của biến (ví dụ gõ chữ "abc" vào `<input type="number"> @bind="tuoi"` với `tuoi` là `int`), Blazor **không** ném exception — nó giữ nguyên giá trị cũ của biến (hoặc set về giá trị mặc định của kiểu, tuỳ phiên bản/loại input), và có thể thêm class CSS `invalid` vào input để bạn tự style báo lỗi. Đây khác hẳn việc tự viết `int.Parse` thủ công trong `@onchange` — `int.Parse("abc")` sẽ ném `FormatException` ngay, crash ứng dụng nếu không có `try/catch`. `@bind` với kiểu số tự xử lý an toàn hơn, nhưng đổi lại bạn ít kiểm soát được thông báo lỗi tuỳ biến — muốn thông báo lỗi rõ ràng hơn, thường kết hợp với `EditForm`/`DataAnnotationsValidator` (học ở chương form nâng cao, ngoài phạm vi bài này).

---

## 3. `@bind` mặc định cập nhật LÚC MẤT FOCUS — ví dụ cụ thể lỗi hành vi runtime

Đây là điểm dễ nhầm nhất khi mới dùng `@bind`: nó **không** cập nhật biến C# ngay lúc bạn gõ từng ký tự, mà chỉ cập nhật khi input **mất focus** (`onchange`), tức là khi bạn click ra chỗ khác, tab qua field khác, hoặc nhấn Enter.

Ví dụ cụ thể chứng minh hành vi này — hiển thị "trực tiếp" số ký tự đã gõ trong lúc gõ:

```razor title="BindMatFocus.razor"
<input @bind="tenGo" placeholder="Gõ 'An' rồi ĐỪNG click ra ngoài..." />
<p>Số ký tự biến C# đang thấy: @tenGo.Length</p>

@code {
    private string tenGo = "";
}
```

Hành vi runtime cụ thể khi chạy: bạn gõ "An" (2 ký tự) vào input — con số hiển thị ở `<p>` **vẫn là 0**, không đổi, dù trên màn hình input đã hiện rõ chữ "An". Chỉ khi bạn **click ra ngoài input** (hoặc Tab, hoặc Enter) — tức input mất focus — sự kiện `onchange` mới bắn, `tenGo` mới thật sự được gán "An", và `<p>` mới nhảy lên hiển thị `2`. Nếu bạn kỳ vọng con số đổi ngay lúc gõ (như validate độ dài real-time, hay search-as-you-type), `@bind` mặc định **sẽ cho kết quả sai/trễ** — không phải lỗi code, mà là đúng theo cơ chế mặc định của `@bind`, chỉ là không đúng ý bạn cần.

!!! danger "Lỗi runtime cụ thể nếu tưởng `@bind` cập nhật ngay lúc gõ"
    Nếu bạn dùng `@bind` mặc định cho một ô tìm kiếm "gõ tới đâu lọc kết quả tới đâu" (search-as-you-type), kết quả lọc sẽ **trễ một bước** — chỉ lọc lại sau khi người dùng rời khỏi ô input, hoàn toàn không giống hành vi tìm kiếm real-time mong đợi. Đây không phải exception hay lỗi build — code chạy "được", nhưng hành vi UI sai lệch so với yêu cầu, và rất dễ bị hiểu nhầm là "bug lạ" nếu không biết cơ chế mặc định này.

Một biến thể của lỗi này gây nhầm lẫn hơn nữa: nếu component có **hai** input cùng `@bind` vào hai biến khác nhau, và bạn kiểm tra điều kiện dựa trên **cả hai** biến đó ngay trong markup, kết quả kiểm tra chỉ đúng sau khi **cả hai** input đã lần lượt mất focus — không phải ngay khi gõ xong input thứ hai (nếu input thứ nhất vẫn chưa từng mất focus):

```razor title="HaiInputMatFocus.razor"
<input @bind="matKhau" placeholder="Mật khẩu" />
<input @bind="xacNhanMatKhau" placeholder="Xác nhận mật khẩu" />

@if (matKhau != xacNhanMatKhau)
{
    <p style="color:red">Hai mật khẩu không khớp</p>
}

@code {
    private string matKhau = "";
    private string xacNhanMatKhau = "";
}
```

Nếu người dùng gõ mật khẩu ở ô 1, Tab qua ô 2 (ô 1 mất focus — `matKhau` cập nhật), gõ xác nhận ở ô 2 nhưng **chưa** click ra ngoài hay Tab tiếp — `xacNhanMatKhau` **chưa** cập nhật, nên điều kiện `matKhau != xacNhanMatKhau` đang so sánh giá trị cũ (rỗng) của `xacNhanMatKhau`, hiển thị cảnh báo "không khớp" một cách gây hiểu nhầm ngay cả khi người dùng đang gõ đúng. Mục 4 giải quyết đúng trường hợp này bằng `@bind:event="oninput"`.

---

## 4. `@bind:event="oninput"` — cập nhật NGAY khi gõ, so sánh trực tiếp

**Định nghĩa (một câu):** `@bind:event="oninput"` là cách chỉ định rõ **sự kiện DOM nào** kích hoạt việc cập nhật ngược của `@bind` — thay vì dùng `onchange` (mặc định, chờ mất focus), bạn ép nó dùng `oninput` (bắn ngay mỗi ký tự).

Sửa lại đúng ví dụ mục 3, chỉ thêm `@bind:event="oninput"`:

```razor title="BindOnInput.razor"
<input @bind="tenGo" @bind:event="oninput" placeholder="Gõ 'An'..." />
<p>Số ký tự biến C# đang thấy: @tenGo.Length</p>

@code {
    private string tenGo = "";
}
```

So sánh trực tiếp với mục 3 — cùng một biến `tenGo`, cùng một `<p>` hiển thị độ dài, chỉ khác đúng một directive `@bind:event="oninput"`: bây giờ khi bạn gõ "An", con số ở `<p>` nhảy lên `1` ngay sau ký tự "A", rồi `2` ngay sau ký tự "n" — **không cần** click ra ngoài hay mất focus. `@bind:event` không tạo binding mới; nó chỉ đổi sự kiện DOM nào kích hoạt chiều "HTML → C#" của `@bind` đã học ở mục 2.

| | `@bind="tenGo"` (mặc định) | `@bind="tenGo" @bind:event="oninput"` |
|---|---|---|
| Sự kiện DOM kích hoạt cập nhật ngược | `onchange` | `oninput` |
| Thời điểm biến C# thật sự đổi | Sau khi mất focus / Enter | Ngay mỗi ký tự gõ/xoá/paste |
| Phù hợp cho | Form nhập rồi submit, không cần phản hồi tức thời | Search-as-you-type, đếm ký tự trực tiếp, validate ngay lúc gõ |
| Chi phí | Ít lần re-render hơn (chỉ khi mất focus) | Nhiều lần re-render hơn (mỗi ký tự) — cần cân nhắc nếu logic sau binding nặng |

!!! warning "Không phải lúc nào cũng nên dùng `oninput`"
    `oninput` re-render component ở **mỗi ký tự**, nên nếu phần còn lại của component có logic nặng (ví dụ gọi API mỗi lần đổi, tính toán phức tạp), dùng `oninput` tràn lan có thể gây giật lag hoặc gọi API quá nhiều lần. Với các trường hợp đó, `onchange` mặc định (mục 3) thường đủ; nếu thật sự cần phản hồi gần-tức-thời nhưng tránh gọi quá nhiều lần, kỹ thuật "debounce" (trì hoãn gọi vài trăm ms sau ký tự cuối) là hướng nâng cao — xem phần DEEP DIVE cuối bài.

Ngoài `@bind:event`, còn có `@bind:after` — chạy một method **sau khi** giá trị đã được gán vào biến (bất kể sự kiện kích hoạt là `onchange` hay `oninput`), hữu ích khi bạn muốn làm gì đó ngay sau khi binding cập nhật, mà không cần tự viết `@onchange`/`@oninput` song song với `@bind`:

```razor title="BindAfter.razor"
<input @bind="tuKhoa" @bind:event="oninput" @bind:after="KhiTuKhoaDoi" placeholder="Tìm kiếm..." />
<p>Đang tìm: "@tuKhoa" (đã gọi lọc @soLanLoc lần)</p>

@code {
    private string tuKhoa = "";
    private int soLanLoc = 0;

    // Được gọi SAU khi tuKhoa đã được gán giá trị mới -
    // không cần viết tay một @oninput song song để "biết khi nào binding xong".
    private void KhiTuKhoaDoi()
    {
        soLanLoc++;
        // Ở đây thường gọi hàm lọc danh sách thật, ví dụ LocDanhSach(tuKhoa).
    }
}
```

Khác biệt với việc tự thêm `@oninput` riêng: nếu bạn viết cả `@bind="tuKhoa"` và `@oninput="KhiTuKhoaDoi"` trên cùng một input, hai directive này **xung đột** — Blazor không cho phép gắn cả `@bind` và event thủ công cùng loại event mà `@bind` đang dùng, sẽ gây lỗi build. `@bind:after` được thiết kế riêng để "nối thêm hành động" sau `@bind` mà không xung đột.

---

## 5. `StateHasChanged()` — định nghĩa và khi nào cần gọi thủ công

Mục 1–4 đều cho thấy một điểm chung: UI tự cập nhật mà bạn không phải viết thêm gì để "báo" cho Blazor. Điều này dễ khiến người mới nghĩ Blazor **luôn luôn** tự phát hiện mọi thay đổi biến — nhưng thực ra Blazor chỉ tự động vẽ lại UI ở **những thời điểm nó biết chắc có thể đã có thay đổi** (ngay sau một event nó tự điều phối, hoặc sau các lifecycle method như `OnInitializedAsync`/`OnParametersSetAsync`). Ngoài các thời điểm đó, nếu state đổi, Blazor **không hề biết** — đây là lúc `StateHasChanged()` thủ công cần xuất hiện.

**Định nghĩa (một câu):** `StateHasChanged()` là method có sẵn trên `ComponentBase` mà khi gọi, nó **báo cho Blazor biết state của component này đã đổi, hãy vẽ lại (re-render) UI** — cần gọi thủ công đúng khi state đổi **từ một luồng nằm ngoài** vòng xử lý event/lifecycle bình thường mà Blazor đang tự theo dõi.

Ở các ví dụ mục 1–4, bạn **không** cần gọi `StateHasChanged()` — vì `TangSoLan()` (mục 1) và cập nhật của `@bind` (mục 2–4) đều chạy **trong** một event handler do Blazor tự điều phối (`@onclick`, `@onchange`, `@oninput`): sau khi handler đó chạy xong, Blazor **tự động** gọi `StateHasChanged()` cho bạn. Vấn đề chỉ xuất hiện khi state đổi từ nơi Blazor **không** biết để tự gọi — ví dụ callback của một `System.Threading.Timer`:

```razor title="DemThoiGianTimer.razor"
@implements IDisposable

<p>Số giây đã trôi qua: @soGiay</p>

@code {
    private int soGiay = 0;
    private Timer? _timer;

    protected override void OnInitialized()
    {
        // Timer chạy trên MỘT LUỒNG RIÊNG, hoàn toàn ngoài vòng xử lý
        // event bình thường của Blazor (không phải @onclick/@onchange...).
        _timer = new Timer(_ =>
        {
            soGiay++;
            // KHÔNG có dòng này -> UI sẽ KHÔNG bao giờ tự cập nhật,
            // dù soGiay trong bộ nhớ vẫn tăng đúng mỗi giây.
            InvokeAsync(StateHasChanged);
        }, null, dueTime: 1000, period: 1000);
    }

    public void Dispose()
    {
        _timer?.Dispose();
    }
}
```

Nếu bạn **bỏ** dòng `InvokeAsync(StateHasChanged)`: chương trình vẫn chạy, không có exception nào, và `soGiay` vẫn tăng đúng mỗi giây trong bộ nhớ (bạn có thể kiểm tra bằng cách log ra console trong callback) — nhưng `<p>Số giây đã trôi qua: @soGiay</p>` trên màn hình **đứng yên mãi ở 0**, vì Blazor không biết callback của `Timer` vừa đổi state, nên không tự vẽ lại. Đây là hành vi runtime sai cụ thể mục yêu cầu: UI "trông như đóng băng" trong khi dữ liệu bên dưới vẫn thay đổi bình thường.

Chú ý dùng `InvokeAsync(StateHasChanged)` (không gọi trực tiếp `StateHasChanged()`) vì callback của `Timer` chạy trên một luồng thread pool khác với luồng Blazor đang render — `InvokeAsync` đảm bảo `StateHasChanged()` được thực thi đúng trên luồng UI của Blazor (tương tự khái niệm "chạy trên UI thread" ở các framework UI khác), tránh lỗi truy cập chéo luồng không an toàn.

!!! danger "Quên `IDisposable`/`Dispose()` — memory leak cụ thể"
    Component này implement `IDisposable` và huỷ `_timer` trong `Dispose()`. Nếu bạn **bỏ** `@implements IDisposable` và không override `Dispose()`, khi người dùng điều hướng rời khỏi trang chứa component này, Blazor loại bỏ component khỏi cây UI — nhưng `Timer` bên dưới **vẫn tiếp tục chạy** (nó không tự biết component "cha" của nó đã biến mất), tiếp tục gọi callback mỗi giây, tiếp tục giữ tham chiếu tới component cũ trong bộ nhớ. Đây chính là memory leak: object không còn hiển thị nhưng vẫn sống, và nếu người dùng vào-ra trang này nhiều lần, số lượng `Timer` "ma" chạy ngầm cứ tăng dần, tốn CPU/RAM tích lũy theo thời gian sử dụng ứng dụng.

!!! note "Không cần `StateHasChanged()` trong ví dụ mục 1–4 — vì sao"
    `@onclick`, `@onchange`, `@oninput` đều là **event Blazor tự đăng ký và tự lắng nghe** trên DOM (qua cơ chế nội bộ, không phải bạn tự gắn `addEventListener` JavaScript tay). Khi một trong các event này bắn, Blazor tự chạy handler C# tương ứng, và **ngay sau khi handler chạy xong**, tự gọi `StateHasChanged()` cho toàn bộ subtree liên quan — đây là hành vi mặc định của `ComponentBase`. `StateHasChanged()` thủ công chỉ cần khi state đổi từ một nguồn Blazor **không** biết để tự làm việc đó: `Timer`, một `Task` chạy nền không phải do await trực tiếp trong lifecycle method, một event từ service khác (ví dụ `AuthenticationStateProvider` thông báo đổi trạng thái đăng nhập ở nơi khác trong app), hoặc callback từ JS Interop không đi qua đường event bình thường.

Một trường hợp thứ hai thường gặp cần `StateHasChanged()` thủ công: một service C# thuần (không phải component) tự nổ ra một sự kiện .NET (`event`), và component subscribe vào sự kiện đó trong `OnInitialized()`:

```razor title="LangNgheServiceNgoai.razor"
@implements IDisposable
@inject ThongBaoService ThongBao

<p>Thông báo mới nhất: @noiDungMoiNhat</p>

@code {
    private string noiDungMoiNhat = "Chưa có thông báo";

    protected override void OnInitialized()
    {
        // Đăng ký lắng nghe event từ một service - service này KHÔNG PHẢI
        // component, nó không biết gì về StateHasChanged hay vòng render Blazor.
        ThongBao.CoThongBaoMoi += KhiCoThongBaoMoi;
    }

    private void KhiCoThongBaoMoi(string noiDung)
    {
        noiDungMoiNhat = noiDung;
        // Bắt buộc gọi thủ công - event C# thường KHÔNG đi qua vòng
        // xử lý @onclick/@onchange nào của Blazor, nên Blazor không tự biết.
        StateHasChanged();
    }

    public void Dispose()
    {
        // Bắt buộc huỷ đăng ký - nếu không, service (thường sống lâu hơn
        // component, ví dụ Singleton/Scoped) vẫn giữ tham chiếu tới
        // KhiCoThongBaoMoi của component ĐÃ BỊ HUỶ, gây gọi vào object chết.
        ThongBao.CoThongBaoMoi -= KhiCoThongBaoMoi;
    }
}
```

```csharp title="ThongBaoService.cs"
// test:skip minh hoa - can dang ky DI trong du an Blazor thuc te, khong doc lap duoc
public sealed class ThongBaoService
{
    public event Action<string>? CoThongBaoMoi;

    public void GuiThongBao(string noiDung) => CoThongBaoMoi?.Invoke(noiDung);
}
```

Ở đây gọi trực tiếp `StateHasChanged()` (không qua `InvokeAsync`) là hợp lệ **nếu** `GuiThongBao` được gọi từ cùng luồng UI của Blazor (ví dụ từ một handler khác trong app, không phải từ thread nền) — chỉ khi nguồn gọi đến từ thread khác (như `Timer` ở ví dụ trước) mới cần bọc qua `InvokeAsync`. Nếu không chắc event có thể bắn từ thread nào, dùng `InvokeAsync(StateHasChanged)` luôn là lựa chọn an toàn hơn.

---

## 6. Truyền event từ con lên cha qua `EventCallback<T>` — định nghĩa và ví dụ tối thiểu

Component cha truyền dữ liệu **xuống** con qua `[Parameter]` thường (một chiều: cha → con) là điều đã học ở chương component cơ bản. Nhưng chiều ngược lại — con muốn báo tin **lên** cha (ví dụ "người dùng vừa click nút trong tôi", "người dùng vừa chọn giá trị này trong tôi") — cần một cơ chế khác, vì con không thể "tự ý" sửa biến của cha (cha và con là hai class hoàn toàn tách biệt, con không có tham chiếu trực tiếp tới biến nội bộ của cha).

**Định nghĩa (một câu):** `EventCallback<T>` là một kiểu parameter đặc biệt cho phép component con **gọi ngược lên một method của component cha** kèm một giá trị kiểu `T`, giống một sự kiện .NET thông thường (`event`) nhưng được Blazor tự động tích hợp với vòng render — cha không cần tự gọi `StateHasChanged()` sau khi nhận callback.

Ví dụ tối thiểu, độc lập — component con là một nút bấm gửi số lên, component cha nhận và hiển thị:

```razor title="NutGuiSo.razor (con)"
<button @onclick="GuiLen">Gửi số 5 lên cha</button>

@code {
    // Parameter kiểu EventCallback<int> - cha sẽ "lắng nghe" qua đây.
    [Parameter]
    public EventCallback<int> OnGuiSo { get; set; }

    private async Task GuiLen()
    {
        // InvokeAsync gọi ngược lên method mà cha đã gắn vào OnGuiSo,
        // truyền kèm giá trị 5 (kiểu int, đúng khai báo EventCallback<int>).
        await OnGuiSo.InvokeAsync(5);
    }
}
```

```razor title="TrangCha.razor (cha)"
<NutGuiSo OnGuiSo="KhiConGuiSo" />
<p>Cha nhận được số: @soNhanDuoc</p>

@code {
    private int soNhanDuoc = 0;

    private void KhiConGuiSo(int so)
    {
        soNhanDuoc = so;
    }
}
```

Điểm mấu chốt: `NutGuiSo` (con) **không biết gì** về `TrangCha` hay biến `soNhanDuoc` — nó chỉ khai báo "tôi có một parameter tên `OnGuiSo`, kiểu `EventCallback<int>`, và tôi sẽ gọi nó kèm một số nguyên khi người dùng click". `TrangCha` (cha) gắn method `KhiConGuiSo` vào parameter đó qua `OnGuiSo="KhiConGuiSo"` — đúng cú pháp giống gắn `@onclick` ở mục 1, chỉ khác đây là parameter tự định nghĩa, không phải event DOM có sẵn. Khi click, `NutGuiSo` gọi `OnGuiSo.InvokeAsync(5)`, Blazor chuyển lời gọi đó tới `KhiConGuiSo(5)` bên `TrangCha`, cha cập nhật `soNhanDuoc`, và **Blazor tự vẽ lại `TrangCha`** — đúng như một event Blazor tự quản lý, không cần cha tự gọi `StateHasChanged()`.

!!! danger "Sai lầm phổ biến: dùng `Action<T>` thường thay vì `EventCallback<T>`"
    Nếu bạn khai báo parameter là `[Parameter] public Action<int> OnGuiSo { get; set; }` (delegate C# thường) thay vì `EventCallback<int>`, code vẫn build được và có thể chạy đúng trong trường hợp đơn giản — nhưng bạn mất đi việc Blazor **tự động** gọi `StateHasChanged()` sau khi callback chạy xong, và mất khả năng `await` đúng cách nếu handler ở cha là async (`Action` không hỗ trợ async tự nhiên — dùng `async void` ẩn dưới `Action` dễ nuốt exception âm thầm, lỗi không hiện ra ở đâu cả, rất khó debug). `EventCallback<T>`/`EventCallback` là kiểu **được thiết kế riêng cho Blazor** đúng vì lý do này — luôn dùng nó (không dùng `Action`/`Func` thường) cho parameter đóng vai trò event từ con lên cha.

Khi con không cần gửi giá trị nào lên cha — chỉ cần báo "một việc đã xảy ra" — dùng `EventCallback` (không có `<T>`), gọi `InvokeAsync()` không tham số:

```razor title="NutDong.razor (con)"
<button @onclick="Dong">Đóng</button>

@code {
    [Parameter]
    public EventCallback OnDong { get; set; }

    private async Task Dong()
    {
        await OnDong.InvokeAsync();
    }
}
```

```razor title="TrangChaThuHai.razor (cha)"
@if (hienThi)
{
    <div class="hop-thoai">
        <p>Đây là hộp thoại</p>
        <NutDong OnDong="AnHopThoai" />
    </div>
}

@code {
    private bool hienThi = true;

    private void AnHopThoai()
    {
        hienThi = false;
    }
}
```

So sánh hai ví dụ trong mục này — khi nào dùng `EventCallback<T>`, khi nào dùng `EventCallback`:

| | `EventCallback<T>` (ví dụ `NutGuiSo`) | `EventCallback` không generic (ví dụ `NutDong`) |
|---|---|---|
| Con gửi kèm dữ liệu gì lên cha? | Có — một giá trị kiểu `T` (ví dụ `int`, `string`, một DTO) | Không — chỉ báo "sự kiện đã xảy ra" |
| Cách gọi bên con | `await OnX.InvokeAsync(giaTri)` | `await OnX.InvokeAsync()` |
| Chữ ký method handler bên cha | Nhận đúng một tham số kiểu `T` | Không tham số (hoặc `object?` nếu cần, hiếm dùng) |
| Ví dụ thực tế | Component chọn ngày gửi lên ngày đã chọn; ô input tuỳ biến gửi lên giá trị mới | Nút đóng modal; nút "làm mới" không cần truyền gì |

!!! warning "Đặt tên parameter `EventCallback` theo quy ước `On...` — không bắt buộc nhưng nên theo"
    Không có quy tắc CI nào bắt buộc tên parameter `EventCallback` phải bắt đầu bằng `On` (như `OnGuiSo`, `OnDong`) — đây là **quy ước cộng đồng** giúp code dễ đọc, phân biệt rõ đâu là parameter dữ liệu thường (`Ten`, `Gia`...) và đâu là parameter đóng vai trò sự kiện. Nếu bạn đặt tên khác (ví dụ `GuiSo` không có tiền tố `On`), code vẫn build và chạy đúng — chỉ là kém rõ ràng hơn khi đồng nghiệp đọc lại component sau này.

---

## Cạm bẫy & thực chiến

- **Gắn `@onclick="TenMethod()"` (có dấu ngoặc) khi method trả về `void`:** lỗi build "cannot convert void to EventCallback"; nếu method trả về giá trị khác `void`, code build được nhưng method chỉ chạy đúng một lần lúc render, click sau đó vô tác dụng (mục 1).
- **Dùng `value="@bien"` viết tay và tưởng đó là binding hai chiều:** đây chỉ là hiển thị một chiều (C# → HTML) — gõ vào input không bao giờ đổi lại biến C#. Phải dùng `@bind="bien"` mới có cả hai chiều (mục 0, mục 2).
- **Kỳ vọng `@bind` cập nhật ngay lúc gõ nhưng không thêm `@bind:event="oninput"`:** với `@bind` mặc định, biến C# chỉ đổi khi input mất focus (`onchange`) — mọi logic phụ thuộc giá trị "tức thời" trong lúc gõ (đếm ký tự, search-as-you-type) sẽ trễ một bước nếu quên chỉ định `oninput` (mục 3, mục 4).
- **Dùng `oninput` tràn lan cho mọi input dù không cần phản hồi tức thời:** gây re-render ở mỗi ký tự, tốn hiệu năng không cần thiết nếu phần còn lại của component có logic nặng (gọi API, tính toán phức tạp) — chỉ dùng `oninput` khi thật sự cần phản hồi ngay lúc gõ (mục 4).
- **Đổi state trong callback không do Blazor điều phối (`Timer`, thread nền, event từ service ngoài) mà quên gọi `StateHasChanged()`:** dữ liệu trong bộ nhớ vẫn đúng, nhưng UI đứng yên, "trông như đóng băng" — không có exception nào báo lỗi, rất dễ bị bỏ sót khi debug (mục 5).
- **Gọi `StateHasChanged()` trực tiếp (không qua `InvokeAsync`) từ một luồng khác luồng UI của Blazor:** có thể gây lỗi truy cập chéo luồng không an toàn hoặc hành vi không nhất quán — dùng `InvokeAsync(StateHasChanged)` khi state đổi từ callback không đồng bộ với luồng render (mục 5).
- **Quên implement `IDisposable`/`Dispose()` khi component tạo `Timer`, subscribe event, hoặc mở kết nối bên ngoài:** resource đó tiếp tục sống và chạy ngầm sau khi component đã bị Blazor loại bỏ khỏi UI — memory leak tích lũy theo số lần người dùng vào-ra trang (mục 5).
- **Dùng `Action<T>`/`Func<T>` thường thay vì `EventCallback<T>` cho parameter đóng vai trò event từ con lên cha:** mất tự động `StateHasChanged()` sau callback, và dễ nuốt exception âm thầm nếu handler ở cha là async (mục 6).
- **Viết cả `@bind="bien"` và `@onchange="..."` (hoặc `@oninput="..."`) thủ công trên cùng một phần tử, cùng loại event mà `@bind` đang dùng:** Blazor không cho phép gắn trùng — gây lỗi build (thường là "Duplicate attribute" hoặc lỗi tương tự). Muốn thêm hành động sau khi `@bind` cập nhật, dùng `@bind:after` (mục 4), không tự thêm event thủ công song song.
- **Gõ giá trị không parse được vào input `@bind` kiểu số (ví dụ chữ vào `<input type="number">`) và không kiểm tra `class="invalid"`/thông báo lỗi:** `@bind` không ném exception khi parse thất bại, nhưng cũng không tự hiện thông báo lỗi rõ ràng cho người dùng nếu bạn không style/xử lý thêm — dễ để người dùng "gõ mà không biết vì sao giá trị không đổi" (mục 2).
- **Kiểm tra điều kiện dựa trên hai (hoặc nhiều) biến `@bind` mặc định ngay trong markup, mà không đồng bộ thời điểm cập nhật của cả hai input:** kết quả kiểm tra có thể dựa trên giá trị "nửa cũ nửa mới" nếu các input mất focus ở thời điểm khác nhau — cần `@bind:event="oninput"` nếu logic yêu cầu so sánh tức thời giữa nhiều input (mục 3).
- **Subscribe một event C# thường (`+=`) của một service trong `OnInitialized()` nhưng quên huỷ đăng ký (`-=`) trong `Dispose()`:** service (thường sống lâu hơn component, đăng ký Singleton/Scoped trong DI) vẫn giữ tham chiếu tới handler của component đã bị Blazor huỷ — không chỉ là memory leak, mà còn có thể gây gọi vào một component "đã chết", ném exception khó chẩn đoán nếu component đó đã dispose các resource khác (mục 5).
- **Viết `@onclick="Xoa(id)"` (thiếu `() =>`) trong một `@foreach` khi muốn truyền tham số theo từng dòng:** Blazor gọi `Xoa(id)` ngay lúc render mỗi dòng (giống lỗi dấu ngoặc ở mục 1), không chờ click nào — danh sách có thể tự "xoá hết" ngay khi vừa hiển thị, hoặc lỗi build nếu `Xoa` không trả về kiểu tương thích `EventCallback`. Phải dùng `@onclick="() => Xoa(id)"` để tạo đúng một lambda chờ click.

---

## Bài tập

**Bài 1 (giàn giáo):** Viết một component `BoDemTangGiam.razor` có hai nút — "Tăng" và "Giảm" — và một đoạn hiển thị số hiện tại (bắt đầu từ 0). Nút "Giảm" không được cho số xuống dưới 0.

??? success "Lời giải + vì sao"
    ```razor title="BoDemTangGiam.razor"
    <p>Giá trị hiện tại: @gia</p>
    <button @onclick="Tang">Tăng</button>
    <button @onclick="Giam">Giảm</button>

    @code {
        private int gia = 0;

        private void Tang()
        {
            gia++;
        }

        private void Giam()
        {
            if (gia > 0)
            {
                gia--;
            }
        }
    }
    ```

    **Vì sao đúng:** cả hai nút dùng `@onclick` gắn đúng method (không dấu ngoặc, đúng mục 1). `Giam()` kiểm tra điều kiện `gia > 0` trước khi trừ — vì cả hai method chạy trong event handler do Blazor tự điều phối, không cần gọi `StateHasChanged()` thủ công; UI tự vẽ lại đúng ngay sau mỗi click.

**Bài 2 (thiết kế — so sánh `@bind` mặc định vs `oninput`):** Bạn có một form nhập "Tên đăng nhập" cần validate độ dài tối thiểu 3 ký tự, và muốn hiển thị cảnh báo **ngay khi gõ** (không chờ mất focus). Viết component, và giải thích vì sao chọn `@bind:event` nào.

??? success "Lời giải + vì sao"
    ```razor title="ValidateTenDangNhap.razor"
    <input @bind="tenDangNhap" @bind:event="oninput" placeholder="Tên đăng nhập..." />
    @if (tenDangNhap.Length > 0 && tenDangNhap.Length < 3)
    {
        <p style="color:red">Tên đăng nhập phải có ít nhất 3 ký tự</p>
    }

    @code {
        private string tenDangNhap = "";
    }
    ```

    **Vì sao đúng:** yêu cầu là cảnh báo hiện **ngay khi gõ**, không chờ mất focus — đúng trường hợp mục 4 mô tả (search-as-you-type/validate tức thời). Nếu dùng `@bind` mặc định (không thêm `@bind:event="oninput"`), cảnh báo chỉ xuất hiện sau khi người dùng click ra ngoài input — sai với yêu cầu "ngay khi gõ" (đúng lỗi hành vi mục 3 đã minh hoạ).

**Bài 3 (tổng hợp — component con báo tin lên cha):** Viết một component con `TheSanPham.razor` hiển thị tên một sản phẩm và một nút "Thêm vào giỏ". Khi click nút, component con phải báo lên component cha **tên sản phẩm** đã được thêm (kiểu `string`), và component cha hiển thị danh sách các tên sản phẩm đã được thêm (dùng một `List<string>`).

??? success "Lời giải + vì sao"
    ```razor title="TheSanPham.razor (con)"
    <div class="the-san-pham">
        <p>@ten</p>
        <button @onclick="ThemVaoGio">Thêm vào giỏ</button>
    </div>

    @code {
        [Parameter]
        public string Ten { get; set; } = "";

        [Parameter]
        public EventCallback<string> OnThem { get; set; }

        private string ten => Ten; // chỉ để markup ngắn hơn, không bắt buộc

        private async Task ThemVaoGio()
        {
            await OnThem.InvokeAsync(Ten);
        }
    }
    ```

    ```razor title="TrangGioHang.razor (cha)"
    <TheSanPham Ten="Ban phim" OnThem="KhiThemSanPham" />
    <TheSanPham Ten="Chuot" OnThem="KhiThemSanPham" />

    <p>Giỏ hàng (@danhSachDaThem.Count món):</p>
    <ul>
        @foreach (var ten in danhSachDaThem)
        {
            <li>@ten</li>
        }
    </ul>

    @code {
        private List<string> danhSachDaThem = new();

        private void KhiThemSanPham(string ten)
        {
            danhSachDaThem.Add(ten);
        }
    }
    ```

    **Vì sao đúng:** `TheSanPham` (con) nhận `Ten` qua `[Parameter]` thường (một chiều, cha truyền xuống), và báo tin ngược lên qua `EventCallback<string>` (đúng mục 6) — con hoàn toàn không biết `danhSachDaThem` tồn tại. Mỗi lần `TrangGioHang` (cha) render lại hai `<TheSanPham>` với `Ten` khác nhau, cả hai đều gọi **cùng** method `KhiThemSanPham` — nhưng mỗi lần gọi mang giá trị `Ten` khác nhau (đúng của component con nào vừa click), nên `danhSachDaThem` luôn nhận đúng tên sản phẩm tương ứng, không bị lẫn giữa hai thẻ sản phẩm.

---

## Tự kiểm tra

1. `@onclick="TenMethod"` và `@onclick="TenMethod()"` khác nhau thế nào? Viết sai dạng nào gây lỗi/hành vi sai cụ thể gì?

    ??? note "Đáp án"
        `@onclick="TenMethod"` (không ngoặc) gắn method làm handler, gọi lại mỗi lần click. `@onclick="TenMethod()"` (có ngoặc) gọi method **ngay lúc render**, gán kết quả trả về làm handler — với method `void` gây lỗi build "cannot convert void to EventCallback"; với method trả kiểu khác, build được nhưng chỉ chạy đúng một lần, click sau đó không có tác dụng.

2. `@bind="ten"` tương đương với việc tự viết hai thứ gì bằng tay?

    ??? note "Đáp án"
        Tương đương `value="@ten"` (hiển thị, chiều C# → HTML) cộng với một `@onchange` tự sinh gán giá trị input mới ngược lại vào `ten` (chiều HTML → C#). `@bind` chỉ là cú pháp gọn cho đúng cặp thao tác đó.

3. `@bind` mặc định cập nhật biến C# vào lúc nào? Nếu bạn cần cập nhật ngay lúc gõ từng ký tự, phải thêm gì?

    ??? note "Đáp án"
        Mặc định cập nhật lúc input **mất focus** (dùng sự kiện `onchange` bên dưới) — gõ chữ trong lúc input vẫn đang focus không làm biến C# đổi ngay. Muốn cập nhật ngay mỗi ký tự, thêm `@bind:event="oninput"`.

4. Vì sao các ví dụ dùng `@onclick`/`@bind` ở mục 1–4 không cần gọi `StateHasChanged()` thủ công, nhưng ví dụ `Timer` ở mục 5 lại cần?

    ??? note "Đáp án"
        `@onclick`/`@onchange`/`@oninput` là event Blazor tự đăng ký và điều phối — sau khi handler tương ứng chạy xong, Blazor tự động gọi `StateHasChanged()`. `Timer` chạy callback trên một luồng riêng, hoàn toàn ngoài vòng event Blazor tự theo dõi, nên Blazor không biết state đã đổi để tự vẽ lại — phải gọi `InvokeAsync(StateHasChanged)` thủ công.

5. Nếu quên gọi `StateHasChanged()` trong callback của `Timer`, điều gì xảy ra cụ thể — có exception không?

    ??? note "Đáp án"
        Không có exception nào. Biến state (ví dụ `soGiay`) vẫn tăng đúng trong bộ nhớ, nhưng UI hiển thị đứng yên, không cập nhật — vì Blazor không được báo là cần vẽ lại. Đây là lỗi hành vi im lặng, khó phát hiện nếu không biết cơ chế này.

6. Component có tạo `Timer`/subscribe event nhưng không implement `IDisposable` sẽ gặp vấn đề gì khi người dùng điều hướng rời trang?

    ??? note "Đáp án"
        `Timer` (hoặc subscription) vẫn tiếp tục chạy dù component đã bị Blazor loại khỏi cây UI — vì không ai gọi huỷ nó. Đây là memory leak: resource vẫn sống, tiếp tục tốn CPU/RAM, và tích lũy dần nếu người dùng vào-ra trang nhiều lần.

7. `EventCallback<T>` dùng để làm gì, và vì sao nên dùng nó thay vì `Action<T>` cho parameter kiểu "event từ con lên cha"?

    ??? note "Đáp án"
        `EventCallback<T>` cho phép component con gọi ngược lên method của component cha kèm một giá trị kiểu `T`, và được Blazor tích hợp sẵn với vòng render (tự gọi `StateHasChanged()` sau khi callback chạy). `Action<T>` là delegate thường, không có tích hợp này, và dễ gây nuốt exception âm thầm nếu handler ở cha là async.

8. Trong ví dụ `NutGuiSo`/`TrangCha` ở mục 6, `NutGuiSo` (con) có biết gì về biến `soNhanDuoc` bên `TrangCha` (cha) không?

    ??? note "Đáp án"
        Không. `NutGuiSo` chỉ biết nó có một parameter `OnGuiSo` kiểu `EventCallback<int>` và gọi `InvokeAsync(5)` khi click — nó không biết cha là ai, không biết cha làm gì với giá trị đó. Đây đúng là mục tiêu của `EventCallback<T>`: con phát ra sự kiện, hoàn toàn không phụ thuộc vào cách cha xử lý.

9. `@bind` áp dụng cho `<input type="checkbox">` dùng attribute và event nào bên dưới? Với `<input type="number">`, `@bind` giúp bạn tránh phải tự viết gì?

    ??? note "Đáp án"
        Với checkbox, `@bind` dùng attribute `checked` (không phải `value`) và event `onchange`. Với input number, `@bind` tự chuyển đổi (parse) chuỗi người dùng gõ sang kiểu số của biến (ví dụ `int`) — bạn không cần tự gọi `int.Parse`/`int.TryParse` bằng tay như khi viết `@onchange` thủ công với `ChangeEventArgs`.

10. `@bind:after` khác gì so với việc tự thêm `@onchange`/`@oninput` song song với `@bind` trên cùng một input?

    ??? note "Đáp án"
        Tự thêm `@onchange`/`@oninput` song song với `@bind` khi `@bind` đang dùng đúng loại event đó sẽ **xung đột**, gây lỗi build (gắn trùng event). `@bind:after` được thiết kế riêng để chạy một method **sau khi** giá trị đã được `@bind` gán xong, không xung đột với cơ chế bên trong của `@bind`.

11. Khi nào dùng `EventCallback` (không có `<T>`) thay vì `EventCallback<T>` cho parameter của component con?

    ??? note "Đáp án"
        Dùng `EventCallback` không generic khi component con chỉ cần báo "một sự kiện đã xảy ra" mà không cần gửi kèm dữ liệu gì lên cha (ví dụ nút Đóng, nút Làm mới). `EventCallback<T>` dùng khi con cần gửi kèm một giá trị cụ thể kiểu `T` lên cha (ví dụ giá trị đã chọn, tên sản phẩm được thêm).

12. Nếu một component subscribe vào event của một service (`ThongBao.CoThongBaoMoi += ...`) trong `OnInitialized()` nhưng quên huỷ đăng ký trong `Dispose()`, hậu quả cụ thể là gì?

    ??? note "Đáp án"
        Service (thường sống lâu hơn component do lifetime Singleton/Scoped trong DI) vẫn giữ tham chiếu tới handler của component đã bị Blazor huỷ khỏi UI. Đây là memory leak, và nếu service sau đó bắn event, nó sẽ gọi vào một handler của component "đã chết" — có thể ném exception khó chẩn đoán nếu component đó đã dispose các resource nội bộ khác.

---

??? abstract "DEEP DIVE — nâng cao (ngoài fast path)"
    - **Debounce cho `oninput`:** khi cần phản hồi gần-tức-thời (search-as-you-type) nhưng muốn tránh gọi API/tính toán nặng ở **mỗi** ký tự, kỹ thuật debounce trì hoãn xử lý một khoảng thời gian ngắn (ví dụ 300ms) sau ký tự cuối cùng — nếu người dùng gõ tiếp trong khoảng đó, bộ đếm thời gian reset lại. Blazor không có debounce sẵn trong `@bind`; thường tự viết bằng một `Timer`/`CancellationTokenSource` huỷ-và-tạo-lại trong handler `oninput`, hoặc dùng thư viện cộng đồng chuyên cho việc này.
    - **`@bind-value`/`@bind-value:event` cho component tuỳ biến:** `@bind` không chỉ áp dụng cho `<input>` HTML thuần — bạn có thể tự thiết kế một component con hỗ trợ binding hai chiều bằng cách khai báo đúng cặp parameter `Value` (kiểu `T`) và `ValueChanged` (kiểu `EventCallback<T>`), rồi component cha dùng `@bind-Value="bien"` trên component đó. Đây là cách các component thư viện UI (MudBlazor, Radzen...) cho phép `@bind-Value` hoạt động trên component tuỳ biến của họ giống hệt `<input>` gốc.
    - **`ShouldRender()` để kiểm soát re-render tinh hơn:** với component có `StateHasChanged()` được gọi rất thường xuyên (ví dụ nhận rất nhiều sự kiện `oninput`/`Timer` liên tục), override `ShouldRender()` (trả `bool`) cho phép chặn một số lần vẽ lại không cần thiết (ví dụ nếu giá trị mới giống giá trị cũ) — một kỹ thuật tối ưu hiệu năng dùng khi đã đo được vấn đề thật, không nên áp dụng mặc định cho mọi component.
    - **`@key` khi render danh sách component trong một `@foreach`:** nếu bạn render nhiều component con cùng loại trong một vòng lặp (ví dụ nhiều `<TheSanPham>` như bài tập 3) và danh sách nguồn có thể thêm/xoá/sắp xếp lại, thêm `@key="item.Id"` giúp Blazor giữ đúng instance component gắn với đúng dữ liệu khi danh sách thay đổi thứ tự — nếu không có `@key`, Blazor có thể "gán nhầm" state nội bộ (ví dụ giá trị một input riêng trong từng thẻ) giữa các item khi thứ tự đổi, dẫn tới UI hiển thị sai dữ liệu cho đúng vị trí nhưng sai item.
    - **So sánh với two-way binding ở các framework khác:** `@bind` của Blazor phục vụ đúng mục đích giống `v-model` (Vue) hay `[(ngModel)]` (Angular) — ràng buộc hai chiều giữa state và input. Khác biệt lớn nhất là cơ chế bên dưới: Blazor Server gửi diff UI qua SignalR (cần kết nối mạng liên tục, không chạy được khi mất mạng), còn Blazor WebAssembly chạy toàn bộ vòng lặp binding này ngay trong trình duyệt qua runtime WASM (không cần server sau khi đã tải xong, trừ khi gọi API) — cùng cú pháp `@bind` nhưng chi phí mạng/độ trễ cập nhật khác nhau đáng kể giữa hai mô hình hosting.
    - **`EventCallback` và exception — khác biệt với gọi method C# thường:** nếu handler bên trong một `EventCallback` ném exception, Blazor Server và Blazor WebAssembly xử lý hơi khác nhau ở tầng hạ tầng (Blazor Server có thể đóng kết nối SignalR nếu exception không được bắt, khiến UI "đơ" cho tới khi tự kết nối lại; Blazor WebAssembly thường hiện lỗi ra console trình duyệt và UI có thể vẫn tiếp tục hoạt động một phần) — nhưng nguyên tắc chung cho cả hai vẫn là: nên `try/catch` trong handler nếu bạn gọi thao tác có thể thất bại (như gọi API), thay vì để exception thoát ra ngoài `EventCallback` không kiểm soát.

**Tiếp theo →** [P7 · Routing & Navigation](routing-navigation.md)
