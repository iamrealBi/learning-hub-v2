---
tier: core
status: core
owner: core-team
verified_on: "2026-07-05"
dotnet_version: "10.0"
bloom: phân biệt
requires: [p9-k8s]
est_minutes_fast: 24
---

# Infrastructure as Code: Terraform & Bicep

!!! info "bạn đang ở đây"
    cần trước: bạn đã biết các mô hình IaaS/PaaS/SaaS (chương Cloud Fundamentals) và khái niệm Pod/Deployment/Service của Kubernetes (chương Container Orchestration) — chương này học cách **định nghĩa việc tạo ra hạ tầng** (máy chủ, mạng, database, cả cluster Kubernetes) bằng file code thay vì bấm chuột trên giao diện web của nhà cung cấp cloud.
    mở khoá: sau chương này bạn phân biệt được declarative với imperative, đọc hiểu một file `.tf` (Terraform) hoặc `.bicep` (Bicep) ở mức cơ bản, và biết chính xác `terraform plan` khác `terraform apply` ở đâu — đủ để không hoảng khi thấy các file này trong một dự án thật, dù chưa cần thành thạo viết chúng.

> **Mục tiêu (đo được):** sau chương này bạn **định nghĩa** được Infrastructure as Code và khái niệm declarative, **phân biệt** được declarative với imperative, Terraform với Bicep, và `terraform plan` với `terraform apply`, **đọc** được một file `.tf`/`.bicep` tối thiểu và biết nó sẽ tạo ra resource nào.

---

## 0. Đoán nhanh trước khi học

Một kỹ sư trong nhóm bạn đăng nhập vào giao diện web của nhà cung cấp cloud (AWS, Azure...), bấm chuột thêm một firewall rule mới để mở tạm một cổng cho việc debug, rồi quên xoá. Ba tháng sau, một kỹ sư khác nhìn thấy rule này đang mở trong hệ thống production.

??? question "Đoán trước, đáp án ở dưới"
    Gợi ý: rule này không nằm trong bất kỳ file code nào, không có commit, không có pull request, không có tên người tạo gắn kèm log thay đổi lâu dài. Kỹ sư thứ hai có cách nào để biết ai tạo rule này, khi nào, và vì lý do gì — mà không phải hỏi từng người trong nhóm?

??? note "Đáp án"
    KHÔNG có cách nào tra được tự động. Giao diện web (console) của nhà cung cấp cloud thường chỉ lưu log "ai bấm gì lúc nào" trong một khoảng thời gian giới hạn (ví dụ 90 ngày), và log đó chỉ nói "user X tạo rule Y lúc Z" — không nói **lý do**, không có ngữ cảnh, không liên kết với một task/ticket nào. Sau 3 tháng, kỹ sư thứ hai chỉ còn cách hỏi trực tiếp từng người, hoặc — nếu không ai nhớ hoặc người đó đã nghỉ việc — phải đoán rule đó có an toàn để xoá không, một quyết định rủi ro trên hệ thống production. Đây chính là vấn đề gốc mà mục 1 giải quyết: nếu hạ tầng được định nghĩa trong file code, lý do rule đó tồn tại nằm ngay trong commit message hoặc pull request tạo ra nó — tra được **mãi mãi**, không phụ thuộc trí nhớ con người.

---

## 1. Vấn đề gốc: tạo hạ tầng bằng tay trên console không review được, không tái tạo được

**Định nghĩa "console" (giao diện quản trị cloud):** là trang web do nhà cung cấp cloud (AWS, Azure, Google Cloud...) cung cấp, cho phép người dùng tạo/sửa/xoá resource (máy chủ, database, mạng...) bằng cách bấm chuột qua các form và nút trên trình duyệt.

Cách làm việc phổ biến nhất khi mới bắt đầu với cloud là mở console, bấm "Create Virtual Machine", điền vài form, bấm "Create". Nhanh, trực quan, không cần học cú pháp gì. Nhưng cách này có ba vấn đề tích lũy dần theo thời gian và theo quy mô nhóm:

- **Không thể review.** Code ứng dụng phải qua pull request trước khi merge (đã học ở chương CI/CD) — một người khác đọc, góp ý, rồi mới cho vào production. Bấm chuột trên console thì không ai review được **trước khi** thay đổi có hiệu lực — rule sai, resource thừa, hoặc lỗ hổng bảo mật đã tồn tại thật trên production trước khi bất kỳ ai khác biết.
- **Không biết ai đổi gì lúc nào, vì sao.** Như ví dụ mục 0: log console (nếu có) chỉ ghi hành động, không ghi lý do, và thường bị xoá sau một khoảng thời gian giới hạn.
- **Không tái tạo lại chính xác được.** Giả sử hệ thống production có 40 resource được tạo qua console trong 2 năm bởi nhiều người khác nhau. Khi cần dựng một môi trường staging **giống hệt** để test, không có cách nào chắc chắn tái tạo đúng 40 resource đó với đúng cấu hình — phải bấm lại bằng tay, dễ thiếu sót hoặc lệch cấu hình so với bản gốc.

**Điều gì xảy ra khi dùng sai (chỉ dùng console cho hạ tầng lâu dài):** hạ tầng dần trở thành một hộp đen mà không ai trong nhóm nắm được toàn bộ trạng thái thật — hiện tượng này gọi là **configuration drift** (cấu hình trôi dạt): trạng thái thật trên cloud dần lệch khỏi bất kỳ tài liệu nào mô tả nó, vì tài liệu (nếu có) không tự động cập nhật theo mỗi lần bấm chuột.

**Infrastructure as Code (IaC) — định nghĩa:** là cách quản lý hạ tầng bằng cách **định nghĩa hạ tầng trong file code**, lưu file đó vào Git, và review thay đổi qua pull request — giống hoàn toàn quy trình bạn đã dùng cho code ứng dụng (đã học ở P0 và chương CI/CD). Thay vì bấm "Create Virtual Machine" trên console, bạn viết một file mô tả "tôi cần một virtual machine với cấu hình X", commit file đó, tạo pull request, một đồng nghiệp review, rồi một công cụ (Terraform, Bicep...) đọc file đó và tự tạo resource thật trên cloud.

Với IaC, câu hỏi ở mục 0 ("ai tạo rule này, vì sao") có câu trả lời tức thì: mở lịch sử Git của file định nghĩa firewall, tìm đúng dòng thêm rule đó, xem commit message và pull request liên kết — lý do nằm ngay trong đó, tồn tại vĩnh viễn trong lịch sử Git, không phụ thuộc log tạm thời của console hay trí nhớ con người.

---

## 2. Declarative vs imperative: khai báo TRẠNG THÁI MONG MUỐN, không khai báo TỪNG BƯỚC

Đây là khái niệm dễ nhầm nhất khi mới học IaC, vì cả hai cách đều là "viết code để tạo hạ tầng" — sự khác biệt nằm ở **những gì bạn viết ra**, không nằm ở việc có dùng code hay không.

**Định nghĩa "imperative" (mệnh lệnh, khai báo từng bước):** bạn viết ra **chính xác từng bước thao tác** theo thứ tự — ví dụ một script bash gọi `aws ec2 run-instances`, rồi `aws ec2 create-security-group`, rồi `aws ec2 authorize-security-group-ingress`, theo đúng trình tự đó. Công cụ chỉ thực thi đúng những lệnh bạn viết, không tự suy luận gì thêm.

**Định nghĩa "declarative" (khai báo, khai báo trạng thái mong muốn):** bạn chỉ viết ra **trạng thái cuối cùng bạn muốn có** — ví dụ "tôi cần 1 virtual machine tên `web-01`, loại `Standard_B2s`, 1 firewall rule mở cổng 443". Bạn KHÔNG viết các bước thao tác để đạt được trạng thái đó. Công cụ (Terraform, Bicep) tự so sánh trạng thái mong muốn này với trạng thái hiện tại trên cloud, rồi **tự tính toán** cần tạo/sửa/xoá resource nào để đạt được trạng thái đó.

Ví dụ tối thiểu minh hoạ đúng sự khác biệt này — cùng một mục tiêu ("có 1 thư mục tên `data`"), viết theo hai cách:

```bash title="imperative.sh — tung buoc thao tac, phai tu kiem tra dieu kien"
#!/usr/bin/env bash
# Cach imperative: phai tu viet TUNG BUOC, tu kiem tra da ton tai chua.
if [ ! -d "data" ]; then
  mkdir data
fi
echo "Da co thu muc data"
```

