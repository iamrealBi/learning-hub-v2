---
tier: core
status: core
owner: core-team
verified_on: "2026-07-05"
dotnet_version: "10.0"
bloom: "Phân biệt"
requires: [p9-cicd]
est_minutes_fast: 25
---

# Cloud Fundamentals: IaaS, PaaS, SaaS

!!! info "Bạn đang ở đây"
    **cần trước:** đã hiểu CI/CD — biết pipeline tự động build/test (CI) và tự động deploy sau khi CI xanh (CD) đưa code lên môi trường chạy thật.
    **mở khoá:** hiểu **nơi** code sau khi deploy thực sự "sống" — thuê máy chủ vật lý, thuê máy chủ ảo trên cloud, thuê nền tảng sẵn có, hay chỉ dùng phần mềm có sẵn — và nền tảng khái niệm để đọc các chương container orchestration, Infrastructure as Code, monitoring.

> **Mục tiêu:** **Phân biệt** được On-premise, IaaS, PaaS, SaaS theo đúng một tiêu chí duy nhất (tầng nào người dùng phải tự quản lý), **giải thích** được vì sao doanh nghiệp chuyển từ tự lắp server sang thuê cloud, và **nhận diện** được scale up với scale out khi đọc một tình huống vận hành cụ thể.

---

## 0. Đoán nhanh trước khi học

Một công ty khởi nghiệp bán hàng online. Tháng 1, họ mua **2 máy chủ vật lý** (mỗi máy 20 triệu đồng), thuê kỹ thuật viên lắp đặt tại một trung tâm dữ liệu thuê chỗ (colocation), mất **3 tuần** từ lúc đặt hàng máy tới lúc website chạy được. Hệ thống chạy ổn với khoảng 500 khách/ngày.

Tháng 11, công ty chạy chương trình giảm giá Black Friday. Lượng khách truy cập tăng gấp **40 lần** trong đúng 2 ngày (500 → 20.000 khách/ngày), rồi giảm về mức bình thường ngay sau đó. Với 2 máy chủ vật lý đã mua, website sập vì quá tải — công ty **không thể** mua thêm máy chủ mới và lắp đặt kịp trong vài ngày (quy trình mua + lắp đặt mất nhiều tuần như tháng 1), và ngay cả khi mua được, 2 máy chủ thừa ra sau Black Friday sẽ **nằm không dùng** cả năm, vẫn tốn tiền điện, tiền thuê chỗ, tiền bảo trì.

??? question "Đoán trước, đáp án ở dưới"
    Gợi ý: vấn đề cốt lõi không phải là công ty "tính sai" số máy cần mua — mà là mô hình **mua đứt phần cứng vật lý** có đặc điểm gì khiến nó không hợp với loại tải "tăng vọt rồi giảm" như Black Friday?

??? note "Đáp án"
    Mua phần cứng vật lý gắn liền với hai đặc điểm không thể tránh: **chi phí trả trước** (phải trả tiền mua máy trước khi biết chắc có cần dùng hết công suất đó không) và **thời gian lắp đặt cố định** (dù công ty phát hiện cần thêm máy vào phút cuối, quy trình đặt hàng - vận chuyển - lắp đặt - cấu hình vẫn mất nhiều tuần, không thể rút ngắn bằng tiền). Tải của Black Friday tăng rồi giảm trong vài ngày — không có mô hình mua phần cứng nào khớp với nhịp độ đó. Mục 1 gọi tên chính xác mô hình công ty đang dùng (on-premise) và mục 2 giới thiệu giải pháp: thuê tài nguyên qua Internet, trả tiền theo giờ dùng, có thể tăng/giảm trong vài phút.

---

## 1. On-premise: tự quản lý toàn bộ từ phần cứng

**Định nghĩa:** On-premise (tại chỗ) là mô hình trong đó tổ chức **tự mua, tự lắp đặt, và tự quản lý toàn bộ** hạ tầng — từ phần cứng vật lý (máy chủ, ổ cứng, dây mạng), hệ điều hành, phần mềm runtime, cho tới ứng dụng và dữ liệu — thường đặt tại văn phòng riêng hoặc một trung tâm dữ liệu đi thuê chỗ (colocation).

Tình huống mục 0 là ví dụ độc lập, minh hoạ đúng một khái niệm này:

```text title="Vi du: chi phi va thoi gian cua mo hinh on-premise"
Thang 1:
  - Mua 2 may chu vat ly: 2 x 20 trieu = 40 trieu dong (tra TRUOC, mot lan)
  - Thue cho dat may (colocation): phi hang thang co dinh
  - Thoi gian tu dat hang toi chay duoc: 3 TUAN
  - Cong ty tu cai he dieu hanh, tu cai .NET runtime, tu cau hinh mang, tu vá lỗi bảo mật OS

Thang 11 (Black Friday, tai tang 40 lan trong 2 ngay):
  - Can them may -> KHONG THE mua + lap dat kip trong vai ngay (quy trinh giong thang 1)
  - Website sap vi 2 may hien co qua tai
  - Sau Black Friday: neu da mua kip may moi, may do "thua" ca nam, van ton tien dien/bao tri
```

Đây là hệ quả trực tiếp của việc tổ chức tự chịu trách nhiệm **mọi tầng**, bắt đầu từ tầng thấp nhất (phần cứng). Không có gì sai về mặt kỹ thuật khi vận hành on-premise — nhiều tổ chức lớn (ngân hàng, chính phủ) vẫn chọn on-premise vì lý do kiểm soát dữ liệu hoặc quy định pháp lý. Vấn đề chỉ xuất hiện rõ khi **tải thay đổi nhanh và không đoán trước được** — đúng tình huống Black Friday.

**Điều gì xảy ra khi dùng sai:** nếu một tổ chức vận hành on-premise nhưng đội ngũ đánh giá sai lượng tải tối đa (mua thiếu máy cho tải đỉnh dự kiến, hoặc không có kế hoạch dự phòng khi phần cứng hỏng), hậu quả là **downtime kéo dài hàng tuần** trong lúc chờ mua/lắp máy mới — không giống như trên cloud, nơi thêm tài nguyên chỉ mất vài phút (mục 2-3 sẽ chỉ rõ vì sao). Đây chính là động lực kinh doanh khiến "cloud computing" (tính toán trên mây — thuê tài nguyên qua Internet, không tự sở hữu phần cứng) trở thành lựa chọn phổ biến từ giữa những năm 2000, và là điểm chuẩn để mục 2, 3, 4 so sánh.

---

## 2. IaaS: thuê máy chủ ảo, tự quản lý từ hệ điều hành trở lên

**Định nghĩa:** IaaS (Infrastructure as a Service — hạ tầng dưới dạng dịch vụ) là mô hình thuê **máy chủ ảo** (và các tài nguyên hạ tầng khác như ổ đĩa, mạng) qua Internet từ một nhà cung cấp cloud (ví dụ AWS, Azure, Google Cloud) — nhà cung cấp chịu trách nhiệm phần cứng vật lý và lớp ảo hoá, còn người dùng **tự cài đặt và quản lý** hệ điều hành, runtime, ứng dụng, và dữ liệu trên máy chủ ảo đó.

Ví dụ cụ thể: thuê một máy chủ ảo (thường gọi là VM — Virtual Machine) trên một cloud provider, ví dụ một "Azure Virtual Machine" hoặc "AWS EC2 instance". Sau khi thuê xong:

```text title="Vi du: thue 1 VM tren cloud provider (IaaS) - viec NGUOI DUNG phai tu lam"
Buoc 1: Chon cau hinh VM (bao nhieu CPU, RAM, o dia) -> bam nut thue -> co VM trong VAI PHUT
        (khac han "3 TUAN" cua on-premise o muc 1)

Buoc 2: VM moi thue la mot may TRONG - nguoi dung phai TU:
        - Cai he dieu hanh (vi du Ubuntu Linux hoac Windows Server)
        - Cai .NET runtime de chay ung dung ASP.NET Core
        - Cau hinh firewall, mo cong mang can thiet
        - Cai va cau hinh web server (vi du Nginx lam reverse proxy)
        - Tu vá lỗi bảo mật he dieu hanh dinh ky (patching)
        - Deploy code ung dung len VM, tu khoi dong lai khi VM restart

Buoc 3: Neu tai tang cao -> thue THEM VM moi (van chi mat vai phut), KHONG can mua phan cung moi.
```

So với on-premise (mục 1), điểm khác biệt cốt lõi là **ai sở hữu và bảo trì phần cứng vật lý**: với IaaS, nhà cung cấp cloud lo phần cứng, trung tâm dữ liệu, điện, làm mát, ảo hoá — người dùng chỉ cần "bấm nút" là có máy chủ ảo dùng ngay, và **trả tiền theo thời gian sử dụng** (theo giờ hoặc theo giây) thay vì trả một lần trước cho phần cứng. Nhưng từ hệ điều hành trở lên (cài OS, cài runtime, vá lỗi bảo mật, cấu hình mạng), người dùng IaaS vẫn phải **tự làm mọi việc**, giống hệt như khi họ có một máy chủ vật lý riêng.

