---
tier: core
status: core
owner: core-team
verified_on: "2026-07-05"
dotnet_version: "10.0"
bloom: áp dụng
requires: [p6-clean-architecture]
est_minutes_fast: 32
---

# CQRS: tách mô hình đọc và ghi

!!! info "bạn đang ở đây · p6 → node `p6-cqrs` · kiến trúc/pattern"
    **cần trước:** clean architecture — vì CQRS là cách tổ chức lại luồng nghiệp vụ *bên trong* lớp application, không thay lớp đó.
    **mở khoá:** nhận diện đúng lúc nào một tính năng cần tách hẳn đường đọc và đường ghi, và lúc nào việc tách đó chỉ là làm phức tạp thêm một CRUD đơn giản.

> **Mục tiêu (đo được):** sau chương này bạn **giải thích** được vấn đề cụ thể mà CQRS giải quyết (model đọc và model ghi bị kéo cùng một hình dạng); **viết** được một Command handler và một Query handler tách biệt cho cùng một nghiệp vụ; **phân biệt** được CQRS (khái niệm kiến trúc) với MediatR (một thư viện phổ biến để cài đặt CQRS trong .NET); và **quyết định** được khi nào áp dụng CQRS là hợp lý, khi nào là over-engineering cho một CRUD đơn giản.

---

## 0. Đoán nhanh trước khi đọc

Trước khi xem đáp án, hãy tự trả lời (desirable difficulty — đoán sai vẫn giúp nhớ lâu hơn):

1. CQRS là viết tắt của cụm từ gì?
2. Một endpoint `GET /orders/{id}` nên đi qua "Command" hay "Query" trong CQRS?
3. Nếu ứng dụng của bạn chỉ có 4 API: thêm, xem, sửa, xoá một `Product` — có cần CQRS không?
4. MediatR có phải là CQRS, hay chỉ là một cách để *cài đặt* CQRS?
5. Trong CQRS, một Command có được phép trả về dữ liệu chi tiết (ví dụ toàn bộ object vừa tạo) không?

??? note "Đáp án"
    1. **Command Query Responsibility Segregation** — tách trách nhiệm giữa lệnh (thay đổi trạng thái) và truy vấn (đọc dữ liệu).
    2. **Query** — nó chỉ đọc dữ liệu, không thay đổi trạng thái hệ thống.
    3. **Không** — CRUD đơn giản có model đọc và model ghi giống nhau gần như hoàn toàn; tách CQRS ở đây là over-engineering, làm code phức tạp hơn không cần thiết.
    4. **Chỉ là cách cài đặt** — MediatR là một thư viện (thông qua interface `IRequest`/`IRequestHandler`) giúp tổ chức code theo phong cách CQRS; bạn hoàn toàn có thể làm CQRS mà không cần MediatR.
    5. **Không nên** — nguyên tắc CQRS là Command chỉ thay đổi trạng thái, không trả dữ liệu chi tiết (nhiều nhất trả về id hoặc trạng thái thành công/thất bại); trả dữ liệu chi tiết là việc của Query.

---

## 1. Vấn đề cụ thể: một model dùng chung bị kéo cẳng hai phía

**Bối cảnh:** giả sử bạn có một ứng dụng quản lý đơn hàng (`Order`). Ban đầu team dùng **một** model duy nhất — `OrderDto` — cho cả việc ghi (tạo đơn) và đọc (xem danh sách đơn, xem báo cáo doanh thu).

```csharp title="C#"
// test:compile chỉ minh hoạ hình dạng model dùng chung — không có Program.cs endpoint ở đây
public class OrderDto
{
    public int Id { get; set; }
    public int CustomerId { get; set; }
    public List<OrderLineDto> Lines { get; set; } = new();
    public decimal TotalAmount { get; set; }

    // Các trường dưới đây CHỈ có ý nghĩa khi ĐỌC (báo cáo), vô nghĩa khi TẠO đơn mới:
    public string CustomerName { get; set; } = "";      // phải JOIN sang bảng Customer
    public string CustomerTier { get; set; } = "";       // phải tính từ lịch sử mua hàng
    public decimal DiscountAppliedPercent { get; set; }  // phải tính lại từ rule khuyến mãi
}

public class OrderLineDto
{
    public int ProductId { get; set; }
    public string ProductName { get; set; } = "";  // chỉ cần khi đọc, JOIN sang Product
    public int Quantity { get; set; }
    public decimal UnitPrice { get; set; }
}
```

**Vấn đề xuất hiện dần khi hệ thống lớn lên:**

- **Khi ghi (tạo đơn mới):** client gọi `POST /orders` chỉ có `CustomerId` và danh sách `ProductId` + `Quantity` — nhưng vì dùng chung `OrderDto`, endpoint buộc phải nhận cả `CustomerName`, `CustomerTier`, `ProductName` dù những trường này **vô nghĩa lúc tạo** (client gửi lên cũng bị bỏ qua, hoặc tệ hơn — bị hiểu nhầm là dữ liệu hợp lệ). Validate cho "ghi" phải cẩn thận loại trừ các trường "chỉ để đọc".
- **Khi đọc (xem báo cáo doanh thu theo khách hàng):** báo cáo cần JOIN `Order` với `Customer`, `Product`, tính `DiscountAppliedPercent` từ rule khuyến mãi phức tạp, có thể còn cần GROUP BY theo tháng. Nhưng vì code đọc phải trả về đúng hình dạng `OrderDto` (để tái dùng model ghi), bạn không thể tối ưu câu query đọc theo đúng nhu cầu báo cáo (ví dụ dùng `SELECT` chỉ những cột cần, hoặc denormalize cho nhanh) — mọi thay đổi ở model ghi (thêm field bắt buộc khi tạo đơn) đều **rung chuyển** cả phần đọc, dù báo cáo không liên quan gì đến việc tạo đơn.
- **Hệ quả rõ nhất:** đội đọc (làm dashboard/báo cáo) và đội ghi (làm nghiệp vụ tạo đơn) buộc phải phối hợp mỗi khi đổi field — trong khi hai nhu cầu này **về bản chất không liên quan đến nhau**: một bên cần validate nghiệp vụ chặt (ghi), một bên cần tối ưu tốc độ đọc và định dạng linh hoạt cho hiển thị (đọc).

**Điều gì xảy ra khi dùng sai (cố nhồi thêm field vào model chung):** một dev thêm field `DiscountAppliedPercent` vào `OrderDto` để phục vụ báo cáo, quên rằng model này cũng dùng để nhận request tạo đơn — validator tạo đơn giờ phải tự loại trừ field đó, nếu quên sẽ có lỗi kiểu:

```text title="Lỗi thực tế khi model đọc/ghi lẫn lộn"
System.Text.Json.JsonException: The JSON value could not be converted to
System.Decimal. Path: $.DiscountAppliedPercent | LineNumber: 0 | BytePositionInLine: 142
```

Client gọi `POST /orders` gửi thiếu hoặc gửi sai kiểu cho một field mà nó **không hề cần biết** (vì field đó chỉ có ý nghĩa lúc đọc) — đây chính là dấu hiệu model đang bị dùng cho hai mục đích khác nhau.

