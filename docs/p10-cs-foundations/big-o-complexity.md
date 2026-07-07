---
tier: core
status: core
owner: core-team
verified_on: "2026-07-05"
dotnet_version: "10.0"
bloom: phân tích
requires: [p9-monitoring]
est_minutes_fast: 45
---

# Big-O & Độ phức tạp thuật toán

!!! info "bạn đang ở đây"
    cần trước: đây là chương đầu tiên của P10, ngay sau P9 (DevOps & Cloud) trong lộ trình — nhưng kiến thức thật sự cần dùng lại là ở P1 (`collections.md`): bạn đã **dùng** List/Dictionary/HashSet/Queue/Stack qua các method có sẵn của BCL, và đã thấy Big-O xuất hiện rải rác (ví dụ "Dictionary tra cứu O(1)", "Add của List là O(1) khấu hao"). Chương đó dùng Big-O như một **nhãn dán** cho từng thao tác, chưa giải thích Big-O **là gì** và **vì sao** tính ra được con số đó. Chương này lấp đúng lỗ hổng ấy — định nghĩa Big-O từ gốc, dạy cách tự tính, rồi mới quay lại giải thích các nhãn dán bạn đã thấy.
    mở khoá: sau chương này bạn tự tính được Big-O cho một đoạn code C# bất kỳ (không cần tra bảng), phân biệt được best/average/worst case, hiểu vì sao "đo giờ chạy thực tế" không đủ tin cậy để so sánh hai thuật toán — nền tảng bắt buộc để đọc hiểu chương kế tiếp về cấu trúc dữ liệu tự cài đặt (cây, heap, đồ thị) và các thuật toán sắp xếp/tìm kiếm nâng cao.

> Mục tiêu (đo được): sau chương này bạn **định nghĩa** được Big-O bằng lời (mô tả tốc độ tăng, không phải thời gian tuyệt đối), **tính toán** được Big-O của một đoạn code C# cho trước bằng cách đếm thao tác, **phân loại** được một đoạn code vào đúng lớp độ phức tạp (O(1) đến O(n²), nhận diện được O(2ⁿ)/O(n!)), **phân biệt** được best/average/worst case bằng ví dụ QuickSort cụ thể, và **giải thích** được vì sao đo giờ chạy thực tế (stopwatch) không đủ để so sánh hai thuật toán một cách khoa học.

---

## 0. Đoán nhanh trước khi học

Hai đồng nghiệp viết hai hàm khác nhau để kiểm tra một số `x` có nằm trong danh sách `n` số đã **sắp xếp tăng dần** hay không. Cả hai hàm đều cho kết quả đúng.

- Đồng nghiệp A chạy hàm của mình trên laptop đời cũ, đo được **120 ms** với `n = 1.000.000`.
- Đồng nghiệp B chạy hàm của mình trên máy trạm mạnh hơn, đo được **40 ms** với cùng `n = 1.000.000`.

B kết luận: "Hàm của tôi nhanh hơn hàm của A gấp 3 lần, thuật toán của tôi tốt hơn."

Kết luận này có đáng tin không?

??? note "Đáp án"
    Không đáng tin — vì hai con số **120 ms** và **40 ms** bị nhiễu bởi ít nhất ba yếu tố không liên quan đến chất lượng thuật toán: (1) tốc độ CPU khác nhau giữa hai máy, (2) tải hệ thống lúc đo (chương trình khác đang chạy nền), (3) hiệu ứng JIT warm-up của .NET (lần chạy đầu luôn chậm hơn các lần sau). Đo giờ chạy thực tế (stopwatch) cho biết "trên máy này, lúc này, thuật toán này chạy mất bao lâu" — không cho biết "thuật toán này có **về bản chất** nhanh hơn thuật toán kia không" khi `n` lớn dần.

    Ví dụ cụ thể lật ngược tình huống: nếu hàm của A dùng **binary search** (chia đôi phạm vi tìm mỗi bước, chỉ khả thi vì danh sách đã sắp xếp) còn hàm của B dùng **linear search** (dò từng phần tử) nhưng B tình cờ chạy trên máy nhanh hơn 3 lần, con số đo được có thể đánh lừa hoàn toàn: B "thắng" ở `n = 1.000.000` hiện tại, nhưng nếu `n` tăng lên 100 triệu, linear search của B sẽ chậm hơn binary search của A rất nhiều lần, bất kể máy nào nhanh hơn. Cái cần so sánh không phải "bao nhiêu milliseconds trên máy X" mà là "**tốc độ tăng** của thời gian chạy khi `n` tăng" — đó chính là thứ Big-O đo. Mục 1 định nghĩa chính xác điều này.

---

## 1. Big-O giải quyết vấn đề gì, và định nghĩa chính xác

**Định nghĩa (một câu):** Big-O là một ký hiệu toán học mô tả **tốc độ tăng** (growth rate) của thời gian chạy hoặc bộ nhớ dùng của một thuật toán khi kích thước dữ liệu đầu vào `n` tiến về **vô cùng**, hoàn toàn **không phụ thuộc** vào máy chạy, ngôn ngữ lập trình, hay thời gian tuyệt đối tính bằng giây/milliseconds.

Ví dụ tối thiểu, độc lập, chỉ minh hoạ đúng khái niệm "đo tốc độ tăng thay vì đo thời gian tuyệt đối" — đếm số lần một phép so sánh được thực hiện (không đo giờ):

```csharp title="dem-so-sanh.cs (minh hoa dem thao tac, khong do gio)"
// test:run
int DemSoSanh_TimTuyenTinh(int[] a, int target)
{
    int soLanSoSanh = 0;
    foreach (var x in a)
    {
        soLanSoSanh++;           // mỗi vòng lặp = 1 phép so sánh
        if (x == target) break;
    }
    return soLanSoSanh;
}

// Trường hợp xấu nhất: phần tử cần tìm ở CUỐI mảng (hoặc không có)
Console.WriteLine(DemSoSanh_TimTuyenTinh(new int[10], 999));        // n=10   -> 10 lần so sánh
Console.WriteLine(DemSoSanh_TimTuyenTinh(new int[100], 999));       // n=100  -> 100 lần so sánh
Console.WriteLine(DemSoSanh_TimTuyenTinh(new int[1000], 999));      // n=1000 -> 1000 lần so sánh
```

Kết quả: khi `n` tăng gấp 10 lần (10 → 100 → 1000), số lần so sánh cũng tăng **đúng gấp 10 lần**. Đây là bằng chứng bằng số cho tốc độ tăng **tuyến tính** — không cần biết máy chạy nhanh hay chậm, không cần đo bằng `Stopwatch`, chỉ cần đếm thao tác. Đây chính là cách Big-O được xác lập: đếm số thao tác cơ bản (so sánh, gán, phép tính) theo hàm của `n`, rồi mô tả **dạng** của hàm đó khi `n` lớn.

**Nếu hiểu sai:** một hiểu lầm phổ biến là nghĩ Big-O đo "bao nhiêu giây". **Sai** — Big-O là một hàm của `n` (biến số), không phải một con số thời gian cụ thể. `O(n)` không có nghĩa là "chạy trong n giây"; nó có nghĩa là "nếu `n` tăng gấp đôi, số thao tác cũng tăng khoảng gấp đôi" — bất kể mỗi thao tác trên máy bạn tốn bao nhiêu nano giây.

**Quy tắc đơn giản hoá:** khi tính Big-O, ta **bỏ hằng số nhân** và **bỏ thành phần bậc thấp hơn**, chỉ giữ lại thành phần tăng nhanh nhất.

Ví dụ cụ thể: một đoạn code thực hiện chính xác `3n + 5` phép so sánh (3 vòng lặp độc lập qua `n` phần tử, cộng 5 phép tính khởi tạo cố định). Big-O của đoạn code này là **O(n)**, không phải O(3n+5). Lý do:

- Hằng số nhân `3` bị bỏ vì khi `n` tiến ra vô cùng, `3n` và `n` có **cùng tốc độ tăng** — cả hai đều tăng tuyến tính, chỉ khác độ dốc (một đường dốc gấp 3 lần đường kia, nhưng vẫn là đường thẳng). Big-O chỉ quan tâm "đường thẳng hay đường cong", không quan tâm "dốc bao nhiêu".
- Hằng số cộng `5` bị bỏ vì khi `n` đủ lớn (ví dụ `n = 1.000.000`), số `5` trở nên **không đáng kể** so với `3n = 3.000.000` — ảnh hưởng của nó biến mất khi `n` tiến về vô cùng.

