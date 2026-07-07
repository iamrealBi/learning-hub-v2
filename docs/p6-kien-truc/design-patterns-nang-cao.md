---
tier: core
status: core
owner: core-team
verified_on: "2026-07-03"
dotnet_version: "10.0"
bloom: "Analyze"
requires: [p6-patterns-basic]
est_minutes_fast: 70
---

# Design Patterns nâng cao: Observer, Singleton, Adapter

!!! info "bạn đang ở đây · p6 → node `p6-patterns-advanced`"
    **cần trước:** đã biết class/interface/kế thừa (oop), delegate và `event` (delegates-events), và các pattern nền tảng ở node `p6-patterns-basic` (Factory, Strategy, Decorator).
    **mở khoá:** đọc hiểu kiến trúc event-driven, phân biệt đúng hai khái niệm cùng tên "Singleton", và biết cách bọc thư viện ngoài mà không để nó rò rỉ vào toàn bộ codebase.

> **Mục tiêu (đo được):** Sau chương này bạn (1) **giải thích** vì sao Observer tách rời publisher khỏi danh sách subscriber, và **cài đặt** được nó bằng `event`/delegate của C#; (2) **phân biệt** rõ Singleton pattern (GoF, tự code) với Singleton lifetime (DI container) — hai khái niệm khác nhau dùng chung một cái tên; (3) **thiết kế** một Adapter bọc thư viện ngoài có interface không tương thích với interface nội bộ; (4) **nhận diện** khi nào áp dụng một trong ba pattern này là over-engineering, làm code phức tạp không cần thiết.

---

## 0. Đoán nhanh trước khi học

Bạn có class `OrderService.PlaceOrder(...)`. Ba việc **khác nhau** đều cần chạy sau khi đặt hàng thành công: gửi email xác nhận, trừ hàng trong kho, ghi log. Bạn viết thẳng cả ba lời gọi vào trong `PlaceOrder`:

```csharp title="Vấn đề: OrderService biết quá nhiều"
// test:skip đoạn trích minh hoạ vấn đề, không đầy đủ để chạy độc lập
public class OrderService
{
    public void PlaceOrder(Order order)
    {
        SaveToDatabase(order);
        EmailSender.SendConfirmation(order);      // OrderService phải biết EmailSender
        InventoryService.Reduce(order.Items);      // và biết InventoryService
        AuditLog.Write($"Order {order.Id} placed"); // và biết AuditLog
    }
}
```

??? question "Đoán trước: ba tháng sau, sếp yêu cầu thêm 'gửi SMS khi đặt hàng'. Bạn sửa ở đâu? Có rủi ro gì?"
    Bạn phải **mở lại và sửa** `OrderService.PlaceOrder` — thêm một dòng gọi `SmsSender.Send(...)`. Rủi ro: mỗi lần có thêm một bên "muốn biết" về việc đặt hàng, `OrderService` lại phình to và phải sửa lại, dù logic đặt hàng THẬT SỰ (lưu database) không đổi. Tệ hơn, nếu `EmailSender` ném exception, cả `PlaceOrder` gãy theo — dù gửi email lỗi không nên làm hỏng việc đặt hàng.

    Đây chính là vấn đề mà **Observer pattern** giải quyết ở Mục 1: để `OrderService` chỉ "thông báo có sự kiện xảy ra", còn ai muốn nghe thì tự đăng ký — không cần `OrderService` biết tên của họ.

---

## 1. Observer pattern

### 1.1 Định nghĩa

**Observer là gì?** Observer là một pattern trong đó **một object (subject/publisher) thông báo cho nhiều object khác (observer/subscriber) khi trạng thái của nó thay đổi**, mà **subject không cần biết cụ thể có bao nhiêu observer, hay chúng là loại gì** — subject chỉ biết "có ai đang lắng nghe" qua một danh sách trừu tượng.

### 1.2 Ví dụ tối thiểu

Trước khi ghép vào bài toán `OrderService`, đây là ví dụ tối thiểu — một `Counter` phát thông báo mỗi khi giá trị đổi, không quan tâm ai nghe:

```csharp title="Observer tối thiểu bằng event"
// test:run
var counter = new Counter();

// Đăng ký hai observer khác nhau — Counter không biết chúng là ai
counter.Changed += value => Console.WriteLine($"Observer A thấy: {value}");
counter.Changed += value => Console.WriteLine($"Observer B nhân đôi: {value * 2}");

counter.Increment();   // cả hai observer cùng được gọi
counter.Increment();

class Counter
{
    private int _value;
    public event Action<int>? Changed;   // "cổng" cho observer đăng ký

    public void Increment()
    {
        _value++;
        Changed?.Invoke(_value);   // thông báo, KHÔNG biết ai đang nghe
    }
}
```

```text title="Kết quả"
Observer A thấy: 1
Observer B nhân đôi: 2
Observer A thấy: 2
Observer B nhân đôi: 4
```

**Điểm mấu chốt:** `Counter` không có một dòng nào nhắc tới "Observer A" hay "Observer B" — nó chỉ khai báo một `event`. Ai muốn nghe thì `+=` vào, ai không muốn nữa thì `-=` ra. `Counter` hoàn toàn không đổi dù bạn thêm bao nhiêu observer.

### 1.3 Vấn đề cụ thể Observer giải quyết

Áp dụng lại vào `OrderService` ở Mục 0: vấn đề là `PlaceOrder` phải **biết tên** của `EmailSender`, `InventoryService`, `AuditLog` — tức phụ thuộc cứng vào cả ba, và phải sửa code mỗi khi thêm một bên quan tâm mới. Dưới đây là cách áp dụng Observer để sửa: `OrderService` chỉ phát ra một `event`, không tự gọi tên bất kỳ ai.

```csharp title="Sửa OrderService bằng Observer (event)"
// test:run
var orderService = new OrderService();

// Ba "observer" độc lập, tự đăng ký — OrderService không biết chúng tồn tại
orderService.OrderPlaced += order => Console.WriteLine($"[Email] Xác nhận đơn #{order.Id} đã gửi");
orderService.OrderPlaced += order => Console.WriteLine($"[Kho] Đã trừ {order.Items} món cho đơn #{order.Id}");
orderService.OrderPlaced += order => Console.WriteLine($"[Log] Order {order.Id} placed");

orderService.PlaceOrder(new Order(Id: 101, Items: 3));

public record Order(int Id, int Items);

public class OrderService
{
    public event Action<Order>? OrderPlaced;   // "cổng" thông báo, không biết ai nghe

    public void PlaceOrder(Order order)
    {
        // Logic THẬT của đặt hàng — chỉ việc này, không việc khác
        Console.WriteLine($"[DB] Lưu đơn #{order.Id}");
        OrderPlaced?.Invoke(order);   // thông báo "đã đặt xong", ai quan tâm tự xử lý
    }
}
```

