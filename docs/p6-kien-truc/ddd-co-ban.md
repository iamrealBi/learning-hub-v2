---
tier: core
status: core
owner: core-team
verified_on: "2026-07-05"
dotnet_version: "10.0"
bloom: phân biệt
requires: [p6-cqrs]
est_minutes_fast: 34
---

# Domain-Driven Design cơ bản: Entity, Value Object, Aggregate

!!! info "bạn đang ở đây · p6 → node `p6-ddd` · kiến trúc/pattern"
    **cần trước:** CQRS — vì DDD ở đây tổ chức *bên trong* model nghiệp vụ, còn CQRS tổ chức luồng đọc/ghi ở lớp application; hai thứ bổ sung cho nhau, không thay thế nhau.
    **mở khoá:** phân biệt được ba khối xây dựng cốt lõi của DDD (Entity, Value Object, Aggregate) và nhận ra lúc nào một `record` C# đã đủ, lúc nào cần một class có danh tính riêng.

> **Mục tiêu (đo được):** sau chương này bạn **phân biệt** được Entity với Value Object dựa trên tiêu chí danh tính (identity) chứ không phải dữ liệu; **cài đặt** được một Value Object bằng `record` và một Entity bằng `class` có `Id`; **thiết kế** được một Aggregate với đúng một Aggregate Root kiểm soát toàn bộ thay đổi bên trong; và **quyết định** được khi nào áp dụng DDD là hợp lý, khi nào là over-engineering cho một CRUD đơn giản.

---

## 0. Đoán nhanh trước khi đọc

Trước khi xem đáp án, hãy tự trả lời (desirable difficulty — đoán sai vẫn giúp nhớ lâu hơn):

1. Hai đối tượng `Customer` cùng tên, cùng email, nhưng `Id` khác nhau — chúng là "giống nhau" hay "khác nhau" trong DDD?
2. Hai đối tượng `Address` cùng số nhà, cùng đường, cùng thành phố — chúng là "giống nhau" hay "khác nhau" trong DDD?
3. `record` C# so sánh bằng giá trị (value-equality) theo mặc định — điều này hợp với Entity hay Value Object hơn?
4. Nếu `Order` có danh sách `OrderLine`, code bên ngoài có nên gọi `order.Lines.Add(new OrderLine(...))` trực tiếp không?
5. Một API quản lý `Country` chỉ có `Code` và `Name`, không có rule nghiệp vụ nào — có cần mô hình hoá theo DDD (Entity/Aggregate) không?

??? note "Đáp án"
    1. **Khác nhau về dữ liệu nhưng CÙNG MỘT Entity** nếu `Id` giống nhau (ví dụ do đổi tên); ở đây `Id` khác nhau nên đây là **hai Entity khác nhau**, dù toàn bộ dữ liệu khác có thể trùng — Entity xác định bằng danh tính (`Id`), không phải bằng dữ liệu.
    2. **Giống nhau** — Value Object không có danh tính riêng, hai `Address` cùng giá trị được xem là **một**, có thể thay thế cho nhau.
    3. **Value Object** — vì value-equality (so sánh theo giá trị) đúng là bản chất của Value Object; dùng `record` cho Entity sẽ gây hiểu lầm vì `record` sẽ coi hai object cùng dữ liệu là "bằng nhau" dù `Id` có thể đang đại diện hai bản ghi khác nhau trong hệ thống.
    4. **Không nên** — nên đi qua method của `Order` (ví dụ `order.AddLine(...)`) để `Order` (Aggregate Root) kiểm soát được rule nghiệp vụ (ví dụ giới hạn số dòng, validate sản phẩm trùng) mỗi khi có thay đổi.
    5. **Không cần** — `Country` không có rule nghiệp vụ nào, không có vòng đời hay hành vi phức tạp; áp DDD ở đây là over-engineering, một `record CountryDto(string Code, string Name)` là đủ.

---

## 1. Entity là gì

**Định nghĩa (một câu, giả định bạn chưa biết khái niệm này):** Entity là một object được xác định bởi **danh tính (identity)** — thường là một trường `Id` — tồn tại xuyên suốt thời gian và có thể **thay đổi dữ liệu bên trong**, nhưng vẫn là "cùng một thứ" miễn `Id` không đổi; ngược lại, hai Entity có `Id` khác nhau luôn được xem là **hai thứ khác nhau**, dù mọi dữ liệu khác trùng nhau y hệt.

**Phân biệt ngay với `record` value-equality đã học ở P1:** ở P1, `record` so sánh bằng nhau theo **giá trị** — hai `record` có cùng dữ liệu là `Equals() == true`. Entity **cố ý làm ngược lại**: so sánh bằng nhau chỉ dựa vào `Id`, bất kể dữ liệu khác giống hay khác nhau.

**Ví dụ tối thiểu, độc lập:**

```csharp title="C#"
// test:run
using System;

public class Customer
{
    public int Id { get; }
    public string Name { get; private set; }
    public string Email { get; private set; }

    public Customer(int id, string name, string email)
    {
        Id = id;
        Name = name;
        Email = email;
    }

    public void ChangeName(string newName) => Name = newName;

    // Đúng bản chất Entity: chỉ so sánh Id, KHÔNG so sánh Name/Email.
    public override bool Equals(object? obj)
        => obj is Customer other && Id == other.Id;

    public override int GetHashCode() => Id.GetHashCode();
}

public static class Program
{
    public static void Main()
    {
        var customer = new Customer(1, "Nguyễn Văn A", "a@test.com");

        // Cùng một Entity (Id = 1) sau khi đổi tên — VẪN LÀ "cùng một khách hàng".
        var beforeChange = new Customer(1, "Nguyễn Văn A", "a@test.com");
        customer.ChangeName("Nguyễn Văn A2");
        Console.WriteLine($"Cùng Id, dữ liệu khác nhau -> Equals: {customer.Equals(beforeChange)}");

        // Hai Entity khác Id, dữ liệu TRÙNG NHAU HOÀN TOÀN — VẪN LÀ hai khách hàng khác nhau.
        var twin1 = new Customer(2, "Trần Thị B", "b@test.com");
        var twin2 = new Customer(3, "Trần Thị B", "b@test.com");
        Console.WriteLine($"Id khác nhau, dữ liệu trùng -> Equals: {twin1.Equals(twin2)}");
    }
}
```

```text title="Kết quả"
Cùng Id, dữ liệu khác nhau -> Equals: True
Id khác nhau, dữ liệu trùng -> Equals: False
```

