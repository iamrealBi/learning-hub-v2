---
tier: core
status: core
owner: core-team
verified_on: "2026-07-05"
dotnet_version: "10.0"
bloom: "Apply"
requires: [p10-dp]
est_minutes_fast: 70
---

# Interview Patterns: Two Pointers & Sliding Window

!!! info "bạn đang ở đây · p10 → node `p10-patterns`"
    **Cần trước:** quy hoạch động cơ bản (đã biết đo Big-O bằng cách đếm phép lặp/lời gọi hàm cụ thể, không đoán mò).
    **Mở khoá:** nhận diện nhanh 2 "khuôn mẫu" giải pháp lặp lại nhiều nhất trong phỏng vấn thuật toán, giảm thời gian suy nghĩ từ đầu cho các bài về mảng/chuỗi.
    ⏱️ Fast path ~70 phút.

> **Mục tiêu (đo được):** Sau chương này bạn (1) **giải thích** được vì sao brute-force lồng hai vòng lặp là O(n²) và Two Pointers rút xuống O(n) cho cùng bài toán trên dữ liệu đã sắp xếp; (2) **tự viết** Two Pointers cho bài "tìm hai số có tổng bằng X" và đo số lần so sánh thực tế; (3) **tự viết** Sliding Window độ dài cố định và độ dài thay đổi, **phân biệt** rõ khi nào dùng loại nào; (4) **nhận diện** đúng dấu hiệu đề bài để chọn pattern, và **chỉ ra** một ví dụ cụ thể mà Two Pointers/Sliding Window KHÔNG áp dụng được.

---

## 0. Đoán nhanh trước khi học (60 giây)

Đọc và **tự đoán** trước khi mở đáp án: đoạn code dưới đếm số lần **so sánh** để tìm hai số trong mảng đã sắp xếp có tổng bằng `10`.

```csharp title="Đoán số lần so sánh"
// test:run
int[] mang = { 1, 3, 4, 6, 7, 9, 11, 13 };   // đã sắp xếp tăng dần
int dich = 10;
int soLanSoSanh = 0;

int trai = 0, phai = mang.Length - 1;
while (trai < phai)
{
    soLanSoSanh++;
    int tong = mang[trai] + mang[phai];
    if (tong == dich) break;
    if (tong < dich) trai++;      // tổng nhỏ hơn đích -> cần tăng -> đẩy con trỏ trái vào
    else phai--;                  // tổng lớn hơn đích -> cần giảm -> đẩy con trỏ phải vào
}

Console.WriteLine($"{mang[trai]} + {mang[phai]} = {dich}");
Console.WriteLine($"Số lần so sánh: {soLanSoSanh}");
// Đoán: bao nhiêu lần so sánh so với 8 phần tử? Gần 8, hay gần 8*8=64?
```

??? note "Đáp án — mở SAU khi đã đoán"
    Kết quả `1 + 9 = 10`, và **số lần so sánh chỉ là 3 lần** — rất gần với số phần tử (8), **không phải** gần `8 × 8 = 64` như brute-force lồng hai vòng lặp sẽ tốn. Diễn biến cụ thể: bước 1 `trai=0(1), phai=7(13)` tổng `14 > 10` nên lùi `phai`; bước 2 `trai=0(1), phai=6(11)` tổng `12 > 10` nên lùi `phai` tiếp; bước 3 `trai=0(1), phai=5(9)` tổng `10 == 10` — dừng ngay. Hai biến `trai` và `phai` (hai "con trỏ") tiến vào nhau, mỗi bước loại bỏ đúng **một** phần tử khỏi vùng cần xét, nên tổng số bước tối đa là `n` — đây chính là **Two Pointers**, pattern đầu tiên của chương này.

---

## 1. Vấn đề gốc: nhiều bài phỏng vấn lặp lại cùng một "khuôn mẫu"

Khi giải bài thuật toán mới, cách chậm nhất là **nghĩ lại từ đầu** mỗi lần. Nhưng quan sát thực tế cho thấy rất nhiều bài về mảng/chuỗi trong phỏng vấn — nhìn khác nhau về đề bài — lại có **cùng một cấu trúc lời giải bên dưới**. Nhận ra cấu trúc đó (gọi là "pattern" — khuôn mẫu) giúp bạn **suy ra hướng giải trong vài giây** thay vì dò brute-force rồi mới tối ưu.

Chương này đi sâu vào hai pattern xuất hiện dày đặc nhất: **Two Pointers** (hai con trỏ) và **Sliding Window** (khung trượt). Cả hai đều có một điểm chung: thay vòng lặp lồng nhau O(n²) bằng cách **di chuyển thông minh** một hoặc hai vị trí đang xét, tận dụng thông tin đã biết từ bước trước — không tính lại từ đầu.

**Vì sao gọi là "khuôn mẫu" (pattern) chứ không phải "thuật toán":** khác với một thuật toán cụ thể (như MergeSort hay BFS, đã học ở các chương trước — mỗi thuật toán giải đúng một bài toán cụ thể), một pattern là một **cách tư duy/cấu trúc di chuyển chỉ số** có thể áp dụng cho **nhiều bài toán khác nhau về đề bài** nhưng giống nhau về cấu trúc dữ liệu bên dưới (mảng/chuỗi có tính đơn điệu, hoặc cần xét đoạn con liên tiếp). Vì vậy học một pattern không phải học một công thức duy nhất, mà là học **điều kiện áp dụng** + **cơ chế di chuyển** — từ đó tự suy ra code cụ thể cho bài toán trước mắt, thay vì nhớ máy móc lời giải của một bài cụ thể.

---

## 2. Two Pointers — định nghĩa và ví dụ tối thiểu

**Định nghĩa bằng lời:** Two Pointers là kỹ thuật dùng **hai biến chỉ số (con trỏ)** cùng đi qua một mảng/chuỗi, thường xuất phát từ hai đầu khác nhau (hoặc cùng đầu, cách nhau một khoảng) và **di chuyển có chủ đích dựa trên so sánh giá trị hiện tại**, thay cho việc dùng hai vòng lặp lồng nhau để xét mọi cặp phần tử.

**Bài toán ví dụ tối thiểu:** cho một mảng **đã sắp xếp tăng dần**, tìm hai phần tử có tổng bằng một số `X` cho trước.

```csharp title="Two Pointers: tìm hai số có tổng bằng X (mảng đã sắp xếp)"
// test:run
(int, int) TimHaiSo(int[] mang, int dich)
{
    int trai = 0;
    int phai = mang.Length - 1;

    while (trai < phai)
    {
        int tong = mang[trai] + mang[phai];
        if (tong == dich) return (mang[trai], mang[phai]);
        if (tong < dich) trai++;    // tổng đang NHỎ hơn đích -> cần số lớn hơn -> trai đi vào
        else phai--;                // tổng đang LỚN hơn đích -> cần số nhỏ hơn -> phai đi vào
    }
    return (-1, -1);   // không tìm được cặp nào
}

var (a, b) = TimHaiSo(new[] { 1, 3, 4, 6, 7, 9, 11, 13 }, 10);
Console.WriteLine($"{a} + {b} = 10");   // 1 + 9 = 10
```

**Vì sao di chuyển con trỏ là đúng, không bỏ sót cặp nào:** vì mảng **đã sắp xếp**, nếu `mang[trai] + mang[phai] < X`, thì **không có cách nào** `mang[trai]` kết hợp với bất kỳ phần tử nào ở bên trái `phai` (đều nhỏ hơn hoặc bằng `mang[phai]`) cho tổng đạt `X` — vậy `trai` phải tăng để thử số lớn hơn. Lý luận đối xứng áp dụng khi tổng lớn hơn `X`. Mỗi bước loại bỏ chắc chắn **một** khả năng sai mà không cần thử lại.

---

## 3. Độ phức tạp Two Pointers — tính cụ thể, không nói miệng

**So sánh với brute-force:** cách chậm nhất để tìm hai số có tổng `X` là thử **mọi cặp** `(i, j)` với `i < j` — hai vòng lặp lồng nhau, vòng ngoài chạy `n` lần, vòng trong chạy tới `n` lần → O(n²) phép so sánh.

```csharp title="Brute-force: thử mọi cặp — O(n^2)"
// test:run
int[] mang = { 1, 3, 4, 6, 7, 9, 11, 13 };
int dich = 10;
int soLanSoSanh = 0;

for (int i = 0; i < mang.Length; i++)
{
    for (int j = i + 1; j < mang.Length; j++)
    {
        soLanSoSanh++;
        if (mang[i] + mang[j] == dich)
        {
            Console.WriteLine($"{mang[i]} + {mang[j]} = {dich}, số lần so sánh: {soLanSoSanh}");
            return;
        }
    }
}
```