```text title="Kết quả"
[DB] Lưu đơn #101
[Email] Xác nhận đơn #101 đã gửi
[Kho] Đã trừ 3 món cho đơn #101
[Log] Order 101 placed
```

Bây giờ thêm "gửi SMS" chỉ là thêm một dòng `orderService.OrderPlaced += ...` ở nơi cấu hình ứng dụng — **`OrderService` không cần sửa một chữ nào**. Đây chính là lợi ích cốt lõi: subject (đối tượng phát) và observer (đối tượng nghe) **không phụ thuộc lẫn nhau về kiểu**, chỉ phụ thuộc vào chữ ký delegate chung.

!!! info "Observer trong C# = event/delegate, không cần interface IObserver riêng"
    Sách Gang of Four (1994) mô tả Observer bằng hai interface `Subject`/`Observer` với phương thức `Attach`/`Detach`/`Notify` — vì Java/C++ thời đó không có delegate hạng nhất (first-class). C# đã có `event`/`delegate` xây sẵn đúng ngữ nghĩa Observer (đăng ký nhiều handler, thông báo tất cả), nên bài chương delegates-events chính là "Observer pattern được cài đặt sẵn trong ngôn ngữ" — thứ bạn học ở đó (`+=`, `?.Invoke()`, unsubscribe để tránh rò rỉ) chính là cách cài Observer chuẩn trong C#, không cần tự viết `interface IObserver<T> { void OnNext(T value); }` trừ khi cần ngữ nghĩa phức tạp hơn (xem 1.5).

### 1.4 Khi nào KHÔNG nên dùng Observer (over-engineering)

Nếu chỉ có **một** nơi gọi và **một** nơi xử lý, theo một trình tự cố định luôn giống nhau (ví dụ `PlaceOrder` luôn phải gọi `SendConfirmation` ngay sau khi lưu, không ai khác cần biết, và không có ý định thêm subscriber mới), thì viết thẳng lời gọi phương thức là đủ và **rõ ràng hơn** Observer. Observer đánh đổi tính rõ ràng của luồng gọi (đọc code không thấy ngay "ai sẽ chạy khi X xảy ra" — phải tìm hết các nơi `+=`) để lấy khả năng mở rộng không cần sửa subject. Chỉ trả giá đó khi thực sự có **nhiều bên độc lập, không biết trước hết**, cùng quan tâm một sự kiện — đúng như tình huống `OrderPlaced` ở trên. Nếu chỉ có một bên quan tâm duy nhất, thêm `event` vào là thừa một lớp gián tiếp không giúp gì.

### 1.5 Khi Observer phức tạp hơn: IObservable/IObserver

BCL có cặp interface `IObservable<T>`/`IObserver<T>` (namespace `System`) cho trường hợp Observer cần ngữ nghĩa đầy đủ hơn `event` đơn giản — có `OnNext`, `OnError`, `OnCompleted`, và trả về một `IDisposable` để hủy đăng ký gọn gàng. Đây là nền của Reactive Extensions (Rx.NET). Với hầu hết nhu cầu trong ứng dụng nghiệp vụ thông thường, `event`/delegate là đủ; chỉ cần `IObservable<T>` khi có luồng dữ liệu bất đồng bộ phức tạp (nhiều sự kiện lỗi/hoàn tất cần phân biệt) — vượt phạm vi chương này.

### 1.6 Nhiều observer, thứ tự chạy, và một observer lỗi không nên chặn observer khác

Multicast delegate (đã học ở delegates-events) chạy các handler **theo đúng thứ tự đăng ký**, và nếu một handler ném exception, các handler đăng ký **sau** nó sẽ không chạy — chuỗi bị đứt. Với Observer pattern, đây thường là hành vi **không mong muốn**: observer "gửi email" bị lỗi không nên khiến observer "ghi log" (đăng ký sau) không chạy được. Cách phòng: publisher tự duyệt `GetInvocationList()` và bọc `try/catch` quanh từng observer, để một observer lỗi không ảnh hưởng các observer khác.

```csharp title="Observer: một handler lỗi không nên chặn handler khác"
// test:run
var orderService = new OrderServiceSafe();
orderService.OrderPlaced += _ => throw new InvalidOperationException("Email server sập");
orderService.OrderPlaced += order => Console.WriteLine($"[Log] Order {order.Id} placed");

orderService.PlaceOrder(new OrderSafe(Id: 7));

public record OrderSafe(int Id);

public class OrderServiceSafe
{
    public event Action<OrderSafe>? OrderPlaced;

    public void PlaceOrder(OrderSafe order)
    {
        Console.WriteLine($"[DB] Lưu đơn #{order.Id}");
        RaiseSafely(order);
    }

    private void RaiseSafely(OrderSafe order)
    {
        if (OrderPlaced is null) return;
        foreach (Action<OrderSafe> observer in OrderPlaced.GetInvocationList())
        {
            try { observer(order); }
            catch (Exception ex) { Console.WriteLine($"[Cảnh báo] một observer lỗi: {ex.Message}"); }
        }
    }
}
```

```text title="Kết quả"
[DB] Lưu đơn #7
[Cảnh báo] một observer lỗi: Email server sập
[Log] Order 7 placed
```

**Điểm mấu chốt:** So với gọi trực tiếp `OrderPlaced?.Invoke(order)` (như ví dụ 1.3), `RaiseSafely` tốn thêm một vòng lặp và `try/catch` — đây là chi phí chấp nhận được để đảm bảo một observer hỏng không kéo sập observer khác. Chỉ cần làm điều này khi các observer **thật sự độc lập về nghiệp vụ** (như gửi email và ghi log không liên quan tới nhau); nếu một observer lỗi thì các observer sau **nên** dừng theo (ví dụ bước 2 phụ thuộc kết quả bước 1), giữ hành vi mặc định của multicast delegate là đúng, không cần thêm `try/catch` này.

---

## 2. Singleton pattern (GoF) — KHÁC Singleton lifetime (DI)

### 2.1 Định nghĩa

**Singleton pattern (GoF) là gì?** Singleton là một pattern **tự code**, đảm bảo một class **chỉ có đúng một instance tồn tại trong toàn bộ chương trình**, và cung cấp một điểm truy cập toàn cục (thường là một property/method `static`) để lấy instance đó — class tự chịu trách nhiệm ngăn ai đó tạo thêm instance thứ hai bằng `new`.