**Vấn đề cụ thể nếu dùng `record` (value-equality) cho Entity thay vì `class` với so sánh theo `Id`:**

```csharp title="C#"
// test:run
using System;

// SAI: dùng record cho Entity -> Equals so sánh TOÀN BỘ dữ liệu, không phải Id.
public record CustomerRecord(int Id, string Name, string Email);

public static class BadProgram
{
    public static void Main()
    {
        // Trường hợp 1: CÙNG một khách hàng (Id = 101) nhưng vừa đổi email —
        // đây PHẢI là "cùng một thứ" theo đúng bản chất Entity ở mục 1.
        var before = new CustomerRecord(101, "Lê Văn C", "old@congty.com");
        var after = new CustomerRecord(101, "Lê Văn C", "new@congty.com");
        Console.WriteLine($"Cùng Id, đổi email -> record Equals: {before.Equals(after)}");
        // record trả về False vì Email khác — SAI về nghiệp vụ: đây vẫn là MỘT khách hàng
        // (chỉ vừa đổi email), nhưng record khiến code hiểu nhầm là "hai thứ khác nhau".

        // Trường hợp 2: HAI khách hàng khác nhau (Id khác) nhưng trùng Name/Email
        // (ví dụ hai người tên giống nhau, đăng ký email công ty chung của phòng ban).
        var customerA = new CustomerRecord(201, "Lê Văn C", "sale@congty.com");
        var customerB = new CustomerRecord(202, "Lê Văn C", "sale@congty.com");
        Console.WriteLine($"Id khác nhau, dữ liệu trùng -> record Equals: {customerA.Equals(customerB)}");
        // record trả về False ở đây thì lại ĐÚNG — nhưng đúng "nhờ trùng hợp" (vì Id nằm
        // trong constructor), không phải vì record CHỦ ĐÍCH so sánh theo Id như Entity cần.
    }
}
```

```text title="Kết quả"
Cùng Id, đổi email -> record Equals: False
Id khác nhau, dữ liệu trùng -> record Equals: False
```

Đây chính là lý do Entity **không nên** cài đặt bằng `record`: dòng đầu cho thấy vấn đề thật — cùng một khách hàng (`Id` không đổi) nhưng vừa cập nhật email lại bị `record.Equals()` báo là "khác nhau" (`False`), trong khi đúng bản chất Entity ở mục 1 phải là "cùng một thứ" (`True`) vì `Id` không đổi. `record` so sánh **toàn bộ** dữ liệu, còn Entity chỉ cần so sánh **`Id`** — dùng nhầm `record` sẽ làm mọi lần cập nhật dữ liệu (đổi tên, đổi email...) vô tình biến Entity "thành một thứ khác" trong mọi đoạn code dựa vào `Equals`/`GetHashCode` (ví dụ tìm trong `HashSet<CustomerRecord>` sẽ không thấy bản ghi cũ sau khi cập nhật).

---

## 2. Value Object là gì

**Định nghĩa (một câu):** Value Object là một object được xác định **hoàn toàn bởi giá trị dữ liệu của nó**, không có `Id` hay danh tính riêng — hai Value Object có cùng giá trị được xem là **một**, có thể thay thế cho nhau ở bất cứ đâu mà không mất thông tin gì.

**Liên hệ trực tiếp với `record` đã học ở P1:** `record` chính là cách cài đặt **tự nhiên nhất** cho Value Object trong C#, vì `record` đã có sẵn value-equality — đúng thứ Value Object cần, không cần tự viết `Equals`/`GetHashCode` như Entity ở mục 1.

**Ví dụ tối thiểu, độc lập:**

```csharp title="C#"
// test:run
using System;

// Value Object: KHÔNG có Id, xác định hoàn toàn bởi giá trị (Street, City, ZipCode)
public record Address(string Street, string City, string ZipCode);

// Value Object khác: Money — hai Money cùng Amount + Currency là MỘT giá trị, không phải "hai đối tượng"
public record Money(decimal Amount, string Currency)
{
    public Money Add(Money other)
    {
        if (Currency != other.Currency)
            throw new InvalidOperationException($"Không thể cộng {Currency} với {other.Currency}");
        return new Money(Amount + other.Amount, Currency);
    }
}

public static class Program
{
    public static void Main()
    {
        var addressA = new Address("123 Lê Lợi", "Hồ Chí Minh", "700000");
        var addressB = new Address("123 Lê Lợi", "Hồ Chí Minh", "700000");

        // Hai object KHÁC NHAU trong bộ nhớ (khác reference) nhưng CÙNG GIÁ TRỊ -> được coi là MỘT.
        Console.WriteLine($"Hai Address cùng giá trị -> Equals: {addressA.Equals(addressB)}");
        Console.WriteLine($"Có phải cùng reference? {ReferenceEquals(addressA, addressB)}");

        var price1 = new Money(50_000m, "VND");
        var price2 = new Money(30_000m, "VND");
        var total = price1.Add(price2);
        Console.WriteLine($"Tổng tiền: {total.Amount:N0} {total.Currency}");
    }
}
```

```text title="Kết quả"
Hai Address cùng giá trị -> Equals: True
Có phải cùng reference? False
Tổng tiền: 80,000 VND
```

**Vấn đề cụ thể nếu dùng nhầm Entity (có `Id`, so sánh theo `Id`) cho một khái niệm vốn là Value Object:**

```csharp title="C#"
// test:compile minh hoạ SAI — gắn Id vào một khái niệm vốn không cần danh tính
public class AddressEntity
{
    public int Id { get; set; } // SAI: Address không có "danh tính" nghiệp vụ nào cả
    public string Street { get; set; } = "";
    public string City { get; set; } = "";
    public string ZipCode { get; set; } = "";
}

// Hệ quả: hai địa chỉ giao hàng CÙNG giá trị (cùng số nhà, đường, thành phố) nhưng được
// tạo ở hai lần khác nhau sẽ có Id khác nhau (1 và 2) -> hệ thống hiểu nhầm là "hai địa chỉ
// khác nhau", dẫn tới việc phải viết thêm logic so sánh Street/City/ZipCode thủ công ở
// mọi nơi cần kiểm tra "địa chỉ này có giống địa chỉ kia không" — trong khi bản chất
// chỉ cần Equals() có sẵn của record (mục 2) nếu không gắn Id vào từ đầu.
```

