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
| **Spaced repetition** (ôn cách quãng) | Ebbinghaus; Cepeda (2006) | [Quiz tự chấm](on-tap.md): rút ngẫu nhiên N câu (5/10/20) từ toàn bộ 78 chương mỗi lần mở lại — cơ chế nhẹ (không lên lịch tự động theo khoảng ngày như Leitner box thật), người học tự chọn quay lại | Chống quên; tốn ít giờ hơn nhồi |
| **Interleaving** (trộn chủ đề) | Rohrer (2012) | [Quiz tự chấm](on-tap.md) rút câu hỏi trộn giữa các chương khi chọn "toàn bộ chương trình" | Phân biệt khái niệm tốt hơn |
| **Worked-example effect** | Sweller & Cooper (1985) | Mục 2 luôn có ví dụ mẫu chạy được kèm output | Giảm tải nhận thức khi mới học |
| **Faded scaffolding** (gỡ giàn giáo dần) | Renkl & Atkinson (2003) | L1 điền chỗ trống → L2 có test sẵn → L3 chỉ spec | Xây năng lực độc lập, không phụ thuộc copy |
| **Cognitive load theory** | Sweller | Fast-path ≤1200 từ; deep-dive gập lại | Không nhồi; lý thuyết đúng-lúc-cần |
| **Desirable difficulties** | Bjork (1994) | Mục 0 bắt *đoán trước* khi học | Sai lúc đầu → nhớ lâu hơn |
| **Test-enhanced + feedback tức thì** | — | Code chạy `dotnet run` cho pass/fail <10s | Vòng lặp phản hồi cực ngắn = học nhanh |
| **Dual coding** (chữ + hình) | Paivio; Mayer | Mỗi khái niệm cốt lõi kèm 1 sơ đồ mermaid | Hai kênh mã hoá, nhớ tốt hơn |
| **Project-based learning** | — | Một dự án TaskFlow lớn dần xuyên P1→Capstone cuối cùng (P5: capstone trung gian API-only; capstone cuối: thêm kiến trúc/Blazor/production/CI-CD từ P6-P10) | Kiến thức gắn ngữ cảnh, có động lực |
| **Sửa quan niệm sai chủ động** | Chi (2008) | Khối `!!! danger "Huyền thoại cần gỡ"` | Bắt trúng lỗi kinh điển (vd "value type = stack") |

## Cách sư phạm này tạo ra "cân bằng tốc độ ↔ chất lượng"

- **Nhanh:** vòng phản hồi <10s (chạy code); [Fast Path 2 ngày](FAST-PATH-2-NGAY.md) chọn tay 13 chương lõi nhất trong tổng 78 để "làm được việc thật" sớm (tag `tier: fast` trong `curriculum/curriculum.yml` hiện đánh dấu toàn bộ 78 chương là core — không còn phân biệt fast/deep sau khi chương trình mở rộng từ bản vertical-slice ban đầu; Fast Path dùng danh sách chọn tay riêng, không dựa vào tag này); AI nháp phần lớn nội dung, worked-example giảm tải người mới.
- **Chắc:** retrieval + spacing + interleaving là *bộ ba* được chứng minh tạo trí nhớ dài hạn; mastery-gating chặn nợ kiến thức; sửa-misconception ngăn học sai từ gốc.
- **Cân bằng được cưỡng chế:** deep-dive không bao giờ chặn tiến độ (bảo vệ tốc độ); nhưng mọi trang CORE phải qua CI + người kiểm sư phạm (bảo vệ chất lượng). Khi xung đột → đóng băng tốc độ đến khi xanh.

## Điều một cỗ máy KHÔNG làm thay được

CI chứng minh code *compile* và dữ kiện *có nguồn*; nó **không** chứng minh lời giảng *đúng mô hình tư duy* hay *dễ hiểu cho người mới*. Vì thế mỗi trang CORE vẫn cần **một người giỏi tiếng Việt + .NET** đọc theo checklist: *đúng mô hình? đúng thứ tự? người mới hiểu được? an toàn mặc định?* Đây là nút cổ chai thật, và phạm vi (12 phase, 78 chương) được định cỡ quanh nó — không giấu sau khẩu hiệu "AI review".