### 2.2 Ví dụ tối thiểu

```csharp title="Singleton pattern (GoF) tối thiểu: tự đảm bảo chỉ một instance"
// test:run
var a = AppConfig.Instance;
var b = AppConfig.Instance;
Console.WriteLine(ReferenceEquals(a, b));   // True — cùng một instance

a.Setting = "đã đổi ở a";
Console.WriteLine(b.Setting);                // "đã đổi ở a" — vì a và b là CÙNG một object

public sealed class AppConfig
{
    private static readonly AppConfig _instance = new();

    // Constructor private -> KHÔNG ai bên ngoài gọi được "new AppConfig()"
    private AppConfig() { }

    public static AppConfig Instance => _instance;

    public string Setting { get; set; } = "mặc định";
}
```

```text title="Kết quả"
True
đã đổi ở a
```

**Điểm mấu chốt:** Constructor được đánh dấu `private` — đây là phần bắt buộc để pattern này "tự đảm bảo": không có `private`, ai đó vẫn viết được `new AppConfig()` tạo instance thứ hai, phá vỡ đúng cam kết "chỉ một instance" mà pattern hứa hẹn.

**Lỗi nếu bỏ `private` khỏi constructor:** mất hoàn toàn cam kết duy nhất — code sau vẫn biên dịch được (không có `private` chặn), nhưng lại đúng là điều Singleton pattern muốn ngăn:

```csharp title="Thiếu private constructor: pattern mất tác dụng (minh hoạ, không phải lỗi biên dịch)"
// test:run — biên dịch và chạy OK; đây chính là vấn đề: KHÔNG có gì chặn được instance thứ hai
var x = new BrokenConfig();          // biên dịch OK — nhưng đây là instance THỨ HAI
var y = BrokenConfig.Instance;
Console.WriteLine(ReferenceEquals(x, y));   // False -> đã phá vỡ đúng điều Singleton hứa "chỉ một instance"

public sealed class BrokenConfig
{
    private static readonly BrokenConfig _instance = new();
    public static BrokenConfig Instance => _instance;
    // Thiếu "private" ở constructor -> constructor mặc định public
}
```

```text title="Kết quả"
False
```

### 2.3 Vấn đề cụ thể Singleton (GoF) giải quyết

Singleton (GoF) giải quyết đúng một vấn đề: có những resource **về bản chất chỉ nên tồn tại một lần** trong toàn chương trình — ví dụ một bộ đếm ID toàn cục, hoặc một cấu hình đọc-một-lần-dùng-mọi-nơi — và bạn muốn **ngôn ngữ tự chặn** việc ai đó vô tình tạo thêm bản thứ hai (thứ mà nếu xảy ra sẽ gây lỗi logic, ví dụ hai bộ đếm ID độc lập sinh trùng số).

### 2.4 PHÂN BIỆT với Singleton lifetime của DI container

Đây là điểm dễ nhầm nhất: **hai khái niệm cùng tên "Singleton" nhưng là hai thứ khác nhau**, đã học Singleton *lifetime* ở chương dependency-injection (P3) — nhắc lại ngắn để đối chiếu, không dạy lại từ đầu.

| | Singleton pattern (GoF) | Singleton lifetime (DI container) |
|---|---|---|
| Ai đảm bảo chỉ-một-instance? | Class **tự code** (constructor `private` + field `static`) | **DI container** (`AddSingleton<T>`) đảm bảo, class không biết gì về việc này |
| Phạm vi "duy nhất" | Toàn bộ **AppDomain/process** — tuyệt đối, không có ngoại lệ | Duy nhất **trong một `IServiceProvider`** (một container) — tạo container thứ hai (ví dụ trong test) sẽ có instance khác |
| Có `new` thủ công được không? | **Không** — constructor `private` chặn cứng | **Có** — class vẫn là class bình thường, `new MyService()` vẫn hợp lệ, chỉ là *nếu* lấy qua DI thì luôn ra cùng instance |
| Test được không? | Khó — global state, một test đổi giá trị ảnh hưởng test khác chạy sau, không "tháo" ra thay bằng fake được | Dễ — chỉ cần đăng ký một implementation khác (`AddSingleton<IFoo, FakeFoo>()`) trong container test |
| Điểm truy cập | `AppConfig.Instance` (static, gọi từ bất kỳ đâu) | Constructor injection (`ctor(IFoo foo)`) — không có điểm truy cập tĩnh toàn cục |

```csharp title="Singleton LIFETIME của DI — không phải Singleton pattern GoF"
// test:compile
var builder = WebApplication.CreateBuilder(args);

// "Singleton" ở đây là LIFETIME: container đảm bảo chỉ tạo MỘT AppClock
// cho toàn bộ vòng đời app — nhưng AppClock vẫn là class BÌNH THƯỜNG,
// constructor public, ai muốn vẫn new AppClock() được (không bị chặn).
builder.Services.AddSingleton<AppClock>();

var app = builder.Build();
app.MapGet("/", (AppClock clock) => Results.Ok(clock.Now));
app.Run();

public class AppClock
{
    public AppClock() { }   // constructor PUBLIC — khác hẳn Singleton GoF ở 2.2
    public DateTime Now => DateTime.UtcNow;
}
```

!!! danger "Nhầm lẫn thường gặp: 'Singleton lifetime nghĩa là class phải theo Singleton pattern'"
    KHÔNG đúng. `AddSingleton<AppClock>()` chỉ nói "container giữ và trả lại đúng một instance của `AppClock` cho mọi request lấy qua container". `AppClock` **không** cần constructor `private`, **không** cần field `static Instance`. Nếu bạn viết `AppClock` theo Singleton pattern GoF (constructor `private`, `AppClock.Instance` tĩnh) VÀ đồng thời đăng ký `AddSingleton<AppClock>()`, bạn đang **trộn hai cơ chế** không cần thiết — DI container không gọi qua `AppClock.Instance`, nó gọi constructor trực tiếp (nên constructor phải public), khiến pattern GoF của bạn vô dụng hoặc gây lỗi biên dịch (container không gọi được constructor `private`).

### 2.5 Khi nào KHÔNG nên dùng Singleton pattern GoF (over-engineering)