**Điều gì xảy ra khi dùng sai:** nếu một đội chọn IaaS nhưng **quên** trách nhiệm "tự quản lý OS" đi kèm với nó — ví dụ không vá lỗi bảo mật hệ điều hành định kỳ, hoặc không tự cấu hình firewall — VM đó có thể bị tấn công qua lỗ hổng hệ điều hành đã biết công khai (CVE) mà nhà cung cấp cloud **không** tự vá thay, vì hợp đồng IaaS chỉ cam kết phần cứng và lớp ảo hoá hoạt động, không cam kết những gì người dùng tự cài lên trên. Đây là lý do IaaS đòi hỏi đội vận hành phải có kỹ năng quản trị hệ thống (sysadmin) tương đương với on-premise — chỉ khác là không cần lo phần cứng vật lý.

---

## 3. PaaS: nền tảng sẵn có, chỉ cần deploy code

**Định nghĩa:** PaaS (Platform as a Service — nền tảng dưới dạng dịch vụ) là mô hình trong đó nhà cung cấp cloud đã cài đặt và quản lý sẵn hệ điều hành, runtime, và các thành phần hạ tầng vận hành (cân bằng tải, tự động khởi động lại khi crash...) — người dùng **chỉ cần deploy code ứng dụng và quản lý dữ liệu**, không đụng tới việc cài OS hay vá lỗi hệ điều hành.

Ví dụ cụ thể: một dịch vụ "App Service" (Azure App Service, hoặc tương tự như AWS Elastic Beanstalk, Google App Engine) chạy một web app ASP.NET Core:

```text title="Vi du: deploy web app ASP.NET Core len mot dich vu PaaS - viec NGUOI DUNG phai tu lam"
Buoc 1: Tao mot "App Service" tren cloud provider, chon runtime la ".NET 10"
        -> nha cung cap TU DONG cai san he dieu hanh + .NET runtime dung phien ban.

Buoc 2: Nguoi dung CHI can:
        - Build code ung dung (dotnet publish)
        - Day (deploy) file build len dich vu qua lenh CLI hoac pipeline CI/CD
        - Cau hinh bien moi truong (connection string, API key...) qua giao dien San cua PaaS

Buoc 3: Nha cung cap TU DONG lo:
        - Cai va vá lỗi bảo mật he dieu hanh ben duoi
        - Tu khoi dong lai ung dung neu crash
        - Cung cap san co che scale (them instance) chi bang mot nut bam hoac 1 dong config

Nguoi dung KHONG BAO GIO thay hoac dung toi may chu ao/he dieu hanh ben duoi - no bi "an" hoan toan.
```

Khác biệt cốt lõi so với IaaS (mục 2): với PaaS, **tầng hệ điều hành và runtime đã bị nhà cung cấp "ẩn" đi hoàn toàn** — người dùng không thấy, không cấu hình, không vá lỗi cho nó. Đổi lại, người dùng mất đi một phần khả năng tuỳ biến sâu (ví dụ không thể tự cài một phần mềm hệ thống đặc biệt mà PaaS không hỗ trợ), nhưng tốc độ đưa ứng dụng lên môi trường chạy thật nhanh hơn nhiều — không cần kỹ năng quản trị hệ điều hành, chỉ cần biết build và deploy code.

**Điều gì xảy ra khi dùng sai:** nếu một đội chọn PaaS nhưng vẫn cố "SSH vào máy chủ" hoặc tự cài phần mềm hệ thống mức OS như cách làm quen thuộc với IaaS/on-premise, họ sẽ **không tìm được** cách làm đó — hầu hết dịch vụ PaaS không cho truy cập trực tiếp vào hệ điều hành bên dưới (đây là thiết kế có chủ đích, không phải thiếu tính năng). Ngược lại, nếu ứng dụng cần một cấu hình hệ điều hành đặc biệt mà PaaS không hỗ trợ (ví dụ một driver phần cứng đặc thù, hoặc một phiên bản thư viện hệ thống cụ thể không có trong môi trường PaaS chuẩn), đội buộc phải chuyển xuống IaaS để có toàn quyền cấu hình — chọn nhầm mô hình theo hướng này gây tốn công sức "di dời" sau này.

---

## 4. SaaS: dùng phần mềm hoàn chỉnh, không quản lý gì về hạ tầng hay code