Với mảng 8 phần tử, brute-force tốn **5 lần so sánh** trước khi tìm ra `1 + 9` (thử theo thứ tự `(1,3) (1,4) (1,6) (1,7) (1,9)` — dừng ngay ở cặp thứ 5), còn Two Pointers ở mục 2 chỉ tốn **3 lần** (xem lại mục 0). Khoảng cách này không lớn với mảng nhỏ, nhưng với `n` lớn hơn (worst-case brute-force phải thử gần hết mọi cặp trước khi tìm ra hoặc kết luận "không có"), khoảng cách giãn ra rất nhanh — bảng dưới minh hoạ tốc độ tăng của **giới hạn trên (worst-case)**:

| n (số phần tử) | Brute-force O(n²) — số cặp tối đa | Two Pointers O(n) — số bước tối đa |
|---|---|---|
| 10 | 45 | 10 |
| 100 | 4.950 | 100 |
| 10.000 | ~50 triệu | 10.000 |

**Đo cụ thể độ phức tạp Two Pointers:** hai con trỏ `trai` và `phai` bắt đầu cách nhau tối đa `n - 1` vị trí. Mỗi vòng lặp, **đúng một** trong hai con trỏ di chuyển vào trong đúng 1 bước (`trai++` hoặc `phai--`), làm khoảng cách `phai - trai` giảm đúng 1. Vòng lặp dừng khi `trai >= phai`, tức sau tối đa `n - 1` bước. Mỗi bước làm O(1) việc (một phép cộng, một phép so sánh). Vậy tổng độ phức tạp là **O(n)** thời gian, O(1) bộ nhớ phụ (chỉ hai biến chỉ số, không cấp phát cấu trúc dữ liệu mới).

!!! danger "Điều kiện bắt buộc: mảng phải ĐÃ SẮP XẾP"
    Two Pointers kiểu "hai đầu tiến vào nhau" ở mục 2 **chỉ đúng** khi mảng đã sắp xếp — lý luận "tổng nhỏ hơn đích thì phải tăng `trai`" dựa hoàn toàn vào tính đơn điệu (giá trị tăng dần theo chỉ số). Với mảng **chưa sắp xếp**, di chuyển con trỏ theo cách này có thể **bỏ sót** cặp đúng đang tồn tại thật.

    Ví dụ cụ thể: mảng `[1, 2, 3, 4, 6, 5]` (chưa sắp xếp — phần tử `6` và `5` bị đảo vị trí so với thứ tự tăng dần), tìm tổng `10`. Cặp đúng tồn tại là `mang[3] + mang[4] = 4 + 6 = 10`. Nhưng chạy Two Pointers "hai đầu tiến vào nhau" trên mảng này:

    | Bước | trai (giá trị) | phai (giá trị) | tổng | Hành động |
    |---|---|---|---|---|
    | 1 | 0 (1) | 5 (5) | 6 | `6 < 10` → tăng `trai` |
    | 2 | 1 (2) | 5 (5) | 7 | `7 < 10` → tăng `trai` |
    | 3 | 2 (3) | 5 (5) | 8 | `8 < 10` → tăng `trai` |
    | 4 | 3 (4) | 5 (5) | 9 | `9 < 10` → tăng `trai` |
    | 5 | 4 (6) | 5 (5) | 11 | `11 > 10` → giảm `phai` → `trai == phai == 4`, vòng lặp dừng |

    Thuật toán báo "không tìm được", nhưng cặp `(4, 6)` ở chỉ số `(3, 4)` — không phải chỉ số `(3, 5)` hay `(4, 5)` — bị bỏ sót hoàn toàn vì con trỏ `phai` đi thẳng từ chỉ số `5` xuống `4` mà **không bao giờ dừng lại ở chỉ số 4 cùng lúc với `trai` ở chỉ số 3**: khi `trai = 3`, `phai` đang là `5` (chưa kịp giảm xuống `4`); tới lúc `trai` tăng lên `4` thì `phai` cũng vừa giảm xuống `4`, hai con trỏ trùng nhau và vòng lặp dừng trước khi có cơ hội xét cặp `(3, 4)`. Nguyên nhân gốc: mảng không đơn điệu, nên "tổng nhỏ hơn đích thì tăng trai" không còn đúng logic loại trừ nữa. Nếu dữ liệu chưa sắp xếp, phải sắp xếp trước (tốn O(n log n)) rồi mới áp dụng Two Pointers, hoặc dùng HashSet (cách khác, không thuộc phạm vi chương này).

---

## 3.1 Biến thể Two Pointers: hai con trỏ CÙNG HƯỚNG (không phải hai đầu tiến vào nhau)

Mục 2 và 3 dùng dạng Two Pointers "hai đầu tiến vào nhau" (`trai` bắt đầu từ đầu mảng, `phai` bắt đầu từ cuối mảng). Đây là một dạng **khác**: cả hai con trỏ **cùng xuất phát gần nhau** (thường cả hai từ đầu mảng) và **cùng đi theo một hướng**, nhưng với **tốc độ/vai trò khác nhau** — một con trỏ "chậm" chỉ tiến khi tìm thấy phần tử hợp lệ, một con trỏ "nhanh" luôn tiến để dò xét.

**Định nghĩa bằng lời (dạng cùng hướng):** hai con trỏ cùng đi từ đầu đến cuối mảng theo cùng chiều; con trỏ "nhanh" dùng để **dò/đọc** từng phần tử, con trỏ "chậm" dùng để **ghi/giữ** vị trí kết quả hợp lệ cuối cùng đã xác nhận — chỉ tiến lên khi con trỏ nhanh phát hiện một phần tử cần giữ lại.

**Bài toán ví dụ tối thiểu:** cho một mảng **đã sắp xếp**, xoá các phần tử trùng lặp **tại chỗ** (in-place, không tạo mảng mới), trả về số phần tử còn lại sau khi loại trùng.

```csharp title="Two Pointers cùng hướng: xoá trùng lặp tại chỗ trên mảng đã sắp xếp"
// test:run
int XoaTrungLap(int[] mang)
{
    if (mang.Length == 0) return 0;

    int cham = 0;   // con trỏ "chậm": vị trí cuối cùng đã ghi giá trị hợp lệ
    for (int nhanh = 1; nhanh < mang.Length; nhanh++)   // con trỏ "nhanh": dò từng phần tử
    {
        if (mang[nhanh] != mang[cham])   // gặp giá trị MỚI, khác giá trị vừa giữ -> cần giữ lại
        {
            cham++;
            mang[cham] = mang[nhanh];    // ghi giá trị mới vào ngay sau vị trí hợp lệ cuối
        }
        // nếu mang[nhanh] == mang[cham] -> bỏ qua, không ghi gì (đây là phần tử trùng)
    }

    return cham + 1;   // số phần tử KHÁC NHAU còn lại
}

var mang = new[] { 1, 1, 2, 2, 2, 3, 4, 4, 5 };
int soLuong = XoaTrungLap(mang);
Console.WriteLine(soLuong);                                    // 5
Console.WriteLine(string.Join(",", mang[..soLuong]));           // 1,2,3,4,5
```

**Vì sao hai con trỏ khác vai trò vẫn là Two Pointers:** cả hai vẫn là hai biến chỉ số cùng đi qua mảng **một lần duy nhất**, và mỗi bước di chuyển đều dựa vào **so sánh giá trị hiện tại** (giống Two Pointers hai đầu ở mục 2) — chỉ khác ở chỗ cả hai đi **cùng chiều** với tốc độ khác nhau, thay vì đối đầu nhau từ hai phía. Đây vẫn thuộc họ Two Pointers vì tận dụng đúng nguyên lý: **dữ liệu đã sắp xếp** đảm bảo mọi phần tử trùng nhau **nằm liền kề**, nên chỉ cần so sánh với phần tử hợp lệ gần nhất (`mang[cham]`), không cần so sánh với mọi phần tử đã xử lý trước đó.

**Độ phức tạp:** con trỏ `nhanh` chạy đúng `n - 1` lần (một vòng `for` duy nhất, không lặp lại). Con trỏ `cham` chỉ tăng khi `nhanh` phát hiện giá trị mới — tối đa cũng chỉ tăng `n - 1` lần trong toàn bộ hàm. Mỗi bước làm O(1) việc (một phép so sánh, có thể một phép ghi). Tổng: **O(n)** thời gian, O(1) bộ nhớ phụ (sửa tại chỗ trên mảng gốc, không cấp phát mảng mới) — so với cách "tạo `HashSet` rồi build mảng mới" cũng cho O(n) thời gian nhưng tốn thêm O(n) bộ nhớ cho cấu trúc phụ, trong khi Two Pointers tại chỗ giữ bộ nhớ phụ ở mức O(1).