```text title="declarative.txt — chi khai bao TRANG THAI MONG MUON (gia lap, khong phai ngon ngu thuc thi)"
# Cach declarative: chi noi TRANG THAI MUON CO, khong noi CACH LAM.
resource "local_directory" "data" {
  path = "data"
}
# Cong cu tu kiem tra: da co thu muc "data" chua? Neu chua -> tu tao.
# Neu da co va dung cau hinh -> khong lam gi (khong bao loi, khong tao lai).
```

Sự khác biệt cốt lõi: bản imperative phải **tự viết logic kiểm tra** ("nếu chưa có thì mới tạo") — nếu quên dòng `if`, chạy lại script lần hai sẽ báo lỗi "đã tồn tại". Bản declarative không cần logic kiểm tra này — công cụ tự so sánh trạng thái mong muốn với trạng thái thật và tự quyết định hành động, chạy lại nhiều lần với cùng file đều an toàn (tính chất này gọi là **idempotent** — đã học khái niệm idempotent ở chương resilience patterns cho retry HTTP, ở đây áp dụng cùng nguyên lý cho hạ tầng).

**Điều gì xảy ra khi nhầm lẫn hai khái niệm này:** một người quen viết script imperative (ví dụ Ansible playbook kiểu cũ, hoặc bash script gọi CLI cloud) khi chuyển sang Terraform thường cố "chỉ đạo từng bước" trong file `.tf` — ví dụ cố viết điều kiện if/else phức tạp để "kiểm soát thứ tự tạo". Terraform không hoạt động theo tư duy đó: nó tự xây dựng **dependency graph** (đồ thị phụ thuộc) giữa các resource dựa trên việc resource này có tham chiếu resource khác không, rồi tự quyết định thứ tự tạo — cố áp tư duy imperative vào sẽ gây khó hiểu khi đọc lỗi hoặc khi Terraform tạo resource theo thứ tự "không như mong đợi" (nhưng thực ra đúng theo dependency thật).

---

## 3. Terraform: công cụ IaC đa cloud, viết bằng HCL

**Định nghĩa:** Terraform là một công cụ IaC declarative, mã nguồn mở, cho phép định nghĩa hạ tầng trên **nhiều nhà cung cấp cloud khác nhau** (AWS, Azure, Google Cloud, và hàng trăm provider khác kể cả dịch vụ không phải cloud như GitHub, Cloudflare) bằng **cùng một ngôn ngữ** gọi là HCL (HashiCorp Configuration Language).

Điểm khác biệt lớn nhất của Terraform so với việc dùng CLI/SDK riêng của từng cloud: nếu tổ chức của bạn dùng cả AWS và Azure, bạn học **một** cú pháp HCL, dùng cho cả hai, thay vì học riêng cách viết cho từng nhà cung cấp.

Ví dụ tối thiểu — một file `.tf` định nghĩa **một** resource duy nhất (một storage bucket trên một cloud giả định, chỉ để minh hoạ cấu trúc, không chạy thật):

```hcl title="main.tf — vi du toi thieu, 1 file dinh nghia 1 resource"
# Khai bao provider (nha cung cap cloud) se dung.
provider "aws" {
  region = "ap-southeast-1"
}

# Khai bao MOT resource: loai "aws_s3_bucket", ten noi bo "hoc_lieu".
resource "aws_s3_bucket" "hoc_lieu" {
  bucket = "learning-hub-tai-lieu-2026"

  tags = {
    Environment = "production"
    ManagedBy   = "terraform"
  }
}
```

Đọc file này: từ khoá `resource` khai báo một resource, `"aws_s3_bucket"` là **loại** resource (bucket lưu trữ file trên AWS), `"hoc_lieu"` là tên nội bộ để Terraform và các resource khác trong cùng project tham chiếu tới nó, và phần trong `{ }` là cấu hình mong muốn (đây chính là declarative — bạn khai báo "tôi muốn một bucket tên `learning-hub-tai-lieu-2026`", không khai báo lệnh API nào để tạo nó).

**Điều gì xảy ra khi thiếu khối `provider`:** Terraform không biết đang làm việc với nhà cung cấp cloud nào, không biết cách xác thực (credentials) hay gọi API nào để đọc/tạo resource — lệnh `terraform init` (bước khởi tạo, tải provider) sẽ báo lỗi ngay, không thể tiến tới bước `plan` hay `apply`.

---

## 4. Bicep: công cụ IaC chuyên riêng cho Azure, cú pháp gọn hơn ARM template gốc