**Định nghĩa:** SaaS (Software as a Service — phần mềm dưới dạng dịch vụ) là mô hình trong đó người dùng chỉ **sử dụng một phần mềm hoàn chỉnh** qua trình duyệt hoặc ứng dụng client, hoàn toàn không quản lý hạ tầng, không quản lý runtime, và **không viết hay deploy code** — nhà cung cấp chịu trách nhiệm toàn bộ, từ phần cứng tới tính năng phần mềm.

Ví dụ cụ thể: một nhân viên kinh doanh dùng phần mềm quản lý khách hàng (CRM) online qua trình duyệt, hoặc một công ty dùng dịch vụ email doanh nghiệp (ví dụ Microsoft 365, Google Workspace) để gửi/nhận email:

```text title="Vi du: dung mot CRM online (SaaS) - viec NGUOI DUNG can lam"
Buoc 1: Dang ky tai khoan qua trinh duyet, tra phi theo thang/nam theo so nguoi dung.

Buoc 2: Nguoi dung CHI can:
        - Dang nhap qua trinh duyet
        - Nhap du lieu khach hang, dung tinh nang co san (bao cao, gui email...)

Nguoi dung KHONG:
        - Khong biet va khong can biet phan mem nay chay tren may chu nao, o dau
        - Khong viet mot dong code nao
        - Khong deploy, khong cau hinh runtime, khong vá lỗi bảo mật gi ca
        - Neu phan mem loi/sap, nguoi dung CHI co the bao loi cho nha cung cap, khong tu sua duoc
```

Đây là điểm khác biệt lớn nhất so với IaaS và PaaS: cả IaaS và PaaS đều **giả định người dùng có code riêng cần deploy** (một ứng dụng do chính tổ chức xây dựng) — SaaS thì ngược lại, người dùng **không có code nào cả**, chỉ là người tiêu thụ (consumer) của một phần mềm đã hoàn chỉnh, do một công ty khác xây dựng và vận hành toàn bộ.

**Điều gì xảy ra khi dùng sai:** nếu một tổ chức chọn SaaS cho một nhu cầu đòi hỏi tuỳ biến sâu (ví dụ logic nghiệp vụ rất đặc thù mà không phần mềm CRM có sẵn nào đáp ứng được), họ sẽ bị **giới hạn hoàn toàn** trong những tính năng nhà cung cấp SaaS đã xây — không có cách "sửa code" vì không có quyền truy cập code, chỉ có thể chờ nhà cung cấp thêm tính năng (nếu họ đồng ý) hoặc chuyển sang xây dựng riêng (tự viết ứng dụng, deploy qua PaaS/IaaS). Ngược lại, nếu một nhu cầu đơn giản, phổ biến (gửi email, quản lý lịch) mà tổ chức lại tự xây dựng ứng dụng riêng rồi tự deploy qua IaaS/PaaS thay vì dùng SaaS có sẵn, họ tốn thời gian/nhân lực xây dựng lại thứ hàng triệu tổ chức khác đã dùng chung — đây là kiểu lãng phí công sức ngược lại với ví dụ trên.

---

## 5. Bảng so sánh: ai quản lý tầng nào

Sau khi đã hiểu riêng từng khái niệm (mục 1-4), bảng dưới tổng hợp theo đúng một tiêu chí duy nhất: ở mỗi tầng (từ phần cứng tới dữ liệu), **ai** là người phải tự quản lý — người dùng (tổ chức) hay nhà cung cấp dịch vụ.

| Tầng | On-premise | IaaS | PaaS | SaaS |
|---|---|---|---|---|
| Phần cứng vật lý | Người dùng | Nhà cung cấp | Nhà cung cấp | Nhà cung cấp |
| Ảo hoá / mạng nền | Người dùng | Nhà cung cấp | Nhà cung cấp | Nhà cung cấp |
| Hệ điều hành (OS) | Người dùng | **Người dùng** | Nhà cung cấp | Nhà cung cấp |
| Runtime (.NET, v.v.) | Người dùng | **Người dùng** | Nhà cung cấp | Nhà cung cấp |
| Ứng dụng / code | Người dùng | Người dùng | **Người dùng** | Nhà cung cấp |
| Dữ liệu | Người dùng | Người dùng | **Người dùng** | Nhà cung cấp (nhưng tổ chức thường vẫn "sở hữu" dữ liệu về mặt hợp đồng) |
| Ví dụ cụ thể | 2 máy chủ vật lý tự mua (mục 0-1) | Azure VM / AWS EC2 (mục 2) | Azure App Service (mục 3) | CRM online, Microsoft 365 (mục 4) |