!!! danger "Điều kiện vẫn giữ nguyên: PHẢI đã sắp xếp"
    Kỹ thuật "xoá trùng lặp tại chỗ" ở trên **chỉ đúng** khi mảng đã sắp xếp — vì logic "chỉ so sánh với phần tử hợp lệ gần nhất" giả định mọi giá trị trùng nhau **nằm liền kề nhau**. Với mảng chưa sắp xếp, ví dụ `[1, 2, 1, 3]`, giá trị `1` xuất hiện ở chỉ số `0` và `2` nhưng **không liền kề** (bị `2` chen giữa) — thuật toán trên sẽ **không phát hiện** `mang[2] == 1` là trùng với `mang[0]`, vì nó chỉ so sánh với `mang[cham]` (giá trị hợp lệ *gần nhất*, không phải *mọi* giá trị đã giữ). Kết quả: hàm trả về sai số lượng phần tử duy nhất.

---

## 4. Sliding Window — định nghĩa và ví dụ tối thiểu (độ dài CỐ ĐỊNH)

**Định nghĩa bằng lời:** Sliding Window (khung trượt) là kỹ thuật giữ một **đoạn con liên tiếp** (khung) trong mảng/chuỗi, và khi cần xét đoạn con kế tiếp, chỉ **cập nhật khung hiện tại** (thêm phần tử mới, bỏ phần tử cũ) thay vì tính lại toàn bộ đoạn từ đầu.

**Bài toán ví dụ tối thiểu:** cho một mảng số và một số `k`, tìm **tổng lớn nhất** của `k` phần tử liên tiếp.

```csharp title="Sliding Window độ dài cố định: tổng lớn nhất của k phần tử liên tiếp"
// test:run
int TongLonNhat(int[] mang, int k)
{
    int tongHienTai = 0;
    for (int i = 0; i < k; i++)
        tongHienTai += mang[i];          // tính tổng khung ĐẦU TIÊN, độ dài đúng k

    int tongLonNhat = tongHienTai;

    for (int i = k; i < mang.Length; i++)
    {
        tongHienTai += mang[i];          // thêm phần tử MỚI vào bên phải khung
        tongHienTai -= mang[i - k];      // bỏ phần tử CŨ ra khỏi bên trái khung
        tongLonNhat = Math.Max(tongLonNhat, tongHienTai);
    }

    return tongLonNhat;
}

Console.WriteLine(TongLonNhat(new[] { 2, 1, 5, 1, 3, 2 }, 3));   // 9  -> khung [5,1,3]
Console.WriteLine(TongLonNhat(new[] { 2, 3, 4, 1, 5 }, 2));      // 7  -> khung [3,4]
```

**Vì sao "trượt" nhanh hơn tính lại:** khung có độ dài `k` cố định — khi trượt từ vị trí `i-1` sang `i`, khung mới và khung cũ **chồng lấp `k - 1` phần tử**, chỉ khác đúng 1 phần tử ở mỗi đầu. Vì vậy `tongHienTai` mới = `tongHienTai` cũ + phần tử vào - phần tử ra, là phép tính O(1), không cần cộng lại `k` phần tử từ đầu.

---

## 5. Độ phức tạp Sliding Window (độ dài cố định)

**So sánh với cách tính lại mỗi lần:** nếu không trượt khung mà tính lại tổng `k` phần tử từ đầu cho **mỗi** vị trí bắt đầu có thể, đó là vòng lặp ngoài chạy `n - k + 1` lần, vòng trong cộng `k` phần tử mỗi lần → O(n × k) thời gian.

```csharp title="Cách chậm: tính lại tổng k phần tử mỗi lần — O(n*k)"
// test:run
int TongLonNhatChậm(int[] mang, int k)
{
    int tongLonNhat = int.MinValue;
    for (int i = 0; i <= mang.Length - k; i++)
    {
        int tong = 0;
        for (int j = i; j < i + k; j++)
            tong += mang[j];             // cộng lại TỪ ĐẦU mỗi lần, dù trùng k-1 phần tử với lần trước
        tongLonNhat = Math.Max(tongLonNhat, tong);
    }
    return tongLonNhat;
}

Console.WriteLine(TongLonNhatChậm(new[] { 2, 1, 5, 1, 3, 2 }, 3));   // 9 — cùng kết quả, chậm hơn
```

Với Sliding Window (mục 4), vòng lặp đầu tính tổng khung đầu tiên tốn O(k), sau đó vòng lặp thứ hai chạy `n - k` lần, mỗi lần làm đúng O(1) việc (một phép cộng, một phép trừ, một so sánh) — tổng lại: O(k) + O(n - k) = **O(n)** thời gian, O(1) bộ nhớ phụ. So với O(n × k) của cách tính lại, Sliding Window nhanh hơn hẳn khi `k` lớn — bảng minh hoạ với `n = 10.000`:

| k | Cách tính lại O(n×k) | Sliding Window O(n) |
|---|---|---|
| 10 | ~100.000 phép cộng | ~10.000 phép cộng/trừ |
| 1.000 | ~10.000.000 phép cộng | ~10.000 phép cộng/trừ |

---

## 6. Sliding Window độ dài THAY ĐỔI — định nghĩa riêng, khác mục 4

**Định nghĩa bằng lời:** Sliding Window độ dài **thay đổi** là biến thể trong đó khung **không có độ dài cố định trước** — khung **mở rộng** (di chuyển biên phải) khi còn hợp lệ, và **co lại** (di chuyển biên trái) khi vi phạm một điều kiện nào đó, tự điều chỉnh kích thước theo dữ liệu thực tế.

**Bài toán ví dụ:** cho một chuỗi, tìm độ dài đoạn con **liên tiếp dài nhất** mà **không có ký tự lặp lại**.

```csharp title="Sliding Window độ dài thay đổi: đoạn con dài nhất không lặp ký tự"
// test:run
int DoanDaiNhatKhongLap(string chuoi)
{
    var trongKhung = new HashSet<char>();
    int trai = 0;
    int doDaiToiDa = 0;

    for (int phai = 0; phai < chuoi.Length; phai++)
    {
        // Khung [trai, phai] đang muốn thêm chuoi[phai] -> nếu ký tự đã có trong khung,
        // phải CO khung lại từ bên trái cho tới khi hết trùng
        while (trongKhung.Contains(chuoi[phai]))
        {
            trongKhung.Remove(chuoi[trai]);
            trai++;
        }

        trongKhung.Add(chuoi[phai]);                      // mở rộng khung sang phải
        doDaiToiDa = Math.Max(doDaiToiDa, phai - trai + 1); // độ dài khung hiện tại
    }

    return doDaiToiDa;
}

Console.WriteLine(DoanDaiNhatKhongLap("abcabcbb"));   // 3  -> "abc"
Console.WriteLine(DoanDaiNhatKhongLap("bbbbb"));      // 1  -> "b"
Console.WriteLine(DoanDaiNhatKhongLap("pwwkew"));     // 3  -> "wke"
```

**Vì sao vòng `while` co khung là đúng, không bỏ sót đáp án tốt hơn:** khi `chuoi[phai]` đã tồn tại trong khung, khung **hiện tại** (bắt đầu từ `trai` cũ) không còn hợp lệ nếu giữ `chuoi[phai]` — buộc phải loại bỏ phần tử từ bên trái (`trai++`) cho tới khi ký tự trùng biến mất khỏi khung. Mỗi phần tử bị loại khỏi `trongKhung` chỉ **đúng một lần** trước khi `trai` vượt qua nó vĩnh viễn — không quay lại.

---

## 7. Độ phức tạp Sliding Window độ dài thay đổi

Nhìn qua, đoạn code mục 6 có **vòng lặp lồng nhau** (`for phai` bên ngoài, `while trai` bên trong) — dễ nhầm là O(n²). Nhưng phải đếm cụ thể: biến `phai` chạy đúng `n` lần (một vòng `for` từ `0` đến `n-1`, không quay lại). Biến `trai` **chỉ tăng, không bao giờ giảm** trong suốt toàn bộ hàm — tổng số lần `trai++` trong toàn bộ vòng `while` (cộng dồn qua tất cả các lần lặp của `for`) **tối đa là `n`** vì `trai` chỉ đi từ `0` đến tối đa `n - 1`. Vậy tổng công việc là O(n) (cho `phai`) + O(n) (cho tổng mọi lần `trai` tăng, cộng dồn toàn hàm) = **O(n)** thời gian, O(k) bộ nhớ cho `trongKhung` (k = số ký tự khác nhau tối đa có thể nằm trong khung, bị chặn bởi kích thước bảng ký tự).

**Kỹ thuật đếm này gọi là "amortized analysis" (phân tích khấu hao):** dù có vòng lặp lồng nhau về mặt cú pháp, tổng số lần thực thi của vòng trong **trên toàn bộ hàm** (không phải trên từng lần lặp ngoài riêng lẻ) mới quyết định Big-O thật.

---

## 8. Nhận diện: khi nào dùng Two Pointers, khi nào dùng Sliding Window

Hai pattern đã được định nghĩa và đo riêng ở các mục trên — giờ mới đặt cạnh nhau để nhận diện dấu hiệu đề bài.

