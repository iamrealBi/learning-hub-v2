---
tier: core
status: core
owner: core-team
verified_on: "2026-07-05"
dotnet_version: "10.0"
bloom: áp dụng
requires: [p8-cors]
est_minutes_fast: 24
---

# CI/CD với GitHub Actions

!!! info "bạn đang ở đây"
    cần trước: bạn đã biết CORS và security header là các cơ chế bảo vệ phía trình duyệt cho một API đã deploy (chương CORS & Security Headers) — chương đó giả định API "đã chạy ở đâu đó". Chương này lùi lại một bước, trả lời câu hỏi: làm sao code của bạn **tự động** được kiểm tra và đưa lên chỗ chạy đó, mỗi khi bạn `git push`, mà không cần tự tay build/test/deploy thủ công.
    mở khoá: sau chương này bạn hiểu đúng CI là gì, CD là gì, và hai khái niệm đó khác nhau ở đâu (lỗi nhập nhằng rất phổ biến), đọc được cấu trúc workflow/job/step/trigger trong một file `.yml`, và đọc hiểu được **chính file CI thật** (`.github/workflows/ci.yml`) đang chạy trên repo Learning Hub bạn đang học — không phải ví dụ bịa, mà là cỗ máy thật đang gác mọi lần merge vào repo này.

> **Mục tiêu (đo được):** sau chương này bạn **định nghĩa** đúng và **phân biệt** được CI với CD, **đọc** được cấu trúc workflow/job/step/trigger của GitHub Actions, **giải thích** được vì sao job `deploy` trong file CI thật của Learning Hub cần `needs: [gates, dotnet]` để chặn deploy khi có lỗi, và **nhận diện** được mục đích của `permissions: contents: write` trong job đó.
>
> Chương này không dạy bạn viết YAML từ số 0 theo kiểu liệt kê hết cú pháp — trọng tâm là hiểu đúng **bản chất** của CI/CD (hai khái niệm khác nhau, hay bị gộp lẫn) và đọc hiểu một workflow thật đang chạy, để khi mở file `.github/workflows/ci.yml` của bất kỳ repo nào khác, bạn biết mình đang nhìn vào cái gì.

---

## 0. Đoán nhanh trước khi học

Hai bạn cùng làm một dự án ASP.NET Core. Bạn A sửa file `OrderService.cs`, chạy `dotnet build` trên máy mình — xanh, không lỗi. Bạn B (cùng lúc, không biết bạn A đang sửa gì) sửa file `OrderController.cs` gọi tới một method trong `OrderService.cs`, cũng `dotnet build` trên máy mình — xanh, không lỗi. Cả hai đều tự tin `git push`. Ngay sau khi B merge code của A và code của mình lại, dự án **không còn build được nữa** — nhưng cả A và B đều đã thấy "xanh" trên máy riêng của họ trước đó.

??? question "Đoán trước, đáp án ở dưới"
    Gợi ý: "build xanh trên máy A" và "build xanh trên máy B" là hai phép kiểm tra **riêng biệt**, trên hai bản code **khác nhau** (mỗi người chỉ có code của chính mình). Vậy ai, và ở đâu, thực sự kiểm tra bản code **sau khi đã ghép** cả hai lại?

??? note "Đáp án"
    Không ai kiểm tra bản code đã ghép — cho tới khi có người (thường là người merge cuối, hoặc tệ hơn, hệ thống deploy production) chạy build lần đầu tiên trên bản đã ghép. Đây chính là vấn đề gốc mà CI (mục 1) được sinh ra để giải quyết: mỗi lần có code mới được đẩy lên (`push`) hoặc đề xuất ghép (`pull_request`), một máy chủ trung lập tự động lấy đúng bản code sẽ được ghép, build và test **bản đó**, rồi báo kết quả trước khi ai được phép merge. A và B không cần "nhớ" phải test cùng nhau — máy làm việc đó tự động, sớm, và trên đúng bản sẽ tồn tại sau khi merge. Mục 1 định nghĩa chính xác CI; mục 5 chỉ ra đúng chỗ máy đó chạy trong file CI thật của Learning Hub.

---

## 1. CI (Continuous Integration) là gì: tự động build/test mỗi lần push, phát hiện lỗi SỚM

**Định nghĩa:** CI (Continuous Integration — tích hợp liên tục) là thực hành **tự động build và chạy test mỗi lần có code mới được đẩy lên** (push hoặc đề xuất merge qua pull request), nhằm phát hiện lỗi **sớm** — ngay tại thời điểm code được đẩy lên, chứ không phải đợi tới lúc merge xong hoặc tệ hơn, tới lúc deploy lên production rồi mới phát hiện.

Quay lại ví dụ ở mục 0: nếu có CI, ngay khi bạn B mở pull request để merge code của mình vào nhánh chứa code của A, một máy chủ tự động (không phải máy của A, không phải máy của B) lấy đúng bản code đã ghép, chạy `dotnet build` trên **bản ghép đó**. Nếu lỗi (như tình huống ở mục 0), CI báo đỏ ngay trên pull request — trước khi B bấm nút merge, chứ không phải sau. Đây là khác biệt cốt lõi: CI không ngăn được A hoặc B viết code có lỗi tương thích, nhưng nó đảm bảo **không ai cần phải tự nhớ** kiểm tra bản ghép — máy làm việc đó tự động và sớm hơn con người có thể làm bằng tay.

