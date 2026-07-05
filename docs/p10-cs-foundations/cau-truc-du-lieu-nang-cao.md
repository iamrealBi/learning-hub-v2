---
tier: core
status: core
owner: core-team
verified_on: "2026-07-05"
dotnet_version: "10.0"
bloom: "Analyze"
requires: [p10-bigo]
est_minutes_fast: 90
---

# Cấu trúc dữ liệu nâng cao: tự viết Linked List, Stack, Queue, Tree, Heap

!!! info "bạn đang ở đây · p10 → node `p10-ds`"
    **Cần trước:** Big-O (đo tốc độ tăng của thao tác khi n tiến ra vô cùng, ký hiệu O(1)/O(n)/O(log n)/O(n²)).
    **Mở khoá:** thuật toán sắp xếp/tìm kiếm nâng cao, đồ thị (BFS/DFS dùng Queue/Stack tự viết), thiết kế cache/LRU, phỏng vấn kỹ thuật vòng cấu trúc dữ liệu.

> **Mục tiêu (đo được):** Sau chương này bạn (1) **tự viết** được `class Node` và cài Linked List với insert/traverse, **giải thích** vì sao chèn đầu O(1) trong khi array phải shift O(n); (2) **tự cài** Stack (LIFO) và Queue (FIFO) từ đầu, **chứng minh** vì sao Dequeue từ đầu array thô là O(n) và cách circular buffer né được điều đó; (3) **tự cài** Binary Search Tree với Insert/Search, **đo** Big-O trung bình O(log n) và **chỉ ra** trường hợp xấu nhất O(n) khi cây bị lệch; (4) **tự cài** một Min-Heap bằng mảng phẳng (không con trỏ) và **giải thích** cơ chế sift-up/sift-down làm nền cho priority queue.

---

## 0. Đoán nhanh trước khi học (60 giây)

Đọc và **tự đoán output** trước khi mở đáp án.

```csharp title="Đoán output"
// test:run
var head = new Node(3);
head.Next = new Node(7);
head.Next.Next = new Node(9);

// Chèn số 1 vào ĐẦU danh sách — không đụng tới 3 node cũ
head = new Node(1) { Next = head };

var cur = head;
while (cur != null)
{
    Console.Write(cur.Value + " ");
    cur = cur.Next;
}

class Node
{
    public int Value;
    public Node? Next;
    public Node(int v) { Value = v; }
}
```

??? note "Đáp án — mở SAU khi đã đoán"
    In ra **`1 3 7 9 `**. Chèn đầu chỉ tạo 1 node mới rồi cho `Next` của nó trỏ tới `head` cũ — 3 node `3, 7, 9` **không bị di chuyển hay copy**, chỉ có một con trỏ (`head`) đổi hướng. Đây chính là lý do chèn đầu Linked List là **O(1)**, còn `List<int>.Insert(0, x)` (đã học ở P1) phải **dịch cả mảng nền sang phải** — O(n). Mục 1 sẽ mổ xẻ đầy đủ.

---

## 1. Nhắc lại 1 câu về P1, rồi vào chủ đề thật của chương này

Ở P1 (`collections.md`) bạn đã học **dùng** `List<T>`, `Dictionary<K,V>`, `HashSet<T>`, `Queue<T>`, `Stack<T>` — gọi method có sẵn của BCL (`Add`, `Enqueue`, `Push`...) và biết Big-O của từng thao tác đó. Chương này **không lặp lại cách gọi các method đó** — thay vào đó, chúng ta **tự viết `class Node` và cấu trúc bên trong** để hiểu **vì sao** những Big-O ở P1 lại đúng như vậy, và tự cài thêm hai cấu trúc P1 chưa dạy: Binary Search Tree và Heap.

---

## 2. Linked List — chuỗi node tự trỏ tới nhau

**Định nghĩa:** Linked List là một cấu trúc dữ liệu gồm các **node** rời rạc trên heap, mỗi node giữ **một giá trị dữ liệu** và **một con trỏ (tham chiếu) tới node kế tiếp**; không có mảng nền liên tục nào cả.

### 2.1 Tự viết Node và phép chèn đầu

```csharp title="Linked List tối thiểu: Node + AddFirst"
// test:run
class Node
{
    public int Value;
    public Node? Next;
    public Node(int value) { Value = value; }
}

class DanhSachLienKet
{
    private Node? _head;
    public int Count { get; private set; }

    // Chèn vào ĐẦU danh sách — O(1): chỉ tạo 1 node, đổi 1 con trỏ
    public void AddFirst(int value)
    {
        var node = new Node(value) { Next = _head };
        _head = node;
        Count++;
    }

    public void Traverse(Action<int> action)
    {
        var cur = _head;
        while (cur != null)
        {
            action(cur.Value);
            cur = cur.Next;
        }
    }
}

var ds = new DanhSachLienKet();
ds.AddFirst(30);
ds.AddFirst(20);
ds.AddFirst(10);   // danh sách hiện tại: 10 -> 20 -> 30

ds.Traverse(v => Console.Write(v + " "));   // 10 20 30
Console.WriteLine();
Console.WriteLine(ds.Count);   // 3
```

`AddFirst` chỉ làm 2 việc bất kể danh sách có 3 hay 3 triệu phần tử: tạo node mới, gán `Next`. Đó là bản chất của O(1).

### 2.2 Big-O: chèn đầu O(1) vs array phải shift O(n)

| Thao tác | Linked List | Array / `List<T>` (đã học ở P1) | Vì sao |
|---|---|---|---|
| Chèn đầu | O(1) | O(n) | Array phải **dịch mọi phần tử hiện có** sang phải 1 ô để tạo chỗ trống ở đầu; Linked List chỉ đổi 1 con trỏ |
| Chèn cuối (đã giữ con trỏ node cuối) | O(1) | O(1) khấu hao | Cả hai đều nhanh nếu biết vị trí cuối; array đôi khi phải phình mảng |
| Truy cập phần tử thứ i | O(n) | O(1) | Linked List phải **đi từng node** từ đầu vì không có công thức "địa chỉ = base + i×size" như array |
| Duyệt toàn bộ (traverse) | O(n) | O(n) | Cả hai đều phải chạm mọi phần tử ít nhất 1 lần |