---

## 2. CQRS là gì

**Định nghĩa (một câu, giả định bạn chưa biết khái niệm này):** CQRS (Command Query Responsibility Segregation) là nguyên tắc **tách riêng đường xử lý cho hành động thay đổi trạng thái** (gọi là **Command**) và **đường xử lý cho hành động đọc dữ liệu** (gọi là **Query**) thành hai model và hai luồng xử lý độc lập, thay vì dùng chung một model như ở mục 1.

Hai quy tắc cốt lõi:

- **Command:** thay đổi trạng thái hệ thống (tạo, sửa, xoá). **Không trả về dữ liệu chi tiết** — nhiều nhất trả `id` mới tạo, hoặc `true/false`/exception khi thất bại.
- **Query:** chỉ đọc dữ liệu, **không được gây tác dụng phụ** (không ghi, không sửa gì). Được tự do trả về bất kỳ hình dạng dữ liệu nào tiện cho việc đọc (denormalize, JOIN, tính toán sẵn).

**Ví dụ tối thiểu, độc lập** — áp dụng đúng vấn đề ở mục 1: tách `OrderDto` thành một Command (chỉ để tạo đơn) và một Query (chỉ để đọc báo cáo), mỗi bên có model riêng, không còn dùng chung:

```csharp title="C#"
// test:run
using System;
using System.Collections.Generic;

// ---------- COMMAND: chỉ chứa dữ liệu CẦN để tạo đơn, không có field "chỉ để đọc" ----------
public record CreateOrderCommand(int CustomerId, List<OrderLineInput> Lines);
public record OrderLineInput(int ProductId, int Quantity);

// Command handler: THAY ĐỔI trạng thái (tạo đơn), CHỈ trả về id — không trả dữ liệu chi tiết.
public class CreateOrderHandler
{
    private readonly List<StoredOrder> _store; // giả lập database trong bộ nhớ

    public CreateOrderHandler(List<StoredOrder> store) => _store = store;

    public int Handle(CreateOrderCommand command)
    {
        if (command.Lines.Count == 0)
            throw new InvalidOperationException("Đơn hàng phải có ít nhất một dòng sản phẩm.");

        var newId = _store.Count + 1;
        _store.Add(new StoredOrder(newId, command.CustomerId, command.Lines));
        return newId; // chỉ trả id — đúng nguyên tắc Command không trả dữ liệu chi tiết
    }
}

// ---------- QUERY: model đọc RIÊNG, tự do có field denormalize để hiển thị ----------
public record OrderReportView(int OrderId, string CustomerName, int LineCount, decimal EstimatedTotal);

// Query handler: CHỈ đọc, KHÔNG thay đổi trạng thái. Tự do JOIN/tính toán cho tiện hiển thị.
public class GetOrderReportHandler
{
    private readonly List<StoredOrder> _store;
    private readonly Dictionary<int, string> _customerNames;

    public GetOrderReportHandler(List<StoredOrder> store, Dictionary<int, string> customerNames)
    {
        _store = store;
        _customerNames = customerNames;
    }

    public OrderReportView Handle(int orderId)
    {
        var order = _store.Find(o => o.Id == orderId)
            ?? throw new KeyNotFoundException($"Không tìm thấy đơn hàng {orderId}");

        var customerName = _customerNames.GetValueOrDefault(order.CustomerId, "Khách chưa rõ tên");
        var estimatedTotal = order.Lines.Count * 100_000m; // giả lập tính giá — thực tế sẽ JOIN bảng Product

        return new OrderReportView(order.Id, customerName, order.Lines.Count, estimatedTotal);
    }
}

public record StoredOrder(int Id, int CustomerId, List<OrderLineInput> Lines);

public static class Program
{
    public static void Main()
    {
        var store = new List<StoredOrder>();
        var customerNames = new Dictionary<int, string> { [7] = "Nguyễn Văn A" };

        // 1) Gọi Command để TẠO đơn — chỉ gửi dữ liệu cần cho việc ghi
        var createHandler = new CreateOrderHandler(store);
        var newOrderId = createHandler.Handle(new CreateOrderCommand(7, new List<OrderLineInput>
        {
            new OrderLineInput(ProductId: 1, Quantity: 2),
            new OrderLineInput(ProductId: 3, Quantity: 1),
        }));
        Console.WriteLine($"Đã tạo đơn, id = {newOrderId}");

        // 2) Gọi Query để ĐỌC báo cáo — model hoàn toàn khác, có field denormalize (CustomerName)
        var reportHandler = new GetOrderReportHandler(store, customerNames);
        var report = reportHandler.Handle(newOrderId);
        Console.WriteLine(
            $"Báo cáo: đơn #{report.OrderId} của {report.CustomerName}, " +
            $"{report.LineCount} dòng, ước tính {report.EstimatedTotal:N0}đ");
    }
}
```

```text title="Kết quả"
Đã tạo đơn, id = 1
Báo cáo: đơn #1 của Nguyễn Văn A, 2 dòng, ước tính 200,000đ
```

Đọc lại đúng vấn đề ở mục 1: `CreateOrderCommand` **không có** `CustomerName` hay `EstimatedTotal` — nó chỉ chứa đúng thứ cần để ghi. `OrderReportView` **không dùng lại** hình dạng của Command — nó tự do có `CustomerName` (denormalize), `EstimatedTotal` (tính sẵn), những field chỉ có ý nghĩa lúc đọc. Hai handler này **độc lập hoàn toàn**: đổi field trong Command không ảnh hưởng gì đến Query, và ngược lại.

**Điều gì xảy ra khi dùng sai — vi phạm nguyên tắc Command không trả dữ liệu:**

```csharp title="C#"
// test:compile minh hoạ SAI nguyên tắc — Command trả nguyên object chi tiết
// (BadStoredOrder/BadCreateOrderCommand khai báo lại tối giản ở đây để đoạn minh hoạ tự đủ,
// tương đương StoredOrder/CreateOrderCommand đã dùng ở ví dụ mục 2.)
public record BadCreateOrderCommand(int CustomerId, List<OrderLineInput> Lines);
public record OrderLineInput(int ProductId, int Quantity);
public record BadStoredOrder(int Id, int CustomerId, List<OrderLineInput> Lines);

public class BadCreateOrderHandler
{
    public BadStoredOrder Handle(BadCreateOrderCommand command)
    {
        var order = new BadStoredOrder(1, command.CustomerId, command.Lines);
        // SAI: Command trả về toàn bộ entity — caller giờ phụ thuộc vào HÌNH DẠNG GHI
        // để đọc dữ liệu, kéo lại đúng vấn đề CQRS muốn giải quyết ở mục 1.
        return order;
    }
}
```

Khi Command trả nguyên `StoredOrder`, phía gọi (ví dụ UI) sẽ có xu hướng **đọc luôn dữ liệu từ kết quả Command** thay vì gọi Query riêng — dần dần, model ghi lại bị kéo giãn để "vừa ghi vừa phục vụ đọc luôn", quay lại chính vấn đề ban đầu.

---

## 3. CQRS không phải là kiến trúc phân tách database

