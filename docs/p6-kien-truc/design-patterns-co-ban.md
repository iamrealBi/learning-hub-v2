---
tier: core
status: core
owner: core-team
verified_on: "2026-07-03"
dotnet_version: "10.0"
bloom: "Áp dụng"
requires: [p6-repository]
est_minutes_fast: 35
---

# Design Patterns cốt lõi: Factory, Strategy, Decorator

!!! info "bạn đang ở đây · p6 → node `p6-patterns-basic`"
    **cần trước:** đã hiểu vì sao Repository pattern có lúc thừa với EF Core — bài này tiếp tục tinh thần đó: mọi pattern chỉ đáng dùng khi nó *giải quyết một vấn đề cụ thể đang tồn tại*, không phải để "cho có kiến trúc".
    **mở khoá:** nhận diện đúng lúc dùng Factory, Strategy, Decorator — ba pattern hành vi/khởi tạo xuất hiện nhiều nhất trong code C# thực tế, và biết khi nào dùng chúng là over-engineering.

> **Mục tiêu:** **Áp dụng** được Factory pattern để tách logic tạo object phức tạp ra một nơi, Strategy pattern để đổi hành vi lúc runtime qua interface, và Decorator pattern để bọc thêm hành vi cho một object mà không sửa class gốc — đồng thời **phân tích** được khi nào mỗi pattern là thừa so với cách viết đơn giản hơn.

---

## 0. Đoán nhanh trước khi đọc

Trước khi xem đáp án, hãy tự trả lời (desirable difficulty — đoán sai vẫn giúp nhớ lâu hơn):

1. Nếu bạn thấy cùng một đoạn `switch-case` để tạo object lặp lại ở 5 nơi khác nhau trong code, đó là dấu hiệu thiếu pattern nào?
2. Strategy pattern và một `if-else` chọn thuật toán khác nhau ở điểm nào — hay chỉ là "cùng một thứ, tên khác"?
3. Decorator có sửa class gốc để thêm hành vi mới không?
4. Nếu bạn chỉ có 2 lựa chọn cố định, ít khi đổi (ví dụ "giảm giá cuối tuần" và "không giảm giá"), dùng Strategy pattern đầy đủ (interface + nhiều class) có phải lựa chọn tốt nhất không?
5. `ILogger` trong ASP.NET Core, khi bạn "bọc" một `HttpClient` để thêm log trước/sau mỗi request mà không sửa `HttpClient` gốc — đó gần với pattern nào?

??? note "Đáp án"
    1. Thiếu **Factory pattern** — logic tạo object đang bị rải ra nhiều nơi, khó thêm loại mới vì phải sửa nhiều chỗ.
    2. Về mặt hành vi, `if-else` chọn "cứng" trong một hàm — không tách được, không thay được thuật toán lúc runtime. Strategy đóng gói mỗi hành vi vào **một class riêng cài cùng interface**, cho phép đổi (`inject`, gán property) mà không sửa code gọi. Nếu chỉ có 2 lựa chọn cố định, `if-else` đơn giản có thể vẫn đủ — pattern không phải lúc nào cũng thắng.
    3. **Không** — Decorator bọc object gốc bằng một lớp khác cùng interface, class gốc không đổi một dòng nào.
    4. **Không nhất thiết** — với 2 lựa chọn ổn định, một `enum` + `switch` đơn giản hơn, ít file hơn, dễ đọc hơn. Strategy đáng giá khi số lựa chọn *nhiều* và *hay thay đổi/mở rộng*.
    5. **Decorator** — bạn bọc thêm hành vi (log) quanh một hành vi gốc (gửi request) mà không sửa code gửi request gốc.

---

## 1. Factory pattern

### 1.1 Vấn đề cụ thể: logic tạo object rải rác, khó thêm loại mới

Giả sử bạn có hệ thống tính phí thanh toán, hỗ trợ nhiều nhà cung cấp (`CreditCard`, `PayPal`, `BankTransfer`). Không dùng pattern gì, code tạo object thường trông như sau — và tệ hơn, đoạn `switch` này **lặp lại ở nhiều nơi gọi**:

```csharp title="C#"
// test:run
using System;

public interface IPaymentProcessor
{
    string Process(decimal amount);
}

public class CreditCardProcessor : IPaymentProcessor
{
    public string Process(decimal amount) => $"Trừ {amount:C} qua thẻ tín dụng";
}

public class PayPalProcessor : IPaymentProcessor
{
    public string Process(decimal amount) => $"Trừ {amount:C} qua PayPal";
}

public class BankTransferProcessor : IPaymentProcessor
{
    public string Process(decimal amount) => $"Trừ {amount:C} qua chuyển khoản ngân hàng";
}

public class Program
{
    // Nơi gọi #1 — controller thanh toán
    public static string HandleCheckout(string method, decimal amount)
    {
        IPaymentProcessor processor;
        switch (method)
        {
            case "creditcard": processor = new CreditCardProcessor(); break;
            case "paypal": processor = new PayPalProcessor(); break;
            case "banktransfer": processor = new BankTransferProcessor(); break;
            default: throw new ArgumentException($"Không hỗ trợ: {method}");
        }
        return processor.Process(amount);
    }

    // Nơi gọi #2 — job hoàn tiền, PHẢI COPY LẠI CHÍNH switch NÀY
    public static string HandleRefund(string method, decimal amount)
    {
        IPaymentProcessor processor;
        switch (method)
        {
            case "creditcard": processor = new CreditCardProcessor(); break;
            case "paypal": processor = new PayPalProcessor(); break;
            case "banktransfer": processor = new BankTransferProcessor(); break;
            default: throw new ArgumentException($"Không hỗ trợ: {method}");
        }
        return "Hoàn tiền: " + processor.Process(-amount);
    }

    public static void Main()
    {
        Console.WriteLine(HandleCheckout("paypal", 100m));
        Console.WriteLine(HandleRefund("creditcard", 50m));
    }
}
```

**Vấn đề cụ thể, không phải lý thuyết suông:** khi thêm nhà cung cấp thứ tư (ví dụ `MomoProcessor`), bạn phải **sửa switch ở cả hai nơi gọi** (và bất kỳ nơi gọi nào khác từng copy đoạn này). Quên sửa một nơi → bug production, khách chọn Momo mà hệ thống báo "không hỗ trợ" ở job hoàn tiền dù checkout vẫn chạy được.

### 1.2 Định nghĩa

**Factory pattern** là cách **tách logic tạo object phức tạp (chọn class nào, khởi tạo ra sao) ra đúng một nơi duy nhất**, để phần code còn lại chỉ gọi "cho tôi một object phù hợp với X", không cần biết object đó thuộc class cụ thể nào.

### 1.3 Áp dụng Factory để sửa vấn đề trên

```csharp title="C#"
// test:run
using System;
using System.Collections.Generic;

public interface IPaymentProcessor
{
    string Process(decimal amount);
}

public class CreditCardProcessor : IPaymentProcessor
{
    public string Process(decimal amount) => $"Trừ {amount:C} qua thẻ tín dụng";
}

public class PayPalProcessor : IPaymentProcessor
{
    public string Process(decimal amount) => $"Trừ {amount:C} qua PayPal";
}

public class BankTransferProcessor : IPaymentProcessor
{
    public string Process(decimal amount) => $"Trừ {amount:C} qua chuyển khoản ngân hàng";
}

// ĐÚNG LÀ FACTORY: một nơi DUY NHẤT biết cách tạo IPaymentProcessor.
public static class PaymentProcessorFactory
{
    private static readonly Dictionary<string, Func<IPaymentProcessor>> _creators = new()
    {
        ["creditcard"] = () => new CreditCardProcessor(),
        ["paypal"] = () => new PayPalProcessor(),
        ["banktransfer"] = () => new BankTransferProcessor(),
    };

    public static IPaymentProcessor Create(string method)
    {
        if (_creators.TryGetValue(method, out var creator))
            return creator();

        throw new ArgumentException($"Không hỗ trợ: {method}");
    }
}

public class Program
{
    // Cả hai nơi gọi giờ CHỈ gọi factory — không còn switch lặp lại.
    public static string HandleCheckout(string method, decimal amount) =>
        PaymentProcessorFactory.Create(method).Process(amount);

    public static string HandleRefund(string method, decimal amount) =>
        "Hoàn tiền: " + PaymentProcessorFactory.Create(method).Process(-amount);

    public static void Main()
    {
        Console.WriteLine(HandleCheckout("paypal", 100m));
        Console.WriteLine(HandleRefund("creditcard", 50m));
    }
}
```

**Điều gì thay đổi:** thêm `MomoProcessor` giờ chỉ cần **một dòng** trong `_creators` — không sửa `HandleCheckout`, không sửa `HandleRefund`, không sửa bất kỳ nơi gọi nào khác. Logic "biết cách tạo processor nào" nằm đúng **một nơi**.

**Điều gì xảy ra khi dùng sai:** nếu bạn quên đăng ký một `method` mới vào `_creators`, factory ném lỗi rõ ràng ngay tại điểm tạo — không để lỗi trôi xuống tận lúc gọi `.Process()` rồi mới `NullReferenceException` khó hiểu:

```text title="Lỗi khi gọi Create với method chưa đăng ký"
Unhandled exception. System.ArgumentException: Không hỗ trợ: momo
   at PaymentProcessorFactory.Create(String method)
```

### 1.4 Khi nào Factory là thừa (over-engineering)

Nếu bạn chỉ có **một class duy nhất, không có biến thể**, đừng bọc `new CreditCardProcessor()` vào một factory "cho chuẩn kiến trúc" — đó là thêm một lớp gián tiếp không giải quyết vấn đề gì cả:

```csharp title="C#"
// test:compile
public interface IEmailSender
{
    void Send(string to, string body);
}

public class SmtpEmailSender : IEmailSender
{
    public void Send(string to, string body) { /* gửi qua SMTP */ }
}

// THỪA: chỉ có 1 class, factory này không tách được gì cả, chỉ thêm một bước gọi.
public static class EmailSenderFactory
{
    public static IEmailSender Create() => new SmtpEmailSender();
}
```

Factory chỉ đáng dùng khi việc **chọn class nào** thực sự có logic (nhiều loại, điều kiện chọn, hoặc khởi tạo phức tạp cần che giấu) — như ví dụ thanh toán ở trên. Nếu chỉ có một cách tạo, gọi `new SmtpEmailSender()` trực tiếp (hoặc qua DI container) là đủ.

---

## 2. Strategy pattern

### 2.1 Vấn đề cụ thể: if-else chọn thuật toán ngày càng dài

Giả sử bạn tính phí vận chuyển theo loại giao hàng. Ban đầu chỉ có 2 loại, `if-else` rất gọn:

```csharp title="C#"
// test:compile
public static decimal CalculateShippingFeeV1(string type, decimal weight)
{
    if (type == "standard") return weight * 5_000m;
    else return weight * 15_000m; // express
}
```

Nhưng nghiệp vụ mở rộng dần: thêm `same-day`, `international`, mỗi loại có công thức riêng (có loại cộng phụ phí cố định, có loại theo bậc khối lượng). `if-else` bắt đầu phình to và **lồng logic tính toán chi tiết ngay trong một hàm**:

```csharp title="C#"
// test:compile
public static decimal CalculateShippingFeeV2(string type, decimal weight, decimal distanceKm)
{
    if (type == "standard")
    {
        return weight * 5_000m;
    }
    else if (type == "express")
    {
        return weight * 15_000m;
    }
    else if (type == "same-day")
    {
        return weight * 25_000m + 50_000m; // phụ phí cố định
    }
    else if (type == "international")
    {
        return weight * 30_000m + distanceKm * 2_000m; // theo khoảng cách
    }
    else
    {
        throw new ArgumentException($"Không hỗ trợ loại giao hàng: {type}");
    }
}
```

**Vấn đề cụ thể:** hàm này càng ngày càng dài, mỗi lần thêm loại giao hàng mới phải sửa **đúng hàm này** (vi phạm Open/Closed — đã học ở SOLID mức class, giờ thấy lại ở mức module: thêm hành vi mới không nên đòi sửa code cũ). Ngoài ra, muốn viết unit test riêng cho công thức `international` thì phải gọi qua cả hàm lớn, không test được công thức đó độc lập.

### 2.2 Định nghĩa

**Strategy pattern** là cách **đóng gói một thuật toán/hành vi thành một interface**, mỗi cách làm cụ thể là một class cài interface đó, và cho phép **đổi thuật toán lúc runtime** (qua constructor, property, hoặc tham số) mà không sửa code gọi.

### 2.3 Áp dụng Strategy để sửa vấn đề trên

```csharp title="C#"
// test:run
using System;
using System.Collections.Generic;

// Interface Strategy: mọi công thức tính phí đều cài interface này.
public interface IShippingStrategy
{
    decimal Calculate(decimal weight, decimal distanceKm);
}

public class StandardShipping : IShippingStrategy
{
    public decimal Calculate(decimal weight, decimal distanceKm) => weight * 5_000m;
}

public class ExpressShipping : IShippingStrategy
{
    public decimal Calculate(decimal weight, decimal distanceKm) => weight * 15_000m;
}

public class SameDayShipping : IShippingStrategy
{
    public decimal Calculate(decimal weight, decimal distanceKm) => weight * 25_000m + 50_000m;
}

public class InternationalShipping : IShippingStrategy
{
    public decimal Calculate(decimal weight, decimal distanceKm) => weight * 30_000m + distanceKm * 2_000m;
}

// "Context": không biết công thức cụ thể, chỉ biết gọi qua interface.
public class ShippingCalculator
{
    private readonly IShippingStrategy _strategy;

    public ShippingCalculator(IShippingStrategy strategy) => _strategy = strategy;

    public decimal CalculateFee(decimal weight, decimal distanceKm) =>
        _strategy.Calculate(weight, distanceKm);
}

public class Program
{
    public static void Main()
    {
        var calculator = new ShippingCalculator(new InternationalShipping());
        Console.WriteLine(calculator.CalculateFee(weight: 3m, distanceKm: 800m));

        // Đổi hành vi lúc runtime — chỉ cần đổi strategy được truyền vào,
        // KHÔNG sửa một dòng nào trong ShippingCalculator.
        var calculator2 = new ShippingCalculator(new SameDayShipping());
        Console.WriteLine(calculator2.CalculateFee(weight: 3m, distanceKm: 800m));
    }
}
```