Trong một ứng dụng ASP.NET Core hiện đại có DI container sẵn có (đã học ở P3), Singleton *pattern* GoF (constructor `private`, `static Instance`) hầu như **không cần dùng nữa** — dùng `AddSingleton<T>()` của DI container đạt được cùng lợi ích (một instance chia sẻ) mà **vẫn test được** (tráo implementation khi test) và **không có global static state** (nguồn lỗi kinh điển: test A đổi state, test B chạy sau đọc thấy state cũ, thất bại ngẫu nhiên tùy thứ tự chạy test). Chỉ còn dùng Singleton pattern GoF thật sự cho code **không chạy trong DI container** — ví dụ một class utility trong một thư viện console nhỏ, không có `IServiceProvider` nào quản lý vòng đời. Nếu bạn đang viết ASP.NET Core Web API, gần như luôn chọn `AddSingleton<T>()`, không phải tự code Singleton GoF.

### 2.6 Chứng minh cụ thể: vì sao Singleton GoF khó test còn Singleton lifetime dễ test

Đoạn dưới đây chứng minh trực tiếp khẳng định ở bảng 2.4 bằng code chạy được — không chỉ nói "khó test" mà cho thấy **chính xác chỗ nào** bị kẹt.

```csharp title="Singleton GoF: không có cách nào thay _instance bằng một bản giả (fake) khi test"
// test:run
// Code "nghiệp vụ" dùng thẳng điểm truy cập tĩnh:
Console.WriteLine(BillingClock.Instance.Today());

public sealed class BillingClock
{
    private static readonly BillingClock _instance = new();
    private BillingClock() { }
    public static BillingClock Instance => _instance;

    // Muốn test "nghiệp vụ chạy đúng vào ngày 30/2" ? KHÔNG THỂ — Today() luôn
    // trả về giờ hệ thống thật, và không có "chỗ nào" để nhét ngày giả vào,
    // vì không ai truyền BillingClock qua constructor — code gọi thẳng Instance.
    public DateTime Today() => DateTime.UtcNow.Date;
}
```

```text title="Kết quả"
(ngày hiện tại của máy chạy — không kiểm soát được trong test)
```

```csharp title="Singleton LIFETIME: đổi implementation khi test chỉ bằng cách đăng ký khác"
// test:compile
var builder = WebApplication.CreateBuilder(args);

// Production: đăng ký bản thật
builder.Services.AddSingleton<IClockService, RealClockService>();

var app = builder.Build();
app.MapGet("/today", (IClockService clock) => Results.Ok(clock.Today()));
app.Run();

public interface IClockService
{
    DateTime Today();
}

public class RealClockService : IClockService
{
    public DateTime Today() => DateTime.UtcNow.Date;
}

// Trong test (không chạy ở đây, chỉ minh hoạ cách đăng ký khác cho test):
//   services.AddSingleton<IClockService>(new FixedClockService(new DateTime(2026, 7, 5)));
// -> Nghiệp vụ nhận IClockService qua constructor injection, không biết
//    (và không cần biết) đang chạy bản RealClockService hay bản giả FixedClockService.
public class FixedClockService : IClockService
{
    private readonly DateTime _fixedDate;
    public FixedClockService(DateTime fixedDate) => _fixedDate = fixedDate;
    public DateTime Today() => _fixedDate;
}
```

**Điểm mấu chốt:** Với `BillingClock.Instance`, code nghiệp vụ **gọi thẳng** điểm truy cập tĩnh — không có "khe hở" nào để chèn giá trị giả vào khi test, vì không có gì được truyền qua constructor. Với `IClockService` qua DI, code nghiệp vụ chỉ khai báo "tôi cần một `IClockService`" qua constructor — nó không biết (và không quan tâm) ai đang đứng sau interface đó, nên test chỉ cần đăng ký `FixedClockService` thay `RealClockService`, không sửa một dòng nào của code nghiệp vụ.

---

## 3. Adapter pattern

### 3.1 Định nghĩa

**Adapter là gì?** Adapter là một pattern **chuyển đổi interface của một class sang một interface khác mà code gọi nó mong đợi**, giúp hai phía không tương thích về chữ ký (nhưng làm việc tương đương về ý nghĩa) có thể làm việc cùng nhau mà không cần sửa code của bên nào cả.

### 3.2 Ví dụ tối thiểu

```csharp title="Adapter tối thiểu: hai interface không khớp chữ ký"
// test:run
ITemperatureSensor sensor = new LegacySensorAdapter(new LegacySensor());
Console.WriteLine($"{sensor.ReadCelsius():0.#}°C");

// Interface NỘI BỘ mà toàn bộ code mới của ta dùng
public interface ITemperatureSensor
{
    double ReadCelsius();
}

// Thư viện CŨ/NGOÀI — trả độ F, tên phương thức khác, ta KHÔNG sửa được class này
public class LegacySensor
{
    public double GetFahrenheit() => 98.6;
}

// Adapter: bọc LegacySensor, "giả trang" thành ITemperatureSensor
public class LegacySensorAdapter : ITemperatureSensor
{
    private readonly LegacySensor _legacy;
    public LegacySensorAdapter(LegacySensor legacy) => _legacy = legacy;

    public double ReadCelsius() => (_legacy.GetFahrenheit() - 32) / 1.8;
}
```

```text title="Kết quả"
37°C
```

**Điểm mấu chốt:** `LegacySensor` không đổi một chữ nào — nó không biết `ITemperatureSensor` tồn tại. `LegacySensorAdapter` là lớp trung gian duy nhất biết cả hai phía: nó implement interface nội bộ, và bên trong gọi đúng phương thức của thư viện cũ, kèm phép chuyển đổi đơn vị cần thiết (F sang C).

### 3.3 Vấn đề cụ thể Adapter giải quyết

Tình huống thực chiến: bạn có interface nội bộ `IPaymentGateway` đã định nghĩa cho toàn hệ thống, nhưng thư viện thanh toán của bên thứ ba có interface hoàn toàn khác — tên phương thức khác, tham số khác, thậm chí đơn vị tiền khác (cents vs. đồng). Không sửa được thư viện ngoài (đóng gói sẵn, cập nhật qua NuGet). Nếu gọi trực tiếp thư viện ngoài rải khắp codebase, khi đổi nhà cung cấp thanh toán bạn phải sửa **mọi nơi** gọi tới nó.

```csharp title="Vấn đề: gọi trực tiếp thư viện ngoài rải khắp code (KHÔNG dùng Adapter)"
// test:skip minh hoạ vấn đề, không đầy đủ để chạy độc lập
public class CheckoutController
{
    public void Checkout(Order order)
    {
        // Gọi TRỰC TIẾP API của thư viện ngoài — chữ ký, đơn vị tiền do HỌ quyết định
        var extResult = new ExternalPaymentSdk().Charge(
            amountInCents: (int)(order.Total * 100),
            cardToken: order.CardToken);

        if (extResult.StatusCode == 0)   // 0 nghĩa là "thành công" theo docs của SDK ngoài
            Console.WriteLine("Thanh toán OK");
    }
}
```