```csharp title="Chứng minh chèn đầu Linked List không phụ thuộc kích thước hiện tại"
// test:run
class Node2
{
    public int Value;
    public Node2? Next;
    public Node2(int v) { Value = v; }
}

// Đo số "bước" (thao tác con trỏ) khi chèn đầu vào danh sách đã có N node
static int SoBuocChenDau(Node2? head, int giaTriMoi, out Node2 headMoi)
{
    int buoc = 0;
    var node = new Node2(giaTriMoi); buoc++;   // 1 bước: tạo node
    node.Next = head; buoc++;                  // 1 bước: nối con trỏ
    headMoi = node;
    return buoc;   // LUÔN = 2, bất kể head trỏ tới 1 node hay 1 triệu node
}

Node2? rong = null;
int b1 = SoBuocChenDau(rong, 1, out var h1);            // danh sách rỗng
Node2 mot = new Node2(99);
int b2 = SoBuocChenDau(mot, 2, out var h2);             // danh sách có sẵn 1 node

Console.WriteLine(b1);   // 2
Console.WriteLine(b2);   // 2 — GIỐNG NHAU, không tăng theo số node hiện có -> O(1)
```

!!! danger "Cạm bẫy: nhầm Linked List nhanh hơn List<T> ở mọi mặt"
    Linked List chỉ thắng khi bạn **chèn/xoá ở đầu (hoặc giữa, nếu đã giữ sẵn tham chiếu node)**. Truy cập theo chỉ số và duyệt tuần tự thì `List<T>` (mảng liền khối, cache CPU tốt — đã giải thích ở P1) thường **nhanh hơn** dù cùng độ phức tạp O(n), vì con trỏ rải node khắp heap gây cache-miss. Đây cũng chính là lý do BCL hiếm khi khuyên dùng `LinkedList<T>`.

### 2.3 Xoá một giá trị: phải tìm node trước đó (predecessor)

Xoá node ở **đầu** danh sách chỉ cần đổi `_head` — O(1). Nhưng xoá một **giá trị bất kỳ ở giữa** danh sách đơn (singly linked) khó hơn: bạn phải tìm được **node đứng ngay trước** node cần xoá để nối `Next` của nó vượt qua node bị xoá, vì node không tự biết ai đang trỏ tới mình.

```csharp title="Xoá một giá trị khỏi Linked List đơn: phải dò tới node trước đó"
// test:run
class Node4
{
    public int Value;
    public Node4? Next;
    public Node4(int v) { Value = v; }
}

class DanhSachLienKet3
{
    private Node4? _head;

    public void AddFirst(int v) => _head = new Node4(v) { Next = _head };

    // Xoá phần tử đầu tiên có Value == value. Trả về true nếu xoá được.
    public bool Remove(int value)
    {
        if (_head == null) return false;

        if (_head.Value == value)   // trường hợp đặc biệt: xoá ngay node đầu -> O(1)
        {
            _head = _head.Next;
            return true;
        }

        var truoc = _head;
        while (truoc.Next != null && truoc.Next.Value != value)
            truoc = truoc.Next;              // dò O(n) để tìm node NGAY TRƯỚC node cần xoá

        if (truoc.Next == null) return false;   // không tìm thấy
        truoc.Next = truoc.Next.Next;            // "nhảy qua" node cần xoá
        return true;
    }

    public void Traverse(Action<int> a)
    {
        var cur = _head;
        while (cur != null) { a(cur.Value); cur = cur.Next; }
    }
}

var ds3 = new DanhSachLienKet3();
foreach (var v in new[] { 30, 20, 10 }) ds3.AddFirst(v);   // danh sách: 10 -> 20 -> 30

Console.WriteLine(ds3.Remove(20));   // True — xoá node giữa, phải dò từ đầu
ds3.Traverse(v => Console.Write(v + " "));
Console.WriteLine();                  // 10 30

Console.WriteLine(ds3.Remove(99));   // False — không tồn tại
```

**Big-O của `Remove`:** xoá node đầu là O(1); xoá một giá trị bất kỳ khác là **O(n)** vì phải dò tuần tự để tìm node trước đó — không có cách nào "nhảy thẳng" tới giữa danh sách như array vì không có công thức địa chỉ.

!!! note "Doubly linked list: đánh đổi thêm 1 con trỏ để xoá O(1) khi đã có tham chiếu node"
    Nếu mỗi node giữ thêm một con trỏ `Prev` (trỏ ngược về node trước) — gọi là **danh sách liên kết đôi** — thì khi đã có sẵn tham chiếu tới node cần xoá (ví dụ do vừa `Traverse` tới), việc xoá node đó chỉ cần nối `Prev.Next` và `Next.Prev` bỏ qua nó — **O(1)**, không cần dò lại từ đầu. Đây chính là cơ chế bên trong `LinkedList<T>` của BCL (`AddBefore`/`AddAfter`/`Remove(node)` đều O(1) — đã học ở P1) khi bạn đã giữ sẵn `LinkedListNode<T>`. Cái giá phải trả: mỗi node tốn thêm 8 byte cho con trỏ `Prev` trên runtime 64-bit.

---

## 3. Tự cài Stack — LIFO (vào sau ra trước)

**Định nghĩa:** Stack là cấu trúc dữ liệu chỉ cho phép **thêm và lấy phần tử tại một đầu duy nhất** (gọi là "đỉnh"), theo nguyên tắc **vào sau ra trước** (Last In, First Out — LIFO).

### 3.1 Cài bằng Linked List: Push/Pop O(1)

```csharp title="Stack tự viết trên Linked List: Push/Pop O(1)"
// test:run
class NodeS
{
    public int Value;
    public NodeS? Next;
    public NodeS(int v) { Value = v; }
}

class NganXepTuVietVe
{
    private NodeS? _top;
    public int Count { get; private set; }

    public void Push(int value)   // O(1): thêm node mới ngay tại đỉnh
    {
        _top = new NodeS(value) { Next = _top };
        Count++;
    }

    public int Pop()   // O(1): lấy node đỉnh, đưa đỉnh về node kế
    {
        if (_top == null) throw new InvalidOperationException("Stack rỗng");
        int gt = _top.Value;
        _top = _top.Next;
        Count--;
        return gt;
    }

    public int Peek() => _top is null
        ? throw new InvalidOperationException("Stack rỗng")
        : _top.Value;
}

var st = new NganXepTuVietVe();
st.Push(1); st.Push(2); st.Push(3);   // đỉnh hiện tại: 3
Console.WriteLine(st.Peek());          // 3
Console.WriteLine(st.Pop());           // 3
Console.WriteLine(st.Pop());           // 2
Console.WriteLine(st.Count);           // 1
```

`Push` và `Pop` chỉ chạm vào node đỉnh — không đụng tới phần còn lại của stack, bất kể stack có bao nhiêu phần tử → **O(1)**.

### 3.2 Big-O tổng kết Stack

| Thao tác | Big-O | Vì sao |
|---|---|---|
| `Push` | O(1) | Chỉ thêm node/ô mới tại đỉnh |
| `Pop` | O(1) | Chỉ lấy và bỏ node/ô ở đỉnh |
| `Peek` | O(1) | Đọc trực tiếp con trỏ/chỉ số đỉnh, không quét |

---

## 4. Tự cài Queue — FIFO (vào trước ra trước)