Một ví dụ khác: `n² + 100n + 50` được rút gọn thành **O(n²)**, vì khi `n` đủ lớn, thành phần `n²` tăng nhanh hơn hẳn `100n` (dù `100n` lớn hơn `n²` khi `n` còn nhỏ, ví dụ `n=50`: `100n=5000` > `n²=2500` — nhưng tại `n=1000`: `n²=1.000.000` > `100n=100.000`, và khoảng cách này càng mở rộng khi `n` tiếp tục tăng). Big-O mô tả hành vi khi `n` tiến ra **vô cùng**, không phải hành vi tại một giá trị `n` cụ thể nào đó.

Quay lại tình huống ở mục 0: nếu ta thay việc "đo giờ trên hai máy khác nhau" bằng việc "đếm thao tác trên cùng một máy, với `n` tăng dần", ta có một cách so sánh đáng tin cậy hơn nhiều. Ví dụ dưới đây dùng `Stopwatch` (đo giờ thật) nhưng đo **trên cùng một máy**, với nhiều giá trị `n` tăng dần, để quan sát **tỷ lệ tăng** — đây là cách benchmark đúng, khác với cách đo sai ở mục 0 (so hai máy khác nhau tại một `n` cố định):

```csharp title="quan-sat-ty-le-tang-tren-cung-mot-may.cs"
// test:run
using System.Diagnostics;

long DoThoiGianTimTuyenTinh(int n)
{
    var a = new int[n];
    a[n - 1] = 999;   // dat gia tri can tim o CUOI -> buoc phai la worst-case

    var sw = Stopwatch.StartNew();
    for (int lanChay = 0; lanChay < 50; lanChay++)   // chay nhieu lan de giam nhieu do JIT warm-up
    {
        int viTri = -1;
        for (int i = 0; i < a.Length; i++)
            if (a[i] == 999) { viTri = i; break; }
    }
    sw.Stop();
    return sw.ElapsedTicks;
}

// Chay tren CUNG MOT MAY, tang n gap 10 lan qua moi buoc
long t1 = DoThoiGianTimTuyenTinh(100_000);
long t2 = DoThoiGianTimTuyenTinh(1_000_000);
long t3 = DoThoiGianTimTuyenTinh(10_000_000);

Console.WriteLine($"n=100.000:    {t1} ticks");
Console.WriteLine($"n=1.000.000:  {t2} ticks  (ty le so voi t1: ~{(double)t2 / t1:F1}x)");
Console.WriteLine($"n=10.000.000: {t3} ticks  (ty le so voi t2: ~{(double)t3 / t2:F1}x)");
// Ket qua thuc te se dao dong theo may, nhung TY LE tang giua cac buoc se xap xi 10x moi lan --
// dung voi du doan cua O(n): n tang gap 10 -> thao tac tang gap 10.
```

Điểm mấu chốt của ví dụ này: con số tuyệt đối (`t1`, `t2`, `t3` — bao nhiêu ticks) **không quan trọng** và sẽ khác nhau hoàn toàn nếu chạy lại trên máy khác — đúng như đã cảnh báo ở mục 0. Nhưng **tỷ lệ tăng** giữa `t2/t1` và `t3/t2` (xấp xỉ 10 lần mỗi bước, tương ứng với `n` tăng gấp 10 lần) là thứ **ổn định** và lặp lại được trên bất kỳ máy nào — đó chính là bằng chứng thực nghiệm cho O(n), khớp với kết quả đếm thao tác lý thuyết đã làm ở ví dụ đầu mục này.

---

## 2. O(1) — hằng số

**Định nghĩa (một câu):** O(1) nghĩa là số thao tác **không đổi**, bất kể kích thước đầu vào `n` lớn hay nhỏ — truy cập luôn tốn cùng một số bước.

```csharp title="o1-truy-cap-index.cs"
// test:run
int LayPhanTuDauTien(int[] a) => a[0];   // luôn đúng 1 bước, dù a có 5 hay 5 triệu phần tử

var mangNho = new int[] { 10, 20, 30 };
var mangLon = new int[5_000_000];
mangLon[0] = 99;

Console.WriteLine(LayPhanTuDauTien(mangNho));   // 10  — 1 bước
Console.WriteLine(LayPhanTuDauTien(mangLon));   // 99  — vẫn 1 bước, dù mảng lớn gấp 1.6 triệu lần
```

**Độ phức tạp: O(1).** Truy cập phần tử theo chỉ số (`a[0]`) trên `array`/`List<T>` luôn là một phép tính địa chỉ trực tiếp (địa chỉ gốc + chỉ số × kích thước phần tử) — không cần dò qua phần tử nào cả, nên số bước là hằng số, không phụ thuộc `n`.

**Nếu dùng sai/thiếu:** nhầm O(1) với "nhanh tuyệt đối" là sai — O(1) chỉ nghĩa là "không phụ thuộc `n`", một thao tác O(1) vẫn có thể tốn nhiều thời gian tuyệt đối hơn một thao tác O(n) nếu `n` rất nhỏ (ví dụ một phép tính O(1) phức tạp gồm 1000 dòng code, so với một vòng lặp O(n) chỉ có 3 phần tử). Big-O so sánh **xu hướng khi `n` lớn dần**, không so sánh thời gian tuyệt đối tại một `n` cụ thể.

---

## 3. O(log n) — logarit

**Định nghĩa (một câu):** O(log n) nghĩa là mỗi bước **loại bỏ một phần lớn (thường là một nửa)** dữ liệu còn lại cần xét, nên số bước tăng rất chậm khi `n` tăng — ví dụ `n` tăng gấp 1000 lần, số bước chỉ tăng thêm khoảng 10.

Điều kiện bắt buộc: binary search **chỉ** hoạt động đúng trên dữ liệu **đã sắp xếp** — nếu dữ liệu chưa sắp xếp, thuật toán này cho kết quả sai (không thể suy ra "nửa nào chứa target" nếu không có thứ tự).

```csharp title="ologn-binary-search.cs"
// test:run
int BinarySearch(int[] aDaSapXep, int target)
{
    int trai = 0, phai = aDaSapXep.Length - 1;
    int soLanLap = 0;
    while (trai <= phai)
    {
        soLanLap++;
        int giua = trai + (phai - trai) / 2;
        if (aDaSapXep[giua] == target) { Console.WriteLine($"Tìm thấy sau {soLanLap} lần lặp"); return giua; }
        if (aDaSapXep[giua] < target) trai = giua + 1;   // target ở nửa phải -> bỏ nửa trái
        else phai = giua - 1;                             // target ở nửa trái -> bỏ nửa phải
    }
    Console.WriteLine($"Không thấy sau {soLanLap} lần lặp");
    return -1;
}

var daySapXep = new int[1024];
for (int i = 0; i < daySapXep.Length; i++) daySapXep[i] = i;   // 0,1,2,...,1023 (đã sắp xếp)

BinarySearch(daySapXep, 777);   // Tìm thấy sau 9 lần lặp (nhỏ hơn mức tối đa log2(1024) = 10, vì 777 không rơi đúng vào ca xấu nhất)
```

**Độ phức tạp: O(log n).** Mỗi vòng lặp loại bỏ đúng **một nửa** phạm vi còn lại (`trai..phai`), nên sau `k` lần lặp, phạm vi còn lại có kích thước `n / 2^k`. Thuật toán dừng khi phạm vi còn `1` phần tử, tức `n / 2^k = 1`, giải ra `k = log₂(n)` — với `n = 1024`, `log₂(1024) = 10`, đây là số lần lặp **tối đa** (worst-case) có thể xảy ra. Kết quả in ra ở trên cho `target = 777` là 9 lần — ít hơn mức tối đa vì giá trị này không rơi đúng vào tình huống xấu nhất, nhưng vẫn cùng bậc O(log n): với `n = 1024` bất kỳ target nào cũng cần **không quá 10** lần lặp. So với O(n) của tìm tuyến tính (tối đa 1024 lần lặp), O(log n) chỉ cần tối đa 10 lần — chênh lệch càng lớn khi `n` càng lớn.

