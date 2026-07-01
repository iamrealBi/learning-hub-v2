---
hide:
  - navigation
---

# Learning Hub v2 — Fullstack .NET & AI

Một **trục học duy nhất** (không phải nhiều track chồng chéo), mỗi trang được **CI kiểm chứng** (build được, code compile được, câu hỏi có đáp án, không lỗi thời, không bịa). Hiện hành: **.NET {{ dotnet.current }} / C# {{ csharp.version }}**, PostgreSQL {{ postgres.current }}.

!!! warning "Cam kết trung thực về thời gian học"
    Không ai đi từ zero đến *master* fullstack .NET + AI trong 2 ngày — khoa học học tập (gợi nhớ cách quãng, luyện tập có chủ đích) không cho phép, và hứa điều đó là **chỗ chê** lớn nhất. Cái sản phẩm này **bảo đảm được**:

    - **Fast Path 2 ngày** → *làm được việc thật*: hiểu lõi + ship một API chạy được. Xem [Kế hoạch 2 ngày](FAST-PATH-2-NGAY.md).
    - **Lộ trình Mastery (6–8 tuần)** → *chắc & sâu*, cùng nội dung nhưng ôn theo lịch cách quãng.

    Cùng một sản phẩm, **hai tốc độ**. Bạn chọn.

## Bắt đầu

<div class="grid cards" markdown>

-   :material-rocket-launch: **Fast Path — 2 ngày**

    ---
    Lõi tối thiểu để ship được một app. Bỏ qua mọi deep-dive.

    [:octicons-arrow-right-24: Kế hoạch 2 ngày](FAST-PATH-2-NGAY.md)

-   :material-cog: **P0 · Thiết lập**

    ---
    Zero → chạy được bài tập "xanh" đầu tiên trong <30 phút.

    [:octicons-arrow-right-24: Thiết lập](00-thiet-lap/index.md)

-   :material-star: **Xem một chương CORE mẫu**

    ---
    Bộ nhớ & Kiểu dữ liệu — chuẩn sư phạm + kỹ thuật của toàn hub.

    [:octicons-arrow-right-24: Value vs Reference](p1-csharp/bo-nho-va-kieu-du-lieu.md)

-   :material-school: **Vì sao học được nhanh mà chắc?**

    ---
    Kiến trúc sư phạm áp dụng (mastery, retrieval, spacing…).

    [:octicons-arrow-right-24: PEDAGOGY](PEDAGOGY.md)

</div>

## Trục học (spine)

`P0 Thiết lập → P1 C# → P2 SQL/EF Core → P3 Web API → P4 Auth/Bảo mật/Test/Deploy → P5 AI Engineering → Capstone`

Mỗi khái niệm có **đúng một trang canonical**; xây trên **một dự án lớn dần (TaskFlow)**. Chi tiết trong `curriculum/curriculum.yml`.

---
*Chất lượng là cái máy CI, không phải lời hứa. Xem `.github/workflows/ci.yml`.*