**Định nghĩa cần đính chính ngay:** CQRS ở mức **cơ bản** (áp dụng trong hầu hết ứng dụng .NET thông thường) chỉ là tách **model và luồng xử lý trong code** — Command và Query vẫn có thể đọc/ghi trên **cùng một database, cùng một bộ bảng**. Việc tách hẳn thành hai database riêng (read database được đồng bộ từ write database qua event) là một **biến thể nâng cao** (CQRS + Event Sourcing), không phải điều kiện bắt buộc để gọi là CQRS.

!!! danger "Hiểu lầm phổ biến — đính chính"
    **Sai:** "Áp dụng CQRS nghĩa là phải có hai database riêng, một cho đọc một cho ghi."
    **Đúng:** CQRS cơ bản chỉ tách **model C#** (Command/Query object) và **luồng xử lý** (handler riêng), vẫn dùng chung một database — ví dụ ở mục 2, `store` là một danh sách trong bộ nhớ dùng chung cho cả Command và Query. Tách hẳn hai database là lựa chọn kiến trúc **riêng, nâng cao hơn**, chỉ cần khi tải đọc và tải ghi lệch nhau quá lớn (ví dụ đọc gấp hàng nghìn lần ghi) — tuyệt đại đa số ứng dụng nội bộ **không cần** tới mức đó.

---

## 4. CẢNH BÁO OVER-ENGINEERING: CQRS cho CRUD đơn giản là thừa

Đây là điểm quan trọng nhất của chương này, vì CQRS là một trong những pattern **bị lạm dụng nhiều nhất** khi mới học xong.

**Ví dụ cụ thể — khi KHÔNG nên dùng CQRS:** một API quản lý `Category` (danh mục sản phẩm) chỉ có 4 hành động cơ bản: thêm, xem theo id, sửa tên, xoá. Model đọc và model ghi **giống nhau gần như 100%**.

```csharp title="C#"
// test:compile minh hoạ CRUD đơn giản — model đọc và ghi giống nhau, KHÔNG cần tách CQRS
public record CategoryDto(int Id, string Name);

// Nếu áp dụng CQRS ở đây, bạn sẽ phải viết THÊM:
//   CreateCategoryCommand, CreateCategoryHandler,
//   UpdateCategoryCommand, UpdateCategoryHandler,
//   DeleteCategoryCommand, DeleteCategoryHandler,
//   GetCategoryQuery, GetCategoryHandler, GetCategoryListQuery, GetCategoryListHandler
// — tức là 8 class mới, để thay cho một CategoryService có 4 method, xử lý ĐÚNG MỘT model DTO.
// Không có lợi ích thực chất nào vì model đọc và model ghi ở đây LÀ MỘT.
```

**Dấu hiệu nhận biết CQRS đang thừa (checklist tự hỏi trước khi áp dụng):**

- Model đọc và model ghi của tính năng này có khác nhau đáng kể không, hay chỉ là cùng một DTO?
- Có logic nghiệp vụ phức tạp ở phía ghi (validate nhiều bước, tính toán, side-effect) khác biệt hẳn với phía đọc không?
- Phía đọc có cần denormalize/JOIN nhiều bảng/tính toán tổng hợp mà phía ghi hoàn toàn không quan tâm không?

Nếu câu trả lời cho cả ba câu trên là **"không"** hoặc **"chỉ hơi khác"** — dùng một service/method thống nhất là đủ, không cần tách Command/Query. Tách ra trong trường hợp này chỉ tạo thêm nhiều file, nhiều lớp gián tiếp (indirection) mà không giải quyết vấn đề gì có thật — đây chính là **over-engineering**: áp dụng pattern vì "pattern này hay", không phải vì bài toán thật sự cần nó.

**Ngược lại — khi CQRS đáng giá:** đúng như ví dụ đơn hàng ở mục 1–2, khi model đọc (báo cáo, dashboard, JOIN nhiều bảng, tính toán tổng hợp) và model ghi (validate nghiệp vụ tạo/sửa đơn) **thật sự khác nhau đáng kể**, và hai đội/hai luồng thay đổi độc lập với nhau — tách CQRS giúp mỗi bên tối ưu đúng theo nhu cầu của nó mà không kéo bên còn lại theo.

---

## 5. CQRS khác MediatR: khái niệm vs công cụ cài đặt

**Định nghĩa:** CQRS là một **nguyên tắc kiến trúc** (mục 2) — bạn có thể áp dụng nó chỉ bằng class C# thuần, như ví dụ ở mục 2, không cần thư viện nào cả. **MediatR** là một **thư viện .NET cụ thể**, phổ biến trong cộng đồng, cung cấp interface `IRequest<TResponse>` và `IRequestHandler<TRequest, TResponse>` để tổ chức Command/Query theo một khuôn thống nhất, kèm cơ chế gửi request qua một `IMediator` trung gian (mediator pattern) thay vì gọi trực tiếp handler.

**Ví dụ minh hoạ hình dạng API của MediatR** (chỉ để thấy sự khác biệt — không tự chạy vì cần cài package ngoài):

```csharp title="C#"
// test:skip cần package MediatR (NuGet) ngoài BCL — chỉ minh hoạ hình dạng API,
// KHÔNG phải phần bắt buộc của CQRS (mục 2 đã cài CQRS thuần, không cần MediatR).
using MediatR;

public record CreateOrderCommand(int CustomerId, List<OrderLineInput> Lines) : IRequest<int>;

public class CreateOrderHandler : IRequestHandler<CreateOrderCommand, int>
{
    public Task<int> Handle(CreateOrderCommand request, CancellationToken cancellationToken)
    {
        // Cùng logic như CreateOrderHandler.Handle ở mục 2 — chỉ khác là MediatR
        // gọi Handle() qua interface chuẩn, và caller gọi qua _mediator.Send(command)
        // thay vì gọi trực tiếp createHandler.Handle(command).
        return Task.FromResult(1);
    }
}
```

**So sánh CQRS (khái niệm) vs MediatR (thư viện) — chỉ đưa ra SAU khi đã hiểu riêng từng cái ở mục 2 và ở trên:**

| Khía cạnh | CQRS | MediatR |
|-----------|------|---------|
| Là gì | Nguyên tắc kiến trúc: tách Command/Query | Một thư viện NuGet cụ thể |
| Bắt buộc phải dùng cùng nhau? | Không — CQRS dùng được với class thuần (mục 2) | Không — MediatR dùng được cho code không theo CQRS |
| Cái gì cung cấp | Cách tư duy tách trách nhiệm đọc/ghi | Interface `IRequest`/`IRequestHandler` + cơ chế gửi qua `IMediator` |
| Lợi ích thêm khi dùng chung | — | Tự động tìm handler đúng (không cần DI thủ công từng handler), dễ thêm pipeline behavior (logging, validation) qua middleware của MediatR |