**Điều gì xảy ra khi KHÔNG có CI (hậu quả vận hành cụ thể):** không có bước tự động kiểm tra bản code đã ghép, lỗi kiểu mục 0 chỉ được phát hiện khi có người tình cờ chạy build trên bản mới nhất — có thể là một lập trình viên thứ ba vài ngày sau, hoặc tệ nhất, hệ thống deploy production khi cố build để lên bản mới và build fail giữa quy trình deploy. Ở quy mô một dự án chỉ 2 người, hậu quả là mất vài giờ debug xem "ai làm hỏng cái gì". Ở quy mô một team 10-20 người push code nhiều lần mỗi ngày, không có CI đồng nghĩa nhánh chính (`main`) thường xuyên ở trạng thái "không chắc có build được không" — không ai dám deploy ngay vì không biết bản hiện tại có lỗi ẩn nào chưa lộ ra.

```mermaid title="CI: kiem tra ban da ghep, ngay khi co pull request, truoc khi merge"
sequenceDiagram
    participant A as Lap trinh vien A
    participant B as Lap trinh vien B
    participant GH as GitHub
    participant CI as May CI (tu dong)

    A->>GH: push code A vao nhanh feature-A
    B->>GH: mo pull request: merge feature-B vao main
    GH->>CI: kich hoat CI tren ban DA GHEP (feature-B + main hien tai)
    CI->>CI: chay dotnet build + test tren ban ghep
    CI--xGH: BAO DO - build loi tren ban ghep (du A, B deu xanh rieng le)
    GH->>B: chan nut merge, hien thi loi CI ngay tren pull request
```

**So sánh với việc tự chạy `dotnet build` thủ công trên máy cá nhân:** chạy build trên máy riêng vẫn hữu ích (phát hiện lỗi cú pháp cơ bản sớm nhất có thể), nhưng nó **không** thay thế được CI vì hai lý do: (1) máy cá nhân chỉ có code của riêng người đó, không có code mới nhất từ đồng nghiệp khác đang được merge cùng lúc; (2) không ai đảm bảo mọi lập trình viên đều thực sự chạy đủ build/test trước khi push — con người quên, vội, hoặc bỏ qua bước đó khi deadline gấp. CI chạy trên một máy chủ trung lập, **không thể bị bỏ qua bằng cách quên**, vì nó tự động kích hoạt bởi chính hành động push/pull request, không phụ thuộc vào việc con người có nhớ chạy hay không.

---

## 2. CD (Continuous Deployment/Delivery) là gì: tự động deploy SAU KHI CI xanh — khác CI, không phải cùng một việc

**Định nghĩa:** CD (Continuous Deployment hoặc Continuous Delivery — triển khai liên tục) là thực hành **tự động đưa code lên môi trường chạy thật** (staging hoặc production) **sau khi** các bước kiểm tra CI đã báo xanh — CD chỉ chạy nếu CI đã thành công, và CD giải quyết một bài toán **khác hẳn** CI: CI hỏi "code này có build/test đúng không?", CD hỏi "code đã được xác nhận đúng này có nên được đưa lên chạy thật ngay bây giờ không, và bằng cách nào?".

Đây là điểm dễ nhầm lẫn nhất của toàn chương, cần khắc đúng ngay: **CI và CD là hai khái niệm khác nhau, giải quyết hai bài toán khác nhau, dù thường được viết liền thành "CI/CD" và đôi khi nằm trong cùng một file cấu hình.** Một dự án hoàn toàn có thể có CI mà **không có** CD (build/test tự động, nhưng deploy vẫn làm tay — ví dụ một người kỹ sư vận hành tự SSH vào server và chạy lệnh deploy sau khi thấy CI xanh). Ngược lại, một dự án có CD mà không CI đúng nghĩa là rất nguy hiểm — tự động đẩy code lên production mà không có bước kiểm tra nào trước, bất kỳ lỗi cú pháp nhỏ cũng lập tức thành sự cố thật.

**Điều gì xảy ra khi nhầm CI với CD (hậu quả cụ thể):** một lỗi phổ biến ở người mới là nghĩ "CI đã chạy nghĩa là code đã lên production rồi" — thực tế CI chỉ trả lời "code có build/test được không", nó **không tự động đưa code đi đâu cả** trừ khi có một job CD riêng được viết thêm và được cấu hình chạy sau khi CI xanh. Ngược lại, một lỗi khác là tưởng "cứ push code, không cần chờ CI xanh, vì có CD lo deploy" — nếu hệ thống CD được thiết kế đúng (như job `deploy` trong ví dụ mục 5 dưới đây), nó sẽ **không** chạy nếu CI báo lỗi; nhưng nếu ai đó cấu hình CD tách rời, không phụ thuộc kết quả CI, code lỗi vẫn có thể bị đẩy thẳng lên production — đây là lỗi cấu hình nghiêm trọng, không phải bản chất của CD.

Bảng phân biệt CI và CD, mỗi khái niệm trả lời một câu hỏi khác nhau:

| Khái niệm | Câu hỏi trả lời | Chạy khi nào | Ví dụ hành động cụ thể |
|---|---|---|---|
| CI (Continuous Integration) | "Code này có build/test đúng không?" | Mỗi lần `push` hoặc mở `pull_request` | `dotnet build`, chạy các script kiểm tra (như job `gates`, mục 5), build site tài liệu |
| CD (Continuous Deployment/Delivery) | "Code đã xác nhận đúng có nên đưa lên chạy thật không, bằng cách nào?" | Sau khi CI xanh, thường chỉ trên nhánh chính (ví dụ `main`) | `mkdocs gh-deploy --force` (job `deploy`, mục 5), publish site tài liệu, deploy API lên cloud |

