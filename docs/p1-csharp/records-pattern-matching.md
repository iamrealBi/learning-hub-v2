---
tier: core
status: core
owner: core-team
verified_on: "2026-07-01"
dotnet_version: "10.0"
bloom: "Analyze"
requires: [p1-oop]
est_minutes_fast: 60
est_minutes_deep: 130
---

# Records & Pattern Matching

!!! info "Bạn đang ở đây · P1 → node `p1-records-pattern-matching`"
    **Cần trước:** oop (class, struct, constructor, `virtual`/`override`, interface, `Equals`/`GetHashCode`, `ToString`); hiểu kiểu tham chiếu vs kiểu giá trị; cú pháp switch cổ điển.
    **Mở khoá:** domain model bất biến (immutable DTO/value object), xử lý cây cú pháp & message, code phân nhánh gọn ở tầng dịch vụ P3, và tư duy functional cho LINQ nâng cao.
    ⏱️ Fast path ~60 phút · Deep dive +70 phút.

> **Mục tiêu (đo được):** Sau chương này bạn (1) **tự sinh trong đầu** được `Equals`, `GetHashCode`, `ToString`, `Deconstruct`, `<Clone>$` mà compiler tạo cho một record; (2) **dự đoán chính xác** kết quả `==` giữa hai record — kể cả cạm bẫy field mảng/`List`; (3) **viết đúng** mọi loại pattern (constant, type, declaration, var, discard, property, positional, relational, logical, list, slice, parenthesized) và một `switch` expression **vét cạn**; (4) **chọn đúng** giữa `record class`, `record struct`, `readonly record struct`, và `class` cho một bài toán; (5) **nhận diện và sửa** lỗi thứ tự arm và lỗi property pattern với `null`.

---

## 0. Đoán nhanh trước khi học (30 giây)

Đọc và **tự đoán output** trước khi mở đáp án.

```csharp title="Đoán output"
// test:run
var a = new Point(1, 2);
var b = new Point(1, 2);
var c = a with { Y = 99 };

Console.WriteLine(a == b);        // ?
Console.WriteLine(ReferenceEquals(a, b)); // ?
Console.WriteLine(a);             // ?
Console.WriteLine(c);             // ?

record Point(int X, int Y);
```

??? note "Đáp án — mở SAU khi đã đoán"
    Lần lượt in ra:
    ```text title="Kết quả"
    True
    False
    Point { X = 1, Y = 2 }
    Point { X = 1, Y = 99 }
    ```
    - `a == b` là **`True`**: record dùng **value equality** — so sánh theo *giá trị các thành viên*, không theo địa chỉ. `Point(1,2)` bằng `Point(1,2)`.
    - `ReferenceEquals(a, b)` là **`False`**: chúng vẫn là **hai đối tượng khác nhau** trên heap (record class là kiểu tham chiếu). Value equality khác reference equality.
    - `ToString` tự sinh in đẹp: `Point { X = 1, Y = 2 }`.
    - `a with { Y = 99 }` tạo **bản sao mới** (`a` không đổi), chỉ thay `Y`. Đây là **non-destructive mutation**. Mục 1-3 sẽ giải phẫu từng cơ chế này.

---

## 1. Vì sao cần record? Bài toán value object

Trong tầng nghiệp vụ, rất nhiều kiểu chỉ là **túi dữ liệu bất biến** mà "hai cái bằng nhau khi nội dung bằng nhau": toạ độ, tiền tệ, khoảng thời gian, DTO trả về từ API, message trong pipeline. Với `class` thường, bạn phải viết tay rất nhiều code lặp:

```csharp title="Class thường — value object viết TAY, dài và dễ sai"
// test:skip minh hoạ lượng boilerplate, không cần chạy
public sealed class Money
{
    public decimal Amount { get; }
    public string Currency { get; }

    public Money(decimal amount, string currency)
    {
        Amount = amount;
        Currency = currency;
    }

    // value equality: PHẢI override thủ công
    public override bool Equals(object? obj) =>
        obj is Money m && m.Amount == Amount && m.Currency == Currency;

    public override int GetHashCode() => HashCode.Combine(Amount, Currency);

    public static bool operator ==(Money? a, Money? b) => Equals(a, b);
    public static bool operator !=(Money? a, Money? b) => !Equals(a, b);

    // in đẹp: viết tay
    public override string ToString() => $"Money(Amount={Amount}, Currency={Currency})";

    // "sửa" mà không phá bản gốc: viết tay
    public Money WithAmount(decimal amount) => new(amount, Currency);
}
```