**Khi nào KHÔNG cần MediatR dù vẫn áp dụng CQRS:** nếu ứng dụng nhỏ, số lượng Command/Query ít, gọi trực tiếp handler qua Dependency Injection (như ví dụ mục 2, đăng ký `CreateOrderHandler` và `GetOrderReportHandler` vào DI container, inject trực tiếp vào endpoint) là đủ — không cần thêm một lớp gián tiếp (`IMediator.Send(...)`) chỉ để "theo đúng chuẩn cộng đồng". Thêm MediatR chỉ thật sự đáng khi số lượng Command/Query lớn (vài chục trở lên) và bạn cần pipeline behavior dùng chung (validate, logging) áp cho tất cả handler mà không phải lặp code ở từng handler.

---

## 6. Validate khác nhau giữa Command và Query — vì sao tách ra lại giúp validate rõ hơn

**Vấn đề cụ thể khi validate vẫn dùng chung model (nối lại đúng vấn đề mục 1):** nếu bạn còn dùng `OrderDto` chung, validator cho việc tạo đơn phải viết kiểu loại trừ — "bắt buộc `CustomerId`, bắt buộc `Lines` không rỗng, nhưng **bỏ qua** `CustomerName`, `DiscountAppliedPercent` dù chúng có mặt trong model". Rule "bỏ qua trường nào" này **không nằm ở đâu rõ ràng cả** — dev mới vào dự án rất dễ quên, dẫn đến validate sai hoặc thiếu.

**Định nghĩa:** khi Command và Query đã có model riêng (mục 2), **validate cho Command chỉ cần khai báo đúng trên chính model Command** — không còn trường nào "phải nhớ bỏ qua", vì Command đơn giản là không hề chứa những trường chỉ dùng để đọc.

**Ví dụ tối thiểu, độc lập** — validate trực tiếp trên `CreateOrderCommand`, không cần loại trừ gì:

```csharp title="C#"
// test:run
using System;
using System.Collections.Generic;
using System.Linq;

public record CreateOrderCommand(int CustomerId, List<OrderLineInput> Lines);
public record OrderLineInput(int ProductId, int Quantity);

public static class CreateOrderValidator
{
    // Validate CHỈ nhìn vào field của Command — không có field "chỉ để đọc" nào lẫn vào,
    // nên không cần dòng loại trừ nào như khi dùng chung OrderDto ở mục 1.
    public static List<string> Validate(CreateOrderCommand command)
    {
        var errors = new List<string>();

        if (command.CustomerId <= 0)
            errors.Add("CustomerId phải lớn hơn 0.");

        if (command.Lines.Count == 0)
            errors.Add("Đơn hàng phải có ít nhất một dòng sản phẩm.");

        if (command.Lines.Any(l => l.Quantity <= 0))
            errors.Add("Số lượng mỗi dòng sản phẩm phải lớn hơn 0.");

        return errors;
    }
}

public static class Program
{
    public static void Main()
    {
        var invalidCommand = new CreateOrderCommand(CustomerId: 0, Lines: new List<OrderLineInput>());
        var errors = CreateOrderValidator.Validate(invalidCommand);

        Console.WriteLine($"Số lỗi tìm thấy: {errors.Count}");
        foreach (var e in errors)
            Console.WriteLine($"- {e}");
    }
}
```

```text title="Kết quả"
Số lỗi tìm thấy: 2
- CustomerId phải lớn hơn 0.
- Đơn hàng phải có ít nhất một dòng sản phẩm.
```

Vì `CreateOrderCommand` không có `CustomerName`/`DiscountAppliedPercent`, validator **không cần một dòng nào** để "bỏ qua" các trường đó — nguy cơ quên loại trừ (đúng lỗi thực tế ở mục 1) biến mất hoàn toàn, không phải vì bạn viết validator cẩn thận hơn, mà vì **model đã không còn chứa trường thừa**.

**Điều gì xảy ra khi dùng sai — validate Query như validate Command:** một lỗi tư duy khác là áp rule validate "bắt buộc phải có" lên model Query, ví dụ ép `OrderReportView.CustomerName` không được rỗng. Nhưng Query chỉ đọc dữ liệu đã có sẵn — nếu một khách hàng bị xoá (nhưng đơn hàng cũ vẫn còn), `CustomerName` hợp lệ là **rỗng hoặc "Khách chưa rõ tên"**, không phải lỗi cần chặn. Validate "bắt buộc" chỉ có ý nghĩa ở đầu vào của Command (dữ liệu người dùng gửi lên để ghi), không áp dụng cho Query (dữ liệu đọc ra để hiển thị, có thể thiếu một cách hợp lệ).

---

## 7. Test Command handler và Query handler độc lập

**Vấn đề cụ thể khi test một model dùng chung:** nếu còn dùng `OrderDto` chung, một test cho "tạo đơn thành công" phải tự dựng cả những field chỉ có ý nghĩa lúc đọc (`CustomerName`, `DiscountAppliedPercent`) dù test này **không quan tâm** tới chúng — test dễ trông rối, và khi những field đọc-only đổi kiểu dữ liệu, test tạo đơn (không liên quan) cũng phải sửa lại cho compile được.

**Định nghĩa:** vì Command handler và Query handler là hai class độc lập (mục 2), bạn test được **từng cái riêng biệt**, mỗi test chỉ cần dựng đúng dữ liệu mà handler đó cần — không phải "giả vờ" có đủ field của cả hai phía.

**Ví dụ tối thiểu, độc lập** — hai test riêng, không phụ thuộc lẫn nhau, dùng `Console.WriteLine` + so sánh thủ công để không cần thêm package test ngoài:

```csharp title="C#"
// test:run
using System;
using System.Collections.Generic;

public record CreateOrderCommand(int CustomerId, List<OrderLineInput> Lines);
public record OrderLineInput(int ProductId, int Quantity);
public record StoredOrder(int Id, int CustomerId, List<OrderLineInput> Lines);
public record OrderReportView(int OrderId, string CustomerName, int LineCount, decimal EstimatedTotal);

public class CreateOrderHandler
{
    private readonly List<StoredOrder> _store;
    public CreateOrderHandler(List<StoredOrder> store) => _store = store;

    public int Handle(CreateOrderCommand command)
    {
        if (command.Lines.Count == 0)
            throw new InvalidOperationException("Đơn hàng phải có ít nhất một dòng sản phẩm.");
        var newId = _store.Count + 1;
        _store.Add(new StoredOrder(newId, command.CustomerId, command.Lines));
        return newId;
    }
}

public class GetOrderReportHandler
{
    private readonly List<StoredOrder> _store;
    private readonly Dictionary<int, string> _customerNames;

    public GetOrderReportHandler(List<StoredOrder> store, Dictionary<int, string> customerNames)
    {
        _store = store;
        _customerNames = customerNames;
    }

    public OrderReportView Handle(int orderId)
    {
        var order = _store.Find(o => o.Id == orderId)
            ?? throw new KeyNotFoundException($"Không tìm thấy đơn hàng {orderId}");
        var name = _customerNames.GetValueOrDefault(order.CustomerId, "Khách chưa rõ tên");
        return new OrderReportView(order.Id, name, order.Lines.Count, order.Lines.Count * 100_000m);
    }
}

public static class Program
{
    private static int _passed = 0, _failed = 0;

    private static void Assert(bool condition, string testName)
    {
        if (condition) { _passed++; Console.WriteLine($"PASS: {testName}"); }
        else { _failed++; Console.WriteLine($"FAIL: {testName}"); }
    }

    public static void Main()
    {
        // Test 1 — CHỈ test Command handler, không cần biết gì về OrderReportView.
        var storeForCommand = new List<StoredOrder>();
        var createHandler = new CreateOrderHandler(storeForCommand);
        var newId = createHandler.Handle(new CreateOrderCommand(1, new List<OrderLineInput>
        {
            new OrderLineInput(1, 2),
        }));
        Assert(newId == 1, "Tạo đơn đầu tiên phải có id = 1");
        Assert(storeForCommand.Count == 1, "Store phải có đúng 1 đơn sau khi tạo");

        // Test 2 — CHỈ test Query handler, dựng sẵn dữ liệu có sẵn (không gọi lại Command handler).
        var storeForQuery = new List<StoredOrder> { new StoredOrder(1, 7, new List<OrderLineInput> { new OrderLineInput(1, 2) }) };
        var names = new Dictionary<int, string> { [7] = "Nguyễn Văn A" };
        var reportHandler = new GetOrderReportHandler(storeForQuery, names);
        var report = reportHandler.Handle(1);
        Assert(report.CustomerName == "Nguyễn Văn A", "Báo cáo phải denormalize đúng tên khách hàng");
        Assert(report.LineCount == 1, "Báo cáo phải đếm đúng số dòng sản phẩm");

        Console.WriteLine($"\nTổng kết: {_passed} PASS, {_failed} FAIL");
    }
}
```