**Định nghĩa:** Bicep là một công cụ IaC declarative do Microsoft phát triển, **chỉ dùng cho Azure** (không đa cloud như Terraform), với cú pháp gọn và dễ đọc hơn ARM template (Azure Resource Manager template — định dạng JSON gốc, dài dòng, từng là cách duy nhất định nghĩa hạ tầng Azure bằng code trước khi Bicep ra đời).

Ví dụ tối thiểu — cùng ý tưởng "tạo một storage account", viết bằng Bicep:

```text title="main.bicep — vi du toi thieu, 1 file dinh nghia 1 resource Azure"
// Khai bao MOT resource: loai storage account, ten noi bo "hocLieu".
resource hocLieu 'Microsoft.Storage/storageAccounts@2023-01-01' = {
  name: 'learninghubtailieu2026'
  location: 'southeastasia'
  sku: {
    name: 'Standard_LRS'
  }
  kind: 'StorageV2'
}
```

So với Terraform: cú pháp Bicep gọn hơn ARM JSON gốc rất nhiều (ARM JSON tương đương cần khoảng gấp 3-4 lần số dòng với nhiều dấu ngoặc lồng nhau), nhưng Bicep **chỉ hiểu Azure** — nếu tổ chức dùng nhiều cloud, Bicep không giúp được cho phần AWS hay Google Cloud.

**Điều gì xảy ra khi chọn sai công cụ cho tình huống:** một tổ chức chỉ dùng Azure mà chọn Terraform không sai (Terraform vẫn hỗ trợ Azure qua provider `azurerm`), nhưng phải tự quản lý thêm state file (mục 5) và học HCL — trong khi Bicep tích hợp sẵn với Azure CLI, không cần quản lý state file riêng (Azure tự lưu trạng thái). Ngược lại, một tổ chức dùng cả AWS và Azure mà chọn Bicep sẽ phải dùng thêm một công cụ khác hoàn toàn cho phần AWS — mất đi lợi ích "một cú pháp cho mọi cloud" mà Terraform mang lại.

---

## 5. `terraform plan` vs `terraform apply`: XEM TRƯỚC khác THỰC SỰ THỰC HIỆN

Đây là khái niệm quan trọng nhất về mặt an toàn vận hành trong chương này.

**Định nghĩa `terraform plan`:** đọc file `.tf`, so sánh với trạng thái hiện tại (lưu trong **state file** — file Terraform dùng để nhớ resource nào nó đang quản lý và cấu hình hiện tại của từng resource), rồi **chỉ in ra** danh sách thay đổi sẽ xảy ra (resource nào sẽ được tạo mới, sửa, hoặc xoá) — **không** thực hiện bất kỳ thay đổi thật nào trên cloud.

**Định nghĩa `terraform apply`:** thực hiện đúng những thay đổi mà `plan` đã tính toán — **thật sự** gọi API cloud để tạo/sửa/xoá resource. Chạy `apply` mà chưa từng chạy `plan` để xem trước vẫn hoạt động (Terraform tự chạy một `plan` ngầm rồi hỏi xác nhận trước khi tiến hành), nhưng workflow chuẩn tách riêng hai bước để có cơ hội **đọc kỹ** danh sách thay đổi trước khi bất kỳ điều gì xảy ra thật.

Ví dụ cụ thể vì sao tách hai bước này quan trọng: giả sử ai đó sửa file `.tf`, đổi tên nội bộ của một resource đang chạy production (ví dụ đổi `resource "aws_s3_bucket" "hoc_lieu"` thành `resource "aws_s3_bucket" "tai_lieu"` — chỉ đổi tên nội bộ, không đổi gì về ý định). Với Terraform, đổi tên nội bộ này KHÔNG được hiểu là "đổi tên resource cũ" — nó được hiểu là "xoá resource cũ (`hoc_lieu`) và tạo một resource mới hoàn toàn (`tai_lieu`)", vì Terraform theo dõi resource qua tên nội bộ trong state file. Nếu chạy `terraform apply` ngay mà không đọc output của `plan`, bucket production cũ (cùng toàn bộ file lưu trong đó) sẽ bị **xoá thật**, và một bucket rỗng mới được tạo ra — dữ liệu mất hoàn toàn. Nếu chạy `terraform plan` trước và đọc kỹ, output sẽ hiện rõ dòng `# aws_s3_bucket.hoc_lieu will be destroyed` — dấu hiệu cảnh báo rõ ràng để dừng lại và sửa file `.tf` bằng lệnh đổi tên đúng cách (`terraform state mv`) trước khi có bất kỳ thay đổi thật nào xảy ra.

