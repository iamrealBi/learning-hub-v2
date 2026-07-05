---
tier: core
status: core
owner: core-team
verified_on: "2026-07-05"
dotnet_version: "10.0"
bloom: phân biệt
requires: [p9-iac]
est_minutes_fast: 22
---

# Monitoring & Alerting Production

!!! info "bạn đang ở đây"
    cần trước: ở P8 (`health-checks-observability.md`) bạn đã học ba trụ cột observability — Logs (sự kiện rời rạc), Metrics (số liệu tích lũy theo thời gian), Traces (đường đi một request qua nhiều service). Chương đó dừng ở việc **hệ thống phát ra được dữ liệu gì**. Chương này KHÔNG dạy lại Logs/Metrics/Traces từ đầu — nó tập trung vào hai bước tiếp theo, xảy ra SAU khi dữ liệu đã có: ai **nhìn** vào dữ liệu đó (Monitoring), và ai/cái gì **chủ động báo** khi có gì bất thường (Alerting).
    mở khoá: sau chương này bạn phân biệt được Monitoring và Alerting (hai việc khác nhau, hay bị coi là một), hiểu threshold-based alert hoạt động thế nào, biết vì sao alert quá nhiều lại nguy hiểm (alert fatigue), phân biệt được ba mức cam kết SLI/SLO/SLA hay bị nhầm lẫn, và hiểu runbook là gì — nền tảng để đọc hiểu quy trình vận hành production thật, trước khi học sâu hơn về container orchestration và IaC ở các chương kế tiếp.

> Mục tiêu (đo được): sau chương này bạn **phân biệt** được Monitoring và Alerting, **giải thích** được cơ chế threshold-based alert bằng ví dụ cụ thể, **nhận diện** được tình huống alert fatigue và nguyên nhân gây ra nó, **phân biệt** được SLI/SLO/SLA ở ba tầng cam kết khác nhau, và **mô tả** được vai trò của runbook trong việc giảm thời gian phản ứng sự cố.

---

## 0. Đoán nhanh trước khi học

Team của bạn đã cấu hình Metrics đầy đủ (đã học ở P8) — có dashboard hiển thị CPU, RAM, số request/giây, tỷ lệ lỗi 5xx.

Một đêm, CPU của server production tăng lên 95% và giữ nguyên như vậy suốt 2 giờ. Không ai trong team biết, vì không ai đang mở dashboard lúc 2 giờ sáng. Sáng hôm sau khách hàng phàn nàn ứng dụng chậm.

Vấn đề nằm ở đâu — thiếu Metrics, hay thiếu một thứ khác?

??? note "Đáp án"
    Không thiếu Metrics — dashboard đã hiển thị đúng CPU 95% suốt 2 giờ, dữ liệu **có ở đó**. Vấn đề là hệ thống chỉ có **Monitoring** (thu thập + hiển thị) mà không có **Alerting** (chủ động báo khi vượt ngưỡng). Monitoring giả định có người đang *xem* — nhưng không ai xem lúc 2 giờ sáng. Alerting giải quyết đúng lỗ hổng này: tự động gửi cảnh báo (SMS, Slack, email trực ban) ngay khi CPU vượt ngưỡng, không cần ai ngồi canh màn hình 24/7. Mục 1 và 2 định nghĩa rõ ràng sự khác biệt này.

    Lưu ý thêm: nếu bạn nghĩ "vậy chỉ cần bắt team trực xem dashboard 24/7 là đủ, không cần Alerting" — về lý thuyết đúng, nhưng về thực tế **không bền vững**.

    Yêu cầu con người liên tục chú ý tới một màn hình trong nhiều giờ liền, kể cả lúc không có gì bất thường xảy ra, là một cách sử dụng nguồn lực con người rất kém hiệu quả, và con người vẫn có thể lơ là, mất tập trung, hoặc đơn giản là cần ngủ. Alerting không phải một "tính năng thêm cho vui" — nó là giải pháp bắt buộc để một hệ thống production vận hành bền vững ngoài giờ làm việc mà không cần một đội ngũ khổng lồ canh màn hình liên tục.

---

## 1. Monitoring là gì

**Định nghĩa (một câu):** Monitoring là việc **thu thập và hiển thị liên tục** các chỉ số hệ thống (thường qua Metrics đã học ở P8) trên một dashboard, để con người có thể **xem** tình trạng hệ thống tại bất kỳ thời điểm nào khi họ chủ động mở nó lên.

Ví dụ tối thiểu, độc lập, chỉ minh hoạ đúng khái niệm Monitoring — mô tả một dashboard đơn giản (không phải code, vì Monitoring là một hoạt động vận hành/hạ tầng, không phải một API bạn viết trong ứng dụng):

```text title="dashboard-production.txt (minh hoa 1 dashboard toi thieu)"
Dashboard: "API Ban hang - Production"
Cap nhat: moi 15 giay

| Chi so          | Gia tri hien tai | Bieu do 1 gio qua |
|------------------|-------------------|-------------------|
| CPU              | 42%               | [dao dong 30-50%] |
| RAM               | 61%               | [tang dan tu 55%] |
| So request/giay  | 210               | [on dinh]         |
| Ty le loi 5xx    | 0.3%              | [on dinh]         |
```

Đây là một dashboard tối thiểu: bốn dòng chỉ số, cập nhật định kỳ, hiển thị cả giá trị hiện tại và xu hướng gần đây. Một người vận hành mở trang này lên, nhìn vào, và **tự đánh giá** "hệ thống có vẻ ổn" hay "RAM đang tăng dần, cần chú ý".

Điểm mấu chốt cần nắm: Monitoring **không tự động làm gì cả** ngoài hiển thị. Nó không gửi tin nhắn, không gọi điện, không tạo ticket. Toàn bộ giá trị của Monitoring phụ thuộc vào việc có **con người đang chủ động nhìn vào nó** tại đúng thời điểm có vấn đề xảy ra.

**Nếu dùng sai/thiếu:** nếu một team chỉ có Monitoring (dashboard đẹp, đầy đủ chỉ số) mà không có Alerting, hệ thống vận hành giống đúng ví dụ ở mục 0 — sự cố xảy ra ngoài giờ làm việc, ngoài lúc có người mở dashboard, và không ai biết cho tới khi khách hàng báo.

Dữ liệu **đã có sẵn** trên dashboard suốt thời gian đó, nhưng "có dữ liệu" không đồng nghĩa "có người biết". Đây chính xác là lỗ hổng mà Alerting (mục 2) được sinh ra để lấp.

Một câu hỏi hay gặp khi mới học: "vậy Monitoring có phải chỉ là một cái tên khác của Metrics (đã học ở P8) không?" Câu trả lời là không hoàn toàn.

Metrics là **dữ liệu** (con số đo được, tích lũy theo thời gian), còn Monitoring là **hoạt động vận hành** dùng dữ liệu đó (thu thập liên tục + hiển thị trên một giao diện để con người xem). Nói cách khác, Metrics là nguyên liệu, Monitoring là một trong những cách bạn *dùng* nguyên liệu đó.

Bạn có thể có Metrics mà không có Monitoring theo nghĩa chặt (ví dụ số liệu được ghi vào database nhưng không có dashboard nào hiển thị, không ai từng mở lên xem) — khi đó dữ liệu tồn tại nhưng hoàn toàn vô dụng cho mục đích vận hành, vì không ai và không hệ thống nào đọc nó theo thời gian thực.

Trong thực tế, một dashboard Monitoring trưởng thành thường có nhiều hơn bốn chỉ số ở ví dụ trên — chia theo tầng khác nhau của hệ thống:

- **Tầng hạ tầng (infrastructure):** CPU, RAM, dung lượng đĩa còn trống, băng thông mạng — những chỉ số về "máy chủ vật lý/máy ảo" đang chạy có khỏe không.
- **Tầng ứng dụng (application):** số request/giây, độ trễ (latency) trung bình và p95/p99, tỷ lệ lỗi theo mã trạng thái HTTP (4xx, 5xx) — những chỉ số về "phần mềm" đang phục vụ người dùng có tốt không.
- **Tầng nghiệp vụ (business):** số đơn hàng tạo thành công mỗi giờ, số người dùng đăng ký mới, doanh thu theo thời gian thực — những chỉ số không phải "kỹ thuật" nhưng vẫn cực kỳ quan trọng để phát hiện vấn đề (ví dụ số đơn hàng giảm mạnh bất thường có thể là dấu hiệu một luồng thanh toán đang lỗi, dù mọi chỉ số kỹ thuật vẫn "xanh").

Ba tầng này không tách biệt hoàn toàn — một sự cố ở tầng hạ tầng (CPU cao) thường kéo theo ảnh hưởng ở tầng ứng dụng (độ trễ tăng), rồi cuối cùng ảnh hưởng tầng nghiệp vụ (khách hàng bỏ giỏ hàng vì trang chậm).

Một dashboard Monitoring tốt thường hiển thị cả ba tầng cạnh nhau, để người xem tự nối được nguyên nhân — ví dụ nhìn thấy CPU tăng đúng lúc số đơn hàng giảm, họ có thể suy luận nhanh hơn là chỉ nhìn một tầng riêng lẻ.

Về mặt công cụ thực tế (chỉ để bạn có hình dung, không cần thành thạo ở mức chương này): dữ liệu Metrics thường được một hệ thống thu thập chuyên dụng lưu lại theo thời gian (ví dụ Prometheus — thu thập và lưu số liệu dạng "chuỗi thời gian", time series), rồi một công cụ hiển thị riêng (ví dụ Grafana) đọc dữ liệu đó và vẽ thành biểu đồ trên dashboard.

Hai công cụ này thường đi cùng nhau nhưng đóng vai trò khác nhau: một cái **lưu trữ và truy vấn** số liệu theo thời gian, một cái **trình bày** số liệu đó thành hình ảnh dễ đọc cho con người. Bạn không cần biết cách cài đặt hay cấu hình Prometheus/Grafana ở mức chương này — chỉ cần hiểu rằng "dashboard" trong thực tế thường không phải một trang web bạn tự viết từ đầu, mà là kết quả của việc nối dữ liệu Metrics (đã có từ P8, qua OpenTelemetry) vào một công cụ hiển thị chuyên dụng có sẵn.

Một điểm cần làm rõ ngay từ đầu, để tránh một hiểu nhầm thường gặp: Monitoring không đồng nghĩa với "xem log". Log (đã học ở P8) ghi lại **từng sự kiện rời rạc** — Monitoring theo đúng định nghĩa ở chương này tập trung vào **chỉ số tổng hợp theo thời gian** (Metrics), hiển thị dưới dạng biểu đồ xu hướng, không phải một danh sách dòng log để đọc từng dòng.