```text title="Kết quả"
PASS: Tạo đơn đầu tiên phải có id = 1
PASS: Store phải có đúng 1 đơn sau khi tạo
PASS: Báo cáo phải denormalize đúng tên khách hàng
PASS: Báo cáo phải đếm đúng số dòng sản phẩm

Tổng kết: 4 PASS, 0 FAIL
```

Quan sát mấu chốt: **Test 1 không hề cần `Dictionary<int, string> customerNames`** (chỉ Query handler cần), và **Test 2 không hề gọi `CreateOrderHandler`** — nó tự dựng sẵn `StoredOrder` trong danh sách để test đúng một hành vi của Query. Tách CQRS giúp mỗi test **nhỏ, rõ ý định, không phải dựng dữ liệu thừa** cho phần logic mà test đó không quan tâm.

**Điều gì xảy ra khi dùng sai — một test "to" kiểm cả tạo và đọc cùng lúc:** nếu bạn viết một test duy nhất gọi Command rồi ngay lập tức assert luôn trên kết quả trả về của Command (ví dụ assert `result.CustomerName == "..."`), bạn đang giả định Command trả dữ liệu chi tiết — đúng lỗi đã cảnh báo ở mục 2. Khi handler Command sau này đổi (chỉ trả `int` thay vì object, đúng nguyên tắc), test này vỡ dù logic tạo đơn không có gì sai — test đang kiểm nhầm trách nhiệm.

---

## 8. CQRS và tầng data access — Command/Query có cần Repository riêng không?

**Nối lại với chương trước (`p6-clean-architecture`):** chương clean architecture đã nhắc rằng với EF Core, `DbSet<T>` **đã là** một Unit-of-Work + Repository-like abstraction sẵn có — bọc thêm một lớp Repository riêng thường là **thừa**, chỉ đáng khi cần gom logic query phức tạp dùng lại nhiều nơi. Câu hỏi tự nhiên khi học CQRS: "Command và Query có cần *hai* Repository khác nhau không?"

**Trả lời ngắn:** **không cần**, và đây là một hiểu lầm khác dễ mắc phải sau khi học CQRS. CQRS tách **model và handler ở tầng application**, không bắt buộc tách tầng data access. Cả Command handler và Query handler ở ví dụ mục 2 hoàn toàn có thể dùng **cùng một** `DbContext`/`DbSet<Order>` — khác biệt là cách chúng **dùng** `DbSet` đó:

```csharp title="C#"
// test:skip cần package Microsoft.EntityFrameworkCore (NuGet) ngoài Web SDK trần — chỉ minh hoạ hình dạng API
using Microsoft.EntityFrameworkCore;

public class AppDbContext : DbContext
{
    public AppDbContext(DbContextOptions<AppDbContext> options) : base(options) { }
    public DbSet<OrderEntity> Orders => Set<OrderEntity>();
}

public class OrderEntity
{
    public int Id { get; set; }
    public int CustomerId { get; set; }
}

// COMMAND handler: dùng DbSet để GHI — Add + SaveChanges, không JOIN gì thêm.
public class CreateOrderEfHandler
{
    private readonly AppDbContext _db;
    public CreateOrderEfHandler(AppDbContext db) => _db = db;

    public async Task<int> Handle(CreateOrderCommand command, CancellationToken ct)
    {
        var entity = new OrderEntity { CustomerId = command.CustomerId };
        _db.Orders.Add(entity);
        await _db.SaveChangesAsync(ct);
        return entity.Id;
    }
}

// QUERY handler: dùng CHÍNH DbSet đó, nhưng gọi .AsNoTracking() + Select để tối ưu ĐỌC,
// không quan tâm change-tracking (vốn chỉ cần cho ghi).
public class GetOrderReportEfHandler
{
    private readonly AppDbContext _db;
    public GetOrderReportEfHandler(AppDbContext db) => _db = db;

    public Task<OrderReportView?> Handle(int orderId, CancellationToken ct) =>
        _db.Orders
            .AsNoTracking() // không cần EF theo dõi thay đổi vì đây chỉ để đọc — nhanh hơn
            .Where(o => o.Id == orderId)
            .Select(o => new OrderReportView(o.Id, "(demo)", 0, 0m))
            .FirstOrDefaultAsync(ct);
}
```

Điểm mấu chốt: cả hai handler tiêm (inject) **cùng một `AppDbContext`** — không có "CommandDbContext" và "QueryDbContext" riêng nào cả ở mức cơ bản. Sự khác biệt CQRS mang lại nằm ở **cách gọi API của `DbSet`** (Command: `Add` + `SaveChangesAsync`, có change-tracking; Query: `AsNoTracking()` + `Select` chiếu thẳng ra model đọc, bỏ qua change-tracking để nhanh hơn), không nằm ở việc phải tạo thêm lớp Repository bọc quanh `DbSet`.

**Khi nào một Repository riêng cho Query mới đáng làm:** nếu logic đọc phức tạp (nhiều điều kiện lọc, nhiều cách JOIN) bị **lặp lại ở nhiều Query handler khác nhau**, gom chúng vào một class `OrderReadRepository` có thể hợp lý — nhưng đây là quyết định **độc lập** với việc có dùng CQRS hay không (đúng nguyên tắc "Repository chỉ đáng khi cần gom logic query phức tạp dùng lại nhiều nơi" đã học ở chương trước), không phải hệ quả bắt buộc của CQRS.

---

## 9. Cạm bẫy & thực chiến