**Nếu dùng sai/thiếu:** chạy `BinarySearch` trên mảng **chưa sắp xếp** cho kết quả **sai** (không ném lỗi, chỉ đơn giản trả về `-1` sai hoặc chỉ số sai), vì logic "bỏ nửa trái/phải" giả định toàn bộ nửa trái nhỏ hơn giữa và toàn bộ nửa phải lớn hơn giữa — giả định này chỉ đúng khi dữ liệu đã sắp xếp.

Để thấy rõ O(log n) tăng chậm đến mức nào, so sánh số lần lặp tối đa cần thiết khi `n` tăng theo cấp số nhân:

```csharp title="olog-n-tang-cham-den-muc-nao.cs"
// test:run
int SoLanLapToiDa_BinarySearch(int n)
{
    int soLanLap = 0;
    int pham_vi = n;
    while (pham_vi > 1)
    {
        pham_vi /= 2;      // mo phong "bo mot nua" moi buoc
        soLanLap++;
    }
    return soLanLap;
}

Console.WriteLine($"n=1.000:            toi da {SoLanLapToiDa_BinarySearch(1_000)} lan lap");
Console.WriteLine($"n=1.000.000:        toi da {SoLanLapToiDa_BinarySearch(1_000_000)} lan lap");
Console.WriteLine($"n=1.000.000.000:    toi da {SoLanLapToiDa_BinarySearch(1_000_000_000)} lan lap");
// n tang 1000 lan (1.000 -> 1.000.000) nhung so lan lap chi tang khoang 10 (~10 -> ~20)
// n tang tiep 1000 lan nua (-> 1 ty) so lan lap chi tang them khoang 10 nua (~20 -> ~30)
```

Kết quả cho thấy: mỗi khi `n` tăng gấp **1000 lần**, số lần lặp tối đa của binary search chỉ tăng thêm khoảng **10** (vì `2^10 ≈ 1024`). Đây là lý do O(log n) được coi là gần với O(1) trong thực hành — với những `n` cực lớn (hàng tỷ phần tử), binary search vẫn chỉ cần khoảng 30 lần lặp, một con số nhỏ đến mức không đáng lo về hiệu năng.

---

## 4. O(n) — tuyến tính

**Định nghĩa (một câu):** O(n) nghĩa là số thao tác tăng **theo đúng tỷ lệ** với số phần tử đầu vào — mỗi phần tử được xét đúng một lần (không lồng thêm vòng lặp khác).

```csharp title="on-vong-lap-don.cs"
// test:run
int TimGiaTriLonNhat(int[] a)
{
    int max = a[0];
    foreach (var x in a)          // 1 vòng lặp duy nhất qua n phần tử
        if (x > max) max = x;
    return max;
}

Console.WriteLine(TimGiaTriLonNhat(new[] { 3, 7, 2, 9, 4 }));   // 9 — xét đúng 5 phần tử, 1 lần mỗi phần tử
```

**Độ phức tạp: O(n).** Vòng lặp `foreach` chạy đúng `n` lần (bằng số phần tử của `a`), mỗi lần thực hiện một số hằng số phép tính (so sánh + có thể gán) — tổng số thao tác là `c × n` với `c` là hằng số, rút gọn theo quy tắc ở mục 1 thành **O(n)**.

**Nếu dùng sai/thiếu:** nhầm "chỉ có một vòng lặp `foreach`" là luôn O(n) — sai nếu bên trong vòng lặp còn gọi một hàm khác không phải O(1) (ví dụ gọi `list.Contains(x)` trên một `List<T>` khác bên trong vòng lặp, thứ tự thực chất là O(n×m), xem mục 6 và phần Cạm bẫy).

---

## 5. O(n log n) — tuyến tính-logarit

**Định nghĩa (một câu):** O(n log n) nghĩa là dữ liệu được **chia nhỏ theo logarit** (giống mục 3) nhưng ở **mỗi tầng chia**, toàn bộ `n` phần tử vẫn phải được xử lý một lượt (giống mục 4) — kết hợp cả hai tốc độ tăng.

```csharp title="onlogn-sort.cs"
// test:run
int[] MergeSortDonGian(int[] a)
{
    if (a.Length <= 1) return a;
    int giua = a.Length / 2;
    var trai = MergeSortDonGian(a[..giua]);      // chia nửa trái -> đệ quy (tầng log n)
    var phai = MergeSortDonGian(a[giua..]);      // chia nửa phải -> đệ quy (tầng log n)
    return TronHai(trai, phai);                   // trộn lại -> quét qua n phần tử (tầng n)
}

int[] TronHai(int[] x, int[] y)
{
    var ketQua = new int[x.Length + y.Length];
    int i = 0, j = 0, k = 0;
    while (i < x.Length && j < y.Length)
        ketQua[k++] = x[i] <= y[j] ? x[i++] : y[j++];
    while (i < x.Length) ketQua[k++] = x[i++];
    while (j < y.Length) ketQua[k++] = y[j++];
    return ketQua;
}

var chuaSapXep = new[] { 5, 2, 9, 1, 7, 3 };
Console.WriteLine(string.Join(",", MergeSortDonGian(chuaSapXep)));   // 1,2,3,5,7,9
```

**Độ phức tạp: O(n log n).** Cây đệ quy chia mảng làm đôi liên tục có độ sâu `log₂(n)` tầng (giống binary search ở mục 3). Ở **mỗi tầng**, hàm `TronHai` phải quét qua tổng cộng `n` phần tử để trộn (giống vòng lặp tuyến tính ở mục 4). Tổng số thao tác là (số tầng) × (công việc mỗi tầng) = `log(n) × n` = **O(n log n)**. MergeSort đạt O(n log n) ở **cả worst-case** (không phụ thuộc thứ tự dữ liệu đầu vào), nhưng đánh đổi bằng việc cần cấp thêm mảng phụ có kích thước O(n) (không in-place) — chi tiết đánh đổi này quay lại ở mục "Không gian" (mục 9).

---

## 6. O(n²) — bình phương

**Định nghĩa (một câu):** O(n²) nghĩa là với **mỗi** phần tử, ta lại phải xét qua **toàn bộ** (hoặc gần toàn bộ) các phần tử khác một lần nữa — hai vòng lặp lồng nhau, mỗi vòng chạy khoảng `n` lần.

```csharp title="on2-hai-vong-lap-long-nhau.cs"
// test:run
void InCacCapTrung(int[] a)
{
    int soLanSoSanh = 0;
    for (int i = 0; i < a.Length; i++)
    {
        for (int j = i + 1; j < a.Length; j++)   // vòng trong lồng vào vòng ngoài
        {
            soLanSoSanh++;
            if (a[i] == a[j])
                Console.WriteLine($"Cặp trùng: a[{i}]={a[i]} và a[{j}]={a[j]}");
        }
    }
    Console.WriteLine($"Tổng số lần so sánh: {soLanSoSanh}");
}

InCacCapTrung(new[] { 3, 5, 3, 7, 5 });
// Cặp trùng: a[0]=3 và a[2]=3
// Cặp trùng: a[1]=5 và a[4]=5
// Tổng số lần so sánh: 10   (với n=5: n×(n-1)/2 = 5×4/2 = 10 -> vẫn thuộc lớp O(n²))
```

**Độ phức tạp: O(n²).** Vòng ngoài chạy `n` lần; với mỗi lần đó, vòng trong chạy trung bình khoảng `n/2` lần (vì bắt đầu từ `i+1`) — tổng số thao tác là khoảng `n × n/2 = n²/2`. Áp quy tắc đơn giản hoá ở mục 1 (bỏ hằng số nhân `1/2`), kết quả là **O(n²)**. Khi `n` tăng gấp đôi, số thao tác tăng gấp **bốn** lần (đặc trưng của bậc hai) — khác hẳn O(n) (tăng gấp đôi khi `n` tăng gấp đôi).

**Nếu dùng sai/thiếu:** dùng O(n²) cho dữ liệu lớn (ví dụ `n = 100.000`) sẽ cần khoảng `100.000² = 10 tỷ` thao tác — trên máy hiện đại (khoảng 1 tỷ thao tác đơn giản/giây), việc này tốn **khoảng 10 giây chỉ để so sánh**, một con số không chấp nhận được cho hầu hết ứng dụng thực tế. Đây là lý do các thư viện sort chuẩn (như `Array.Sort` của .NET) dùng thuật toán O(n log n), không dùng thuật toán O(n²) như Bubble Sort.