Một người vận hành có thể "monitor" hệ thống mà không cần đọc một dòng log nào — chỉ cần nhìn biểu đồ CPU/RAM/tỷ lệ lỗi đang đi lên hay đi xuống. Khi cần hiểu **chi tiết vì sao** một chỉ số bất thường, họ mới chuyển sang đọc log — đó là bước tiếp theo, không phải một phần của Monitoring theo nghĩa hẹp.

Một khía cạnh khác của Monitoring ít được nói tới nhưng quan trọng trong thực tế: **khoảng thời gian lưu giữ dữ liệu** (retention). Một dashboard chỉ hiển thị dữ liệu "1 giờ qua" là đủ để theo dõi tình trạng hiện tại, nhưng khi cần **so sánh** (ví dụ "tuần này CPU trung bình có cao hơn tuần trước không") hoặc **điều tra sự cố đã xảy ra vài ngày trước**, bạn cần dữ liệu lịch sử được lưu lại đủ lâu.

Lưu giữ dữ liệu chi tiết (từng giây) vô hạn thời gian tốn rất nhiều dung lượng lưu trữ, nên hệ thống Monitoring thực tế thường áp dụng chính sách "downsample" — giữ chi tiết đầy đủ cho vài ngày gần nhất, rồi tự động nén lại thành số liệu trung bình theo giờ/ngày cho dữ liệu cũ hơn, đánh đổi độ chi tiết để tiết kiệm chi phí lưu trữ dài hạn.

Ai thực tế là người mở dashboard Monitoring lên xem, và khi nào? Trong thực tế có ba tình huống phổ biến, đáng phân biệt vì chúng đặt ra yêu cầu khác nhau cho thiết kế dashboard:

- **Xem chủ động, định kỳ:** một kỹ sư vận hành dành vài phút mỗi sáng để lướt qua dashboard, kiểm tra không có gì bất thường tích lũy qua đêm — một dạng "khám sức khỏe định kỳ" cho hệ thống, không chờ có alert mới xem.
- **Xem sau khi nhận alert:** như đã nhắc ở mục 2, khi một alert được gửi tới, bước đầu tiên thường là mở dashboard để có bức tranh đầy đủ trước khi quyết định hành động — đây là tình huống dashboard được dùng **cùng** với Alerting, không phải thay thế.
- **Xem khi điều tra một vấn đề đã biết:** ví dụ khách hàng báo lỗi cụ thể, kỹ sư mở dashboard để xem tại đúng khoảng thời gian khách hàng gặp lỗi, có gì bất thường trên hệ thống không — đây là lúc khả năng xem **dữ liệu lịch sử** (retention đã nhắc ở trên) trở nên quan trọng, vì thời điểm khách hàng gặp lỗi thường đã qua vài giờ hoặc vài ngày trước khi họ báo.

Ba tình huống này cho thấy Monitoring không phải một hoạt động "một lần rồi xong" — nó là một công cụ được dùng lại nhiều lần, trong nhiều ngữ cảnh khác nhau, và một dashboard thiết kế tốt cần phục vụ được cả ba mà không cần xây riêng ba dashboard khác nhau.

---

## 2. Alerting là gì — và khác Monitoring ở điểm nào

**Định nghĩa (một câu):** Alerting là cơ chế **tự động phát hiện** khi một chỉ số vượt ra ngoài phạm vi bình thường, rồi **chủ động gửi thông báo** tới người vận hành (qua SMS, Slack, PagerDuty, email...) — mà không cần bất kỳ ai đang ngồi xem dashboard.

Bảng phân biệt hai khái niệm (chỉ đưa ra **sau khi** đã định nghĩa riêng từng khái niệm ở trên):

| Tiêu chí | Monitoring | Alerting |
|---|---|---|
| Hành động chính | Thu thập + hiển thị | Phát hiện + chủ động báo |
| Cần con người làm gì | Phải chủ động mở dashboard để xem | Không cần ai chủ động xem — hệ thống tự tìm đến người |
| Khi nào phát hiện vấn đề | Chỉ khi có người đang nhìn đúng lúc | Ngay khi chỉ số vượt ngưỡng đã cấu hình, bất kể giờ nào |
| Ví dụ cụ thể | Dashboard CPU/RAM/request 24/7 | Tin nhắn SMS lúc 2 giờ sáng: "CPU server-prod-01 đã vượt 90% trong 5 phút" |

Quan hệ giữa hai khái niệm không phải "chọn một trong hai" — Alerting **luôn cần dữ liệu từ Monitoring** để có cái để kiểm tra (không có chỉ số thì không có gì để so ngưỡng). Nói cách khác: Monitoring là **nền tảng dữ liệu**, Alerting là **lớp hành động tự động** xây trên nền tảng đó.

Một hệ thống production nghiêm túc cần cả hai — có Monitoring mà không Alerting thì vẫn phải trông chờ vào việc "tình cờ có người đang xem"; có Alerting mà không Monitoring thì không có gì để Alerting đọc chỉ số từ đó.

Một cách hình dung dễ nhớ: Monitoring giống một camera an ninh đang ghi hình liên tục — hữu ích để **xem lại** hoặc để nhân viên bảo vệ chủ động theo dõi màn hình. Alerting giống một cảm biến chuyển động gắn chuông báo — **tự động kêu** ngay khi có động, không cần ai đang nhìn màn hình camera lúc đó. Camera (Monitoring) vẫn cần để xem lại chi tiết chuyện gì đã xảy ra, nhưng chuông báo (Alerting) mới là thứ **đánh thức** bạn giữa đêm.

**Nếu dùng sai/thiếu:** nhầm lẫn phổ biến nhất là nghĩ "có dashboard đẹp là đủ" — như ví dụ mục 0, một team có dashboard chi tiết vẫn hoàn toàn "mù" trước sự cố nếu không có ai đang xem đúng lúc nó xảy ra.

Hậu quả cụ thể: thời gian phát hiện sự cố (time-to-detect) kéo dài từ vài phút (nếu có Alerting) lên tới hàng giờ hoặc qua đêm (nếu chỉ có Monitoring) — và trong khoảng thời gian đó, người dùng thật đang chịu ảnh hưởng mà không ai trong team biết.

Một điểm dễ gây hiểu lầm ngược lại cũng cần nói rõ: có Alerting không có nghĩa là **bỏ qua** Monitoring. Khi một alert được gửi tới, bước đầu tiên người trực ban thường làm là **mở dashboard Monitoring** để nhìn bức tranh đầy đủ (không chỉ con số đã vượt ngưỡng, mà cả các chỉ số liên quan khác, xu hướng trước/sau thời điểm alert).

Alerting cho bạn biết "có gì đó cần chú ý, ngay bây giờ"; Monitoring cho bạn biết "chuyện gì đang diễn ra, đầy đủ ngữ cảnh" để quyết định hành động tiếp theo là gì. Hai công cụ luôn dùng **cùng nhau**, không phải cái này thay thế cái kia — chính ví dụ runbook ở mục 6 (Bước 1: "mở dashboard Monitoring, xác nhận...") sẽ cho thấy rõ trình tự thực tế này.

Cũng cần phân biệt rạch ròi: Alerting **không phải** là việc gửi mọi log lỗi qua Slack ngay khi nó xảy ra. Nếu một API bị lỗi 500 đúng một lần trong hàng triệu request (ví dụ do một race condition hiếm gặp, tự phục hồi ngay lần request sau), gửi alert cho **mỗi lần lỗi đơn lẻ** sẽ tạo ra nhiễu khổng lồ — không phải mọi "sự kiện bất thường" đều xứng đáng một alert riêng.

Alerting đúng nghĩa hoạt động ở tầng **tổng hợp theo thời gian** (ví dụ "tỷ lệ lỗi 5xx trong 5 phút qua"), không phải tầng "từng dòng log riêng lẻ" — đây là lý do threshold-based alert (mục 3) luôn có một khoảng thời gian quan sát, không chỉ một điều kiện tức thời.

Về kênh gửi thông báo trong thực tế, Alerting thường không chỉ dùng một kênh duy nhất — hệ thống thường định tuyến (route) tới nhiều kênh khác nhau tùy mức độ nghiêm trọng và thời điểm trong ngày:

- **Giờ làm việc, mức độ nhẹ:** gửi vào một kênh Slack/Teams chung của team, không cần đánh chuông ưu tiên.
- **Ngoài giờ làm việc, mức độ nghiêm trọng:** gọi qua một dịch vụ chuyên quản lý ca trực (on-call), ví dụ PagerDuty hoặc Opsgenie — dịch vụ này biết ai đang trong ca trực hiện tại, gọi điện/gửi SMS liên tục cho tới khi có người xác nhận đã nhận (acknowledge), và tự động **leo thang (escalate)** gọi người tiếp theo trong danh sách nếu người đầu tiên không phản hồi trong một khoảng thời gian quy định.
- **Bất kể giờ nào, mức độ nghiêm trọng cực cao (toàn hệ thống sập):** thường gửi đồng thời qua nhiều kênh cùng lúc (SMS + gọi điện + Slack) để tối đa hoá khả năng có người phản hồi nhanh nhất, chấp nhận đánh đổi "gây ồn ào hơn cần thiết" để đổi lấy tốc độ phản ứng trong tình huống nghiêm trọng nhất.

Cơ chế "leo thang" (escalation) ở trên đáng chú ý riêng: nó giải quyết một vấn đề thực tế mà một alert đơn giản không giải quyết được — điều gì xảy ra nếu người trực ban đầu tiên không phản hồi (đang ngủ sâu, điện thoại hết pin, đang ở khu vực không có sóng)?

Không có cơ chế leo thang, alert coi như đã "gửi xong nhiệm vụ" dù không ai thực sự nhận được nó — một lỗ hổng nguy hiểm không kém gì hoàn toàn không có Alerting. Cơ chế leo thang biến việc gửi alert từ "gửi một lần rồi thôi" thành một quy trình chủ động đảm bảo **có người thật sự tiếp nhận**, không chỉ "đã gửi đi".

Một thuật ngữ hay gặp kèm theo Alerting là "acknowledge" (thường viết tắt "ack") — hành động người trực ban xác nhận rõ ràng "tôi đã nhận và đang xử lý alert này", thường bằng một nút bấm trong ứng dụng quản lý ca trực.

Việc "ack" khác với việc chỉ đơn giản đọc thông báo: hệ thống Alerting **biết chắc** ai đang xử lý (không phải đoán dựa vào việc thông báo đã được đọc hay chưa), và nếu quá một khoảng thời gian mà không ai "ack", cơ chế leo thang tự động kích hoạt gọi người tiếp theo — đây là cách một hệ thống Alerting trưởng thành đảm bảo không có alert nào "rơi vào im lặng" mà không ai biết.