Khi gắn `Id` vào một khái niệm chỉ cần xác định bởi giá trị, bạn tạo ra một bài toán không có thật: "hai bản ghi khác `Id` nhưng cùng giá trị có phải là một không?" — trong khi câu trả lời đúng theo nghiệp vụ luôn là "có", còn cách cài đặt bằng Entity lại buộc phải trả lời "không" (vì `Id` khác).

---

## 3. Aggregate và Aggregate Root

**Định nghĩa (một câu):** Aggregate là một nhóm Entity và Value Object có liên quan, **luôn thay đổi cùng nhau như một đơn vị nghiệp vụ thống nhất**, và chỉ được truy cập/thay đổi thông qua **đúng một Entity đứng đầu** gọi là **Aggregate Root** — code bên ngoài không được thay đổi trực tiếp các thành phần bên trong.

**Ví dụ tối thiểu, độc lập** — `Order` là Aggregate Root, chứa danh sách `OrderLine` (chỉ tồn tại có ý nghĩa **bên trong** một `Order`, không đứng độc lập):

```csharp title="C#"
// test:run
using System;
using System.Collections.Generic;
using System.Linq;

public record OrderLine(int ProductId, int Quantity, Money UnitPrice)
{
    public Money LineTotal => new Money(UnitPrice.Amount * Quantity, UnitPrice.Currency);
}

public record Money(decimal Amount, string Currency);

// Aggregate Root: MỌI thay đổi lên OrderLine phải đi qua method của Order.
public class Order
{
    public int Id { get; }
    public int CustomerId { get; }
    private readonly List<OrderLine> _lines = new();
    public IReadOnlyList<OrderLine> Lines => _lines; // chỉ cho ĐỌC, không cho sửa trực tiếp từ ngoài

    public Order(int id, int customerId)
    {
        Id = id;
        CustomerId = customerId;
    }

    // Rule nghiệp vụ nằm ở ĐÂY, ngay chỗ dữ liệu thay đổi — không nơi nào khác được sửa _lines.
    public void AddLine(int productId, int quantity, Money unitPrice)
    {
        if (quantity <= 0)
            throw new InvalidOperationException("Số lượng phải lớn hơn 0.");
        if (_lines.Any(l => l.ProductId == productId))
            throw new InvalidOperationException($"Sản phẩm {productId} đã có trong đơn — dùng UpdateLineQuantity để sửa số lượng.");

        _lines.Add(new OrderLine(productId, quantity, unitPrice));
    }

    public void RemoveLine(int productId)
    {
        if (_lines.Count == 1)
            throw new InvalidOperationException("Đơn hàng phải có ít nhất một dòng sản phẩm.");
        _lines.RemoveAll(l => l.ProductId == productId);
    }

    public Money GetTotal()
    {
        if (_lines.Count == 0) return new Money(0, "VND");
        var currency = _lines[0].UnitPrice.Currency;
        return new Money(_lines.Sum(l => l.LineTotal.Amount), currency);
    }
}

public static class Program
{
    public static void Main()
    {
        var order = new Order(1, customerId: 7);
        order.AddLine(productId: 1, quantity: 2, new Money(50_000m, "VND"));
        order.AddLine(productId: 2, quantity: 1, new Money(120_000m, "VND"));

        Console.WriteLine($"Đơn #{order.Id} có {order.Lines.Count} dòng, tổng {order.GetTotal().Amount:N0}đ");

        try
        {
            order.AddLine(productId: 1, quantity: 5, new Money(50_000m, "VND")); // trùng sản phẩm
        }
        catch (InvalidOperationException ex)
        {
            Console.WriteLine($"Lỗi nghiệp vụ: {ex.Message}");
        }
    }
}
```

```text title="Kết quả"
Đơn #1 có 2 dòng, tổng 220,000đ
Lỗi nghiệp vụ: Sản phẩm 1 đã có trong đơn — dùng UpdateLineQuantity để sửa số lượng.
```

**Vấn đề cụ thể nếu KHÔNG có Aggregate Root — code ngoài sửa trực tiếp danh sách con:**

```csharp title="C#"
// test:compile minh hoạ SAI — cho phép sửa OrderLine trực tiếp từ ngoài, KHÔNG qua Order
public record Money(decimal Amount, string Currency);

public record OrderLine(int ProductId, int Quantity, Money UnitPrice)
{
    public Money LineTotal => new Money(UnitPrice.Amount * Quantity, UnitPrice.Currency);
}

public class UnsafeOrder
{
    public int Id { get; set; }
    public List<OrderLine> Lines { get; set; } = new(); // SAI: public setter + List thường, ai cũng sửa được

    public Money GetTotal() => new Money(Lines.Sum(l => l.LineTotal.Amount), "VND");
}

public static class BadUsage
{
    public static void Run()
    {
        var order = new UnsafeOrder { Id = 1 };

        // Code ở TẦNG KHÁC (ví dụ một service không liên quan) thêm thẳng vào Lines,
        // BỎ QUA hoàn toàn rule "không được trùng sản phẩm" đã viết trong Order.AddLine ở trên.
        order.Lines.Add(new OrderLine(1, -5, new Money(50_000m, "VND"))); // số lượng ÂM lọt qua!
        order.Lines.Add(new OrderLine(1, 3, new Money(50_000m, "VND"))); // trùng ProductId lọt qua!

        // Hệ quả: GetTotal() tính ra số tiền SAI (vì có dòng số lượng âm), và dữ liệu
        // có 2 dòng cùng ProductId = 1 mà không ai validate ngăn lại — rule nghiệp vụ
        // đã viết trong Order.AddLine (mục 3) hoàn toàn bị vô hiệu vì bị bỏ qua ở đây.
        Console.WriteLine($"Tổng (SAI vì có số lượng âm lọt qua): {order.GetTotal().Amount:N0}đ");
    }
}
```

Khi không ép truy cập qua Aggregate Root (dùng `List<T>` public, setter mở), **mọi rule nghiệp vụ viết trong `Order.AddLine`** (chặn số lượng âm, chặn trùng sản phẩm) đều có thể bị bỏ qua bởi bất kỳ đoạn code nào sửa `Lines` trực tiếp — đây chính là lý do Aggregate Root phải là **cửa duy nhất** để thay đổi dữ liệu bên trong Aggregate.

---

## 4. Bounded Context — giới thiệu khái niệm (không đi sâu)