Không phải mọi O(n²) đều là lỗi cần sửa — cần phân biệt hai tình huống:

```csharp title="on2-can-thiet-vs-on2-do-vo-tinh.cs"
// test:run
// Tinh huong 1: O(n^2) CAN THIET -- bai toan tu ban chat can xet moi cap (i, j)
// Vi du: tinh khoang cach GIUA MOI CAP diem trong mot danh sach diem
double[,] TinhMaTranKhoangCach(double[] x, double[] y)
{
    int n = x.Length;
    var ketQua = new double[n, n];
    for (int i = 0; i < n; i++)
        for (int j = 0; j < n; j++)
            ketQua[i, j] = Math.Sqrt(Math.Pow(x[i] - x[j], 2) + Math.Pow(y[i] - y[j], 2));
    return ketQua;   // KHONG THE lam nhanh hon O(n^2) vi dinh nghia bai toan la "moi cap" -> co n^2 cap
}

// Tinh huong 2: O(n^2) DO VO TINH -- co the sua thanh O(n) bang cau truc du lieu dung (xem Bai 2)
bool CoTrungLap_ONVoTinh(int[] a)
{
    for (int i = 0; i < a.Length; i++)
        for (int j = 0; j < a.Length; j++)
            if (i != j && a[i] == a[j]) return true;   // KHONG can thiet -- HashSet lam duoc O(n), xem Bai 2
    return false;
}

var diem_x = new[] { 0.0, 3.0, 6.0 };
var diem_y = new[] { 0.0, 4.0, 8.0 };
var maTran = TinhMaTranKhoangCach(diem_x, diem_y);
Console.WriteLine(maTran[0, 1]);   // 5 -- khoang cach tu diem 0 den diem 1
```

`TinhMaTranKhoangCach` là O(n²) **cần thiết**: bài toán yêu cầu kết quả cho **mọi cặp** trong tổng số `n × n` cặp có thể — không có cách nào tính ra đủ `n²` kết quả bằng ít hơn `n²` bước cơ bản (mỗi kết quả cần tính riêng). `CoTrungLap_ONVoTinh` là O(n²) **do vô tình chọn cấu trúc dữ liệu chưa tối ưu** — như đã sửa ở Bài tập 2, đổi qua `HashSet<T>` hạ được xuống O(n). Kỹ năng quan trọng khi review code không phải "thấy O(n²) là báo lỗi ngay", mà là hỏi: "bài toán này có thực sự cần xét mọi cặp không, hay chỉ đang dùng nhầm cấu trúc dữ liệu?"

---

## 7. O(2ⁿ) và O(n!) — giới thiệu ngắn để biết tồn tại

**Định nghĩa (một câu, giới thiệu ngắn, không đi sâu):** O(2ⁿ) và O(n!) là các lớp độ phức tạp **bùng nổ** (exponential/factorial) — số thao tác tăng cực nhanh đến mức chỉ `n` khoảng 30–40 đã đủ làm máy tính hiện đại chạy nhiều năm không xong; các lớp này xuất hiện ở bài toán phải xét **mọi tổ hợp con** (O(2ⁿ), ví dụ liệt kê mọi tập con của một tập `n` phần tử) hoặc **mọi cách sắp xếp thứ tự** (O(n!), ví dụ liệt kê mọi cách hoán vị `n` phần tử — bài toán người du lịch dạng brute-force).

```text title="minh-hoa-quy-mo-bung-no.txt"
So sanh so thao tac can thuc hien khi n tang, giua cac lop do phuc tap:

n = 10:   O(n) = 10        O(n^2) = 100         O(2^n) = 1.024              O(n!) = 3.628.800
n = 20:   O(n) = 20        O(n^2) = 400         O(2^n) = 1.048.576          O(n!) = qua lon (~2.4 x 10^18)
n = 40:   O(n) = 40        O(n^2) = 1.600       O(2^n) = ~1.1 nghin ty      O(n!) = khong the tinh trong doi nguoi

Ket luan: O(2^n) va O(n!) chi kha thi voi n RAT NHO (thuong < 20-25).
Voi n lon hon, can chuyen sang thuat toan xap xi hoac Dynamic Programming (chuong sau).
```

Mục này chỉ giới thiệu để bạn **nhận diện** hai lớp này khi gặp trong phân tích thuật toán hoặc phỏng vấn — không đi sâu cách cài đặt. Điểm cần nhớ: nếu một bài toán có lời giải brute-force rơi vào O(2ⁿ) hoặc O(n!), đó là dấu hiệu cần tìm thuật toán tốt hơn (ví dụ Dynamic Programming, được giới thiệu ở chương cấu trúc dữ liệu nâng cao kế tiếp) trước khi chạy với `n` thực tế lớn.

---

## 8. Best case, average case, worst case

**Định nghĩa (một câu):** Best/average/worst case là ba cách mô tả độ phức tạp của **cùng một thuật toán** ứng với ba giả định khác nhau về **dữ liệu đầu vào** — dữ liệu thuận lợi nhất (best), dữ liệu điển hình/trung bình (average), và dữ liệu bất lợi nhất (worst) — vì cùng một thuật toán có thể nhanh hay chậm rất khác nhau tuỳ vào **thứ tự/giá trị cụ thể** của dữ liệu đưa vào, không chỉ tuỳ vào kích thước `n`.

Ví dụ cụ thể: QuickSort — thuật toán chọn một phần tử làm **pivot**, chia mảng thành "nhỏ hơn pivot" và "lớn hơn pivot", rồi đệ quy trên hai phần.

```csharp title="quicksort-minh-hoa-worst-average.cs"
// test:run
int soLanSoSanhToanCuc = 0;

int[] QuickSort(int[] a)
{
    if (a.Length <= 1) return a;
    int pivot = a[0];                                    // chọn pivot = phần tử ĐẦU (đơn giản hoá để minh hoạ worst-case)
    var nho = new List<int>();
    var lon = new List<int>();
    for (int i = 1; i < a.Length; i++)
    {
        soLanSoSanhToanCuc++;
        if (a[i] < pivot) nho.Add(a[i]); else lon.Add(a[i]);
    }
    var ketQua = new List<int>();
    ketQua.AddRange(QuickSort(nho.ToArray()));
    ketQua.Add(pivot);
    ketQua.AddRange(QuickSort(lon.ToArray()));
    return ketQua.ToArray();
}

// Truong hop XAU NHAT cho cach chon pivot = phan tu dau: mang DA SAP XEP SAN
soLanSoSanhToanCuc = 0;
QuickSort(new[] { 1, 2, 3, 4, 5, 6, 7, 8 });
Console.WriteLine($"Worst-case (mang da sap xep, pivot luon la min): {soLanSoSanhToanCuc} lan so sanh");
// 7+6+5+4+3+2+1 = 28 lan -> gan n(n-1)/2 -> dac trung O(n^2)

// Truong hop THUAN LOI: mang xao tron ngau nhien -> pivot thuong chia doi mang
soLanSoSanhToanCuc = 0;
QuickSort(new[] { 4, 7, 1, 8, 3, 6, 2, 5 });
Console.WriteLine($"Average-case (mang xao tron): {soLanSoSanhToanCuc} lan so sanh");
// it hon 28 ro rang -> gan n log n
```

**Độ phức tạp:**

- **Worst-case: O(n²).** Xảy ra khi pivot **luôn** là giá trị nhỏ nhất hoặc lớn nhất của phần mảng đang xét (ví dụ dữ liệu đã sắp xếp sẵn và cách chọn pivot là "luôn lấy phần tử đầu", như code trên) — mỗi lần đệ quy chỉ loại được **đúng 1 phần tử** (chính pivot), phần còn lại `n-1` phần tử vẫn phải xử lý tiếp. Tổng số so sánh là `(n-1) + (n-2) + ... + 1 = n(n-1)/2` — đúng dạng O(n²), khớp với kết quả `28` lần so sánh khi `n=8` (`8×7/2=28`).
- **Average-case: O(n log n).** Với dữ liệu **ngẫu nhiên**, pivot thường rơi vào khoảng giữa giá trị nhỏ nhất và lớn nhất một cách tương đối, nên mỗi lần đệ quy chia mảng thành hai phần **có kích thước tương đương** (giống MergeSort ở mục 5) — cho ra độ sâu đệ quy khoảng `log n` tầng, mỗi tầng xử lý tổng cộng khoảng `n` phần tử, tổng là O(n log n). Đây là lý do QuickSort **trung bình** vẫn được coi là một trong những thuật toán sort nhanh nhất trong thực tế, dù worst-case về lý thuyết là O(n²).
- **Best-case: O(n log n).** Xảy ra khi pivot luôn chia mảng thành hai nửa **đều nhau tuyệt đối** — về bản chất tốc độ tăng giống average-case ở đây.