Vấn đề: `CheckoutController` (và mọi nơi khác cần thanh toán) phải biết `ExternalPaymentSdk` làm việc ra sao — đơn vị `cents`, mã trạng thái `0`/không-`0`. Đổi nhà cung cấp thanh toán = sửa lại **từng nơi gọi**. Dưới đây áp dụng Adapter để sửa: định nghĩa interface nội bộ theo ngôn ngữ nghiệp vụ của ta, rồi bọc thư viện ngoài sau một lớp Adapter duy nhất.

```csharp title="Sửa bằng Adapter: interface nội bộ ổn định, thư viện ngoài bị bọc lại"
// test:run
IPaymentGateway gateway = new ExternalPaymentAdapter(new ExternalPaymentSdk());

var result = gateway.Charge(amount: 199.99m, cardToken: "tok_abc123");
Console.WriteLine(result.Success ? "Thanh toán OK" : "Thanh toán lỗi");

// ---- Interface NỘI BỘ: toàn bộ code nghiệp vụ chỉ biết đến cái này ----
public interface IPaymentGateway
{
    PaymentResult Charge(decimal amount, string cardToken);
}

public record PaymentResult(bool Success, string? ErrorMessage);

// ---- Thư viện NGOÀI: chữ ký khác hẳn, KHÔNG sửa được (giả lập SDK bên thứ ba) ----
public class ExternalPaymentSdk
{
    public ExternalChargeResponse Charge(int amountInCents, string cardToken)
        => new ExternalChargeResponse(StatusCode: 0, Message: "ok");
}
public record ExternalChargeResponse(int StatusCode, string Message);

// ---- Adapter: điểm DUY NHẤT biết cả hai phía ----
public class ExternalPaymentAdapter : IPaymentGateway
{
    private readonly ExternalPaymentSdk _sdk;
    public ExternalPaymentAdapter(ExternalPaymentSdk sdk) => _sdk = sdk;

    public PaymentResult Charge(decimal amount, string cardToken)
    {
        var response = _sdk.Charge(
            amountInCents: (int)(amount * 100),      // đổi đơn vị: đồng -> cents
            cardToken: cardToken);

        return response.StatusCode == 0
            ? new PaymentResult(Success: true, ErrorMessage: null)
            : new PaymentResult(Success: false, ErrorMessage: response.Message);
    }
}
```

```text title="Kết quả"
Thanh toán OK
```

Giờ `CheckoutController` (và mọi nơi khác) chỉ phụ thuộc `IPaymentGateway` — không biết `ExternalPaymentSdk` tồn tại. Đổi nhà cung cấp thanh toán = viết một `ExternalPaymentAdapter` mới, **không sửa** `CheckoutController`.

### 3.4 Lỗi nếu quên bọc — gọi nhầm interface

Nếu code nghiệp vụ vô tình cầm trực tiếp `ExternalPaymentSdk` thay vì `IPaymentGateway`, sẽ không biên dịch được ở những nơi mong đợi interface nội bộ — đây là cách compiler "ép" bạn đi qua Adapter:

```csharp title="Gán thư viện ngoài thẳng vào biến interface nội bộ: lỗi biên dịch (cố ý)"
// test:skip minh hoạ lỗi biên dịch cố ý — CS0029
IPaymentGateway gateway = new ExternalPaymentSdk();   // LỖI CS0029: không chuyển đổi ngầm
// ExternalPaymentSdk KHÔNG implement IPaymentGateway -> phải đi qua ExternalPaymentAdapter

public interface IPaymentGateway { }
public class ExternalPaymentSdk { }
```

### 3.5 Khi nào KHÔNG nên dùng Adapter (over-engineering)

Nếu bạn **chỉ** dùng một thư viện ngoài duy nhất, ở **một** nơi duy nhất trong toàn bộ ứng dụng, và không có kế hoạch/khả năng đổi sang thư viện khác, việc tạo cả một `interface` nội bộ cộng một class Adapter chỉ để bọc một lời gọi API là **thêm một lớp gián tiếp không mang lại giá trị** — gọi trực tiếp SDK ngoài ở chỗ đó là đủ. Adapter đáng giá khi có **ít nhất một trong hai**: (a) interface của thư viện ngoài thật sự không khớp với ngôn ngữ nghiệp vụ nội bộ của bạn (đơn vị khác, chữ ký khác — như ví dụ trên), hoặc (b) bạn cần khả năng **thay thế** thư viện ngoài mà không sửa code gọi (ví dụ để unit-test không gọi API thật, hoặc để dễ đổi nhà cung cấp). Bọc Adapter cho một thư viện bạn chắc chắn không bao giờ đổi và test cũng không cần fake, chỉ tạo thêm một tầng phải đọc/maintain mà không giải quyết vấn đề gì thật.

### 3.6 Object Adapter (C#) vs Class Adapter — vì sao C# chỉ dùng được một kiểu

Sách GoF phân biệt hai cách cài Adapter:

- **Object Adapter** — Adapter **giữ một tham chiếu** tới object cần bọc (composition), rồi gọi qua tham chiếu đó. Đây chính là cách `ExternalPaymentAdapter` ở Mục 3.3 làm (field `_sdk`).
- **Class Adapter** — Adapter **kế thừa** cả interface đích lẫn class cần bọc cùng lúc, dựa vào đa kế thừa (multiple inheritance) của C++.

C# (giống Java) **không hỗ trợ đa kế thừa class** (một class chỉ kế thừa được một class cha, dù implement được nhiều interface) — nên **Class Adapter theo đúng nghĩa GoF không viết được trong C#** nếu class cần bọc không phải là interface. Vì lý do đó, trong C# gần như luôn dùng **Object Adapter** (composition: giữ field tham chiếu tới object cần bọc) — đây không phải một lựa chọn thiết kế, mà là **giới hạn ngôn ngữ** quyết định sẵn.

```csharp title="Class Adapter kiểu C#: kế thừa được TỐI ĐA một class + nhiều interface"
// test:compile Class Adapter chỉ viết được khi đích (ITarget) là interface, không phải class cụ thể
public interface ITarget { void Do(); }
public class LegacyThing { public void OldDo() { } }

// Biên dịch OK — vì ITarget là interface, không tính vào giới hạn "tối đa một class cha".
// Nếu ITarget ở đây là MỘT CLASS CỤ THỂ khác (không phải interface), dòng kế thừa 2 class
// này sẽ báo lỗi CS1721 ("'BadClassAdapter': cannot have multiple base classes") — đó là
// lý do Class Adapter đúng nghĩa GoF (kế thừa CẢ HAI class) không viết được trong C#.
public class BadClassAdapter : LegacyThing, ITarget
{
    public void Do() => OldDo();
}
```