---

## 3. Threshold-based alert: cơ chế phổ biến nhất của Alerting

**Định nghĩa (một câu):** Threshold-based alert là một quy tắc alert đơn giản dạng "**nếu** chỉ số X vượt qua một ngưỡng cố định **trong** một khoảng thời gian liên tục, **thì** gửi cảnh báo" — đây là cơ chế nền tảng, dễ hiểu nhất, và phổ biến nhất trong thực tế.

Ví dụ cụ thể, độc lập, chỉ minh hoạ đúng cơ chế này:

```text title="quy-tac-alert.txt (minh hoa 1 threshold-based alert)"
TEN QUY TAC: cpu-cao-server-prod

DIEU KIEN:  CPU trung binh > 90%
THOI GIAN:  lien tuc trong 5 phut
HANH DONG:  gui SMS + Slack toi nhom truc ban
MUC DO:     nghiem trong (critical)
```

Đọc quy tắc này theo đúng ba phần của định nghĩa: **điều kiện** (CPU > 90%), **khoảng thời gian liên tục** (5 phút, không phải một lần đo tức thời), **hành động** (gửi SMS + Slack).

Phần "trong 5 phút liên tục" quan trọng không kém phần "> 90%" — nếu chỉ kiểm tra một lần đo tức thời (ví dụ CPU tăng vọt 92% trong đúng 2 giây do một tác vụ nền chạy đột xuất, rồi tụt về 40% ngay sau đó), gửi alert ngay lập tức sẽ là một **báo động giả** (false positive): hệ thống không có vấn đề thật, chỉ là một đợt tăng tải thoáng qua hoàn toàn bình thường.

Yêu cầu "liên tục trong khoảng thời gian" đóng vai trò lọc nhiễu, giống hệt vai trò của `failureThreshold` trong health check probe mà bạn đã gặp ở P8 — cả hai đều là cơ chế "đợi đủ lâu/đủ nhiều lần thất bại mới coi là thật", để tránh phản ứng thái quá với một điểm dữ liệu bất thường đơn lẻ.

**Nếu dùng sai/thiếu:** đặt ngưỡng quá nhạy (ví dụ CPU > 70% cảnh báo ngay, không cần khoảng thời gian liên tục) khiến hệ thống gửi alert liên tục cho những dao động hoàn toàn bình thường trong vận hành hàng ngày (ví dụ giờ cao điểm buổi tối).

Ngược lại, đặt ngưỡng quá lười (CPU > 99%, mới báo) khiến alert đến quá muộn — hệ thống đã bắt đầu ảnh hưởng người dùng thật từ lâu trước khi ngưỡng 99% được chạm tới. Cả hai sai lầm đều xuất phát từ việc chọn ngưỡng và khoảng thời gian mà không dựa trên hành vi thực tế đã quan sát được của hệ thống — đây là lý do mục 4 (alert fatigue) và runbook (mục 6) liên quan trực tiếp tới việc chỉnh ngưỡng đúng.

Threshold-based alert không chỉ áp dụng cho chỉ số hạ tầng (CPU, RAM) — nó áp dụng được cho bất kỳ chỉ số đo được nào, kể cả chỉ số tầng nghiệp vụ đã nhắc ở mục 1. Vài ví dụ khác để thấy tính tổng quát của cơ chế này:

- **Tỷ lệ lỗi:** "nếu tỷ lệ request trả 5xx > 5% trong 3 phút liên tục thì báo mức nghiêm trọng."
- **Độ trễ:** "nếu độ trễ p99 của API Thanh toán > 2 giây trong 2 phút liên tục thì báo."
- **Dung lượng đĩa:** "nếu dung lượng đĩa trống < 10% thì báo" — lưu ý ví dụ này thường **không cần** điều kiện "liên tục trong bao lâu", vì dung lượng đĩa không dao động lên xuống thất thường như CPU; nó thường chỉ tăng dần một chiều tới khi đầy, nên chỉ cần một lần đo dưới ngưỡng cũng đủ đáng tin.
- **Chỉ số nghiệp vụ:** "nếu số đơn hàng thành công trong 10 phút qua giảm hơn 50% so với trung bình cùng giờ các ngày trước thì báo" — đây là một dạng threshold **so sánh tương đối** (so với baseline lịch sử) thay vì một số tuyệt đối cố định, hữu ích khi hành vi bình thường của hệ thống thay đổi theo thời điểm trong ngày/tuần (ví dụ traffic buổi tối luôn cao hơn buổi sáng — một ngưỡng tuyệt đối cố định sẽ báo động giả liên tục vào buổi tối nếu đặt dựa trên baseline buổi sáng).

Điểm chung của mọi ví dụ trên: threshold-based alert luôn cần **ba quyết định** — chọn đúng chỉ số đại diện cho vấn đề thật (không phải chỉ số nào cũng đáng theo dõi), chọn ngưỡng dựa trên hành vi bình thường đã quan sát (không phải một số bịa ra), và chọn khoảng thời gian đủ để lọc nhiễu ngắn hạn nhưng không quá dài tới mức chậm phát hiện.

Ba quyết định này không có công thức máy móc áp dụng chung cho mọi hệ thống — chúng đòi hỏi quan sát dữ liệu Monitoring thật (mục 1) trong một khoảng thời gian trước khi đặt ngưỡng, rồi tinh chỉnh dần theo kinh nghiệm vận hành thực tế.

"Threshold-based" là tên gọi nhấn mạnh **cách phát hiện bất thường** (so với một ngưỡng cố định hoặc tương đối, do con người tự chọn), để phân biệt với một hướng khác tồn tại trong thực tế: **anomaly detection** (phát hiện bất thường bằng thống kê/machine learning), trong đó hệ thống tự học "hành vi bình thường trông như thế nào" từ dữ liệu lịch sử, rồi tự phát hiện khi có sai lệch đáng kể mà không cần con người đặt ngưỡng thủ công.

Anomaly detection mạnh hơn ở việc phát hiện những bất thường phức tạp mà một ngưỡng đơn giản khó diễn tả (ví dụ "hành vi traffic hôm nay khác thường so với cùng-giờ-cùng-thứ-trong-tuần các tuần trước", một mẫu hình phức tạp hơn một số cố định) — nhưng đòi hỏi hạ tầng phức tạp hơn nhiều và khó giải thích **vì sao** một alert được kích hoạt (so với threshold-based, nơi lý do luôn rõ ràng: "vì X vượt ngưỡng Y").

Trong phần lớn hệ thống ở quy mô vừa và nhỏ, threshold-based alert vẫn là lựa chọn mặc định và đủ dùng — đây cũng là lý do chương này chỉ giới thiệu threshold-based ở mức chi tiết, còn anomaly detection chỉ nhắc tên để bạn biết nó tồn tại khi cần tìm hiểu sâu hơn sau này.

Một ví dụ minh hoạ threshold-based alert kết hợp nhiều điều kiện cùng lúc (compound condition), để thấy cơ chế này mở rộng được thế nào ngoài trường hợp "một chỉ số, một ngưỡng" đơn giản ở ví dụ đầu mục:

```text title="quy-tac-alert-ket-hop.txt (minh hoa threshold ket hop nhieu dieu kien)"
TEN QUY TAC: qua-tai-nghiem-trong

DIEU KIEN:  (CPU trung binh > 85%)  VA  (do tre p99 > 1000ms)
THOI GIAN:  lien tuc trong 3 phut
HANH DONG:  goi dien + SMS toi nhom truc ban, leo thang sau 5 phut khong ai xac nhan
MUC DO:     nghiem trong (critical)
```

Điều kiện kết hợp (`VA`, tức "and") ở đây có mục đích cụ thể: chỉ báo khi **cả hai** dấu hiệu cùng xảy ra, giảm khả năng báo động giả so với việc chỉ dựa vào một chỉ số đơn lẻ.

CPU cao một mình có thể chỉ là một tác vụ nền đang chạy bình thường (không ảnh hưởng người dùng thật, vì độ trễ vẫn ổn); độ trễ cao một mình có thể do một nguyên nhân khác không liên quan CPU (ví dụ mạng chậm).

Nhưng khi **cả hai cùng xảy ra đồng thời**, khả năng đây là một sự cố thật ảnh hưởng người dùng cao hơn nhiều — đây là lý do nhiều hệ thống Alerting trưởng thành dùng điều kiện kết hợp cho các alert mức nghiêm trọng cao nhất, thay vì chỉ dựa vào một chỉ số riêng lẻ.

---

## 4. Alert fatigue: khi có QUÁ NHIỀU alert

**Định nghĩa (một câu):** Alert fatigue là hiện tượng người vận hành nhận **quá nhiều alert**, trong đó phần lớn không thật sự quan trọng hoặc không thể hành động được, đến mức họ dần **lơ là cả những alert quan trọng thật** — biến chính công cụ được tạo ra để giúp phát hiện sớm thành nguyên nhân bỏ sót sự cố.

Ví dụ cụ thể để thấy cơ chế này hình thành như thế nào:

Một team cấu hình alert cho **mọi** chỉ số có thể đo được: CPU > 70% (không có khoảng thời gian liên tục), RAM > 60%, mỗi request chậm hơn 500ms, mỗi lần cache miss...

Kết quả: điện thoại của người trực ban rung liên tục — có ngày hơn 200 alert, phần lớn là những dao động bình thường tự phục hồi trong vài giây (ví dụ CPU chạm 71% trong 3 giây rồi tụt về 40%). Sau vài tuần, người trực ban hình thành thói quen **liếc qua rồi bỏ qua** hầu hết alert mà không đọc kỹ nội dung — vì kinh nghiệm cho thấy 95% trong số đó không cần hành động gì.

Đến ngày có một alert **thật sự nghiêm trọng** (database sắp hết dung lượng đĩa, sẽ crash trong 10 phút), nó bị lướt qua giống như 200 alert vô hại trước đó — sự cố chỉ được phát hiện khi database đã crash thật.

**Nếu không nhận diện được alert fatigue — hậu quả cụ thể:** thời gian phản ứng với sự cố thật càng ngày càng chậm dần theo thời gian (không phải do hệ thống Alerting hỏng — nó vẫn gửi alert đúng như cấu hình — mà do con người nhận alert đã mất niềm tin vào tín hiệu).

Đây là một dạng thất bại "âm thầm" đặc biệt nguy hiểm: không có lỗi kỹ thuật nào để debug, hệ thống Alerting về mặt kỹ thuật vẫn "hoạt động đúng thiết kế" — vấn đề nằm ở **thiết kế** ngưỡng/số lượng alert, giống hệt bài học ở P8 về việc gộp sai check vào một endpoint Readiness.