**Nếu dùng sai/thiếu:** một câu trả lời sai phổ biến khi được hỏi "QuickSort độ phức tạp bao nhiêu?" là trả lời thẳng "O(n log n)" mà không nói rõ đó là average-case — bỏ sót worst-case O(n²) là một lỗi hiểu **không đầy đủ**, vì trong tình huống dữ liệu đầu vào bị kẻ tấn công cố ý sắp xếp để luôn rơi vào worst-case (một dạng tấn công có thật gọi là algorithmic complexity attack), hệ thống dùng QuickSort ngây thơ có thể bị làm chậm nghiêm trọng.

---

## 9. Độ phức tạp không gian (bộ nhớ) — giới thiệu ngắn

**Định nghĩa (một câu):** Độ phức tạp không gian (space complexity) mô tả **tốc độ tăng của lượng bộ nhớ phụ** (không tính bộ nhớ chứa dữ liệu đầu vào) mà một thuật toán cần cấp phát thêm, theo cùng cách ký hiệu Big-O, khi kích thước đầu vào `n` tăng.

```csharp title="space-complexity-minh-hoa.cs"
// test:run
// (a) O(1) khong gian phu: chi dung mot bien tam, khong phu thuoc n
int TongO1KhongGian(int[] a)
{
    int tong = 0;                 // 1 bien duy nhat, du a co n=10 hay n=10 trieu
    foreach (var x in a) tong += x;
    return tong;
}

// (b) O(n) khong gian phu: cap phat mang moi co kich thuoc bang dau vao
int[] NhanDoiTatCa_On_KhongGian(int[] a)
{
    var ketQua = new int[a.Length];   // mang phu co kich thuoc = n -> ti le voi dau vao
    for (int i = 0; i < a.Length; i++) ketQua[i] = a[i] * 2;
    return ketQua;
}

Console.WriteLine(TongO1KhongGian(new[] { 1, 2, 3, 4, 5 }));                          // 15 -> dung O(1) bo nho phu
Console.WriteLine(string.Join(",", NhanDoiTatCa_On_KhongGian(new[] { 1, 2, 3 })));    // 2,4,6 -> dung O(n) bo nho phu
```

**Độ phức tạp:** hàm `(a)` dùng **O(1)** không gian phụ — chỉ một biến `tong`, không đổi dù `n` lớn hay nhỏ. Hàm `(b)` dùng **O(n)** không gian phụ — mảng `ketQua` có kích thước đúng bằng `a.Length`, tăng tỷ lệ thuận với `n`. Đây chính là lý do MergeSort (mục 5) bị coi là "không in-place": nó cần cấp một mảng phụ O(n) tại mỗi lần trộn, trong khi QuickSort (mục 8, cài đặt in-place chuẩn — khác với bản minh hoạ dùng `List` ở trên) chỉ cần O(log n) không gian phụ cho ngăn xếp đệ quy trong average-case.

**Nếu dùng sai/thiếu:** đánh đổi thời gian và không gian là chuyện thường gặp — một thuật toán nhanh hơn về thời gian (ví dụ nhờ cache kết quả trung gian) thường tốn nhiều bộ nhớ hơn. Khi chọn thuật toán cho hệ thống thực tế, phải xét **cả hai** trục, không chỉ tối ưu một trục rồi bỏ quên trục kia (ví dụ một thuật toán O(n) thời gian nhưng cần O(n²) bộ nhớ có thể làm hệ thống hết RAM trước khi kịp chậm về thời gian).

Một ví dụ mở rộng để thấy rõ đánh đổi: giả sử bạn cần kiểm tra một số có phải số nguyên tố hay không, gọi hàm này `n` lần với `n` số khác nhau.

```csharp title="space-time-tradeoff-sang-loc-so-nguyen-to.cs"
// test:run
// Cach 1: kiem tra tung so tu dau, O(1) khong gian phu, nhung moi lan goi ton O(sqrt(k)) thoi gian
bool LaSoNguyenTo_KhongCache(int k)
{
    if (k < 2) return false;
    for (int i = 2; (long)i * i <= k; i++)
        if (k % i == 0) return false;
    return true;
}

// Cach 2: "Sang Eratosthenes" -> tinh truoc TOAN BO co (0..gioiHan) MOT LAN, cache vao mang bool
// Doi lai O(gioiHan) khong gian phu, nhung tra cuu sau do la O(1) moi lan
bool[] SangEratosthenes(int gioiHan)
{
    var laNguyenTo = new bool[gioiHan + 1];
    Array.Fill(laNguyenTo, true);
    laNguyenTo[0] = laNguyenTo[1] = false;
    for (int i = 2; i * i <= gioiHan; i++)
        if (laNguyenTo[i])
            for (int j = i * i; j <= gioiHan; j += i)
                laNguyenTo[j] = false;   // danh dau moi boi so cua i la hop so
    return laNguyenTo;
}

Console.WriteLine(LaSoNguyenTo_KhongCache(97));          // True  -> O(1) bo nho, O(sqrt(k)) thoi gian MOI LAN goi
var bangCache = SangEratosthenes(1000);                   // tra truoc mot lan: O(1000) bo nho
Console.WriteLine(bangCache[97]);                          // True  -> sau do tra cuu O(1) moi lan
```

Cách 1 không tốn bộ nhớ phụ đáng kể (O(1)) nhưng mỗi lần gọi lại tốn O(√k) thời gian — nếu gọi hàm này `n` lần, tổng thời gian là O(n√k). Cách 2 tốn trước O(gioiHan) bộ nhớ để dựng bảng, nhưng sau đó mỗi lần tra cứu chỉ O(1) — nếu gọi `n` lần, tổng thời gian chỉ còn O(gioiHan + n). Khi `n` rất lớn và `gioiHan` cố định, cách 2 rõ ràng thắng về thời gian, đổi lại phải chấp nhận tốn thêm bộ nhớ cho bảng cache. Không có lựa chọn nào "luôn đúng" — phụ thuộc ràng buộc thực tế (bộ nhớ có sẵn bao nhiêu, hàm được gọi bao nhiêu lần).

---

## 10. Bảng tổng hợp các lớp độ phức tạp

Bảng này chỉ tổng hợp lại — **không** giới thiệu khái niệm mới nào chưa dạy ở mục 2-9. Sắp xếp theo tốc độ tăng từ chậm nhất (tốt nhất) đến nhanh nhất (tệ nhất) khi `n` tăng.

| Lớp | Tên gọi | Ví dụ đã học | `n=10` (thao tác) | `n=1.000` (thao tác) | `n` tăng gấp 10 lần thì thao tác tăng |
|---|---|---|---|---|---|
| O(1) | Hằng số | Truy cập `a[0]` (mục 2) | 1 | 1 | không tăng |
| O(log n) | Logarit | Binary search (mục 3) | ~3 | ~10 | tăng rất chậm (+ vài đơn vị) |
| O(n) | Tuyến tính | Vòng lặp đơn tìm max (mục 4) | 10 | 1.000 | tăng gấp 10 |
| O(n log n) | Tuyến tính-log | MergeSort (mục 5) | ~33 | ~10.000 | tăng hơn 10, chưa tới 100 |
| O(n²) | Bình phương | Hai vòng lặp lồng (mục 6) | 100 | 1.000.000 | tăng gấp 100 |
| O(2ⁿ) | Bùng nổ mũ | Liệt kê mọi tập con (mục 7) | 1.024 | không khả thi | tăng theo cấp lũy thừa |
| O(n!) | Bùng nổ giai thừa | Liệt kê mọi hoán vị (mục 7) | 3.628.800 | không khả thi | tăng nhanh hơn cả O(2ⁿ) |