Đọc bảng theo đúng logic: đi từ trái sang phải (On-premise → IaaS → PaaS → SaaS), số tầng người dùng **phải tự quản lý** giảm dần — và ngược lại, mức độ kiểm soát/tuỳ biến sâu cũng giảm dần theo đúng chiều đó. Không có lựa chọn nào "tốt nhất tuyệt đối"; lựa chọn đúng phụ thuộc vào việc tổ chức có code riêng cần chạy hay không (nếu không, SaaS là hợp lý), và nếu có code riêng, đội ngũ có đủ kỹ năng/nhân lực quản trị hệ điều hành hay không (nếu có và cần tuỳ biến sâu, chọn IaaS; nếu muốn tập trung vào code, chọn PaaS).

Một điểm dễ nhầm cần làm rõ: PaaS **không** có nghĩa là "IaaS nhưng rẻ hơn" — đây là nhầm lẫn phổ biến. Sự khác biệt là về **tầng trách nhiệm**, không phải về giá. Một ứng dụng đơn giản chạy PaaS có thể rẻ hơn IaaS (vì không cần tự quản lý OS), nhưng một ứng dụng cần tài nguyên rất lớn hoặc cấu hình đặc biệt chạy trên PaaS có thể đắt hơn tự thuê VM (IaaS) và tự tối ưu hệ điều hành cho đúng nhu cầu đó.

---

## 6. Scale up vs scale out: hai cách khác nhau để "thêm sức mạnh"

**Định nghĩa scale up (nâng cấp theo chiều dọc / vertical scaling):** scale up là tăng khả năng chịu tải bằng cách **nâng cấp một máy hiện có lên mạnh hơn** (thêm CPU, thêm RAM cho đúng máy đó) — số lượng máy không đổi, chỉ máy đó "khoẻ" hơn.

**Định nghĩa scale out (mở rộng theo chiều ngang / horizontal scaling):** scale out là tăng khả năng chịu tải bằng cách **thêm nhiều máy chạy song song** (mỗi máy giữ nguyên cấu hình, hoặc tương đương), rồi phân phối tải giữa các máy đó (thường qua một load balancer) — số lượng máy tăng lên, mỗi máy không cần mạnh hơn.

```text title="Vi du doc lap: cung mot muc tieu 'chiu duoc gap 4 lan tai', hai cach khac nhau"
Tinh huong: 1 VM dang chay web app, chiu duoc 1.000 request/giay, can chiu 4.000 request/giay.

Cach 1 - SCALE UP:
  Nang cap 1 VM hien co tu 2 CPU/4GB RAM -> 8 CPU/16GB RAM (mot may MANH HON).
  -> Van la 1 may duy nhat. Neu may nay crash/mat mang, TOAN BO he thong ngung hoat dong.
  -> Co GIOI HAN tren: khong the nang cap vo han (may vat ly/ao co cau hinh toi da nha cung cap ho tro).

Cach 2 - SCALE OUT:
  Giu 4 VM, moi VM van 2 CPU/4GB RAM (khong doi), dat load balancer truoc 4 VM.
  Load balancer chia deu 4.000 request/giay -> moi VM nhan khoang 1.000 request/giay (nhu cu).
  -> Neu 1 trong 4 VM crash, 3 VM con lai VAN CHAY DUOC (giam tai chiu duoc, khong ngung hoan toan).
  -> Khong co gioi han ro ret: can chiu tai gap 10 lan -> them VM thu 10, thu 11...
```

Sự khác biệt quan trọng nhất giữa hai cách này không chỉ là "cách tính toán" mà là **khả năng chịu lỗi (fault tolerance)**: scale up vẫn giữ nguyên **một điểm lỗi duy nhất** (single point of failure) — máy đó mạnh hơn không giúp gì nếu chính máy đó gặp sự cố phần cứng hoặc mất kết nối mạng. Scale out phân tán tải ra nhiều máy độc lập, nên một máy gặp sự cố không làm sập toàn bộ hệ thống — đây cũng là lý do các chương trước (ví dụ caching, mục "IMemoryCache mất đồng bộ giữa nhiều instance") giả định trước một hệ thống đã scale out (nhiều instance chạy song song sau load balancer).