**Định nghĩa mức giới thiệu:** Bounded Context là một **ranh giới nghiệp vụ** trong đó một khái niệm (ví dụ `Product`) có **một ý nghĩa và một mô hình dữ liệu thống nhất** — cùng tên `Product` nhưng ở context "Bán hàng" nó có `Price`, `StockQuantity`, còn ở context "Vận chuyển" nó có `Weight`, `Dimensions`; đây là **hai model khác nhau**, dù cùng tên, vì phục vụ hai nghiệp vụ khác nhau.

```text title="Sơ đồ ý tưởng — KHÔNG đi sâu ở bài này"
Context "Bán hàng":         Context "Vận chuyển":
  Product                     Product
  ├─ Price                    ├─ Weight
  ├─ StockQuantity            ├─ Dimensions
  └─ Description               └─ FragileFlag
(cùng tên "Product", nhưng KHÔNG PHẢI cùng một class/model — mỗi context có Aggregate riêng)
```

Ở mức "core" của bài này, bạn chỉ cần biết: **Entity, Value Object, Aggregate mà mục 1–3 vừa học đều tồn tại BÊN TRONG một Bounded Context cụ thể** — không có một `Order` "đúng duy nhất" cho toàn công ty, mà mỗi context (Bán hàng, Kế toán, Vận chuyển) có thể có mô hình `Order` khác nhau, phục vụ đúng nhu cầu của context đó.

**Ví dụ cụ thể tại sao ranh giới này quan trọng:** nếu không có Bounded Context, một team sẽ cố gộp `Product` của "Bán hàng" và `Product` của "Vận chuyển" thành **một class duy nhất** chứa cả `Price`, `StockQuantity`, `Weight`, `Dimensions`, `FragileFlag` — kết quả là mỗi khi team Vận chuyển thêm field mới (ví dụ `HazardousMaterialCode`), team Bán hàng phải review lại class dùng chung dù không liên quan gì đến nghiệp vụ giá/kho của họ. Đây là cùng một dạng vấn đề với "model dùng chung bị kéo hai phía" đã thấy ở CQRS (bài trước) — chỉ khác là ở đây vấn đề nằm ở **ranh giới nghiệp vụ giữa hai team/module**, không phải ranh giới đọc/ghi.

Đi sâu vào cách vẽ ranh giới giữa các context (context mapping, shared kernel, anti-corruption layer...) là nội dung nâng cao, vượt phạm vi "core" của bài này — bạn chỉ cần nhớ nguyên tắc: **mỗi Bounded Context có Aggregate riêng cho khái niệm cùng tên, không cố dùng chung một model cho mọi ngữ cảnh.**

Trong thực tế triển khai .NET, Bounded Context thường (không bắt buộc) ánh xạ tới **một solution/project riêng** hoặc **một namespace gốc riêng** (ví dụ `Company.Sales.Domain` và `Company.Shipping.Domain`), mỗi bên có class `Product` của riêng mình, không tham chiếu chéo trực tiếp vào Entity/Aggregate của context khác — nếu context "Vận chuyển" cần biết giá sản phẩm, nó gọi qua một API/interface tường minh (ví dụ `IPricingService`), không `using Company.Sales.Domain;` rồi dùng thẳng Aggregate `Product` của bên kia.

Với một ứng dụng .NET nội bộ cỡ nhỏ-vừa (một team, một database), thường chỉ có **một** Bounded Context — khái niệm này bắt đầu có giá trị rõ ràng khi hệ thống lớn tới mức nhiều team làm việc trên các module nghiệp vụ tách biệt nhau.

---

## 5. So sánh Entity, Value Object và DTO thuần — chỉ đưa ra SAU khi đã hiểu riêng từng khái niệm

Sau khi đã hiểu riêng Entity (mục 1), Value Object (mục 2), và Aggregate (mục 3), giờ mới đến lúc so sánh ba cách mô hình hoá dữ liệu thường bị nhầm lẫn với nhau:

| Khía cạnh | Entity | Value Object | DTO thuần (record đơn giản) |
|-----------|--------|---------------|------------------------------|
| Có danh tính (`Id`) không | Có — bắt buộc | Không | Có thể có `Id` nhưng chỉ để tham chiếu, không có hành vi bảo vệ |
| Cách so sánh bằng nhau | Theo `Id` | Theo toàn bộ giá trị | Theo giá trị (nếu dùng `record`) hoặc không quan tâm |
| Có hành vi (method) bảo vệ rule nghiệp vụ không | Có — mọi thay đổi qua method | Có thể có (ví dụ `Money.Add` tự kiểm tra `Currency`) | Không — chỉ chứa dữ liệu, validate nằm ở nơi khác (service) |
| Cách cài đặt tự nhiên trong C# | `class` với `Id` riêng, setter private, method thay đổi | `record` (value-equality có sẵn) | `record` hoặc `class` với property `get; set;` mở |
| Ví dụ | `Customer`, `Order`, `Employee` | `Address`, `Money`, `PhoneNumber` | `CategoryDto`, `CountryDto` — chỉ để truyền dữ liệu qua API |

**Vì sao bảng này chỉ có ý nghĩa nếu đọc SAU mục 1–3, không phải đọc trước:** nếu chưa hiểu Entity cần `Id` để làm gì (mục 1) hay Value Object không cần `Id` để làm gì (mục 2), dòng "Có danh tính hay không" trong bảng chỉ là một sự thật khô khan, không giải thích được **vì sao** lại phân chia như vậy — đây là lý do định nghĩa và ví dụ luôn phải đến trước bảng so sánh.

---

## 6. Ví dụ nâng cao: Value Object tự bảo vệ, Aggregate với nhiều rule lồng nhau

**Chỉ đưa ra sau khi đã hiểu cơ bản ở mục 1–3** — hai ví dụ dưới đây mở rộng đúng những khái niệm đã học, không giới thiệu thêm khái niệm mới.

**Nâng cao 1 — Value Object tự kiểm tra tính hợp lệ ngay lúc tạo (không chỉ chứa dữ liệu thô):** ở mục 2, `Address`/`Money` chỉ là data holder thuần. Trong thực chiến, Value Object thường **tự bảo vệ** để không bao giờ tồn tại ở trạng thái vô lý — dùng constructor riêng (không dùng cú pháp `record` vị trí mặc định) để validate ngay khi tạo.