Đây chính là hình thức gần nhất C# có với Class Adapter, và về bản chất **không khác Object Adapter về mặt giữ tham chiếu**: nó chỉ gộp việc kế thừa dữ liệu/hành vi của `LegacyThing` thay vì giữ nó qua field. Cách này ít linh hoạt hơn Object Adapter (không đổi được `LegacyThing` sang một bản khác lúc runtime, vì nó gắn cứng qua kế thừa) nên Object Adapter (composition, như 3.3) vẫn là lựa chọn mặc định nên dùng trong C#.

---

## 4. So sánh Observer, Singleton, Adapter — khi nào chọn cái nào

Ba pattern này giải quyết ba vấn đề **hoàn toàn khác nhau** — bảng dưới đây tổng hợp lại để tránh nhầm "cứ có nhiều class là dùng pattern nào cũng được":

| Pattern | Vấn đề giải quyết | Dấu hiệu NÊN dùng | Dấu hiệu ĐANG over-engineering |
|---|---|---|---|
| **Observer** | Một nguồn sự kiện, nhiều bên độc lập cần biết, không muốn nguồn phải biết tên từng bên | Có ≥ 2 bên độc lập, không biết trước hết, cùng quan tâm một sự kiện; danh sách người quan tâm có thể tăng theo thời gian | Chỉ có đúng một nơi xử lý cố định, thứ tự luôn y hệt, không có kế hoạch thêm subscriber |
| **Singleton (GoF)** | Cần ngôn ngữ **tự chặn cứng** việc tạo instance thứ hai, ngoài phạm vi một DI container | Code không chạy trong DI container (thư viện nhỏ, console app không có `IServiceProvider`) | Đang có DI container sẵn có (ASP.NET Core) — hầu như luôn nên dùng `AddSingleton<T>()` thay vì tự code |
| **Adapter** | Interface bên ngoài không khớp interface nội bộ, không sửa được bên ngoài | Chữ ký/đơn vị dữ liệu khác nhau thật, HOẶC cần khả năng thay thế/fake khi test | Chỉ một nơi gọi, một thư viện, không có kế hoạch đổi, test không cần fake |

**Ghi nhớ chung:** cả ba đều thêm một tầng gián tiếp (indirection). Câu hỏi cần tự trả lời trước khi áp dụng bất kỳ pattern nào trong ba cái này không phải "pattern này có đúng không" (kỹ thuật gần như luôn đúng) mà là "**vấn đề cụ thể nào đang tồn tại** mà cách viết đơn giản hơn không giải quyết được" — nếu không trả lời được câu đó bằng một ví dụ cụ thể, khả năng cao là chưa cần pattern.

---

## Cạm bẫy & thực chiến

1. **Observer + lambda inline khiến `-=` không gỡ được.** Giống cạm bẫy đã học ở delegates-events: `orderService.OrderPlaced += order => {...}` rồi `-= order => {...}` là hai đối tượng khác nhau, không gỡ được. Muốn hủy đăng ký đúng, giữ lại tham chiếu (named method hoặc biến delegate) rồi `-=` đúng tham chiếu đó.

2. **Observer publisher sống lâu, subscriber ngắn hạn = rò rỉ bộ nhớ.** Nếu `OrderService` là singleton còn observer là một object ngắn hạn (ví dụ một form UI), quên `-=` khi observer hết vòng đời khiến nó không được GC — đây chính là cơ chế rò rỉ event đã học chi tiết ở delegates-events, áp dụng nguyên vẹn cho Observer pattern (Observer về bản chất chính là event).

3. **Nhầm Singleton pattern GoF với Singleton lifetime DI (lỗi phổ biến nhất trong chương này).** Đăng ký `AddSingleton<Foo>()` không có nghĩa `Foo` phải viết theo Singleton pattern GoF (constructor `private`). Ngược lại, nếu `Foo` viết theo Singleton pattern GoF (constructor `private`, `Foo.Instance` tĩnh), DI container **không gọi được** constructor để tạo instance — container cần constructor public để tự invoke. Chọn một trong hai, không trộn.

4. **Singleton pattern GoF làm global mutable state khó test.** Vì `AppConfig.Instance` là điểm truy cập toàn cục, một test sửa `Instance.Setting` sẽ ảnh hưởng mọi test khác chạy trong cùng process — kết quả test phụ thuộc **thứ tự chạy**, một trong những nguồn lỗi test "flaky" (không ổn định) kinh điển nhất. Đây là lý do chính khiến DI + `AddSingleton<T>()` (tráo implementation được khi test) được ưu tiên hơn trong ứng dụng hiện đại.

5. **Adapter "rò rỉ" kiểu dữ liệu của thư viện ngoài ra interface nội bộ.** Nếu `Charge()` trong `IPaymentGateway` trả thẳng `ExternalChargeResponse` (kiểu của SDK ngoài) thay vì `PaymentResult` (kiểu nội bộ), bạn chưa thật sự cách ly — đổi SDK ngoài vẫn buộc sửa nơi gọi vì kiểu trả về đổi theo. Adapter đúng nghĩa phải trả về **kiểu của phía nội bộ**, như `PaymentResult` ở ví dụ 3.3.

6. **Tạo Adapter cho một thư viện chỉ dùng một lần, không có ý định đổi (over-engineering).** Xem chi tiết Mục 3.5 — thêm interface + Adapter cho một lời gọi API duy nhất, không có kế hoạch thay thế và không cần fake khi test, là phức tạp hoá không cần thiết.

---

## Bài tập

### Bài 1 (giàn giáo) — Observer cho giỏ hàng

Viết class `ShoppingCart` phát `event Action<decimal>? TotalChanged` mỗi khi `AddItem(decimal price)` được gọi (giá trị phát ra là tổng tiền mới). Đăng ký hai observer: một in ra tổng tiền, một in cảnh báo nếu tổng vượt `500_000`.

