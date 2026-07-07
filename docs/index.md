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
-   :material-flask: **Luyện tập tương tác** — [SQL Playground](sql-playground.md) · [Quiz tự chấm](on-tap.md)
-   :material-flag-checkered: **Capstone cuối cùng (P1–P10)** — [TaskFlow đầy đủ](capstone-final/final.md)

</div>

## 🗺️ Toàn bộ lộ trình (một dự án TaskFlow lớn dần xuyên suốt P1 → Capstone)

### P0 · Thiết lập
[Zero → bài tập xanh đầu tiên](00-thiet-lap/index.md)

### P1 · C#
[Nền tảng](p1-csharp/nen-tang.md) · [Bộ nhớ & Kiểu dữ liệu](p1-csharp/bo-nho-va-kieu-du-lieu.md) · [OOP](p1-csharp/oop.md) · [Generics](p1-csharp/generics.md) · [Delegates, Events & Lambda](p1-csharp/delegates-events.md) · [Records & Pattern Matching](p1-csharp/records-pattern-matching.md) · [Collections](p1-csharp/collections.md) · [Collections & LINQ (tổng hợp)](p1-csharp/collections-linq.md) · [async/await](p1-csharp/async-await.md) · [Xử lý ngoại lệ](p1-csharp/exceptions.md)

### P2 · Dữ liệu (SQL & EF Core)
[SQL nền tảng](p2-du-lieu/sql-nen-tang.md) · [Lọc & Biểu thức nâng cao](p2-du-lieu/loc-nang-cao.md) · [Ràng buộc dữ liệu (Constraints)](p2-du-lieu/constraints.md) · [Thiết kế CSDL & Chuẩn hoá](p2-du-lieu/thiet-ke-schema.md) · [Index, Transaction & ACID](p2-du-lieu/index-transaction.md) · [JOIN, GROUP BY & Subquery](p2-du-lieu/joins-aggregation.md) · [Subquery & CTE (WITH)](p2-du-lieu/subquery-cte.md) · [Window Functions](p2-du-lieu/window-functions.md) · [EF Core](p2-du-lieu/ef-core.md) · [EF Core: Quan hệ & N+1](p2-du-lieu/ef-core-quan-he.md) · [EF Core: Migration & Seeding](p2-du-lieu/ef-core-migration.md)

### P3 · Web API
[Minimal API & REST](p3-web-api/minimal-api.md) · [Dependency Injection](p3-web-api/dependency-injection.md) · [Routing & Model Binding](p3-web-api/routing-model-binding.md) · [Configuration & Options](p3-web-api/configuration-options.md) · [Validation](p3-web-api/validation.md) · [Middleware Pipeline](p3-web-api/middleware.md) · [Xử lý lỗi toàn cục & ProblemDetails](p3-web-api/xu-ly-loi-toan-cuc.md) · [OpenAPI & Swagger](p3-web-api/openapi-swagger.md) · [Gọi API bên ngoài (HttpClient)](p3-web-api/goi-api-ngoai.md)

### P4 · Bảo mật, Test & Deploy
[JWT (canonical)](p4-bao-mat/jwt.md) · [Tải file an toàn](p4-bao-mat/tai-file-an-toan.md) · [Testing (xUnit)](p4-bao-mat/testing.md) · [Structured Logging (ILogger)](p4-bao-mat/logging-exceptions.md) · [Docker & Deploy](p4-bao-mat/deploy-docker.md)

### P5 · AI Engineering
[Dùng Claude Code](p5-ai/claude-code.md) · [Model Context Protocol](p5-ai/mcp.md) · [🏁 Capstone trung gian: TaskFlow (P1–P4)](p5-ai/capstone.md)

### P6 · Kiến trúc & Design Patterns
[Kiến trúc phân lớp](p6-kien-truc/kien-truc-phan-lop.md) · [Repository & Unit of Work](p6-kien-truc/repository-unit-of-work.md) · [Design Patterns cốt lõi](p6-kien-truc/design-patterns-co-ban.md) · [Design Patterns nâng cao](p6-kien-truc/design-patterns-nang-cao.md) · [Clean Architecture](p6-kien-truc/clean-architecture.md) · [CQRS](p6-kien-truc/cqrs.md) · [Domain-Driven Design cơ bản](p6-kien-truc/ddd-co-ban.md) · [Message Queue & Event-Driven](p6-kien-truc/message-queue-event-driven.md)

### P7 · Blazor Frontend
[Blazor: Server vs WebAssembly vs Hybrid](p7-blazor/blazor-tong-quan.md) · [Component cơ bản](p7-blazor/component-co-ban.md) · [Data Binding & Sự kiện](p7-blazor/data-binding-events.md) · [Routing & Navigation](p7-blazor/routing-navigation.md) · [Forms & Validation](p7-blazor/forms-validation.md) · [Quản lý State](p7-blazor/state-management.md) · [Gọi API Backend](p7-blazor/goi-api-tu-blazor.md) · [Authentication trong Blazor](p7-blazor/blazor-authentication.md) · [JS Interop & Lifecycle nâng cao](p7-blazor/js-interop-lifecycle-sau.md) · [Performance & Deploy](p7-blazor/blazor-performance-deploy.md)

### P8 · Production
[Caching: IMemoryCache & Distributed Cache](p8-production/caching.md) · [Rate Limiting](p8-production/rate-limiting.md) · [Health Checks & Observability](p8-production/health-checks-observability.md) · [Background Jobs](p8-production/background-jobs.md) · [API Versioning](p8-production/api-versioning.md) · [Resilience Patterns](p8-production/resilience-patterns.md) · [Security Headers & CORS](p8-production/security-headers-cors.md)

### P9 · DevOps
[CI/CD với GitHub Actions](p9-devops/cicd-github-actions.md) · [Cloud Fundamentals: IaaS, PaaS, SaaS](p9-devops/cloud-fundamentals.md) · [Container Orchestration: Kubernetes cơ bản](p9-devops/container-orchestration.md) · [Infrastructure as Code: Terraform & Bicep](p9-devops/infrastructure-as-code.md) · [Monitoring & Alerting Production](p9-devops/monitoring-alerting.md)

### P10 · CS Foundations & Interview Prep
[Big-O & Độ phức tạp thuật toán](p10-cs-foundations/big-o-complexity.md) · [Cấu trúc dữ liệu nâng cao](p10-cs-foundations/cau-truc-du-lieu-nang-cao.md) · [Graph & BFS/DFS](p10-cs-foundations/graph-bfs-dfs.md) · [Sorting Algorithms](p10-cs-foundations/sorting-algorithms.md) · [Recursion & Binary Search](p10-cs-foundations/recursion-binary-search.md) · [Dynamic Programming cơ bản](p10-cs-foundations/dynamic-programming-co-ban.md) · [Interview Patterns: Two Pointers & Sliding Window](p10-cs-foundations/interview-patterns.md) · [System Design cơ bản & Behavioral Interview](p10-cs-foundations/system-design-behavioral.md)

### Capstone cuối cùng
[Capstone cuối cùng — TaskFlow đầy đủ (P1–P10)](capstone-final/final.md)

---
*Mỗi khái niệm có đúng một trang canonical; chất lượng do CI cưỡng chế (`.github/workflows/ci.yml`), không phải lời hứa.*
