---
tier: core
status: core
owner: core-team
verified_on: "2026-07-05"
dotnet_version: "10.0"
bloom: "Apply"
requires: [p10-ds]
est_minutes_fast: 90
---

# Graph & BFS/DFS

!!! info "Bạn đang ở đây · P10 → node `p10-graph`"
    **Cần trước:** cấu trúc dữ liệu nâng cao (tự cài Node/class, Queue, Stack — xem chương cấu trúc dữ liệu nâng cao).
    **Mở khoá:** tìm đường đi ngắn nhất trong bản đồ/mạng xã hội, phát hiện deadlock (cycle), sắp thứ tự phụ thuộc (topological sort), các bài toán "duyệt mạng" trong phỏng vấn.
    ⏱️ Fast path ~90 phút.

> **Mục tiêu (đo được):** Sau chương này bạn (1) **định nghĩa** được Graph, đỉnh, cạnh, directed vs undirected; (2) **tự cài đặt** hai cách biểu diễn Graph (adjacency list, adjacency matrix) và **giải thích** khi nào dùng loại nào; (3) **tự viết** BFS bằng Queue để tìm đường đi ngắn nhất theo số cạnh trong graph không trọng số; (4) **tự viết** DFS bằng đệ quy/Stack và **dùng DFS phát hiện cycle**; (5) **tính đúng** độ phức tạp O(V+E) cho cả BFS và DFS.

---

## 0. Đoán nhanh trước khi học (60 giây)

Đọc và **tự đoán output** trước khi mở đáp án.

```csharp title="Đoán output"
// test:run
var ke = new Dictionary<int, List<int>>
{
    [1] = new List<int> { 2, 3 },
    [2] = new List<int> { 4 },
    [3] = new List<int> { 4 },
    [4] = new List<int>(),
};

// Duyệt theo Queue (FIFO), bắt đầu từ 1
var hang = new Queue<int>();
var daThay = new HashSet<int> { 1 };
hang.Enqueue(1);
var thuTu = new List<int>();

while (hang.Count > 0)
{
    var dinh = hang.Dequeue();
    thuTu.Add(dinh);
    foreach (var hangXom in ke[dinh])
    {
        if (daThay.Add(hangXom)) hang.Enqueue(hangXom);
    }
}

Console.WriteLine(string.Join(",", thuTu));   // thứ tự nào?
```

??? note "Đáp án — mở SAU khi đã đoán"
    In ra **`1,2,3,4`**. Đây chính là BFS: xuất phát từ đỉnh `1`, thăm hết các "hàng xóm trực tiếp" của `1` (là `2` và `3`) trước, rồi mới đến hàng xóm của hàng xóm (`4`, xuất hiện từ cả `2` và `3` nhưng chỉ vào Queue **một lần** nhờ `HashSet daThay`). Đặc điểm này — thăm **theo từng lớp** tính từ điểm xuất phát — là lý do BFS luôn tìm ra đường đi có **số cạnh ít nhất** trong graph không trọng số. Mục 4 sẽ mổ xẻ kỹ hơn.

---

## 1. Graph là gì

Graph (đồ thị) là một cấu trúc dữ liệu gồm **tập đỉnh (vertex/node)** và **tập cạnh (edge)** nối các đỉnh đó lại với nhau, không nhất thiết có thứ tự hay cấp bậc như cây (tree).

Nói cách khác: cây là graph đặc biệt (không có chu trình, có một gốc); còn graph nói chung thì "phẳng" hơn — bất kỳ đỉnh nào cũng có thể nối tới bất kỳ đỉnh nào, kể cả tạo thành vòng.

Ví dụ thực tế:

- **Mạng xã hội:** mỗi người là một đỉnh, mỗi quan hệ "bạn bè"/"theo dõi" là một cạnh.
- **Bản đồ đường đi:** mỗi giao lộ/thành phố là một đỉnh, mỗi đoạn đường là một cạnh.
- **Sơ đồ phụ thuộc package:** mỗi package là một đỉnh, "A cần B" là một cạnh có hướng từ A tới B.

```csharp title="Graph tối thiểu: 4 đỉnh, 3 cạnh, chỉ để hình dung"
// test:run
// Đỉnh: 1 (Hà Nội), 2 (Hải Phòng), 3 (Nam Định), 4 (Ninh Bình)
// Cạnh: 1-2, 1-3, 3-4  (đường nối trực tiếp giữa các tỉnh)
var canh = new List<(int Tu, int Den)>
{
    (1, 2),
    (1, 3),
    (3, 4),
};

Console.WriteLine($"Số đỉnh liên quan: 4, số cạnh: {canh.Count}");   // Số đỉnh liên quan: 4, số cạnh: 3
```

**Độ phức tạp của chính khái niệm này:** Graph không phải một "thao tác", nên không có Big-O riêng. Nhưng mọi thuật toán trên Graph đều được đo theo **hai tham số**: `V` = số đỉnh (vertex), `E` = số cạnh (edge). Mục 4 và 5 sẽ dùng lại đúng hai ký hiệu này.

### 1.1 Directed vs Undirected — cạnh có hướng hay không

**Undirected graph** (đồ thị vô hướng) là graph mà mỗi cạnh **đi được hai chiều**: nếu có cạnh nối A và B thì đi từ A sang B được, và từ B sang A cũng được — giống một con đường hai chiều.

**Directed graph** (đồ thị có hướng, hay "digraph") là graph mà mỗi cạnh **chỉ đi được một chiều đã quy định**: cạnh từ A tới B **không** đồng nghĩa có cạnh từ B tới A — giống một đường một chiều.