- **Tách CQRS cho CRUD đơn giản (đã nhấn ở mục 4):** đây là lỗi phổ biến nhất — thấy CQRS "trông chuyên nghiệp" nên áp dụng cho mọi entity, kể cả `Category`, `Tag`, những bảng chỉ có 4 field và không có logic phức tạp. Kết quả: gấp đôi, gấp ba số file so với cần thiết, review code chậm hơn, không ai được lợi.
- **Command trả về dữ liệu chi tiết (vi phạm nguyên tắc ở mục 2):** nhiều người viết Command trả nguyên `OrderDto` "cho tiện, để UI không phải gọi thêm Query" — làm mất hoàn toàn lợi ích của việc tách, vì UI lại phụ thuộc vào hình dạng ghi để hiển thị, đúng vấn đề ban đầu ở mục 1.
- **Query có tác dụng phụ ẩn:** một Query "chỉ để xem" nhưng trong handler lại âm thầm ghi log vào bảng `AuditLog`, tăng bộ đếm `ViewCount`... Nếu tác dụng phụ này **thay đổi trạng thái nghiệp vụ quan trọng** (không phải log kỹ thuật thuần), nó phải là một Command riêng — nếu không, code sẽ có tác dụng phụ ẩn mà người đọc Query không lường trước, gây khó test (test Query mà lại phải kiểm tra cả AuditLog).
- **Tưởng CQRS bắt buộc phải tách database (đã đính chính ở mục 3):** dẫn tới việc đội kỹ thuật trì hoãn áp dụng CQRS vì nghĩ phải đầu tư hạ tầng đồng bộ dữ liệu hai chiều — trong khi CQRS cơ bản chỉ cần tách model/class trong code, vẫn một database.
- **Đặt tên Command/Query không rõ ý định:** đặt tên `OrderService.Process(OrderDto dto)` cho cả tạo và sửa, không rõ đây là Command hay Query — nên đặt tên theo động từ mệnh lệnh cho Command (`CreateOrderCommand`, `CancelOrderCommand`) và theo câu hỏi/danh từ cho Query (`GetOrderReportQuery`, `OrderReportView`), để chỉ nhìn tên là biết ngay đây có thay đổi trạng thái hay không.

---

## 10. Bài tập

**Bài 1 — Nhận diện over-engineering.** Một API quản lý `Tag` (thẻ gắn bài viết) có 3 hành động: thêm tag mới (chỉ có `Name`), xem danh sách tag, xoá tag. Không có logic nghiệp vụ phức tạp nào. Đồng nghiệp đề xuất tách CQRS với `CreateTagCommand`, `DeleteTagCommand`, `GetTagListQuery`, mỗi cái một handler riêng. Bạn đồng ý hay phản đối? Nêu lý do dựa trên checklist ở mục 4.

??? success "Lời giải + vì sao"
    **Phản đối** (hoặc ít nhất đề nghị cân nhắc lại). Áp checklist mục 4:
    - Model đọc và ghi có khác nhau đáng kể? Không — `Tag` chỉ có `Id` và `Name`, đọc và ghi dùng chung một hình dạng.
    - Có logic nghiệp vụ phức tạp ở ghi? Không được nêu — có vẻ chỉ là thêm/xoá đơn giản.
    - Đọc có cần denormalize/JOIN phức tạp? Không — chỉ là danh sách tag.

    Cả ba câu trả lời đều "không" → đây là dấu hiệu rõ của over-engineering. Một `TagService` với 3 method (`Create`, `Delete`, `GetAll`) dùng chung một `TagDto` là đủ, không cần 3 Command/Query class riêng.

**Bài 2 — Viết Command và Query tách biệt.** Cho nghiệp vụ: hệ thống quản lý thư viện, có hành động (a) mượn sách (`BorrowBook`, cần `BookId`, `MemberId`, thay đổi trạng thái sách thành "đã mượn") và (b) xem danh sách sách đang được mượn kèm tên người mượn và số ngày còn lại (cần JOIN với bảng `Member`, tính từ ngày mượn). Viết signature (chỉ record + tên method, không cần cài đặt đầy đủ) cho một Command và một Query tương ứng, đúng nguyên tắc mục 2 (Command không trả dữ liệu chi tiết, Query không có tác dụng phụ).

??? success "Lời giải + vì sao"
    ```csharp title="C#"
    // test:compile minh hoạ signature — đúng nguyên tắc Command/Query tách biệt
    // COMMAND: thay đổi trạng thái, chỉ trả về thành công/thất bại (ở đây: void, ném exception nếu lỗi)
    public record BorrowBookCommand(int BookId, int MemberId);

    public class BorrowBookHandler
    {
        public void Handle(BorrowBookCommand command)
        {
            // 1. Kiểm tra sách còn trống không lỗi nghiệp vụ (ném exception nếu đã có người mượn)
            // 2. Đổi trạng thái Book.Status = "Borrowed", ghi BorrowedByMemberId, BorrowedDate
            // KHÔNG trả về BookDto chi tiết — chỉ trả void hoặc throw nếu thất bại.
        }
    }

    // QUERY: chỉ đọc, tự do JOIN + tính toán, KHÔNG đổi trạng thái gì
    public record BorrowedBookView(int BookId, string Title, string MemberName, int DaysRemaining);

    public class GetBorrowedBooksHandler
    {
        public List<BorrowedBookView> Handle()
        {
            // JOIN Book + Member, tính DaysRemaining = DueDate - hôm nay.
            // Không ghi gì vào database ở đây — đúng nguyên tắc Query không tác dụng phụ.
            return new List<BorrowedBookView>();
        }
    }
    ```
    **Vì sao đúng cấu trúc CQRS:** `BorrowBookCommand`/`BorrowBookHandler` chỉ chứa đúng dữ liệu cần để thay đổi trạng thái (`BookId`, `MemberId`), không trả object sách chi tiết. `BorrowedBookView`/`GetBorrowedBooksHandler` có field hoàn toàn khác (`MemberName` denormalize, `DaysRemaining` tính toán) — những field này **vô nghĩa** nếu nhồi vào `BorrowBookCommand`, đúng minh chứng cho lý do CQRS đáng dùng ở đây: đọc cần JOIN + tính toán phức tạp, ghi cần validate nghiệp vụ (sách còn trống hay không) — hai nhu cầu thật sự khác nhau, không giống bài `Tag` ở Bài 1.

**Bài 3 — Repository riêng hay dùng chung `DbSet`?** Team bạn đang dùng CQRS cho nghiệp vụ đơn hàng (như ví dụ mục 2). Một thành viên mới đề xuất: "Đã dùng CQRS thì nên tạo `IOrderCommandRepository` và `IOrderQueryRepository` riêng, mỗi Command/Query handler chỉ nói chuyện qua Repository của nó, không đụng trực tiếp `DbContext`." Dựa trên mục 8, đề xuất này có bắt buộc không? Khi nào nó thật sự đáng làm?

