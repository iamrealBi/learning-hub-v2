---
# === BẮT BUỘC (CI: scripts/naming_lint.py + front-matter schema kiểm) ===
tier: core            # core | edge
status: draft         # draft | core | edge  (draft = nav-stub 'sắp có')
owner: core-team      # ai chịu trách nhiệm; T3 phải là security-expert/ai-expert
verified_on: "YYYY-MM-DD"
dotnet_version: "10.0"
bloom: "Apply"        # động từ Bloom cho mục tiêu: Remember/Understand/Apply/Analyze/Evaluate/Create
requires: []          # danh sách node-id cần học trước (DAG)
est_minutes_fast: 20
# concept_owner: <slug>   # BẬT nếu đây là trang canonical duy nhất cho một khái niệm
# risk_tier: T3           # BẬT cho bảo mật / model-fact → cần expert ký
---

# <Tên chương ngắn gọn>

<!--
KHUNG SƯ PHẠM BẮT BUỘC — mỗi mục dưới đây là một biện pháp học tập có căn cứ.
Xoá phần chú thích khi viết thật. Xem PEDAGOGY.md để biết vì sao.
-->

!!! info "Bạn đang ở đây · <Pha> → node `<id>`"
    **Cần trước:** [<node>](…)  ·  **Mở khoá sau:** <node kế>  ·  ⏱️ Fast ~N phút

> **Mục tiêu (đo được):** Sau bài này bạn <ĐỘNG TỪ BLOOM> được <kết quả quan sát được>.

## 0. Kiểm tra trước / dự đoán (30s)  ← *desirable difficulty*
<!-- Một câu hỏi/đoạn code để học viên ĐOÁN trước khi học. Sai lúc này = nhớ lâu hơn. -->

## 1. Ý niệm cốt lõi  ← *dual coding: chữ + 1 sơ đồ mermaid*
<!-- Ngắn gọn ≤1200 từ cho fast-path. Nêu 'huyền thoại/misconception' nếu có, trong khối !!! danger -->

## 2. Ví dụ mẫu (worked example) — CHẠY ĐƯỢC  ← *worked-example effect*
```csharp title="vi_du.cs"
// test:run          ← CI trích & chạy; đổi thành test:compile / test:skip(reason)
```
<!-- Kèm output kỳ vọng để học viên tự đối chiếu. Mọi code phải qua CI. -->

## 3. Bài tập có giàn giáo (điền chỗ trống)  ← *scaffolding, faded*
<!-- L1: điền chỗ trống. Lời giải trong khối ??? có giải thích 'vì sao'. -->

## 4. (Tuỳ chương) Cạm bẫy / hiệu năng / bảo mật

## 5. Tự kiểm tra (retrieval practice)  ← *test-enhanced learning*
<!-- 3–5 câu; đáp án CO-LOCATED trong ??? ; ít nhất 1 câu có code chạy được.
     CI (qa_lint.py) FAIL nếu thiếu đáp án. -->
!!! tip "Ôn cách quãng (spaced repetition)"
    <!-- Trỏ tới bộ ôn Leitner + bài Review cuối pha (interleaving). -->

## 6. Thử thách độc lập (đã gỡ giàn giáo)  ← *deliberate practice*
<!-- Chỉ spec + tiêu chí chấp nhận; học viên tự thiết kế + viết test. -->

??? abstract "🔬 DEEP DIVE (tuỳ chọn) — không nằm trên fast path"
    <!-- Nội bộ/edge-case/perf. Bỏ qua vẫn làm được việc. -->

<!-- Dùng {{ dotnet.current }}, {{ csharp.version }}, {{ model('opus').id }} — KHÔNG viết version literal. -->
**Tiếp theo →** [<node kế>](…)