**Định nghĩa:** Queue là cấu trúc dữ liệu cho phép **thêm vào một đầu (cuối) và lấy ra ở đầu kia (đầu)**, theo nguyên tắc **vào trước ra trước** (First In, First Out — FIFO).

### 4.1 Cạm bẫy: Dequeue từ đầu array thô là O(n)

```csharp title="Queue cài SAI trên array thô: Dequeue là O(n)"
// test:run
class HangDoiSaiTrenArray
{
    private int[] _data = new int[4];
    private int _count;

    public void Enqueue(int v) => _data[_count++] = v;   // thêm cuối: O(1)

    public int Dequeue()   // SAI CÁCH: lấy đầu rồi dịch mọi phần tử còn lại sang trái
    {
        int gt = _data[0];
        for (int i = 1; i < _count; i++)
            _data[i - 1] = _data[i];   // dịch trái từng phần tử -> O(n)
        _count--;
        return gt;
    }
}

var q = new HangDoiSaiTrenArray();
q.Enqueue(1); q.Enqueue(2); q.Enqueue(3);
Console.WriteLine(q.Dequeue());   // 1 — đúng kết quả, nhưng mỗi lần Dequeue tốn O(n) vì phải dịch mảng
```

!!! danger "Vì sao Dequeue trên array thô là O(n)"
    Sau khi lấy `_data[0]` ra, để "đầu hàng đợi" luôn nằm ở chỉ số 0, cách ngây thơ là **dịch mọi phần tử còn lại sang trái 1 ô** — số phép dịch tỉ lệ thuận với số phần tử còn lại → **O(n)** mỗi lần Dequeue. Nếu Dequeue n lần liên tiếp, tổng chi phí là O(n²) — chậm không thể chấp nhận cho hàng đợi lớn.

### 4.2 Cách sửa đúng: circular buffer (2 con trỏ head/tail)

**Định nghĩa circular buffer:** một mảng có kích thước cố định, dùng **hai chỉ số `_head` và `_tail`** để đánh dấu vị trí đầu/cuối logic, và khi chỉ số chạy tới cuối mảng thì **quay vòng về 0** — nhờ đó không cần dịch phần tử khi Dequeue.

```csharp title="Queue tự viết đúng bằng circular buffer: Enqueue/Dequeue O(1)"
// test:run
class HangDoiTuVietDung
{
    private int[] _data;
    private int _head;   // chỉ số phần tử ĐẦU (sẽ Dequeue tiếp theo)
    private int _tail;   // chỉ số Ô TRỐNG kế tiếp để Enqueue
    public int Count { get; private set; }

    public HangDoiTuVietDung(int capacity) => _data = new int[capacity];

    public void Enqueue(int v)   // O(1): ghi vào tail, tail quay vòng nếu chạm cuối mảng
    {
        if (Count == _data.Length) throw new InvalidOperationException("Đầy — cần cấp mảng lớn hơn");
        _data[_tail] = v;
        _tail = (_tail + 1) % _data.Length;   // quay vòng: hết mảng thì về lại chỉ số 0
        Count++;
    }

    public int Dequeue()   // O(1): đọc tại head, head quay vòng — KHÔNG dịch phần tử nào
    {
        if (Count == 0) throw new InvalidOperationException("Rỗng");
        int gt = _data[_head];
        _head = (_head + 1) % _data.Length;
        Count--;
        return gt;
    }
}

var q2 = new HangDoiTuVietDung(4);
q2.Enqueue(1); q2.Enqueue(2); q2.Enqueue(3);
Console.WriteLine(q2.Dequeue());   // 1 — head nhảy từ 0 -> 1, KHÔNG dịch phần tử 2,3
q2.Enqueue(4);
q2.Enqueue(5);                     // tail quay vòng về đầu mảng vì đã đi hết 4 ô
Console.WriteLine(q2.Dequeue());   // 2
Console.WriteLine(q2.Count);       // 2 (còn 4, 5)
```

| Thao tác | Big-O | Vì sao |
|---|---|---|
| `Enqueue` | O(1) | Ghi vào `_tail`, tăng chỉ số (quay vòng bằng `%`) — không chạm phần tử khác |
| `Dequeue` | O(1) | Đọc tại `_head`, tăng chỉ số — không dịch phần tử nào |

**Lựa chọn khác:** cài Queue bằng Linked List với 2 con trỏ `_head`/`_tail` (giống mục 2) cũng cho `Enqueue`/`Dequeue` O(1), đánh đổi bằng bộ nhớ con trỏ thay vì phải cấp trước kích thước mảng cố định.

---

## 5. Binary Search Tree (BST) — cây tìm kiếm nhị phân

**Định nghĩa:** Binary Tree là cấu trúc gồm các node, mỗi node có **tối đa 2 con** (gọi là con trái và con phải). Binary Search Tree (BST) là Binary Tree giữ **tính chất thứ tự**: với mọi node, **mọi giá trị ở cây con trái nhỏ hơn** node đó, và **mọi giá trị ở cây con phải lớn hơn** node đó.

### 5.1 Tự viết Node + Insert + Search

```csharp title="BST tối thiểu: Insert + Search"
// test:run
class NodeBST
{
    public int Value;
    public NodeBST? Left;
    public NodeBST? Right;
    public NodeBST(int v) { Value = v; }
}

class CayTimKiemNhiPhan
{
    private NodeBST? _root;

    public void Insert(int value) => _root = InsertVao(_root, value);

    private NodeBST InsertVao(NodeBST? node, int value)
    {
        if (node == null) return new NodeBST(value);   // tìm được chỗ trống -> tạo node mới
        if (value < node.Value) node.Left = InsertVao(node.Left, value);
        else if (value > node.Value) node.Right = InsertVao(node.Right, value);
        // value == node.Value: coi như đã có, không thêm trùng
        return node;
    }

    public bool Search(int value)
    {
        var cur = _root;
        while (cur != null)
        {
            if (value == cur.Value) return true;
            cur = value < cur.Value ? cur.Left : cur.Right;   // rẽ trái nếu nhỏ hơn, phải nếu lớn hơn
        }
        return false;
    }
}

var bst = new CayTimKiemNhiPhan();
foreach (var v in new[] { 8, 3, 10, 1, 6, 14 }) bst.Insert(v);

Console.WriteLine(bst.Search(6));    // True  — có trong cây
Console.WriteLine(bst.Search(99));   // False — không có
```

Cây được tạo ra từ `{8, 3, 10, 1, 6, 14}` có gốc `8`, cây con trái chứa `{3, 1, 6}` (đều < 8), cây con phải chứa `{10, 14}` (đều > 8) — đúng tính chất BST.

### 5.2 Big-O: O(log n) trung bình, O(n) worst-case khi cây lệch