```csharp title="Undirected: bạn bè trên Facebook (A-B thì B-A cũng đúng)"
// test:run
var banBe = new Dictionary<string, List<string>>
{
    ["An"] = new List<string> { "Binh" },
    ["Binh"] = new List<string> { "An" },   // phải khai báo NGƯỢC LẠI thủ công
};

Console.WriteLine(banBe["An"].Contains("Binh"));    // True
Console.WriteLine(banBe["Binh"].Contains("An"));    // True — undirected: cả hai chiều đều có
```

```csharp title="Directed: A theo dõi B trên Twitter/X (A->B không suy ra B->A)"
// test:run
var theoDoi = new Dictionary<string, List<string>>
{
    ["An"] = new List<string> { "Binh" },   // An theo dõi Binh
    ["Binh"] = new List<string>(),          // Binh KHÔNG theo dõi An
};

Console.WriteLine(theoDoi["An"].Contains("Binh"));     // True  — An -> Binh
Console.WriteLine(theoDoi["Binh"].Contains("An"));     // False — Binh -/-> An
```

**Điểm cốt lõi:** với undirected graph khi cài bằng adjacency list, mỗi cạnh `(u, v)` bạn phải **tự thêm hai lần** — cả `u -> v` và `v -> u` — vì bản thân cấu trúc dữ liệu không tự biết cạnh đó "hai chiều". Quên bước này là lỗi kinh điển khi cài undirected graph.

---

## 2. Biểu diễn Graph trong code: Adjacency List

Adjacency list (danh sách kề) là cách biểu diễn graph bằng một **bảng ánh xạ mỗi đỉnh tới danh sách các đỉnh mà nó nối trực tiếp tới** — thường viết bằng `Dictionary<int, List<int>>`.

```csharp title="Adjacency list tối thiểu"
// test:run
var ke = new Dictionary<int, List<int>>
{
    [1] = new List<int> { 2, 3 },   // đỉnh 1 nối tới 2 và 3
    [2] = new List<int> { 4 },      // đỉnh 2 nối tới 4
    [3] = new List<int> { 4 },      // đỉnh 3 nối tới 4
    [4] = new List<int>(),          // đỉnh 4 không nối đi đâu (nhưng vẫn tồn tại)
};

foreach (var hangXom in ke[1])
{
    Console.WriteLine($"1 -> {hangXom}");   // 1 -> 2   rồi   1 -> 3
}
```

**Độ phức tạp:** với adjacency list, tra "1 nối tới ai" là O(1) để lấy ra `List<int>` (tra `Dictionary`), rồi O(deg(v)) để duyệt hết hàng xóm của đỉnh đó (`deg(v)` = số cạnh xuất phát từ `v`, gọi là "bậc" của đỉnh). Kiểm tra "có cạnh cụ thể `u -> v` hay không" là O(deg(u)) vì phải quét `List<int>` của `u` (không có chỉ số để nhảy thẳng tới). Bộ nhớ dùng: O(V + E) — chỉ lưu đúng những cạnh **thực sự tồn tại**.

## 3. Biểu diễn Graph trong code: Adjacency Matrix

Adjacency matrix (ma trận kề) là cách biểu diễn graph bằng một **mảng hai chiều kích thước V×V**, trong đó ô `[u, v]` cho biết có cạnh từ `u` tới `v` hay không (thường là `1`/`0` hoặc `true`/`false`).

```csharp title="Adjacency matrix tối thiểu"
// test:run
int v = 5;   // 5 đỉnh, đánh số 0..4
var matrix = new bool[v, v];

matrix[1, 2] = true;   // cạnh 1 -> 2
matrix[1, 3] = true;   // cạnh 1 -> 3
matrix[3, 4] = true;   // cạnh 3 -> 4

Console.WriteLine(matrix[1, 2]);   // True  — có cạnh
Console.WriteLine(matrix[2, 1]);   // False — directed: chiều ngược lại không tự có
```

**Độ phức tạp:** kiểm tra "có cạnh `u -> v` hay không" là O(1) tuyệt đối — chỉ đọc thẳng ô `matrix[u, v]`, không cần quét gì. Nhưng duyệt "tất cả hàng xóm của `u`" luôn là O(V) — phải quét hết cả một dòng dù đỉnh đó chỉ nối với 1 hàng xóm hay 1000 hàng xóm. Bộ nhớ dùng: O(V²) **cố định**, bất kể graph có bao nhiêu cạnh thật.

### 3.1 Khi nào dùng adjacency list, khi nào dùng adjacency matrix

Bây giờ cả hai cách biểu diễn đã được định nghĩa riêng — mới có thể so sánh an toàn.

Trước khi vào bảng, hai từ khoá sẽ dùng: graph **thưa** (sparse) là graph có số cạnh `E` nhỏ hơn nhiều so với `V²` (đa số graph thực tế — mạng xã hội, bản đồ); graph **dày đặc** (dense) là graph có `E` gần bằng `V²` (gần như đỉnh nào cũng nối với đỉnh nào).

| Tiêu chí | Adjacency list | Adjacency matrix |
|---|---|---|
| Bộ nhớ | O(V + E) | O(V²) luôn cố định |
| Kiểm tra cạnh `u→v` cụ thể | O(deg(u)) — phải quét | O(1) — đọc thẳng ô |
| Duyệt hết hàng xóm của `u` | O(deg(u)) — chỉ đúng số hàng xóm thật | O(V) — luôn quét hết cả dòng |
| Phù hợp graph | **Thưa** (sparse): E nhỏ hơn nhiều so với V² — hầu hết graph thực tế (mạng xã hội, bản đồ, dependency) | **Dày đặc** (dense): E gần bằng V², hoặc cần tra cạnh cụ thể liên tục với V nhỏ |

