<!-- FIXTURE input-XẤU cố ý để gate_selftest chứng minh macro_safety.py bắt được.
     Mô phỏng đúng lỗi thật đã xảy ra: C# escape ngoặc nhọn trong string interpolation
     bị plugin macros hiểu nhầm thành biến Jinja. KHÔNG nằm trong docs/ nên không lên site. -->
# Trang xấu ví dụ

```csharp title="C#"
// test:run
Console.WriteLine($"Money {{ Amount = {amount} }}");
```