Mỗi bước `Insert`/`Search` chỉ rẽ trái hoặc phải một lần rồi đi xuống một tầng — số bước tối đa bằng **chiều cao cây**.

- Nếu dữ liệu chèn vào **ngẫu nhiên** (đủ đa dạng), cây có xu hướng **cân đối**: chiều cao ≈ log₂(n) → Insert/Search là **O(log n)**.
- Nếu dữ liệu chèn vào theo thứ tự **đã sắp xếp sẵn** (ví dụ 1, 2, 3, 4, 5...), mỗi phần tử mới luôn lớn hơn mọi phần tử trước → cây suy biến thành **một chuỗi thẳng** (mỗi node chỉ có con phải) — chiều cao = n → Insert/Search là **O(n)**, không khác gì Linked List.

```csharp title="Chứng minh cây lệch: chèn dữ liệu đã sắp xếp -> O(n)"
// test:run
class NodeBST2
{
    public int Value;
    public NodeBST2? Left;
    public NodeBST2? Right;
    public NodeBST2(int v) { Value = v; }
}

static int ChieuCao(NodeBST2? node) =>
    node == null ? 0 : 1 + Math.Max(ChieuCao(node.Left), ChieuCao(node.Right));

static NodeBST2 ChenKhongCanBang(NodeBST2? node, int v)
{
    if (node == null) return new NodeBST2(v);
    if (v < node.Value) node.Left = ChenKhongCanBang(node.Left, v);
    else node.Right = ChenKhongCanBang(node.Right, v);
    return node;
}

// Ca 1: chèn NGẪU NHIÊN — cây cân đối, chiều cao ~ log2(n)
NodeBST2? canDoi = null;
foreach (var v in new[] { 8, 3, 10, 1, 6, 14, 4, 7 })
    canDoi = ChenKhongCanBang(canDoi, v);
Console.WriteLine($"Cây ngẫu nhiên, 8 phần tử, chiều cao = {ChieuCao(canDoi)}");   // ~3-4, gần log2(8)=3

// Ca 2: chèn THEO THỨ TỰ TĂNG — cây lệch hẳn thành chuỗi thẳng, chiều cao = n
NodeBST2? bLech = null;
foreach (var v in new[] { 1, 2, 3, 4, 5, 6, 7, 8 })
    bLech = ChenKhongCanBang(bLech, v);
Console.WriteLine($"Cây lệch, 8 phần tử, chiều cao = {ChieuCao(bLech)}");   // 8 — bằng đúng số phần tử!
```

| Trường hợp | Chiều cao cây | Big-O Insert/Search |
|---|---|---|
| Cây cân đối (dữ liệu chèn đa dạng) | ~log₂(n) | O(log n) — trung bình |
| Cây lệch hẳn (dữ liệu chèn đã sắp xếp) | n | O(n) — worst-case |

!!! danger "Cạm bẫy: tưởng BST luôn O(log n)"
    BST **thuần** (như cài ở trên) **không tự cân bằng**. Nếu input đã sắp xếp hoặc gần như vậy, nó suy biến thành Linked List với đầy đủ chi phí con trỏ mà mất luôn ưu điểm O(log n). Các cây tự cân bằng (AVL, Red-Black — chính là cơ chế bên trong `SortedDictionary<K,V>` đã học ở P1) giải quyết vấn đề này bằng cách tự xoay lại cây sau mỗi lần chèn/xoá để **đảm bảo** chiều cao luôn ~log₂(n), nhưng đó là chủ đề nằm ngoài phạm vi tự-cài của chương này.

### 5.3 Duyệt cây theo thứ tự (traversal): In-order cho ra dãy đã sắp xếp

Có 3 cách duyệt kinh điển một Binary Tree, khác nhau ở **thời điểm "thăm" node hiện tại** so với việc đi vào con trái/phải:

- **In-order** (trái → node → phải): với BST, luôn cho ra dãy giá trị **tăng dần**.
- **Pre-order** (node → trái → phải): thường dùng để **sao chép** cây (thăm cha trước khi thăm con).
- **Post-order** (trái → phải → node): thường dùng để **giải phóng/xoá** cây (xử lý con trước khi xử lý cha).

```csharp title="In-order traversal trên BST: luôn ra dãy tăng dần"
// test:run
class NodeBST3
{
    public int Value;
    public NodeBST3? Left;
    public NodeBST3? Right;
    public NodeBST3(int v) { Value = v; }
}

static NodeBST3 Chen(NodeBST3? node, int v)
{
    if (node == null) return new NodeBST3(v);
    if (v < node.Value) node.Left = Chen(node.Left, v);
    else if (v > node.Value) node.Right = Chen(node.Right, v);
    return node;
}

static void InOrder(NodeBST3? node, List<int> ketQua)
{
    if (node == null) return;
    InOrder(node.Left, ketQua);    // 1. hết cây con trái
    ketQua.Add(node.Value);        // 2. rồi mới tới chính node này
    InOrder(node.Right, ketQua);   // 3. cuối cùng là cây con phải
}

NodeBST3? root = null;
foreach (var v in new[] { 8, 3, 10, 1, 6, 14 }) root = Chen(root, v);

var ketQua = new List<int>();
InOrder(root, ketQua);
Console.WriteLine(string.Join(",", ketQua));   // 1,3,6,8,10,14 — LUÔN tăng dần, bất kể thứ tự chèn
```

**Big-O của traversal:** cả 3 cách đều **O(n)** vì phải thăm đúng mỗi node một lần, không phụ thuộc cây cân đối hay lệch.

### 5.4 Xoá một node khỏi BST: 3 trường hợp

Xoá khỏi BST phức tạp hơn Insert/Search vì phải **giữ đúng tính chất BST** sau khi xoá. Có 3 trường hợp:

1. **Node lá (không con nào):** xoá thẳng, cha trỏ về `null`.
2. **Node có đúng 1 con:** cha "nhảy qua" node bị xoá, trỏ trực tiếp tới con đó (giống xoá giữa Linked List ở mục 2.3).
3. **Node có đủ 2 con:** không thể xoá thẳng vì sẽ "mất" một nhánh — phải tìm **giá trị nhỏ nhất trong cây con phải** (gọi là "successor"), copy giá trị đó lên node hiện tại, rồi xoá node successor (lúc này chắc chắn rơi về trường hợp 1 hoặc 2).