Cách khắc phục alert fatigue trong thực tế xoay quanh một nguyên tắc chung: **mỗi alert gửi đi phải là một alert người nhận CẦN hành động ngay**.

Nếu một điều kiện không cần hành động ngay (ví dụ cache miss rate cao nhưng hệ thống vẫn phục vụ được, chỉ chậm hơn một chút), nó không nên là một alert gửi SMS lúc nửa đêm; nó nên nằm trên dashboard Monitoring (mục 1) để xem xét vào giờ làm việc bình thường, hoặc để mức độ nghiêm trọng thấp hơn (thông báo không khẩn, ví dụ chỉ gửi email tổng hợp hàng ngày thay vì SMS ngay lập tức).

Có một nghịch lý dễ khiến người mới học đặt sai hướng khắc phục: phản ứng tự nhiên khi thấy "quá nhiều alert" là **xóa bớt** alert cho tới khi số lượng giảm xuống.

Nhưng xóa sai alert (ví dụ xóa luôn alert dung lượng đĩa vì nó "ít khi quan trọng") có thể tạo ra một lỗ hổng phát hiện mới, còn nguy hiểm hơn chính vấn đề alert fatigue ban đầu.

Hướng khắc phục đúng không phải "giảm số lượng" một cách máy móc, mà là **phân loại lại đúng mức độ nghiêm trọng** cho từng alert — giữ nguyên việc theo dõi (không xóa dữ liệu, không bỏ qua vấn đề), chỉ thay đổi **cách nó được thông báo** (kênh nào, có đánh thức người trực ban giữa đêm hay không). Phần DEEP DIVE cuối bài sẽ đi sâu hơn vào cách phân loại mức độ nghiêm trọng (severity routing) trong thực tế.

Một dấu hiệu thực tế giúp nhận ra một team đang gặp alert fatigue, ngay cả khi không ai gọi tên nó ra: người trực ban bắt đầu **tự động tắt âm thanh thông báo** ngoài giờ làm việc, hoặc cấu hình quy tắc lọc riêng để "không nhận loại alert X nữa" mà không báo lại với team.

Đây là dấu hiệu cảnh báo sớm rằng hệ thống Alerting đang mất niềm tin từ chính người dùng của nó, và cần được rà soát lại ngưỡng/mức độ nghiêm trọng trước khi có sự cố thật bị bỏ sót.

Để thấy rõ hơn quy mô thực tế của vấn đề, hãy so sánh hai kịch bản cấu hình alert cho cùng một hệ thống, trong cùng một tuần vận hành:

| Kịch bản | Số alert gửi trong 1 tuần | Số alert thật sự cần hành động | Tỷ lệ "báo động giả" |
|---|---|---|---|
| Cấu hình quá nhạy (mọi ngưỡng thấp, không có khoảng thời gian liên tục) | 340 | 6 | 98% |
| Cấu hình đã tinh chỉnh (ngưỡng dựa trên baseline, có khoảng thời gian liên tục, phân loại severity) | 9 | 6 | 33% |

Ở kịch bản đầu, người trực ban phải xem qua 340 alert để tìm ra 6 alert thật sự quan trọng — với tỷ lệ báo động giả 98%, phản ứng tự nhiên của con người (không phải lỗi cá nhân, mà là một cơ chế tâm lý bình thường) là dần bỏ qua phần lớn alert mà không đọc kỹ, vì kinh nghiệm liên tục xác nhận "hầu hết không quan trọng".

Ở kịch bản sau, cùng 6 sự cố thật vẫn được phát hiện đầy đủ, nhưng tổng số alert giảm xuống 9 — mỗi alert đến đều có xác suất cao là đáng chú ý, giữ được sự tin tưởng của người nhận vào tín hiệu.

Đây chính là mục tiêu thực tế của việc chống alert fatigue: không phải "gửi ít alert hơn" như một mục tiêu tự thân, mà là **giữ tỷ lệ báo động giả đủ thấp** để mỗi alert đến vẫn còn ý nghĩa với người nhận.

---

## 5. SLI, SLO, SLA: ba tầng cam kết khác nhau

Ba khái niệm này thường bị gộp chung vì cùng liên quan tới "đo mức độ tốt của hệ thống", nhưng mỗi khái niệm trả lời một câu hỏi khác nhau — định nghĩa riêng từng cái trước khi so sánh.

**Định nghĩa (một câu) — SLI (Service Level Indicator):** SLI là một **chỉ số đo được thực tế** phản ánh chất lượng dịch vụ, ví dụ "tỷ lệ % request trả lời thành công trong tổng số request" hoặc "độ trễ p99 của API". SLI chỉ là **con số quan sát được** — nó không tự mang theo ý nghĩa "tốt" hay "xấu", chỉ là dữ liệu thô đo từ hệ thống thật (tương tự Metrics đã học ở P8, nhưng SLI được chọn lọc làm chỉ số **đại diện** cho chất lượng dịch vụ, không phải mọi Metric đều được dùng làm SLI).

**Định nghĩa (một câu) — SLO (Service Level Objective):** SLO là **mục tiêu nội bộ** mà team đặt ra cho một SLI cụ thể, ví dụ "SLI tỷ lệ thành công phải đạt ít nhất 99.9% mỗi tháng" — SLO là cam kết **giữa team với chính mình** (hoặc với các team khác trong công ty), dùng để tự đánh giá và ra quyết định kỹ thuật (ví dụ có nên chấp nhận rủi ro deploy một thay đổi lớn hay không), không có ràng buộc pháp lý với bên ngoài.

**Định nghĩa (một câu) — SLA (Service Level Agreement):** SLA là một **cam kết chính thức với khách hàng**, thường có ràng buộc hợp đồng — ví dụ "nếu uptime dưới 99.5% trong một tháng, khách hàng được hoàn tiền một phần phí dịch vụ". SLA khác SLO ở điểm cốt lõi: SLA có **hậu quả hợp đồng cụ thể** (bồi thường, hoàn tiền, phạt) nếu không đạt, còn SLO chỉ là mục tiêu nội bộ.

Ví dụ cụ thể phân biệt ba mức, cùng theo một chỉ số uptime, để thấy rõ chúng khác nhau ở tầng nào — không phải ở con số, mà ở **vai trò**:

| Tầng | Ví dụ cụ thể | Ai đặt ra | Nếu không đạt |
|---|---|---|---|
| SLI | "Uptime đo được thực tế tháng này: 99.92%" | Không ai "đặt" — đây là số đo thật | Không có khái niệm "không đạt" — SLI chỉ là quan sát |
| SLO | "Mục tiêu nội bộ: uptime >= 99.9%/tháng" | Team kỹ thuật tự đặt cho mình | Team họp lại, xem xét nguyên nhân, điều chỉnh kế hoạch kỹ thuật — không có hậu quả hợp đồng |
| SLA | "Cam kết với khách hàng: uptime >= 99.5%/tháng, nếu không hoàn 10% phí" | Bộ phận kinh doanh/pháp lý, ký với khách hàng | Công ty phải hoàn tiền theo đúng hợp đồng đã ký |

Điểm quan trọng cần nhớ về thứ tự và quan hệ giữa ba tầng: SLO **luôn được đặt khắt khe hơn** SLA (trong ví dụ trên, SLO 99.9% khắt khe hơn SLA 99.5%) — đây không phải ngẫu nhiên, mà là một khoảng đệm an toàn có chủ đích.

Nếu SLO và SLA bằng nhau, bất kỳ dao động nhỏ nào khiến SLI tụt dưới mục tiêu nội bộ cũng đồng thời là vi phạm hợp đồng với khách hàng — không còn khoảng trống để team phát hiện và xử lý vấn đề **trước khi** nó trở thành hậu quả pháp lý thật.

**Nếu nhầm lẫn ba khái niệm — hậu quả cụ thể:** nếu một kỹ sư báo cáo với khách hàng "SLI tháng này đạt 99.92%" như thể đó là một cam kết ràng buộc (nhầm SLI với SLA), khách hàng có thể hiểu sai rằng con số này là một **đảm bảo hợp đồng** cho các tháng sau — trong khi SLI chỉ là một số đo lịch sử, không mang ý nghĩa dự đoán hay ràng buộc.

Ngược lại, nếu team kỹ thuật đặt SLO bằng đúng SLA (nhầm vai trò "khoảng đệm nội bộ" của SLO), họ sẽ luôn ở trong trạng thái "chạm ranh giới vi phạm hợp đồng" ngay khi có bất kỳ sự cố nhỏ nào, thay vì có không gian xử lý sự cố ở tầng nội bộ trước khi nó ảnh hưởng tới khách hàng.

Một cách hình dung khác giúp nhớ lâu thứ tự ba khái niệm: hãy nghĩ tới một kỳ thi ở trường.

**SLI** giống điểm số thật bạn đạt được sau khi làm bài ("bạn đã đạt 8.5/10 điểm") — chỉ là một con số quan sát được, đã xảy ra rồi, không thể thay đổi.

**SLO** giống mục tiêu bạn tự đặt ra cho bản thân trước kỳ thi ("mình muốn đạt ít nhất 8 điểm") — một cam kết nội bộ, không ai phạt bạn nếu không đạt, chỉ ảnh hưởng tới cách bạn tự đánh giá và điều chỉnh cách học tiếp theo.

**SLA** giống điều kiện học bổng đã ký với nhà trường ("nếu điểm trung bình dưới 7, học bổng bị thu hồi") — có hậu quả ràng buộc thật, không phụ thuộc vào việc bạn tự đặt mục tiêu cao hơn hay thấp hơn con số đó.

Cũng cần lưu ý: không phải mọi hệ thống đều cần có đủ cả ba tầng. Một dự án nội bộ nhỏ, không có khách hàng bên ngoài, hoàn toàn có thể chỉ cần SLI (đo để biết) và SLO (mục tiêu tự đặt để cải thiện) mà không cần SLA nào — vì không có bên thứ ba nào để ký cam kết ràng buộc.

SLA chỉ xuất hiện khi có một mối quan hệ **khách hàng — nhà cung cấp dịch vụ** chính thức, thường đi kèm hợp đồng thương mại. Đây cũng là lý do nhiều tài liệu vận hành nội bộ (không bán dịch vụ ra ngoài) chỉ nói tới SLI/SLO, hiếm khi nhắc SLA.

SLI không chỉ dùng cho uptime — trong thực tế, một dịch vụ thường có **nhiều SLI khác nhau**, mỗi SLI đo một khía cạnh chất lượng riêng, và mỗi SLI có thể có SLO riêng của nó:

- **SLI về độ khả dụng (availability):** tỷ lệ % thời gian dịch vụ phản hồi được (không tính lỗi 5xx). SLO ví dụ: ">= 99.9%/tháng".
- **SLI về độ trễ (latency):** tỷ lệ % request được xử lý dưới một ngưỡng thời gian, ví dụ "tỷ lệ request có độ trễ dưới 500ms". SLO ví dụ: ">= 95% request dưới 500ms mỗi ngày".
- **SLI về độ chính xác (correctness):** tỷ lệ % request trả về kết quả đúng (ít gặp hơn, khó đo tự động hơn hai loại trên, nhưng vẫn là một SLI hợp lệ nếu đo được — ví dụ tỷ lệ giao dịch thanh toán được xử lý đúng số tiền).

Việc có nhiều SLI cùng lúc phản ánh đúng thực tế: một dịch vụ có thể "luôn phản hồi" (SLI khả dụng tốt) nhưng "phản hồi chậm" (SLI độ trễ kém) — hai vấn đề khác nhau, cần được theo dõi và cải thiện độc lập, dù cả hai đều thuộc về "chất lượng dịch vụ" nói chung.

Đây là lý do một bảng SLO thực tế của một dịch vụ nghiêm túc thường có nhiều dòng, mỗi dòng một SLI riêng, không chỉ một số uptime duy nhất như ví dụ đơn giản hoá ở trên.

Để thấy con số SLO/SLA thực sự nghĩa là gì về mặt thời gian (không chỉ là một tỷ lệ % trừu tượng), hãy quy đổi vài mức uptime phổ biến sang số phút "được phép" ngừng hoạt động mỗi tháng (giả định một tháng có khoảng 43.200 phút):

| Mức uptime | Thời gian downtime tối đa cho phép/tháng |
|---|---|
| 99% | ~432 phút (~7.2 giờ) |
| 99.5% | ~216 phút (~3.6 giờ) |
| 99.9% | ~43 phút |
| 99.95% | ~22 phút |
| 99.99% | ~4 phút |

Bảng này giúp thấy rõ một điều dễ bị bỏ qua khi chỉ nhìn tỷ lệ %: khoảng cách giữa 99% và 99.9% nghe có vẻ nhỏ (chỉ 0.9 điểm phần trăm), nhưng tương ứng với khoảng cách gần **10 lần** về số phút downtime cho phép (432 phút so với 43 phút).

Đây là lý do vì sao việc "nâng SLO từ 99% lên 99.9%" không phải một điều chỉnh nhỏ về mặt kỹ thuật — nó thường đòi hỏi đầu tư đáng kể vào khả năng chịu lỗi của hệ thống (ví dụ nhiều instance dự phòng hơn, resilience pattern chặt chẽ hơn đã học ở P8) để có thể đạt được, không chỉ là "cố gắng hơn một chút".

---

## 6. Runbook: tài liệu hướng dẫn xử lý alert

**Định nghĩa (một câu):** Runbook là một **tài liệu hướng dẫn từng bước cụ thể** cho một loại alert/sự cố nhất định — mô tả chính xác người trực ban cần kiểm tra gì, chạy lệnh gì, liên hệ ai — với mục đích **giảm thời gian phản ứng** khi sự cố xảy ra, thay vì để người trực ban phải tự suy nghĩ từ đầu trong lúc đang chịu áp lực thời gian.

Ví dụ cụ thể, độc lập, chỉ minh hoạ đúng khái niệm runbook — gắn với chính quy tắc alert đã định nghĩa ở mục 3:

```text title="runbook-cpu-cao.txt (minh hoa 1 runbook toi thieu)"
RUNBOOK: cpu-cao-server-prod
Kich hoat khi: alert "cpu-cao-server-prod" (muc 3) duoc gui

BUOC 1: Mo dashboard Monitoring, xac nhan CPU van > 90%
        (loai truong hop alert da tu phuc hoi truoc khi ban mo may).

BUOC 2: Chay lenh xem tien trinh nao dang chiem CPU cao nhat tren server.
        Neu la tien trinh quen thuoc (vd job xu ly du lieu dinh ky) va
        du kien tu ket thuc trong vai phut -> theo doi them, KHONG can escalate.

BUOC 3: Neu CPU van cao sau 10 phut VA khong ro nguyen nhan
        -> escalate cho ky su phu trach he thong (xem danh sach lien he
        o cuoi runbook), kem log tu Buoc 2.

BUOC 4: Sau khi xu ly xong, ghi lai nguyen nhan thuc su vao he thong
        theo doi su co, de lan sau alert nay xay ra co the tra cuu nhanh hon.

Lien he escalation: [ten + so dien thoai ky su truc]
```

Điểm mấu chốt của runbook không phải "chứa nhiều thông tin kỹ thuật" — mà là **loại bỏ nhu cầu suy nghĩ từ đầu** ngay tại thời điểm áp lực cao nhất (giữa đêm, khách hàng đang bị ảnh hưởng).

Một người trực ban mới, chưa từng gặp sự cố này trước đây, vẫn có thể xử lý đúng quy trình chỉ bằng cách làm theo từng bước đã viết sẵn, không cần chờ người có kinh nghiệm hơn thức dậy trả lời điện thoại.

**Nếu thiếu runbook — hậu quả cụ thể:** khi alert "cpu-cao-server-prod" (mục 3) được gửi tới một người trực ban mới, chưa từng gặp tình huống này, họ phải **tự đoán** phải làm gì tiếp theo — kiểm tra cái gì trước, có nên restart server không, có nên gọi ai không.

Thời gian phản ứng kéo dài không phải vì thiếu kỹ năng kỹ thuật, mà vì thiếu **quy trình đã được chuẩn hoá trước**, khiến mỗi sự cố trở thành một lần "khám phá lại từ đầu" — kể cả khi đây là lần thứ 5 hệ thống gặp đúng vấn đề CPU cao giống nhau.

Một điểm quan trọng khác: runbook nên được **viết trước khi cần** (trong lúc bình tĩnh, không có sự cố đang xảy ra) và **cập nhật sau mỗi lần dùng thật** (bước "ghi lại nguyên nhân thực sự" ở Bước 4 trên chính là nguồn dữ liệu để cập nhật runbook — nếu nguyên nhân thực tế khác với những gì runbook giả định, runbook cần được sửa lại cho lần sau).

Một runbook viết một lần rồi không bao giờ cập nhật sẽ dần trở nên lạc hậu so với hệ thống thật, và tới một lúc nào đó hướng dẫn trong đó không còn khớp với cách hệ thống production thực sự vận hành.

Cần phân biệt rõ runbook với hai loại tài liệu khác dễ bị nhầm:

- **Runbook khác tài liệu kiến trúc (architecture doc):** tài liệu kiến trúc giải thích **hệ thống được thiết kế như thế nào và tại sao** (ví dụ "vì sao chọn message queue thay vì gọi HTTP trực tiếp") — hữu ích khi lập kế hoạch hoặc khi có kỹ sư mới gia nhập team, nhưng không phải thứ bạn mở ra giữa lúc sự cố đang xảy ra. Runbook chỉ tập trung vào **hành động cụ thể cần làm ngay**, bỏ qua phần giải thích "tại sao hệ thống được thiết kế vậy" — vì lúc sự cố xảy ra, người trực ban cần tốc độ, không cần một bài giảng kiến trúc.
- **Runbook khác README/tài liệu hướng dẫn cài đặt:** README hướng dẫn cách **thiết lập môi trường từ đầu** (ví dụ "clone repo, chạy `dotnet restore`, cấu hình connection string"). Runbook giả định hệ thống **đã chạy sẵn trong production** và đang gặp một vấn đề cụ thể — nó không dạy lại cách cài đặt từ đầu.

Một runbook tốt trong thực tế thường có thêm các phần sau, ngoài các bước đã minh hoạ ở ví dụ trên: **mức độ ưu tiên** (alert này cần xử lý trong bao lâu — vài phút hay có thể chờ tới sáng), **tác động dự kiến** (bao nhiêu người dùng bị ảnh hưởng, tính năng nào bị hỏng) để người trực ban đánh giá đúng mức độ khẩn cấp thật.

Thêm vào đó, **lệnh/script cụ thể có thể copy-paste chạy ngay** (không chỉ mô tả bằng lời "kiểm tra tiến trình nào đang chiếm CPU" mà viết thẳng câu lệnh cụ thể) — mục tiêu cuối cùng vẫn là giảm tối đa thời gian từ "nhận alert" tới "bắt đầu hành động đúng".

Một ví dụ runbook thứ hai, cho một loại alert khác hẳn (không phải hạ tầng, mà là một alert nghiệp vụ dựa trên SLI đã học ở mục 5), để thấy runbook áp dụng được cho nhiều loại tình huống, không chỉ "CPU cao":

```text title="runbook-ty-le-loi-thanh-toan.txt (minh hoa runbook cho alert nghiep vu)"
RUNBOOK: ty-le-loi-thanh-toan-cao
Kich hoat khi: SLI "ty le giao dich thanh toan thanh cong" giam duoi 95%
               trong 5 phut lien tuc (SLO noi bo la >= 99%)

MUC DO UU TIEN: Nghiem trong - xu ly ngay, khong cho toi sang
TAC DONG DU KIEN: Kem theo muc do giam, uoc tinh % khach hang
                  khong thanh toan duoc thanh cong ngay luc nay

BUOC 1: Mo dashboard Monitoring, xem ty le loi dang o muc nao va
        co dang tiep tuc giam hay da on dinh.

BUOC 2: Kiem tra health check (da hoc o P8) cua dich vu Thanh toan
        va dich vu Cong thanh toan ben thu ba (gateway ngan hang).
        Neu health check dich vu ben thu ba dang Unhealthy
        -> day la nguyen nhan ben ngoai, khong sua duoc tu phia minh,
           chuyen sang BUOC 3b.

BUOC 3a (loi tu phia minh): Xem log dich vu Thanh toan quanh thoi diem
        loi tang, tim exception hoac ma loi lien tuc xuat hien.

BUOC 3b (loi tu ben thu ba): Kiem tra trang thai circuit breaker
        (da hoc o P8) cho ket noi toi Cong thanh toan. Neu dang Open,
        day la hanh vi dung (tu bao ve, khong goi tiep toi dich vu loi).
        Thong bao cho khach hang qua trang trang thai he thong (status page),
        theo doi cho ben thu ba tu hoi phuc.

BUOC 4: Sau khi ty le thanh toan hoi phuc tren 99%, ghi lai nguyen nhan
        va thoi gian anh huong vao he thong theo doi su co - du lieu nay
        anh huong truc tiep toi SLI/SLO thang nay (muc 5).

Lien he escalation: [nhom Thanh toan] -> [nhom Ha tang] neu can
```