```csharp title="C#"
// test:run
using System;

public record EmailAddress
{
    public string Value { get; }

    public EmailAddress(string value)
    {
        if (string.IsNullOrWhiteSpace(value) || !value.Contains('@'))
            throw new ArgumentException($"'{value}' không phải email hợp lệ.");
        Value = value;
    }
}

public static class Program
{
    public static void Main()
    {
        var email1 = new EmailAddress("a@congty.com");
        var email2 = new EmailAddress("a@congty.com");

        // Vẫn giữ đúng bản chất Value Object: cùng giá trị -> Equals = True (record tự sinh).
        Console.WriteLine($"Cùng giá trị -> Equals: {email1.Equals(email2)}");

        try
        {
            var invalid = new EmailAddress("khong-phai-email");
        }
        catch (ArgumentException ex)
        {
            Console.WriteLine($"Bị chặn ngay lúc tạo: {ex.Message}");
        }
    }
}
```

```text title="Kết quả"
Cùng giá trị -> Equals: True
Bị chặn ngay lúc tạo: 'khong-phai-email' không phải email hợp lệ.
```

Điểm khác với `Address`/`Money` ở mục 2: `EmailAddress` **không thể tồn tại** ở trạng thái sai định dạng — constructor chặn ngay, không để một `EmailAddress` "xấu" lọt vào hệ thống rồi mới validate ở nơi khác. Đây vẫn là Value Object đúng nghĩa (không `Id`, value-equality nhờ `record`), chỉ thêm bước tự bảo vệ.

**Nâng cao 2 — Aggregate với nhiều rule PHỤ THUỘC LẪN NHAU (không chỉ một rule đơn lẻ như mục 3):** mở rộng `Order` ở mục 3 với rule khuyến mãi — mã giảm giá chỉ áp dụng được khi tổng tiền đạt ngưỡng, và không áp được hai lần:

```csharp title="C#"
// test:run
using System;
using System.Collections.Generic;
using System.Linq;

public record Money(decimal Amount, string Currency);
public record OrderLine(int ProductId, int Quantity, Money UnitPrice)
{
    public Money LineTotal => new Money(UnitPrice.Amount * Quantity, UnitPrice.Currency);
}

public class Order
{
    public int Id { get; }
    private readonly List<OrderLine> _lines = new();
    public IReadOnlyList<OrderLine> Lines => _lines;
    public string? AppliedDiscountCode { get; private set; }
    public decimal DiscountPercent { get; private set; }

    public Order(int id) => Id = id;

    public void AddLine(int productId, int quantity, Money unitPrice)
    {
        if (quantity <= 0) throw new InvalidOperationException("Số lượng phải lớn hơn 0.");
        _lines.Add(new OrderLine(productId, quantity, unitPrice));
    }

    // Rule LỒNG NHAU: (1) không áp mã hai lần, (2) phải đạt ngưỡng tổng tiền TRƯỚC khi giảm giá.
    public void ApplyDiscount(string code, decimal percent, decimal minimumOrderAmount)
    {
        if (AppliedDiscountCode is not null)
            throw new InvalidOperationException($"Đơn đã áp mã '{AppliedDiscountCode}', không thể áp thêm mã khác.");

        var subtotal = GetSubtotal().Amount;
        if (subtotal < minimumOrderAmount)
            throw new InvalidOperationException(
                $"Đơn cần tối thiểu {minimumOrderAmount:N0}đ để áp mã '{code}', hiện tại {subtotal:N0}đ.");

        AppliedDiscountCode = code;
        DiscountPercent = percent;
    }

    public Money GetSubtotal()
    {
        if (_lines.Count == 0) return new Money(0, "VND");
        return new Money(_lines.Sum(l => l.LineTotal.Amount), _lines[0].UnitPrice.Currency);
    }

    // Tổng tiền CUỐI luôn tính lại từ subtotal + discount — không có setter "TotalAmount" rời rạc
    // để tránh tình trạng tổng tiền bị sửa tay, lệch khỏi dữ liệu dòng + mã giảm giá thật.
    public Money GetFinalTotal()
    {
        var subtotal = GetSubtotal();
        var discountAmount = subtotal.Amount * DiscountPercent / 100m;
        return new Money(subtotal.Amount - discountAmount, subtotal.Currency);
    }
}

public static class Program
{
    public static void Main()
    {
        var order = new Order(1);
        order.AddLine(1, 2, new Money(200_000m, "VND"));

        try
        {
            // Chưa đạt ngưỡng 500_000đ (mới có 400_000đ) -> bị chặn.
            order.ApplyDiscount("SALE10", percent: 10, minimumOrderAmount: 500_000m);
        }
        catch (InvalidOperationException ex)
        {
            Console.WriteLine($"Lỗi lần 1: {ex.Message}");
        }

        order.AddLine(2, 1, new Money(150_000m, "VND")); // giờ subtotal = 550_000đ, đạt ngưỡng
        order.ApplyDiscount("SALE10", percent: 10, minimumOrderAmount: 500_000m);
        Console.WriteLine($"Áp mã thành công, tổng cuối: {order.GetFinalTotal().Amount:N0}đ");

        try
        {
            order.ApplyDiscount("SALE20", percent: 20, minimumOrderAmount: 0m); // áp lần 2 -> bị chặn
        }
        catch (InvalidOperationException ex)
        {
            Console.WriteLine($"Lỗi lần 2: {ex.Message}");
        }
    }
}
```

```text title="Kết quả"
Lỗi lần 1: Đơn cần tối thiểu 500,000đ để áp mã 'SALE10', hiện tại 400,000đ.
Áp mã thành công, tổng cuối: 495,000đ
Lỗi lần 2: Đơn đã áp mã 'SALE10', không thể áp thêm mã khác.
```

Đây chính là lý do Aggregate đáng giá khi rule **lồng nhau và phụ thuộc trạng thái hiện tại** (`ApplyDiscount` cần biết `AppliedDiscountCode` đã có chưa, cần tính lại `GetSubtotal()` mỗi lần) — nếu để logic này rải rác ở một service bên ngoài (đọc `order.Lines` rồi tự tính subtotal, tự kiểm tra `AppliedDiscountCode` ở đâu đó), rất dễ có hai đoạn code tính subtotal khác cách nhau, hoặc quên kiểm tra "đã áp mã chưa" ở một luồng khác — gom vào method của `Order` đảm bảo **chỉ có một chỗ đúng duy nhất** để tính và kiểm tra.

---

## 7. CẢNH BÁO OVER-ENGINEERING: DDD cho CRUD đơn giản là thừa