Một cách nhớ ngắn: **CI đứng trước, hỏi "có đúng không"; CD đứng sau, hỏi "có nên đưa lên không" — và CD chỉ nên hỏi câu đó khi CI đã trả lời "đúng" rồi.**

---

## 3. GitHub Actions: workflow, job, step — ba tầng cấu trúc của một file tự động hoá

**Định nghĩa:** GitHub Actions là công cụ tự động hoá **có sẵn** trong GitHub, cho phép bạn định nghĩa các bước tự động (build, test, deploy...) bằng file YAML đặt trong thư mục `.github/workflows/` của repo — mỗi file `.yml` trong thư mục này là một **workflow** (quy trình tự động), tự chạy trên máy ảo của GitHub mỗi khi một **trigger** (sự kiện kích hoạt, mục 4) xảy ra.

Ba khái niệm lồng nhau, từ lớn tới nhỏ, cần phân biệt rõ:

1. **Workflow** (quy trình): là **toàn bộ một file `.yml`** — ví dụ file `.github/workflows/ci.yml` của Learning Hub là một workflow, có tên khai báo ở dòng `name:` đầu file. Một repo có thể có nhiều workflow (nhiều file `.yml` khác nhau trong `.github/workflows/`), mỗi workflow phục vụ một mục đích riêng (ví dụ một workflow cho CI, một workflow khác cho việc tự động đóng issue cũ).
2. **Job** (công việc): mỗi workflow chứa **một hoặc nhiều job**, khai báo dưới mục `jobs:`. Mỗi job chạy trên **một máy ảo riêng biệt** (khai báo qua `runs-on: ubuntu-latest` — nghĩa là máy ảo chạy hệ điều hành Ubuntu Linux) — các job trong cùng workflow **mặc định chạy song song** (đồng thời, không chờ nhau), trừ khi bạn khai báo tường minh job này phải chờ job khác xong trước (từ khoá `needs:`, xem mục 6).
3. **Step** (bước): mỗi job chứa **một danh sách các step** chạy **tuần tự** (bước sau chỉ chạy khi bước trước xong) trên cùng một máy ảo của job đó — mỗi step là một lệnh cụ thể, ví dụ `run: dotnet build` (chạy một lệnh shell) hoặc `uses: actions/checkout@v4` (dùng lại một hành động có sẵn do GitHub hoặc cộng đồng viết sẵn, ở đây là hành động tải code của repo về máy ảo).

**Điều gì xảy ra khi hiểu sai job vs step:** một lỗi phổ biến của người mới là nghĩ mọi lệnh trong workflow chạy tuần tự trên cùng một máy — thực tế **hai job khác nhau chạy trên hai máy ảo hoàn toàn tách biệt**, không chia sẻ file/biến môi trường với nhau trừ khi bạn tường minh dùng cơ chế "artifact" (tải file lên rồi tải xuống ở job khác) hoặc "output" (job này truyền một giá trị cụ thể cho job kia qua cơ chế riêng). Nếu bạn cài một package ở job A rồi mong job B "đã có sẵn" package đó vì "cùng workflow" — điều đó **không đúng**, job B khởi động một máy ảo hoàn toàn mới, sạch, phải tự cài lại mọi thứ nó cần, đúng như bạn sẽ thấy job `dotnet` trong ví dụ mục 5 tự cài `pip install -r requirements.txt` **lại từ đầu**, dù job `gates` (chạy trên máy ảo khác) đã cài y hệt dependency đó rồi.

---

## 4. Trigger (`on:`): sự kiện nào kích hoạt workflow chạy

**Định nghĩa:** Trigger (khai báo bằng khoá `on:` ở đầu file workflow) là **sự kiện cụ thể** xảy ra trên GitHub khiến workflow **tự động bắt đầu chạy** — không có trigger khớp, workflow không bao giờ tự chạy (bạn vẫn có thể chạy tay qua giao diện GitHub với trigger đặc biệt `workflow_dispatch`, nhưng đó nằm ngoài phạm vi chương này).

Hai trigger phổ biến nhất, cả hai đều xuất hiện trong file CI thật của Learning Hub:

- **`push`:** kích hoạt workflow ngay khi có commit mới được đẩy (`git push`) lên một nhánh khớp điều kiện khai báo. Ví dụ `push: { branches: [main] }` nghĩa là chỉ kích hoạt khi push **thẳng vào** nhánh `main` (không phải mọi nhánh trong repo).
- **`pull_request`:** kích hoạt workflow khi có pull request được mở hoặc cập nhật, nhắm tới một nhánh khớp điều kiện khai báo. Ví dụ `pull_request: { branches: [main] }` nghĩa là kích hoạt mỗi khi có pull request đề xuất merge **vào** nhánh `main` — đây chính là trigger giải quyết đúng tình huống mục 0 (bạn B mở pull request, CI tự chạy trên bản đã ghép **trước khi** B bấm merge).

