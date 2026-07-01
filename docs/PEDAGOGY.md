---
tier: core
status: core
owner: core-team
verified_on: "2026-07-01"
---

# Kiến trúc sư phạm — vì sao học nhanh mà vẫn chắc

Mỗi mục trong template chương không phải trang trí — nó là một **biện pháp học tập có căn cứ nghiên cứu**. Đây là bản đồ "tính năng → cơ chế → lợi ích".

| Biện pháp | Cơ sở | Hiện diện trong bài | Lợi ích |
|---|---|---|---|
| **Mastery learning** (đạt chuẩn mới đi tiếp) | Bloom (1968) | DAG prerequisite; phải xanh node N mới mở N+1 | Không "nợ kiến thức" tích luỹ |
| **Retrieval practice** (gợi lại > đọc lại) | Roediger & Karpicke (2006) | Mục 5 "Tự kiểm tra": trả lời *không nhìn bài* rồi mới mở đáp án | Trí nhớ bền hơn hẳn đọc thụ động |
| **Spaced repetition** (ôn cách quãng) | Ebbinghaus; Cepeda (2006) | Hộp Leitner 1d→3d→1w; bài "Review cuối pha" | Chống quên; tốn ít giờ hơn nhồi |
| **Interleaving** (trộn chủ đề) | Rohrer (2012) | Review cuối pha trộn câu từ nhiều node | Phân biệt khái niệm tốt hơn |
| **Worked-example effect** | Sweller & Cooper (1985) | Mục 2 luôn có ví dụ mẫu chạy được kèm output | Giảm tải nhận thức khi mới học |
| **Faded scaffolding** (gỡ giàn giáo dần) | Renkl & Atkinson (2003) | L1 điền chỗ trống → L2 có test sẵn → L3 chỉ spec | Xây năng lực độc lập, không phụ thuộc copy |
| **Cognitive load theory** | Sweller | Fast-path ≤1200 từ; deep-dive gập lại | Không nhồi; lý thuyết đúng-lúc-cần |
| **Desirable difficulties** | Bjork (1994) | Mục 0 bắt *đoán trước* khi học | Sai lúc đầu → nhớ lâu hơn |
| **Test-enhanced + feedback tức thì** | — | Code chạy `dotnet run` cho pass/fail <10s | Vòng lặp phản hồi cực ngắn = học nhanh |
| **Dual coding** (chữ + hình) | Paivio; Mayer | Mỗi khái niệm cốt lõi kèm 1 sơ đồ mermaid | Hai kênh mã hoá, nhớ tốt hơn |
| **Project-based learning** | — | Một dự án TaskFlow lớn dần xuyên P1→P5 | Kiến thức gắn ngữ cảnh, có động lực |
| **Sửa quan niệm sai chủ động** | Chi (2008) | Khối `!!! danger "Huyền thoại cần gỡ"` | Bắt trúng lỗi kinh điển (vd "value type = stack") |

## Cách sư phạm này tạo ra "cân bằng tốc độ ↔ chất lượng"

- **Nhanh:** vòng phản hồi <10s (chạy code), fast-path chỉ ~30 node, AI nháp 70% nội dung, worked-example giảm tải người mới.
- **Chắc:** retrieval + spacing + interleaving là *bộ ba* được chứng minh tạo trí nhớ dài hạn; mastery-gating chặn nợ kiến thức; sửa-misconception ngăn học sai từ gốc.
- **Cân bằng được cưỡng chế:** deep-dive không bao giờ chặn tiến độ (bảo vệ tốc độ); nhưng mọi trang CORE phải qua CI + người kiểm sư phạm (bảo vệ chất lượng). Khi xung đột → đóng băng tốc độ đến khi xanh.

## Điều một cỗ máy KHÔNG làm thay được

CI chứng minh code *compile* và dữ kiện *có nguồn*; nó **không** chứng minh lời giảng *đúng mô hình tư duy* hay *dễ hiểu cho người mới*. Vì thế mỗi trang CORE vẫn cần **một người giỏi tiếng Việt + .NET** đọc theo checklist: *đúng mô hình? đúng thứ tự? người mới hiểu được? an toàn mặc định?* Đây là nút cổ chai thật, và phạm vi (12 chương lõi) được định cỡ quanh nó — không giấu sau khẩu hiệu "AI review".