**Điều gì xảy ra khi dùng sai:** nếu một đội chỉ biết scale up (nâng cấp máy hiện có) mà không biết scale out, họ sẽ gặp **giới hạn cứng** khi tải vượt quá cấu hình máy mạnh nhất nhà cung cấp hỗ trợ — không có "máy mạnh hơn nữa" để mua, dù sẵn sàng trả thêm tiền. Ngược lại, nếu một ứng dụng được thiết kế để scale out (nhiều instance) nhưng code lại lưu trạng thái (state) trực tiếp trong RAM của từng máy theo kiểu chỉ hợp với 1 máy duy nhất (ví dụ giữ session người dùng trong biến static của tiến trình, không dùng cơ chế chia sẻ giữa các instance), việc thêm instance mới sẽ gây lỗi logic — người dùng bị "đăng xuất" ngẫu nhiên mỗi khi request của họ rơi vào một instance khác không giữ session đó. Đây là lý do khi thiết kế hệ thống dự tính scale out, ứng dụng cần được viết theo kiểu **stateless** (không giữ trạng thái riêng trong từng tiến trình) — khái niệm này liên hệ trực tiếp tới container orchestration (chương kế tiếp), nơi số lượng instance của ứng dụng có thể tự động tăng/giảm theo tải.

IaaS và PaaS (mục 2, 3) đều hỗ trợ cả hai cách scale, nhưng PaaS thường cung cấp cơ chế scale out **có sẵn, cấu hình bằng vài dòng** (ví dụ đặt "số instance tối thiểu/tối đa" trong một dịch vụ App Service), trong khi trên IaaS, đội vận hành phải **tự dựng** load balancer và tự quản lý việc thêm/gỡ VM — một lý do nữa để cân nhắc PaaS khi ưu tiên tốc độ triển khai hơn mức tuỳ biến sâu.

---

## Cạm bẫy & thực chiến

- **Nhầm PaaS là "IaaS rẻ hơn":** đây là nhầm lẫn về bản chất — sự khác biệt là **tầng trách nhiệm** (ai quản lý OS/runtime), không phải giá. Một ứng dụng cần tuỳ biến sâu ở tầng hệ điều hành chạy trên PaaS có thể đắt hơn và bị giới hạn hơn IaaS, không phải luôn rẻ hơn (mục 5).
- **Chọn IaaS nhưng quên trách nhiệm vá lỗi hệ điều hành đi kèm:** nhà cung cấp IaaS chỉ cam kết phần cứng và lớp ảo hoá — không tự vá lỗi bảo mật hệ điều hành người dùng tự cài lên trên (mục 2). Bỏ qua điều này là lỗ hổng bảo mật thực tế, không phải rủi ro lý thuyết.
- **Cố truy cập hệ điều hành bên dưới trên một dịch vụ PaaS** (SSH, cài phần mềm hệ thống): hầu hết PaaS chủ động không cho phép — đây là thiết kế có chủ đích để "ẩn" tầng OS, không phải thiếu tính năng cần báo lỗi (mục 3).
- **Tưởng nâng cấp một máy (scale up) là giải pháp vô hạn:** luôn có giới hạn cấu hình tối đa nhà cung cấp hỗ trợ cho một máy — khi vượt giới hạn đó, chỉ scale out (thêm máy) mới giải quyết được (mục 6).
- **Thiết kế ứng dụng giữ trạng thái trong RAM của một tiến trình rồi mong scale out suôn sẻ:** nếu ứng dụng không stateless, thêm instance mới gây lỗi logic (mất session, dữ liệu không đồng bộ) thay vì chỉ đơn giản là "chạy nhanh hơn" (mục 6).
- **Áp dụng SaaS cho một nhu cầu cần tuỳ biến sâu mà phần mềm có sẵn không hỗ trợ:** tổ chức bị giới hạn hoàn toàn trong tính năng nhà cung cấp đã xây, không có cách "sửa code" vì không có quyền truy cập code (mục 4).
- **Đánh giá sai tải cao điểm khi vận hành on-premise:** vì thời gian mua/lắp phần cứng vật lý mất nhiều tuần, không có cách "tăng công suất trong vài giờ" như trên cloud — đây là rủi ro vận hành cụ thể, không phải lý thuyết trừu tượng (mục 1, mục 0).

---

## Bài tập

**Bài 1 (phân loại).** Một công ty thuê một máy chủ ảo trên AWS (EC2 instance), sau đó tự cài Ubuntu Linux, tự cài .NET runtime, tự cấu hình Nginx, rồi deploy ứng dụng ASP.NET Core của mình lên đó. Công ty này đang dùng mô hình nào: on-premise, IaaS, PaaS, hay SaaS? Giải thích dựa trên tầng nào công ty phải tự quản lý.

??? success "Lời giải + vì sao"
    **IaaS.** Công ty thuê máy chủ ảo qua Internet (không tự mua phần cứng vật lý — khác on-premise), nhưng vẫn phải **tự cài và quản lý** hệ điều hành (Ubuntu), runtime (.NET), và web server (Nginx) — đúng đặc điểm cốt lõi của IaaS ở mục 2: nhà cung cấp chỉ lo phần cứng và ảo hoá, còn từ OS trở lên là trách nhiệm của người dùng. Nếu công ty dùng một dịch vụ như Azure App Service (chỉ cần chọn runtime ".NET 10" rồi deploy code, không tự cài OS) thì đó mới là PaaS.