**Quy tắc thực dụng:** mạng xã hội với triệu người dùng nhưng mỗi người chỉ vài trăm bạn là graph **thưa** → adjacency list tiết kiệm bộ nhớ khủng khiếp so với matrix (V² với V = 1 triệu là 10^12 ô, không thể cấp phát). Ngược lại, nếu graph nhỏ (vài trăm đỉnh) và cần tra "có cạnh không" liên tục trong vòng lặp nóng, matrix O(1) tra cạnh có thể nhanh hơn thực tế.

### 3.2 Adjacency matrix cho undirected graph

Với undirected graph, adjacency matrix có một đặc điểm hình học: ma trận **đối xứng** qua đường chéo chính — `matrix[u, v]` luôn bằng `matrix[v, u]`, vì "có đường hai chiều" nghĩa là cả hai ô đều đúng.

```csharp title="Adjacency matrix cho undirected: ghi cả hai ô cho mỗi cạnh"
// test:run
int v = 4;
var matrix = new bool[v, v];

void ThemCanhKhongHuong(int u, int w)
{
    matrix[u, w] = true;
    matrix[w, u] = true;   // undirected -> ghi CẢ HAI ô, khác với directed chỉ ghi một
}

ThemCanhKhongHuong(0, 1);
ThemCanhKhongHuong(1, 2);

Console.WriteLine(matrix[0, 1]);   // True
Console.WriteLine(matrix[1, 0]);   // True — đối xứng, đúng với undirected
Console.WriteLine(matrix[0, 2]);   // False — không có cạnh trực tiếp 0-2
```

**Điểm cốt lõi:** matrix cho undirected graph tốn đúng gấp đôi số ô ghi so với directed graph (mỗi cạnh ghi 2 ô thay vì 1), nhưng tổng dung lượng cấp phát vẫn là O(V²) — không đổi so với directed, vì kích thước ma trận chỉ phụ thuộc V, không phụ thuộc số cạnh thật ghi vào.

---

## 4. BFS — Breadth-First Search

BFS (tìm kiếm theo chiều rộng) là thuật toán duyệt graph dùng **Queue (FIFO)** để thăm các đỉnh **theo từng lớp** — thăm hết mọi đỉnh cách điểm xuất phát 1 cạnh, rồi mới sang lớp cách 2 cạnh, rồi 3 cạnh...

```csharp title="BFS tối thiểu: duyệt và in thứ tự thăm"
// test:run
var ke = new Dictionary<int, List<int>>
{
    [1] = new List<int> { 2, 3 },
    [2] = new List<int> { 1, 4 },
    [3] = new List<int> { 1, 4 },
    [4] = new List<int> { 2, 3 },
};

var hang = new Queue<int>();
var daThay = new HashSet<int> { 1 };
hang.Enqueue(1);

while (hang.Count > 0)
{
    var dinh = hang.Dequeue();
    Console.Write(dinh + " ");    // 1 2 3 4
    foreach (var hangXom in ke[dinh])
    {
        if (daThay.Add(hangXom)) hang.Enqueue(hangXom);
    }
}
```

Vì sao dùng Queue mà không dùng List thường: Queue đảm bảo **đỉnh nào được thêm vào trước thì được xử lý trước** (FIFO — First In First Out). Đó chính là cơ chế bắt buộc để duyệt "theo từng lớp": tất cả đỉnh của lớp hiện tại phải được xử lý xong (và các hàng xóm của chúng được xếp hàng) trước khi lớp tiếp theo bắt đầu.

### 4.1 BFS tìm đường đi ngắn nhất theo số cạnh

Vì BFS thăm theo từng lớp tính từ điểm xuất phát, đỉnh nào được thăm ở "lớp thứ k" chắc chắn cách điểm xuất phát đúng k cạnh theo đường ngắn nhất — không có đường nào ngắn hơn, vì nếu có, BFS đã thăm đỉnh đó ở lớp sớm hơn rồi.

```csharp title="BFS tìm đường đi ngắn nhất (số cạnh) từ 1 tới mọi đỉnh"
// test:run
var ke = new Dictionary<int, List<int>>
{
    [1] = new List<int> { 2, 3 },
    [2] = new List<int> { 1, 4 },
    [3] = new List<int> { 1, 4 },
    [4] = new List<int> { 2, 3, 5 },
    [5] = new List<int> { 4 },
};

var khoangCach = new Dictionary<int, int> { [1] = 0 };   // đỉnh xuất phát cách 0 cạnh
var hang = new Queue<int>();
hang.Enqueue(1);

while (hang.Count > 0)
{
    var dinh = hang.Dequeue();
    foreach (var hangXom in ke[dinh])
    {
        if (!khoangCach.ContainsKey(hangXom))
        {
            khoangCach[hangXom] = khoangCach[dinh] + 1;   // cách xa hơn đỉnh hiện tại đúng 1
            hang.Enqueue(hangXom);
        }
    }
}

Console.WriteLine(khoangCach[5]);   // 3  — đường ngắn nhất 1 -> 3 -> 4 -> 5 (hoặc 1 -> 2 -> 4 -> 5), đều 3 cạnh
Console.WriteLine(khoangCach[4]);   // 2
```

**Lưu ý bắt buộc:** BFS chỉ tìm đúng đường **ngắn nhất theo số cạnh** khi graph **không có trọng số** (mọi cạnh coi như "giá" bằng nhau). Nếu các cạnh có trọng số khác nhau (ví dụ khoảng cách km), BFS sai — phải dùng Dijkstra (thuộc chương thuật toán đồ thị có trọng số, không thuộc phạm vi chương này).

### 4.2 Độ phức tạp BFS

