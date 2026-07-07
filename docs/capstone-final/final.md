---
tier: core
status: core
owner: core-team
verified_on: "2026-07-05"
dotnet_version: "10.0"
bloom: "Tổng hợp"
requires: [p10-systemdesign]
est_minutes_fast: 2400
---

# Capstone cuối cùng — TaskFlow đầy đủ (P1–P10)

!!! info "bạn đang ở đây · node `p-capstone-final` · chương cuối cùng của toàn bộ chương trình"
    **cần trước:** toàn bộ P1–P10 — đặc biệt `p5-capstone` (TaskFlow bản P1–P4), `p6-layered`…`p6-messaging` (kiến trúc), `p7-overview`…`p7-deploy` (Blazor), `p8-caching`…`p8-cors` (production), `p9-cicd`…`p9-monitoring` (DevOps), `p10-systemdesign` (tư duy thiết kế hệ thống) — chương này không dạy khái niệm mới, chỉ ghép lại toàn bộ 10 phase vào một hệ thống chạy được đầu-cuối.
    **mở khoá:** năng lực tự mở rộng một hệ thống có sẵn (brownfield) bằng kiến trúc, frontend thật, vận hành production và CI/CD thật — đúng công việc một lập trình viên .NET làm mỗi ngày, không riêng TaskFlow.

> **Mục tiêu (đo được):** sau chương này bạn **Tổng hợp** (Bloom: Tổng hợp) toàn bộ 10 phase đã học thành một hệ thống TaskFlow hoàn chỉnh — mở rộng đúng bản TaskFlow P1–P4 đã có (không viết lại từ đầu) bằng kiến trúc phân lớp/pattern phù hợp từ P6, một Blazor frontend thật thay cho API-only từ P7, caching/rate-limit/resilience/health-check từ P8, và một pipeline CI/CD thật từ P9 — rồi tự chấm kết quả bằng một Definition of Done gồm ít nhất 10 tiêu chí đo được bằng lệnh cụ thể, liên kết lại với toàn bộ 10 phase của chương trình.

!!! warning "Đây là bài tập tích hợp, không phải bài dạy khái niệm mới"
    Không có mục "Đoán nhanh" hay định nghĩa từng khái niệm ở đây — bạn đã học và đã tự kiểm tra từng khái niệm ở P1–P10 rồi. Nếu đọc một mục dưới đây và thấy tên pattern/API lạ, đó là dấu hiệu bạn cần quay lại đúng chương gốc đọc lại (tên chương được nêu chính xác ở mỗi mục), không phải học lại ở đây.

Nhắc lại đúng phạm vi bản gốc: TaskFlow ở `p5-capstone` đã có `User`/`TaskItem` quan hệ 1-N qua EF Core, 5 endpoint (`POST /auth/login`, `GET /tasks`, `POST /tasks`, `PUT /tasks/{id}`, `DELETE /tasks/{id}`) bảo vệ bằng JWT, validation trả `400`, exception handler toàn cục, `TaskService` tách đúng ranh giới (không biết `HttpContext`), ít nhất 2 test xUnit, và structured logging. Chương này **mở rộng tiếp** từ đúng code base đó — không tạo entity mới thay thế, không đổi tên project.

---

## 1. Kiến trúc tổng quan — TaskFlow sau khi hoàn thiện cả 10 phase

**Sơ đồ đầy đủ** (khác bản P5 ở: có tầng Blazor Server-Side Rendering làm UI, có Repository/Unit of Work tách khỏi `AppDbContext` trực tiếp, có `IMemoryCache` + rate limiter + Polly `ResiliencePipeline` chặn trước khi chạm domain, có pipeline CI/CD chạy test/build/deploy tự động):