**Điều gì thay đổi:** thêm loại giao hàng mới (`DroneShipping`) chỉ cần **một class mới** cài `IShippingStrategy`, không sửa `ShippingCalculator`. Mỗi công thức giờ **test được độc lập** — gọi trực tiếp `new InternationalShipping().Calculate(...)` mà không cần dựng cả hệ thống.

**Điều gì xảy ra khi dùng sai:** nếu bạn quên inject strategy (truyền `null`), lỗi xảy ra ngay khi gọi, rõ ràng chứ không âm thầm sai kết quả:

```text title="Lỗi khi truyền strategy null"
Unhandled exception. System.NullReferenceException: Object reference not set to an instance of an object.
   at ShippingCalculator.CalculateFee(Decimal weight, Decimal distanceKm)
```

### 2.4 So sánh với Enum + switch — khi nào KHÔNG cần Strategy đầy đủ

Nếu số lựa chọn **ít (2–3) và hiếm khi đổi**, `enum` + `switch` đơn giản hơn hẳn — không cần 4-5 file interface/class chỉ để chứa vài dòng công thức:

```csharp title="C#"
// test:compile
public enum ShippingType { Standard, Express }

public static class SimpleShippingCalculator
{
    // Với 2 lựa chọn ổn định, switch biểu thức (C# 8+) NGẮN GỌN HƠN Strategy đầy đủ.
    public static decimal Calculate(ShippingType type, decimal weight) => type switch
    {
        ShippingType.Standard => weight * 5_000m,
        ShippingType.Express => weight * 15_000m,
        _ => throw new ArgumentOutOfRangeException(nameof(type)),
    };
}
```

Quy tắc thực dụng: **Strategy đáng giá khi số lượng thuật toán nhiều, hay mở rộng, và/hoặc cần test độc lập từng thuật toán.** Với vài lựa chọn cố định, ít thay đổi — `enum + switch` là đủ, thêm interface/class ở đây là **thêm độ phức tạp không đổi lại giá trị gì**.

---

## 3. Decorator pattern

### 3.1 Vấn đề cụ thể: cần thêm logging/caching mà không sửa code gốc

Giả sử bạn có một service lấy giá sản phẩm từ database:

```csharp title="C#"
// test:run
using System;
using System.Collections.Generic;

public interface IProductPriceService
{
    decimal GetPrice(string productId);
}

public class DatabaseProductPriceService : IProductPriceService
{
    private readonly Dictionary<string, decimal> _fakeDb = new()
    {
        ["sku-1"] = 199_000m,
        ["sku-2"] = 499_000m,
    };

    public decimal GetPrice(string productId)
    {
        // Giả lập truy vấn database — có chi phí thật (I/O).
        if (_fakeDb.TryGetValue(productId, out var price)) return price;
        throw new KeyNotFoundException($"Không tìm thấy sản phẩm: {productId}");
    }
}
```

Bây giờ yêu cầu mới: cần **log mỗi lần gọi** (để debug) và **cache kết quả** (để giảm tải database) — nhưng **không được sửa** `DatabaseProductPriceService` vì đây là class đã có test, đã chạy ổn định production, và có thể có nhiều nơi khác dùng chung interface `IProductPriceService`. Cách tệ là sửa trực tiếp vào class gốc, trộn lẫn 3 trách nhiệm (đọc DB, log, cache) vào một nơi — vi phạm Single Responsibility, khó tắt/mở từng phần riêng.

### 3.2 Định nghĩa

**Decorator pattern** là cách **bọc một object bằng một object khác cùng interface**, để thêm hành vi mới (log, cache, kiểm tra quyền…) **trước hoặc sau** khi gọi object gốc, mà **không sửa một dòng code nào** của class gốc.

### 3.3 Áp dụng Decorator để sửa vấn đề trên