Ví dụ nâng cao trộn nhiều khái niệm — cho một hàm xử lý dữ liệu qua ba giai đoạn nối tiếp, tính Big-O tổng thể:

```csharp title="tron-nhieu-giai-doan-tinh-tong-bigo.cs"
// test:run
int[] XuLyBaGiaiDoan(int[] a)
{
    // Giai doan 1: O(n log n) -- sap xep
    var daSapXep = a.OrderBy(x => x).ToArray();

    // Giai doan 2: O(log n) -- binary search 1 gia tri trong mang da sap xep
    int viTri = Array.BinarySearch(daSapXep, daSapXep[0]);

    // Giai doan 3: O(n) -- quet 1 luot cong tong
    int tong = 0;
    foreach (var x in daSapXep) tong += x;

    Console.WriteLine($"Vi tri tim thay: {viTri}, Tong: {tong}");
    return daSapXep;
}

XuLyBaGiaiDoan(new[] { 5, 2, 8, 1, 9, 3 });
```

**Big-O tổng thể của `XuLyBaGiaiDoan`: O(n log n).** Quy tắc khi cộng nhiều giai đoạn **nối tiếp** (không lồng nhau): tổng Big-O bằng **giai đoạn có tốc độ tăng nhanh nhất**, các giai đoạn nhỏ hơn bị "nuốt" theo đúng quy tắc bỏ thành phần bậc thấp ở mục 1. Cụ thể: `O(n log n) + O(log n) + O(n)` — khi `n` tiến ra vô cùng, `n log n` tăng nhanh hơn cả `log n` và `n`, nên hai thành phần sau trở nên không đáng kể, tổng rút gọn thành **O(n log n)**. Đây là ví dụ đầu tiên trộn nhiều khái niệm (O(log n), O(n), O(n log n)) đã học riêng ở các mục 3-5 — đúng theo quy tắc chỉ đưa ví dụ trộn sau khi mọi khái niệm liên quan đã được dạy riêng.

---

## Cạm bẫy & thực chiến

1. **Coi Big-O là thời gian tuyệt đối.** `O(n)` không có nghĩa "chạy trong n giây" hay "n milliseconds" — nó chỉ mô tả **tốc độ tăng**. Một thuật toán O(n) trên máy chậm có thể chạy lâu hơn một thuật toán O(n²) trên máy nhanh, **khi `n` còn nhỏ**. Big-O chỉ đảm bảo ai thắng khi `n` đủ lớn.

2. **Chỉ đếm số vòng lặp lồng nhau mà quên method gọi bên trong không phải O(1).** Ví dụ `for (int i=0;i<n;i++) if (listB.Contains(a[i])) ...` **nhìn** giống một vòng lặp O(n), nhưng `List<T>.Contains` bên trong là O(m) (dò tuyến tính), nên thực chất là **O(n×m)**. Đây chính là lỗi đã nêu ở P1 (`collections.md`) — sửa bằng cách đổi `listB` thành `HashSet<T>` để `Contains` thành O(1), đưa tổng về O(n).

3. **Nhầm worst-case của QuickSort là "QuickSort chậm".** Trong thực tế, các thư viện chuẩn (bao gồm .NET) dùng các biến thể QuickSort có chọn pivot ngẫu nhiên hoặc "median-of-three" để làm cho worst-case O(n²) **cực khó xảy ra** với dữ liệu thông thường — nhưng về lý thuyết, worst-case vẫn tồn tại và vẫn cần biết để trả lời đúng khi phân tích thuật toán hoặc phỏng vấn.

4. **Dùng Big-O để so sánh hai thuật toán khi `n` luôn rất nhỏ và cố định.** Nếu hệ thống của bạn chỉ bao giờ xử lý `n ≤ 20` phần tử, sự khác biệt giữa O(n) và O(n²) có thể **không đáng kể về thời gian tuyệt đối** so với chi phí khác (I/O, network). Big-O là công cụ dự đoán **xu hướng khi `n` lớn dần** — áp dụng máy móc cho `n` luôn nhỏ có thể khiến bạn tối ưu sai chỗ (premature optimization) và bỏ lỡ chỗ cần tối ưu thật (thường là I/O hoặc network, không phải thuật toán trong bộ nhớ).

5. **Quên rằng hằng số bị bỏ có thể lớn trong thực tế.** Hai thuật toán cùng O(n) có thể khác nhau **hằng số nhân** rất nhiều (một là `n` phép tính, một là `50n` phép tính) — Big-O coi cả hai "cùng lớp", nhưng với `n` nhỏ, thuật toán `50n` vẫn chậm hơn nhiều lần trong thực tế. Big-O trả lời "ai thắng khi n → vô cùng", không trả lời "ai thắng ở n=100 hôm nay" — cần đo thực tế (benchmark) khi cần con số cụ thể cho `n` biết trước.

6. **Nhầm "độ phức tạp của thuật toán" với "độ phức tạp của bài toán".** Big-O mô tả một **cách giải cụ thể** (một thuật toán), không phải bản chất của bài toán. Cùng một bài toán "sắp xếp" có nhiều thuật toán khác nhau (Bubble Sort O(n²), MergeSort O(n log n)) — nói "sắp xếp là O(n²)" là sai, phải nói "Bubble Sort áp dụng cho bài toán sắp xếp là O(n²)". Một bài toán có thể có nhiều lời giải với Big-O rất khác nhau.

7. **Áp dụng quy tắc "bỏ hằng số" một cách máy móc khi so sánh hai thuật toán cùng lớp Big-O nhưng khác use-case.** Ví dụ `Dictionary<K,V>` và `SortedDictionary<K,V>` cả hai đều có `TryGetValue` gần O(1) và O(log n) tương ứng — nhưng nếu bài toán cần **duyệt theo thứ tự khoá**, so sánh thuần Big-O của riêng phép tra cứu là chưa đủ, cần xét thêm khả năng mà mỗi cấu trúc dữ liệu cung cấp (đã học ở P1 `collections.md` mục 7).

---

## Bài tập

### Bài 1 (giàn giáo) — Tính Big-O bằng đếm thao tác

Cho hàm sau, đếm số phép so sánh `arr[i] == arr[j]` được thực hiện theo `n = arr.Length`, rồi suy ra Big-O.

```csharp title="bai1-giandao.cs"
// test:skip giàn giáo cho học viên tự điền
int[] arr = new int[6];
// TODO: viết 2 vòng lặp lồng nhau, vòng ngoài i từ 0 đến n-1,
//       vòng trong j từ 0 đến n-1 (KHÔNG bắt đầu từ i+1 lần này — chạy đủ cả n),
//       đếm tổng số lần so sánh arr[i] == arr[j] thực hiện.
// Kỳ vọng với n=6: tổng số lần so sánh = ?
```

??? success "Lời giải"
    ```csharp title="bai1-loigiai.cs"
    // test:run
    int[] arr = new int[6];
    int n = arr.Length;
    int dem = 0;
    for (int i = 0; i < n; i++)
        for (int j = 0; j < n; j++)   // chạy đủ cả n, không phải i+1
            dem++;

    Console.WriteLine($"n={n}, tong so lan so sanh={dem}");   // n=6, tong=36
    Console.WriteLine($"n^2 = {n * n}");                       // 36 -> khop chinh xac
    ```
    **Điểm cốt lõi:** vì vòng trong chạy đủ `n` lần (không rút ngắn như `InCacCapTrung` ở mục 6), tổng số thao tác là đúng `n × n = n²` — Big-O là **O(n²)**, không có hằng số `1/2` như ví dụ ở mục 6 (nơi vòng trong bắt đầu từ `i+1` nên chỉ chạy trung bình `n/2` lần).

### Bài 2 (thiết kế) — Phát hiện và sửa O(n²) ẩn thành O(n)

Hàm dưới đây kiểm tra một mảng có phần tử trùng lặp không, đang chạy O(n²) vì dùng `List<T>.Contains` bên trong vòng lặp. Viết lại để đạt O(n).

```csharp title="bai2-giandao.cs"
// test:skip giàn giáo cho học viên tự điền
bool CoTrungLap_Cham(int[] a)
{
    var daThay = new List<int>();
    foreach (var x in a)
    {
        if (daThay.Contains(x)) return true;   // List.Contains la O(m) -> tong O(n^2)
        daThay.Add(x);
    }
    return false;
}
// TODO: viet lai ham CoTrungLap_Nhanh dat O(n), dung HashSet<T> thay List<T>
```