**Điều gì xảy ra khi khai báo trigger sai:** nếu bạn chỉ khai báo `on: push` mà quên `pull_request`, CI sẽ **không** chạy khi có ai mở pull request — nghĩa là đúng tình huống nguy hiểm nhất ở mục 0 (kiểm tra bản code đã ghép **trước khi** merge) lại **không** được CI bảo vệ; CI chỉ chạy **sau khi** code đã push thẳng vào nhánh, tức là sau khi lỗi đã lỡ vào `main` rồi mới phát hiện — quá muộn so với mục đích "phát hiện sớm" của CI (mục 1). Đây là lý do file CI thật của Learning Hub khai báo **cả hai** trigger cùng lúc, nhắm cùng nhánh `main`.

```yaml title=".github/workflows/ci.yml — trigger thuc te cua Learning Hub"
name: CI - Cong chat luong (chan merge)
on:
  push: { branches: [main] }
  pull_request: { branches: [main] }
```

Đọc đúng hai dòng trên: workflow này tự chạy trong **hai tình huống** — (1) có ai push thẳng vào `main` (hiếm, thường chỉ xảy ra sau khi đã merge), và (2) có ai mở hoặc cập nhật pull request nhắm merge vào `main` (tình huống phổ biến nhất, xảy ra mỗi lần có người đề xuất thay đổi). Cả hai trigger dùng cùng cú pháp `{ branches: [main] }` — giới hạn chỉ nhánh `main`, không kích hoạt cho các nhánh khác dù có push/pull request tới đó.

---

## 5. Đọc file CI thật của Learning Hub: ba job `gates`, `dotnet`, `deploy`

Phần này không giới thiệu khái niệm mới — áp dụng đúng ba khái niệm workflow/job/step (mục 3) và trigger (mục 4) đã học vào **chính file** `.github/workflows/ci.yml` đang chạy thật trên repo Learning Hub bạn đang học. Đây là cơ hội hiếm để đọc một CI **thật** đang gác merge, không phải ví dụ tưởng tượng.

File này định nghĩa **một workflow** (tên `CI - Cong chat luong (chan merge)`), chứa **ba job**: `gates`, `dotnet`, và `deploy`. Ba job này chạy trên ba máy ảo riêng biệt (mục 3 đã giải thích job không chia sẻ máy ảo với nhau).

```yaml title=".github/workflows/ci.yml — job gates (rut gon)"
jobs:
  gates:
    name: Gate cau truc + noi dung + build
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with: { python-version: "3.12", cache: pip }
      - run: pip install -r requirements.txt
      - run: python scripts/gate_selftest.py
      - run: python scripts/nav_audit.py
      - run: python scripts/naming_lint.py
      - run: python scripts/banned_terms.py docs
      - run: python scripts/qa_lint.py
      - run: python scripts/tangle.py
      - run: python scripts/macro_safety.py docs
      - run: mkdocs build --strict
```

**Job `gates` làm gì:** đây là job kiểm tra **cấu trúc và nội dung** của toàn bộ tài liệu — mỗi `run:` là một step riêng, chạy tuần tự trên cùng một máy ảo Ubuntu. Đọc từ trên xuống: tải code repo về (`actions/checkout@v4`), cài Python 3.12, cài các thư viện Python cần thiết, rồi chạy lần lượt từng script kiểm tra (nav không mồ côi, tên file nhất quán, không thuật ngữ cấm/lỗi thời, câu hỏi có đủ đáp án, trích code block đúng, không vỡ macro-syntax), cuối cùng build toàn bộ site tài liệu bằng `mkdocs build --strict` (chế độ nghiêm — bất kỳ link nội bộ gãy cũng khiến bước này fail, không chỉ cảnh báo). Nếu **bất kỳ** step nào trong danh sách trên fail (trả về mã lỗi khác 0), toàn bộ job `gates` được đánh dấu đỏ — các step **sau** step lỗi trong cùng job sẽ không chạy tiếp (tuần tự, dừng lại ngay khi gặp lỗi, theo mặc định của GitHub Actions).

```yaml title=".github/workflows/ci.yml — job dotnet (rut gon)"
  dotnet:
    name: Compile/chay moi code C#
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with: { python-version: "3.12" }
      - run: pip install -r requirements.txt
      - uses: actions/setup-dotnet@v4
        with: { dotnet-version: "10.0.x" }
      - run: python scripts/tangle.py
      - run: bash scripts/verify_dotnet.sh
```

**Job `dotnet` làm gì:** job này chạy trên một máy ảo **khác hẳn** máy ảo của job `gates` (dù cũng là `ubuntu-latest`) — vì vậy nó phải tự `checkout` code, tự cài Python, tự `pip install` lại **từ đầu**, đúng như mục 3 đã nhấn mạnh (không có gì được "chia sẻ" tự động giữa hai job). Sau đó nó cài thêm .NET SDK (`actions/setup-dotnet@v4`) — thứ job `gates` không cần vì job đó không compile C#. Step `python scripts/tangle.py` trích xuất các đoạn code C# từ tài liệu Markdown ra thành file thật; step cuối `bash scripts/verify_dotnet.sh` thực sự **build/chạy** từng đoạn code đó bằng .NET SDK — nếu một chương tài liệu nào đó chứa code C# bịa (gọi method không tồn tại, sai cú pháp), bước này fail, bắt đúng lớp lỗi "tài liệu dạy sai" mà chỉ đọc mắt thường không phát hiện được.