```csharp title="C#"
// test:run
using System;
using System.Collections.Generic;

public interface IProductPriceService
{
    decimal GetPrice(string productId);
}

public class DatabaseProductPriceService : IProductPriceService
{
    private readonly Dictionary<string, decimal> _fakeDb = new()
    {
        ["sku-1"] = 199_000m,
        ["sku-2"] = 499_000m,
    };

    public decimal GetPrice(string productId)
    {
        if (_fakeDb.TryGetValue(productId, out var price)) return price;
        throw new KeyNotFoundException($"Không tìm thấy sản phẩm: {productId}");
    }
}

// DECORATOR 1: thêm logging — bọc quanh BẤT KỲ IProductPriceService nào, không chỉ DatabaseProductPriceService.
public class LoggingProductPriceService : IProductPriceService
{
    private readonly IProductPriceService _inner;

    public LoggingProductPriceService(IProductPriceService inner) => _inner = inner;

    public decimal GetPrice(string productId)
    {
        Console.WriteLine($"[LOG] Bắt đầu GetPrice({productId})");
        var result = _inner.GetPrice(productId); // gọi hành vi gốc
        Console.WriteLine($"[LOG] Kết thúc GetPrice({productId}) = {result}");
        return result;
    }
}

// DECORATOR 2: thêm caching — bọc quanh service đã được bọc logging (xếp lớp được).
public class CachingProductPriceService : IProductPriceService
{
    private readonly IProductPriceService _inner;
    private readonly Dictionary<string, decimal> _cache = new();

    public CachingProductPriceService(IProductPriceService inner) => _inner = inner;

    public decimal GetPrice(string productId)
    {
        if (_cache.TryGetValue(productId, out var cached))
        {
            Console.WriteLine($"[CACHE HIT] {productId}");
            return cached;
        }

        var result = _inner.GetPrice(productId);
        _cache[productId] = result;
        return result;
    }
}

public class Program
{
    public static void Main()
    {
        // Xếp lớp decorator: Caching bọc ngoài Logging, Logging bọc ngoài Database.
        IProductPriceService service =
            new CachingProductPriceService(
                new LoggingProductPriceService(
                    new DatabaseProductPriceService()));

        Console.WriteLine(service.GetPrice("sku-1")); // lần 1: log + đọc DB, rồi cache lại
        Console.WriteLine(service.GetPrice("sku-1")); // lần 2: cache hit, KHÔNG log, KHÔNG đọc DB
    }
}
```

**Điều gì thay đổi:** `DatabaseProductPriceService` **không đổi một dòng nào** so với bản gốc. Logging và caching là hai class độc lập, **xếp lớp lên nhau tuỳ ý** — muốn bỏ caching, chỉ cần bỏ một dòng khởi tạo, không đụng vào logic đọc DB hay logic log.

**Điều gì xảy ra khi dùng sai:** nếu bạn quên gọi `_inner.GetPrice(...)` trong decorator (lỗi hay gặp khi mới viết Decorator), hành vi gốc **không bao giờ chạy**, bug âm thầm — không có exception, chỉ là kết quả sai hoặc thiếu:

```csharp title="C# — decorator viết SAI, quên gọi _inner"
// test:compile
public class BrokenLoggingService : IProductPriceService
{
    private readonly IProductPriceService _inner;
    public BrokenLoggingService(IProductPriceService inner) => _inner = inner;

    public decimal GetPrice(string productId)
    {
        Console.WriteLine($"[LOG] {productId}");
        return 0m; // SAI: quên gọi _inner.GetPrice(productId) — mất hoàn toàn hành vi gốc
    }
}
```

Đây là cạm bẫy thực chiến số một của Decorator: **luôn kiểm tra decorator có thật sự gọi `_inner`** — quên gọi là lỗi im lặng, khó phát hiện bằng mắt vì code vẫn compile và chạy, chỉ trả kết quả sai.

### 3.4 Khi nào Decorator là thừa

Nếu bạn chỉ cần thêm **một hành vi duy nhất, không cần tắt/mở độc lập, và không có ý định xếp lớp nhiều decorator khác nhau**, viết logic đó **trực tiếp trong class** thường rõ ràng hơn là dựng cả một chuỗi decorator:

```csharp title="C#"
// test:compile
using System;
using System.Collections.Generic;

// ĐỦ DÙNG: chỉ cần log, không cần tách lớp, không có kế hoạch thêm decorator khác.
public class SimpleProductPriceService : IProductPriceService
{
    private readonly Dictionary<string, decimal> _fakeDb = new() { ["sku-1"] = 199_000m };

    public decimal GetPrice(string productId)
    {
        Console.WriteLine($"[LOG] GetPrice({productId})"); // log trực tiếp, không cần decorator riêng
        if (_fakeDb.TryGetValue(productId, out var price)) return price;
        throw new KeyNotFoundException(productId);
    }
}
```

Decorator đáng giá khi bạn cần **kết hợp nhiều hành vi độc lập, tắt/mở riêng lẻ, tái dùng cho nhiều service khác** (ví dụ `LoggingXxxService` dùng lại được cho cả `IOrderService`, `IUserService` nếu chúng cùng một interface hình dạng tương tự). Nếu chỉ có đúng một hành vi, một nơi dùng, không có kế hoạch mở rộng — viết thẳng vào class là đủ, tách decorator ra là thêm số lượng file và một lớp gọi gián tiếp không đổi lại lợi ích gì.

---

## 4. Bảng so sánh ba pattern

Bây giờ đã hiểu riêng từng pattern qua vấn đề cụ thể của nó, đây là so sánh trực diện:

| Khía cạnh | Factory | Strategy | Decorator |
|-----------|---------|----------|-----------|
| Giải quyết vấn đề gì | Logic **tạo object** rải rác, khó thêm loại mới | Logic **chọn thuật toán/hành vi** cứng trong if-else, khó test riêng | Cần **thêm hành vi** (log, cache, quyền) mà không sửa class gốc |
| Input | Một điều kiện chọn (tên, enum, tham số) | Một thuật toán được inject | Một object gốc cùng interface, được bọc lại |
| Output | Một object đã tạo xong | Kết quả tính toán theo thuật toán đã chọn | Object cùng interface, hành vi = gốc + thêm |
| Có gọi lại object khác không | Không — chỉ tạo mới | Không — object context gọi thẳng strategy | **Có** — decorator luôn gọi `_inner` (nếu quên, mất hành vi gốc) |
| Số lượng object khi dùng | 1 object được factory trả về | 1 strategy tại một thời điểm | Nhiều lớp bọc lồng nhau (0..N decorator quanh 1 gốc) |
| Khi nào là thừa | Chỉ có 1 class, không có logic chọn | Chỉ 2-3 lựa chọn cố định, ít đổi → dùng `enum + switch` | Chỉ 1 hành vi, 1 nơi dùng, không cần tắt/mở riêng → viết thẳng vào class |

**Điểm chung dễ nhầm giữa ba pattern:** cả ba đều dùng **interface** để tách phần "cố định" (code gọi) khỏi phần "thay đổi" (implementation cụ thể) — đây là kỹ thuật nền chung (đa hình/polymorphism, đã học ở P1-OOP). Khác biệt nằm ở **mục đích tách**: Factory tách việc *tạo*, Strategy tách việc *tính toán/hành vi thay thế lẫn nhau*, Decorator tách việc *bổ sung hành vi bao quanh hành vi đã có*.

---

## 5. Cạm bẫy & thực chiến

- **Factory rải logic điều kiện ra ngoài factory:** nếu code gọi vẫn phải `if (method == "creditcard") { ... factory.Create(...) } else { ... }`, bạn chưa thực sự tách logic chọn — factory chỉ có ý nghĩa khi *toàn bộ* quyết định "tạo gì" nằm trong nó, nơi gọi chỉ truyền tham số và nhận object.
- **Decorator quên gọi `_inner` (lỗi im lặng đã minh hoạ ở mục 3.3):** đây là lỗi runtime khó phát hiện nhất trong ba pattern vì code vẫn compile, không throw exception — chỉ trả sai/thiếu kết quả. Luôn viết test riêng cho từng decorator, khẳng định hành vi gốc **thực sự được gọi** (ví dụ assert giá trị trả về khớp với service gốc, không phải giá trị mặc định).
- **Strategy stateful bị tái sử dụng nhầm giữa nhiều request:** nếu một class strategy có field lưu trạng thái (ví dụ đếm số lần gọi) và bạn đăng ký nó làm **singleton** trong DI container, các request khác nhau sẽ **chia sẻ chung trạng thái đó** — một request có thể vô tình đọc dữ liệu tính toán dở của request khác. Strategy nên là **stateless** (không field mutable), hoặc đăng ký lifetime `Transient`/`Scoped` phù hợp — đây chính là điểm phải phân biệt **Singleton pattern (GoF, tự tay code một instance duy nhất)** khác với **Singleton lifetime (DI container tự quản lý một instance trong vòng đời ứng dụng)**: dùng sai lifetime cho strategy có trạng thái là lỗi rất khó tái hiện (chỉ lộ ra khi có tải đồng thời).
- **Áp cả ba pattern vào một tính năng chỉ vì "học rồi phải dùng" (over-engineering):** ví dụ một tính năng gửi email đơn giản, chỉ một cách gửi, không cần log/cache thêm — nếu bạn vẫn dựng `EmailFactory` + `IEmailStrategy` + `LoggingEmailDecorator` cho nó, bạn đã biến 10 dòng logic thành 5 file, tăng thời gian đọc hiểu mà không giải quyết vấn đề thực nào. Luôn tự hỏi: *vấn đề cụ thể nào đang tồn tại mà pattern này sửa?* Nếu không trả lời được bằng một câu cụ thể (như các mục 1.1, 2.1, 3.1 ở trên), đừng thêm pattern.
- **Nhầm Factory pattern (GoF) với "factory method" chung trong .NET (ví dụ `Task.Factory`, hay các hàm tĩnh `XxxFactory.Create`):** khái niệm cốt lõi giống nhau (tách logic tạo ra một nơi), nhưng không phải mọi hàm tĩnh trả về object đều là "Factory pattern" theo đúng nghĩa GoF (có phiên bản Abstract Factory, Factory Method tách biệt qua kế thừa). Ở mức thực dụng, chỉ cần nhớ: **tên gọi không quan trọng bằng việc bạn có thực sự tách được logic chọn/tạo ra một nơi hay không.**

---

## 6. Bài tập

**Bài 1 — Factory.** Bạn có 3 loại thông báo: `EmailNotifier`, `SmsNotifier`, `PushNotifier`, đều cài `INotifier` với phương thức `Send(string message)`. Viết một `NotifierFactory` để tạo đúng notifier theo tên (`"email"`, `"sms"`, `"push"`), ném `ArgumentException` nếu tên không hợp lệ.