**Bài 2 (thiết kế, đối chiếu mục 6).** Một ứng dụng web đang chạy trên 1 VM (2 CPU/4GB RAM), chịu được 800 request/giây. Đội vận hành dự đoán tải sẽ tăng dần và ổn định ở khoảng 1.500 request/giây trong 6 tháng tới, KHÔNG có đợt tăng vọt bất thường nào. Đề xuất scale up hay scale out cho tình huống này, và nêu một tình huống khác (đổi giả định) mà lựa chọn sẽ đảo ngược.

??? success "Lời giải + vì sao"
    Với tải tăng **dần và ổn định**, không có đợt tăng vọt bất thường, **scale up** (nâng cấp VM lên cấu hình mạnh hơn, ví dụ 4 CPU/8GB RAM) là lựa chọn đơn giản hơn — không cần dựng thêm load balancer, không cần lo vấn đề stateless (mục 6), và đủ đáp ứng 1.500 request/giây nếu VM mạnh hơn đủ công suất.

    **Tình huống đảo ngược:** nếu tải có khả năng **tăng vọt đột ngột và không đoán trước được** (ví dụ một chiến dịch marketing viral, hoặc mô hình kinh doanh có Black Friday như mục 0), scale out là lựa chọn đúng hơn — vì scale out cho phép thêm/gỡ instance nhanh theo đúng tải thực tế tại từng thời điểm, còn scale up đòi hỏi lên kế hoạch nâng cấp trước (và có giới hạn cấu hình tối đa), không phản ứng kịp với tải tăng vọt trong vài giờ.

---

## Tự kiểm tra

1. On-premise khác IaaS ở điểm nào — cụ thể là ai sở hữu và bảo trì phần cứng vật lý?

    ??? note "Đáp án"
        On-premise: tổ chức tự mua và bảo trì phần cứng vật lý (mục 1). IaaS: nhà cung cấp cloud sở hữu và bảo trì phần cứng vật lý, tổ chức chỉ thuê máy chủ ảo qua Internet, trả tiền theo thời gian dùng (mục 2).

2. Vì sao nói PaaS "ẩn" tầng hệ điều hành, còn IaaS thì không?

    ??? note "Đáp án"
        Với IaaS, người dùng nhận một máy chủ ảo trống, phải tự cài hệ điều hành và tự vá lỗi bảo mật cho nó (mục 2). Với PaaS, nhà cung cấp đã cài sẵn và tự quản lý hệ điều hành/runtime — người dùng không thấy, không cấu hình, không vá lỗi cho tầng đó, chỉ deploy code (mục 3).

3. Một tổ chức dùng phần mềm CRM online qua trình duyệt, không viết một dòng code nào. Đây là mô hình nào, và tổ chức đó phải tự quản lý tầng nào?

    ??? note "Đáp án"
        SaaS. Tổ chức không tự quản lý tầng nào về hạ tầng hay code — chỉ sử dụng phần mềm hoàn chỉnh do nhà cung cấp xây dựng và vận hành toàn bộ (mục 4).

4. Scale up và scale out khác nhau ở điểm cơ bản nào?

    ??? note "Đáp án"
        Scale up là nâng cấp MỘT máy hiện có lên mạnh hơn (thêm CPU/RAM cho đúng máy đó, số lượng máy không đổi). Scale out là thêm NHIỀU máy chạy song song, phân phối tải giữa chúng qua load balancer, mỗi máy giữ cấu hình như cũ (mục 6).

5. Vì sao scale up vẫn giữ nguyên "một điểm lỗi duy nhất" (single point of failure), còn scale out thì không?

    ??? note "Đáp án"
        Scale up chỉ nâng cấp cấu hình của một máy — hệ thống vẫn phụ thuộc vào đúng một máy đó; nếu máy này gặp sự cố phần cứng hoặc mất kết nối mạng, toàn bộ hệ thống ngừng hoạt động. Scale out phân tán tải ra nhiều máy độc lập; nếu một máy gặp sự cố, các máy còn lại vẫn tiếp tục phục vụ (mục 6).