??? success "Lời giải bài 1"
    ```csharp title="Giải bài 1"
    // test:run
    var cart = new ShoppingCart();
    cart.TotalChanged += total => Console.WriteLine($"Tổng: {total:N0}đ");
    cart.TotalChanged += total =>
    {
        if (total > 500_000) Console.WriteLine("CẢNH BÁO: vượt 500,000đ");
    };

    cart.AddItem(200_000);
    cart.AddItem(350_000);

    class ShoppingCart
    {
        private decimal _total;
        public event Action<decimal>? TotalChanged;

        public void AddItem(decimal price)
        {
            _total += price;
            TotalChanged?.Invoke(_total);
        }
    }
    ```
    ```text title="Kết quả"
    Tổng: 200,000đ
    Tổng: 550,000đ
    CẢNH BÁO: vượt 500,000đ
    ```
    `ShoppingCart` không biết có bao nhiêu observer hay chúng làm gì — mỗi observer tự quyết định phản ứng với giá trị phát ra.

### Bài 2 (thiết kế) — Adapter cho dịch vụ gửi SMS ngoài

Bạn có interface nội bộ `INotifier { void Notify(string to, string message); }`. Thư viện SMS ngoài có class `ThirdPartySmsClient` với phương thức `SendText(string phoneNumber, string body)` trả về `bool` (true = thành công). Viết `SmsAdapter` implement `INotifier`, in ra `"Gửi thất bại"` nếu `SendText` trả `false`.

??? success "Lời giải bài 2"
    ```csharp title="Giải bài 2"
    // test:run
    INotifier notifier = new SmsAdapter(new ThirdPartySmsClient());
    notifier.Notify("0900000000", "Đơn hàng của bạn đã được xác nhận");

    public interface INotifier
    {
        void Notify(string to, string message);
    }

    public class ThirdPartySmsClient
    {
        public bool SendText(string phoneNumber, string body)
        {
            Console.WriteLine($"[SMS ngoài] gửi tới {phoneNumber}: {body}");
            return true;
        }
    }

    public class SmsAdapter : INotifier
    {
        private readonly ThirdPartySmsClient _client;
        public SmsAdapter(ThirdPartySmsClient client) => _client = client;

        public void Notify(string to, string message)
        {
            var ok = _client.SendText(to, message);
            if (!ok) Console.WriteLine("Gửi thất bại");
        }
    }
    ```
    ```text title="Kết quả"
    [SMS ngoài] gửi tới 0900000000: Đơn hàng của bạn đã được xác nhận
    ```
    Nếu ngày mai đổi sang nhà cung cấp SMS khác, chỉ cần viết một `INotifier` mới — không sửa code gọi `Notify`.

### Bài 3 (thử thách) — phân biệt hai loại Singleton trong cùng một chương trình

Viết một Singleton pattern GoF thật (`RequestCounter` — constructor `private`, đếm số lần gọi toàn cục qua `Instance.Increment()`), và một class `ClockService` bình thường (constructor public) được đăng ký `AddSingleton<ClockService>()` trong một `WebApplicationBuilder`. Giải thích trong comment vì sao `RequestCounter` KHÔNG đăng ký được vào DI container theo đúng cách Singleton pattern của nó.

??? success "Lời giải bài 3"
    ```csharp title="Giải bài 3 — phần chạy được: Singleton pattern GoF"
    // test:run
    RequestCounter.Instance.Increment();
    RequestCounter.Instance.Increment();
    RequestCounter.Instance.Increment();
    Console.WriteLine($"Tổng request: {RequestCounter.Instance.Count}");   // 3

    public sealed class RequestCounter
    {
        private static readonly RequestCounter _instance = new();
        private RequestCounter() { }             // private -> không new() được từ ngoài
        public static RequestCounter Instance => _instance;

        public int Count { get; private set; }
        public void Increment() => Count++;
    }
    ```
    ```text title="Kết quả"
    Tổng request: 3
    ```
    ```csharp title="Giải bài 3 — phần DI: Singleton LIFETIME, class khác hẳn về thiết kế"
    // test:compile
    var builder = WebApplication.CreateBuilder(args);

    // ClockService là class BÌNH THƯỜNG, constructor public -> DI gọi được trực tiếp.
    builder.Services.AddSingleton<ClockService>();

    var app = builder.Build();
    app.MapGet("/now", (ClockService clock) => Results.Ok(clock.Now));
    app.Run();

    public class ClockService
    {
        public ClockService() { }   // public -> khác RequestCounter ở trên
        public DateTime Now => DateTime.UtcNow;
    }

    // Vì sao RequestCounter (Singleton GoF) KHÔNG đăng ký "đúng cách" được vào DI:
    // AddSingleton<RequestCounter>() sẽ FAIL lúc runtime vì DI container cần gọi
    // "new RequestCounter()" để tạo instance, nhưng constructor của nó là private ->
    // container không có quyền truy cập, ném MissingMethodException khi resolve.
    // Hai cơ chế "chỉ một instance" (tự code vs. container quản lý) không trộn được.
    ```
    ```text title="Kết quả build"
    (test:compile — chỉ kiểm tra build thành công, không có output runtime)
    ```

---

## Tự kiểm tra

Trả lời rồi mới mở đáp án.

1. **Trong Observer pattern, vì sao subject (publisher) không cần biết cụ thể observer là kiểu gì?**

??? note "Đáp án 1"
    Vì subject chỉ giữ một `event`/delegate với chữ ký cố định (ví dụ `Action<Order>`) — nó thông báo qua chữ ký đó, không quan tâm ai đã đăng ký hay có bao nhiêu người đăng ký. Bất kỳ observer nào khớp chữ ký đều `+=` được mà không cần sửa subject.

2. **`event`/delegate của C# liên quan gì tới Observer pattern của GoF?**

??? note "Đáp án 2"
    `event`/delegate chính là cách C# cài đặt sẵn ngữ nghĩa Observer trong ngôn ngữ — Gang of Four mô tả Observer bằng interface `Subject`/`Observer` tự viết vì Java/C++ thời đó chưa có delegate hạng nhất; C# đã có `+=`/`?.Invoke()` làm sẵn đúng việc đó.

3. **Singleton pattern (GoF) và Singleton lifetime (DI container) khác nhau ở điểm nào về constructor?**

??? note "Đáp án 3"
    Singleton pattern GoF **bắt buộc** constructor `private` để tự chặn việc `new` thêm instance. Singleton lifetime của DI container yêu cầu constructor **public** (hoặc ít nhất container truy cập được) vì chính container phải gọi constructor đó để tạo instance — hai yêu cầu đối lập nhau, không trộn được trên cùng một class.

4. **Vì sao Singleton pattern GoF khó test hơn Singleton lifetime của DI?**