??? success "Lời giải"
    ```csharp title="bai2-loigiai.cs"
    // test:run
    bool CoTrungLap_Nhanh(int[] a)
    {
        var daThay = new HashSet<int>();
        foreach (var x in a)
        {
            if (!daThay.Add(x)) return true;   // Add tra false neu da co -> gop kiem tra + them thanh 1 buoc O(1)
        }
        return false;
    }

    Console.WriteLine(CoTrungLap_Nhanh(new[] { 1, 2, 3, 4, 2 }));   // True  -> 2 lap lai
    Console.WriteLine(CoTrungLap_Nhanh(new[] { 1, 2, 3, 4, 5 }));   // False -> khong lap
    ```
    **Điểm cốt lõi:** `HashSet<T>.Add` vừa kiểm tra tồn tại vừa thêm trong **một** lời gọi O(1), thay cho `Contains` (O(m)) + `Add` (O(1)) riêng biệt trên `List<T>`. Tổng độ phức tạp giảm từ O(n²) xuống **O(n)** — chỉ đổi cấu trúc dữ liệu, không đổi logic nghiệp vụ.

### Bài 3 (thử thách) — Phân loại Big-O cho bốn đoạn code khác nhau

Cho bốn hàm dưới đây, xác định Big-O của mỗi hàm theo `n = a.Length`, và với hàm nào có worst-case khác average-case, chỉ rõ sự khác biệt.

```csharp title="bai3-giandao.cs"
// test:skip giàn giáo cho học viên tự điền
int HamA(int[] a)
{
    return a.Length > 0 ? a[a.Length - 1] : -1;   // TODO: Big-O?
}

int HamB(int[] a, int target)
{
    // TODO: viet linear search tu dau den cuoi, tra ve vi tri hoac -1. Big-O?
    return -1;
}

void HamC(int[] a)
{
    // TODO: 2 vong lap long nhau, vong ngoai va vong trong deu chay het n. Big-O?
}

int[] HamD(int[] a)
{
    // TODO: goi Array.Sort (dung thu vien chuan .NET). Big-O?
    return a;
}
```

??? success "Lời giải"
    ```csharp title="bai3-loigiai.cs"
    // test:run
    int HamA(int[] a) => a.Length > 0 ? a[a.Length - 1] : -1;   // O(1) -- truy cap chi so, khong phu thuoc n

    int HamB(int[] a, int target)   // O(n) -- worst-case phai quet het n phan tu (target o cuoi hoac khong co)
    {
        for (int i = 0; i < a.Length; i++)
            if (a[i] == target) return i;
        return -1;
    }

    void HamC(int[] a)   // O(n^2) -- hai vong lap long nhau, ca hai deu chay het n
    {
        int n = a.Length;
        for (int i = 0; i < n; i++)
            for (int j = 0; j < n; j++)
                _ = a[i] + a[j];
    }

    int[] HamD(int[] a)   // O(n log n) average-case; that su .NET dung introsort nen worst-case cung O(n log n) (xem DEEP DIVE)
    {
        Array.Sort(a);
        return a;
    }

    var mau = new[] { 4, 1, 3, 2 };
    Console.WriteLine(HamA(mau));            // 2   -- phan tu cuoi
    Console.WriteLine(HamB(mau, 3));         // 2   -- vi tri cua 3
    HamC(mau);                                // khong in gi, chi minh hoa O(n^2)
    Console.WriteLine(string.Join(",", HamD(mau)));   // 1,2,3,4
    ```
    **Điểm cốt lõi:** `HamA` là O(1) vì `a.Length` và truy cập theo chỉ số đều là phép tính trực tiếp, không dò qua phần tử nào. `HamB` là O(n) vì **worst-case** (target ở cuối hoặc không tồn tại) phải xét cả `n` phần tử — best-case (target ở đầu) là O(1), nhưng khi nói Big-O của một hàm mà không chỉ rõ trường hợp, quy ước là nói đến **worst-case**. `HamC` là O(n²) vì hai vòng lặp lồng nhau chạy đủ. `HamD` dùng `Array.Sort` — về lý thuyết QuickSort thuần có worst-case O(n²), nhưng .NET dùng introsort (lai QuickSort/HeapSort/Insertion Sort, xem phần DEEP DIVE cuối chương) nên **cả worst-case thực tế cũng là O(n log n)**, không rơi vào O(n²) như QuickSort ngây thơ ở mục 8.

---

## Tự kiểm tra

Trả lời rồi mở đáp án.

1. Big-O đo cái gì — thời gian chạy tuyệt đối (giây/ms) hay tốc độ tăng của thời gian chạy?

    ??? note "Đáp án"
        Tốc độ tăng (growth rate) của thời gian/bộ nhớ khi kích thước đầu vào `n` tiến về vô cùng — hoàn toàn không phải thời gian tuyệt đối, không phụ thuộc máy chạy hay ngôn ngữ.

2. Vì sao `O(3n + 5)` được viết gọn thành `O(n)`?

    ??? note "Đáp án"
        Vì Big-O bỏ hằng số nhân (`3`) và thành phần cộng bậc thấp hơn/hằng số (`5`) — khi `n` tiến ra vô cùng, `3n+5` và `n` có cùng tốc độ tăng (cùng là đường thẳng tuyến tính, chỉ khác độ dốc/điểm xuất phát), Big-O chỉ quan tâm dạng tăng, không quan tâm hệ số.

3. Binary search có điều kiện tiên quyết gì để hoạt động đúng, và nếu vi phạm điều kiện đó thì xảy ra chuyện gì?

    ??? note "Đáp án"
        Dữ liệu phải **đã được sắp xếp**. Nếu chạy trên mảng chưa sắp xếp, thuật toán không ném lỗi mà cho **kết quả sai** (trả về sai vị trí hoặc báo không tìm thấy dù phần tử có tồn tại), vì logic "loại bỏ nửa trái/phải" dựa trên giả định thứ tự tăng dần.

4. QuickSort worst-case và average-case khác nhau ở Big-O nào, và worst-case xảy ra khi nào?

    ??? note "Đáp án"
        Worst-case là **O(n²)**, xảy ra khi pivot luôn là giá trị nhỏ nhất hoặc lớn nhất của phần đang xét (ví dụ dữ liệu đã sắp xếp sẵn kết hợp cách chọn pivot ngây thơ "luôn lấy phần tử đầu") — mỗi lần đệ quy chỉ loại được 1 phần tử. Average-case là **O(n log n)**, xảy ra với dữ liệu ngẫu nhiên khiến pivot thường chia mảng thành hai phần cỡ tương đương.

5. MergeSort và QuickSort (average-case) cùng là O(n log n) về thời gian — điểm khác biệt quan trọng về không gian giữa hai thuật toán này là gì?

    ??? note "Đáp án"
        MergeSort cần cấp thêm **O(n)** bộ nhớ phụ (mảng tạm để trộn) — không in-place. QuickSort (bản in-place chuẩn) chỉ cần khoảng **O(log n)** bộ nhớ phụ cho ngăn xếp đệ quy trong average-case — tiết kiệm bộ nhớ hơn, đây là lý do nhiều thư viện ưu tiên biến thể QuickSort khi bộ nhớ là ràng buộc quan trọng.

6. Một đoạn code có 2 vòng lặp `for` **không lồng nhau** (chạy nối tiếp, mỗi vòng qua `n` phần tử) có Big-O là bao nhiêu — O(n²) hay O(n)?

    ??? note "Đáp án"
        **O(n)**. Hai vòng lặp nối tiếp (không lồng) cho tổng số thao tác là `n + n = 2n`, áp quy tắc bỏ hằng số nhân (mục 1) thành O(n). O(n²) chỉ xảy ra khi vòng lặp **lồng nhau** (vòng trong nằm bên trong vòng ngoài), không phải khi chạy nối tiếp.

7. Vì sao đo giờ chạy bằng `Stopwatch` trên một máy cụ thể không đủ để kết luận "thuật toán A tốt hơn thuật toán B" một cách khoa học?

    ??? note "Đáp án"
        Vì thời gian đo được bị nhiễu bởi tốc độ CPU của máy, tải hệ thống lúc đo, và các hiệu ứng runtime (như JIT warm-up của .NET) — những yếu tố này không liên quan đến chất lượng thuật toán. Kết luận khoa học cần dựa trên phân tích Big-O (đếm thao tác theo hàm của `n`, độc lập với máy chạy) hoặc benchmark có kiểm soát chặt với nhiều lần đo và nhiều giá trị `n`.