Hơn 20 dòng cho một kiểu 2 thuộc tính, và bạn có thể **quên đồng bộ** `Equals` với `GetHashCode` (một cạm bẫy kinh điển — hai object bằng nhau nhưng khác hash sẽ phá `Dictionary`/`HashSet`). Record ra đời (**C# 9**) để compiler làm toàn bộ việc này:

```csharp title="Record — cùng ngữ nghĩa, một dòng"
// test:run
var m1 = new Money(10m, "USD");
var m2 = new Money(10m, "USD");
Console.WriteLine(m1 == m2);      // True — value equality tự có
Console.WriteLine(m1);            // Money { Amount = 10, Currency = USD } — ToString tự có
Console.WriteLine(m1 with { Amount = 20m }); // Money { Amount = 20, Currency = USD }

record Money(decimal Amount, string Currency);
```

**Ý tưởng cốt lõi:** `record` là *cú pháp cho một kiểu mà danh tính = giá trị các thành viên*. Compiler tự sinh `Equals`, `GetHashCode`, `operator ==`/`!=`, `ToString`, `Deconstruct`, phương thức sao chép, và constructor. Bạn tập trung vào **ý nghĩa dữ liệu**, không phải boilerplate.

!!! danger "Đính chính hiểu lầm phổ biến"
    "Record là bất biến (immutable) hoàn toàn" — **SAI một nửa**. Record *khuyến khích* bất biến (positional record sinh property `init`, không có `set`), nhưng bạn hoàn toàn có thể khai báo property `set` (mutable) trong record. Cái *thật sự* định nghĩa record là **value equality**, không phải immutability. Xem mục 2.3.

---

## 2. `record class`: giải phẫu mọi thứ compiler sinh ra

Khai báo `record` (không kèm `struct`) mặc định là `record class` — một **kiểu tham chiếu** (nằm trên heap). Ta sẽ mổ từng thành phần compiler tạo.

### 2.1 Value equality — `Equals` / `GetHashCode` tự sinh

Compiler sinh `Equals(T? other)` so sánh **từng thành viên** (property/field được sinh từ positional, cộng field bạn tự khai báo), và `GetHashCode()` tổ hợp hash của chúng — luôn **đồng bộ với nhau**.

```csharp title="Value equality: so sánh nội dung, không so địa chỉ"
// test:run
var p1 = new Person("An", 30);
var p2 = new Person("An", 30);
var p3 = new Person("Bình", 25);

Console.WriteLine(p1.Equals(p2));       // True  — cùng nội dung
Console.WriteLine(p1 == p2);            // True  — operator == cũng gọi value equality
Console.WriteLine(p1.Equals(p3));       // False
Console.WriteLine(p1.GetHashCode() == p2.GetHashCode()); // True — hash cũng bằng

// hệ quả trực tiếp: dùng làm key trong HashSet/Dictionary "just works"
var set = new HashSet<Person> { p1 };
Console.WriteLine(set.Contains(p2));    // True — dù p2 là object khác

record Person(string Name, int Age);
```

```text title="Kết quả"
True
True
False
True
True
```

**Vì sao** value equality quan trọng: với `class` thường, `HashSet` dùng reference equality nên `set.Contains(p2)` sẽ ra `False` (p2 là object khác). Record làm value object hoạt động đúng trong mọi collection dựa trên hash.

### 2.2 `EqualityContract` — vì sao record khác class không thể "bằng"

Compiler sinh một property ẩn `protected virtual Type EqualityContract => typeof(T);`. `Equals` **so cả `EqualityContract`** trước khi so nội dung. Hệ quả: hai record **khác kiểu** không bao giờ bằng nhau, kể cả nội dung giống hệt.

```csharp title="EqualityContract chặn so sánh chéo kiểu"
// test:run
var cat = new Cat("Miu", 3);
var dog = new Dog("Miu", 3);

// object.Equals — nhìn qua thì "cùng Name, cùng Age"
Console.WriteLine(cat.Equals((object)dog)); // False — EqualityContract khác nhau

record Animal(string Name, int Age);
record Cat(string Name, int Age) : Animal(Name, Age);
record Dog(string Name, int Age) : Animal(Name, Age);
```

Điều này cũng giải thích một cạm bẫy kế thừa ở mục 2.7.

### 2.3 Immutability + `init`: positional sinh property chỉ-đọc

Với **positional record** (`record Point(int X, int Y)`), compiler sinh mỗi tham số thành một **public property có `init` accessor** (gán được lúc khởi tạo, sau đó khoá):

```csharp title="init: gán lúc tạo, cấm sửa sau đó"
// test:run
var p = new Config { Timeout = 30 }; // OK — object initializer chạy trong lúc khởi tạo
Console.WriteLine(p.Timeout);        // 30

// p.Timeout = 60;  // <-- nếu bỏ comment sẽ LỖI BIÊN DỊCH: init-only

record Config
{
    public int Timeout { get; init; }  // nominal record với init property
}
```

`init` khác `set` ở chỗ: chỉ cho phép gán trong **constructor** hoặc **object initializer**, sau đó property đóng băng. Nếu muốn record *mutable*, bạn khai báo `set` tường minh:

```csharp title="Record VẪN có thể mutable nếu bạn muốn (thường không nên)"
// test:run
var s = new Counter();
s.Value = 5;               // được — vì property dùng set
s.Value = 10;
Console.WriteLine(s.Value); // 10

record Counter
{
    public int Value { get; set; }  // mutable — hợp lệ nhưng phá tinh thần value object
}
```

!!! danger "Cạm bẫy: record mutable phá value equality theo thời gian"
    Nếu record có property `set` và bạn dùng nó làm key trong `Dictionary`, rồi *đổi giá trị sau khi thêm vào*, hash sẽ lệch và bạn "mất" phần tử. Value object nên **bất biến** — hãy giữ `init`, đừng dùng `set` trừ khi có lý do rất rõ ràng.

### 2.4 `with`-expression: non-destructive mutation

`with` tạo một **bản sao nông (shallow copy)** rồi ghi đè các thành viên bạn liệt kê. Bản gốc **không đổi** — đây là "mutation không phá huỷ".

```csharp title="with tạo bản sao mới, gốc bất biến"
// test:run
var v1 = new Vector(1, 2, 3);
var v2 = v1 with { Z = 30 };       // chỉ đổi Z
var v3 = v1 with { X = 10, Y = 20 }; // đổi nhiều thành viên

Console.WriteLine(v1); // Vector { X = 1, Y = 2, Z = 3 }  — gốc không đổi
Console.WriteLine(v2); // Vector { X = 1, Y = 2, Z = 30 }
Console.WriteLine(v3); // Vector { X = 10, Y = 20, Z = 3 }
Console.WriteLine(ReferenceEquals(v1, v2)); // False — object mới

record Vector(int X, int Y, int Z);
```

**Cơ chế bên dưới:** compiler sinh một constructor sao chép `protected Vector(Vector original)` và một phương thức ẩn `public virtual Vector <Clone>$()`. `with` gọi `<Clone>$()` (clone toàn bộ), rồi gán các thành viên trong `{ }`. Vì clone là **nông**, field tham chiếu (như `List`) được sao chép *địa chỉ*, không phải nội dung — nguồn của cạm bẫy ở mục 2.8.

```csharp title="with { } trống = clone y hệt"
// test:run
var a = new Person("An", 30);
var clone = a with { };            // sao chép hoàn toàn
Console.WriteLine(a == clone);            // True  — nội dung bằng
Console.WriteLine(ReferenceEquals(a, clone)); // False — object khác

record Person(string Name, int Age);
```

### 2.5 `ToString` tự sinh

Compiler sinh `ToString()` in dạng `TênKiểu { Prop1 = v1, Prop2 = v2 }`. Nó gọi một phương thức ảo `PrintMembers` mà lớp con có thể mở rộng — nên khi in record kế thừa, mọi property (cả lớp cha lẫn con) đều hiện.

```csharp title="ToString tự sinh, có tính kế thừa"
// test:run
Person emp = new Employee("An", 30, "Dev");
Console.WriteLine(emp); // Employee { Name = An, Age = 30, Role = Dev }

record Person(string Name, int Age);
record Employee(string Name, int Age, string Role) : Person(Name, Age);
```

### 2.6 Deconstruction — tách positional record thành biến

Positional record tự sinh `Deconstruct(out ...)` cho mọi tham số vị trí, cho phép tách nhanh — rất hợp với positional pattern (mục 4.7).

```csharp title="Deconstruction: một dòng tách hết"
// test:run
var p = new Point(3, 4);
var (x, y) = p;                    // gọi Deconstruct tự sinh
Console.WriteLine($"{x}, {y}");    // 3, 4

// bỏ qua thành phần không cần bằng discard _
var (_, onlyY) = p;
Console.WriteLine(onlyY);          // 4

record Point(int X, int Y);
```

!!! danger "Nominal record KHÔNG tự sinh Deconstruct"
    Chỉ **positional** record (có tham số trong ngoặc) mới có `Deconstruct`. Nếu bạn viết `record Foo { public int A {get;init;} }` (nominal), `var (a) = foo;` sẽ **lỗi biên dịch** vì không có `Deconstruct`. Muốn có, bạn tự viết `public void Deconstruct(out int a) => a = A;`.

### 2.7 Kế thừa giữa các record

Record class **được kế thừa** (record kế thừa record). Compiler nối `PrintMembers`, `Equals`, `GetHashCode`, và constructor sao chép theo chuỗi kế thừa. Nhưng nhớ `EqualityContract` (2.2): so sánh tôn trọng **kiểu runtime**.

```csharp title="Kế thừa record: Equals tôn trọng kiểu thực"
// test:run
Person a = new Employee("An", 30, "Dev");
Person b = new Person("An", 30);
Console.WriteLine(a.Equals(b));    // False — a thực chất là Employee, b là Person

Person c = new Employee("An", 30, "Dev");
Console.WriteLine(a.Equals(c));    // True  — cùng kiểu Employee, cùng nội dung

record Person(string Name, int Age);
record Employee(string Name, int Age, string Role) : Person(Name, Age);
```

!!! danger "Record KHÔNG kế thừa được từ class (và ngược lại)"
    `record` chỉ kế thừa được `record`; `class` chỉ kế thừa `class`. `record Foo : SomeClass` là **lỗi biên dịch** (trừ khi kế thừa `object` ngầm). Lý do: cơ chế equality tự sinh giả định toàn bộ chuỗi kế thừa cùng "hợp đồng" record.

### 2.8 Cạm bẫy equality KINH ĐIỂN: field là mảng / List

Đây là cái bẫy khiến rất nhiều người mất niềm tin vào record. Value equality tự sinh so sánh **từng thành viên bằng `EqualityComparer<T>.Default`**. Với `int`, `string` — đó là so sánh giá trị. Nhưng với `int[]`, `List<T>` — `Default` comparer của chúng là **reference equality**. Nghĩa là record chứa mảng/List so sánh mảng **theo địa chỉ, KHÔNG theo phần tử**.

```csharp title="BẪY: hai record cùng nội dung mảng nhưng KHÁC nhau"
// test:run
var t1 = new Team("A", new[] { "An", "Bình" });
var t2 = new Team("A", new[] { "An", "Bình" }); // mảng khác object, cùng phần tử

Console.WriteLine(t1 == t2);   // False (!!) — mảng so theo tham chiếu

// nếu dùng CHUNG một mảng thì lại bằng
var shared = new[] { "An", "Bình" };
var t3 = new Team("A", shared);
var t4 = new Team("A", shared);
Console.WriteLine(t3 == t4);   // True — cùng địa chỉ mảng

record Team(string Name, string[] Members);
```

```text title="Kết quả"
False
True
```

**Cách sửa:** override `Equals`/`GetHashCode` để so theo phần tử, hoặc dùng kiểu collection có value equality như `ImmutableArray<T>` kết hợp comparer, hoặc bọc bằng một record với `IStructuralEquatable`. Cách gọn nhất là tự viết:

```csharp title="Sửa: so sánh mảng theo phần tử"
// test:run
var t1 = new Team("A", new[] { "An", "Bình" });
var t2 = new Team("A", new[] { "An", "Bình" });
Console.WriteLine(t1 == t2);   // True — nay so theo phần tử

record Team(string Name, string[] Members)
{
    public virtual bool Equals(Team? other) =>
        other is not null
        && Name == other.Name
        && Members.SequenceEqual(other.Members);   // so từng phần tử

    public override int GetHashCode()
    {
        var hc = new HashCode();
        hc.Add(Name);
        foreach (var m in Members) hc.Add(m);      // hash theo phần tử → đồng bộ Equals
        return hc.GetHashCode();
    }
}
```

!!! danger "Khi override Equals của record, dùng chữ ký ĐÚNG"
    Phải là `public virtual bool Equals(Team? other)` (virtual, tham số kiểu chính record đó). Nếu viết `public override bool Equals(object? obj)` như class thường, compiler sẽ báo lỗi/ cảnh báo vì nó xung đột với `Equals(Team?)` tự sinh. Và **luôn override `GetHashCode` cùng lúc** để giữ đồng bộ.

---

## 3. `record struct`, `readonly record struct` (C# 10) và cách chọn kiểu

### 3.1 `record struct` — value equality trên kiểu giá trị

`record struct` (ra ở **C# 10**) là **kiểu giá trị** (nằm trên stack / inline trong object cha, không cấp phát heap riêng), nhưng vẫn được compiler sinh value equality, `ToString`, `Deconstruct`, `with`.

```csharp title="record struct: nhẹ như struct, tiện như record"
// test:run
var a = new Coord(1, 2);
var b = new Coord(1, 2);
Console.WriteLine(a == b);         // True — value equality
Console.WriteLine(a);              // Coord { X = 1, Y = 2 }
var c = a with { Y = 9 };          // with cũng dùng được
Console.WriteLine(c);              // Coord { X = 1, Y = 9 }

record struct Coord(int X, int Y);
```

**Khác biệt then chốt so với `record class`:**

| Khía cạnh | `record class` | `record struct` | `readonly record struct` |
|---|---|---|---|
| Loại kiểu | tham chiếu (heap) | giá trị (stack/inline) | giá trị (stack/inline) |
| Property positional sinh ra | `{ get; init; }` (bất biến) | `{ get; set; }` (**mutable!**) | `{ get; init; }` (bất biến) |
| Kế thừa | có (record ↔ record) | **không** (struct không kế thừa) | **không** |
| `null` hợp lệ? | có (kiểu tham chiếu) | không (cần `Nullable<T>`) | không |
| Equality | so thành viên + `EqualityContract` | so thành viên (không EqualityContract) | so thành viên |
| Cấp phát | 1 lần trên heap | không cấp phát heap | không cấp phát heap |
| Toàn bộ struct bất biến | — | không (field vẫn ghi được) | **có** (`readonly` toàn bộ) |

!!! danger "BẪY ít ai để ý: record struct MẶC ĐỊNH mutable"
    `record struct Coord(int X, int Y)` sinh property **`set`**, không phải `init`. Nghĩa là `var c = new Coord(1,2); c.X = 5;` **hợp lệ**. Điều này ngược với `record class` (sinh `init`). Nếu bạn muốn value object bất biến thật sự, dùng **`readonly record struct`** — nó ép mọi field `readonly` và property thành `init`.

```csharp title="record struct MUTABLE vs readonly record struct BẤT BIẾN"
// test:run
var m = new MCoord(1, 2);
m.X = 100;                 // OK — record struct thường: property có set
Console.WriteLine(m.X);    // 100

var r = new RCoord(1, 2);
// r.X = 100;              // <-- LỖI BIÊN DỊCH nếu bỏ comment: init-only trong readonly struct
Console.WriteLine(r.X);    // 1

record struct MCoord(int X, int Y);
readonly record struct RCoord(int X, int Y);
```

### 3.2 positional vs nominal record

- **Positional** `record Point(int X, int Y)`: tham số vị trí → primary constructor + property + `Deconstruct` tự sinh. Ngắn gọn, hợp value object nhỏ.
- **Nominal** `record Point { public int X {get;init;} public int Y {get;init;} }`: khai báo property tường minh, khởi tạo bằng object initializer, **không tự sinh `Deconstruct`**, không có primary constructor. Hợp khi cần property có default, validation, hoặc nhiều property tuỳ chọn.

```csharp title="Positional vs nominal — kết hợp được"
// test:run
// positional + thêm property tính toán và validation trong body
var acc = new Account("VN01", 100m);
Console.WriteLine(acc.IsRich);      // False
Console.WriteLine(acc);             // Account { Id = VN01, Balance = 100, IsRich = False }

record Account(string Id, decimal Balance)
{
    public bool IsRich => Balance > 1000m;   // property phái sinh, cũng vào ToString
}
```

### 3.3 Khi nào dùng record vs class vs struct

| Bạn cần… | Chọn |
|---|---|
| Túi dữ liệu bất biến, danh tính = giá trị (DTO, value object, message) | `record class` |
| Như trên nhưng nhỏ (≤ ~16 byte), sống ngắn, tránh cấp phát heap | `readonly record struct` |
| Entity có danh tính riêng (Id), trạng thái thay đổi theo thời gian | `class` |
| Kiểu giá trị nhỏ, hiệu năng cao, không cần value equality tự sinh | `struct` / `readonly struct` |
| Cần kế thừa đa tầng + value equality | `record class` (record struct không kế thừa được) |

**Quy tắc ngón tay cái:** "Nếu hai cái *nội dung giống nhau* nên được coi là *bằng nhau* → record. Nếu nó có **danh tính riêng** (một `User` với `Id=5` vẫn là user đó dù đổi tên) → `class`."

---

## 4. Pattern matching: ĐẦY ĐỦ TỪNG loại pattern

Pattern matching là *kiểm tra một giá trị có khớp một khuôn mẫu không, đồng thời trích dữ liệu ra*. C# có nhiều loại pattern; ta đi **hết**, mỗi loại một ví dụ chạy được.

### 4.1 Constant pattern — khớp hằng số

Khớp khi giá trị **bằng** một hằng (số, chuỗi, `char`, `bool`, `null`, enum, hằng `const`).

```csharp title="Constant pattern"
// test:run
static string Classify(int n) => n switch
{
    0 => "không",
    1 => "một",
    _ => "khác"
};
Console.WriteLine(Classify(0));   // không
Console.WriteLine(Classify(5));   // khác

// null cũng là constant pattern:
object? o = null;
Console.WriteLine(o is null);     // True
```

### 4.2 Type pattern & declaration pattern

- **Type pattern**: `is Kiểu` — kiểm tra kiểu runtime.
- **Declaration pattern**: `is Kiểu tên` — kiểm tra kiểu **và** gán vào biến mới (đã ép kiểu sẵn).

```csharp title="Type & declaration pattern"
// test:run
static string Describe(object o) => o switch
{
    int i => $"số nguyên {i}",           // declaration: gán vào i
    string s => $"chuỗi dài {s.Length}", // declaration
    double => "một double nào đó",       // type pattern: không cần tên
    _ => "không rõ"
};
Console.WriteLine(Describe(42));       // số nguyên 42
Console.WriteLine(Describe("hello"));  // chuỗi dài 5
Console.WriteLine(Describe(3.14));     // một double nào đó
```

### 4.3 `var` pattern — luôn khớp, gán tên

`var x` khớp **mọi** giá trị (kể cả `null`) và gán vào `x` với kiểu suy luận. Hữu ích để "bắt" giá trị trung gian rồi dùng trong `when`.

```csharp title="var pattern + when"
// test:run
static string Sign((int a, int b) t) => t switch
{
    var (a, b) when a + b > 0 => "tổng dương",
    var (a, b) when a + b < 0 => "tổng âm",
    _ => "tổng bằng 0"
};
Console.WriteLine(Sign((3, 4)));   // tổng dương
Console.WriteLine(Sign((-5, 1)));  // tổng âm
Console.WriteLine(Sign((2, -2)));  // tổng bằng 0
```

!!! danger "var pattern khớp cả null"
    `x is var y` **luôn** đúng, kể cả `x` là `null` — `y` sẽ là `null`. Đừng dùng `is var` để lọc null; nó không lọc gì cả.

### 4.4 Discard `_` — khớp mọi thứ, không giữ

`_` khớp bất kỳ giá trị nào nhưng **không tạo biến**. Trong `switch` expression, một arm `_ =>` là **nhánh mặc định** (catch-all).

```csharp title="Discard trong deconstruction và switch"
// test:run
var p = new Point(3, 4);
var (_, y) = p;               // bỏ X, lấy Y
Console.WriteLine(y);         // 4

static string Q(int n) => n switch
{
    > 0 => "dương",
    _ => "không dương"        // _ = default arm
};
Console.WriteLine(Q(-1));     // không dương

record Point(int X, int Y);
```

### 4.5 Property pattern (kể cả lồng)

Khớp theo **giá trị property/field**. Có thể **lồng** để đào sâu vào object con.

```csharp title="Property pattern phẳng và LỒNG"
// test:run
var order = new Order(new Customer("An", new Address("HN", "VN")), 500m);

static string Ship(Order o) => o switch
{
    // property pattern LỒNG: đào vào Customer.Address.Country
    { Customer.Address.Country: "VN", Total: > 100m } => "nội địa, freeship",
    { Customer.Address.Country: "VN" } => "nội địa",
    _ => "quốc tế"
};
Console.WriteLine(Ship(order)); // nội địa, freeship

record Address(string City, string Country);
record Customer(string Name, Address Address);
record Order(Customer Customer, decimal Total);
```

!!! danger "Property pattern với null — cạm bẫy im lặng"
    `{ Prop: ... }` **âm thầm không khớp** nếu object là `null` (không ném NullReferenceException — an toàn). Nhưng nếu bạn cần *phân biệt* null với "không khớp", hãy thêm arm `null =>` **TRƯỚC**. Ví dụ `{ Address.Country: "VN" }` khi `Address` là null → arm này *không khớp*, rơi xuống arm sau; nó không nổ, nhưng dễ khiến bạn tưởng "khách VN" bị xếp nhầm. Thêm `{ Address: null } => ...` cho rõ ý.

### 4.6 Relational pattern (`<` `>` `<=` `>=`)

So sánh với hằng, ghép cực gọn cho phân khoảng. (Ra ở **C# 9**.)

```csharp title="Relational pattern + kết hợp thành khoảng"
// test:run
static string Grade(int score) => score switch
{
    >= 90 => "A",
    >= 80 => "B",
    >= 70 => "C",
    >= 50 => "D",
    _ => "F"
};
Console.WriteLine(Grade(95)); // A
Console.WriteLine(Grade(72)); // C
Console.WriteLine(Grade(40)); // F
```

### 4.7 Positional pattern (deconstruct trong pattern)

Khớp bằng cách **deconstruct** (từ record hoặc tuple hoặc kiểu có `Deconstruct`), rồi khớp từng vị trí.

```csharp title="Positional pattern trên record & tuple"
// test:run
var p = new Point(0, 5);

static string Where(Point pt) => pt switch
{
    (0, 0) => "gốc toạ độ",
    (0, _) => "trên trục Y",
    (_, 0) => "trên trục X",
    (var x, var y) when x == y => "đường chéo",
    _ => "đâu đó"
};
Console.WriteLine(Where(p));                 // trên trục Y
Console.WriteLine(Where(new Point(3, 3)));   // đường chéo

record Point(int X, int Y);
```

### 4.8 Logical pattern: `and` / `or` / `not`

Ghép các pattern con bằng logic. Độ ưu tiên: `not` > `and` > `or` (dùng ngoặc để rõ).

```csharp title="Logical pattern"
// test:run
static string Temp(int c) => c switch
{
    < 0 or > 40 => "nguy hiểm",           // or
    >= 18 and <= 26 => "dễ chịu",         // and — khoảng đóng
    not (>= 18 and <= 26) => "chấp nhận được",
};
Console.WriteLine(Temp(-5));  // nguy hiểm
Console.WriteLine(Temp(22));  // dễ chịu
Console.WriteLine(Temp(35));  // chấp nhận được

// not dùng thay cho != null rất gọn:
object? o = "x";
Console.WriteLine(o is not null); // True
```

!!! danger "`x is not null` an toàn hơn `x != null`"
    Với kiểu có overload `operator !=` (như một số class), `x != null` có thể gọi code người dùng và cho kết quả bất ngờ. `is not null` **luôn** là kiểm tra null thuần tuý của runtime, không gọi operator nào. Nên ưu tiên `is null` / `is not null`.

### 4.9 List pattern & slice pattern (`..`) — C# 11

**List pattern** (ra ở **C# 11**) khớp phần tử của mảng/`List`/`Span` theo vị trí. **Slice pattern** `..` khớp "không hoặc nhiều phần tử", và có thể bắt phần giữa vào biến.

```csharp title="List pattern + slice pattern"
// test:run
int[] a = { 1, 2, 3 };

Console.WriteLine(a is [1, 2, 3]);     // True — khớp chính xác 3 phần tử
Console.WriteLine(a is [1, .., 3]);    // True — đầu 1, cuối 3, giữa bất kỳ
Console.WriteLine(a is [_, _, _]);     // True — đúng 3 phần tử bất kỳ
Console.WriteLine(a is [1, 2]);        // False — sai số lượng

// bắt phần tử đầu và phần đuôi:
if (a is [var first, .. var rest])
    Console.WriteLine($"đầu={first}, đuôi có {rest.Length} phần tử"); // đầu=1, đuôi có 2

// list pattern trong switch:
static string Shape(int[] xs) => xs switch
{
    [] => "rỗng",
    [var only] => $"một phần tử: {only}",
    [var h, .. var t] => $"đầu {h}, còn {t.Length}",
};
Console.WriteLine(Shape(new int[0]));      // rỗng
Console.WriteLine(Shape(new[] { 42 }));    // một phần tử: 42
Console.WriteLine(Shape(new[] { 1,2,3 })); // đầu 1, còn 2
```

```text title="Kết quả"
True
True
True
False
đầu=1, đuôi có 2 phần tử
rỗng
một phần tử: 42
đầu 1, còn 2
```

!!! danger "Chỉ được MỘT slice `..` trong một list pattern"
    `[.., 3, ..]` là **lỗi biên dịch** — không thể có hai slice mở vì compiler không biết cắt ở đâu. Slice có thể ở đầu `[.., x]`, giữa `[a, .., b]`, hoặc cuối `[a, ..]`, nhưng chỉ một cái.

### 4.10 Parenthesized pattern — nhóm bằng ngoặc

`( )` nhóm pattern để đảo/định độ ưu tiên khi kết hợp logical pattern.

```csharp title="Parenthesized pattern"
// test:run
static bool Weird(int n) => n is not (> 0 and < 10);
Console.WriteLine(Weird(5));   // False — 5 nằm trong (0,10) nên "not (...)" là False
Console.WriteLine(Weird(50));  // True
Console.WriteLine(Weird(-1));  // True
```

---

## 5. `switch` expression: cú pháp, guard, vét cạn

### 5.1 Cú pháp arm, `when` guard, `_`

`switch` **expression** trả về *giá trị* (khác `switch` *statement* cũ chỉ chạy lệnh). Mỗi **arm** là `pattern => biểu_thức`, phân tách bằng dấu phẩy. `when` thêm điều kiện boolean sau khi pattern khớp.

```csharp title="switch expression đầy đủ arm + when + _"
// test:run
static string Fare(string kind, int age) => (kind, age) switch
{
    ("VIP", _) => "500k",                       // positional trên tuple
    (_, < 6) => "miễn phí",                     // trẻ dưới 6
    (_, >= 60) => "150k",                       // người cao tuổi
    ("normal", var a) when a is >= 6 and < 60 => "300k", // when guard
    _ => "không xác định"                        // catch-all
};
Console.WriteLine(Fare("VIP", 40));    // 500k
Console.WriteLine(Fare("normal", 3));  // miễn phí
Console.WriteLine(Fare("normal", 30)); // 300k
Console.WriteLine(Fare("normal", 70)); // 150k
```

### 5.2 Tính vét cạn (exhaustiveness) & cảnh báo

Compiler kiểm tra `switch` expression có phủ **mọi** giá trị đầu vào không. Nếu thiếu, nó **cảnh báo** `CS8509` và, khi chạy tới giá trị không arm nào khớp, ném `SwitchExpressionException`. Với enum, thêm giá trị mới mà quên cập nhật switch cũng bị cảnh báo.

```csharp title="Không vét cạn → ném SwitchExpressionException lúc chạy"
// test:run
static string OnlyPositive(int n) => n switch
{
    > 0 => "dương"
    // thiếu nhánh cho 0 và số âm → compiler CẢNH BÁO CS8509
};

try
{
    Console.WriteLine(OnlyPositive(-1)); // không arm nào khớp
}
catch (Exception ex)
{
    Console.WriteLine(ex.GetType().Name); // SwitchExpressionException
}
```

```text title="Kết quả"
SwitchExpressionException
```

**Cách sửa:** luôn có arm `_ =>` mặc định, hoặc phủ hết mọi khoảng. Với enum nên vẫn để `_ =>` để phòng giá trị mới thêm sau này.

### 5.3 Cạm bẫy THỨ TỰ ARM

`switch` expression thử arm **từ trên xuống**, dừng ở arm đầu tiên khớp. Đặt arm **rộng** trước arm **hẹp** → arm hẹp thành *chết* (unreachable). Với `switch` **expression** (khác `switch` statement), đây KHÔNG chỉ là cảnh báo — trình biên dịch **từ chối biên dịch** với lỗi `CS8510` ("pattern is unreachable"). Đây là điểm hay: compiler tự bắt lỗi logic này trước khi bạn kịp chạy code.

```csharp title="Thứ tự arm SAI: arm rộng nuốt arm hẹp — LỖI BIÊN DỊCH, không chạy được"
// test:skip cố ý minh hoạ lỗi biên dịch CS8510 (pattern is unreachable) — xem giải thích
static string Wrong(int n) => n switch
{
    > 0 => "dương",     // arm RỘNG đứng trước
    > 100 => "rất lớn", // <-- LỖI CS8510: unreachable, "> 100" đã bị "> 0" nuốt
    _ => "khác"
};
```

Đúng thì phải đặt arm hẹp/cụ thể **trước**:

```csharp title="Thứ tự arm ĐÚNG: hẹp trước, rộng sau"
// test:run
static string Right(int n) => n switch
{
    > 100 => "rất lớn", // hẹp trước
    > 0 => "dương",     // rộng sau
    _ => "khác"
};
Console.WriteLine(Right(500)); // rất lớn
Console.WriteLine(Right(50));  // dương
```

---

## 6. `is`-pattern trong `if`, và pattern trong `while`

Pattern không chỉ dùng trong `switch`. `is` kết hợp declaration pattern là idiom kiểm-tra-và-ép-kiểu gọn nhất; nó cũng dùng được trong điều kiện `while`.

```csharp title="is-pattern trong if: kiểm tra + ép kiểu + null-check một dòng"
// test:run
static void Handle(object? o)
{
    if (o is string s && s.Length > 3)   // ép kiểu, gán s, và guard
        Console.WriteLine($"chuỗi dài: {s}");
    else if (o is int i and > 0)         // pattern kết hợp trong if
        Console.WriteLine($"số dương: {i}");
    else if (o is null)
        Console.WriteLine("null");
    else
        Console.WriteLine("khác");
}
Handle("hello"); // chuỗi dài: hello
Handle(42);      // số dương: 42
Handle(null);    // null
Handle(1.5);     // khác
```

```csharp title="pattern trong while: lặp tới khi hết khớp"
// test:run
var stack = new Stack<int>(new[] { 1, 2, 3 });
// TryPop trả (bool, out); nhưng minh hoạ pattern trong while bằng Count:
while (stack is { Count: > 0 })          // property pattern trong điều kiện while
{
    Console.WriteLine(stack.Pop());
}
// in ra 3, 2, 1

// ví dụ khác: đọc tới khi gặp null (giả lập)
var queue = new Queue<string?>(new[] { "a", "b", null, "c" });
while (queue.Count > 0 && queue.Dequeue() is { } item) // { } = "not null"
    Console.WriteLine(item);
// in a, b rồi dừng ở null
```

```text title="Kết quả"
3
2
1
a
b
```

!!! danger "`{ }` (property pattern rỗng) nghĩa là NOT NULL"
    `x is { }` khớp khi `x` **khác null** (bất kể property). Nó tương đương `x is not null` nhưng đọc lạ. `x is { }` và `x is object` cùng ý; chọn cách nào dễ đọc cho đồng đội.

---

## Cạm bẫy & thực chiến

1. **Field mảng/List phá value equality** (mục 2.8). Record `{ Data: int[] }` so mảng theo *tham chiếu*. Trong DTO có collection, hoặc override `Equals`+`GetHashCode` theo phần tử, hoặc dùng `ImmutableArray` với structural comparer, hoặc chấp nhận và document rõ.

2. **`record struct` mặc định mutable.** `record struct Coord(int X, int Y)` sinh `set`, không phải `init`. Nếu bạn *muốn* value object bất biến (thường là vậy), luôn viết **`readonly record struct`**. Quên chữ `readonly` là bug âm thầm.

3. **Thứ tự arm trong switch expression.** Arm rộng đặt trước nuốt arm hẹp (mục 5.3) → **lỗi biên dịch** `CS8510` (unreachable), không phải chỉ cảnh báo. Luôn xếp **cụ thể → tổng quát**.

4. **Quên nhánh mặc định `_`.** Không vét cạn → cảnh báo `CS8509` + `SwitchExpressionException` lúc runtime. Luôn có `_ =>` trừ khi bạn *chắc chắn* đã phủ hết (và ngay cả với enum vẫn nên có, phòng giá trị enum mới).

5. **Property pattern với null.** `{ Prop: value }` không nổ khi object null, nó chỉ *không khớp* — dễ khiến case null rơi nhầm vào nhánh khác. Nếu null có ý nghĩa riêng, thêm arm `null =>` hoặc `{ } =>` **trước**.

6. **`with` là clone NÔNG.** `record` chứa `List` → `a with { X = 1 }` sao chép *cùng địa chỉ* `List`. Sửa `List` trong bản sao cũng đổi bản gốc. Muốn bản sao độc lập phải clone collection thủ công: `a with { Items = a.Items.ToList() }`.

7. **Override `Equals` sai chữ ký trong record.** Phải `public virtual bool Equals(T? other)`, không phải `override bool Equals(object?)`. Và luôn kèm `GetHashCode`.

8. **`is var` không lọc null.** `x is var y` luôn đúng. Dùng để bắt giá trị, không dùng để kiểm null. Kiểm null dùng `is not null` / `is { }`.

---

## Bài tập

### Bài 1 (giàn giáo): Value object `Money`

Viết một `record` `Money(decimal Amount, string Currency)` sao cho: (a) hai `Money` cùng amount + currency thì bằng nhau; (b) có phương thức `Add` cộng hai `Money` **cùng loại tiền** (khác loại thì ném `InvalidOperationException`), trả về `Money` mới (không sửa bản gốc). Chứng minh bằng vài dòng.

??? note "Lời giải"
    ```csharp title="Bài 1 — lời giải"
    // test:run
    var a = new Money(10m, "USD");
    var b = new Money(5m, "USD");
    var c = a.Add(b);
    Console.WriteLine(c);                 // Money { Amount = 15, Currency = USD }
    Console.WriteLine(a);                 // Money { Amount = 10, Currency = USD } — gốc không đổi
    Console.WriteLine(a == new Money(10m, "USD")); // True — value equality

    try
    {
        a.Add(new Money(1m, "EUR"));      // khác loại tiền
    }
    catch (InvalidOperationException ex)
    {
        Console.WriteLine($"Chặn: {ex.Message}"); // Chặn: Khác loại tiền
    }

    record Money(decimal Amount, string Currency)
    {
        public Money Add(Money other)
        {
            if (Currency != other.Currency)
                throw new InvalidOperationException("Khác loại tiền");
            return this with { Amount = Amount + other.Amount };
        }
    }
    ```
    Điểm mấu chốt: dùng `with` để tạo bản mới thay vì mutate; value equality có sẵn nên không cần viết `Equals`.

### Bài 2 (thiết kế): Cây biểu thức + `switch` expression đệ quy

Cho các record biểu thức số học: `Num(double Value)`, `Add(Expr L, Expr R)`, `Mul(Expr L, Expr R)` (đều kế thừa `Expr`). Viết hàm `Eval(Expr e)` dùng **switch expression + positional pattern** để tính giá trị. Tính `(2 + 3) * 4`.

??? note "Lời giải"
    ```csharp title="Bài 2 — lời giải"
    // test:run
    Expr tree = new Mul(new Add(new Num(2), new Num(3)), new Num(4));
    Console.WriteLine(Eval(tree)); // 20

    static double Eval(Expr e) => e switch
    {
        Num(var v)      => v,                    // positional pattern rút Value
        Add(var l, var r) => Eval(l) + Eval(r),  // đệ quy
        Mul(var l, var r) => Eval(l) * Eval(r),
        _ => throw new InvalidOperationException("Nút lạ")
    };

    abstract record Expr;
    record Num(double Value) : Expr;
    record Add(Expr L, Expr R) : Expr;
    record Mul(Expr L, Expr R) : Expr;
    ```
    Đây là mẫu **discriminated union giả lập** trong C#: `abstract record` cha + các record con, xử lý bằng switch expression theo type/positional pattern. Rất mạnh cho parser, interpreter, xử lý message.

### Bài 3 (thử thách): Phân loại "bàn tay" bài bằng list pattern

Cho một tay bài là `int[]` các giá trị đã **sắp xếp tăng dần** (3 lá, giá trị 1-13). Viết `Rank(int[] hand)` dùng **list pattern** để trả: `"ba lá giống"` nếu cả ba bằng nhau; `"sảnh"` nếu ba lá liên tiếp; `"đôi"` nếu đúng hai lá bằng nhau; ngược lại `"mậu thầu"`. Test với `[7,7,7]`, `[4,5,6]`, `[2,2,9]`, `[1,5,10]`.

??? note "Lời giải"
    ```csharp title="Bài 3 — lời giải"
    // test:run
    Console.WriteLine(Rank(new[] { 7, 7, 7 }));  // ba lá giống
    Console.WriteLine(Rank(new[] { 4, 5, 6 }));  // sảnh
    Console.WriteLine(Rank(new[] { 2, 2, 9 }));  // đôi
    Console.WriteLine(Rank(new[] { 1, 5, 10 })); // mậu thầu

    static string Rank(int[] hand) => hand switch
    {
        [var a, var b, var c] when a == b && b == c => "ba lá giống",
        [var a, var b, var c] when b == a + 1 && c == b + 1 => "sảnh",
        [var a, var b, var c] when a == b || b == c => "đôi",  // đã sort nên đôi luôn kề nhau
        [_, _, _] => "mậu thầu",
        _ => "tay bài không hợp lệ"     // khác 3 lá
    };
    ```
    Điểm mấu chốt: list pattern `[var a, var b, var c]` vừa **ràng buộc đúng 3 phần tử** vừa **bắt tên**; `when` xử lý logic so sánh. Vì input đã sort, "đôi" chỉ cần kiểm hai lá kề nhau. Arm `_ =>` cuối phòng mảng khác 3 phần tử để switch vét cạn.

---

## Tự kiểm tra

Trả lời rồi mở đáp án.

1. Điều gì **thật sự** định nghĩa một record, immutability hay value equality?
   ??? note "Đáp án"
       **Value equality**. Record có thể mutable (property `set`) nhưng vẫn là record. Cái compiler luôn sinh và luôn là bản chất record: `Equals`/`GetHashCode`/`operator ==` so theo giá trị thành viên (+ `EqualityContract` với record class).

2. `new Team("A", new[]{"x"}) == new Team("A", new[]{"x"})` cho kết quả gì với `record Team(string Name, string[] Members)`? Vì sao?
   ??? note "Đáp án"
       **`False`**. Field `string[]` so bằng `EqualityComparer<string[]>.Default` = **reference equality**; hai mảng là hai object khác nhau. Muốn `True` phải override `Equals`+`GetHashCode` so theo phần tử (`SequenceEqual`).

3. Khác biệt property positional sinh ra giữa `record class` và `record struct` (không `readonly`)?
   ??? note "Đáp án"
       `record class` sinh property **`init`** (bất biến). `record struct` sinh property **`set`** (mutable). Muốn record struct bất biến phải dùng `readonly record struct` (sinh `init` + field `readonly`).

4. Trong switch expression, đặt `> 0 =>` trước `> 100 =>` gây ra chuyện gì?
   ??? note "Đáp án"
       Arm `> 100` trở thành **unreachable** (không bao giờ chạy được) vì `> 0` đã nuốt mọi số > 0, kể cả > 100. Với switch **expression**, đây là **lỗi biên dịch** `CS8510`, code sẽ không compile được chứ không chỉ chạy sai. Phải xếp arm hẹp (`> 100`) **trước** arm rộng (`> 0`).

5. `x is var y` khi `x` là `null` cho kết quả gì?
   ??? note "Đáp án"
       **Luôn `True`**, và `y` sẽ là `null`. `var` pattern khớp mọi giá trị, không lọc null. Muốn lọc null dùng `is not null` hoặc `is { }`.

6. `a with { }` (ngoặc rỗng) làm gì? Object kết quả có `ReferenceEquals` với `a` không?
   ??? note "Đáp án"
       Tạo một **bản sao nông** giống hệt `a`. `a == kết_quả` là `True` (value equality) nhưng `ReferenceEquals(a, kết_quả)` là **`False`** (object mới). Đây là clone không phá huỷ.

7. Vì sao một `record Cat` và một `record Dog` cùng kế thừa `Animal`, cùng `Name`/`Age`, lại **không** bằng nhau?
   ??? note "Đáp án"
       Vì `Equals` tự sinh so cả `EqualityContract` (= `typeof` kiểu runtime). `Cat` có `EqualityContract == typeof(Cat)`, `Dog` có `typeof(Dog)` → khác nhau → không bằng, dù nội dung giống.

8. Bao nhiêu slice `..` được phép trong một list pattern? Cho ví dụ hợp lệ và không hợp lệ.
   ??? note "Đáp án"
       Tối đa **một** `..`. Hợp lệ: `[1, .., 9]`, `[.., x]`, `[a, ..]`. Không hợp lệ (lỗi biên dịch): `[.., 3, ..]` — hai slice khiến compiler không biết cắt ở đâu.

---

??? abstract "DEEP DIVE: cơ chế tầng dưới (IL / runtime / hiệu năng)"
    **1. Compiler sinh gì cho `record Point(int X, int Y)`?** Nhìn qua IL/decompiler, bạn sẽ thấy:
    ```csharp title="Phiên bản 'giải nén' record (khái niệm)"
    // test:skip minh hoạ cái compiler sinh, không tự chạy độc lập
    public class Point : IEquatable<Point>
    {
        public int X { get; init; }
        public int Y { get; init; }
        public Point(int X, int Y) { this.X = X; this.Y = Y; }

        protected virtual Type EqualityContract => typeof(Point);

        public virtual bool Equals(Point? other) =>
            other is not null
            && EqualityContract == other.EqualityContract
            && EqualityComparer<int>.Default.Equals(X, other.X)
            && EqualityComparer<int>.Default.Equals(Y, other.Y);

        public override bool Equals(object? obj) => Equals(obj as Point);

        public override int GetHashCode() =>
            (EqualityComparer<Type>.Default.GetHashCode(EqualityContract) * -1521134295
             + EqualityComparer<int>.Default.GetHashCode(X)) * -1521134295
             + EqualityComparer<int>.Default.GetHashCode(Y);

        public static bool operator ==(Point? a, Point? b) =>
            (object)a == b || (a?.Equals(b) ?? false);
        public static bool operator !=(Point? a, Point? b) => !(a == b);

        protected Point(Point original) { X = original.X; Y = original.Y; } // copy ctor
        public virtual Point <Clone>$() => new Point(this);                  // dùng cho with

        public override string ToString()
        {
            var sb = new StringBuilder();
            sb.Append("Point { ");
            if (PrintMembers(sb)) sb.Append(' ');
            sb.Append('}');
            return sb.ToString();
        }
        protected virtual bool PrintMembers(StringBuilder sb)
        {
            sb.Append("X = ").Append(X).Append(", Y = ").Append(Y);
            return true;
        }
    }
    ```
    Ghi chú: `EqualityContract` là **virtual** → lớp con record override nó, đó là cách so-sánh-theo-kiểu-runtime hoạt động. `<Clone>$` là tên phương thức compiler đặt (ký tự `<>` không hợp lệ trong C# nguồn nên bạn không gọi trực tiếp; `with` dịch thành lời gọi nó rồi gán property).

    **2. `with` dịch thành gì?** `var c = a with { Y = 30 };` ≈
    ```csharp title="with sau desugar (khái niệm)"
    // test:skip
    var __tmp = a.<Clone>$();  // clone nông toàn bộ
    __tmp.Y = 30;              // gán vào init/backing field trong ngữ cảnh khởi tạo
    var c = __tmp;
    ```
    Vì thế `with` chỉ đắt bằng **một lần cấp phát + copy field nông**. Field tham chiếu chỉ copy con trỏ → nguồn cạm bẫy 6.

    **3. `record struct` và cấp phát:** vì là kiểu giá trị, `record struct` **không cấp phát heap** khi là biến cục bộ hay field inline; `Equals`/`GetHashCode` không so `EqualityContract` (struct không có kế thừa nên không cần). `with` trên struct là **copy giá trị trên stack** — cực rẻ, không tạo rác GC. Đây là lý do `readonly record struct` lý tưởng cho value object nóng (hot path) như toạ độ, id đóng gói.

    **4. Pattern matching biên dịch thành gì?** `switch` expression với các relational/type pattern **không** phải chuỗi `if` ngây thơ. Compiler xây một **decision tree**: nó gom các test theo kiểu và hằng, dùng nhảy (jump) hiệu quả, và với constant pattern số nguyên/chuỗi dày đặc có thể sinh **jump table** (như `switch` IL truyền thống) — O(1) thay vì O(n) so tuần tự. Type pattern dịch thành `isinst` (IL) + kiểm null. List pattern dịch thành kiểm `Length`/`Count` rồi index từng phần tử; slice `..` dùng `[start..end]` (indexer Range) nếu kiểu hỗ trợ, hoặc `Slice`. Vì vậy list pattern trên `Span<T>` không tạo rác.

    **5. Exhaustiveness là phân tích compile-time:** compiler mô hình hoá miền giá trị (đặc biệt tốt với `enum`, `bool`, kiểu bao đóng như record hierarchy có `sealed`) và cảnh báo nếu có "khe hở". Đánh dấu record cha `abstract` + con `sealed` giúp compiler suy luận vét cạn tốt hơn và cảnh báo chính xác khi bạn quên một biến thể.

Tiếp theo -> generics