```csharp title="Xoá node khỏi BST: xử lý đủ 3 trường hợp"
// test:run
class NodeBST4
{
    public int Value;
    public NodeBST4? Left;
    public NodeBST4? Right;
    public NodeBST4(int v) { Value = v; }
}

static NodeBST4? Chen4(NodeBST4? node, int v)
{
    if (node == null) return new NodeBST4(v);
    if (v < node.Value) node.Left = Chen4(node.Left, v);
    else if (v > node.Value) node.Right = Chen4(node.Right, v);
    return node;
}

static NodeBST4? Xoa(NodeBST4? node, int value)
{
    if (node == null) return null;

    if (value < node.Value) { node.Left = Xoa(node.Left, value); return node; }
    if (value > node.Value) { node.Right = Xoa(node.Right, value); return node; }

    // value == node.Value: đây chính là node cần xoá
    if (node.Left == null) return node.Right;    // 0 hoặc 1 con (phải) -> trả con phải lên thay chỗ
    if (node.Right == null) return node.Left;     // 1 con (trái) -> trả con trái lên thay chỗ

    // Đủ 2 con: tìm giá trị nhỏ nhất trong cây con phải (successor)
    var ke = node.Right;
    while (ke.Left != null) ke = ke.Left;
    node.Value = ke.Value;                         // copy giá trị successor lên node hiện tại
    node.Right = Xoa(node.Right, ke.Value);        // xoá node successor (giờ chắc chắn rơi về TH 1/2)
    return node;
}

static void InOrder2(NodeBST4? node, List<int> kq)
{
    if (node == null) return;
    InOrder2(node.Left, kq); kq.Add(node.Value); InOrder2(node.Right, kq);
}

NodeBST4? root4 = null;
foreach (var v in new[] { 8, 3, 10, 1, 6, 14 }) root4 = Chen4(root4, v);

root4 = Xoa(root4, 3);   // xoá node có 2 con (1 và 6) -> successor là 6

var kq2 = new List<int>();
InOrder2(root4, kq2);
Console.WriteLine(string.Join(",", kq2));   // 1,6,8,10,14 — vẫn đúng tính chất BST sau khi xoá
```

**Big-O của `Xoa`:** giống Insert/Search — phải đi từ gốc xuống để **tìm** node cần xoá (O(log n) trung bình, O(n) worst-case cây lệch), cộng thêm việc tìm successor cũng đi xuống tối đa chiều cao cây — tổng vẫn cùng cấp độ phức tạp, không đổi bậc.

---

## 6. Heap — Binary Tree đặc biệt dựng trên mảng phẳng

**Định nghĩa:** Heap là một Binary Tree đặc biệt giữ **tính chất heap**: trong **min-heap**, mọi node cha có giá trị **nhỏ hơn hoặc bằng** hai con của nó (max-heap thì ngược lại, cha **lớn hơn hoặc bằng** con); heap được lưu bằng **một mảng phẳng duy nhất**, không cần con trỏ Left/Right.

### 6.1 Vì sao dùng mảng phẳng mà không cần con trỏ

Với node ở chỉ số `i` trong mảng (đánh chỉ số từ 0), công thức cố định:

- Con trái ở chỉ số `2*i + 1`
- Con phải ở chỉ số `2*i + 2`
- Cha ở chỉ số `(i - 1) / 2`

Nhờ công thức này, "di chuyển" giữa cha và con chỉ là **tính toán chỉ số** — không cần lưu con trỏ `Left`/`Right`/`Parent` như Binary Tree ở mục 5, tiết kiệm bộ nhớ và tận dụng cache CPU (mảng liền khối, giống lý do `List<T>` nhanh hơn `LinkedList<T>` ở mục 2).

### 6.2 Tự cài Min-Heap: Insert (sift-up) và ExtractMin (sift-down)

```csharp title="Min-Heap tối thiểu trên mảng phẳng: Insert + ExtractMin"
// test:run
class MinHeapTuVietVe
{
    private readonly List<int> _data = new();
    public int Count => _data.Count;

    public void Insert(int value)
    {
        _data.Add(value);                    // đặt vào cuối mảng
        SiftUp(_data.Count - 1);              // rồi "nổi" lên đúng vị trí
    }

    public int ExtractMin()
    {
        if (_data.Count == 0) throw new InvalidOperationException("Heap rỗng");
        int min = _data[0];                            // gốc luôn là phần tử nhỏ nhất
        _data[0] = _data[^1];                           // đưa phần tử cuối lên gốc
        _data.RemoveAt(_data.Count - 1);
        if (_data.Count > 0) SiftDown(0);               // rồi "chìm" xuống đúng vị trí
        return min;
    }

    private void SiftUp(int i)
    {
        while (i > 0)
        {
            int cha = (i - 1) / 2;
            if (_data[i] >= _data[cha]) break;          // đã đúng chỗ -> dừng
            (_data[i], _data[cha]) = (_data[cha], _data[i]);   // đổi chỗ với cha
            i = cha;
        }
    }

    private void SiftDown(int i)
    {
        while (true)
        {
            int trai = 2 * i + 1, phai = 2 * i + 2, nhoNhat = i;
            if (trai < _data.Count && _data[trai] < _data[nhoNhat]) nhoNhat = trai;
            if (phai < _data.Count && _data[phai] < _data[nhoNhat]) nhoNhat = phai;
            if (nhoNhat == i) break;                    // đã đúng chỗ -> dừng
            (_data[i], _data[nhoNhat]) = (_data[nhoNhat], _data[i]);
            i = nhoNhat;
        }
    }
}

var heap = new MinHeapTuVietVe();
foreach (var v in new[] { 5, 2, 8, 1, 9, 3 }) heap.Insert(v);

Console.WriteLine(heap.ExtractMin());   // 1 — luôn lấy ra phần tử NHỎ NHẤT hiện có
Console.WriteLine(heap.ExtractMin());   // 2
Console.WriteLine(heap.ExtractMin());   // 3
Console.WriteLine(heap.Count);          // 3 còn lại (5, 8, 9 theo thứ tự nào đó bên trong)
```

### 6.3 Big-O của Heap

| Thao tác | Big-O | Vì sao |
|---|---|---|
| `Insert` | O(log n) | Thêm cuối mảng O(1), rồi `SiftUp` đi tối đa **chiều cao cây** = log₂(n) bước |
| `ExtractMin` | O(log n) | Lấy gốc O(1), đưa phần tử cuối lên gốc, rồi `SiftDown` đi tối đa log₂(n) bước |
| Xem phần tử nhỏ nhất (`_data[0]`) | O(1) | Tính chất heap đảm bảo phần tử nhỏ nhất **luôn** ở gốc — chỉ số 0 |

Heap **luôn cân đối** (không bao giờ lệch như BST ở mục 5) vì nó được lưu tuần tự trong mảng theo tầng, không phụ thuộc thứ tự chèn — đây là lý do Big-O của heap **ổn định**, không có "worst-case do dữ liệu xấu" như BST.

### 6.4 Ứng dụng: priority queue