**Điều gì xảy ra khi bỏ qua `plan`, chạy `apply` trực tiếp trên production mà không xem trước:** không có bước nào để phát hiện các thay đổi ngoài ý muốn (như ví dụ xoá nhầm bucket ở trên) trước khi chúng xảy ra thật — hậu quả từ resource bị xoá nhầm là **không thể hoàn tác** trong nhiều trường hợp (dữ liệu trong storage bị xoá, database bị drop). Đây là lý do quy trình chuẩn trong CI/CD cho hạ tầng luôn có bước `plan` chạy tự động và hiển thị output trong pull request để người review đọc, và bước `apply` chỉ chạy sau khi có người xác nhận (tương tự cơ chế gate CI đã học ở chương CI/CD — CI không xanh thì không merge, ở đây `plan` không được review kỹ thì không nên `apply`).

---

## Cạm bẫy & thực chiến

- **Bấm chuột sửa resource trực tiếp trên console sau khi đã dùng Terraform quản lý resource đó:** gây configuration drift — lần `plan` kế tiếp sẽ phát hiện sự khác biệt giữa state file và thực tế, có thể đề xuất "sửa lại" (ghi đè) đúng thay đổi bạn vừa bấm tay, gây nhầm lẫn nghiêm trọng về việc thay đổi nào là "thật" (mục 1, mục 5).
- **Đổi tên nội bộ (`resource "..." "ten_cu"` thành `"ten_moi"`) và tưởng đó chỉ là đổi tên hiển thị:** Terraform hiểu đây là xoá resource cũ + tạo resource mới — nếu là database hoặc storage đang chứa dữ liệu, dữ liệu **mất thật** khi `apply` (mục 5). Dùng `terraform state mv` để đổi tên an toàn mà không xoá resource thật.
- **Chạy `terraform apply` trên production mà không đọc output của `plan` trước:** bỏ lỡ cơ hội duy nhất để phát hiện thay đổi ngoài ý muốn trước khi nó xảy ra thật và có thể không thể hoàn tác (mục 5).
- **Nhầm declarative với "không cần hiểu gì cả":** dù công cụ tự tính toán cách đạt trạng thái mong muốn, người viết file `.tf`/`.bicep` vẫn phải hiểu resource đó phụ thuộc resource nào khác (ví dụ một virtual machine cần một mạng đã tồn tại) — Terraform tự suy ra thứ tự tạo qua tham chiếu giữa resource, nhưng không tự "biết" bạn muốn kiến trúc nào (mục 2).
- **Không lưu trữ state file an toàn và có kiểm soát truy cập (ví dụ để state file trên máy cá nhân, không backup):** state file chứa toàn bộ thông tin resource đang được quản lý (đôi khi cả dữ liệu nhạy cảm). Mất state file khiến Terraform "quên" nó đang quản lý resource nào, dù resource thật vẫn tồn tại trên cloud — gây khó khăn lớn để tiếp tục quản lý bằng Terraform.
- **Trộn lẫn resource do console tạo tay và resource do Terraform quản lý trong cùng một môi trường mà không rõ ràng resource nào thuộc nhóm nào:** khi cần dọn dẹp hoặc tái tạo môi trường, không biết resource nào an toàn để xoá tự động (do Terraform quản lý, tái tạo được) và resource nào không (tạo tay, có thể chứa dữ liệu không thể tái tạo) (mục 1).
- **Chọn Bicep cho một tổ chức đang dùng nhiều cloud, hoặc chọn Terraform cho một tổ chức chỉ dùng Azure mà không cân nhắc việc phải tự quản lý state file:** cả hai không phải lỗi kỹ thuật, nhưng gây thêm việc không cần thiết nếu không khớp với tình huống thật của tổ chức (mục 4).

---

## Bài tập

**Bài 1 (nhận diện).** Đọc hai đoạn sau, xác định đoạn nào là declarative, đoạn nào là imperative, và giải thích dựa trên đặc điểm nào.

```bash title="doan-a.sh"
# test:skip vi du minh hoa imperative, khong phai C#
aws ec2 create-security-group --group-name web-sg
aws ec2 authorize-security-group-ingress --group-name web-sg --port 443
aws ec2 run-instances --security-group-ids web-sg --image-id ami-xxxx
```

