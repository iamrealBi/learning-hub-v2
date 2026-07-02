# Learning Hub v2 — Fullstack .NET & AI

Bộ tài liệu học **được thiết kế lại từ đầu** để cân bằng **tốc độ học ↔ chất lượng đầu ra**, và là **liều thuốc trực tiếp** cho từng lỗi tìm thấy khi audit bản cũ (build hỏng, 51 link gãy, sản phẩm bịa "Antigravity IDE", lỗi thời .NET 8, dạy code mất an toàn, trùng lặp, Q&A thiếu đáp án).

> ⚖️ **Cam kết trung thực:** không ai master fullstack .NET+AI từ zero trong 2 ngày.
> Sản phẩm này cho **2 tốc độ trên cùng một nội dung**: **Fast Path 2 ngày → làm được việc thật**, và **Mastery 6–8 tuần** (ôn cách quãng) → **chắc & sâu**. Xem `docs/FAST-PATH-2-NGAY.md`.

## Triết lý một câu

**Chất lượng là cái máy CI chặn-merge, không phải lời hứa. Tốc độ đến từ vòng lặp phản hồi <10s + phạm vi nhỏ có kỷ luật. Khi xung đột → đóng băng tốc độ đến khi xanh (quality wins ties).**

## Cấu trúc

```
learning-hub-v2/
├── data/facts.yml          # NGUỒN SỰ THẬT: version, model ID, allowlist, banned (chống lỗi thời)
├── data/questions.yml      # Q&A có schema (mọi câu PHẢI có đáp án)
├── curriculum/curriculum.yml  # SPINE: 1 trục học, DAG prerequisite, tier, canonical-owner
├── docs/                   # 20 bài CORE (24 trang) — trọn lộ trình zero→senior
│   ├── index.md · FAST-PATH-2-NGAY.md · PEDAGOGY.md
│   ├── 00-thiet-lap/       # P0 · zero → bài xanh đầu tiên
│   ├── p1-csharp/          # P1 · nen-tang, bo-nho, oop, collections-linq, async-await, exceptions
│   ├── p2-du-lieu/         # P2 · sql-nen-tang, joins-aggregation, ef-core
│   ├── p3-web-api/         # P3 · minimal-api, dependency-injection, validation
│   ├── p4-bao-mat/         # P4 · jwt, tai-file-an-toan, testing, logging-exceptions, deploy-docker
│   └── p5-ai/              # P5 · claude-code, mcp, capstone (TaskFlow đầu-cuối)
├── templates/chuong-template.md   # khung sư phạm bắt buộc cho mọi chương
├── scripts/                # CÁC GATE (biến chất lượng thành thứ cưỡng chế)
├── tests/fixtures/         # input-xấu để gate_selftest chứng minh gate hoạt động
└── .github/workflows/ci.yml
```

## Cỗ máy chất lượng (bộ Tier-1 chạy mỗi PR)

| Gate | Script | Bắt lỗi bản cũ nào |
|---|---|---|
| 0 · Self-test | `gate_selftest.py` | Chứng minh gate thật sự chạy (khác "AI reviewer" giả) |
| 1 · Nav | `nav_audit.py` | 26 trang mồ côi, 51 nav gãy |
| 2 · Đặt tên | `naming_lint.py` | 5 kiểu tên lẫn lộn |
| 3 · Chống lỗi thời/bịa | `banned_terms.py` | "Antigravity IDE", ".NET 8 = mới nhất", "Claude 3.5 Sonnet" |
| 4 · Q&A | `qa_lint.py` | 35/55 câu không đáp án |
| 5 · Trích code | `tangle.py` | Code không được kiểm chứng |
| 5b · Macro-safety | `macro_safety.py` | `{{`/`}}` trong code (vd escape brace C#) làm vỡ build macro |
| 6 · Build strict | `mkdocs build --strict` | Config mermaid hỏng → site không deploy |
| 7 · Compile C# | `verify_dotnet.sh` | Code sai/API bịa ("value type=stack", hook JSON sai) |

**Không xanh hết = không merge.** Deploy chỉ chạy sau khi cả 2 job xanh.

## Chạy thử tại máy

```bash
cd learning-hub-v2
pip install -r requirements.txt

# chạy toàn bộ gate (trừ dotnet):
python scripts/gate_selftest.py
python scripts/nav_audit.py
python scripts/naming_lint.py
python scripts/banned_terms.py docs
python scripts/qa_lint.py
python scripts/tangle.py

# xem site:
mkdocs serve      # http://127.0.0.1:8000
```

## Thêm một chương mới

1. `cp templates/chuong-template.md docs/<pha>/<ten-kebab>.md` và điền front-matter.
2. Thêm node vào `curriculum/curriculum.yml` (id, requires, tier, owner).
3. Thêm vào `nav` của `mkdocs.yml` (nếu không, Gate 1 sẽ báo mồ côi).
4. Mọi block ```csharp phải có tag `// test:run|compile|skip`.
5. Câu hỏi → thêm vào `data/questions.yml` (phải có `answer`).
6. Version/model → dùng macro `{{ dotnet.current }}`… KHÔNG viết literal (Gate 3 chặn).
7. Mở PR → CI phải xanh → **một người giỏi tiếng Việt + .NET đọc kiểm sư phạm** (cái máy không thay được) → merge.

## Vì sao thiết kế này (từ audit + phản biện đa góc nhìn)

- **Một trục học** thay 4 track chồng chéo → hết "học cái nào?" và hết trùng.
- **SSOT mỗi khái niệm** (JWT một trang) → sửa 1 chỗ, không drift.
- **facts.yml** → cập nhật .NET/model = sửa 1 dòng, không lục 81 chương.
- **Fast/Deep hai làn** → deep-dive không chặn tiến độ (bảo vệ tốc độ).
- **Ship spine 12 chương xanh trước**, không sinh ồ ạt (bài học lớn nhất: volume ≠ progress).
- **Con người** dồn vào chỗ máy không làm được: đúng sư phạm + chất lượng tiếng Việt + bảo mật.

Chi tiết kiến trúc sư phạm: `docs/PEDAGOGY.md`.