BFS ghé **mỗi đỉnh đúng một lần** (nhờ `daThay`/`khoangCach` chặn lặp lại) — đóng góp O(V). Với mỗi đỉnh được ghé, BFS quét **toàn bộ danh sách kề** của đỉnh đó để tìm hàng xóm chưa thăm — tổng cộng trên toàn bộ graph, tổng số lần quét này bằng tổng bậc của mọi đỉnh, tức O(E) (mỗi cạnh được xét tối đa 2 lần với undirected, 1 lần với directed — cả hai đều là hằng số nên vẫn O(E)). Tổng lại: **O(V + E)**.

---

## 5. DFS — Depth-First Search

DFS (tìm kiếm theo chiều sâu) là thuật toán duyệt graph đi **hết một nhánh tới cùng** trước khi lùi lại thử nhánh khác — cài bằng **đệ quy** (dùng ngăn xếp gọi hàm có sẵn của ngôn ngữ) hoặc bằng **Stack (LIFO)** tường minh.

```csharp title="DFS tối thiểu bằng đệ quy"
// test:run
var ke = new Dictionary<int, List<int>>
{
    [1] = new List<int> { 2, 3 },
    [2] = new List<int> { 1, 4 },
    [3] = new List<int> { 1, 4 },
    [4] = new List<int> { 2, 3 },
};

var daThay = new HashSet<int>();
DuyetSau(1);

void DuyetSau(int dinh)
{
    if (!daThay.Add(dinh)) return;   // đã thăm rồi -> dừng nhánh này
    Console.Write(dinh + " ");       // 1 2 4 3  (đi sâu hết nhánh qua 2 rồi mới quay lại 3)
    foreach (var hangXom in ke[dinh])
    {
        DuyetSau(hangXom);
    }
}
```

Vì sao dùng đệ quy mà không dùng Queue: mỗi lần gọi `DuyetSau(hangXom)`, hàm hiện tại **bị treo lại** (đẩy vào ngăn xếp gọi hàm của runtime) cho tới khi nhánh sâu hơn xử lý xong mới quay lại xử lý hàng xóm tiếp theo — đúng cơ chế LIFO (Last In First Out) của Stack, chỉ khác là ngăn xếp này do CLR quản lý ngầm thay vì bạn tự khai báo `Stack<T>`.

```csharp title="DFS bằng Stack tường minh (không đệ quy)"
// test:run
var ke = new Dictionary<int, List<int>>
{
    [1] = new List<int> { 2, 3 },
    [2] = new List<int> { 1, 4 },
    [3] = new List<int> { 1, 4 },
    [4] = new List<int> { 2, 3 },
};

var ngan = new Stack<int>();
var daThay = new HashSet<int>();
ngan.Push(1);

while (ngan.Count > 0)
{
    var dinh = ngan.Pop();
    if (!daThay.Add(dinh)) continue;
    Console.Write(dinh + " ");
    foreach (var hangXom in ke[dinh])
    {
        ngan.Push(hangXom);
    }
}
```

**Điểm cốt lõi:** đệ quy và Stack tường minh cho **cùng ý tưởng** (đi sâu trước khi lui) nhưng thứ tự thăm cụ thể có thể khác nhau chút (do thứ tự `Push` các hàng xóm). Đệ quy dễ đọc hơn nhưng có rủi ro `StackOverflowException` nếu graph rất sâu (hàng trăm nghìn đỉnh nối chuỗi); Stack tường minh không có giới hạn độ sâu vì nó chạy trên heap.

### 5.1 Độ phức tạp DFS

Giống lý luận với BFS: mỗi đỉnh được thăm đúng một lần nhờ `daThay` chặn lặp — O(V). Mỗi đỉnh khi được thăm phải quét hết danh sách kề để tìm hàng xóm — tổng lại trên toàn graph là O(E). Tổng: **O(V + E)** — cùng độ phức tạp với BFS, chỉ khác cơ chế duyệt (Queue theo lớp vs Stack/đệ quy theo nhánh).

### 5.2 Dùng DFS phát hiện cycle (chu trình)

Cycle (chu trình) là một đường đi bắt đầu và kết thúc ở **cùng một đỉnh** mà không đi lại cạnh nào hai lần. DFS phát hiện được cycle bằng cách theo dõi các đỉnh **đang nằm trên nhánh đệ quy hiện tại** (chưa lùi ra) — nếu gặp lại một đỉnh đang nằm trên nhánh đó, tức là có đường quay vòng.

```csharp title="DFS phát hiện cycle trong directed graph"
// test:run
var ke = new Dictionary<int, List<int>>
{
    [1] = new List<int> { 2 },
    [2] = new List<int> { 3 },
    [3] = new List<int> { 1 },   // 3 -> 1 tạo vòng: 1 -> 2 -> 3 -> 1
};

var daThayXong = new HashSet<int>();      // đỉnh đã xử lý hoàn tất (lùi ra rồi)
var dangTrenNhanh = new HashSet<int>();   // đỉnh đang nằm trên nhánh đệ quy hiện tại

Console.WriteLine(CoCycle(1));   // True

bool CoCycle(int dinh)
{
    if (dangTrenNhanh.Contains(dinh)) return true;    // gặp lại đỉnh đang trên nhánh -> có vòng
    if (daThayXong.Contains(dinh)) return false;       // đã xử lý xong nhánh này rồi, an toàn

    dangTrenNhanh.Add(dinh);
    foreach (var hangXom in ke[dinh])
    {
        if (CoCycle(hangXom)) return true;
    }
    dangTrenNhanh.Remove(dinh);   // lùi ra khỏi nhánh -> bỏ khỏi tập "đang trên nhánh"
    daThayXong.Add(dinh);
    return false;
}
```