```hcl title="doan-b.tf"
resource "aws_security_group" "web_sg" {
  name = "web-sg"
  ingress {
    from_port = 443
    to_port   = 443
    protocol  = "tcp"
  }
}

resource "aws_instance" "web" {
  ami             = "ami-xxxx"
  security_groups = [aws_security_group.web_sg.name]
}
```

??? success "Lời giải + vì sao"
    Đoạn A là **imperative**: nó liệt kê chính xác từng lệnh CLI theo thứ tự thực thi (`create-security-group` trước, `authorize-security-group-ingress` sau, `run-instances` cuối) — người viết phải tự biết và tự viết đúng trình tự này.

    Đoạn B là **declarative**: nó chỉ khai báo hai resource mong muốn (`aws_security_group` và `aws_instance`) và mối quan hệ giữa chúng (instance tham chiếu tới security group qua `aws_security_group.web_sg.name`). Không có lệnh thao tác nào được viết ra — Terraform tự đọc tham chiếu này, tự suy ra phải tạo `web_sg` trước `web` (vì `web` cần `web_sg` đã tồn tại), và tự gọi API theo đúng thứ tự đó.

**Bài 2 (dự đoán hậu quả).** Một đồng nghiệp báo bạn: "Tôi vừa sửa file `main.tf`, đổi giá trị `instance_type` từ `"t3.micro"` sang `"t3.large"` cho một virtual machine đang chạy production, và tôi sắp chạy `terraform apply` luôn vì tôi tự tin thay đổi này chỉ là nâng cấp kích thước, không có gì rủi ro." Bạn sẽ khuyên gì trước khi đồng nghiệp chạy `apply`?

??? success "Lời giải + vì sao"
    Khuyên chạy `terraform plan` trước và đọc kỹ output, dù thay đổi có vẻ đơn giản. Lý do: một số thay đổi thuộc tính (tuỳ loại resource và tuỳ nhà cung cấp cloud) không thể áp dụng "tại chỗ" (in-place) — đổi `instance_type` trên một số cloud yêu cầu **xoá và tạo lại** (destroy + recreate) toàn bộ instance, không chỉ đơn giản là "nâng cấp". Nếu đúng là trường hợp này, output của `plan` sẽ hiện rõ dòng resource đó sẽ bị `destroyed` rồi `created` (không phải `updated in-place`) — dấu hiệu cho biết virtual machine đó (và bất kỳ dữ liệu chỉ lưu trên local disk của nó, không lưu ở storage riêng) sẽ mất khi `apply`. Chạy `plan` trước là cách duy nhất để phát hiện điều này trước khi nó xảy ra thật trên production, đúng nguyên lý đã học ở mục 5.

---

## Tự kiểm tra

1. Vì sao tạo resource cloud bằng cách bấm chuột trên console lại khó review hơn thay đổi code ứng dụng qua pull request?

    ??? note "Đáp án"
        Vì hành động bấm chuột có hiệu lực **ngay lập tức** trên hệ thống thật, không qua bước chờ người khác đọc và góp ý trước — khác với code ứng dụng phải qua pull request (một người khác đọc, phê duyệt) trước khi merge và có hiệu lực.

2. Định nghĩa Infrastructure as Code trong một câu.

    ??? note "Đáp án"
        Là cách quản lý hạ tầng bằng cách định nghĩa hạ tầng trong file code, lưu vào Git, và review thay đổi qua pull request — giống quy trình dùng cho code ứng dụng.

3. Phân biệt declarative với imperative bằng một câu cho mỗi loại.

    ??? note "Đáp án"
        Declarative: khai báo **trạng thái mong muốn cuối cùng**, để công cụ tự tính cách đạt được. Imperative: khai báo **từng bước thao tác** theo đúng thứ tự, công cụ chỉ thực thi đúng các bước đó, không tự suy luận gì thêm.

4. Terraform khác Bicep ở điểm nào về phạm vi nhà cung cấp cloud hỗ trợ?

    ??? note "Đáp án"
        Terraform hỗ trợ nhiều nhà cung cấp cloud khác nhau (AWS, Azure, Google Cloud...) qua cùng một cú pháp HCL. Bicep chỉ hỗ trợ Azure.

5. `terraform plan` và `terraform apply` khác nhau ở điểm nào?

    ??? note "Đáp án"
        `plan` chỉ tính toán và **in ra** danh sách thay đổi sẽ xảy ra, không thực hiện gì trên cloud thật. `apply` **thực sự thực hiện** các thay đổi đó (gọi API tạo/sửa/xoá resource thật).