Heap chính là cơ chế bên trong `PriorityQueue<TElement, TPriority>` mà P1 đã dùng qua method có sẵn (`Enqueue`/`Dequeue`) — Min-Heap tự viết ở trên là **đúng cấu trúc dữ liệu nằm phía sau** lớp BCL đó: `Insert` tương ứng `Enqueue`, `ExtractMin` tương ứng `Dequeue`. Ứng dụng thực tế: lịch task theo độ ưu tiên, thuật toán Dijkstra (luôn lấy đỉnh có khoảng cách nhỏ nhất tiếp theo), xử lý sự kiện theo thời gian gần nhất.

---

## 7. Tổng kết: chọn đúng cấu trúc — bảng so sánh và ví dụ trộn

Bây giờ cả 4 cấu trúc (Linked List, Stack, Queue, BST, Heap) đã được dạy **riêng lẻ, đủ định nghĩa — ví dụ — Big-O** ở các mục 2-6. Mục này mới đưa ra bảng so sánh tổng thể và một ví dụ **trộn nhiều cấu trúc** để giải một bài toán thực tế.

### 7.1 Bảng so sánh Big-O

| Cấu trúc | Chèn | Xoá | Tìm/truy cập | Bộ nhớ phụ mỗi phần tử |
|---|---|---|---|---|
| Linked List (đơn) | O(1) đầu / O(n) giữa-cuối không giữ tail | O(1) đầu / O(n) giá trị bất kỳ | O(n) | 1 con trỏ (`Next`) |
| Stack (trên Linked List) | O(1) (`Push`) | O(1) (`Pop`) | O(1) chỉ đỉnh (`Peek`) | 1 con trỏ |
| Queue (circular buffer) | O(1) (`Enqueue`) | O(1) (`Dequeue`) | O(1) chỉ đầu (`Peek`) | 0 — dùng lại mảng cấp trước |
| BST (không tự cân bằng) | O(log n) tb / O(n) xấu nhất | O(log n) tb / O(n) xấu nhất | O(log n) tb / O(n) xấu nhất | 2 con trỏ (`Left`, `Right`) |
| Heap (mảng phẳng) | O(log n) luôn ổn định | O(log n) luôn ổn định (`ExtractMin`) | O(1) chỉ phần tử ưu tiên nhất | 0 — dùng lại mảng, chỉ số tính bằng công thức |

**Cách chọn nhanh:** cần LIFO (hoàn tác, DFS) → Stack. Cần FIFO (xử lý theo thứ tự đến, BFS) → Queue. Cần tìm kiếm có thứ tự và chấp nhận rủi ro lệch cây → BST (hoặc `SortedDictionary` nếu cần tự cân bằng, đã học P1). Cần luôn lấy ra phần tử ưu tiên nhất nhanh → Heap. Cần chèn/xoá đầu liên tục mà không cần truy cập chỉ số → Linked List.

### 7.2 Ví dụ trộn: mô phỏng phòng cấp cứu bằng Heap + Queue

Bài toán: bệnh nhân đến theo thứ tự bất kỳ, mỗi người có một **mức độ nghiêm trọng** (số nhỏ hơn = nghiêm trọng hơn, cần cấp cứu trước). Trong cùng mức độ nghiêm trọng, ai đến trước khám trước (FIFO). Đây trộn cả **Heap** (ưu tiên theo mức độ) và ý tưởng **Queue** (thứ tự đến, dùng làm tiêu chí phụ để heap ổn định).

```csharp title="Trộn Heap + tiêu chí phụ FIFO: mô phỏng phòng cấp cứu"
// test:run
class MinHeapBenhNhan
{
    // Mỗi phần tử: (mucDoNghiemTrong, thuTuDen) — so theo mucDo trước, thuTuDen là tiêu chí phụ
    private readonly List<(int MucDo, int ThuTu, string Ten)> _d = new();
    public int Count => _d.Count;

    private static bool NhoHon((int MucDo, int ThuTu, string Ten) a, (int MucDo, int ThuTu, string Ten) b)
        => a.MucDo != b.MucDo ? a.MucDo < b.MucDo : a.ThuTu < b.ThuTu;   // tiêu chí phụ: đến trước ưu tiên trước

    public void Insert(int mucDo, int thuTuDen, string ten)
    {
        _d.Add((mucDo, thuTuDen, ten));
        int i = _d.Count - 1;
        while (i > 0)
        {
            int cha = (i - 1) / 2;
            if (!NhoHon(_d[i], _d[cha])) break;
            (_d[i], _d[cha]) = (_d[cha], _d[i]);
            i = cha;
        }
    }

    public string ExtractMin()
    {
        var min = _d[0];
        _d[0] = _d[^1];
        _d.RemoveAt(_d.Count - 1);
        int i = 0;
        while (_d.Count > 0)
        {
            int trai = 2 * i + 1, phai = 2 * i + 2, nn = i;
            if (trai < _d.Count && NhoHon(_d[trai], _d[nn])) nn = trai;
            if (phai < _d.Count && NhoHon(_d[phai], _d[nn])) nn = phai;
            if (nn == i) break;
            (_d[i], _d[nn]) = (_d[nn], _d[i]);
            i = nn;
        }
        return min.Ten;
    }
}

var phongCapCuu = new MinHeapBenhNhan();
phongCapCuu.Insert(mucDo: 3, thuTuDen: 0, ten: "Binh (trẹo cổ chân)");
phongCapCuu.Insert(mucDo: 1, thuTuDen: 1, ten: "Chi (khó thở)");
phongCapCuu.Insert(mucDo: 3, thuTuDen: 2, ten: "An (sốt nhẹ)");   // cùng mức 3 với Binh, đến SAU
phongCapCuu.Insert(mucDo: 1, thuTuDen: 3, ten: "Dung (đau ngực)");   // cùng mức 1 với Chi, đến SAU

while (phongCapCuu.Count > 0)
    Console.WriteLine(phongCapCuu.ExtractMin());
// Chi (khó thở)          — mức 1, đến trước Dung
// Dung (đau ngực)         — mức 1, đến sau Chi
// Binh (trẹo cổ chân)     — mức 3, đến trước An
// An (sốt nhẹ)            — mức 3, đến sau Binh
```

Kết quả cho thấy: heap luôn ưu tiên `MucDo` nhỏ hơn trước; khi `MucDo` bằng nhau, `ThuTu` (đóng vai trò tương tự FIFO của Queue) quyết định ai ra trước — đây là kỹ thuật ghép **tiêu chí phụ** đã nhắc ở mục 6 (P1 cũng cảnh báo điều này với `PriorityQueue` của BCL: nó không tự đảm bảo ổn định giữa các phần tử cùng ưu tiên, phải tự ghép thêm tiêu chí phụ như trên).

---

## Cạm bẫy & thực chiến