8. O(2ⁿ) và O(n!) thường xuất hiện trong loại bài toán nào, và tại sao chúng chỉ khả thi với `n` rất nhỏ?

    ??? note "Đáp án"
        O(2ⁿ) xuất hiện khi phải xét **mọi tập con** của `n` phần tử; O(n!) xuất hiện khi phải xét **mọi cách hoán vị/sắp thứ tự** của `n` phần tử. Cả hai tăng nhanh đến mức chỉ `n` khoảng 30-40 đã vượt quá khả năng tính toán trong thời gian hợp lý của máy tính hiện đại — cần thay bằng thuật toán tốt hơn (ví dụ Dynamic Programming) khi `n` thực tế lớn hơn ngưỡng đó.

9. Cho một hàm chạy hai giai đoạn **nối tiếp** (không lồng nhau): giai đoạn 1 là O(n log n), giai đoạn 2 là O(n). Big-O tổng thể của cả hàm là gì, và vì sao?

    ??? note "Đáp án"
        **O(n log n)**. Khi cộng nhiều giai đoạn nối tiếp, Big-O tổng thể bằng giai đoạn có tốc độ tăng nhanh nhất — các giai đoạn tăng chậm hơn bị "nuốt" theo đúng quy tắc bỏ thành phần bậc thấp (mục 1 và mục 10), vì khi `n` tiến ra vô cùng, `n log n` áp đảo hoàn toàn `n`.

10. Vì sao nói "Big-O của `HamB` (linear search) là O(n)" thực chất là đang nói về **worst-case**, không phải best-case?

    ??? note "Đáp án"
        Vì quy ước khi nói "Big-O của một hàm" mà không chỉ rõ trường hợp, người ta mặc định nói đến **worst-case** — tình huống tệ nhất có thể xảy ra (target ở cuối mảng hoặc không tồn tại, phải quét hết `n` phần tử). Best-case của linear search (target ở vị trí đầu) thực ra là O(1), nhưng con số đó không đại diện cho hành vi đảm bảo của thuật toán trong mọi tình huống.

---

??? abstract "DEEP DIVE — Big-O, Big-Omega, Big-Theta và cận chính xác"
    **Big-O chỉ là một trong ba ký hiệu.** Trong toán học chính xác, Big-O (`O`) mô tả **cận trên** (upper bound) — "thuật toán này **không chậm hơn** tốc độ tăng này". Big-Omega (`Ω`) mô tả **cận dưới** (lower bound) — "thuật toán này **không nhanh hơn** tốc độ tăng này". Big-Theta (`Θ`) mô tả **cận chính xác** (tight bound) — khi cận trên và cận dưới trùng nhau, nghĩa là tốc độ tăng thực sự đúng bằng mức đó, không chỉ là giới hạn trên. Trong thực hành kỹ thuật phần mềm, người ta thường nói "O(n)" một cách thông tục để chỉ luôn cả trường hợp Θ(n) (tức là vừa đúng cận trên vừa đúng cận dưới) — cách dùng thông tục này chấp nhận được trong giao tiếp hàng ngày, nhưng về mặt học thuật chặt chẽ, "worst-case là O(n²)" chỉ khẳng định n² là **cận trên** (có thể tốt hơn với input cụ thể), còn "worst-case là Θ(n²)" khẳng định mạnh hơn: với **input xấu nhất**, thuật toán **chắc chắn** cần đúng cỡ n² thao tác, không thể tốt hơn.

    Ví dụ cụ thể để phân biệt: tìm kiếm tuyến tính (linear search) trên một mảng chưa sắp xếp có worst-case là Θ(n) — không chỉ "không chậm hơn n" (đó là O(n)) mà còn "không thể nhanh hơn n trong trường hợp xấu nhất" (đó là Ω(n)), vì nếu phần tử cần tìm không tồn tại, thuật toán **buộc phải** xét hết cả `n` phần tử để chắc chắn kết luận "không có" — không có cách nào rút ngắn hơn với thông tin đã cho. Ngược lại, bài toán "tìm giá trị lớn nhất trong một mảng đã biết trước là được sắp xếp tăng dần" có Θ(1) (chỉ cần lấy phần tử cuối), thấp hơn hẳn Θ(n) của bài toán tương tự trên mảng chưa sắp xếp — cùng là "tìm max" nhưng giả định khác về input làm cận chính xác khác hẳn.

    **Tại sao .NET's `Array.Sort` không dùng QuickSort thuần.** `Array.Sort` trong .NET dùng một thuật toán lai (introsort): bắt đầu bằng QuickSort (nhanh trong thực tế nhờ average-case tốt và cache-friendly do truy cập tuần tự trên mảng), nhưng theo dõi độ sâu đệ quy — nếu độ sâu vượt ngưỡng `log₂(n)` nhân với một hằng số (dấu hiệu đang rơi vào tình huống gần worst-case), nó **chuyển sang HeapSort** (luôn đảm bảo O(n log n), không có worst-case O(n²)) để tránh kịch bản tồi tệ nhất. Với mảng nhỏ (dưới một ngưỡng, thường khoảng 16 phần tử), nó chuyển sang Insertion Sort (O(n²) về lý thuyết nhưng cực nhanh trong thực tế với `n` nhỏ vì overhead thấp và tận dụng tốt cache CPU). Đây là ví dụ thực tế của nguyên tắc đã nêu trong Cạm bẫy #4: hằng số và chi phí thực tế vẫn quan trọng, không chỉ Big-O lý thuyết thuần tuý — kỹ sư giỏi kết hợp cả phân tích Big-O và đo đạc thực tế để chọn ngưỡng chuyển đổi giữa các thuật toán.

    **Amortized analysis (độ phức tạp khấu hao) — vì sao `List<T>.Add` được gọi là O(1) dù đôi khi phải copy cả mảng.** Đây là khái niệm bạn đã gặp thoáng qua ở P1 (`collections.md`, câu tự kiểm tra số 1) nhưng chưa được định nghĩa formal. `List<T>` bên trong dùng một mảng nền (`_items`) có sức chứa cố định; khi `Add` làm mảng đầy, .NET cấp một mảng **mới gấp đôi kích thước** rồi copy toàn bộ phần tử cũ sang — riêng lần đó tốn O(n). Nhưng vì kích thước gấp đôi mỗi lần phình, số lần phình xảy ra rất thưa (chỉ `log₂(n)` lần trong tổng số `n` lần Add) — nếu cộng tổng chi phí của tất cả các lần copy và chia đều cho `n` lần Add, chi phí **trung bình mỗi Add** hội tụ về một hằng số, dù từng lần Add riêng lẻ có thể là O(1) (bình thường) hoặc O(n) (lúc phình). Đây gọi là O(1) **khấu hao** (amortized) — khác với O(1) tuyệt đối (mọi lần gọi đều chắc chắn là hằng số, như truy cập chỉ số ở mục 2). Phân biệt hai loại O(1) này quan trọng khi thiết kế hệ thống real-time, nơi một lần Add bị "trúng" đúng lúc phình mảng có thể gây trễ (latency spike) dù độ phức tạp trung bình vẫn tốt.

    **Big-O trong ngữ cảnh nhiều biến (không chỉ một biến `n`).** Một số bài toán có độ phức tạp phụ thuộc **nhiều hơn một** kích thước đầu vào — ví dụ so khớp hai chuỗi có độ dài `n` và `m` khác nhau thường có Big-O dạng O(n × m), không rút gọn về một biến duy nhất được vì `n` và `m` độc lập với nhau. Tương tự, thuật toán trên đồ thị (sẽ học ở chương cấu trúc dữ liệu nâng cao) thường biểu diễn theo cả số đỉnh `V` và số cạnh `E`, ví dụ BFS/DFS là O(V + E) — không thể rút gọn thành một biến `n` chung nếu đồ thị không đảm bảo quan hệ cố định giữa `V` và `E`.

**Tiếp theo →** [P10 · Cấu trúc dữ liệu nâng cao](cau-truc-du-lieu-nang-cao.md)