| Dấu hiệu trong đề bài | Pattern nên nghĩ tới | Vì sao |
|---|---|---|
| Dữ liệu **đã sắp xếp** hoặc có tính **đối xứng** (ví dụ kiểm tra palindrome) | Two Pointers | Có thể suy luận "tiến vào nhau" dựa vào tính đơn điệu/đối xứng, loại bỏ chắc chắn một phía sai mỗi bước |
| Hỏi về "**đoạn con liên tiếp**" (subarray) hoặc "**chuỗi con liên tiếp**" (substring) với một điều kiện (tổng, độ dài, số ký tự khác nhau...) | Sliding Window | Đoạn con liên tiếp có thể "trượt" — thêm/bớt một đầu mà không cần tính lại cả đoạn |
| Độ dài đoạn con là **số cố định `k` cho trước** | Sliding Window độ dài **cố định** (mục 4) | Khung luôn giữ đúng `k` phần tử, chỉ trượt, không co/giãn |
| Độ dài đoạn con **không biết trước**, phụ thuộc điều kiện ("dài nhất thoả X", "ngắn nhất thoả Y") | Sliding Window độ dài **thay đổi** (mục 6) | Khung phải tự mở rộng/co lại theo dữ liệu, không có `k` cố định |

**Quy tắc thực dụng:** đọc đề, gạch chân các cụm "đã sắp xếp"/"tăng dần" → nghĩ Two Pointers. Gạch chân cụm "đoạn con"/"subarray"/"substring liên tiếp" → nghĩ Sliding Window, rồi hỏi tiếp "độ dài có cố định không" để chọn đúng biến thể.

### 8.1 Luyện nhận diện: 6 đề bài mẫu, chọn đúng pattern trước khi viết code

Đọc từng đề bài dưới, **tự đoán pattern** trước khi mở đáp án — đây là bước "nhận diện" thực tế trong phỏng vấn, xảy ra **trước khi** viết bất kỳ dòng code nào.

1. "Cho một mảng số nguyên đã sắp xếp tăng dần, kiểm tra có tồn tại hai chỉ số `i != j` sao cho `mang[i] + mang[j] == 0` hay không."

    ??? note "Đáp án"
        **Two Pointers hai đầu.** Dấu hiệu: "đã sắp xếp tăng dần" + "hai chỉ số/hai phần tử có tổng = một giá trị cụ thể" — khớp chính xác mẫu ở mục 2.

2. "Cho một chuỗi, tìm độ dài của đoạn con liên tiếp dài nhất chỉ chứa tối đa 2 loại ký tự khác nhau."

    ??? note "Đáp án"
        **Sliding Window độ dài thay đổi.** Dấu hiệu: "đoạn con liên tiếp" + "dài nhất" (không biết trước độ dài) + có điều kiện ràng buộc (tối đa 2 loại ký tự) — khung mở rộng khi còn hợp lệ (dưới 2 loại), co lại khi vi phạm (vượt quá 2 loại) — cùng cơ chế mục 6, chỉ đổi điều kiện kiểm tra từ "không trùng ký tự" sang "không vượt quá 2 loại ký tự khác nhau", theo dõi bằng `Dictionary<char,int>` (đếm số lượng) thay vì `HashSet<char>` (chỉ có/không).

3. "Cho một mảng nhiệt độ theo từng ngày, tìm nhiệt độ trung bình cao nhất của mọi giai đoạn 7 ngày liên tiếp."

    ??? note "Đáp án"
        **Sliding Window độ dài cố định.** Dấu hiệu: "7 ngày liên tiếp" — độ dài `k = 7` cố định, cho trước — khớp mẫu mục 4 (thay "tổng lớn nhất" bằng "trung bình lớn nhất", chỉ cần chia tổng cho 7 sau khi tính bằng cùng cơ chế trượt).

4. "Cho hai mảng đã sắp xếp, hợp nhất chúng thành một mảng đã sắp xếp duy nhất (merge hai mảng, giống bước 'merge' trong MergeSort)."

    ??? note "Đáp án"
        **Two Pointers, nhưng trên HAI mảng khác nhau** (không phải hai đầu của một mảng). Đây là biến thể khác: mỗi con trỏ đi trên **một mảng riêng**, cùng tiến lên (không phải đối đầu), so sánh giá trị tại hai con trỏ để quyết định lấy phần tử nào ra trước — vẫn đúng tinh thần "hai chỉ số di chuyển có chủ đích dựa trên so sánh giá trị", nhưng không thuộc dạng "hai đầu tiến vào nhau" hay "cùng hướng trên một mảng" đã học — cho thấy Two Pointers là một **họ kỹ thuật rộng**, không chỉ hai biến thể trong chương này.