**Điểm cốt lõi:** phải tách **hai tập** — `dangTrenNhanh` (đỉnh trên đường đi hiện tại, từ gốc xuống tới đây, chưa lùi) và `daThayXong` (đỉnh đã xử lý triệt để, không còn liên quan). Nếu chỉ dùng một `HashSet daThay` như DFS thường (mục 5), bạn sẽ báo "có cycle" sai cho graph như `1 -> 2`, `1 -> 3`, `2 -> 4`, `3 -> 4` (đỉnh `4` được thăm hai lần qua hai nhánh khác nhau — không phải cycle, chỉ là hai đường tới cùng một đỉnh). Với **undirected graph**, quy tắc phát hiện cycle khác một chút: phải bỏ qua cạnh quay lại đúng "đỉnh cha" vừa đi tới (vì undirected lưu cả hai chiều `u-v` và `v-u`, nếu không loại trừ cạnh vừa đi qua sẽ luôn báo cycle giả).

---

## 6. BFS vs DFS — khi nào dùng cái nào

Cả hai đã được định nghĩa và cài đặt riêng ở mục 4 và 5 — giờ mới đặt cạnh nhau.

Hai bài toán sẽ nhắc tới trong bảng, chưa gặp trước đây: **thành phần liên thông** — một nhóm đỉnh nối được với nhau nhưng không nối được ra ngoài nhóm (Bài 3 sẽ giải chi tiết); **sắp thứ tự topological** — xếp các đỉnh của graph có hướng không cycle thành một hàng sao cho mọi cạnh `u -> v` đều có `u` đứng trước `v` (ví dụ: thứ tự cài đặt các package phụ thuộc nhau; phần DEEP DIVE cuối bài giải thích cách cài).

| Tiêu chí | BFS | DFS |
|---|---|---|
| Cấu trúc dùng | Queue (FIFO) | Stack (LIFO) hoặc đệ quy |
| Thứ tự thăm | Theo từng lớp, gần trước xa sau | Đi hết một nhánh rồi mới lùi |
| Big-O | O(V + E) | O(V + E) |
| Bộ nhớ đỉnh (worst-case) | O(V) — có thể phải giữ cả một "lớp" rộng trong Queue | O(V) — độ sâu nhánh dài nhất (nếu đệ quy: giới hạn bởi stack thật của CLR) |
| Bài toán phù hợp nhất | Tìm đường đi **ngắn nhất theo số cạnh** trong graph không trọng số | Kiểm tra **tồn tại đường đi**, **phát hiện cycle**, sắp thứ tự topological, tìm thành phần liên thông |

**Quy tắc thực dụng:** câu hỏi có chữ "ngắn nhất"/"ít bước nhất" trong graph không trọng số → nghĩ ngay BFS. Câu hỏi "có đường đi từ A tới B không", "graph này có vòng không", "sắp thứ tự các task theo phụ thuộc" → nghĩ ngay DFS.

### 6.1 Trace từng bước để thấy rõ sự khác biệt

Cùng một graph `1-2, 1-3, 2-4, 3-4` (undirected), xuất phát từ đỉnh `1`. Bảng dưới trace từng bước để thấy BFS và DFS rẽ nhánh khác nhau ra sao dù cùng Big-O.

| Bước | BFS — Queue (nội dung sau bước) | Thứ tự thăm BFS | DFS — Stack/đệ quy (đỉnh đang xử lý) | Thứ tự thăm DFS |
|---|---|---|---|---|
| 1 | `[1]` → dequeue 1, enqueue 2,3 | 1 | gọi `DFS(1)` | 1 |
| 2 | `[2,3]` → dequeue 2, enqueue 4 | 1,2 | `DFS(1)` gọi `DFS(2)` | 1,2 |
| 3 | `[3,4]` → dequeue 3 (4 đã có, không enqueue lại) | 1,2,3 | `DFS(2)` gọi `DFS(4)` | 1,2,4 |
| 4 | `[4]` → dequeue 4 | 1,2,3,4 | `DFS(4)` lùi ra, `DFS(2)` lùi ra, `DFS(1)` gọi `DFS(3)` (3 đã thăm ở nhánh khác? không — thăm mới nếu chưa `daThay`) | 1,2,4,3 |

**Quan sát:** BFS thăm `3` **trước** `4` (vì `3` cùng lớp với `2`, còn `4` ở lớp sau). DFS thăm `4` **trước** `3` (vì đi sâu vào nhánh `1→2→4` tới cùng trước khi quay lại thử nhánh `1→3`). Cả hai đều đúng, đều thăm hết 4 đỉnh, đều O(V+E) — chỉ khác **thứ tự**, và thứ tự đó chính là lý do BFS mới đảm bảo "ngắn nhất".

---

## Cạm bẫy & thực chiến

- **Quên chặn đỉnh đã thăm → vòng lặp vô hạn.** Nếu graph có cycle và bạn không dùng `HashSet daThay` (hoặc tương đương), BFS/DFS sẽ lặp mãi giữa các đỉnh trong vòng, không bao giờ kết thúc. Luôn kiểm tra "đã thăm chưa" **trước khi** enqueue/push, không phải chỉ khi dequeue/pop.

- **Undirected graph chỉ khai báo một chiều.** Khi build adjacency list từ danh sách cạnh `(u, v)` cho undirected graph, quên thêm `ke[v].Add(u)` (chỉ thêm `ke[u].Add(v)`) làm graph "biến thành" directed một cách âm thầm — BFS/DFS từ `v` sẽ không bao giờ thấy `u`, dù trên đề bài là undirected.

- **Lẫn giữa BFS và DFS khi cần đường ngắn nhất.** DFS *cũng* tìm được một đường đi từ A tới B nếu nó tồn tại, nhưng **không đảm bảo đó là đường ngắn nhất** — DFS có thể đi lạc vào một nhánh dài trước khi tình cờ chạm B. Chỉ BFS đảm bảo đường ngắn nhất theo số cạnh trong graph không trọng số.