- **Nhầm Linked List "luôn nhanh hơn" array/List<T>.** Chỉ đúng cho chèn/xoá đầu (hoặc giữa khi đã giữ tham chiếu node). Truy cập theo chỉ số và duyệt tuần tự thì array/`List<T>` thắng nhờ cache CPU liền khối — xem mục 2.2.
- **Dequeue trực tiếp từ đầu array bằng cách dịch phần tử.** Đây là lỗi thường gặp nhất khi tự cài Queue lần đầu — biến O(1) kỳ vọng thành O(n) thực tế. Luôn dùng circular buffer (2 con trỏ head/tail quay vòng) hoặc Linked List với con trỏ tail — xem mục 4.
- **Tưởng BST luôn O(log n).** BST thuần không tự cân bằng: chèn dữ liệu đã sắp xếp (hoặc gần sắp xếp) làm cây suy biến thành chuỗi thẳng, Insert/Search rơi về O(n) — xem mục 5.2. Muốn đảm bảo O(log n) mọi lúc thì cần cây tự cân bằng (AVL/Red-Black — cơ chế trong `SortedDictionary`).
- **Nhầm Heap là cây có sắp xếp toàn phần.** Heap chỉ đảm bảo cha ≤ con (min-heap) tại **mọi cặp cha-con trực tiếp** — không đảm bảo thứ tự giữa hai node anh em hoặc giữa các nhánh khác nhau. Muốn lấy phần tử nhỏ thứ 2, thứ 3... phải `ExtractMin` lần lượt, không thể đọc trực tiếp từ chỉ số cố định nào khác ngoài gốc.
- **Quên kiểm tra rỗng trước khi Pop/Dequeue/ExtractMin.** Gọi trên cấu trúc rỗng phải ném exception rõ ràng (như code ở mục 3, 4, 6) — im lặng trả giá trị mặc định (0, null) sẽ che giấu bug ở tầng gọi.
- **Đệ quy `Insert`/`ChieuCao` trên cây rất sâu (worst-case BST lệch) có thể stack overflow.** Với n lớn (hàng trăm nghìn phần tử) chèn theo thứ tự đã sắp xếp, đệ quy đi sâu n tầng — nên cân nhắc viết lại bằng vòng lặp (iterative) cho code chạy production.

---

## Bài tập

1. Viết thêm method `AddLast(int value)` cho `DanhSachLienKet` ở mục 2.1 (thêm vào **cuối** danh sách, không phải đầu). So sánh Big-O của `AddLast` khi bạn phải duyệt từ `_head` tới cuối, với `AddFirst`.

    ??? success "Lời giải"
        ```csharp title="AddLast: phải duyệt tới cuối -> O(n) nếu không giữ con trỏ tail"
        // test:run
        class Node3
        {
            public int Value;
            public Node3? Next;
            public Node3(int v) { Value = v; }
        }

        class DanhSachLienKet2
        {
            private Node3? _head;

            public void AddFirst(int value) => _head = new Node3(value) { Next = _head };

            public void AddLast(int value)   // O(n): phải đi hết danh sách để tìm node cuối
            {
                var node = new Node3(value);
                if (_head == null) { _head = node; return; }
                var cur = _head;
                while (cur.Next != null) cur = cur.Next;   // duyệt tới hết -> O(n)
                cur.Next = node;
            }

            public void Traverse(Action<int> a)
            {
                var cur = _head;
                while (cur != null) { a(cur.Value); cur = cur.Next; }
            }
        }

        var ds = new DanhSachLienKet2();
        ds.AddLast(1); ds.AddLast(2); ds.AddFirst(0);
        ds.Traverse(v => Console.Write(v + " "));   // 0 1 2
        ```
        `AddLast` như trên là **O(n)** vì phải duyệt từ `_head` tới node cuối mỗi lần gọi. Muốn `AddLast` cũng O(1), phải **giữ thêm một con trỏ `_tail`** luôn chỉ tới node cuối cùng (giống cách `LinkedList<T>` của BCL làm), cập nhật `_tail` mỗi khi thêm.

2. Dùng `MinHeapTuVietVe` ở mục 6.2, viết một hàm `TopK(int[] data, int k)` trả về `k` giá trị nhỏ nhất trong `data`, theo thứ tự tăng dần. Giải thích Big-O tổng thể.

    ??? success "Lời giải"
        ```csharp title="TopK bằng Min-Heap tự viết"
        // test:run
        class MinHeap2
        {
            private readonly List<int> _d = new();
            public int Count => _d.Count;

            public void Insert(int v)
            {
                _d.Add(v);
                int i = _d.Count - 1;
                while (i > 0)
                {
                    int cha = (i - 1) / 2;
                    if (_d[i] >= _d[cha]) break;
                    (_d[i], _d[cha]) = (_d[cha], _d[i]);
                    i = cha;
                }
            }

            public int ExtractMin()
            {
                int min = _d[0];
                _d[0] = _d[^1];
                _d.RemoveAt(_d.Count - 1);
                int i = 0;
                while (true)
                {
                    int trai = 2 * i + 1, phai = 2 * i + 2, nn = i;
                    if (trai < _d.Count && _d[trai] < _d[nn]) nn = trai;
                    if (phai < _d.Count && _d[phai] < _d[nn]) nn = phai;
                    if (nn == i) break;
                    (_d[i], _d[nn]) = (_d[nn], _d[i]);
                    i = nn;
                }
                return min;
            }
        }

        static int[] TopK(int[] data, int k)
        {
            var heap = new MinHeap2();
            foreach (var v in data) heap.Insert(v);   // n lần Insert, mỗi lần O(log n)

            var ketQua = new int[k];
            for (int i = 0; i < k; i++)
                ketQua[i] = heap.ExtractMin();          // k lần ExtractMin, mỗi lần O(log n)
            return ketQua;
        }

        var kq = TopK(new[] { 9, 3, 7, 1, 8, 2 }, 3);
        Console.WriteLine(string.Join(",", kq));   // 1,2,3
        ```
        Tổng Big-O: `n` lần `Insert` tốn O(n log n), cộng `k` lần `ExtractMin` tốn O(k log n) — tổng **O((n + k) log n)**, hay gọn hơn O(n log n) vì k ≤ n.

---

## Tự kiểm tra

1. Vì sao chèn vào đầu Linked List là O(1) nhưng chèn vào đầu `List<T>` là O(n)?

    ??? note "Đáp án"
        Linked List chỉ tạo 1 node mới và đổi 1 con trỏ (`head`), không đụng tới node nào khác. `List<T>` lưu phần tử liên tục trong mảng nền, chèn đầu buộc phải **dịch mọi phần tử hiện có** sang phải 1 ô để tạo chỗ trống — số phép dịch tỉ lệ với số phần tử hiện có.