Đây là điểm quan trọng nhất của chương này — giống CQRS ở bài trước, DDD (Entity/Value Object/Aggregate đầy đủ với rule nghiệp vụ bọc trong method) là pattern **dễ bị áp dụng tràn lan** ngay khi vừa học xong.

**Ví dụ cụ thể — khi KHÔNG nên dùng DDD đầy đủ:** một API quản lý `Country` (danh sách quốc gia) chỉ có `Code` và `Name`, không có rule nghiệp vụ, không có vòng đời, không có thành phần con nào cần bảo vệ.

```csharp title="C#"
// test:compile minh hoạ CRUD đơn giản — KHÔNG cần Entity class riêng + Aggregate Root
public record CountryDto(string Code, string Name);

// Nếu áp DDD đầy đủ ở đây, bạn sẽ phải viết THÊM:
//   class Country (Entity) với Id ẩn, private setter, method riêng cho từng thay đổi field
//   (dù chỉ có 2 field, không field nào cần validate phức tạp)
// — tạo ra một class "giả vờ có hành vi" nhưng thực chất chỉ là data holder,
// không có lợi ích thực chất nào vì không có rule nghiệp vụ nào để bảo vệ.
```

**Dấu hiệu nhận biết DDD đang thừa (checklist tự hỏi trước khi áp dụng):**

- Đối tượng này có **rule nghiệp vụ** nào cần bảo vệ khi thay đổi dữ liệu không, hay chỉ là lưu/đọc dữ liệu thuần?
- Đối tượng này có **thành phần con** (như `OrderLine` trong `Order`) mà nếu sửa trực tiếp từ ngoài sẽ phá vỡ tính nhất quán không?
- Nghiệp vụ có **nhiều rule lồng nhau, phụ thuộc lẫn nhau** (ví dụ: không cho xoá dòng cuối, tổng tiền phải khớp tổng các dòng, đổi trạng thái phải theo đúng thứ tự) hay chỉ là các field độc lập, sửa cái nào không ảnh hưởng cái khác?

Nếu câu trả lời cho cả ba câu trên là **"không"** — một `record`/DTO đơn giản với service CRUD là đủ, không cần class Entity riêng với `Id` ẩn, private setter, method bọc từng thay đổi. Tách ra trong trường hợp này chỉ tạo thêm lớp gián tiếp (nhiều class, nhiều method rỗng) mà không bảo vệ được rule nghiệp vụ nào có thật — đây chính là **over-engineering**.

**Ngược lại — khi DDD đáng giá:** đúng như ví dụ `Order`/`OrderLine` ở mục 3, khi có **nhiều rule nghiệp vụ lồng nhau** (không trùng sản phẩm, số lượng phải dương, không xoá dòng cuối, tổng tiền phải tính đúng từ các dòng) và có **thành phần con cần được bảo vệ khỏi thay đổi tuỳ tiện từ ngoài** — Entity + Aggregate Root giúp gom toàn bộ rule vào **một nơi duy nhất** (method của Aggregate Root), thay vì rải rác khắp các service khác nhau, mỗi nơi validate lại một ít (và dễ quên, dễ validate không đồng bộ).

---

## 8. Cạm bẫy & thực chiến

- **Dùng `record` cho Entity (đã nhấn ở mục 1):** gây sai lệch value-equality — hai bản ghi khác `Id` nhưng trùng dữ liệu bị coi là "bằng nhau", có thể làm mất dữ liệu khi dùng làm key trong `Dictionary`/`HashSet`, hoặc làm logic dedupe sai.
- **Gắn `Id` vào Value Object (đã nhấn ở mục 2):** tạo ra bài toán giả "hai bản ghi khác Id, cùng giá trị, có phải một không" — trong khi Value Object đúng bản chất trả lời "có" ngay lập tức nhờ value-equality có sẵn của `record`.
- **Cho phép sửa thành phần con của Aggregate trực tiếp từ ngoài (đã nhấn ở mục 3):** dùng `public List<T>` với setter mở khiến rule nghiệp vụ viết trong Aggregate Root (như `Order.AddLine`) bị bỏ qua hoàn toàn bởi bất kỳ code nào sửa thẳng vào danh sách con — luôn expose danh sách con qua `IReadOnlyList<T>` và bắt buộc thay đổi đi qua method.
- **Áp DDD đầy đủ cho CRUD đơn giản (đã nhấn ở mục 7):** đây là lỗi phổ biến nhất sau khi học DDD — thấy Entity/Aggregate "trông chuyên nghiệp" nên áp dụng cho mọi bảng, kể cả `Country`, `Currency`, những bảng chỉ có 2-3 field và không có rule nào. Kết quả: nhiều class rỗng, nhiều method bọc field không cần validate gì, review code chậm hơn.
- **Aggregate quá lớn ("God Aggregate"):** nhồi quá nhiều Entity không thật sự luôn thay đổi cùng nhau vào một Aggregate (ví dụ nhồi cả `Customer` đầy đủ lịch sử mua hàng vào bên trong Aggregate `Order`) khiến mỗi lần load `Order` phải load luôn toàn bộ dữ liệu khách hàng — Aggregate nên **nhỏ nhất có thể**, chỉ gồm những gì bắt buộc phải nhất quán cùng lúc; `Order` chỉ cần `CustomerId` (tham chiếu), không cần nhồi nguyên `Customer` vào.
- **Quên rằng Value Object nên bất biến (immutable) — sửa field trực tiếp thay vì tạo bản mới:** vì `record` ở mục 2 cho phép khai báo `init`-only property, cách đúng để "đổi" một Value Object là tạo **bản mới** bằng cú pháp `with` (ví dụ `var newAddress = oldAddress with { City = "Hà Nội" }`), không phải thêm setter mở để sửa field cũ tại chỗ. Nếu vô tình thêm `set` công khai vào Value Object, hai biến đang giữ "cùng một địa chỉ" (nhưng thực chất là hai reference riêng do không có danh tính để theo dõi) có thể vô tình bị thay đổi chung, gây lỗi khó truy — đây là lý do Value Object nên giữ nguyên tắc bất biến, chỉ tạo bản mới khi cần giá trị khác.

---

## 9. Bài tập

**Bài 1 — Phân biệt Entity và Value Object.** Cho hai khái niệm trong hệ thống quản lý nhân sự: (a) `Employee` (nhân viên, có mã số nhân viên, tên, phòng ban, có thể đổi phòng ban theo thời gian) và (b) `PhoneNumber` (số điện thoại liên hệ, gồm mã vùng và số). Khái niệm nào nên là Entity, khái niệm nào nên là Value Object? Nêu lý do dựa trên tiêu chí danh tính ở mục 1–2.

