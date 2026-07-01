---
hide:
  - navigation
---

# Learning Hub v2 — Fullstack .NET & AI

Một **trục học duy nhất** (không phải nhiều track chồng chéo), mỗi trang được **CI kiểm chứng**: build được, code C# compile + chạy thật, câu hỏi có đáp án, không lỗi thời, không bịa. Hiện hành: **.NET {{ dotnet.current }} / C# {{ csharp.version }}**, PostgreSQL {{ postgres.current }}.

!!! warning "Cam kết trung thực về thời gian học"
    Không ai đi từ zero đến *master* fullstack .NET + AI trong 2 ngày. Cái sản phẩm này **đảm bảo được**:

    - **Fast Path 2 ngày** → *làm được việc thật*: hiểu lõi + ship một API chạy được. Xem [Kế hoạch 2 ngày](FAST-PATH-2-NGAY.md).
    - **Lộ trình Mastery (6–8 tuần)** → *chắc & sâu*, cùng nội dung nhưng ôn theo lịch cách quãng.

## Bắt đầu

<div class="grid cards" markdown>

-   :material-rocket-launch: **Fast Path — 2 ngày** — [Kế hoạch](FAST-PATH-2-NGAY.md)
-   :material-cog: **P0 · Thiết lập** — [Zero → xanh](00-thiet-lap/index.md)
-   :material-star: **Chương mẫu CORE** — [Value vs Reference](p1-csharp/bo-nho-va-kieu-du-lieu.md)
-   :material-school: **Vì sao học nhanh mà chắc?** — [Kiến trúc sư phạm](PEDAGOGY.md)

</div>

## 🗺️ Toàn bộ lộ trình (một dự án TaskFlow lớn dần)

### P0 · Thiết lập
- [Zero → bài tập xanh đầu tiên](00-thiet-lap/index.md)

### P1 · Ngôn ngữ C#
- [Nền tảng](p1-csharp/nen-tang.md) · [Bộ nhớ & Kiểu dữ liệu](p1-csharp/bo-nho-va-kieu-du-lieu.md) · [OOP](p1-csharp/oop.md) · [Collections & LINQ](p1-csharp/collections-linq.md) · [async/await](p1-csharp/async-await.md) · [Xử lý ngoại lệ](p1-csharp/exceptions.md)

### P2 · Dữ liệu — SQL & EF Core
- [SQL nền tảng](p2-du-lieu/sql-nen-tang.md) · [JOIN, GROUP BY & Subquery](p2-du-lieu/joins-aggregation.md) · [EF Core](p2-du-lieu/ef-core.md)

### P3 · ASP.NET Core Web API
- [Minimal API & REST](p3-web-api/minimal-api.md) · [Dependency Injection](p3-web-api/dependency-injection.md) · [Validation](p3-web-api/validation.md)

### P4 · Bảo mật, Test & Deploy
- [JWT](p4-bao-mat/jwt.md) · [Tải file an toàn](p4-bao-mat/tai-file-an-toan.md) · [Testing (xUnit)](p4-bao-mat/testing.md) · [Logging & Xử lý ngoại lệ toàn cục](p4-bao-mat/logging-exceptions.md) · [Docker & Deploy](p4-bao-mat/deploy-docker.md)

### P5 · AI Engineering
- [Dùng Claude Code](p5-ai/claude-code.md) · [Model Context Protocol (MCP)](p5-ai/mcp.md) · [🏁 Capstone: TaskFlow đầu-cuối](p5-ai/capstone.md)

---
*Mỗi khái niệm có đúng một trang canonical; chất lượng do CI cưỡng chế (`.github/workflows/ci.yml`), không phải lời hứa.*