2. Vì sao Dequeue trực tiếp từ đầu một array thô (`_data[0]`, rồi dịch trái) là O(n), và circular buffer giải quyết vấn đề này thế nào?

    ??? note "Đáp án"
        Sau khi lấy `_data[0]`, để giữ đầu hàng đợi luôn ở chỉ số 0, cách ngây thơ phải dịch mọi phần tử còn lại sang trái — O(n). Circular buffer dùng 2 chỉ số `_head`/`_tail` di chuyển độc lập (quay vòng bằng `% length`) nên Dequeue chỉ cần tăng `_head`, không dịch phần tử nào — O(1).

3. Big-O trung bình và worst-case của Insert/Search trên Binary Search Tree là gì, và điều gì gây ra worst-case?

    ??? note "Đáp án"
        Trung bình **O(log n)** khi cây cân đối (chiều cao ≈ log₂n). Worst-case **O(n)** khi cây bị lệch hẳn thành chuỗi thẳng (chiều cao = n) — xảy ra khi dữ liệu được chèn vào theo thứ tự đã sắp xếp hoặc gần như vậy.

4. Min-heap và max-heap khác nhau ở tính chất nào?

    ??? note "Đáp án"
        Min-heap: mọi node cha ≤ hai con của nó (gốc luôn là giá trị nhỏ nhất). Max-heap: mọi node cha ≥ hai con của nó (gốc luôn là giá trị lớn nhất).

5. Vì sao Heap có thể lưu bằng một mảng phẳng mà không cần con trỏ Left/Right/Parent như Binary Tree thường?

    ??? note "Đáp án"
        Vì chỉ số của con trái, con phải, cha đều có thể tính trực tiếp từ chỉ số node hiện tại bằng công thức cố định (con trái = 2i+1, con phải = 2i+2, cha = (i-1)/2) — không cần lưu tham chiếu tường minh.

6. Tại sao `SiftUp` khi Insert vào heap chỉ cần tối đa O(log n) bước, không phải O(n)?

    ??? note "Đáp án"
        Vì heap luôn là cây cân đối (lưu tuần tự theo tầng trong mảng, không phụ thuộc thứ tự chèn như BST), nên chiều cao cây luôn ≈ log₂n. `SiftUp` di chuyển từ node vừa thêm lên tối đa tới gốc, tức tối đa "chiều cao" bước.

7. Chương P1 (`collections.md`) đã dạy gì về `List`/`Dictionary`/`Queue`/`Stack`, và chương này khác ở điểm nào?

    ??? note "Đáp án"
        P1 dạy **dùng** các collection có sẵn của BCL (gọi `Add`, `Enqueue`, `Push`...) và Big-O của thao tác đó. Chương này dạy **cách cài đặt bên trong** các cấu trúc đó từ đầu (tự viết `class Node`, tự quản lý con trỏ/chỉ số) để hiểu vì sao Big-O ở P1 lại đúng như vậy.

8. Vì sao `LinkedList<T>` của BCL (hoặc Linked List tự viết) thường chậm hơn `List<T>` trong thực tế dù cùng độ phức tạp O(n) khi duyệt?

    ??? note "Đáp án"
        `List<T>` lưu phần tử liên tục trong một khối nhớ, CPU đọc theo cache line nên duyệt tuần tự rất hiệu quả (ít cache-miss). Linked List rải các node khắp heap qua con trỏ, mỗi bước di chuyển là một lần truy cập vùng nhớ khác — nhiều khả năng cache-miss hơn, nên O(n) của nó chậm hơn O(n) của array trên dữ liệu thật.

---

??? abstract "DEEP DIVE — cơ chế tầng dưới"
    **Vì sao cây tự cân bằng (AVL/Red-Black) tránh được worst-case O(n) của BST thuần.** Sau mỗi lần Insert/Remove, các cây này kiểm tra "độ lệch" giữa hai nhánh con và thực hiện phép **xoay (rotation)** — đổi chỗ một vài node theo mẫu cố định — nếu độ lệch vượt ngưỡng cho phép. Mỗi lần xoay là O(1), và số lần xoay cần thiết sau một Insert/Remove tối đa là O(log n), nên tổng chi phí Insert/Remove vẫn giữ được O(log n) trong khi đảm bảo chiều cao cây luôn ~log₂n — đây chính là cơ chế bên trong `SortedDictionary<K,V>`/`SortedSet<T>` của BCL (đã nhắc ở P1) mà không phải tự cài tay.

    **Vì sao `_data[(i-1)/2]` cho ra đúng chỉ số cha trong heap.** Vì heap lưu theo tầng (level-order): tầng 0 có 1 node (chỉ số 0), tầng 1 có 2 node (chỉ số 1, 2), tầng 2 có 4 node (chỉ số 3, 4, 5, 6)... Với phép chia nguyên, `(i-1)/2` luôn trỏ đúng về node cha ở tầng trên, vì mỗi cặp con liên tiếp `(2i+1, 2i+2)` cùng chia hết cho cùng một cha `i` sau khi trừ 1 và chia 2 (số nguyên, làm tròn xuống).

    **Vì sao Linked List tốn nhiều bộ nhớ hơn array cho cùng số phần tử.** Mỗi node Linked List trong .NET là một object riêng trên heap: ngoài dữ liệu (`int Value` = 4 byte), còn có **object header** (thường 16 byte trên runtime 64-bit: method table pointer + sync block) và con trỏ `Next` (8 byte trên 64-bit) — tổng chi phí phụ trên mỗi phần tử có thể lớn hơn dữ liệu thật sự nhiều lần. Array/`List<T>` chỉ tốn đúng kích thước phần tử liên tục, không có overhead per-node.

    **Sift-down khi ExtractMin vì sao phải so cả hai con rồi chọn nhỏ hơn.** Nếu chỉ so với một con (ví dụ luôn con trái) mà đổi chỗ, có thể phá vỡ tính chất heap ở nhánh còn lại — ví dụ cha lớn hơn con phải nhưng thuật toán lại không phát hiện vì chỉ nhìn con trái. Phải tìm **giá trị nhỏ nhất trong 3 vị trí (cha, con trái, con phải)** trước khi quyết định đổi chỗ, đảm bảo tại mọi bước tính chất min-heap được giữ đúng cho cả hai nhánh.

    **Vì sao circular buffer cần phân biệt "đầy" và "rỗng" khi `_head == _tail`.** Khi `Count` không được lưu riêng, `_head == _tail` có thể là rỗng (chưa Enqueue gì) hoặc đầy (đã Enqueue đủ `capacity` phần tử, `_tail` quay vòng trùng `_head`) — hai trạng thái khác nhau nhưng chỉ số giống nhau. Cách implement ở mục 4.2 tránh nhầm lẫn này bằng cách lưu **`Count` riêng** làm nguồn sự thật duy nhất, thay vì suy ra trạng thái chỉ từ so sánh `_head`/`_tail`.

---

Tiếp theo -> thuật toán sắp xếp và tìm kiếm nâng cao