??? success "Lời giải + vì sao"
    - **`Employee` là Entity:** có danh tính riêng (mã số nhân viên) tồn tại xuyên suốt thời gian; dù đổi tên hay đổi phòng ban, đây vẫn là "cùng một nhân viên đó" — cần class riêng, so sánh theo `Id` (mã số nhân viên), không theo `record` value-equality.
    - **`PhoneNumber` là Value Object:** không có danh tính riêng — hai `PhoneNumber` cùng mã vùng và số là **một** số điện thoại, có thể thay thế cho nhau (ví dụ khi copy số điện thoại của nhân viên A sang hồ sơ liên hệ khẩn cấp của nhân viên B, đó vẫn là "số điện thoại đó", không phải "một bản sao cần theo dõi danh tính riêng"). Nên dùng `record PhoneNumber(string AreaCode, string Number)`.

**Bài 2 — Nhận diện over-engineering và thiết kế Aggregate.** Hệ thống quản lý `Invoice` (hoá đơn) có: `InvoiceLine` (mỗi dòng có sản phẩm, số lượng, đơn giá) và rule nghiệp vụ "tổng tiền hoá đơn phải luôn bằng tổng các dòng, không được sửa tổng tiền tay; không cho xoá dòng nếu hoá đơn đã ở trạng thái `Paid`". So với `Country` ở mục 7, `Invoice` có cần DDD đầy đủ (Entity + Aggregate Root) không? Nếu có, `Invoice` hay `InvoiceLine` nên là Aggregate Root?

??? success "Lời giải + vì sao"
    **Có, cần DDD đầy đủ** — áp checklist mục 7: (1) có rule nghiệp vụ rõ ràng (tổng tiền phải khớp, không xoá dòng khi đã `Paid`); (2) có thành phần con (`InvoiceLine`) mà sửa trực tiếp sẽ phá vỡ tính nhất quán tổng tiền; (3) rule phụ thuộc trạng thái (`Paid` ảnh hưởng được phép xoá dòng hay không) — cả ba đều "có", khác hẳn `Country` ở mục 7.

    **`Invoice` là Aggregate Root**, không phải `InvoiceLine`, vì `InvoiceLine` chỉ có ý nghĩa **bên trong** một `Invoice` cụ thể (không tồn tại độc lập, không ai truy vấn "cho tôi một `InvoiceLine` mà không cần biết thuộc `Invoice` nào"), và rule nghiệp vụ (khớp tổng tiền, chặn xoá khi `Paid`) phải được kiểm tra ở **một nơi duy nhất** — method của `Invoice`, ví dụ `invoice.RemoveLine(lineId)` tự kiểm tra `Status != Paid` trước khi cho xoá, tương tự `Order.AddLine` đã chặn trùng sản phẩm ở mục 3.

---

## Tự kiểm tra

1. Entity được xác định bằng gì? Value Object được xác định bằng gì? Nêu sự khác biệt cốt lõi.
2. Vì sao dùng `record` để cài đặt Entity là một lựa chọn dễ gây lỗi, dù `record` viết ngắn hơn `class`?
3. Vì sao `record` lại là cách cài đặt "tự nhiên nhất" cho Value Object trong C#?
4. Aggregate Root có vai trò gì? Nêu một hệ quả cụ thể nếu cho phép sửa thành phần con của Aggregate trực tiếp từ ngoài, bỏ qua Aggregate Root.
5. Bounded Context giải quyết vấn đề gì khi hai team dùng chung một tên khái niệm (ví dụ `Product`)?
6. Nêu một ví dụ cụ thể (không lấy lại ví dụ trong bài) mà áp dụng Entity/Aggregate đầy đủ là over-engineering.
7. Trong ví dụ `Order`/`OrderLine` ở mục 3, vì sao `OrderLine` không nên là Aggregate Root riêng?
8. Cách đúng để "đổi" một Value Object bất biến (immutable) là gì — sửa trực tiếp field hay tạo bản mới? Nêu cú pháp C# tương ứng.

??? note "Đáp án"
    1. Entity được xác định bằng **danh tính** (`Id`) — hai Entity cùng `Id` là một, dù dữ liệu khác nhau; hai Entity khác `Id` là hai thứ khác nhau, dù dữ liệu trùng nhau. Value Object được xác định **hoàn toàn bởi giá trị** — không có `Id`, hai Value Object cùng giá trị là một.
    2. Vì `record` mặc định so sánh theo giá trị (value-equality) — hai bản ghi Entity khác `Id` nhưng trùng toàn bộ dữ liệu khác sẽ bị `record.Equals()` coi là "bằng nhau", sai với bản chất nghiệp vụ là hai bản ghi khác nhau; hệ quả cụ thể là mất dữ liệu khi dùng làm key trong `Dictionary`/`HashSet` hoặc logic dedupe sai.
    3. Vì Value Object cần đúng thứ `record` đã có sẵn: so sánh bằng nhau theo giá trị, không cần tự viết `Equals`/`GetHashCode` như phải làm cho Entity.
    4. Aggregate Root là **cửa duy nhất** để thay đổi dữ liệu bên trong Aggregate, đảm bảo mọi rule nghiệp vụ được áp dụng nhất quán. Nếu cho sửa trực tiếp thành phần con (ví dụ `List<OrderLine>` public), rule nghiệp vụ viết trong method của Aggregate Root (chặn số lượng âm, chặn trùng sản phẩm) sẽ bị bỏ qua hoàn toàn bởi bất kỳ code nào sửa thẳng vào danh sách con.
    5. Bounded Context cho phép cùng một tên khái niệm (`Product`) có **hai model khác nhau** ở hai ngữ cảnh nghiệp vụ khác nhau (Bán hàng cần `Price`/`StockQuantity`, Vận chuyển cần `Weight`/`Dimensions`) mà không xung đột, vì mỗi context có ranh giới và mô hình riêng, không cố ép về "một `Product` đúng duy nhất" cho toàn hệ thống.
    6. Ví dụ hợp lệ: một API quản lý `Currency` (chỉ có `Code`, `Symbol`), không có rule nghiệp vụ, không có thành phần con nào — dùng Entity class với `Id` ẩn, private setter, method riêng cho từng field là over-engineering, một `record CurrencyDto(string Code, string Symbol)` là đủ.
    7. Vì `OrderLine` không có ý nghĩa tồn tại độc lập — nó chỉ có nghĩa khi gắn với một `Order` cụ thể, và rule nghiệp vụ (không trùng sản phẩm, không xoá dòng cuối) cần được kiểm tra ở phạm vi toàn bộ `Order` (biết được các dòng khác), không thể tự kiểm tra đúng nếu `OrderLine` đứng một mình.
    8. Phải **tạo bản mới**, không sửa trực tiếp field cũ — dùng cú pháp `with` của `record`, ví dụ `var newAddress = oldAddress with { City = "Hà Nội" }` tạo ra một `Address` mới với `City` khác, giữ nguyên các field còn lại, không làm thay đổi `oldAddress` ban đầu.