Runbook thứ hai này minh hoạ một điểm quan trọng: không phải mọi runbook đều dẫn tới "tự sửa được ngay" — Bước 3b mô tả rõ một tình huống hợp lệ và thường gặp là **nguyên nhân nằm ngoài khả năng kiểm soát trực tiếp** (một dịch vụ bên thứ ba đang lỗi).

Trong tình huống đó, hành động đúng không phải "cố sửa cái không sửa được", mà là **xác nhận đúng nguyên nhân, thông báo minh bạch, và theo dõi** — vẫn là một hành động rõ ràng, có ích, giảm thời gian người trực ban phải tự suy nghĩ "giờ phải làm gì", dù không giải quyết được gốc rễ ngay lập tức.

Runbook tốt phải tính tới cả nhánh "nguyên nhân do mình" và nhánh "nguyên nhân ngoài mình", không chỉ giả định mọi sự cố đều tự sửa được.

Một điểm cuối cùng đáng nhắc: cả hai runbook ví dụ trong mục này đều bắt đầu bằng "mở dashboard Monitoring" (mục 1) và kết thúc bằng "ghi lại nguyên nhân, ảnh hưởng tới SLI" (mục 5) — đây không phải sự trùng hợp. Nó cho thấy bốn khái niệm học trong chương này không tách rời nhau trong thực tế, mà luôn nối vào nhau theo một trình tự nhất quán. Mục 7 tiếp theo sẽ ghép rõ toàn bộ trình tự này thành một luồng hoàn chỉnh.

---

## 7. Ghép cả bốn khái niệm thành một luồng vận hành thực tế

Bốn khái niệm đã học (Monitoring, Alerting, SLI/SLO/SLA, runbook) không hoạt động tách biệt — chúng nối vào nhau thành một **vòng lặp vận hành liên tục**. Mục này đi qua toàn bộ vòng lặp đó bằng một tình huống cụ thể, xuyên suốt, để thấy rõ mỗi khái niệm khớp vào đâu trong dòng thời gian thật của một sự cố.

Tình huống: API Giỏ hàng của một trang thương mại điện tử, có SLO nội bộ "tỷ lệ request thành công >= 99.5% mỗi ngày" (mục 5), và SLA đã ký với đối tác lớn nhất là "tỷ lệ thành công >= 99%/tháng, nếu không đạt hoàn 3% phí dịch vụ".

```mermaid title="Vong lap Monitoring - Alerting - Runbook - SLI/SLO/SLA cho 1 su co"
graph LR
    A[Monitoring: dashboard hien thi<br/>ty le loi 5xx tang dan] --> B{Threshold-based alert:<br/>loi 5xx gt 5% trong 3 phut?}
    B -- Chua vuot nguong --> A
    B -- Da vuot nguong --> C[Alert gui toi nguoi truc ban<br/>qua SMS/Slack, co leo thang]
    C --> D[Nguoi truc ban mo Runbook<br/>tuong ung voi alert nay]
    D --> E[Lam theo tung buoc trong Runbook:<br/>xac nhan qua Monitoring, tim nguyen nhan,<br/>xu ly hoac escalate]
    E --> F[Su co duoc xu ly xong,<br/>ty le loi tro lai binh thuong]
    F --> G[Ghi lai nguyen nhan + thoi gian anh huong<br/>-> anh huong SLI thang nay]
    G --> H{SLI thang nay con dat<br/>SLO 99.5%/ngay khong?}
    H -- Con dat --> A
    H -- Khong dat --> I[Xem xet co anh huong SLA<br/>voi doi tac khong]
```

Đọc lại toàn bộ vòng lặp theo đúng thứ tự đã học trong chương này:

1. **Monitoring** (mục 1) liên tục hiển thị tỷ lệ lỗi 5xx trên dashboard — tại thời điểm này, nếu không có Alerting, chỉ có giá trị nếu ai đó đang chủ động xem đúng lúc (đúng vấn đề mục 0 đã nêu).
2. **Threshold-based alert** (mục 3) liên tục so sánh tỷ lệ lỗi với ngưỡng đã đặt (5% trong 3 phút liên tục) — khi vượt ngưỡng, **Alerting** (mục 2) kích hoạt, tự động gửi thông báo mà không cần ai đang xem dashboard.
3. Người trực ban nhận alert, mở **runbook** (mục 6) tương ứng — thay vì tự suy nghĩ từ đầu, họ làm theo các bước đã chuẩn bị trước: xác nhận qua Monitoring, tìm nguyên nhân, xử lý hoặc escalate.
4. Sau khi xử lý xong, dữ liệu về sự cố này (bao gồm thời gian ảnh hưởng) được ghi lại — đây chính là dữ liệu đóng góp vào **SLI** (mục 5) của tháng, tính vào tỷ lệ thành công thực tế.
5. Nếu SLI thực tế cuối tháng vẫn đạt SLO nội bộ (99.5%/ngày duy trì suốt tháng), không có gì cần làm thêm. Nếu SLI giảm xuống dưới SLA đã ký với đối tác (99%/tháng), team cần xem xét trách nhiệm hợp đồng và có thể phải xử lý việc hoàn phí.

Điểm quan trọng nhất cần rút ra từ toàn bộ vòng lặp này: **mỗi khái niệm giải quyết đúng một khoảng trống mà khái niệm trước nó để lại**.

Không có Monitoring, không có dữ liệu gì để dựa vào. Có Monitoring nhưng không có Alerting, dữ liệu chỉ có giá trị khi có người tình cờ đang xem.

Có Alerting nhưng không có runbook, người nhận alert biết "có vấn đề" nhưng không biết làm gì tiếp theo, tốn thời gian tự suy nghĩ ngay lúc cần nhanh nhất.

Có runbook nhưng không đo SLI, team không biết liệu các sự cố đã xử lý có đang ảnh hưởng tới cam kết SLO/SLA hay không, tới khi khách hàng phàn nàn hoặc yêu cầu bồi thường mới biết.

Bốn khái niệm này, dù học riêng lẻ trong chương này để hiểu rõ từng cái, trong thực tế luôn cần được thiết kế và vận hành **cùng nhau** như một chuỗi liên tục.

---

## Cạm bẫy & thực chiến

- **Nhầm "có Monitoring" là "có Alerting":** một dashboard đẹp, đầy đủ chỉ số vẫn hoàn toàn vô dụng nếu không có ai xem đúng lúc sự cố xảy ra — như ví dụ mục 0, sự cố có thể kéo dài hàng giờ trước khi bị phát hiện, dù dữ liệu đã "có sẵn" trên dashboard suốt thời gian đó.
  Cách kiểm tra nhanh một hệ thống có thật sự có Alerting hay không: tự hỏi "nếu chỉ số X vượt ngưỡng lúc 3 giờ sáng, có ai/cái gì chủ động báo cho người vận hành không, hay chỉ có dữ liệu nằm im trên dashboard chờ ai đó tình cờ mở lên xem?".
- **Đặt ngưỡng alert không dựa trên hành vi thực tế đã quan sát:** copy ngưỡng từ một hệ thống khác (ví dụ "CPU > 80%" học từ một bài viết trên mạng) mà không xem hệ thống của mình bình thường vận hành ở mức CPU bao nhiêu — dẫn tới alert liên tục cho dao động bình thường (nếu ngưỡng quá thấp so với baseline thật) hoặc bỏ lỡ sự cố thật (nếu ngưỡng quá cao).
  Cách tránh: quan sát Monitoring (mục 1) trong ít nhất vài ngày/vài tuần vận hành bình thường trước khi đặt threshold, để biết rõ "bình thường" của chính hệ thống này trông như thế nào.
- **Gán cùng mức độ nghiêm trọng cho mọi alert:** khi một sự cố không thể hành động ngay (ví dụ chỉ cần xem xét vào giờ làm việc) được gửi bằng SMS lúc 3 giờ sáng giống như một sự cố nghiêm trọng thật, người nhận dần học cách coi thường mọi SMS — đây chính là cơ chế hình thành alert fatigue (mục 4), và hậu quả là alert thật sự nghiêm trọng cũng bị lướt qua.
- **Nhầm SLO là SLA khi báo cáo ra ngoài:** một kỹ sư nói với khách hàng "chúng tôi cam kết uptime 99.9%" trong khi 99.9% chỉ là mục tiêu nội bộ (SLO) chưa từng được đưa vào hợp đồng — nếu hệ thống không đạt được số này, khách hàng có thể yêu cầu bồi thường dựa trên một cam kết mà công ty chưa bao giờ chính thức đồng ý ràng buộc.
- **Không có khoảng đệm giữa SLO và SLA:** đặt SLO bằng chính xác số SLA đã ký với khách hàng khiến team không còn không gian phát hiện và xử lý vấn đề ở tầng nội bộ trước khi nó leo thang thành vi phạm hợp đồng thật.
- **Viết runbook một lần rồi không cập nhật:** hệ thống thay đổi liên tục (thêm service mới, đổi hạ tầng), nhưng runbook vẫn mô tả quy trình cũ — người trực ban làm theo runbook lỗi thời, tốn thời gian nhận ra các bước không còn khớp với thực tế, rồi phải tự tìm cách xử lý ngoài quy trình đúng vào lúc cần nó chính xác nhất.
- **Đặt threshold tuyệt đối cố định cho một chỉ số có hành vi thay đổi theo thời điểm:** ví dụ đặt "số request/giây < 50 thì báo" dựa trên baseline buổi sáng, rồi alert kêu liên tục mỗi đêm khi traffic tự nhiên thấp hơn — vấn đề không phải hệ thống lỗi, mà ngưỡng không phản ánh đúng hành vi bình thường theo giờ, dẫn tới một dạng alert fatigue khác (nhiễu do sai ngưỡng theo thời gian, không phải do quá nhiều chỉ số).
- **Nhầm runbook với tài liệu kiến trúc hoặc README cài đặt:** nhồi quá nhiều lời giải thích "tại sao hệ thống được thiết kế thế này" hoặc hướng dẫn cài đặt từ đầu vào runbook, khiến người trực ban phải đọc lướt qua nhiều đoạn không liên quan để tìm ra bước hành động thật — làm chậm chính mục tiêu runbook được tạo ra để giải quyết (giảm thời gian phản ứng).
- **Không có cơ chế leo thang (escalation) khi người trực ban đầu tiên không phản hồi:** alert được gửi đi, nhưng nếu không có quy trình tự động gọi tiếp người thứ hai khi người đầu tiên không xác nhận trong một khoảng thời gian, một alert quan trọng có thể "biến mất" lặng lẽ chỉ vì đúng lúc đó người trực ban chính không nghe thấy điện thoại — hệ thống Alerting về lý thuyết đã "làm đúng việc của nó" (đã gửi) nhưng thực tế không ai tiếp nhận.
- **Chỉ đo SLI ở mức tổng thể toàn hệ thống, không tách theo từng dịch vụ/API quan trọng:** một SLI "uptime toàn hệ thống 99.9%" có thể che khuất việc một API quan trọng (ví dụ API Thanh toán) đang có tỷ lệ lỗi cao hơn nhiều so với các API khác ít quan trọng hơn — nếu SLI được tính trung bình gộp chung, vấn đề nghiêm trọng ở một điểm cụ thể có thể bị "hoà loãng" bởi các phần khác đang hoạt động tốt, khiến team lầm tưởng mọi thứ vẫn ổn khi nhìn con số tổng.