```mermaid
flowchart TD
    subgraph Client
      BZ[Blazor UI - component .razor]
    end
    BZ -->|HttpClient + JWT trong localStorage| MW0[Exception handler toan cuc - P3]
    MW0 --> RL[Rate Limiter - P8]
    RL --> MW1[UseAuthentication - P4]
    MW1 --> MW2[UseAuthorization - P4]
    MW2 --> CORS[CORS + security headers - P8]
    CORS --> EP[Endpoint Minimal API - P3]
    EP -->|validate DTO| VAL[Validation - P3]
    EP --> SVC[TaskService - domain rule P1]
    SVC --> CACHE{IMemoryCache co du lieu? - P8}
    CACHE -->|co| SVC
    CACHE -->|khong| RESIL[Polly ResiliencePipeline - P8]
    RESIL --> REPO[TaskRepository / UnitOfWork - P6]
    REPO --> DBCTX[AppDbContext - P2]
    DBCTX --> PG[(PostgreSQL)]
    PG -.du lieu.-> SVC
    SVC -.ket qua.-> EP
    EP -->|200/201/204| BZ
    subgraph Nen_tang_van_hanh
      HC[/health - liveness+readiness - P8]
      BG[BackgroundService nhac han task - P8]
      LOG[Structured logging + CorrelationId - P4]
      OBS[Health checks + observability - P8]
    end
    subgraph CICD
      GH[GitHub Actions - P9]
      GH -->|dotnet test| GATE{Test pass?}
      GATE -->|co| BUILD[Docker build - P4]
      BUILD --> DEPLOY[Deploy - P9]
      GATE -->|khong| FAIL[Chan merge]
    end
```

Đọc đúng khác biệt so với sơ đồ P5: client giờ là **Blazor UI** thật (không phải Postman/curl); trước khi request chạm middleware JWT, nó đi qua **rate limiter**; trước khi `TaskService` chạm database, nó kiểm **`IMemoryCache`** rồi mới gọi qua **Polly `ResiliencePipeline`**; tầng truy cập dữ liệu tách thành **Repository/Unit of Work** riêng khỏi `AppDbContext` gọi trực tiếp; và toàn bộ vòng đời có một pipeline **GitHub Actions** chạy test trước khi build/deploy.

---

## 2. Cần thêm gì từ P6 (Kiến trúc & Design Patterns)

Bản P5 đã có `TaskService` tách đúng ranh giới (không biết `HttpContext`) nhưng gọi `AppDbContext` trực tiếp — đây là điểm cần bổ sung, không phải viết lại:

- **`p6-repository` (Repository/Unit of Work):** tách `AppDbContext.Tasks`/`.Users` ra khỏi `TaskService` bằng một `ITaskRepository` (`GetByIdAsync`, `GetAllByUserAsync`, `AddAsync`) và một `IUnitOfWork` gói `SaveChangesAsync()` — áp dụng đúng nguyên tắc "biết khi nào Repository thật sự cần, khi nào `DbSet` là đủ" đã học: vì TaskFlow giờ có thêm cache/resilience quanh việc đọc dữ liệu (mục 4), tách Repository giúp thêm logic đó vào **một chỗ** mà không sửa `TaskService`.
- **`p6-layered` (Kiến trúc phân lớp):** xác nhận lại luật phụ thuộc một chiều đã áp dụng ở P5 (Endpoint → Service → Repository → DbContext) vẫn đúng khi thêm Blazor — Blazor component **không** gọi `AppDbContext` trực tiếp, luôn gọi qua HTTP tới API, giữ đúng một tầng biên giữa UI và backend.
- **`p6-patterns-basic` (Factory/Strategy/Decorator):** áp dụng **Strategy** cho quy tắc sắp xếp/lọc task (ví dụ `ITaskSortStrategy` cho "theo hạn" vs "theo mức ưu tiên") nếu Blazor UI (mục 3) cần nhiều kiểu sắp xếp — chỉ thêm nếu thật sự có ≥2 biến thể, đúng nguyên tắc "nhận diện khi nào là thừa" đã học.
- **`p6-cqrs` (CQRS):** quyết định **không** tách Command/Query đầy đủ cho TaskFlow (CRUD task đơn giản, không có mô hình đọc phức tạp khác mô hình viết) — nhưng ghi rõ lý do quyết định này vào README của project, đúng kỹ năng "tránh over-engineering CRUD" đã học, chứ không phải bỏ qua vì lười.
- **`p6-ddd` (DDD cơ bản):** xác nhận `TaskItem` là **Entity** (có định danh `Id`, trạng thái thay đổi qua thời gian) và `User` là **Aggregate Root** hợp lý duy nhất cần bảo vệ bất biến (ví dụ: không xoá `User` khi còn task chưa hoàn thành, nếu bạn chọn thêm quy tắc này) — không cần tách thêm Value Object nếu domain vẫn đơn giản như bản P5.
- **`p6-messaging` (Message Queue/Event-Driven):** thêm **một** sự kiện đơn giản — khi `TaskService.TryCompleteAsync` thành công, publish một in-process event (dùng đúng interface `IRequest`/`IRequestHandler`/`IMediator.Send()` đã học ở chương CQRS — nếu không cần MediatR, gọi trực tiếp một service C# thuần đăng ký qua DI, như cách "khi nào KHÔNG cần MediatR" đã học) để `BackgroundService` (mục 4) ghi log "task hoàn thành" — không cần dựng RabbitMQ/Kafka thật cho quy mô capstone, nhưng phải thể hiện đúng tư duy "publisher không biết ai là subscriber".

---

## 3. Cần thêm gì từ P7 (Blazor Frontend)

Bản P5 chỉ có API — đây là thay đổi lớn nhất: TaskFlow giờ có **UI thật**, người dùng cuối không cần Postman.

- **`p7-overview` (chọn hosting model):** chọn **Blazor Web App** (chế độ render Server hoặc Auto theo .NET 10) cho TaskFlow — ghi rõ lý do chọn trong README (ví dụ: ưu tiên tương tác nhanh không cần tải WASM runtime, phù hợp app quản lý task nội bộ ít người dùng đồng thời).
- **`p7-component` (component .razor):** viết tối thiểu 2 component — `TaskList.razor` (nhận `Parameter` là `UserId`, hiển thị danh sách) và `TaskForm.razor` (`ChildContent` hoặc form tạo/sửa task) — đúng thứ tự lifecycle `OnInitializedAsync` trước `OnParametersSetAsync`.
- **`p7-binding` (data binding & events):** dùng `@bind` cho input `Title`/`Status`, `@onclick`/`EventCallback<TaskItem>` cho nút "Hoàn thành" — gọi `StateHasChanged()` đúng chỗ sau khi cập nhật task qua API (không quên, vì gọi từ async callback ngoài lifecycle Blazor).
- **`p7-routing` (routing & navigation):** `@page "/tasks"` cho danh sách, `@page "/tasks/{Id:guid}"` cho chi tiết — dùng route parameter (không query string) để mở đúng task theo `Id`.
- **`p7-forms` (forms & validation):** `EditForm` + `InputText`/`DataAnnotationsValidator` cho `TaskForm.razor`, dùng `OnValidSubmit` (không phải `OnSubmit`) để chỉ gọi API khi form hợp lệ phía client — vẫn giữ validation phía server (đã có ở P5) làm lớp chặn cuối, không tin riêng validation client.
- **`p7-state` (state management):** chọn **state container service** (đăng ký `Scoped`, ví dụ `TaskStateContainer` giữ danh sách task hiện tại + gọi `NotifyStateChanged`) thay vì `CascadingParameter` — vì trạng thái danh sách task cần chia sẻ giữa nhiều component không lồng cha-con trực tiếp.
- **`p7-httpclient` (gọi API từ Blazor):** `TaskApiClient` dùng `IHttpClientFactory`, tự quản lý trạng thái `Loading`/`Error` hiển thị trên UI khi gọi `GET /tasks` — không gọi `AppDbContext` trực tiếp từ Blazor dù cùng chạy trong một process (giữ đúng ranh giới đã nêu ở mục 2).
- **`p7-auth` (Blazor authentication):** lưu JWT (đã cấp từ `p4-jwt`) và implement `AuthenticationStateProvider` tuỳ chỉnh; bọc trang `/tasks` bằng `<AuthorizeView>` — logout thật sự xoá token khỏi nơi lưu (localStorage/`ProtectedBrowserStorage`), không chỉ ẩn UI.
- **`p7-jsinterop` (JS Interop & lifecycle sâu):** dùng đúng `IDisposable`/`IAsyncDisposable` cho component nào subscribe `TaskStateContainer` (tránh rò rỉ memory khi điều hướng); dùng `OnAfterRenderAsync` nếu cần gọi JS interop (ví dụ focus input khi mở form).
- **`p7-deploy` (performance & deploy):** publish Blazor, đo Lighthouse Performance score, tối ưu re-render nếu component `TaskList` re-render toàn bộ danh sách mỗi lần một task đổi trạng thái (dùng `@key` trên `foreach`).

---

## 4. Cần thêm gì từ P8 (Production)

Bản P5 chưa có bất kỳ cơ chế production nào — không cache, không rate limit, không health check.

- **`p8-caching` (IMemoryCache/IDistributedCache):** cache kết quả `GET /tasks` theo `userId` bằng `IMemoryCache`, TTL ngắn (ví dụ 30 giây); **invalidate cache đúng** ngay sau `POST`/`PUT`/`DELETE` thành công trên task của user đó — tránh đúng lỗi "dữ liệu cache cũ" đã học.
- **`p8-ratelimit` (Rate Limiting):** áp `AddRateLimiter` lên `POST /auth/login` bằng thuật toán **Fixed Window** hoặc **Token Bucket** (chọn một, giải thích lý do trong README) để chặn brute-force password — đúng cảnh báo đã có ở phần Deep Dive của bản P5.
- **`p8-health` (Health Checks & Observability):** thêm `/health/live` (liveness — process còn sống) và `/health/ready` (readiness — kết nối PostgreSQL còn tốt) qua `AddHealthChecks().AddNpgSql(...)` — phân biệt đúng hai loại đã học, không gộp chung một endpoint.
- **`p8-background` (Background Jobs):** thêm một `BackgroundService` chạy định kỳ (ví dụ mỗi giờ) quét task quá hạn (`DueDate < DateTime.UtcNow && Status != Done`) và ghi log nhắc hạn — tôn trọng `CancellationToken` khi ứng dụng shutdown, không để job treo.
- **`p8-versioning` (API Versioning):** gắn version cho API hiện có (ví dụ `/api/v1/tasks`) trước khi thêm bất kỳ breaking change nào ở capstone này — xác định rõ việc thêm field mới vào response là **non-breaking**, việc đổi kiểu `Status` từ `enum` sang `string` (nếu có) là **breaking**.
- **`p8-resilience` (Resilience Patterns qua Polly):** bọc lời gọi PostgreSQL (qua Repository, mục 2) bằng một Polly `ResiliencePipeline` kết hợp **Retry** (2-3 lần, backoff) + **Timeout** — không cần Circuit Breaker đầy đủ nếu TaskFlow chỉ gọi một database, nhưng phải giải thích trong README vì sao bỏ Circuit Breaker (đúng tư duy "kết hợp đúng theo tình huống", không phải thêm cho đủ).
- **`p8-cors` (Security Headers & CORS):** cấu hình `AddCors` chỉ cho phép đúng origin của Blazor UI (không dùng `AllowAnyOrigin` cho API có JWT); thêm header bảo mật cơ bản (`X-Content-Type-Options: nosniff`) — ghi rõ CORS là luật browser thực thi, không phải lớp bảo mật server.

---

## 5. Cần thêm gì từ P9 (DevOps & Cloud)

Bản P5 chỉ có Dockerfile đơn (từ `p4-deploy`) — chưa có pipeline tự động, chưa có khái niệm hạ tầng.

- **`p9-cicd` (CI/CD với GitHub Actions):** viết một workflow `.github/workflows/ci.yml` thật có tối thiểu 2 job nối bằng `needs`: job `test` chạy `dotnet test`, job `build` (chỉ chạy nếu `test` pass) build Docker image bằng một step `run: docker build -t taskflow .` (ghép cú pháp job/needs đã học ở p9-cicd với Dockerfile đã có từ `p4-deploy` — chương p9-cicd không tự có ví dụ build Docker image sẵn, vì workflow CI thật của Learning Hub build tài liệu, không phải image) — phân biệt đúng CI (test/build tự động mỗi push) với CD (deploy tự động) đã học; nếu chưa deploy thật, dừng ở CI + build image là đủ.
- **`p9-cloud` (Cloud Fundamentals):** ghi trong README lựa chọn hạ tầng cho TaskFlow (ví dụ PaaS như Azure App Service/Render cho API, static hosting cho Blazor WASM nếu chọn hosting model đó) và lý do — phân biệt đúng tầng bạn tự quản lý (code) vs tầng nhà cung cấp quản lý (OS/runtime) theo IaaS/PaaS/SaaS.
- **`p9-k8s` (Container Orchestration — tuỳ chọn nâng cao):** nếu muốn đi xa hơn mức tối thiểu, viết một `deployment.yaml` + `service.yaml` cơ bản cho TaskFlow API, giải thích vai trò tự phục hồi (self-healing) của Kubernetes khi một Pod crash — không bắt buộc để đạt Definition of Done, nhưng phải hiểu đúng khái niệm nếu đưa vào.
- **`p9-iac` (Infrastructure as Code — tuỳ chọn nâng cao):** nếu triển khai lên cloud thật, viết hạ tầng (database, app service) bằng Terraform/Bicep thay vì tạo tay qua UI — phân biệt đúng `plan` (xem trước thay đổi) vs `apply` (thực thi).
- **`p9-monitoring` (Monitoring & Alerting):** kết nối `/health/ready` (mục 4) với một cơ chế alert đơn giản (ví dụ GitHub Actions scheduled job gọi health check, hoặc log warning nếu response không phải `200`) — định nghĩa tối thiểu một SLI (ví dụ "tỷ lệ request `/health/ready` trả `200`") cho TaskFlow.

---

## 6. Thứ tự gợi ý làm (linh hoạt, không bắt buộc cứng)

Khác với P1→P4 (phải làm tuần tự vì kiến thức xây trên nhau), đây là làm **thêm** vào một code base có sẵn — thứ tự dưới đây là gợi ý giảm rủi ro đổ vỡ, không phải luật cứng:

1. **P6 trước** (mục 2): tách Repository/Unit of Work trước, vì mục 4 (cache/resilience) sẽ chèn vào đúng lớp Repository này — làm sau sẽ phải sửa lại hai lần.
2. **P8 kế tiếp** (mục 4): thêm cache/rate-limit/health-check/resilience vào backend đã có Repository sạch — vẫn kiểm bằng `curl`/Postman, chưa cần UI.
3. **P7 sau đó** (mục 3): xây Blazor UI gọi vào backend đã ổn định — nếu làm Blazor trước khi ổn định API, mỗi lần đổi response shape ở backend phải sửa lại UI, tốn công gấp đôi.
4. **P9 cuối cùng** (mục 5): viết CI/CD khi đã có đủ test (từ P6/P8) và toàn bộ hệ thống (kể cả Blazor) build được — pipeline CI chạy sớm hơn chỉ test được phần nhỏ, ít giá trị.

Ngoại lệ hợp lý: nếu bạn muốn thấy CI "xanh" sớm để có phản hồi liên tục, có thể viết khung CI (bước 4) ngay từ đầu với job `test` rỗng, rồi bổ sung dần — đây là lựa chọn cá nhân, không sai.

---

## 7. Definition of Done

Chấm TaskFlow bản cuối — chỉ tick khi kiểm chứng được bằng lệnh/kết quả cụ thể, không tick theo cảm giác:

- [ ] **1. Repository/Unit of Work tách đúng lớp (P6):** `grep -rn "AppDbContext" --include=*.cs Endpoints/` không tìm thấy `AppDbContext` được inject trực tiếp vào bất kỳ endpoint nào — chỉ `ITaskRepository`/`IUnitOfWork` được inject.
- [ ] **2. `dotnet test` xanh với số lượng tối thiểu:** `dotnet test` trả về **ít nhất 8 test pass, 0 fail** (2 test gốc từ P5 + tối thiểu 6 test mới cho Repository, cache invalidation, rate limiter, health check).
- [ ] **3. Blazor UI chạy được đầu-cuối (P7):** mở `https://localhost:xxxx/tasks` trên browser sau khi đăng nhập, thấy đúng danh sách task của user hiện tại render ra từ component `TaskList.razor`, không phải từ Postman/curl.
- [ ] **4. Auth Blazor hoạt động (P7):** truy cập `/tasks` khi chưa đăng nhập bị `AuthorizeView` chặn và điều hướng về `/login` — kiểm bằng cách xoá token khỏi localStorage rồi reload trang.
- [ ] **5. Cache invalidate đúng (P8):** gọi `GET /tasks` hai lần liên tiếp (lần 2 phải ra từ cache — kiểm qua log "cache hit"), sau đó `POST /tasks` một task mới, gọi lại `GET /tasks` phải thấy task mới ngay (không phải đợi TTL hết) — kiểm bằng `curl -i` xem log server.
- [ ] **6. Rate limiter chặn đúng (P8):** gửi 11 request `POST /auth/login` liên tục trong 10 giây (ví dụ bằng `for i in {1..11}; do curl -s -o /dev/null -w "%{http_code}\n" -X POST .../auth/login; done`) — thấy tối thiểu một response trả `429 Too Many Requests`.
- [ ] **7. Health check phân biệt đúng liveness/readiness (P8):** `curl -i /health/live` trả `200` ngay cả khi tắt PostgreSQL; `curl -i /health/ready` trả `503` khi PostgreSQL không kết nối được — kiểm bằng cách `docker stop <container-postgres>` rồi gọi lại cả hai endpoint.
- [ ] **8. Resilience hoạt động khi database chậm/lỗi (P8):** tạm chặn kết nối PostgreSQL (dừng container) rồi gọi `GET /tasks` — log server thể hiện đúng số lần retry theo cấu hình Polly `ResiliencePipeline`, không phải một lỗi 500 ngay lập tức.
- [ ] **9. CI pipeline xanh trên GitHub Actions (P9):** push commit lên branch, mở tab Actions, thấy job `test` và job `build` đều có dấu tick xanh; nếu chủ động làm một test fail rồi push, job `build` **không chạy** (do `needs: test` chặn) — chứng minh gate hoạt động đúng.
- [ ] **10. Docker image build được từ pipeline (P9):** `docker images` sau khi CI chạy xong (hoặc build local bằng đúng Dockerfile) thấy image TaskFlow được tạo, `docker run` image đó và `curl /health/live` trả `200`.
- [ ] **11. Lighthouse Performance cho Blazor UI (P7):** chạy Lighthouse (Chrome DevTools) trên trang `/tasks` đã publish (Release build, không phải `dotnet watch`), điểm Performance **>= 70**.
- [ ] **12. Không còn lỗ hổng BOLA cũ (P4, kiểm lại):** `curl` `PUT /tasks/{id-của-user-khác}` kèm token hợp lệ của user A vẫn trả `403`/`404` (không `200`) — xác nhận việc thêm Repository (mục 2) không vô tình làm mất kiểm tra chủ sở hữu đã có từ P5.

```bash title="Terminal — kiểm chứng toàn bộ Definition of Done theo thứ tự"
dotnet build
dotnet test
docker compose up -d
curl -i http://localhost:8080/health/live
curl -i http://localhost:8080/health/ready
dotnet run --project TaskFlow.Api
```

---

## 8. Checklist tự đánh giá cuối cùng — liên kết lại toàn bộ 10 phase

Đây là lần cuối bạn tự soát toàn bộ chương trình qua đúng một sản phẩm — với mỗi phase, trả lời được câu hỏi bằng chính TaskFlow của bạn, không phải bằng lý thuyết chung:

- [ ] **P1 (Ngôn ngữ C#):** `TaskItem`/`TaskState` vẫn dùng đúng OOP/record/pattern matching — domain rule vẫn ném exception cụ thể khi vi phạm bất biến, không bị pha trộn logic HTTP vào sau khi thêm Repository.
- [ ] **P2 (Dữ liệu):** `dotnet ef migrations list` cho thấy lịch sử migration liên tục, không có migration bị sửa tay sau khi đã áp dụng; navigation property `User.Tasks`/`TaskItem.User` vẫn đúng, không N+1 query khi `TaskList.razor` tải danh sách (kiểm bằng log SQL của EF Core).
- [ ] **P3 (Web API):** mọi endpoint vẫn trả đúng mã trạng thái theo bảng hợp đồng đã học (`201`/`200`/`204`/`400`/`401`/`403`/`404`) sau khi thêm rate limiter/cache — không có endpoint nào đổi hành vi phụ ngoài ý muốn.
- [ ] **P4 (Bảo mật/Test/Deploy):** JWT vẫn cấp/kiểm đúng, password vẫn hash, `dotnet test` vẫn xanh, Docker image vẫn chạy được — không bị hỏng khi thêm các tầng mới.
- [ ] **P5 (AI Engineering & capstone trung gian):** nếu dùng Claude Code/agent để hỗ trợ mở rộng chương này, có một `CLAUDE.md` mô tả đúng cấu trúc TaskFlow hiện tại, và bạn vẫn là người review từng diff trước khi merge — không để agent tự merge.
- [ ] **P6 (Kiến trúc):** trả lời được "vì sao chọn Repository ở đây mà không phải gọi `DbSet` trực tiếp" bằng đúng lý do đã ghi ở mục 2 (không phải "vì tài liệu bảo làm vậy").
- [ ] **P7 (Blazor):** trả lời được "vì sao chọn state container service mà không phải CascadingParameter" cho `TaskStateContainer` — dựa trên phạm vi chia sẻ dữ liệu thực tế của TaskFlow.
- [ ] **P8 (Production):** trả lời được sự khác biệt giữa liveness và readiness bằng chính hai endpoint `/health/live` và `/health/ready` của TaskFlow, không bằng định nghĩa chung.
- [ ] **P9 (DevOps):** trả lời được "CI khác CD ở đâu trong pipeline TaskFlow của tôi" bằng chính job `test`/`build` đã viết, không bằng định nghĩa sách giáo khoa.
- [ ] **P10 (CS Foundations & System Design):** áp dụng đúng quy trình 4 bước System Design (làm rõ yêu cầu → ước lượng quy mô → thiết kế → đánh đổi) để tự phản biện một quyết định đã đưa ra ở TaskFlow (ví dụ: "nếu TaskFlow phải phục vụ 10,000 request/giây, `IMemoryCache` còn đủ hay phải đổi sang `IDistributedCache` với Redis?").

Hoàn thành đủ 12 tiêu chí ở mục 7 và soát đủ 10 dòng ở mục 8 nghĩa là bạn đã tự đi hết một vòng đầy đủ từ dòng code C# đầu tiên ở P1 đến một hệ thống có kiến trúc, frontend, vận hành production và CI/CD thật — đây chính là năng lực bạn sẽ tái sử dụng ở mọi dự án thật tiếp theo, không riêng TaskFlow.