- **Dùng một `HashSet` duy nhất để phát hiện cycle trong directed graph.** Như đã nói ở mục 5.2, phải tách `dangTrenNhanh` và `daThayXong`; dùng chung một tập sẽ báo cycle giả (false positive) cho graph không có vòng nhưng có nhiều đường tới cùng một đỉnh.

- **Đệ quy DFS trên graph cực sâu → StackOverflowException.** Với input do người dùng kiểm soát được (ví dụ dữ liệu từ API công khai) mà graph có thể có hàng trăm nghìn đỉnh nối thành chuỗi dài, đệ quy có thể làm tràn ngăn xếp gọi hàm thật của CLR. Trường hợp này nên chuyển sang DFS bằng `Stack<T>` tường minh (mục 5), vì stack tường minh nằm trên heap, không bị giới hạn kích thước ngăn xếp gọi hàm.

- **Nhầm O(V+E) thành O(V×E) hoặc O(V²).** BFS/DFS **không** duyệt lại từ đầu cho mỗi đỉnh — mỗi cạnh chỉ được xét một số lần cố định (1 hoặc 2, tuỳ directed/undirected) trong toàn bộ quá trình, không phải mỗi đỉnh quét lại toàn bộ graph. Nếu code của bạn có vòng lặp lồng "với mỗi đỉnh, quét lại tất cả đỉnh khác" thì đó không còn là BFS/DFS chuẩn O(V+E) nữa — rất có thể bạn đang cài sai (ví dụ quên `HashSet` nên phải quét lại).

---

## Bài tập

### Bài 1 (áp dụng) — Đường đi ngắn nhất bằng BFS

Cho adjacency list của một undirected graph 6 đỉnh (1..6): cạnh `(1,2) (1,3) (2,4) (3,4) (4,5) (5,6)`. Viết BFS từ đỉnh `1`, in ra khoảng cách (số cạnh) tới đỉnh `6`.

```csharp title="bai1_giandao.cs"
// test:skip giàn giáo cho học viên tự điền
// TODO: build adjacency list undirected (thêm CẢ HAI chiều cho mỗi cạnh)
// TODO: BFS từ đỉnh 1, lưu Dictionary<int,int> khoangCach
// TODO: in khoangCach[6]
```

??? success "Lời giải"
    ```csharp title="bai1_loigiai.cs"
    // test:run
    var canh = new List<(int, int)> { (1, 2), (1, 3), (2, 4), (3, 4), (4, 5), (5, 6) };
    var ke = new Dictionary<int, List<int>>();
    foreach (var (u, v) in canh)
    {
        if (!ke.ContainsKey(u)) ke[u] = new List<int>();
        if (!ke.ContainsKey(v)) ke[v] = new List<int>();
        ke[u].Add(v);
        ke[v].Add(u);   // undirected -> thêm cả hai chiều
    }

    var khoangCach = new Dictionary<int, int> { [1] = 0 };
    var hang = new Queue<int>();
    hang.Enqueue(1);
    while (hang.Count > 0)
    {
        var dinh = hang.Dequeue();
        foreach (var hx in ke[dinh])
        {
            if (!khoangCach.ContainsKey(hx))
            {
                khoangCach[hx] = khoangCach[dinh] + 1;
                hang.Enqueue(hx);
            }
        }
    }

    Console.WriteLine(khoangCach[6]);   // 4  — đường 1 -> 2 -> 4 -> 5 -> 6 (hoặc qua 3), đều 4 cạnh
    ```
    **Điểm cốt lõi:** undirected graph luôn cần thêm cạnh **hai chiều** lúc build adjacency list; BFS tính khoảng cách bằng công thức `khoangCach[hangXom] = khoangCach[dinh] + 1` ngay lúc lần đầu tiên phát hiện `hangXom`.

### Bài 2 (thiết kế) — Phát hiện cycle trong directed graph

Cho danh sách cạnh có hướng: `(1,2) (2,3) (3,4) (4,2)`. Viết DFS phát hiện cycle, in ra `True`/`False`.

```csharp title="bai2_giandao.cs"
// test:skip giàn giáo cho học viên tự điền
// TODO: build adjacency list directed
// TODO: DFS với hai tập dangTrenNhanh + daThayXong (xem mục 5.2)
// TODO: in kết quả CoCycle từ mọi đỉnh chưa xử lý
```

??? success "Lời giải"
    ```csharp title="bai2_loigiai.cs"
    // test:run
    var canh = new List<(int, int)> { (1, 2), (2, 3), (3, 4), (4, 2) };
    var ke = new Dictionary<int, List<int>>();
    foreach (var (u, v) in canh)
    {
        if (!ke.ContainsKey(u)) ke[u] = new List<int>();
        if (!ke.ContainsKey(v)) ke[v] = new List<int>();
        ke[u].Add(v);
    }

    var dangTrenNhanh = new HashSet<int>();
    var daThayXong = new HashSet<int>();

    bool CoCycle(int dinh)
    {
        if (dangTrenNhanh.Contains(dinh)) return true;
        if (daThayXong.Contains(dinh)) return false;

        dangTrenNhanh.Add(dinh);
        foreach (var hx in ke.GetValueOrDefault(dinh, new List<int>()))
        {
            if (CoCycle(hx)) return true;
        }
        dangTrenNhanh.Remove(dinh);
        daThayXong.Add(dinh);
        return false;
    }

    bool ketQua = false;
    foreach (var dinh in ke.Keys)
    {
        if (CoCycle(dinh)) { ketQua = true; break; }
    }
    Console.WriteLine(ketQua);   // True — vòng 2 -> 3 -> 4 -> 2
    ```
    **Điểm cốt lõi:** phải thử `CoCycle` từ **mọi đỉnh chưa xử lý** (`daThayXong` chưa chứa), vì nếu chỉ gọi từ một đỉnh cố định (ví dụ chỉ từ đỉnh `1`), một cycle nằm ở phần graph không thể tới được từ đỉnh đó sẽ bị bỏ sót.