??? success "Lời giải + vì sao"
    **Không bắt buộc.** Như đã nêu ở mục 8, CQRS chỉ đòi hỏi tách **model và handler ở tầng application** — cả Command handler và Query handler có thể tiêm trực tiếp cùng một `DbContext`/`DbSet<T>`, chỉ khác cách gọi API (Command dùng `Add`/`SaveChangesAsync` có change-tracking; Query dùng `AsNoTracking()` + `Select` để tối ưu đọc). Thêm hai Repository riêng (`IOrderCommandRepository`, `IOrderQueryRepository`) chỉ đáng làm khi logic đọc/ghi **phức tạp và bị lặp lại ở nhiều handler khác nhau** — ví dụ nhiều Query handler khác nhau đều cần cùng một cách JOIN 4 bảng để tính tồn kho, lúc đó gom logic đó vào một `OrderReadRepository` giúp tránh lặp code. Nếu team chỉ có vài Command/Query đơn giản như ví dụ mục 2, thêm hai interface Repository chỉ để "đúng chuẩn CQRS" là **thêm một tầng gián tiếp không cần thiết** — đúng dạng over-engineering đã cảnh báo ở mục 4, lần này áp lên tầng data access thay vì tầng application.

---

## 11. Ba mức độ áp dụng CQRS trong thực tế — chọn đúng mức, không nhảy thẳng lên mức cao nhất

Sau khi đã hiểu đầy đủ khái niệm (mục 2), cách validate (mục 6), cách test (mục 7), và tầng data access (mục 8), giờ mới đến lúc tổng hợp: CQRS trong thực tế không phải "có hoặc không" mà có **nhiều mức độ**, và phần lớn lỗi thực chiến là **nhảy thẳng lên mức cao nhất** khi mức thấp đã đủ.

**Mức 1 — CQRS-lite (class thuần, không thư viện, một database):** đúng như toàn bộ ví dụ ở mục 2, 6, 7, 8 của chương này. Command và Query là hai class C# riêng, gọi trực tiếp qua Dependency Injection, cùng một `DbContext`. Đây là mức phù hợp cho **phần lớn ứng dụng .NET nội bộ, quy mô vừa** — đủ để giải quyết đúng vấn đề ở mục 1 (model đọc/ghi không còn bị kéo cẳng), mà không phải trả thêm chi phí hạ tầng nào.

**Mức 2 — CQRS + MediatR (thêm lớp gián tiếp qua mediator):** như mục 5 đã minh hoạ, thêm `IRequest`/`IRequestHandler` và gọi qua `IMediator.Send(...)`. Đáng chuyển sang mức này khi số lượng Command/Query đã nhiều (vài chục trở lên) và bạn cần **pipeline behavior chung** — ví dụ tự động validate mọi Command bằng FluentValidation trước khi vào handler, hoặc tự động log mọi Command/Query, mà không muốn lặp code gọi validate ở đầu mỗi handler.

```csharp title="C#"
// test:skip minh hoạ pipeline behavior của MediatR — cần package MediatR ngoài BCL
public class ValidationBehavior<TRequest, TResponse> : IPipelineBehavior<TRequest, TResponse>
    where TRequest : IRequest<TResponse>
{
    public async Task<TResponse> Handle(
        TRequest request, RequestHandlerDelegate<TResponse> next, CancellationToken ct)
    {
        // Chạy validate CHUNG cho MỌI Command/Query đi qua mediator, một lần duy nhất —
        // đây chính là lợi ích MediatR mang thêm so với CQRS-lite ở mục 5.
        // (Nếu chỉ có vài handler, viết validate riêng từng handler như mục 6 là đủ, không cần lớp này.)
        return await next();
    }
}
```

**Mức 3 — CQRS + read model riêng/Event Sourcing (hai luồng lưu trữ):** như đã nêu ở phần DEEP DIVE cuối chương, tách hẳn write-side (chuẩn hoá, tối ưu ghi) và read-side (denormalize, tối ưu đọc), đồng bộ qua event, có thể có độ trễ (eventual consistency). Đây là mức **hiếm khi cần** trong ứng dụng .NET nội bộ thông thường — chỉ đáng khi tải đọc và tải ghi lệch nhau ở quy mô rất lớn (chênh nhau hàng nghìn lần), hoặc có yêu cầu audit/replay lịch sử thay đổi rất chặt (ngành tài chính, bảo hiểm).

**So sánh ba mức (chỉ đưa ra SAU khi đã hiểu riêng từng mức ở trên):**

| Mức | Độ phức tạp thêm | Khi nào đáng dùng | Rủi ro nếu dùng sai lúc |
|-----|-------------------|--------------------|--------------------------|
| 1. CQRS-lite | Thấp — chỉ thêm class Command/Query/Handler | Ứng dụng vừa, model đọc/ghi khác biệt rõ (mục 4) | Không nên bỏ qua khi model thật sự khác nhau — quay lại vấn đề mục 1 |
| 2. CQRS + MediatR | Trung bình — thêm thư viện, pipeline behavior | Nhiều Command/Query (vài chục+), cần validate/log chung | Thêm phụ thuộc thư viện, một lớp gián tiếp không cần nếu ít handler |
| 3. CQRS + read model riêng/Event Sourcing | Cao — hai luồng lưu trữ, đồng bộ qua event, eventual consistency | Tải đọc/ghi lệch nhau rất lớn, cần audit/replay lịch sử chặt | Chi phí vận hành rất cao (đồng bộ, dữ liệu tạm không nhất quán) nếu áp dụng khi chưa cần |

**Nguyên tắc chọn mức, tóm gọn:** luôn bắt đầu từ **Mức 1**. Chỉ leo lên Mức 2 khi có triệu chứng cụ thể (nhiều handler lặp code validate/log). Chỉ leo lên Mức 3 khi có triệu chứng cụ thể về tải hoặc yêu cầu audit — không leo thang "phòng khi sau này cần", vì chi phí duy trì Mức 3 phải trả **ngay từ hôm nay**, còn cái lợi "phòng khi sau này" có thể **không bao giờ xảy ra**.

---

## Tự kiểm tra

1. CQRS là viết tắt của gì, và hai chữ "C" và "Q" tương ứng với loại hành động nào?
2. Nêu lại vấn đề cụ thể ở mục 1: vì sao dùng chung một model cho đọc và ghi lại gây khó khăn khi hệ thống lớn lên?
3. Một Command có nên trả về toàn bộ object chi tiết vừa tạo không? Vì sao?
4. CQRS có bắt buộc phải tách thành hai database riêng không?
5. Nêu một ví dụ cụ thể (không lấy lại ví dụ trong bài) mà CQRS là over-engineering.
6. MediatR khác CQRS ở điểm nào — cái nào là khái niệm, cái nào là công cụ?
7. Nêu checklist 3 câu hỏi ở mục 4 để quyết định có nên áp dụng CQRS hay không.
8. Command handler và Query handler có bắt buộc phải dùng hai Repository/DbContext khác nhau không?
9. Vì sao nên bắt đầu từ "CQRS-lite" (mục 11) thay vì áp dụng ngay CQRS + Event Sourcing?