---

## Bài tập

**Bài 1 (phân biệt):** Team của bạn có một dashboard hiển thị tỷ lệ lỗi 5xx của API theo thời gian thực, cập nhật mỗi 10 giây. Không có bất kỳ cơ chế gửi thông báo tự động nào. Đây là Monitoring, Alerting, hay cả hai? Nếu tỷ lệ lỗi 5xx tăng vọt lên 40% vào lúc 4 giờ sáng khi không có ai đang làm việc, điều gì sẽ xảy ra?

??? success "Lời giải + vì sao"
    Đây chỉ là **Monitoring** — có thu thập và hiển thị liên tục, nhưng không có bất kỳ cơ chế tự động phát hiện + báo động nào (đó mới là Alerting).

    Lúc 4 giờ sáng khi tỷ lệ lỗi tăng vọt, dữ liệu vẫn hiển thị đúng trên dashboard, nhưng **không ai biết** vì không ai đang mở dashboard xem — sự cố sẽ tiếp diễn không bị phát hiện cho tới khi có người chủ động mở dashboard (ví dụ đầu giờ làm việc sáng) hoặc khách hàng báo lỗi. Đây đúng là tình huống mục 0 minh hoạ: có dữ liệu không đồng nghĩa có người biết.

**Bài 2 (thiết kế threshold):** Hệ thống của bạn có độ trễ (latency) p99 bình thường dao động 200-400ms trong giờ cao điểm, và đôi khi tăng vọt lên 600ms trong vài giây rồi tự trở lại bình thường (do garbage collection hoặc traffic tăng đột ngột thoáng qua). Hãy thiết kế một threshold-based alert hợp lý cho latency, tránh cả hai lỗi: alert quá nhạy (báo cả dao động bình thường) và alert quá lười (báo quá muộn khi sự cố đã ảnh hưởng nặng người dùng).

??? success "Lời giải + vì sao"
    Ví dụ hợp lý: "**nếu** latency p99 > 800ms **trong** ít nhất 3 phút liên tục **thì** gửi alert mức nghiêm trọng".

    Giải thích từng phần: ngưỡng 800ms cao hơn hẳn cả baseline bình thường (200-400ms) và cả các đợt tăng vọt thoáng qua (600ms), nên tránh được false positive từ dao động GC/traffic bình thường.

    Yêu cầu "liên tục 3 phút" (không phải một lần đo tức thời) lọc bỏ chính xác loại nhiễu "tăng vọt vài giây rồi tự phục hồi" mà đề bài mô tả — nếu chỉ cần một lần đo vượt 800ms đã báo, những đợt GC ngắn hạn (có thể chạm 800ms trong 1-2 giây) sẽ gây báo động giả liên tục. Ngược lại, 3 phút vẫn đủ ngắn để phát hiện sự cố thật kịp thời (không lười tới mức phải chờ hàng chục phút).

    **Vì sao đây là "hợp lý" chứ không phải "duy nhất đúng":** ngưỡng cụ thể phụ thuộc vào baseline thực tế đã quan sát của từng hệ thống (mục Cạm bẫy đã nhắc: không nên copy ngưỡng từ hệ thống khác) — điểm quan trọng cần nắm là **cách suy luận** (ngưỡng phải cao hơn hẳn dao động bình thường đã biết, khoảng thời gian phải đủ để lọc nhiễu ngắn hạn nhưng không quá dài tới mức chậm phát hiện), không phải một con số cụ thể để nhớ máy móc.

**Bài 3 (SLI/SLO/SLA):** Công ty bạn vận hành một API thanh toán. Đội kỹ thuật đo được uptime thực tế tháng vừa qua là 99.95%. Nội bộ team đặt mục tiêu uptime tối thiểu 99.9%/tháng để tự đánh giá chất lượng vận hành. Hợp đồng đã ký với khách hàng lớn nhất ghi rõ "uptime tối thiểu 99.5%/tháng, nếu không đạt sẽ hoàn 5% phí dịch vụ tháng đó". Hãy gọi tên đúng SLI/SLO/SLA cho từng con số trong tình huống này, và cho biết tháng này công ty có phải hoàn tiền không.

??? success "Lời giải + vì sao"
    - **99.95%** (số đo thực tế tháng vừa qua) là **SLI** — chỉ số quan sát được, không phải mục tiêu hay cam kết.
    - **99.9%** (mục tiêu nội bộ team tự đặt) là **SLO**.
    - **99.5% + điều khoản hoàn 5% phí** (ghi trong hợp đồng với khách hàng) là **SLA**.

    Tháng này công ty **không phải** hoàn tiền, vì SLI thực tế (99.95%) cao hơn cả SLO nội bộ (99.9%) và cao hơn nhiều so với ngưỡng SLA đã ký (99.5%) — không có vi phạm hợp đồng nào xảy ra.

    Đáng chú ý: SLI (99.95%) còn cao hơn cả SLO (99.9%), nghĩa là team đang vận hành **tốt hơn** mục tiêu nội bộ họ tự đặt ra — đây là kết quả tốt, không phải một sai lệch cần xử lý.

**Bài 4 (thiết kế runbook):** Team của bạn vừa thêm một alert mới: "nếu dung lượng đĩa trống của server database dưới 15% thì báo mức nghiêm trọng". Đây là lần đầu alert này được tạo ra — chưa có runbook nào cho nó. Hãy phác thảo tối thiểu bốn bước một runbook cho alert này nên có, dựa trên khuôn mẫu đã thấy ở hai ví dụ runbook trong mục 6.

??? success "Lời giải + vì sao"
    Một phác thảo hợp lý (không phải "duy nhất đúng" — quan trọng là đúng khuôn mẫu, không phải đúng từng chữ):

    - **Bước 1:** Mở dashboard Monitoring, xác nhận dung lượng đĩa hiện tại và tốc độ giảm gần đây (đang giảm nhanh hay đã chậm lại) — để biết còn bao lâu nữa thì đầy hoàn toàn.
    - **Bước 2:** Kiểm tra thư mục/bảng nào đang chiếm dung lượng lớn bất thường so với bình thường (ví dụ log file phình to do một lỗi đang lặp liên tục, hoặc bảng dữ liệu tăng nhanh bất thường do một job không dọn dữ liệu cũ).
    - **Bước 3:** Nếu xác định được nguyên nhân cụ thể và có thể xử lý an toàn (ví dụ xoá log cũ đã có chính sách lưu trữ riêng), xử lý ngay. Nếu không rõ nguyên nhân hoặc việc xoá dữ liệu có rủi ro, escalate cho kỹ sư phụ trách database, kèm số liệu đã thu thập ở Bước 1-2.
    - **Bước 4:** Sau khi xử lý xong, ghi lại nguyên nhân thật và cách xử lý vào hệ thống theo dõi sự cố, đồng thời xem xét liệu ngưỡng "15%" đã đủ sớm chưa hay cần điều chỉnh (ví dụ tăng lên 20% nếu 15% được xác nhận là quá gấp để xử lý kịp).

    **Vì sao đúng khuôn mẫu:** cả hai runbook ví dụ trong mục 6 đều theo cùng cấu trúc — xác nhận tình trạng qua Monitoring trước, tìm nguyên nhân cụ thể, phân nhánh giữa "tự xử lý được" và "cần escalate", rồi kết thúc bằng việc ghi lại để cải thiện cho lần sau. Đây là khuôn mẫu chung, không phải nội dung cụ thể cần nhớ máy móc theo từng loại alert.

---

## Tự kiểm tra

1. Monitoring và Alerting khác nhau ở điểm cốt lõi nào?

    ??? note "Đáp án"
        Monitoring thu thập và **hiển thị** chỉ số, cần con người chủ động xem để phát hiện vấn đề. Alerting **tự động phát hiện và chủ động báo** khi chỉ số vượt ngưỡng bất thường, không cần ai đang ngồi xem màn hình 24/7.

2. Một quy tắc "CPU > 90% trong 5 phút liên tục thì báo" — vì sao cần điều kiện "trong 5 phút liên tục", không chỉ "CPU > 90%" tại một thời điểm?

    ??? note "Đáp án"
        Để tránh báo động giả (false positive) từ những đợt CPU tăng vọt thoáng qua và tự phục hồi ngay (ví dụ do một tác vụ nền ngắn hạn) — đây không phải sự cố thật. Yêu cầu "liên tục trong một khoảng thời gian" lọc bỏ nhiễu ngắn hạn, chỉ báo khi tình trạng bất thường thật sự kéo dài.

3. Alert fatigue là gì, và vì sao nó nguy hiểm hơn là chỉ "gây phiền"?

    ??? note "Đáp án"
        Alert fatigue là hiện tượng nhận quá nhiều alert (phần lớn không quan trọng) đến mức người vận hành dần lơ là mọi alert, kể cả những alert thật sự nghiêm trọng. Nó nguy hiểm vì làm mất chính công cụ được tạo ra để phát hiện sớm sự cố — khi alert thật sự quan trọng xuất hiện, nó bị bỏ qua giống như hàng trăm alert vô hại trước đó.

4. Phân biệt SLI, SLO, SLA bằng một câu cho mỗi khái niệm.

    ??? note "Đáp án"
        SLI là chỉ số đo được thực tế (ví dụ uptime đo được tháng này). SLO là mục tiêu nội bộ team tự đặt cho SLI đó (ví dụ mục tiêu uptime >= 99.9%). SLA là cam kết chính thức với khách hàng, có ràng buộc hợp đồng (ví dụ hoàn tiền nếu uptime dưới 99.5%).

5. Vì sao SLO thường được đặt khắt khe hơn SLA, không đặt bằng nhau?

    ??? note "Đáp án"
        Để tạo một khoảng đệm an toàn — nếu SLO và SLA bằng nhau, bất kỳ dao động nhỏ khiến SLI tụt dưới mục tiêu nội bộ cũng đồng thời là vi phạm hợp đồng với khách hàng. Đặt SLO khắt khe hơn cho phép team phát hiện và xử lý vấn đề ở tầng nội bộ trước khi nó leo thang thành hậu quả pháp lý thật.