```yaml title=".github/workflows/ci.yml — job deploy (rut gon)"
  deploy:
    needs: [gates, dotnet]
    if: github.ref == 'refs/heads/main'
    runs-on: ubuntu-latest
    permissions: { contents: write }
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with: { python-version: "3.12" }
      - run: pip install -r requirements.txt
      - run: mkdocs gh-deploy --force
```

**Job `deploy` làm gì — đây chính là phần CD (mục 2) của workflow này:** job này chỉ có **một việc** — chạy `mkdocs gh-deploy --force`, lệnh build site tài liệu rồi **đẩy thẳng lên GitHub Pages** (site thật mà bạn đang đọc chương này trên đó, nếu bạn đang xem qua trình duyệt thay vì đọc file Markdown thô). Đây là hành động **đưa lên chạy thật** — đúng định nghĩa CD ở mục 2, khác hẳn hai job `gates`/`dotnet` (chỉ kiểm tra, không đưa gì lên đâu cả).

---

## 6. `needs: [gates, dotnet]`: dependency giữa job — deploy chỉ chạy khi CẢ HAI job trước xanh

**Định nghĩa:** `needs:` là khai báo **thứ tự phụ thuộc** giữa các job trong cùng workflow — job có `needs: [A, B]` sẽ **chờ** cho tới khi cả job `A` và job `B` đều **chạy xong và thành công**, mới bắt đầu chạy; nếu **bất kỳ** job nào trong danh sách `needs` fail, job đang khai báo `needs` đó sẽ **bị bỏ qua hoàn toàn** (không chạy, không tốn thời gian máy ảo), không phải chạy rồi tự fail.