??? note "Đáp án"
    1. **Command Query Responsibility Segregation.** "C" (Command) là hành động thay đổi trạng thái; "Q" (Query) là hành động chỉ đọc dữ liệu.
    2. Vì model đọc (cần denormalize, JOIN, tính toán cho báo cáo/hiển thị) và model ghi (chỉ cần dữ liệu tối thiểu để validate và lưu) có nhu cầu khác nhau; dùng chung một model khiến mỗi lần đổi field cho một bên đều ảnh hưởng bên còn lại, dù hai nhu cầu không liên quan.
    3. **Không** — nguyên tắc CQRS là Command chỉ trả về thông tin tối thiểu (id, thành công/thất bại); trả dữ liệu chi tiết là việc của Query, trả nguyên object trong Command làm mất lợi ích tách biệt.
    4. **Không** — CQRS cơ bản chỉ tách model/luồng xử lý trong code, vẫn dùng chung một database; tách hai database riêng là biến thể nâng cao (kèm event sourcing), chỉ cần khi tải đọc/ghi lệch nhau rất lớn.
    5. Ví dụ hợp lệ: một API quản lý `Country` (chỉ có `Code`, `Name`), chỉ có thêm/sửa/xoá/xem cơ bản, model đọc và ghi giống nhau hoàn toàn — tách CQRS ở đây tạo thêm nhiều class không giải quyết vấn đề gì có thật.
    6. CQRS là **nguyên tắc kiến trúc** (tách Command/Query); MediatR là **một thư viện NuGet cụ thể** giúp cài đặt nguyên tắc đó qua `IRequest`/`IRequestHandler`, không bắt buộc phải dùng MediatR mới gọi là áp dụng CQRS.
    7. (1) Model đọc và ghi có khác nhau đáng kể không? (2) Có logic nghiệp vụ phức tạp riêng ở phía ghi không? (3) Phía đọc có cần denormalize/JOIN/tính toán tổng hợp mà phía ghi không quan tâm không? Nếu cả ba đều "không" hoặc "chỉ hơi khác" — không cần CQRS.
    8. **Không bắt buộc** — cả hai có thể tiêm cùng một `DbContext`/`DbSet<T>`, chỉ khác cách gọi API (Command: `Add`/`SaveChangesAsync`; Query: `AsNoTracking()` + `Select`). Repository riêng chỉ đáng thêm khi logic đọc/ghi phức tạp bị lặp lại ở nhiều handler.
    9. Vì chi phí vận hành của Event Sourcing (đồng bộ hai luồng lưu trữ, dữ liệu tạm không nhất quán) phải trả **ngay từ đầu**, trong khi lý do cần nó (tải đọc/ghi lệch nhau rất lớn, yêu cầu audit chặt) thường **chưa xảy ra** ở giai đoạn đầu — bắt đầu từ mức đơn giản nhất đủ dùng, chỉ leo thang khi có triệu chứng cụ thể, tránh trả giá phức tạp cho một nhu cầu chưa có thật.

---

??? abstract "DEEP DIVE — CQRS trong một ASP.NET Core Minimal API thật, và ranh giới với Event Sourcing"
    **Ghép CQRS thuần (không MediatR) vào Minimal API** — nối lại toàn bộ ví dụ mục 2 thành endpoint thật, dùng DI để đăng ký handler:

    ```csharp title="Program.cs"
    // test:compile Web SDK trần — minh hoạ đăng ký DI + endpoint cho Command/Query tách biệt
    using Microsoft.AspNetCore.Builder;
    using Microsoft.Extensions.DependencyInjection;

    var builder = WebApplication.CreateBuilder(args);

    // Đăng ký "database" giả lập và hai handler riêng biệt — mỗi handler một trách nhiệm.
    builder.Services.AddSingleton(new List<StoredOrder>());
    builder.Services.AddSingleton(new Dictionary<int, string> { [7] = "Nguyễn Văn A" });
    builder.Services.AddScoped<CreateOrderHandler>();
    builder.Services.AddScoped<GetOrderReportHandler>();

    var app = builder.Build();

    // Endpoint GHI: gọi Command handler, chỉ trả id — đúng nguyên tắc Command không trả chi tiết.
    app.MapPost("/orders", (CreateOrderCommand command, CreateOrderHandler handler) =>
    {
        var id = handler.Handle(command);
        return Results.Created($"/orders/{id}", new { id });
    });

    // Endpoint ĐỌC: gọi Query handler riêng, trả model đọc hoàn toàn khác (denormalize).
    app.MapGet("/orders/{id:int}/report", (int id, GetOrderReportHandler handler) =>
    {
        var report = handler.Handle(id);
        return Results.Ok(report);
    });

    app.Run();

    public record CreateOrderCommand(int CustomerId, List<OrderLineInput> Lines);
    public record OrderLineInput(int ProductId, int Quantity);
    public record StoredOrder(int Id, int CustomerId, List<OrderLineInput> Lines);
    public record OrderReportView(int OrderId, string CustomerName, int LineCount, decimal EstimatedTotal);

    public class CreateOrderHandler
    {
        private readonly List<StoredOrder> _store;
        public CreateOrderHandler(List<StoredOrder> store) => _store = store;

        public int Handle(CreateOrderCommand command)
        {
            var newId = _store.Count + 1;
            _store.Add(new StoredOrder(newId, command.CustomerId, command.Lines));
            return newId;
        }
    }

    public class GetOrderReportHandler
    {
        private readonly List<StoredOrder> _store;
        private readonly Dictionary<int, string> _customerNames;

        public GetOrderReportHandler(List<StoredOrder> store, Dictionary<int, string> customerNames)
        {
            _store = store;
            _customerNames = customerNames;
        }

        public OrderReportView Handle(int orderId)
        {
            var order = _store.Find(o => o.Id == orderId)!;
            var name = _customerNames.GetValueOrDefault(order.CustomerId, "Khách chưa rõ tên");
            return new OrderReportView(order.Id, name, order.Lines.Count, order.Lines.Count * 100_000m);
        }
    }
    ```

    Quan sát: **cả hai endpoint dùng chung một `List<StoredOrder>` (một database duy nhất)** — đúng đính chính ở mục 3, CQRS ở mức này không cần hai database. Điểm khác biệt duy nhất là **hai handler riêng, hai model riêng** cho hai endpoint.

    **Ranh giới với CQRS + Event Sourcing (chỉ nêu để biết, không đi sâu — đây đã là kiến trúc nâng cao, vượt phạm vi "core"):** trong hệ thống tải cực lớn (ví dụ hệ thống đặt vé có hàng triệu lượt đọc mỗi giây so với vài nghìn lượt ghi), người ta có thể tách hẳn Command đi vào một write-database chuẩn hoá (normalized, tối ưu ghi đúng/nhanh), rồi phát sinh **event** (`OrderCreatedEvent`) để một tiến trình riêng cập nhật một read-database denormalize hoàn toàn khác (tối ưu cho tốc độ đọc, có thể trễ vài trăm ms so với ghi — gọi là "eventual consistency"). Đây là lý do CQRS thường bị nhắc cùng Event Sourcing trong tài liệu, nhưng như đã nhấn ở mục 3 và mục 4: **tuyệt đại đa số ứng dụng .NET nội bộ không cần tới mức này** — chỉ cần tách model/handler trong code (như ví dụ Minimal API trên) là đã giải quyết đúng vấn đề gốc ở mục 1, mà không phải trả giá về độ phức tạp vận hành (đồng bộ hai database, xử lý dữ liệu tạm không nhất quán) của Event Sourcing.

Tiếp theo -> vertical slice: tổ chức code theo tính năng thay vì theo lớp