---

??? abstract "DEEP DIVE — Aggregate với validate ở constructor factory method, và ranh giới với Repository/EF Core"
    **Bổ sung factory method để đảm bảo Aggregate luôn ở trạng thái hợp lệ ngay từ lúc tạo** (không chỉ khi thay đổi sau này):

    ```csharp title="C#"
    // test:run
    using System;
    using System.Collections.Generic;
    using System.Linq;

    public record Money(decimal Amount, string Currency);
    public record OrderLine(int ProductId, int Quantity, Money UnitPrice);

    public class Order
    {
        public int Id { get; }
        public int CustomerId { get; }
        public string Status { get; private set; }
        private readonly List<OrderLine> _lines = new();
        public IReadOnlyList<OrderLine> Lines => _lines;

        // Constructor PRIVATE — buộc mọi nơi tạo Order phải đi qua factory method Create(),
        // đảm bảo Order không bao giờ tồn tại ở trạng thái "chưa có dòng nào" (invalid theo rule nghiệp vụ).
        private Order(int id, int customerId)
        {
            Id = id;
            CustomerId = customerId;
            Status = "Draft";
        }

        public static Order Create(int id, int customerId, int firstProductId, int firstQuantity, Money firstUnitPrice)
        {
            var order = new Order(id, customerId);
            order.AddLine(firstProductId, firstQuantity, firstUnitPrice); // đảm bảo LUÔN có ít nhất 1 dòng
            return order;
        }

        public void AddLine(int productId, int quantity, Money unitPrice)
        {
            if (Status == "Paid")
                throw new InvalidOperationException("Không thể sửa đơn đã thanh toán.");
            if (quantity <= 0)
                throw new InvalidOperationException("Số lượng phải lớn hơn 0.");
            if (_lines.Any(l => l.ProductId == productId))
                throw new InvalidOperationException($"Sản phẩm {productId} đã có trong đơn.");

            _lines.Add(new OrderLine(productId, quantity, unitPrice));
        }

        public void MarkAsPaid()
        {
            if (_lines.Count == 0)
                throw new InvalidOperationException("Không thể thanh toán đơn chưa có dòng nào.");
            Status = "Paid";
        }
    }

    public static class Program
    {
        public static void Main()
        {
            // Không thể tạo Order "trống" — Create() buộc phải có dòng đầu tiên ngay từ đầu.
            var order = Order.Create(1, customerId: 7, firstProductId: 1, firstQuantity: 2, new Money(50_000m, "VND"));
            order.AddLine(2, 1, new Money(120_000m, "VND"));
            order.MarkAsPaid();

            Console.WriteLine($"Đơn #{order.Id}, trạng thái: {order.Status}, số dòng: {order.Lines.Count}");

            try
            {
                order.AddLine(3, 1, new Money(10_000m, "VND")); // đã Paid, không được sửa nữa
            }
            catch (InvalidOperationException ex)
            {
                Console.WriteLine($"Lỗi nghiệp vụ: {ex.Message}");
            }
        }
    }
    ```

    ```text title="Kết quả"
    Đơn #1, trạng thái: Paid, số dòng: 2
    Lỗi nghiệp vụ: Không thể sửa đơn đã thanh toán.
    ```

    **Vì sao factory method `Create()` quan trọng hơn là chỉ "tiện":** nếu để constructor `public` và cho phép tạo `Order` không có dòng nào (như ví dụ mục 3), hệ thống sẽ có những `Order` "nửa vời" tồn tại tạm thời giữa lúc tạo và lúc thêm dòng đầu tiên — nếu có lỗi (exception, crash) xảy ra đúng lúc đó, dữ liệu bị lưu lại ở trạng thái không hợp lệ. Factory method gộp "tạo" và "validate dòng đầu tiên" thành **một bước nguyên tử (atomic)** — `Order` chỉ tồn tại khi đã hợp lệ ngay từ đầu, không có trạng thái trung gian không hợp lệ nào lộ ra ngoài.

    **Ranh giới với Repository/EF Core (chỉ nêu để nối lại kiến thức đã học, không đi sâu):** khi persist Aggregate này bằng EF Core, nguyên tắc quan trọng là **load và save theo đúng ranh giới Aggregate** — luôn load `Order` cùng toàn bộ `Lines` của nó trong một transaction, không load/sửa `OrderLine` như một entity độc lập tách rời khỏi `Order` (EF Core hỗ trợ điều này qua owned types hoặc cấu hình quan hệ 1-nhiều với navigation property private setter). Đây cũng là lý do một lớp Repository riêng biệt **chỉ thật sự cần thiết khi Aggregate phức tạp** (nhiều rule load/save đặc thù cần gom lại một nơi) — với Aggregate đơn giản, `DbContext.Set<Order>()` của EF Core (đã là Unit-of-Work + Repository-like abstraction có sẵn) là đủ, không cần tự viết thêm một lớp `IOrderRepository` bọc ngoài nếu không có logic query phức tạp dùng lại nhiều nơi.

    **Tóm lại quan hệ giữa ba mục xây dựng đã học và hạ tầng persist:** Entity/Value Object/Aggregate (mục 1–3) là cách **mô hình hoá nghiệp vụ trong bộ nhớ**, hoàn toàn độc lập với việc dữ liệu được lưu ở đâu; Repository/EF Core (đã học ở bài trước) là **cách persist** mô hình đó — hai lớp kiến thức bổ sung cho nhau nhưng không phải một, và như mọi pattern khác trong chương này, chỉ nên áp dụng đủ độ phức tạp cần thiết cho đúng nghiệp vụ, không áp dụng vì "đây là chuẩn DDD nên phải làm đủ tầng".

Tiếp theo -> vertical slice: tổ chức code theo tính năng thay vì theo lớp
