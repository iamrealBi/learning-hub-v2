---
tier: fast
status: core
owner: core-team
verified_on: "2026-07-01"
dotnet_version: "10.0"
bloom: "Apply"
requires: []
est_minutes_fast: 30
---

# P0 · Thiết lập: Zero → bài tập "xanh" đầu tiên

> **Mục tiêu:** trong **<30 phút**, máy bạn chạy được C# và bạn thấy một test **PASS** đầu tiên. Đây là vòng lặp phản hồi mà mọi bài sau dựa vào.

!!! tip "Cách nhanh nhất: Dev Container (không cần cài gì ngoài Docker + VS Code)"
    Repo có sẵn `.devcontainer` với .NET {{ dotnet.current }} SDK. Mở trong VS Code → "Reopen in Container" → xong. Bỏ qua bước cài SDK thủ công bên dưới.

## 1. Cài .NET SDK {{ dotnet.current }}

=== "Windows"
    ```powershell title="PowerShell"
    winget install Microsoft.DotNet.SDK.10
    ```
=== "macOS"
    ```bash title="Terminal"
    brew install --cask dotnet-sdk
    ```
=== "Linux"
    ```bash title="Terminal"
    # xem hướng dẫn phát hành theo distro; kiểm chứng phiên bản:
    dotnet --version   # phải in ra {{ dotnet.current }}.x
    ```

## 2. Chạy "Hello, green" trong 60 giây

```bash title="terminal"
dotnet new console -o hello && cd hello
dotnet run
```

Bạn sẽ thấy `Hello, World!`. Đó là vòng lặp <10 giây bạn sẽ lặp lại hàng trăm lần.

## 3. Test đầu tiên PASS (đây là "xanh")

```csharp title="Program.cs"
// test:run
int Add(int a, int b) => a + b;

// "test" thủ công đơn giản để thấy khái niệm PASS/FAIL:
Console.WriteLine(Add(2, 3) == 5 ? "PASS ✅" : "FAIL ❌");
```

```bash title="Terminal"
dotnet run    # → PASS ✅
```

!!! success "Xong P0"
    Bạn vừa hoàn tất vòng phản hồi cốt lõi. Từ giờ mỗi bài kết thúc bằng code **chạy được** và câu hỏi **có đáp án**.

**Tiếp theo →** [P1 · Nền tảng](../p1-csharp/nen-tang.md)
