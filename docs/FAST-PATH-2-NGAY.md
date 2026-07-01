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
| Sáng | [P1 Bộ nhớ & Kiểu dữ liệu](p1-csharp/bo-nho-va-kieu-du-lieu.md) | Dự đoán đúng value vs reference | 45' |
| Sáng | P1 async/await *(draft)* | Gọi I/O không chặn thread | 45' |
| Chiều | P2 SQL nền tảng *(draft)* | Viết JOIN/GROUP BY trên PostgreSQL {{ postgres.current }} | 90' |
| Chiều | P2 EF Core *(draft)* | Map domain → DB, đọc/ghi dữ liệu | 90' |

**Cuối ngày 1:** một console app đọc/ghi được dữ liệu qua EF Core.

## Ngày 2 — API, Bảo mật & AI (ship được sản phẩm)

| Khối | Bài | Bạn làm được | ⏱️ |
|---|---|---|---|
| Sáng | P3 Minimal API + DI *(draft)* | Dựng REST endpoint có DI | 90' |
| Sáng | [P4 JWT](p4-bao-mat/jwt.md) | Bảo vệ endpoint bằng token an toàn | 60' |
| Chiều | P4 Test *(draft)* | Viết test xUnit cho API | 60' |
| Chiều | P5 Claude Code *(draft)* | Dùng AI đúng cách để tăng tốc | 60' |
| Chiều | P5 Capstone *(draft)* | Ghép thành app **TaskFlow** chạy đầu-cuối | 90' |

**Cuối ngày 2:** một Web API TaskFlow có auth, có test, deploy được.

## Ôn tiếp để thành "chắc" (tuần 1 → tuần 8)

- **Mỗi sáng 10 phút:** làm các câu Leitner tới hạn (gợi lại, không đọc lại).
- **Cuối mỗi tuần:** làm bài "Review cuối pha" (trộn câu nhiều bài — interleaving).
- **Mỗi bài quay lại làm mục 6 (thử thách độc lập)** — lúc này đã gỡ giàn giáo.
- Mở dần các khối 🔬 **Deep Dive** khi muốn lên senior (GC, perf, internals).

> Nói ngắn: **2 ngày để *biết làm*, vài tuần ôn cách quãng để *làm chắc*.** Đó là lời hứa duy nhất trung thực — và sản phẩm này giữ được nó.