??? success "Lời giải + vì sao"
    ```csharp title="C#"
    // test:run
    using System;
    using System.Collections.Generic;

    public interface INotifier
    {
        void Send(string message);
    }

    public class EmailNotifier : INotifier
    {
        public void Send(string message) => Console.WriteLine($"Email: {message}");
    }

    public class SmsNotifier : INotifier
    {
        public void Send(string message) => Console.WriteLine($"SMS: {message}");
    }

    public class PushNotifier : INotifier
    {
        public void Send(string message) => Console.WriteLine($"Push: {message}");
    }

    public static class NotifierFactory
    {
        private static readonly Dictionary<string, Func<INotifier>> _creators = new()
        {
            ["email"] = () => new EmailNotifier(),
            ["sms"] = () => new SmsNotifier(),
            ["push"] = () => new PushNotifier(),
        };

        public static INotifier Create(string type)
        {
            if (_creators.TryGetValue(type, out var creator)) return creator();
            throw new ArgumentException($"Không hỗ trợ: {type}");
        }
    }

    public class Program
    {
        public static void Main()
        {
            NotifierFactory.Create("sms").Send("Đơn hàng đã giao");
        }
    }
    ```
    **Vì sao đúng:** logic "biết cách tạo `INotifier` nào" nằm đúng một nơi (`_creators`), thêm `SlackNotifier` chỉ cần thêm một dòng, không sửa code gọi `NotifierFactory.Create(...)` ở bất kỳ đâu.

**Bài 2 — Decorator.** Bạn có `IOrderService` với `decimal GetTotal(string orderId)`. Viết một decorator `RetryOrderServiceDecorator` bọc quanh `IOrderService` để **thử lại tối đa 2 lần** nếu lần gọi đầu ném exception, không sửa class `IOrderService` gốc.

??? success "Lời giải + vì sao"
    ```csharp title="C#"
    // test:run
    using System;

    public interface IOrderService
    {
        decimal GetTotal(string orderId);
    }

    public class FlakyOrderService : IOrderService
    {
        private int _attempt = 0;

        public decimal GetTotal(string orderId)
        {
            _attempt++;
            if (_attempt < 2) throw new InvalidOperationException("Lỗi tạm thời (giả lập)");
            return 250_000m;
        }
    }

    // Decorator: bọc quanh IOrderService bất kỳ, thêm hành vi retry mà không sửa gốc.
    public class RetryOrderServiceDecorator : IOrderService
    {
        private readonly IOrderService _inner;
        private readonly int _maxRetries;

        public RetryOrderServiceDecorator(IOrderService inner, int maxRetries = 2)
        {
            _inner = inner;
            _maxRetries = maxRetries;
        }

        public decimal GetTotal(string orderId)
        {
            Exception? lastError = null;
            for (int i = 0; i <= _maxRetries; i++)
            {
                try
                {
                    return _inner.GetTotal(orderId); // luôn gọi hành vi gốc
                }
                catch (Exception ex)
                {
                    lastError = ex;
                }
            }
            throw new InvalidOperationException("Hết số lần thử lại", lastError);
        }
    }

    public class Program
    {
        public static void Main()
        {
            IOrderService service = new RetryOrderServiceDecorator(new FlakyOrderService());
            Console.WriteLine(service.GetTotal("order-1")); // lần 1 lỗi, lần 2 thành công qua retry
        }
    }
    ```
    **Vì sao đúng:** `FlakyOrderService` không đổi gì; hành vi retry nằm hoàn toàn trong decorator, luôn gọi `_inner.GetTotal(orderId)` (không quên gọi — đúng cạnh cảnh báo ở mục 3.3/5), và có thể bỏ decorator này bất kỳ lúc nào chỉ bằng cách đổi lại `service = new FlakyOrderService()`.

---

## Tự kiểm tra

1. Factory pattern giải quyết vấn đề cụ thể gì — nêu đúng triệu chứng code trước khi áp dụng.
2. Vì sao `if-else` chọn thuật toán khác về bản chất với Strategy pattern, không chỉ là "viết dài hơn"?
3. Decorator có sửa class gốc để thêm hành vi mới không? Vì sao đây là điểm mấu chốt của pattern này?
4. Nêu một tình huống Strategy pattern là over-engineering, và cách đơn giản hơn nên dùng.
5. Nêu một tình huống Decorator pattern là over-engineering.
6. Lỗi lập trình phổ biến nhất khi viết Decorator là gì, và vì sao khó phát hiện bằng mắt?
7. Vì sao một Strategy có trạng thái (stateful) đăng ký làm singleton trong DI container lại nguy hiểm?