### Bài 3 (thử thách) — Đếm số thành phần liên thông

Cho undirected graph 7 đỉnh (1..7), cạnh: `(1,2) (2,3) (4,5)` — đỉnh `6` và `7` không nối với ai. Dùng BFS/DFS đếm xem graph có bao nhiêu **thành phần liên thông** (nhóm đỉnh nối được với nhau, không nối được ra ngoài nhóm).

```csharp title="bai3_giandao.cs"
// test:skip giàn giáo cho học viên tự điền
// TODO: build adjacency list undirected cho cả 7 đỉnh (kể cả đỉnh cô lập 6, 7)
// TODO: với mỗi đỉnh CHƯA thăm, chạy BFS/DFS để "tô màu" hết cả nhóm của nó,
//       mỗi lần bắt đầu một nhóm mới -> tăng biến đếm
// TODO: in số nhóm
```

??? success "Lời giải"
    ```csharp title="bai3_loigiai.cs"
    // test:run
    var soDinh = 7;
    var canh = new List<(int, int)> { (1, 2), (2, 3), (4, 5) };
    var ke = new Dictionary<int, List<int>>();
    for (int i = 1; i <= soDinh; i++) ke[i] = new List<int>();   // đảm bảo đỉnh cô lập (6,7) vẫn có mặt
    foreach (var (u, w) in canh)
    {
        ke[u].Add(w);
        ke[w].Add(u);
    }

    var daThay = new HashSet<int>();
    int soNhom = 0;

    for (int dinh = 1; dinh <= soDinh; dinh++)
    {
        if (daThay.Contains(dinh)) continue;   // đã thuộc nhóm xử lý trước đó

        soNhom++;
        var hang = new Queue<int>();
        hang.Enqueue(dinh);
        daThay.Add(dinh);
        while (hang.Count > 0)
        {
            var d = hang.Dequeue();
            foreach (var hx in ke[d])
            {
                if (daThay.Add(hx)) hang.Enqueue(hx);
            }
        }
    }

    Console.WriteLine(soNhom);   // 4 — nhóm {1,2,3}, nhóm {4,5}, nhóm {6}, nhóm {7}
    ```
    **Điểm cốt lõi:** vòng lặp ngoài `for (dinh = 1..soDinh)` là bắt buộc vì một lần BFS/DFS chỉ "tô màu" được **một** thành phần liên thông (nhóm chứa đỉnh xuất phát) — graph có thể gồm nhiều nhóm rời rạc không nối được với nhau, và đỉnh cô lập (không có cạnh nào, như `6`/`7`) vẫn tính là một nhóm riêng có đúng 1 đỉnh.

---

## Tự kiểm tra

Trả lời rồi mở đáp án.

1. Big-O của BFS và DFS trên graph có V đỉnh, E cạnh là gì, và vì sao cả hai giống nhau?

    ??? note "Đáp án"
        Cả hai đều **O(V + E)**. Cả hai thuật toán đều ghé mỗi đỉnh đúng một lần (O(V)) và với mỗi đỉnh phải quét hết danh sách kề để tìm hàng xóm chưa thăm, tổng số lần quét trên toàn graph bằng tổng bậc các đỉnh, tức O(E). Chỉ khác **thứ tự** thăm (theo lớp vs theo nhánh), không khác tổng công việc.

2. Vì sao BFS đảm bảo tìm đường đi ngắn nhất theo số cạnh, còn DFS thì không?

    ??? note "Đáp án"
        BFS thăm đỉnh theo **từng lớp** tính từ điểm xuất phát — mọi đỉnh ở lớp k đã được xác nhận cách xuất phát đúng k cạnh (không có đường nào ngắn hơn, vì nếu có, BFS đã thăm ở lớp sớm hơn). DFS đi sâu theo một nhánh trước, có thể "lạc" vào một đường dài trước khi chạm đích, không có gì đảm bảo đường tìm được là ngắn nhất.

3. Adjacency list và adjacency matrix khác nhau ở điểm nào về bộ nhớ và tốc độ tra cạnh cụ thể?

    ??? note "Đáp án"
        Adjacency list dùng O(V + E) bộ nhớ, tra cạnh cụ thể `u→v` là O(deg(u)) (phải quét). Adjacency matrix dùng O(V²) bộ nhớ cố định, tra cạnh cụ thể là O(1) (đọc thẳng ô). List phù hợp graph thưa (đa số trường hợp thực tế), matrix phù hợp graph dày đặc hoặc cần tra cạnh cụ thể liên tục.

4. Undirected graph khác directed graph ở đâu khi cài bằng adjacency list?

    ??? note "Đáp án"
        Với directed graph, cạnh `u -> v` chỉ thêm một chiều: `ke[u].Add(v)`. Với undirected graph, mỗi cạnh phải thêm **cả hai chiều** thủ công: `ke[u].Add(v)` và `ke[v].Add(u)`, vì cấu trúc dữ liệu không tự hiểu "cạnh hai chiều" — quên một chiều làm undirected graph biến thành directed một cách âm thầm.