5. "Cho một mảng, tìm đoạn con liên tiếp có tổng lớn nhất (mảng có thể chứa số âm)."

    ??? note "Đáp án"
        **KHÔNG phải Sliding Window kiểu mục 4/6 một cách trực tiếp.** Đây là cạm bẫy nhận diện: tuy có cụm "đoạn con liên tiếp", nhưng khi mảng **có số âm**, việc "mở rộng khung luôn tốt hơn hoặc co khung khi vi phạm" không còn áp dụng đơn giản như mục 6 (không có "điều kiện vi phạm" rõ ràng để co khung — thêm một số âm không làm khung "sai", chỉ làm tổng giảm). Bài này thường được giải bằng thuật toán khác (Kadane's algorithm — một dạng quy hoạch động 1 chiều đơn giản, nằm ngoài phạm vi chương này) — minh hoạ đúng tinh thần mục 9-10: không phải mọi bài có từ khoá "đoạn con liên tiếp" đều giải được bằng Sliding Window như đã định nghĩa.

6. "Cho một mảng đã sắp xếp và một số `target`, tìm chỉ số của phần tử `target` (nếu có)."

    ??? note "Đáp án"
        **KHÔNG phải Two Pointers.** Dù dữ liệu đã sắp xếp — dấu hiệu quen thuộc của Two Pointers — bài này chỉ tìm **một** phần tử theo giá trị cụ thể, không phải một **cặp**/tổ hợp phần tử thoả điều kiện. Với dữ liệu đã sắp xếp và tìm một giá trị đơn, công cụ đúng là **Binary Search** (đã học ở chương đệ quy & binary search) — O(log n), nhanh hơn cả Two Pointers O(n). Đây là lời nhắc: "đã sắp xếp" không tự động nghĩa là Two Pointers; phải xem đề bài hỏi về **một phần tử** hay **một cặp/tổ hợp**.

**Điểm cốt lõi rút ra từ 6 ví dụ trên:** nhận diện pattern là bước **gợi ý hướng đi nhanh**, nhưng luôn phải tự kiểm chứng lại bằng câu hỏi "cơ chế di chuyển con trỏ/khung của pattern này có thực sự đúng với đặc điểm cụ thể của bài toán không" (xem thêm mục 9, 10 và phần DEEP DIVE cuối bài) — không áp dụng máy móc chỉ vì thấy từ khoá quen thuộc.

---

## 9. Ví dụ tổng hợp: Container With Most Water — Two Pointers tối ưu một "khung"

Sau khi cả Two Pointers (mục 2-3) và Sliding Window (mục 4-7) đã được định nghĩa riêng, đây là ví dụ cho thấy **ranh giới giữa hai pattern không tuyệt đối**: bài toán dưới dùng đúng cơ chế "hai đầu tiến vào nhau" của Two Pointers, nhưng mục tiêu tối ưu lại là một "khung" giữa hai con trỏ — giống tinh thần Sliding Window.

**Định nghĩa bài toán:** cho một mảng `height`, trong đó `height[i]` là chiều cao của một "vách" dựng tại vị trí `i`. Hai vách tại vị trí `i` và `j` (`i < j`) cùng đáy tạo thành một "thùng chứa nước", có diện tích chứa được là `min(height[i], height[j]) * (j - i)` (chiều cao bị giới hạn bởi vách **thấp hơn**, vì nước tràn qua vách thấp). Tìm diện tích **lớn nhất** có thể tạo được từ hai vách bất kỳ.

```csharp title="Container With Most Water — Two Pointers hai đầu tiến vào nhau"
// test:run
int DienTichLonNhat(int[] height)
{
    int trai = 0, phai = height.Length - 1;
    int dienTichLonNhat = 0;

    while (trai < phai)
    {
        int chieuCaoThapHon = Math.Min(height[trai], height[phai]);
        int dienTich = chieuCaoThapHon * (phai - trai);
        dienTichLonNhat = Math.Max(dienTichLonNhat, dienTich);

        // Vách nào THẤP HƠN mới có khả năng cải thiện diện tích khi di chuyển vào —
        // giữ vách cao, đổi vách thấp mới có cơ hội tìm được vách cao hơn thay thế
        if (height[trai] < height[phai]) trai++;
        else phai--;
    }

    return dienTichLonNhat;
}

Console.WriteLine(DienTichLonNhat(new[] { 1, 8, 6, 2, 5, 4, 8, 3, 7 }));   // 49 -> vách tại chỉ số 1 (cao 8) và chỉ số 8 (cao 7)
```

**Vì sao di chuyển "vách thấp hơn" là đúng, không bỏ sót đáp án tốt hơn:** giả sử `height[trai] < height[phai]`. Nếu giữ `trai` cố định và di chuyển `phai` vào trong (giảm `phai`), khoảng cách `phai - trai` chắc chắn **giảm**, và chiều cao giới hạn vẫn bị chặn bởi `height[trai]` (vẫn là vách thấp hơn hoặc bằng, vì mọi vách còn lại nằm giữa `trai` và `phai` cũ) — diện tích mới **không thể lớn hơn** diện tích hiện tại (cả hai yếu tố nhân đều không tăng). Vì vậy, di chuyển `phai` vào trong khi nó là vách cao hơn **chắc chắn không sinh ra đáp án tốt hơn** — có thể loại trừ an toàn toàn bộ các cặp `(trai, k)` với `k < phai`. Ngược lại, di chuyển `trai` (vách thấp hơn) **vẫn còn cơ hội** gặp một vách cao hơn `height[phai]`, có thể bù lại phần khoảng cách bị mất bằng chiều cao lớn hơn.

**Độ phức tạp:** giống hệt lý luận mục 3 — mỗi bước đúng một con trỏ di chuyển vào 1 bước, khoảng cách `phai - trai` giảm đúng 1 mỗi lần, tổng số bước tối đa `n - 1`. Mỗi bước làm O(1) việc. Tổng: **O(n)** thời gian, O(1) bộ nhớ phụ — so với brute-force thử mọi cặp vách là O(n²).

**Điểm cốt lõi (liên hệ lại mục 8):** bài này được nhận diện là Two Pointers nhờ dấu hiệu "hai đầu tiến vào nhau dựa trên so sánh giá trị hiện tại" (giống mục 2), **không** phải Sliding Window dù khái niệm "khung giữa hai vách" nghe giống "đoạn con liên tiếp" — điểm khác biệt: Sliding Window luôn xét **đoạn liên tiếp về chỉ số** (mọi phần tử giữa `trai` và `phai` đều thuộc khung), còn ở bài này, các vách **nằm giữa** `trai` và `phai` không đóng vai trò gì trong công thức diện tích (chỉ hai vách hai đầu quyết định) — đây là dấu hiệu phân biệt Two Pointers "tối ưu một cặp" với Sliding Window "tổng hợp toàn bộ đoạn".

---

## 10. Cảnh báo: không phải bài nào cũng áp dụng được — ví dụ cụ thể

Two Pointers và Sliding Window **không phải công cụ vạn năng**. Cả hai đều dựa vào một tính chất ngầm: có thể **suy ra hướng di chuyển đúng** từ trạng thái hiện tại mà không cần thử lại các khả năng đã loại bỏ (tính đơn điệu, hoặc "mở rộng/co khung không cần xét lại phần đã qua"). Khi bài toán **không có** tính chất đó, hai pattern này không áp dụng được.

!!! danger "Ví dụ cụ thể: đếm SỐ CẶP có tích là số chính phương — không có tính đơn điệu"
    Cho một mảng số nguyên **chưa sắp xếp** (và giả sử đề bài **cấm sắp xếp lại** vì cần giữ chỉ số gốc để trả về vị trí cặp), đếm số cặp `(i, j)` với `i < j` sao cho `mang[i] * mang[j]` là số chính phương.

    ```csharp title="Đếm cặp tích là số chính phương — PHẢI duyệt mọi cặp, không có 'hướng đúng' để suy ra"
    // test:run
    bool LaSoChinhPhuong(long x)
    {
        if (x < 0) return false;
        long r = (long)Math.Sqrt(x);
        return r * r == x || (r + 1) * (r + 1) == x;
    }

    int DemCap(int[] mang)
    {
        int dem = 0;
        for (int i = 0; i < mang.Length; i++)
        {
            for (int j = i + 1; j < mang.Length; j++)   // PHẢI xét mọi cặp — không thể bỏ qua cặp nào
            {
                if (LaSoChinhPhuong((long)mang[i] * mang[j])) dem++;
            }
        }
        return dem;
    }

    Console.WriteLine(DemCap(new[] { 1, 4, 9, 3, 16 }));   // các cặp (1,4)(1,9)(1,16)(4,9)(4,16)(9,16) đều là chính phương -> 6
    ```

    **Vì sao Two Pointers không áp dụng được ở đây:** Two Pointers cần lý luận kiểu "nếu tổng nhỏ hơn đích, chắc chắn không cần thử lại các cặp nhỏ hơn nữa" — tức **tăng/giảm một con trỏ phải loại bỏ được một tập khả năng chắc chắn sai**. Với "tích là số chính phương", **không có thứ tự nào** giữa hai phần tử cho biết "cặp này chắc chắn không phải, nên bỏ qua toàn bộ các cặp còn lại có phần tử đó" — tính chất chính phương **không đơn điệu** theo giá trị. Ví dụ `1 × 4 = 4` (chính phương) nhưng `1 × 3 = 3` (không), `1 × 9 = 9` (chính phương) — không có quy luật tăng/giảm rõ ràng để loại trừ. Bài này buộc phải xét **toàn bộ** cặp, giữ nguyên O(n²), hoặc cần một cấu trúc dữ liệu khác hoàn toàn (ví dụ nhóm các số theo "phần không chính phương" sau khi phân tích thừa số nguyên tố — nằm ngoài phạm vi chương này).

### 10.1 Bảng tổng kết toàn chương: mọi kỹ thuật đã học và độ phức tạp

Sau khi đã đi qua toàn bộ các biến thể (mục 2-9) và biết rõ giới hạn áp dụng (mục 10), bảng dưới tổng hợp lại toàn bộ để tiện tra cứu khi ôn tập:

| Kỹ thuật | Điều kiện áp dụng | Cơ chế di chuyển | Big-O thời gian | Big-O bộ nhớ phụ | Ví dụ trong chương |
|---|---|---|---|---|---|
| Two Pointers hai đầu | Dữ liệu đã sắp xếp (hoặc có tính đối xứng) | `trai`/`phai` tiến vào nhau | O(n) | O(1) | Mục 2 (tổng = X), Bài tập 1 (palindrome), mục 9 (container) |
| Two Pointers cùng hướng | Dữ liệu đã sắp xếp (cho bài xoá trùng lặp); không bắt buộc sắp xếp cho bài dồn số 0 | Con trỏ nhanh dò, con trỏ chậm giữ vị trí ghi | O(n) | O(1) | Mục 3.1 (xoá trùng lặp), Bài tập 3 (dồn số 0) |
| Sliding Window độ dài cố định | Có số `k` cố định cho trước | Trượt: thêm 1 phần tử phải, bỏ 1 phần tử trái | O(n) | O(1) | Mục 4 (tổng lớn nhất k phần tử) |
| Sliding Window độ dài thay đổi | Cần đoạn con liên tiếp thoả điều kiện, không biết trước độ dài | Mở rộng phải khi hợp lệ, co trái khi cần | O(n) amortized | O(k) — k = kích thước cấu trúc theo dõi trạng thái khung | Mục 6 (không lặp ký tự), Bài tập 2 (tổng >= target) |

**Điểm cốt lõi khi ôn tập:** mọi kỹ thuật trong bảng trên đều đạt **O(n)** thời gian — cùng một tầm mức tối ưu, khác nhau ở **điều kiện áp dụng** và **cơ chế di chuyển cụ thể**. Khi ôn thi, không cần nhớ máy móc từng bài, mà nhớ **điều kiện áp dụng** ở cột 2 để tự suy luận cơ chế phù hợp cho bài mới.

---

## Cạm bẫy khi phỏng vấn

- **Áp Two Pointers "tiến vào nhau" cho mảng chưa sắp xếp.** Như đã chứng minh ở mục 3, cách này có thể **bỏ sót đáp án đúng** một cách âm thầm (không lỗi, chỉ trả về sai) — luôn xác nhận dữ liệu đã sắp xếp trước khi dùng biến thể Two Pointers hai đầu.

- **Nhầm "phải sắp xếp trước" làm mất thông tin cần giữ.** Nếu đề bài cần trả về **chỉ số gốc** (không phải giá trị), sắp xếp lại mảng sẽ làm mất chỉ số ban đầu — phải sắp xếp một mảng cặp `(giá trị, chỉ số gốc)` thay vì sắp xếp trực tiếp mảng giá trị.

- **Sliding Window độ dài cố định nhưng quên trừ phần tử cũ.** Nếu chỉ viết `tongHienTai += mang[i];` mà quên dòng `tongHienTai -= mang[i - k];`, khung sẽ "phình" ra thay vì "trượt", cho tổng sai (lớn hơn thực tế) — đây là lỗi phổ biến nhất khi mới học Sliding Window cố định.

- **Sliding Window độ dài thay đổi nhưng dùng `if` thay cho `while` khi co khung.** Ở mục 6, nếu viết `if (trongKhung.Contains(chuoi[phai]))` thay cho `while (...)`, khung chỉ co **một bước**, có thể vẫn còn ký tự trùng bên trong khung sau khi co — vì có thể phải loại bỏ **nhiều hơn một** phần tử bên trái để hết trùng. Luôn dùng `while` cho điều kiện co khung, không phải `if`.

- **Nhầm lẫn giữa "biến `trai` chỉ tăng" và Big-O thật.** Nhiều người nhìn vòng lặp lồng nhau trong Sliding Window thay đổi và vội kết luận O(n²) — như đã chứng minh ở mục 7, phải đếm **tổng số lần thực thi của vòng trong cộng dồn toàn hàm**, không phải nhân số lần lặp ngoài với số lần lặp trong tối đa.

- **Áp dụng pattern vào bài không có tính đơn điệu/tính chất "đoạn con liên tiếp".** Như mục 10 đã minh hoạ cụ thể, một số bài (đếm cặp theo tính chất không đơn điệu, tổ hợp không liên tiếp...) buộc phải duyệt toàn bộ hoặc cần cấu trúc dữ liệu khác — cố nhồi Two Pointers/Sliding Window vào sẽ cho code chạy nhưng **sai kết quả**, không phải chỉ chậm.

- **Quên kiểm tra điều kiện biên khi mảng rỗng hoặc `k` lớn hơn độ dài mảng.** Sliding Window độ dài cố định với `k > mang.Length` sẽ vòng lặp đầu (`for i = 0..k`) truy cập chỉ số ngoài phạm vi, ném `IndexOutOfRangeException` — luôn kiểm tra `k <= mang.Length` trước khi chạy.

- **Two Pointers cùng hướng (mục 3.1): nhầm giữa "ghi đè" và "hoán đổi".** Bài "xoá trùng lặp" dùng ghi đè trực tiếp (`mang[cham] = mang[nhanh]`) vì giá trị cũ ở vị trí `cham` không còn cần giữ. Nhưng bài "dồn số 0 về cuối" (bài tập 3) **phải** dùng hoán đổi (swap) vì số `0` bị đẩy đi vẫn cần **tồn tại ở đâu đó** trong mảng kết quả — nếu dùng ghi đè thay vì swap ở bài dồn số 0, giá trị gốc tại vị trí `cham` (có thể khác `0`) sẽ bị mất, không xuất hiện lại ở cuối mảng như yêu cầu.

- **Nhầm điều kiện dừng `trai < phai` với `trai <= phai` trong Two Pointers hai đầu.** Với bài tìm hai số có tổng X (mục 2), điều kiện dừng phải là `trai < phai` (nghiêm ngặt) — nếu viết `trai <= phai`, khi `trai == phai` thuật toán sẽ tính `mang[trai] + mang[trai]` (cùng một phần tử cộng với chính nó hai lần), cho kết quả sai vì bài toán yêu cầu **hai phần tử khác nhau** (khác chỉ số).

---

## Bài tập

### Bài 1 (áp dụng) — Two Pointers: kiểm tra chuỗi đối xứng (palindrome)

Viết hàm kiểm tra một chuỗi có phải palindrome (đọc từ đầu và từ cuối giống nhau) hay không, dùng Two Pointers, không dùng `Reverse()`.

```csharp title="bai1_giandao.cs"
// test:skip giàn giáo cho học viên tự điền
bool LaPalindrome(string s)
{
    int trai = 0, phai = s.Length - 1;
    // TODO: while trai < phai
    //   nếu s[trai] != s[phai] -> return false
    //   ngược lại: trai++, phai--
    return true;
}

Console.WriteLine(LaPalindrome("nhannhan"));   // Kỳ vọng: false (không đối xứng)
Console.WriteLine(LaPalindrome("abcba"));      // Kỳ vọng: true
```

??? success "Lời giải"
    ```csharp title="bai1_loigiai.cs"
    // test:run
    bool LaPalindrome(string s)
    {
        int trai = 0, phai = s.Length - 1;
        while (trai < phai)
        {
            if (s[trai] != s[phai]) return false;
            trai++;
            phai--;
        }
        return true;
    }

    Console.WriteLine(LaPalindrome("nhannhan"));   // False
    Console.WriteLine(LaPalindrome("abcba"));      // True
    Console.WriteLine(LaPalindrome("a"));          // True — chuỗi 1 ký tự luôn đối xứng
    ```
    **Điểm cốt lõi:** đây là Two Pointers dạng "hai đầu tiến vào nhau" nhưng **không cần** mảng đã sắp xếp — vì tính chất khai thác ở đây là **đối xứng của chính chuỗi**, không phải tính đơn điệu của giá trị. Mỗi bước so sánh đúng một cặp đối xứng, dừng ngay khi phát hiện sai lệch — O(n) thời gian, O(1) bộ nhớ phụ.

### Bài 2 (thử thách) — Sliding Window độ dài thay đổi: tổng con nhỏ nhất >= target

Cho một mảng số **dương** và một số `target`, tìm độ dài **nhỏ nhất** của một đoạn con liên tiếp có tổng **lớn hơn hoặc bằng** `target`. Nếu không có đoạn nào thoả, trả về `0`.

```csharp title="bai2_giandao.cs"
// test:skip giàn giáo cho học viên tự điền
int DoDaiNhoNhat(int[] mang, int target)
{
    int trai = 0, tong = 0;
    int doDaiNhoNhat = int.MaxValue;
    // TODO: for phai từ 0 đến mang.Length - 1
    //   tong += mang[phai]  (mở rộng khung sang phải)
    //   while (tong >= target)
    //       cập nhật doDaiNhoNhat = Math.Min(doDaiNhoNhat, phai - trai + 1)
    //       tong -= mang[trai]; trai++;   (co khung từ bên trái)
    return doDaiNhoNhat == int.MaxValue ? 0 : doDaiNhoNhat;
}
```

??? success "Lời giải"
    ```csharp title="bai2_loigiai.cs"
    // test:run
    int DoDaiNhoNhat(int[] mang, int target)
    {
        int trai = 0, tong = 0;
        int doDaiNhoNhat = int.MaxValue;

        for (int phai = 0; phai < mang.Length; phai++)
        {
            tong += mang[phai];                        // mở rộng khung sang phải

            while (tong >= target)                      // khung ĐANG đủ điều kiện -> thử co lại xem còn đủ không
            {
                doDaiNhoNhat = Math.Min(doDaiNhoNhat, phai - trai + 1);
                tong -= mang[trai];
                trai++;                                  // co khung từ bên trái
            }
        }

        return doDaiNhoNhat == int.MaxValue ? 0 : doDaiNhoNhat;
    }

    Console.WriteLine(DoDaiNhoNhat(new[] { 2, 3, 1, 2, 4, 3 }, 7));   // 2  -> đoạn [4,3]
    Console.WriteLine(DoDaiNhoNhat(new[] { 1, 1, 1, 1 }, 10));        // 0  -> không đoạn nào đủ tổng 10
    ```
    **Điểm cốt lõi:** khác bài mục 6 (co khung khi **vi phạm** điều kiện), bài này co khung khi khung **đang thoả** điều kiện, để tìm khung **nhỏ nhất còn thoả** — cùng cơ chế con trỏ trái chỉ tăng, nhưng điều kiện kích hoạt `while` ngược lại. Độ phức tạp vẫn O(n) bằng lý luận amortized giống mục 7: `trai` chỉ tăng, tổng số lần tăng cộng dồn tối đa là `n`.

### Bài 3 (thiết kế) — Two Pointers cùng hướng: dồn số 0 về cuối mảng tại chỗ

Cho một mảng số nguyên, di chuyển tất cả số `0` về **cuối** mảng, giữ nguyên **thứ tự tương đối** của các số khác `0`, thực hiện **tại chỗ** (in-place, không tạo mảng mới). Áp dụng biến thể Two Pointers cùng hướng ở mục 3.1 (con trỏ nhanh dò, con trỏ chậm giữ vị trí ghi).

```csharp title="bai3_giandao.cs"
// test:skip giàn giáo cho học viên tự điền
int[] DonSoKhong(int[] mang)
{
    int cham = 0;   // vị trí ghi tiếp theo cho số KHÁC 0
    // TODO: for nhanh từ 0 đến mang.Length - 1
    //   nếu mang[nhanh] != 0:
    //       hoán đổi mang[cham] và mang[nhanh]
    //       cham++
    return mang;
}

Console.WriteLine(string.Join(",", DonSoKhong(new[] { 0, 1, 0, 3, 12 })));   // Kỳ vọng: 1,3,12,0,0
```

??? success "Lời giải"
    ```csharp title="bai3_loigiai.cs"
    // test:run
    int[] DonSoKhong(int[] mang)
    {
        int cham = 0;
        for (int nhanh = 0; nhanh < mang.Length; nhanh++)
        {
            if (mang[nhanh] != 0)
            {
                (mang[cham], mang[nhanh]) = (mang[nhanh], mang[cham]);   // hoán đổi tại chỗ
                cham++;
            }
        }
        return mang;
    }

    Console.WriteLine(string.Join(",", DonSoKhong(new[] { 0, 1, 0, 3, 12 })));   // 1,3,12,0,0
    Console.WriteLine(string.Join(",", DonSoKhong(new[] { 0, 0, 1 })));          // 1,0,0
    ```
    **Điểm cốt lõi:** đây là biến thể của mục 3.1 nhưng dùng **hoán đổi (swap)** thay vì **ghi đè trực tiếp** — vì bài toán yêu cầu giữ nguyên các số `0` ở đâu đó trong mảng (không xoá hẳn như bài "xoá trùng lặp"), swap đảm bảo số `0` bị "đẩy" dần về sau mà không mất giá trị nào. Con trỏ `cham` chỉ tăng khi gặp số khác `0` — đúng cơ chế "con trỏ chậm giữ vị trí hợp lệ cuối" của Two Pointers cùng hướng. Độ phức tạp: O(n) thời gian (một vòng `for` duy nhất), O(1) bộ nhớ phụ (chỉ hoán đổi tại chỗ).

---

## Tự kiểm tra

Trả lời rồi mở đáp án.

1. **interview-patterns-q1.** Vì sao Two Pointers kiểu "hai đầu tiến vào nhau" chỉ dùng đúng được trên dữ liệu đã sắp xếp?

    ??? note "Đáp án"
        Vì lý luận "nếu tổng nhỏ hơn đích thì tăng con trỏ trái" chỉ đúng khi giá trị tăng dần theo chỉ số (tính đơn điệu) — nhờ đó suy ra chắc chắn không cặp nào ở "phía đã loại" có thể là đáp án. Với mảng chưa sắp xếp, không có quy luật đơn điệu này, di chuyển con trỏ có thể bỏ sót đáp án đúng (xem ví dụ `[1,2,3,4,6,5]` tìm tổng 10 ở mục 3, bỏ sót cặp `4+6`).

2. **interview-patterns-q2.** Two Pointers trong bài tìm hai số có tổng X có độ phức tạp thời gian và bộ nhớ phụ là gì, và vì sao?

    ??? note "Đáp án"
        O(n) thời gian, O(1) bộ nhớ phụ. Vì mỗi bước, khoảng cách giữa hai con trỏ `phai - trai` giảm đúng 1 (chỉ một con trỏ di chuyển mỗi lần), nên tổng số bước tối đa là `n - 1`; không cấp phát cấu trúc dữ liệu phụ nào, chỉ hai biến chỉ số.

3. **interview-patterns-q3.** Sliding Window độ dài cố định và độ dài thay đổi khác nhau ở điểm cốt lõi nào?

    ??? note "Đáp án"
        Độ dài cố định: khung luôn giữ đúng `k` phần tử, mỗi bước thêm đúng 1 phần tử mới và bỏ đúng 1 phần tử cũ (trượt thuần). Độ dài thay đổi: khung tự mở rộng (biên phải tiến) khi còn hợp lệ và tự co lại (biên trái tiến) khi vi phạm điều kiện — không có `k` cố định, kích thước khung phụ thuộc dữ liệu thực tế.

4. **interview-patterns-q4.** Vì sao Sliding Window độ dài thay đổi (mục 6, 7) vẫn là O(n) dù có vòng `for` lồng vòng `while`?

    ??? note "Đáp án"
        Vì biến `trai` (điều khiển vòng `while`) chỉ **tăng, không bao giờ giảm**, trong suốt toàn bộ hàm. Tổng số lần `trai++` được thực thi — cộng dồn qua tất cả các lần lặp của vòng `for` bên ngoài — tối đa là `n` (vì `trai` chỉ đi từ 0 đến tối đa `n-1`). Đây là phân tích khấu hao (amortized analysis): không nhân số lần lặp ngoài với số lần lặp trong tối đa, mà đếm tổng thực thi của vòng trong trên toàn hàm.

5. **interview-patterns-q5.** Dấu hiệu nào trong đề bài gợi ý nên nghĩ tới Sliding Window thay vì Two Pointers?

    ??? note "Đáp án"
        Đề bài hỏi về một **đoạn con liên tiếp** (subarray) hoặc **chuỗi con liên tiếp** (substring) với một điều kiện cần thoả (tổng, độ dài, số ký tự khác nhau...) — vì đoạn con liên tiếp có thể "trượt" (thêm/bớt một đầu) mà không cần tính lại cả đoạn từ đầu. Two Pointers thường gợi ý bởi dữ liệu đã sắp xếp hoặc có tính đối xứng.

6. **interview-patterns-q6.** Cho bài "đếm số cặp có tích là số chính phương" trên mảng chưa sắp xếp (mục 10) — vì sao Two Pointers không áp dụng được, dù đề bài liên quan đến "cặp số"?

    ??? note "Đáp án"
        Vì tính chất "tích là số chính phương" **không đơn điệu** theo giá trị — không có quy luật nào cho biết "nếu cặp này không phải, thì tăng/giảm con trỏ sẽ chắc chắn loại được một tập cặp sai khác". Two Pointers cần khả năng suy ra hướng di chuyển đúng dựa trên so sánh; thiếu tính đơn điệu này, không thể loại trừ được cặp nào mà không thử — buộc phải duyệt toàn bộ O(n²).

7. **interview-patterns-q7.** Trong Sliding Window độ dài cố định (mục 4), công thức `tongHienTai += mang[i]; tongHienTai -= mang[i-k];` thể hiện điều gì về mối quan hệ giữa khung mới và khung cũ?

    ??? note "Đáp án"
        Thể hiện rằng khung mới (kết thúc tại `i`) và khung cũ (kết thúc tại `i-1`) **chồng lấp đúng `k-1` phần tử** — chỉ khác nhau đúng một phần tử ở mỗi đầu (`mang[i]` mới thêm vào, `mang[i-k]` bị loại ra). Nhờ đó tổng mới tính được từ tổng cũ bằng O(1) thay vì cộng lại toàn bộ `k` phần tử.

8. **interview-patterns-q8.** Bài tập 2 (tổng con nhỏ nhất >= target) co khung khi nào, và điều này khác gì so với ví dụ "đoạn dài nhất không lặp ký tự" ở mục 6?

    ??? note "Đáp án"
        Bài tập 2 co khung khi khung **đang thoả** điều kiện (`tong >= target`), để tìm khung nhỏ nhất còn thoả. Ví dụ mục 6 co khung khi khung **vi phạm** điều kiện (có ký tự lặp), để khôi phục tính hợp lệ. Cùng cơ chế con trỏ trái chỉ tăng và cùng độ phức tạp O(n) amortized, nhưng điều kiện kích hoạt vòng co khung ngược nhau tuỳ mục tiêu bài toán (tìm nhỏ nhất thoả vs tìm lớn nhất còn hợp lệ).

9. **interview-patterns-q9.** Two Pointers "cùng hướng" (mục 3.1) khác Two Pointers "hai đầu tiến vào nhau" (mục 2) ở điểm nào, và vì sao vẫn được xếp vào cùng họ pattern?

    ??? note "Đáp án"
        Khác biệt: hai đầu tiến vào nhau (mục 2) bắt đầu từ hai phía đối lập của mảng và tiến **vào giữa**; cùng hướng (mục 3.1) cả hai con trỏ bắt đầu gần nhau (thường cùng từ đầu mảng) và đi theo **cùng một chiều** với tốc độ/vai trò khác nhau (một dò, một giữ vị trí ghi). Vẫn cùng họ pattern vì cả hai đều dùng **hai biến chỉ số duyệt qua mảng một lần**, và mỗi bước di chuyển đều dựa trên **so sánh giá trị hiện tại** — cùng nguyên lý cốt lõi, chỉ khác hướng xuất phát và vai trò của từng con trỏ.

10. **interview-patterns-q10.** Trong bài "xoá trùng lặp tại chỗ" (mục 3.1), vì sao thuật toán chỉ so sánh `mang[nhanh]` với `mang[cham]` (giá trị hợp lệ gần nhất) mà không cần so sánh với mọi giá trị đã giữ trước đó?

    ??? note "Đáp án"
        Vì mảng **đã sắp xếp** — mọi giá trị trùng nhau chắc chắn **nằm liền kề nhau** trong mảng đã sắp xếp. Do đó nếu `mang[nhanh]` khác giá trị hợp lệ gần nhất (`mang[cham]`), nó chắc chắn khác mọi giá trị hợp lệ đã giữ trước đó (vì tất cả giá trị nhỏ hơn `mang[cham]` đã được xử lý và mảng không giảm). Với mảng chưa sắp xếp, giả định này sai — như ví dụ `[1,2,1,3]` ở mục 3.1 cho thấy.

11. **interview-patterns-q11.** Trong bài Container With Most Water (mục 9), vì sao luôn di chuyển con trỏ tại vách **thấp hơn**, không phải vách cao hơn?

    ??? note "Đáp án"
        Vì diện tích bị giới hạn bởi vách thấp hơn (`min(height[trai], height[phai])`). Nếu di chuyển con trỏ tại vách **cao hơn** vào trong, khoảng cách giảm nhưng chiều cao giới hạn vẫn không thể vượt quá vách thấp hơn hiện tại (vì vách thấp hơn không đổi) — diện tích chắc chắn không tăng, có thể loại trừ an toàn. Di chuyển con trỏ tại vách **thấp hơn** mới có cơ hội gặp một vách khác cao hơn, có thể bù lại phần khoảng cách mất đi.

---

??? abstract "DEEP DIVE — Biến thể mở rộng và liên hệ với các pattern khác"
    **Two Pointers cùng hướng (fast/slow pointer) — biến thể khác "hai đầu tiến vào nhau".** Ngoài dạng "trái/phải tiến vào nhau" ở chương này, còn một dạng khác gọi là "fast/slow pointer" (con trỏ nhanh/chậm), cả hai đi **cùng hướng** nhưng tốc độ khác nhau — ví dụ con trỏ nhanh đi 2 bước mỗi lần, con trỏ chậm đi 1 bước, dùng để phát hiện cycle trong linked list (thuật toán Floyd) hoặc tìm điểm giữa danh sách trong một lần duyệt. Về bản chất vẫn là "hai biến chỉ số, di chuyển có chủ đích" — cùng tinh thần Two Pointers nhưng cơ chế di chuyển khác. Biến thể "một dò một giữ" ở mục 3.1 (xoá trùng lặp, dồn số 0) là một dạng fast/slow pointer khác nữa — tốc độ khác nhau ở đây không phải "số bước mỗi lần" mà là "điều kiện để được phép tiến".

    **Mở rộng Two Pointers thành ba con trỏ: bài 3Sum (tìm ba số có tổng bằng 0).** Kỹ thuật Two Pointers ở mục 2 giải bài "hai số có tổng X" trong O(n) (trên dữ liệu đã sắp xếp). Bài "tìm ba số có tổng bằng 0" (3Sum) mở rộng tự nhiên: sắp xếp mảng, sau đó **cố định** một chỉ số `i` (vòng lặp ngoài chạy `n` lần), rồi áp dụng Two Pointers hai đầu cho **phần còn lại** của mảng (từ `i+1` đến cuối) để tìm cặp có tổng bằng `-mang[i]`. Vì mỗi lần Two Pointers bên trong tốn O(n), tổng độ phức tạp là O(n) × O(n) = O(n²) — vẫn nhanh hơn brute-force ba vòng lặp lồng nhau O(n³) đúng một bậc, nhờ tận dụng Two Pointers cho hai chỉ số trong cùng.

    ```csharp title="DEEP DIVE: 3Sum — cố định 1 chỉ số, Two Pointers cho 2 chỉ số còn lại, O(n^2)"
    // test:run
    List<(int, int, int)> BaSoTongZero(int[] mangGoc)
    {
        var mang = (int[])mangGoc.Clone();
        Array.Sort(mang);                         // Two Pointers CẦN dữ liệu đã sắp xếp
        var ketQua = new List<(int, int, int)>();

        for (int i = 0; i < mang.Length; i++)
        {
            if (i > 0 && mang[i] == mang[i - 1]) continue;   // bỏ qua trùng lặp cho chỉ số cố định

            int trai = i + 1, phai = mang.Length - 1;
            while (trai < phai)
            {
                int tong = mang[i] + mang[trai] + mang[phai];
                if (tong == 0)
                {
                    ketQua.Add((mang[i], mang[trai], mang[phai]));
                    trai++;
                    phai--;
                    while (trai < phai && mang[trai] == mang[trai - 1]) trai++;   // bỏ qua trùng lặp
                }
                else if (tong < 0) trai++;
                else phai--;
            }
        }
        return ketQua;
    }

    foreach (var (a, b, c) in BaSoTongZero(new[] { -1, 0, 1, 2, -1, -4 }))
        Console.WriteLine($"({a}, {b}, {c})");
    // (-1, -1, 2)
    // (-1, 0, 1)
    ```

    Điểm cốt lõi: mỗi giá trị `i` biến bài toán 3 số thành bài toán **2 số** (đã giải ở mục 2), cho thấy Two Pointers không chỉ là một thuật toán độc lập mà còn là một "khối xây dựng" (building block) có thể lồng vào trong một vòng lặp ngoài để giải các bài phức tạp hơn.

    **Sliding Window và Two Pointers có thể kết hợp.** Container With Most Water (mục 9) dùng đúng cơ chế hai con trỏ tiến vào nhau của Two Pointers, nhưng mục tiêu là tối ưu một "khung" giữa hai con trỏ (diện tích, không phải tổng) — cho thấy ranh giới giữa hai pattern không tuyệt đối, mà là cùng một họ kỹ thuật "duyệt thông minh bằng chỉ số" áp dụng vào các mục tiêu khác nhau.

    **Sliding Window với cấu trúc dữ liệu phụ phức tạp hơn HashSet.** Bài "đoạn con dài nhất không lặp ký tự" (mục 6) dùng `HashSet<char>`, nhưng nhiều biến thể thực tế cần `Dictionary<char, int>` (đếm số lần xuất hiện, không chỉ có/không) — ví dụ "đoạn con nhỏ nhất chứa tất cả ký tự của một chuỗi mẫu" cần đếm chính xác số lượng mỗi ký tự trong khung, so khớp với số lượng cần trong chuỗi mẫu. Cơ chế mở rộng/co khung giữ nguyên O(n) amortized, chỉ đổi cấu trúc dữ liệu theo dõi "trạng thái khung".

    **Sliding Window với số lượng cửa sổ hợp lệ — biến thể "đếm" thay vì "tìm max/min".** Một dạng bài khác không hỏi "đoạn dài nhất/ngắn nhất" mà hỏi "**có bao nhiêu** đoạn con thoả điều kiện" (ví dụ đếm số đoạn con có tổng đúng bằng `k`, với mảng chỉ chứa số dương). Kỹ thuật: với mỗi vị trí `phai`, số đoạn con **kết thúc tại `phai`** thoả điều kiện thường tính được bằng công thức dựa trên vị trí `trai` sau khi co khung — cùng cơ chế mở rộng/co khung của mục 6-7, chỉ đổi phần "làm gì với khung hợp lệ" từ "cập nhật max/min" sang "cộng dồn số lượng". Độ phức tạp vẫn giữ O(n) vì cơ chế con trỏ trái chỉ tăng không đổi.

    **Vì sao các pattern này phổ biến trong phỏng vấn hơn là trong code sản phẩm thực tế.** Two Pointers và Sliding Window tối ưu từ O(n²)/O(n×k) xuống O(n) cho một lớp bài toán hẹp (chủ yếu mảng/chuỗi với tính đơn điệu hoặc đoạn con liên tiếp) — trong code sản phẩm thực tế, phần lớn bài toán tương tự đã có sẵn trong BCL (`Array.Sort`, LINQ) hoặc được giải bằng cấu trúc dữ liệu chuyên dụng hơn (như chương collections cơ bản và chương cấu trúc dữ liệu nâng cao đã đề cập). Giá trị chính của việc học hai pattern này là **rút ngắn thời gian nhận diện hướng giải** trong môi trường phỏng vấn có giới hạn thời gian, không phải để tự viết lại các thuật toán đã có sẵn trong thực tế.

    **Giới hạn của "nhận diện pattern": vì sao vẫn phải tự chứng minh, không chỉ đoán theo cảm giác.** Bảng nhận diện ở mục 8 là công cụ **gợi ý hướng suy nghĩ ban đầu**, không phải quy tắc chắc chắn đúng 100%. Một đề bài có thể chứa từ khoá "đoạn con liên tiếp" nhưng vẫn không giải được bằng Sliding Window nếu điều kiện đánh giá "đoạn này có hợp lệ không" không đơn điệu theo việc mở rộng/co khung (ví dụ điều kiện phụ thuộc vào **giá trị trung vị** của khung, mà thêm/bớt một phần tử không update được trung vị theo O(1)). Luôn tự hỏi "khi mở rộng khung thêm 1 phần tử, hoặc di chuyển 1 con trỏ, tôi có thể cập nhật trạng thái mà KHÔNG cần quét lại toàn bộ khung không" — nếu câu trả lời là không, pattern này không giúp gì, phải tìm hướng khác.

---

**Tiếp theo →** [P10 · System Design cơ bản & Behavioral Interview](system-design-behavioral.md)