??? note "Đáp án"
    1. Logic tạo object (chọn class cụ thể, `switch-case`/`if-else` tạo instance) **lặp lại ở nhiều nơi gọi khác nhau**, khiến việc thêm một loại object mới phải sửa nhiều chỗ, dễ quên sửa sót gây bug.
    2. `if-else` chọn cứng trong một hàm, không tách được thành đơn vị độc lập, không test riêng được từng nhánh, không đổi được lúc runtime mà không sửa code. Strategy đóng gói mỗi thuật toán vào **một class riêng cài cùng interface**, cho phép truyền vào (inject) và đổi mà không sửa "context" gọi nó.
    3. **Không** — đây chính là điểm mấu chốt: Decorator bọc object gốc bằng một class khác cùng interface, hành vi mới được thêm ở lớp bọc, class gốc không đổi một dòng nào, vẫn dùng lại được ở nơi khác không cần decorator.
    4. Ví dụ: chỉ có 2 mức giá vận chuyển cố định, hiếm khi thay đổi — dùng `enum + switch` đơn giản hơn hẳn so với dựng interface + nhiều class chỉ để chứa vài dòng công thức.
    5. Ví dụ: chỉ cần thêm log cho đúng một service, một nơi dùng, không có kế hoạch thêm hành vi khác hay tái dùng cho service khác — viết thẳng dòng log vào trong class đó đơn giản hơn dựng cả decorator riêng.
    6. Quên gọi `_inner` (hành vi gốc) trong decorator. Khó phát hiện vì code vẫn **compile và chạy bình thường**, không có exception — chỉ trả về kết quả sai hoặc giá trị mặc định, chỉ lộ ra khi so sánh kết quả thực tế.
    7. Vì DI container chỉ tạo **một instance duy nhất** cho toàn ứng dụng khi đăng ký singleton; nếu strategy đó có field lưu trạng thái thay đổi được (mutable state), nhiều request đồng thời sẽ **đọc/ghi chung trạng thái đó**, gây lỗi khó tái hiện (race condition), chỉ lộ ra khi có tải đồng thời thực tế.

---

??? abstract "DEEP DIVE — nhìn theo góc GoF gốc và biến thể trong .NET"
    **Factory Method vs Abstract Factory (GoF phân biệt, thực dụng thường gộp chung):** bản gốc trong "Design Patterns" (Gang of Four) tách hai khái niệm: *Factory Method* là một phương thức (thường `virtual`/`abstract` trên class cha) để subclass override quyết định tạo loại con nào; *Abstract Factory* là một *họ* factory tạo ra nhiều object liên quan với nhau (ví dụ `IUiFactory` tạo cả `IButton` và `ICheckbox` cùng theo một "theme"). Ví dụ `PaymentProcessorFactory` ở mục 1 là dạng thực dụng đơn giản hơn cả hai (một static method + dictionary tra cứu) — đủ dùng cho phần lớn code nghiệp vụ, không cần đúng khuôn GoF.

    **Strategy vs Template Method:** cả hai đều "thay đổi được một phần hành vi", nhưng Strategy thay **toàn bộ thuật toán qua composition** (truyền object khác vào), còn Template Method thay **một bước con trong một thuật toán cố định qua kế thừa** (override một phương thức `protected virtual` trong class cha). Nếu bạn thấy mình đang override một phương thức nhỏ trong một quy trình lớn cố định — đó gần Template Method hơn Strategy; đây là lý do các ví dụ ở mục 2 dùng **inject qua constructor** (composition), không dùng kế thừa.

    **Decorator vs Middleware pipeline trong ASP.NET Core:** middleware pipeline (`app.Use(...)`) mà bạn đã học ở P3 thực chất là **một dạng Decorator áp dụng cho toàn bộ HTTP pipeline** — mỗi middleware "bọc" middleware kế tiếp, có thể làm gì đó trước khi gọi `next()` và sau khi `next()` trả về, giống hệt cấu trúc `_inner.GetPrice(...)` ở mục 3.3. Nhìn lại middleware bạn viết ở P3 dưới lăng kính Decorator sẽ thấy nó không phải một khái niệm hoàn toàn mới — cùng một ý tưởng "bọc thêm hành vi quanh hành vi có sẵn", chỉ khác quy mô (một request pipeline, không phải một object đơn lẻ).

    **Kết hợp cả ba trong thực tế:** không hiếm khi một hệ thống dùng cả ba cùng lúc mà không "cố ý" — ví dụ một `IPaymentProcessorFactory` (Factory, mục 1) trả về một `IPaymentProcessor` mà bản thân nó có thể là kết quả của một chuỗi Strategy (công thức tính phí giao dịch khác nhau theo nhà cung cấp, mục 2) đã được bọc thêm `LoggingPaymentProcessor` (Decorator, mục 3) trước khi trả ra. Điều quan trọng không phải là "dùng đủ 3 pattern cho oách", mà là **mỗi lớp tách ra giải quyết đúng một vấn đề cụ thể đang tồn tại** — nếu một trong ba lớp đó không giải quyết vấn đề gì (ví dụ không có nhiều nhà cung cấp, không cần log), bỏ lớp đó đi, đừng giữ vì "kiến trúc cho đẹp".

Tiếp theo -> cqrs va khi nao model doc/ghi tach biet dang gia tri