5. Vì sao dùng `HashSet daThay` (hoặc tương đương) là bắt buộc trong BFS/DFS, kể cả khi graph không có cycle?

    ??? note "Đáp án"
        Vì một đỉnh có thể được tới từ **nhiều hàng xóm khác nhau** (không cần cycle, chỉ cần hai đường khác nhau cùng dẫn tới nó). Không chặn đỉnh đã thăm sẽ enqueue/push trùng lặp nhiều lần, làm tăng số lần xử lý lên vượt quá O(V+E), và với graph có cycle thật sẽ gây lặp vô hạn.

6. DFS phát hiện cycle trong directed graph cần theo dõi mấy tập đỉnh, và vì sao không thể dùng một tập duy nhất?

    ??? note "Đáp án"
        Cần **hai tập**: `dangTrenNhanh` (đỉnh trên đường đệ quy hiện tại, chưa lùi) và `daThayXong` (đỉnh đã xử lý triệt để). Nếu dùng một tập duy nhất `daThay`, một đỉnh được tới từ hai nhánh khác nhau (không phải cycle) sẽ bị báo nhầm là cycle, vì thuật toán không phân biệt được "đỉnh này đang trên đường đi hiện tại" với "đỉnh này đã xử lý xong từ nhánh khác rồi".

7. Cho bài toán "kiểm tra có tồn tại đường đi từ A tới B trong graph rất lớn, không quan tâm độ dài" — nên chọn BFS hay DFS, và vì sao chọn được cả hai vẫn nên ưu tiên DFS?

    ??? note "Đáp án"
        Cả hai đều cho đáp án đúng (Có/Không) với cùng Big-O O(V+E). Nhưng nếu chỉ cần biết "có tồn tại hay không" (không cần đường ngắn nhất), DFS bằng đệ quy thường viết ngắn gọn hơn và không cần cấp phát Queue tường minh — phù hợp hơn về mặt code đơn giản, dù hiệu năng tương đương BFS.

---

??? abstract "DEEP DIVE — Cơ chế tầng dưới & mở rộng"
    **BFS dùng Queue<T> của .NET, cấu trúc bên trong là gì.** `Queue<T>` trong BCL cài bằng **circular buffer** (mảng vòng): một `T[] _array` cùng hai chỉ số `_head` (đầu) và `_tail` (cuối). `Enqueue` ghi vào `_tail` rồi tăng lên (quay lại đầu mảng nếu chạm cuối); `Dequeue` đọc từ `_head` rồi tăng lên. Cả hai đều O(1) vì không phải dịch chuyển phần tử nào — khác hẳn "dùng List rồi RemoveAt(0)" (sẽ là O(n) vì phải dịch cả mảng lên một ô).

    **DFS đệ quy dùng call stack thật của CLR — giới hạn thực tế.** Mỗi lần gọi hàm (kể cả gọi đệ quy) CLR cấp một **stack frame** mới trên ngăn xếp luồng hiện tại (thường 1MB mặc định trên .NET cho luồng chính, có thể chỉnh bằng `Thread` với `maxStackSize`). Với DFS đệ quy trên chuỗi ~50.000-100.000 đỉnh liên tiếp (tuỳ kích thước frame), rất dễ chạm giới hạn và ném `StackOverflowException` — đây là exception **không catch được** trong .NET (chương trình bị kill ngay), nên với graph không kiểm soát được độ sâu, luôn ưu tiên DFS bằng `Stack<T>` tường minh trên heap.

    **Topological sort — ứng dụng trực tiếp của DFS trên DAG.** DAG (Directed Acyclic Graph — đồ thị có hướng, không cycle) có thể "sắp thứ tự tuyến tính" các đỉnh sao cho mọi cạnh `u -> v` đều có `u` đứng trước `v` trong thứ tự đó. Cách cài dùng DFS: chạy DFS, mỗi khi một đỉnh **lùi ra hoàn toàn** (không còn hàng xóm chưa thăm), đẩy đỉnh đó vào đầu một danh sách kết quả; danh sách cuối cùng chính là thứ tự topological. Đây là nền cho các công cụ build (Make, MSBuild), package manager (NuGet, npm) quyết định thứ tự cài đặt/biên dịch theo phụ thuộc.

    **Union-Find (Disjoint Set) — cách khác để phát hiện cycle trong undirected graph.** Với undirected graph, có một cấu trúc chuyên dụng gọi là Union-Find: mỗi đỉnh thuộc một "nhóm liên thông", `Union(u, v)` gộp hai nhóm, `Find(u)` trả về đại diện nhóm. Khi thêm cạnh `(u, v)`, nếu `Find(u) == Find(v)` (đã cùng nhóm từ trước) thì cạnh này tạo cycle. Với tối ưu "path compression" + "union by rank", cả `Union` và `Find` gần như O(1) khấu hao (chính xác là O(α(n)) với α là hàm ngược Ackermann, tăng chậm hơn cả log n) — nhanh hơn DFS lại từ đầu mỗi lần thêm cạnh mới.

    **Bidirectional BFS — tăng tốc tìm đường trong graph khổng lồ.** Với graph rất lớn (mạng xã hội triệu người), BFS một chiều từ A có thể phải thăm hàng triệu đỉnh trước khi chạm B. Bidirectional BFS chạy BFS **đồng thời từ cả A và B**, dừng ngay khi hai "làn sóng" gặp nhau. Vì số đỉnh trong một lớp BFS tăng theo cấp số nhân (bậc trung bình mũ theo khoảng cách), hai BFS "ngắn" từ hai đầu rẻ hơn nhiều so với một BFS "dài" từ một đầu — đây là kỹ thuật LinkedIn dùng thật cho tính năng "khoảng cách kết nối" (1st/2nd/3rd degree).

---

Tiếp theo -> cấu trúc dữ liệu cây và thuật toán trên cây (tree traversal, binary search tree)