??? note "Đáp án 4"
    Vì Singleton GoF là global mutable state truy cập qua điểm tĩnh (`X.Instance`) — không có cách "tráo" nó bằng một fake/mock khi test, và một test sửa state sẽ ảnh hưởng các test khác chạy sau (kết quả phụ thuộc thứ tự chạy). Singleton lifetime của DI cho phép đăng ký một implementation khác (`AddSingleton<IFoo, FakeFoo>()`) riêng cho môi trường test, không đụng tới container thật.

5. **Adapter pattern giải quyết vấn đề gì khi tích hợp thư viện thanh toán bên thứ ba?**

??? note "Đáp án 5"
    Thư viện ngoài có interface (tên phương thức, tham số, đơn vị dữ liệu) khác với `IPaymentGateway` nội bộ, và ta không sửa được thư viện ngoài. Adapter tạo một class bọc lại, implement `IPaymentGateway`, bên trong gọi đúng API của thư viện ngoài và chuyển đổi dữ liệu — nhờ đó code nghiệp vụ chỉ phụ thuộc `IPaymentGateway`, đổi nhà cung cấp thanh toán chỉ cần đổi Adapter.

6. **Vì sao Adapter nên trả về kiểu dữ liệu nội bộ (`PaymentResult`) thay vì kiểu của thư viện ngoài (`ExternalChargeResponse`)?**

??? note "Đáp án 6"
    Nếu Adapter trả thẳng kiểu của thư viện ngoài, code gọi nó vẫn phải biết cấu trúc dữ liệu của thư viện ngoài — chưa thật sự cách ly. Đổi sang thư viện khác (với kiểu response khác) vẫn buộc sửa nơi gọi. Trả về kiểu nội bộ mới đảm bảo code gọi hoàn toàn không biết thư viện ngoài tồn tại.

7. **Cho một ứng dụng chỉ có một chỗ gọi API thời tiết ngoài, không có kế hoạch đổi nhà cung cấp, không cần fake khi test — có nên tạo `IWeatherProvider` + `WeatherAdapter` không? Vì sao?**

??? note "Đáp án 7"
    Không cần — đây là over-engineering. Adapter chỉ đáng giá khi có nhu cầu thay thế/cách ly thật (đổi provider, hoặc cần fake khi test). Nếu không có nhu cầu đó, gọi trực tiếp API ngoài ở chỗ duy nhất đó là đủ, thêm interface + Adapter chỉ tạo thêm một tầng phải đọc mà không giải quyết vấn đề gì.

8. **Nếu một `ShoppingCart` singleton (dùng `AddSingleton`) đăng ký observer từ một object ngắn hạn mà quên `-=` khi object đó hết vòng đời, điều gì xảy ra?**

??? note "Đáp án 8"
    Rò rỉ bộ nhớ: `ShoppingCart` (sống suốt vòng đời ứng dụng) giữ delegate trỏ tới object ngắn hạn đó, khiến GC không thu gom được object dù nơi khác đã "vứt" nó — đúng cơ chế rò rỉ event đã học ở delegates-events, áp dụng cho Observer.

---

??? abstract "DEEP DIVE — biến thể và chi phí thật của ba pattern"
    **Observer và Reactive Extensions.** Khi nhu cầu vượt quá "thông báo đơn giản" — cần kết hợp nhiều luồng sự kiện, throttle, retry khi lỗi — `event` thô trở nên cồng kềnh. `IObservable<T>`/`IObserver<T>` và Rx.NET cung cấp một bộ operator (giống LINQ nhưng cho luồng sự kiện theo thời gian) để xử lý các nhu cầu đó mà không tự viết state machine tay. Chi phí: thêm một dependency và một cách suy nghĩ mới (lập trình phản ứng) — chỉ đáng dùng khi độ phức tạp của luồng sự kiện thật sự cần.

    **Singleton GoF và đa luồng.** Ví dụ 2.2 dùng `static readonly` field khởi tạo ngay — CLR đảm bảo static field khởi tạo **thread-safe, đúng một lần** trước khi bất kỳ luồng nào truy cập type lần đầu (thông qua type initializer được đồng bộ hoá bởi runtime), nên đây là cách viết Singleton GoF an toàn luồng đơn giản nhất, không cần tự viết `lock`. Các cách viết Singleton "lazy" phức tạp hơn (double-checked locking bằng tay) là di sản từ thời trước khi `static readonly` field-initializer được đảm bảo thread-safe rõ ràng trong spec — hiện tại không cần thiết cho phần lớn trường hợp.

    **Singleton lifetime và captive dependency (nhắc lại có liên hệ).** Chương dependency-injection (P3) đã dạy chi tiết: một Singleton (lifetime) vô tình giữ tham chiếu tới một Scoped service sẽ "giam" Scoped đó sống mãi (captive dependency). Điều này không liên quan gì tới Singleton pattern GoF — nó là hệ quả của cách DI container resolve dependency graph, thuần túy về lifetime, không phải về việc class có tự code Singleton hay không.

    **Adapter hai chiều: Adapter vs. Facade vs. Wrapper.** Adapter chuyển **một interface cụ thể sang một interface cụ thể khác đã tồn tại** (thường vì code gọi đã viết sẵn, mong đợi đúng interface đó). Facade (một pattern khác, không phải trọng tâm chương này) đơn giản hoá **nhiều** interface phức tạp thành **một** interface gọn hơn, không nhất thiết phải khớp một interface đã có từ trước. Sự khác biệt: Adapter luôn có một "hợp đồng đích" (target interface) được định nghĩa từ trước mà nó phải khớp chính xác; Facade tự do thiết kế interface mới miễn là gọn hơn. Nhầm hai pattern này là lý do nhiều review pattern gọi "adapter" cho thứ thực ra là "facade" bọc nhiều service thành một.

    **Chi phí gián tiếp chung của cả ba pattern.** Cả Observer, Singleton GoF, và Adapter đều thêm **một tầng gián tiếp** (indirection) giữa nơi gọi và nơi thực thi thật. Indirection luôn có giá: người đọc code sau này phải nhảy qua nhiều file hơn để hiểu "điều gì thực sự xảy ra khi X được gọi". Đây là lý do mọi mục "khi nào KHÔNG nên dùng" trong chương này lặp lại cùng một nguyên tắc senior: **chỉ trả giá indirection khi đã có nhu cầu thật (nhiều subscriber độc lập, cần thay thế implementation, cần cách ly thư viện ngoài) — không trả giá đó "phòng khi cần trong tương lai" nếu tương lai đó chưa chắc xảy ra.**

---

**Tiếp theo →** [P6 · Clean Architecture](clean-architecture.md)
