---
tier: fast
status: core
owner: core-team
verified_on: "2026-07-01"
---

# 🚀 Fast Path — Kế hoạch 2 ngày (trung thực)

!!! danger "Đọc kỹ điều này trước"
    **2 ngày KHÔNG biến bạn thành senior.** Mục tiêu thực tế và *đảm bảo được*: sau 2 ngày bạn **hiểu lõi + tự tay ship được một API .NET {{ dotnet.current }} chạy được có auth**, và có bản đồ rõ để đi tiếp. "Master" là kết quả của lặp lại cách quãng trong 6–8 tuần — xem cột "Ôn tiếp" bên dưới.

## Nguyên tắc 2 ngày

1. Chỉ đi **fast-path**, **bỏ qua mọi khối 🔬 Deep Dive**.
2. Mỗi bài: làm mục 0 (đoán) → 2 (chạy ví dụ) → 3 (bài tập) → 5 (tự kiểm tra). Bỏ mục 6 (để dành tuần sau).
3. Sau mỗi bài, đánh dấu 3 câu tự-kiểm-tra vào bộ ôn Leitner. **Đây là phần biến "nhanh" thành "chắc".**

## Ngày 1 — Ngôn ngữ & Dữ liệu (làm ra được dữ liệu)

| Khối | Bài | Bạn làm được | ⏱️ |
|---|---|---|---|
| Sáng | [P0 Thiết lập](00-thiet-lap/index.md) | Chạy `dotnet run`, thấy test PASS | 30' |
| Sáng | [C# Nền tảng](p1-csharp/nen-tang.md) + [Bộ nhớ & Kiểu dữ liệu](p1-csharp/bo-nho-va-kieu-du-lieu.md) | Cú pháp lõi; value vs reference | 60' |
| Sáng | [async/await](p1-csharp/async-await.md) | Gọi I/O không chặn thread | 45' |
| Chiều | [SQL nền tảng](p2-du-lieu/sql-nen-tang.md) | Viết JOIN/GROUP BY trên PostgreSQL {{ postgres.current }} | 90' |
| Chiều | [EF Core](p2-du-lieu/ef-core.md) | Map domain → DB, đọc/ghi dữ liệu | 90' |

**Cuối ngày 1:** một console app đọc/ghi được dữ liệu qua EF Core.

## Ngày 2 — API, Bảo mật & AI (ship được sản phẩm)

| Khối | Bài | Bạn làm được | ⏱️ |
|---|---|---|---|
| Sáng | [Minimal API](p3-web-api/minimal-api.md) + [DI](p3-web-api/dependency-injection.md) | Dựng REST endpoint có DI | 90' |
| Sáng | [JWT](p4-bao-mat/jwt.md) + [Validation](p3-web-api/validation.md) | Bảo vệ endpoint + kiểm input | 75' |
| Chiều | [Testing](p4-bao-mat/testing.md) | Viết test xUnit cho API | 60' |
| Chiều | [Claude Code](p5-ai/claude-code.md) | Dùng AI đúng cách để tăng tốc | 45' |
| Chiều | [🏁 Capstone](p5-ai/capstone.md) | Ghép thành app **TaskFlow** chạy đầu-cuối | 90' |

**Cuối ngày 2:** một Web API TaskFlow có auth, có test, deploy được.

## Ôn tiếp để thành "chắc" (tuần 1 → tuần 8)

- **Mỗi sáng 10 phút:** làm các câu Leitner tới hạn (gợi lại, không đọc lại).
- **Cuối mỗi tuần:** làm bài "Review cuối pha" (trộn câu nhiều bài — interleaving).
- **Mỗi bài quay lại làm mục 6 (thử thách độc lập)** — lúc này đã gỡ giàn giáo.
- Mở dần các khối 🔬 **Deep Dive** khi muốn lên senior (GC, perf, internals).

> Nói ngắn: **2 ngày để *biết làm*, vài tuần ôn cách quãng để *làm chắc*.** Đó là lời hứa duy nhất trung thực — và sản phẩm này giữ được nó.