6. Runbook giải quyết vấn đề gì mà chỉ có Alerting (không có runbook) không giải quyết được?

    ??? note "Đáp án"
        Alerting chỉ báo "có vấn đề xảy ra", nhưng không hướng dẫn phải làm gì tiếp theo. Runbook cung cấp quy trình xử lý từng bước cụ thể, giúp người trực ban (kể cả người mới, chưa từng gặp sự cố này) phản ứng nhanh và đúng, không cần tự suy nghĩ từ đầu ngay lúc đang chịu áp lực thời gian.

7. Một team báo cáo với khách hàng "SLI uptime tháng này đạt 99.92%" như một cam kết ràng buộc cho các tháng sau. Đây có phải cách dùng đúng khái niệm SLI không? Vì sao?

    ??? note "Đáp án"
        Không đúng. SLI chỉ là một số đo lịch sử (chỉ số quan sát được), không mang ý nghĩa dự đoán hay ràng buộc cho tương lai. Cam kết ràng buộc với khách hàng là vai trò của SLA, không phải SLI — nhầm lẫn này có thể khiến khách hàng hiểu sai rằng con số 99.92% là một đảm bảo hợp đồng.

8. Một team có runbook chi tiết cho alert "CPU cao", nhưng runbook đó được viết một năm trước và hệ thống đã đổi sang một kiến trúc khác (thêm hai service mới) mà chưa ai cập nhật lại runbook. Điều gì có khả năng xảy ra khi alert này được kích hoạt lần tới?

    ??? note "Đáp án"
        Người trực ban làm theo các bước trong runbook cũ, nhưng các bước đó (ví dụ lệnh kiểm tra, tên service cần xem) không còn khớp với kiến trúc hiện tại — họ mất thời gian nhận ra runbook đã lỗi thời, rồi phải tự tìm cách xử lý ngoài quy trình đúng vào lúc cần phản ứng nhanh nhất. Đây là lý do runbook cần được cập nhật sau mỗi lần dùng thật và mỗi khi hệ thống thay đổi đáng kể, không chỉ viết một lần rồi để đó.

9. Trong runbook thứ hai ở mục 6 (tỷ lệ lỗi thanh toán), Bước 3b mô tả tình huống nguyên nhân nằm ở một dịch vụ bên thứ ba, không sửa được trực tiếp. Vì sao đây vẫn là một bước runbook hợp lệ, dù nó không "sửa" được sự cố ngay?

    ??? note "Đáp án"
        Vì mục tiêu của runbook không phải luôn luôn "tự sửa được mọi thứ ngay", mà là loại bỏ nhu cầu suy nghĩ từ đầu cho người trực ban. Xác nhận đúng nguyên nhân (lỗi từ bên thứ ba, không phải từ hệ thống của mình), biết hành động đúng là thông báo minh bạch và theo dõi (thay vì cố gắng "sửa" một thứ không thuộc quyền kiểm soát của mình), vẫn là một hướng dẫn rõ ràng và có ích, giúp người trực ban không mất thời gian đoán việc cần làm.

---

??? abstract "DEEP DIVE: alert routing theo mức độ nghiêm trọng, và mối liên hệ với health check/circuit breaker đã học"
    Trong thực tế, hệ thống Alerting trưởng thành không gửi mọi alert theo cùng một cách — chúng phân loại theo **mức độ nghiêm trọng** (severity) và định tuyến (routing) khác nhau.

    Alert mức "critical" (ảnh hưởng người dùng ngay, cần hành động trong vài phút) gửi qua kênh gây chú ý mạnh (SMS, gọi điện tự động, PagerDuty đánh thức người trực ban giữa đêm). Alert mức "warning" (cần chú ý nhưng không khẩn cấp) gửi qua kênh ít gây gián đoạn hơn (tin nhắn Slack, không đánh thức ai). Alert mức "info" (chỉ để ghi nhận xu hướng) chỉ xuất hiện trên dashboard Monitoring, không gửi thông báo chủ động nào cả.

    Cách phân loại này chính là công cụ kỹ thuật chống alert fatigue (mục 4) — không phải bằng cách giảm số lượng alert, mà bằng cách đảm bảo **mức độ khẩn cấp của kênh thông báo khớp đúng với mức độ nghiêm trọng thật** của vấn đề.

    Một câu hỏi hay gặp: Alerting có thay thế được health check (đã học ở P8) không? Không — hai cơ chế bổ trợ, không thay thế nhau.

    Health check trả lời câu hỏi tức thời "app này đang khỏe không" cho **hạ tầng** (load balancer, orchestrator) tự động hành động ngay (rút traffic, restart) mà không cần con người. Alerting trả lời câu hỏi khác — "có điều gì bất thường cần **con người** chú ý" — và thường hoạt động ở một tầng rộng hơn, tổng hợp dữ liệu theo thời gian (ví dụ "tỷ lệ Unhealthy trong 10 phút qua đã vượt X%") thay vì chỉ một lần gọi health check đơn lẻ.

    Trong thực tế, kết quả health check thường chính là một trong những SLI (mục 5) được dùng để tính SLO uptime, và một chuỗi health check thất bại liên tục thường tự nó kích hoạt một alert riêng — hai hệ thống nối vào nhau qua chính dữ liệu SLI, không phải trùng lặp chức năng.

    Ở quy mô lớn hơn, một khái niệm liên quan là **error budget**: nếu SLO là 99.9% uptime mỗi tháng, "error budget" là 0.1% thời gian còn lại được phép "tiêu" cho sự cố/downtime có kiểm soát (ví dụ triển khai một thay đổi rủi ro, hoặc bảo trì định kỳ) mà vẫn không vi phạm SLO.

    Khi error budget còn nhiều, team có thể chấp nhận rủi ro cao hơn (deploy nhanh, thử tính năng mới); khi error budget gần hết, team nên ưu tiên ổn định hơn tốc độ — đây là cách một số tổ chức dùng SLO không chỉ để "chấm điểm" mà để **ra quyết định kỹ thuật** hàng ngày, kết nối trực tiếp khái niệm SLO (mục 5) với văn hoá vận hành thực tế.

    Một ví dụ số cụ thể để thấy error budget hoạt động ra sao trong một tháng: SLO là 99.9% uptime/tháng, dựa theo bảng quy đổi ở mục 5, error budget tương ứng khoảng 43 phút downtime được "cho phép" tiêu trong cả tháng.

    Giả sử ngày 3 của tháng, một sự cố (đã được Alerting phát hiện và runbook xử lý theo đúng luồng ở mục 7) gây downtime 15 phút. Error budget còn lại của tháng là 43 - 15 = 28 phút.

    Nếu team đang định triển khai một thay đổi hạ tầng rủi ro (ví dụ nâng cấp phiên bản database) vào ngày 20, họ có thể tự hỏi: "nếu thay đổi này thất bại và gây downtime, chúng ta còn đủ error budget để chịu được không?"

    Nếu ước tính rủi ro downtime của thay đổi đó lớn hơn 28 phút còn lại, đây là tín hiệu rõ ràng để **trì hoãn** thay đổi rủi ro đó sang tháng sau (khi error budget được "làm mới" lại đầy 43 phút), hoặc đầu tư thêm vào kế hoạch rollback nhanh để giảm rủi ro downtime ước tính. Đây chính là cách error budget biến một khái niệm trừu tượng (SLO) thành một **con số cụ thể có thể dùng để ra quyết định** hàng ngày, không chỉ nằm im trên một báo cáo cuối tháng.

    Một khía cạnh tổ chức thường bị bỏ qua khi mới học Alerting: **ai chịu trách nhiệm khi alert kêu**. Ở các team nhỏ, thường có một danh sách "ca trực" (on-call rotation) — mỗi tuần một người khác nhau trong team chịu trách nhiệm chính nhận và xử lý alert ngoài giờ, luân phiên để không ai phải chịu áp lực trực 24/7 mãi mãi.

    Việc quay vòng ca trực có liên hệ trực tiếp với chất lượng runbook (mục 6): nếu runbook đầy đủ và rõ ràng, người trực ban tuần này (có thể không phải người quen thuộc nhất với hệ thống) vẫn xử lý được đúng quy trình. Nếu không có runbook, chất lượng xử lý sự cố phụ thuộc hoàn toàn vào việc "ai đang trực tuần này có kinh nghiệm với đúng vấn đề này hay không" — một sự phụ thuộc rủi ro và không bền vững khi team phát triển lớn hơn.

    Một thực hành liên quan khác, thường xuất hiện sau khi một sự cố nghiêm trọng đã được xử lý xong, là **postmortem** (báo cáo sau sự cố) — một tài liệu viết lại toàn bộ dòng thời gian sự cố (khi nào alert kêu, khi nào ai xử lý, khi nào giải quyết xong), nguyên nhân gốc rễ, và hành động cải thiện cụ thể để tránh lặp lại (ví dụ "thêm một alert mới cho dấu hiệu sớm hơn", hoặc "cập nhật runbook thêm bước X").

    Postmortem tốt nhất theo văn hoá "blameless" — tập trung vào **quy trình và hệ thống** cần cải thiện, không quy trách nhiệm cá nhân cho người đã xử lý sự cố — vì mục tiêu là học được gì từ sự cố để hệ thống Monitoring/Alerting/runbook tốt hơn cho lần sau, không phải tìm người để đổ lỗi. Đây chính là cách vòng lặp cải thiện liên tục của cả ba khái niệm mới học trong chương này (Monitoring cho biết có gì bất thường, Alerting báo đúng lúc, runbook hướng dẫn xử lý) khép lại và tự hoàn thiện qua thời gian.

    Cuối cùng, một câu hỏi hay gặp khi so sánh với các chương khác: chương này có liên quan gì tới CI/CD (chương `cicd-github-actions.md`) không? Có, nhưng ở một mối liên hệ gián tiếp.

    Một pipeline CI/CD tốt giúp **giảm khả năng đưa lỗi vào production** ngay từ đầu (gate chất lượng trước khi deploy), còn Monitoring/Alerting/runbook xử lý **sau khi** một vấn đề đã lọt vào production, bất kể nguyên nhân gì (kể cả những vấn đề không liên quan tới code, ví dụ hạ tầng vật lý bên dưới gặp cố).

    Hai nhóm thực hành này không thay thế nhau — một pipeline CI/CD xanh 100% vẫn không đảm bảo hệ thống production không bao giờ gặp sự cố (ví dụ do tải tăng bất ngờ, hoặc phụ thuộc bên thứ ba lỗi), đây là lý do một hệ thống production trưởng thành luôn cần cả hai nhóm thực hành song song: CI/CD để giảm lỗi trước khi deploy, Monitoring/Alerting/runbook để phát hiện và xử lý nhanh những gì CI/CD không thể ngăn được.

Tiếp theo -> container orchestration co ban