6. Vì sao đổi tên nội bộ của một resource trong file `.tf` (ví dụ từ `"hoc_lieu"` sang `"tai_lieu"`) lại nguy hiểm nếu chạy `apply` ngay mà không xem `plan`?

    ??? note "Đáp án"
        Terraform không hiểu đây là "đổi tên" — nó hiểu là xoá resource cũ (tên `hoc_lieu`) và tạo một resource mới hoàn toàn (tên `tai_lieu`). Nếu resource đó chứa dữ liệu (storage, database), dữ liệu sẽ mất khi `apply` thực thi việc xoá và tạo lại này.

7. Configuration drift là gì, và vì sao nó xảy ra khi trộn việc bấm chuột trên console với việc dùng Terraform cho cùng một resource?

    ??? note "Đáp án"
        Configuration drift là hiện tượng trạng thái thật trên cloud lệch khỏi trạng thái được mô tả (trong file `.tf` hoặc trong state file). Nó xảy ra khi ai đó sửa resource trực tiếp qua console — Terraform không biết về thay đổi này, nên state file của nó không còn khớp với thực tế, dẫn tới lần `plan` kế tiếp có thể đề xuất ghi đè lại đúng thay đổi vừa bấm tay.

8. State file trong Terraform dùng để làm gì?

    ??? note "Đáp án"
        Lưu lại resource nào Terraform đang quản lý và cấu hình hiện tại của từng resource đó, để Terraform so sánh với file `.tf` khi chạy `plan`/`apply` và biết cần tạo/sửa/xoá gì.

---

??? abstract "DEEP DIVE: chạy `plan`/`apply` như một gate trong CI, và module hoá file `.tf`"
    Chương CI/CD (`.github/workflows/ci.yml` của chính repo Learning Hub này) đã dạy nguyên lý: mọi thay đổi phải qua một job tự động (`gates`, `dotnet`) chạy và **xanh** trước khi job `deploy` được phép chạy, và job `deploy` chỉ chạy khi `needs: [gates, dotnet]` đã xanh VÀ đang ở nhánh `main` (`if: github.ref == 'refs/heads/main'`). Nguyên lý tương tự áp dụng cho IaC trong một pipeline CI/CD hạ tầng thật: một job chạy `terraform plan` trên **mọi** pull request (giống job `gates` chạy trên mọi push/PR), in output ra để người review đọc ngay trong PR — sau đó job `terraform apply` chỉ chạy khi PR đã được merge vào `main`, đúng cấu trúc `needs: [...]` cộng điều kiện nhánh mà `deploy` trong `ci.yml` đang dùng. Khác biệt duy nhất so với `mkdocs gh-deploy --force` (lệnh `deploy` thật trong `ci.yml`) là quy mô rủi ro: deploy sai một trang tài liệu có thể sửa lại và deploy lại ngay; `apply` sai trên hạ tầng có thể xoá dữ liệu không thể khôi phục — vì vậy nhiều tổ chức thêm một bước "chờ phê duyệt thủ công" (manual approval) giữa `plan` và `apply` trong pipeline, thứ mà pipeline `ci.yml` của Learning Hub không cần vì rủi ro của nó thấp hơn nhiều.

    Khi một file `.tf`/`.bicep` phình to (hàng trăm resource), thực tế thường chia nhỏ thành **module** — một thư mục con định nghĩa một nhóm resource liên quan (ví dụ module `network` định nghĩa toàn bộ mạng, module `database` định nghĩa toàn bộ database), rồi file chính chỉ "gọi" các module đó với tham số riêng cho từng môi trường (dev/staging/production dùng cùng module nhưng tham số khác nhau, ví dụ kích thước máy chủ nhỏ hơn ở dev). Terraform còn có khái niệm **workspace** để quản lý nhiều môi trường dùng cùng file `.tf` nhưng state file tách riêng theo từng môi trường — tránh việc lệnh `apply` cho môi trường dev vô tình chạy nhầm vào state của production. Cả hai khái niệm (module, workspace) chỉ thật sự cần thiết khi hạ tầng đã đủ lớn — ở quy mô học tập/dự án nhỏ, một file `.tf` duy nhất tại mỗi môi trường là đủ, đúng tinh thần "giới thiệu khái niệm, không cần thành thạo công cụ" của chương này.

Tiếp theo -> monitoring & observability nền tảng