6. Vì sao một công ty đang vận hành on-premise khó phản ứng kịp với một đợt tải tăng vọt bất ngờ (ví dụ Black Friday), trong khi công ty dùng IaaS có thể phản ứng trong vài phút?

    ??? note "Đáp án"
        On-premise đòi hỏi mua phần cứng vật lý mới khi cần thêm công suất — quy trình đặt hàng, vận chuyển, lắp đặt, cấu hình mất nhiều tuần, không thể rút ngắn bằng tiền (mục 0, mục 1). IaaS chỉ yêu cầu thuê thêm máy chủ ảo qua giao diện/API của nhà cung cấp cloud — không có bước vận chuyển/lắp đặt vật lý nào, nên có thể có thêm tài nguyên trong vài phút (mục 2).

7. Một đội ngũ nhỏ, không có kỹ năng quản trị hệ điều hành chuyên sâu, cần deploy nhanh một ứng dụng ASP.NET Core và tập trung thời gian vào viết tính năng. Giữa IaaS và PaaS, lựa chọn nào phù hợp hơn, và vì sao?

    ??? note "Đáp án"
        PaaS phù hợp hơn — vì PaaS đã cài sẵn và tự quản lý hệ điều hành/runtime, đội chỉ cần build và deploy code (mục 3), không cần kỹ năng quản trị hệ điều hành như IaaS yêu cầu (mục 2). Đánh đổi là mất một phần khả năng tuỳ biến sâu ở tầng hệ điều hành, nhưng phù hợp với ưu tiên "tốc độ, tập trung vào code" của đội này.

---

??? abstract "Deep dive: đa cloud, ranh giới mờ giữa các mô hình, và chi phí thật của cloud"
    Ranh giới giữa IaaS/PaaS/SaaS trong thực tế **không luôn rõ ràng như bảng mục 5**. Nhiều dịch vụ cloud hiện đại nằm ở giữa — ví dụ dịch vụ container (chạy ứng dụng đóng gói trong container, chương kế tiếp sẽ giới thiệu Kubernetes) thường được gọi là "CaaS" (Container as a Service), nằm giữa IaaS và PaaS: người dùng không tự quản lý hệ điều hành của máy chủ nền (giống PaaS), nhưng vẫn tự quản lý môi trường runtime bên trong container image của mình (gần giống IaaS hơn PaaS thuần). Việc phân loại chính xác 100% không quan trọng bằng việc hiểu đúng **câu hỏi cốt lõi** của mọi mô hình: tầng nào tôi phải tự quản lý, tầng nào nhà cung cấp lo cho tôi.

    Một hiểu lầm phổ biến khác: "chuyển lên cloud luôn rẻ hơn on-premise". Điều này chỉ đúng trong một số tình huống (đặc biệt khi tải biến động mạnh, đúng như ví dụ mục 0) — với tải **ổn định, dự đoán được, và đủ lớn**, chi phí thuê cloud dài hạn (đặc biệt IaaS/PaaS tính theo giờ) có thể cao hơn chi phí tự mua phần cứng khấu hao trong nhiều năm. Đây là lý do các tổ chức lớn thường áp dụng chiến lược "hybrid cloud" (kết hợp on-premise cho tải ổn định + cloud cho tải biến động) hoặc "đa cloud" (dùng nhiều nhà cung cấp cloud khác nhau để tránh phụ thuộc vào một nhà cung cấp duy nhất — gọi là tránh "vendor lock-in"). Những chiến lược này đòi hỏi kiến thức sâu hơn về kiến trúc hệ thống và quản lý chi phí cloud (thường gọi là FinOps) — vượt quá phạm vi giới thiệu khái niệm của chương này, nhưng là hướng học tiếp hợp lý nếu công việc thực tế đòi hỏi ra quyết định về hạ tầng ở quy mô tổ chức.

    Cuối cùng, khái niệm "serverless" (thường bị nhầm là "không có server") đáng nhắc tới ngắn gọn: đây thực chất là một dạng PaaS đẩy xa hơn — người dùng chỉ viết một hàm (function) xử lý một sự kiện cụ thể (ví dụ một request HTTP, hoặc một file mới được tải lên), nhà cung cấp tự động cấp phát tài nguyên chạy hàm đó **chỉ trong lúc nó thực thi**, rồi giải phóng ngay sau đó — người dùng trả tiền theo số lần gọi/thời gian chạy thực tế, không trả tiền cho thời gian máy chủ "rỗi" (idle). Vẫn có server thật chạy bên dưới — chỉ là người dùng không thấy và không quản lý gì về nó, kể cả việc nó có đang "tồn tại" giữa hai lần gọi hay không. Serverless là một hướng đào sâu riêng, không phải nội dung bắt buộc của chương giới thiệu này.

**Tiếp theo →** [P9 · Container Orchestration: Kubernetes cơ bản](container-orchestration.md)