Nhìn lại đúng dòng trong file CI thật: `deploy` khai báo `needs: [gates, dotnet]`. Điều này có nghĩa: job `deploy` (chứa lệnh `mkdocs gh-deploy --force` đẩy site lên thật, mục 5) **chỉ bắt đầu chạy** khi **cả** job `gates` (kiểm tra cấu trúc/nội dung tài liệu) **và** job `dotnet` (compile/chạy mọi code C# trong tài liệu) đều đã báo thành công. Nếu chỉ một trong hai job đó fail — ví dụ `gates` phát hiện một link nội bộ gãy, hoặc `dotnet` phát hiện một đoạn code C# trong tài liệu gọi method bịa không tồn tại — job `deploy` **không chạy**, site cũ vẫn đứng yên trên GitHub Pages, không bị ai vô tình đẩy lên một bản có tài liệu lỗi hoặc code mẫu sai.

```mermaid title="needs: [gates, dotnet] - deploy cho ca hai xanh moi chay"
flowchart LR
    A["Job gates<br/>(kiem tra cau truc + noi dung)"] -->|xanh| D["Job deploy<br/>(mkdocs gh-deploy)"]
    B["Job dotnet<br/>(compile/chay code C#)"] -->|xanh| D
    A -.->|do, fail| X["deploy KHONG chay"]
    B -.->|do, fail| X
```

**Điều gì xảy ra khi KHÔNG có `needs` (hậu quả cụ thể nếu bỏ dòng này):** nếu bạn xoá `needs: [gates, dotnet]` khỏi job `deploy`, ba job `gates`, `dotnet`, `deploy` sẽ **chạy song song ngay từ đầu** (đúng như mục 3 đã nói, mặc định các job không chờ nhau) — nghĩa là `deploy` có thể chạy và **đẩy site lên thật** trong khi `gates` hoặc `dotnet` vẫn đang chạy hoặc thậm chí đã fail, vì `deploy` không hề biết (và không chờ) kết quả của hai job kia. Đây chính xác là lớp lỗi nguy hiểm mà mục 2 đã cảnh báo: "CD chạy mà không phụ thuộc kết quả CI" — code lỗi (tài liệu gãy link, hoặc code mẫu C# bịa không compile được) vẫn có thể bị đẩy thẳng lên site thật đang phục vụ người học, dù chính CI trong cùng workflow đó đã phát hiện ra lỗi (chỉ là báo lỗi **chậm hơn** hoặc **độc lập** với hành động deploy đã lỡ xảy ra).

Điều kiện `if: github.ref == 'refs/heads/main'` đứng cùng dòng với `needs` làm thêm một việc khác: chỉ cho job `deploy` chạy khi workflow được kích hoạt **đúng trên nhánh `main`** (không chạy deploy khi CI chạy vì một pull request từ nhánh khác) — kết hợp với `needs`, job `deploy` có **hai điều kiện phải đều đúng**: (1) đang ở nhánh `main`, và (2) cả `gates` và `dotnet` đã xanh.

---

## 7. `permissions: contents: write`: giới hạn đúng quyền job cần, không hơn

**Định nghĩa:** `permissions:` là khai báo **quyền truy cập** mà job (hoặc toàn workflow) được cấp khi chạy, tính theo nguyên tắc **chỉ cấp đúng quyền cần dùng, không cấp dư** — mặc định GitHub Actions cấp một số quyền hạn chế cho token tự động (`GITHUB_TOKEN`) mà workflow dùng để tương tác với repo; nếu job cần làm một việc vượt quyền mặc định (ví dụ ghi thêm nội dung vào repo), phải khai báo tường minh quyền đó qua `permissions:`.

Trong file CI thật, chỉ job `deploy` có dòng `permissions: { contents: write }` — hai job `gates` và `dotnet` **không** có dòng này, vì chúng chỉ đọc code về để kiểm tra/compile, không cần ghi gì vào repo. Job `deploy` cần quyền `contents: write` (ghi vào nội dung repo) vì lệnh `mkdocs gh-deploy --force` thực chất hoạt động bằng cách **tạo/ghi đè một nhánh riêng** (thường tên `gh-pages`) chứa bản HTML đã build của site tài liệu, rồi push nhánh đó lên repo — đây là hành động **ghi**, không phải chỉ đọc, nên cần quyền `contents: write` được cấp tường minh.

**Điều gì xảy ra khi thiếu `permissions: contents: write`:** nếu job `deploy` thiếu dòng khai báo quyền này (và cấu hình repo không tự cấp quyền ghi mặc định cho `GITHUB_TOKEN`), lệnh `mkdocs gh-deploy --force` sẽ **fail ở đúng bước push nhánh `gh-pages`** với lỗi quyền truy cập bị từ chối (thường dạng `403` hoặc thông báo "permission denied") — mọi step trước đó (checkout, cài Python, build site) có thể chạy hoàn toàn thành công, chỉ riêng bước push cuối cùng thất bại, khiến người mới dễ nhầm là lỗi cấu hình `mkdocs.yml` trong khi nguyên nhân thực chất là thiếu quyền ghi ở tầng workflow.

**Vì sao không khai báo `permissions: write-all` cho gọn:** đúng nguyên tắc "chỉ cấp đúng quyền cần dùng", khai báo quyền rộng hơn cần thiết (ví dụ cấp quyền ghi cho cả `issues`, `pull-requests`... trong khi job chỉ cần ghi `contents`) làm tăng rủi ro nếu có lỗ hổng trong chính script CI hoặc trong một step nào đó — một token có quyền rộng hơn cần thiết, nếu bị lợi dụng (ví dụ qua một dependency Python độc hại được cài ở bước `pip install`), có thể gây thiệt hại rộng hơn phạm vi thực sự cần. Khai báo đúng `contents: write` — không hơn — là ví dụ cụ thể của nguyên tắc bảo mật "least privilege" (đặc quyền tối thiểu) áp dụng vào cấu hình CI/CD.

---

## Cạm bẫy & thực chiến

- **Nhầm CI với CD, nghĩ "CI xanh" nghĩa là "đã lên production":** như mục 2 đã nhấn mạnh, CI chỉ trả lời "code có build/test đúng không" — nó không tự đưa code đi đâu cả trừ khi có job CD riêng (như job `deploy` trong ví dụ) được viết thêm và được cấu hình chạy sau khi CI xanh.
- **Quên trigger `pull_request`, chỉ khai báo `push`:** khiến CI không chạy khi có người mở pull request — mất đúng lớp bảo vệ quan trọng nhất (kiểm tra bản code đã ghép **trước khi** merge, mục 0 và mục 4), CI chỉ phát hiện lỗi **sau khi** code đã lỡ vào nhánh chính.
- **Tưởng hai job trong cùng workflow chia sẻ được file/state với nhau:** mỗi job chạy trên một máy ảo hoàn toàn riêng biệt (mục 3) — cài package ở job A không khiến job B "đã có sẵn" package đó; job B phải tự cài lại từ đầu, đúng như job `dotnet` trong ví dụ tự `pip install` lại dù job `gates` đã làm y hệt.
- **Xoá hoặc quên `needs:` giữa các job có quan hệ phụ thuộc:** không có `needs`, các job chạy song song ngay từ đầu — job deploy có thể chạy trước khi job kiểm tra kịp báo lỗi, đúng lớp lỗi nguy hiểm mục 6 đã minh hoạ (CD không phụ thuộc kết quả CI).
- **Cấp `permissions` rộng hơn cần thiết "cho chắc", ví dụ `write-all`:** vi phạm nguyên tắc đặc quyền tối thiểu — nếu một step nào đó trong job bị lợi dụng (ví dụ qua dependency độc hại), token quyền rộng gây thiệt hại rộng hơn cần thiết. Chỉ khai báo đúng quyền job thực sự cần dùng, như `contents: write` cho job cần ghi nhánh `gh-pages`.
- **Nghĩ workflow chạy y hệt trên máy cá nhân nên không cần lo:** máy ảo CI luôn khởi động **sạch** (không có cache, package, biến môi trường đã cài sẵn trên máy cá nhân của bạn) — một đoạn code "chạy được trên máy tôi" nhưng phụ thuộc ngầm vào một file/biến môi trường chỉ có trên máy cá nhân sẽ fail trên CI, đây là lý do CI vẫn có giá trị phát hiện lỗi dù bạn đã tự test kỹ trên máy mình.
- **Không đọc kỹ điều kiện `if:` đi kèm `needs:`:** hai điều kiện này độc lập nhưng cùng phải đúng — `deploy` trong ví dụ cần **cả** `needs: [gates, dotnet]` xanh **và** `if: github.ref == 'refs/heads/main'` đúng; một pull request từ nhánh khác dù CI xanh vẫn **không** kích hoạt job `deploy`, vì điều kiện nhánh không khớp.

---

## Bài tập

**Bài 1 (áp dụng).** Dựa vào đúng cấu trúc ba job `gates`/`dotnet`/`deploy` của Learning Hub, giải thích: nếu job `gates` fail (ví dụ `mkdocs build --strict` phát hiện một link nội bộ gãy) nhưng job `dotnet` chạy hoàn toàn xanh, job `deploy` có chạy không? Vì sao?

??? success "Lời giải + vì sao"
    Job `deploy` **không chạy**. Dòng `needs: [gates, dotnet]` yêu cầu **cả hai** job trong danh sách phải thành công — chỉ cần một trong hai (ở đây là `gates`) fail, job `deploy` bị bỏ qua hoàn toàn, không chạy dù `dotnet` đã xanh. Đây đúng là mục đích thiết kế của `needs`: đảm bảo site tài liệu thật (đang phục vụ người học) không bị đẩy lên một bản có link nội bộ gãy, dù phần code C# mẫu trong tài liệu hoàn toàn đúng.

**Bài 2 (tìm lỗi).** Một đồng nghiệp viết lại job `deploy` như sau, muốn "deploy nhanh hơn, không cần chờ hai job kiểm tra kia vì thấy chúng chạy lâu". Tìm vấn đề trong cách viết này.

```yaml title="deploy (co van de - rut gon needs)"
deploy:
  if: github.ref == 'refs/heads/main'
  runs-on: ubuntu-latest
  permissions: { contents: write }
  steps:
    - uses: actions/checkout@v4
    - run: mkdocs gh-deploy --force
```

??? success "Lời giải + vì sao"
    Đồng nghiệp đã **xoá `needs: [gates, dotnet]`** — nghĩa là job `deploy` giờ chạy **song song** với `gates` và `dotnet` ngay từ đầu (mặc định các job không chờ nhau, mục 3), không còn phụ thuộc kết quả của hai job kiểm tra kia. Hậu quả: `deploy` có thể đẩy site lên thật **trước hoặc trong khi** `gates`/`dotnet` vẫn đang chạy hoặc đã fail — đúng lớp lỗi CD không phụ thuộc CI mà mục 2 và mục 6 đã cảnh báo. "Chạy lâu" không phải lý do hợp lệ để xoá `needs` — nếu hai job kiểm tra chạy chậm, giải pháp đúng là tối ưu tốc độ của chính chúng (ví dụ cache dependency), không phải bỏ qua việc chờ kết quả của chúng. Sửa đúng là giữ lại `needs: [gates, dotnet]` như file CI thật của Learning Hub.

---

## Tự kiểm tra

1. CI trả lời câu hỏi gì, CD trả lời câu hỏi gì?

    ??? note "Đáp án"
        CI (Continuous Integration) trả lời "code này có build/test đúng không?" — chạy mỗi lần push hoặc mở pull request. CD (Continuous Deployment/Delivery) trả lời "code đã xác nhận đúng có nên đưa lên chạy thật không?" — chỉ chạy sau khi CI đã báo xanh. Hai câu hỏi khác nhau, CD phụ thuộc kết quả của CI, không phải ngược lại.

2. Trong file `.github/workflows/ci.yml` của Learning Hub, trigger nào khiến CI tự chạy khi có người mở pull request đề xuất merge vào `main`?

    ??? note "Đáp án"
        `pull_request: { branches: [main] }`. Trigger này kích hoạt workflow mỗi khi có pull request mở hoặc cập nhật, nhắm merge vào nhánh `main` — đúng lớp bảo vệ kiểm tra bản code đã ghép trước khi ai bấm nút merge.

3. Job `gates` và job `dotnet` chạy trên cùng một máy ảo hay hai máy ảo khác nhau? Vì sao điều này quan trọng?

    ??? note "Đáp án"
        Hai máy ảo khác nhau — mỗi job trong GitHub Actions chạy trên máy ảo riêng biệt, không chia sẻ file/state với job khác trừ khi dùng cơ chế artifact/output riêng. Đây là lý do job `dotnet` phải tự `pip install -r requirements.txt` lại từ đầu, dù job `gates` đã cài đúng dependency đó rồi trên máy ảo của nó.

4. `needs: [gates, dotnet]` trong job `deploy` nghĩa là gì?

    ??? note "Đáp án"
        Job `deploy` chỉ bắt đầu chạy khi cả job `gates` và job `dotnet` đều đã chạy xong và thành công. Nếu một trong hai fail, `deploy` bị bỏ qua hoàn toàn, không chạy — đảm bảo không đẩy lên site thật một bản có lỗi cấu trúc tài liệu hoặc lỗi code C# mẫu.

5. Nếu xoá `needs: [gates, dotnet]` khỏi job `deploy`, điều gì thay đổi về thứ tự chạy?

    ??? note "Đáp án"
        Ba job sẽ chạy song song ngay từ đầu (mặc định của GitHub Actions khi không có `needs`) — `deploy` có thể chạy và đẩy site lên thật trong khi `gates`/`dotnet` vẫn đang chạy hoặc đã fail, vì `deploy` không còn chờ hoặc biết kết quả của hai job đó.

6. `permissions: { contents: write }` trong job `deploy` dùng để làm gì, và vì sao job `gates`/`dotnet` không cần dòng này?

    ??? note "Đáp án"
        Dùng để cấp quyền ghi vào nội dung repo, cần thiết vì lệnh `mkdocs gh-deploy --force` tạo/ghi đè nhánh `gh-pages` rồi push lên repo — một hành động ghi. Job `gates` và `dotnet` chỉ đọc code về để kiểm tra/compile, không ghi gì vào repo, nên không cần khai báo quyền ghi này.

7. Một dự án có CI chạy tốt (build/test tự động mỗi lần push) nhưng việc deploy vẫn do một kỹ sư vận hành tự tay làm sau khi xem CI xanh. Dự án này có CD không?

    ??? note "Đáp án"
        Không có CD theo đúng định nghĩa (mục 2) — CD nghĩa là việc đưa code lên chạy thật cũng được **tự động hoá**, không phải chỉ có CI tự động còn deploy vẫn thao tác tay. Đây là một cấu hình hoàn toàn hợp lệ trong thực tế (nhiều team chọn deploy tay có kiểm soát), chỉ là không nên gọi nó là "có CD" — CI và CD là hai thực hành độc lập, có CI không bắt buộc phải có CD đi kèm.

---

??? abstract "DEEP DIVE: `workflow_dispatch`, secrets, matrix build, và cache dependency"
    **`workflow_dispatch`: trigger chạy tay qua giao diện GitHub.** Ngoài `push` và `pull_request` (mục 4), GitHub Actions còn hỗ trợ trigger `workflow_dispatch` — cho phép một người có quyền trên repo bấm nút "Run workflow" trực tiếp trên giao diện web GitHub, kích hoạt workflow chạy **theo ý muốn**, không cần chờ một push/pull request nào xảy ra. Trigger này hữu ích cho các workflow không nên tự chạy liên tục (ví dụ một workflow dọn dữ liệu cũ, hoặc một lần deploy đặc biệt ngoài lịch thường), khai báo đơn giản bằng thêm `workflow_dispatch:` (thường để trống hoặc kèm tham số đầu vào) vào mục `on:` cùng với các trigger khác.

    **Secrets: giá trị nhạy cảm không được viết thẳng vào file `.yml`.** Nhiều workflow thực tế cần dùng tới thông tin nhạy cảm (API key, mật khẩu database, token đăng nhập cloud) để thực hiện bước deploy — những giá trị này **không bao giờ** nên viết trực tiếp vào file `.yml` (vì file này công khai trong lịch sử Git, ai đọc được repo cũng đọc được). GitHub cung cấp cơ chế "Secrets" (cấu hình trong phần Settings của repo, không nằm trong file `.yml`) — workflow tham chiếu tới secret qua cú pháp double-brace `secrets.TEN_SECRET` đặt trong dấu `${ ... }`, giá trị thật được GitHub tự thay vào lúc chạy, không hiện ra trong log hay trong file code. File CI thật của Learning Hub không cần secret nào (vì `mkdocs gh-deploy` dùng đúng `GITHUB_TOKEN` tự động có sẵn, không cần khai báo thêm secret riêng), nhưng một workflow deploy lên một cloud provider bên ngoài (ví dụ Azure, AWS) thường cần khai báo secret cho khoá truy cập của provider đó.

    **Matrix build: chạy cùng một job với nhiều phiên bản/cấu hình khác nhau.** Một nhu cầu phổ biến là kiểm tra code chạy đúng trên **nhiều phiên bản** của một công cụ (ví dụ nhiều phiên bản .NET, hoặc nhiều hệ điều hành: Ubuntu/Windows/macOS) — thay vì viết lặp lại nhiều job giống nhau chỉ khác một tham số, GitHub Actions hỗ trợ `strategy.matrix` khai báo danh sách giá trị cần thử, tự động sinh ra nhiều lần chạy song song cho từng tổ hợp. Ví dụ khai báo `matrix: { dotnet-version: ["8.0.x", "10.0.x"] }` sẽ khiến job đó tự chạy hai lần, một lần cho mỗi phiên bản, song song, không cần viết tay hai job riêng.

    **Cache dependency: tránh cài lại từ đầu mỗi lần chạy.** Mục 3 đã nhấn mạnh mỗi job khởi động một máy ảo sạch, phải tự cài mọi thứ từ đầu — điều này đúng nhưng có thể được **tối ưu tốc độ** (không phải tối ưu tính đúng đắn) bằng cơ chế cache: ví dụ dòng `with: { cache: pip }` đã xuất hiện trong job `gates` của file CI thật (`actions/setup-python@v5` với tuỳ chọn `cache: pip`) báo GitHub Actions **lưu lại** thư mục chứa các package Python đã cài, để lần chạy workflow **kế tiếp** (nếu `requirements.txt` không đổi) có thể tái sử dụng cache đó thay vì tải lại toàn bộ package từ Internet — giảm đáng kể thời gian chạy CI mà không ảnh hưởng tới việc mỗi job vẫn chạy độc lập, sạch về mặt logic (cache chỉ tối ưu tốc độ tải, không phải chia sẻ state giữa job).

Tóm lại bốn điều cần nhớ khi mang chương này vào một dự án thật: (1) CI và CD là hai khái niệm khác nhau — CI hỏi "có đúng không", CD hỏi "có nên đưa lên không", CD nên luôn phụ thuộc kết quả CI; (2) một workflow GitHub Actions gồm nhiều job chạy trên các máy ảo tách biệt, mỗi job gồm các step chạy tuần tự trên cùng máy ảo đó; (3) `needs: [...]` là cách khai báo job này phải chờ job khác xanh trước khi chạy — bỏ dòng này biến các job độc lập chạy song song, có thể để lỗi lọt qua; (4) `permissions:` nên luôn khai báo đúng quyền tối thiểu job cần, không cấp dư "cho chắc".

**Tiếp theo →** [P9 · Cloud Fundamentals: IaaS, PaaS, SaaS](cloud-fundamentals.md)
