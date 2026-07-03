---
tier: core
status: core
owner: core-team
verified_on: "2026-07-01"
dotnet_version: "10.0"
bloom: phân tích
requires: [p2-joins-aggregation]
est_minutes_fast: 40
---

# Subquery & CTE (WITH)

!!! info "Bạn đang ở đây"
    cần trước: join, group by, having, và subquery cơ bản trong where/exists (chương trước).
    mở khoá: viết truy vấn lồng nhau đúng ngữ nghĩa (where/from/select/correlated), dùng exists thay in một cách an toàn, và đặt tên cho truy vấn con bằng cte (kể cả cte đệ quy cho dữ liệu dạng cây) trước khi sang ef core.

> Mục tiêu (đo được): sau chương này bạn có thể **phân tích** một truy vấn lồng phức tạp, phân loại đúng nó là subquery trong WHERE/FROM/SELECT hay correlated, chọn EXISTS/NOT EXISTS thay vì IN/NOT IN khi có rủi ro NULL, viết lại subquery lặp lại thành CTE dễ đọc, và viết một recursive CTE có điều kiện dừng đúng cho dữ liệu dạng cây.

## 0. Câu hỏi/đoán nhanh

Cho hai bảng: `employees(id, name, manager_id, salary)` — `manager_id` trỏ tới `id` của người quản lý (NULL nếu là sếp lớn nhất), và `departments(id, name, budget)`.

1. `SELECT name FROM employees WHERE salary > (SELECT AVG(salary) FROM employees);` — subquery bên trong chạy bao nhiêu lần: một lần hay một lần cho mỗi dòng?
2. `SELECT name FROM employees e WHERE salary > (SELECT AVG(salary) FROM employees WHERE manager_id = e.manager_id);` — subquery này có gì khác câu 1?
3. Muốn liệt kê toàn bộ chuỗi quản lý từ một nhân viên lên tới sếp lớn nhất (số cấp không biết trước) — GROUP BY hay JOIN thường có đủ không?
4. `SELECT name FROM employees WHERE id NOT IN (SELECT manager_id FROM employees);` — nếu cột `manager_id` có ít nhất một dòng NULL, truy vấn này có nguy cơ gì?

???+ note "Đáp án"
    1. **Một lần duy nhất** — đây là subquery độc lập (non-correlated), không tham chiếu gì tới bảng ngoài, nên chỉ cần tính một lần rồi dùng lại cho mọi dòng.
    2. Đây là **correlated subquery** — nó tham chiếu `e.manager_id` từ truy vấn ngoài, nên về mặt logic phải chạy lại cho mỗi dòng `e` khác nhau (mỗi nhân viên so với trung bình lương của *cùng nhóm quản lý* với mình).
    3. **Không đủ** — JOIN thường cần biết trước số cấp (JOIN 1 lần cho 1 cấp). Số cấp không biết trước cần **recursive CTE**, phần cuối chương này.
    4. **Nguy cơ trả về rỗng một cách âm thầm, sai lệch** — nếu tập `(SELECT manager_id FROM employees)` chứa NULL, `NOT IN` sẽ không khớp bất kỳ dòng nào (không phải lỗi cú pháp, chỉ sai kết quả). Xem mục 5 để hiểu vì sao.

## 1. Subquery trong WHERE

### 1.1 Định nghĩa

Subquery trong `WHERE` là một câu `SELECT` được đặt bên trong dấu ngoặc, nằm ngay sau một toán tử so sánh (`=`, `>`, `IN`...) trong mệnh đề `WHERE` của câu lệnh ngoài, để lọc dòng dựa trên kết quả của câu lệnh con đó.

### 1.2 Ví dụ cú pháp tối thiểu

Tìm nhân viên có lương cao hơn mức lương trung bình toàn công ty:

```sql title="SQL"
CREATE TABLE employees (
    id INT PRIMARY KEY,
    name TEXT,
    manager_id INT,
    salary NUMERIC,
    department_id INT
);

INSERT INTO employees (id, name, manager_id, salary, department_id) VALUES
  (1, 'An',   NULL, 5000, 10),
  (2, 'Binh', 1,    3000, 10),
  (3, 'Chi',  1,    4000, 10),
  (4, 'Dung', 2,    2000, 20);

SELECT name, salary
FROM employees
WHERE salary > (SELECT AVG(salary) FROM employees);
```

```text title="Kết quả"
 name | salary
------+--------
 An   |  5000
 Chi  |  4000
```

Trung bình lương là `(5000+3000+4000+2000)/4 = 3500`. Subquery `(SELECT AVG(salary) FROM employees)` chạy **một lần**, trả về giá trị `3500`, rồi câu lệnh ngoài so sánh từng dòng với con số đó — giống hệt như thể bạn viết `WHERE salary > 3500`.

### 1.3 Điều gì xảy ra khi dùng sai

Subquery trong `WHERE` đứng sau toán tử vô hướng (`=`, `>`, `<`...) mà trả về **nhiều hơn một dòng** sẽ gây lỗi runtime:

```sql title="SQL"
SELECT name
FROM employees
WHERE salary = (SELECT salary FROM employees WHERE manager_id = 1);
-- ERROR:  more than one row returned by a subquery used as an expression
```

Ở đây `manager_id = 1` khớp cả `Binh` (3000) và `Chi` (4000) — hai dòng — nên PostgreSQL không biết lấy giá trị nào để so sánh với `=`. Muốn subquery trả nhiều dòng, phải dùng `IN` thay vì `=` (xem mục 5):

```sql title="SQL"
SELECT name
FROM employees
WHERE salary IN (SELECT salary FROM employees WHERE manager_id = 1);
```

```text title="Kết quả"
 name
------
 Binh
 Chi
```

### 1.4 Nhiều điều kiện WHERE lồng subquery cùng lúc

Một câu lệnh có thể chứa nhiều subquery độc lập trong cùng mệnh đề `WHERE`, kết hợp bằng `AND`/`OR` như điều kiện thường:

```sql title="SQL"
SELECT name, salary
FROM employees
WHERE salary > (SELECT AVG(salary) FROM employees)
  AND department_id = (SELECT id FROM departments WHERE name = 'Kỹ thuật');
```

Mỗi subquery được đánh giá độc lập, không phụ thuộc lẫn nhau — PostgreSQL tính từng cái, rồi mới áp `AND` như một điều kiện boolean bình thường.

## 2. Subquery trong FROM (derived table)

### 2.1 Định nghĩa

Subquery trong `FROM` — còn gọi là **derived table** (bảng dẫn xuất) — là một câu `SELECT` đặt trong ngoặc và được đặt bí danh (alias), dùng làm nguồn dữ liệu như thể nó là một bảng thật, ngay trong mệnh đề `FROM` của truy vấn ngoài.

### 2.2 Ví dụ cú pháp tối thiểu

Tính lương trung bình theo từng quản lý, rồi lọc những quản lý có đội lương trung bình trên 3000 (không dùng `HAVING` để minh hoạ riêng derived table):

```sql title="SQL"
SELECT bang_luong.manager_id, bang_luong.luong_tb
FROM (
    SELECT manager_id, AVG(salary) AS luong_tb
    FROM employees
    WHERE manager_id IS NOT NULL
    GROUP BY manager_id
) AS bang_luong
WHERE bang_luong.luong_tb > 3000;
```

```text title="Kết quả"
 manager_id | luong_tb
------------+----------
 1          |   3500
```

Câu `SELECT manager_id, AVG(salary)...` bên trong ngoặc chạy trước, tạo ra một bảng tạm có tên `bang_luong` với hai cột `manager_id` và `luong_tb`. Câu lệnh ngoài coi `bang_luong` như một bảng bình thường và lọc tiếp trên đó.

### 2.3 Điều gì xảy ra khi dùng sai

Sau khi đặt alias cho derived table, mọi tham chiếu cột **phải** dùng alias đó — gọi lại tên bảng gốc bên trong derived table sẽ gây lỗi vì bảng gốc không còn "nhìn thấy" được ở phạm vi câu lệnh ngoài:

```sql title="SQL"
SELECT employees.manager_id
FROM (
    SELECT manager_id, AVG(salary) AS luong_tb
    FROM employees
    GROUP BY manager_id
) AS bang_luong;
-- ERROR:  missing FROM-clause entry for table "employees"
```

Ở câu lệnh ngoài, `FROM` chỉ có một nguồn dữ liệu tên là `bang_luong` (kết quả của derived table) — cái tên `employees` chỉ tồn tại *bên trong* dấu ngoặc, không lộ ra ngoài. Muốn lấy cột `manager_id`, câu lệnh ngoài phải viết `bang_luong.manager_id`.

Một lỗi khác dễ mắc: quên đặt alias tường minh (`AS ...`) cho cột tính toán bên trong derived table. Khi đó PostgreSQL tự đặt tên cột theo tên hàm (ở đây là `avg`, chữ thường), và tên ẩn danh này vẫn tham chiếu được (`bang_luong.avg`) nhưng dễ gây nhầm lẫn hoặc đọc khó hiểu khi truy vấn phức tạp hơn — luôn đặt alias tường minh cho MỌI cột tính toán bên trong derived table để tránh phải đoán tên cột PostgreSQL tự sinh ra.

### 2.4 Ghép nhiều derived table bằng JOIN

Derived table có thể tham gia JOIN như bảng thật, kể cả JOIN với derived table khác:

```sql title="SQL"
SELECT d.name, luong_tb.trung_binh
FROM departments d
JOIN (
    SELECT department_id, AVG(salary) AS trung_binh
    FROM employees
    GROUP BY department_id
) AS luong_tb ON luong_tb.department_id = d.id;
```

Đây là kỹ thuật phổ biến để "tổng hợp trước, JOIN sau" — tránh việc JOIN 1-nhiều rồi mới tổng hợp làm phồng số dòng trước khi tính `AVG`/`SUM` (cạm bẫy đã nêu ở chương JOIN & GROUP BY trước).

## 3. Subquery trong SELECT (scalar subquery)

### 3.1 Định nghĩa

Scalar subquery là một câu `SELECT` đặt trong ngoặc, nằm ngay trong danh sách cột của mệnh đề `SELECT`, chạy lại cho **mỗi dòng** của truy vấn ngoài và phải trả về đúng **một giá trị duy nhất** (một dòng, một cột) cho mỗi lần chạy.

### 3.2 Ví dụ cú pháp tối thiểu

Với mỗi nhân viên, hiển thị thêm cột "tổng số nhân viên trong công ty" (một con số cố định, lặp lại mọi dòng):

```sql title="SQL"
SELECT
    name,
    salary,
    (SELECT COUNT(*) FROM employees) AS tong_nhan_vien
FROM employees;
```

```text title="Kết quả"
 name | salary | tong_nhan_vien
------+--------+----------------
 An   |  5000  |       4
 Binh |  3000  |       4
 Chi  |  4000  |       4
 Dung |  2000  |       4
```

Ở ví dụ này subquery không tham chiếu gì tới dòng ngoài nên giá trị `4` giống hệt cho mọi dòng — nhưng cú pháp này thường hữu ích hơn khi kết hợp với correlated subquery (mục 4), nơi giá trị scalar thay đổi theo từng dòng.

### 3.3 Điều gì xảy ra khi dùng sai

Scalar subquery trả về nhiều hơn một dòng:

```sql title="SQL"
SELECT
    name,
    (SELECT salary FROM employees) AS luong_nguoi_khac
FROM employees
WHERE manager_id = 1;
-- ERROR:  more than one row returned by a subquery used as an expression
```

Vì bảng `employees` có 4 dòng, subquery `(SELECT salary FROM employees)` trả về 4 giá trị salary — không thể ép vào một ô duy nhất của kết quả. Scalar subquery *bắt buộc* phải tự giới hạn còn đúng một dòng (bằng `WHERE`, `LIMIT 1`, hoặc một hàm tổng hợp như `COUNT`/`AVG`/`MAX`).

### 3.4 Scalar subquery trả về NULL khi không có dòng nào khớp

Khác với lỗi "nhiều dòng", khi scalar subquery **không tìm thấy dòng nào**, nó không báo lỗi — nó trả về `NULL`:

```sql title="SQL"
SELECT
    name,
    (SELECT name FROM employees m WHERE m.id = e.manager_id) AS ten_quan_ly
FROM employees e;
```

```text title="Kết quả"
 name | ten_quan_ly
------+-------------
 An   |    NULL      -- An không có quản lý (manager_id NULL) -> subquery không khớp dòng nào -> NULL
 Binh |    An
 Chi  |    An
 Dung |    Binh
```

Đây là hành vi khác biệt quan trọng so với `more than one row`: "0 dòng" → NULL (im lặng, hợp lệ); "nhiều hơn 1 dòng" → lỗi runtime (dừng câu lệnh). Luôn nhớ 2 trường hợp biên này khi thiết kế scalar subquery.

## 4. Correlated subquery

### 4.1 Định nghĩa

Correlated subquery (subquery tương quan) là một subquery — có thể nằm trong `WHERE`, `SELECT`, hay dùng với `EXISTS` — có tham chiếu tới ít nhất một cột của truy vấn ngoài, nên về mặt logic nó phải được đánh giá lại riêng cho **từng dòng** của truy vấn ngoài, thay vì chỉ một lần.

Khác biệt cụ thể với subquery thường (mục 1-3): subquery thường **độc lập** — chạy một lần, giá trị của nó không đổi. Correlated subquery **phụ thuộc** vào dòng đang xét — giá trị của nó thay đổi theo từng dòng ngoài.

### 4.2 Ví dụ cú pháp tối thiểu

Với mỗi nhân viên, so sánh lương của họ với lương trung bình của *chính nhóm cấp dưới cùng một quản lý*:

```sql title="SQL"
SELECT e.name, e.salary, e.manager_id
FROM employees e
WHERE e.salary > (
    SELECT AVG(e2.salary)
    FROM employees e2
    WHERE e2.manager_id = e.manager_id   -- tham chiếu e.manager_id từ truy vấn ngoài
);
```

```text title="Kết quả"
 name | salary | manager_id
------+--------+------------
 Chi  |  4000  |     1
```

Với `Binh` (manager_id=1): trung bình nhóm 1 (gồm Binh 3000, Chi 4000) là 3500 — 3000 không lớn hơn 3500 nên `Binh` bị loại. Với `Chi`: cùng nhóm, trung bình vẫn 3500, và 4000 > 3500 nên `Chi` được giữ. Với `Dung` (manager_id=2, chỉ có một mình trong nhóm): trung bình nhóm 2 là chính lương của `Dung` (2000), nên `2000 > 2000` sai — bị loại. Với `An` (`manager_id` là NULL): so `e2.manager_id = e.manager_id` khi `e.manager_id` là NULL luôn cho kết quả UNKNOWN (không phải TRUE) — xem mục 5 về NULL — nên `An` cũng bị loại dù không có lỗi.

### 4.3 Điều gì xảy ra khi dùng sai

Gõ nhầm bí danh khiến subquery vô tình tham chiếu **chính nó** thay vì bảng ngoài — đây là lỗi nguy hiểm nhất vì **không có exception nào được ném ra**:

```sql title="SQL"
SELECT e.name, e.salary
FROM employees e
WHERE e.salary > (
    SELECT AVG(x.salary) FROM employees x WHERE x.manager_id = x.manager_id
);
-- không lỗi cú pháp, nhưng SAI NGỮ NGHĨA:
-- x.manager_id = x.manager_id luôn đúng (trừ khi NULL) -> AVG tính trên TOÀN BỘ bảng,
-- không phải trên "cùng nhóm quản lý" như ý định ban đầu
```

Bug chỉ lộ ra khi so sánh kết quả với kỳ vọng nghiệp vụ. Luôn kiểm tra: mỗi cột trong subquery có bí danh đúng nguồn (bảng trong subquery hay bảng ngoài) hay không.

### 4.4 Correlated subquery trong SELECT (kết hợp mục 3 và mục 4)

Scalar subquery (mục 3) trở nên hữu ích hơn hẳn khi nó **tương quan** — giá trị thay đổi theo từng dòng ngoài:

```sql title="SQL"
SELECT
    e.name,
    e.salary,
    (
        SELECT COUNT(*)
        FROM employees sub
        WHERE sub.manager_id = e.manager_id
    ) AS so_dong_nghiep_cung_to
FROM employees e;
```

```text title="Kết quả"
 name | salary | so_dong_nghiep_cung_to
------+--------+------------------------
 An   |  5000  |          0
 Binh |  3000  |          2
 Chi  |  4000  |          2
 Dung |  2000  |          1
```

Mỗi dòng của truy vấn ngoài khiến subquery chạy lại với một `e.manager_id` khác — đây chính là điểm phân biệt correlated scalar subquery với scalar subquery độc lập ở mục 3.2 (nơi kết quả giống hệt nhau cho mọi dòng).

## 5. EXISTS / NOT EXISTS so với IN / NOT IN

### 5.1 Định nghĩa

`EXISTS (subquery)` là một biểu thức chỉ trả `TRUE`/`FALSE` — `TRUE` nếu subquery bên trong trả về **ít nhất một dòng** (nội dung dòng đó không quan trọng), `FALSE` nếu subquery không trả dòng nào. `EXISTS` gần như luôn được viết dưới dạng correlated subquery (tham chiếu bảng ngoài), vì nếu không tương quan thì kết quả `TRUE`/`FALSE` sẽ giống hệt cho mọi dòng — vô nghĩa để lọc.

### 5.2 Ví dụ cú pháp tối thiểu

Tìm quản lý (người có ít nhất một cấp dưới):

```sql title="SQL"
SELECT m.name
FROM employees m
WHERE EXISTS (
    SELECT 1 FROM employees e WHERE e.manager_id = m.id
);
```

```text title="Kết quả"
 name
------
 An
 Binh
```

`SELECT 1` bên trong `EXISTS` là quy ước phổ biến — giá trị `1` không được dùng ở đâu cả, PostgreSQL chỉ quan tâm "có dòng hay không", nên viết `SELECT 1` hay `SELECT *` cho hiệu năng như nhau, PostgreSQL không thật sự lấy dữ liệu cột đó ra.

### 5.3 So sánh IN với EXISTS khi dữ liệu "sạch" (không có NULL)

Khi cột dùng trong subquery **chắc chắn không có NULL**, `IN` và `EXISTS` cho kết quả giống nhau, chỉ khác cách viết:

```sql title="SQL"
-- Cách 1: IN
SELECT name FROM employees WHERE department_id IN (SELECT id FROM departments WHERE budget > 100000);

-- Cách 2: EXISTS (correlated) — cùng kết quả, khi department_id KHÔNG có NULL
SELECT e.name
FROM employees e
WHERE EXISTS (
    SELECT 1 FROM departments d WHERE d.id = e.department_id AND d.budget > 100000
);
```

Cả hai cách đều đúng ở đây vì `id` của `departments` là khoá chính (không NULL). Sự khác biệt thật sự chỉ xuất hiện với **NOT IN / NOT EXISTS**, xem mục 5.4.

### 5.4 Điều gì xảy ra khi dùng sai — NOT IN với cột có thể NULL

Nhầm `NOT IN` với `NOT EXISTS` khi subquery có thể chứa NULL:

```sql title="SQL"
-- Ý định: tìm nhân viên KHÔNG PHẢI là quản lý của ai (không có cấp dưới)
SELECT name
FROM employees
WHERE id NOT IN (SELECT manager_id FROM employees);
```

```text title="Kết quả"
(0 dòng) -- SAI: kỳ vọng phải ra Chi và Dung
```

Lý do: `SELECT manager_id FROM employees` trả về tập `{NULL, 1, 1, 2}` (dòng của `An` có `manager_id` là NULL). Khi `NOT IN` so một giá trị với một tập **có chứa NULL**, kết quả của phép so sánh với NULL luôn là UNKNOWN, và `NOT IN` cần *toàn bộ* các so sánh đều `TRUE` (không khớp bất kỳ giá trị nào) để trả `TRUE` — nhưng UNKNOWN làm hỏng cả biểu thức, khiến `NOT IN` trả UNKNOWN (bị coi như FALSE) cho **mọi dòng**, kể cả dòng lẽ ra phải khớp. Đây không phải lỗi cú pháp — không có exception nào được ném ra, kết quả chỉ âm thầm rỗng hoặc thiếu dòng.

Sửa đúng bằng `NOT EXISTS` (không bị ảnh hưởng bởi NULL vì nó không "so sánh giá trị", chỉ hỏi "có dòng khớp điều kiện không"):

```sql title="SQL"
SELECT name
FROM employees e
WHERE NOT EXISTS (
    SELECT 1 FROM employees m WHERE m.manager_id = e.id
);
```

```text title="Kết quả"
 name
------
 Chi
 Dung
```

Cách sửa thay thế (nếu vẫn muốn dùng `NOT IN`): lọc NULL tường minh bên trong subquery:

```sql title="SQL"
SELECT name
FROM employees
WHERE id NOT IN (
    SELECT manager_id FROM employees WHERE manager_id IS NOT NULL
);
```

```text title="Kết quả"
 name
------
 Chi
 Dung
```

Cách này cũng đúng, nhưng dễ quên hơn `NOT EXISTS` — nếu sau này ai đó thêm một cột khác vào subquery mà quên lọc NULL, bug quay lại. `NOT EXISTS` an toàn theo thiết kế, không phụ thuộc vào việc nhớ lọc NULL.

!!! danger "Quy tắc nhớ: NOT IN + cột có thể NULL = nguy hiểm"
    Nếu subquery của `NOT IN` truy vấn một cột **có khả năng chứa NULL**, luôn đổi sang `NOT EXISTS` hoặc thêm `WHERE cot IS NOT NULL` vào bên trong subquery. `IN`/`EXISTS` (không có NOT) không bị vấn đề này — chỉ `NOT IN` mới sai khi gặp NULL, vì phép phủ định của UNKNOWN vẫn là UNKNOWN, không lật thành TRUE.

### 5.5 Bảng tổng hợp IN/NOT IN/EXISTS/NOT EXISTS

Chỉ đọc bảng này SAU khi đã hiểu rõ từng khái niệm ở trên — đây là tổng kết, không phải nơi học lần đầu:

| Toán tử | An toàn với NULL trong subquery? | Thường dùng khi | Có bắt buộc correlated không? |
|---------|:---:|------------------|:---:|
| `IN` | có | so khớp với danh sách giá trị cố định hoặc subquery không NULL | không |
| `NOT IN` | **không** | tránh dùng nếu subquery có thể NULL | không |
| `EXISTS` | có | kiểm tra "có ít nhất một dòng khớp" | thường có (mới có ý nghĩa lọc) |
| `NOT EXISTS` | có | anti-join an toàn, thay thế `NOT IN` | thường có |

## 6. CTE với WITH — viết lại subquery cho dễ đọc

### 6.1 Định nghĩa

CTE (Common Table Expression — biểu thức bảng chung) là một câu `SELECT` được đặt tên bằng từ khoá `WITH ten_cte AS (...)` ngay trước câu lệnh chính, cho phép truy vấn chính (và các CTE khác) tham chiếu tới nó bằng tên như một bảng tạm, thay vì phải lồng subquery trực tiếp vào `FROM`.

### 6.2 Ví dụ cú pháp tối thiểu

Viết lại ví dụ derived table ở mục 2 bằng CTE:

```sql title="SQL"
WITH bang_luong AS (
    SELECT manager_id, AVG(salary) AS luong_tb
    FROM employees
    WHERE manager_id IS NOT NULL
    GROUP BY manager_id
)
SELECT manager_id, luong_tb
FROM bang_luong
WHERE luong_tb > 3000;
```

```text title="Kết quả"
 manager_id | luong_tb
------------+----------
 1          |   3500
```

Kết quả giống hệt mục 2 — CTE **không phải** một cấu trúc dữ liệu mới, nó chỉ là cách *đặt tên* cho một subquery để câu lệnh chính đọc dễ hơn (không phải đếm ngoặc lồng nhau), và để dùng lại cùng một truy vấn con nhiều lần trong cùng câu lệnh mà không phải viết lại subquery đó nhiều lần.

### 6.3 Điều gì xảy ra khi dùng sai

Tham chiếu CTE trước khi nó được định nghĩa, hoặc quên dấu phẩy khi khai báo nhiều CTE:

```sql title="SQL"
WITH a AS (SELECT 1 AS x)
     b AS (SELECT x FROM a)   -- thiếu dấu phẩy sau CTE "a"
SELECT * FROM b;
-- ERROR:  syntax error at or near "b"
```

Nhiều CTE trong cùng một `WITH` phải cách nhau bằng dấu phẩy, giống khai báo nhiều cột — PostgreSQL đọc `b AS (...)` như một token lạ ngay sau khi đã đóng ngoặc CTE `a` mà không thấy dấu phẩy. Viết đúng:

```sql title="SQL"
WITH a AS (SELECT 1 AS x),
     b AS (SELECT x FROM a)
SELECT * FROM b;
```

Một lỗi khác: một CTE (không đệ quy) tham chiếu **chính nó**:

```sql title="SQL"
WITH loi AS (
    SELECT * FROM loi
)
SELECT * FROM loi;
-- ERROR:  relation "loi" does not exist (khi thiếu RECURSIVE, CTE thường KHÔNG được tự tham chiếu)
```

CTE thường (không có từ khoá `RECURSIVE`) không được phép tham chiếu tới chính tên của nó bên trong định nghĩa — muốn tự tham chiếu, bắt buộc phải dùng `WITH RECURSIVE` (mục 7).

### 6.4 Nhiều CTE dùng lại nhau trong cùng một câu lệnh

Lợi ích rõ nhất của CTE so với subquery lồng: một CTE có thể được tham chiếu **nhiều lần** trong truy vấn chính (hoặc bởi CTE khác định nghĩa sau nó) mà không phải chép lại code:

```sql title="SQL"
WITH luong_theo_phong AS (
    SELECT department_id, AVG(salary) AS luong_tb, COUNT(*) AS so_nguoi
    FROM employees
    GROUP BY department_id
),
phong_luong_cao AS (
    SELECT department_id
    FROM luong_theo_phong
    WHERE luong_tb > 2500
)
SELECT d.name, lp.luong_tb, lp.so_nguoi
FROM departments d
JOIN luong_theo_phong lp ON lp.department_id = d.id
WHERE d.id IN (SELECT department_id FROM phong_luong_cao);
```

`luong_theo_phong` được định nghĩa một lần nhưng dùng ở cả CTE thứ hai (`phong_luong_cao`) lẫn câu lệnh chính (JOIN) — nếu viết bằng subquery lồng trực tiếp, bạn sẽ phải lặp lại toàn bộ `SELECT department_id, AVG(salary)...GROUP BY` hai lần.

### 6.5 CTE không tự động nhanh hơn subquery

Một hiểu lầm phổ biến: CTE luôn được "vật chất hoá" (materialize — tính trước, lưu tạm) nên luôn nhanh hơn subquery lồng trực tiếp. Điều này **sai** kể từ PostgreSQL 12: trình tối ưu có thể **inline** (nhúng thẳng) CTE không đệ quy vào truy vấn chính giống như xử lý một subquery bình thường, trừ khi CTE được tham chiếu nhiều lần, đệ quy, hoặc có `MATERIALIZED` ép buộc. Ép vật chất hoá tường minh:

```sql title="SQL"
WITH bang_luong AS MATERIALIZED (
    SELECT manager_id, AVG(salary) AS luong_tb
    FROM employees
    GROUP BY manager_id
)
SELECT * FROM bang_luong WHERE luong_tb > 3000;
```

`MATERIALIZED` buộc PostgreSQL tính `bang_luong` thành một bảng tạm trong bộ nhớ trước, rồi mới lọc — hữu ích khi CTE tốn kém và được dùng lại nhiều lần, nhưng có thể chậm hơn nếu `WHERE luong_tb > 3000` lẽ ra có thể được đẩy xuống lọc sớm. Ngược lại, ép `NOT MATERIALIZED` buộc PostgreSQL luôn inline:

```sql title="SQL"
WITH bang_luong AS NOT MATERIALIZED (
    SELECT manager_id, AVG(salary) AS luong_tb
    FROM employees
    GROUP BY manager_id
)
SELECT * FROM bang_luong WHERE luong_tb > 3000;
```

Mặc định (không ghi gì) để trình tối ưu tự quyết là lựa chọn an toàn cho hầu hết trường hợp; chỉ can thiệp tường minh khi `EXPLAIN ANALYZE` cho thấy kế hoạch không tối ưu.

## 7. Recursive CTE — dữ liệu dạng cây

### 7.1 Định nghĩa

Recursive CTE là một CTE khai báo bằng `WITH RECURSIVE`, gồm hai phần nối bằng `UNION` hoặc `UNION ALL`: một **anchor member** (truy vấn khởi tạo, không tham chiếu chính CTE) và một **recursive member** (truy vấn tham chiếu lại chính tên CTE đó), lặp lại việc chạy recursive member trên kết quả mới sinh ra cho tới khi recursive member không sinh thêm dòng nào — dùng để duyệt dữ liệu có cấu trúc cây/phân cấp mà số cấp không biết trước.

### 7.2 Ví dụ cú pháp tối thiểu

Lấy toàn bộ chuỗi quản lý từ `Dung` (id=4) lên tới sếp lớn nhất:

```sql title="SQL"
WITH RECURSIVE chuoi_quan_ly AS (
    -- anchor: điểm bắt đầu, KHÔNG tham chiếu chuoi_quan_ly
    SELECT id, name, manager_id, 1 AS cap
    FROM employees
    WHERE id = 4

    UNION ALL

    -- recursive: tham chiếu lại chính CTE "chuoi_quan_ly"
    SELECT e.id, e.name, e.manager_id, cql.cap + 1
    FROM employees e
    JOIN chuoi_quan_ly cql ON e.id = cql.manager_id   -- điều kiện dừng ẩn: hết khớp thì dừng
)
SELECT id, name, manager_id, cap
FROM chuoi_quan_ly
ORDER BY cap;
```

```text title="Kết quả"
 id | name | manager_id | cap
----+------+------------+-----
 4  | Dung |     2      |  1
 2  | Binh |     1      |  2
 1  | An   |    NULL    |  3
```

Cách đọc: cấp 1 là chính `Dung`. Cấp 2 là người có `id` khớp `manager_id` của `Dung` (tức `Binh`, id=2). Cấp 3 là người có `id` khớp `manager_id` của `Binh` (tức `An`, id=1). Vòng lặp dừng tự nhiên ở đây vì không có ai có `id = An.manager_id` (An.manager_id là NULL, không khớp `id` của ai) — recursive member không sinh thêm dòng nào nữa nên PostgreSQL dừng.

Về mặt cơ chế thực thi: PostgreSQL chạy anchor member một lần, đưa kết quả vào một "bảng làm việc" tạm (working table); sau đó lặp — mỗi vòng chạy recursive member CHỈ trên các dòng **mới sinh ra ở vòng trước** (không phải toàn bộ CTE tích luỹ), gộp kết quả mới vào CTE cuối cùng, cho tới khi một vòng không sinh dòng nào.

### 7.3 Điều gì xảy ra khi dùng sai — thiếu điều kiện dừng

Nếu dữ liệu có chu trình (VD lỗi nhập liệu khiến A quản lý B, B quản lý A) hoặc bạn viết điều kiện JOIN sai khiến recursive member luôn sinh ra dòng mới, PostgreSQL sẽ lặp mãi cho tới khi hết bộ nhớ:

```sql title="SQL"
-- Giả sử dữ liệu lỗi: id=1 có manager_id=2, và id=2 có manager_id=1 (chu trình)
WITH RECURSIVE vong_lap AS (
    SELECT id, name, manager_id FROM employees WHERE id = 1
    UNION ALL
    SELECT e.id, e.name, e.manager_id
    FROM employees e
    JOIN vong_lap v ON e.id = v.manager_id
)
SELECT * FROM vong_lap;
-- ERROR:  out of memory / hoặc chạy vô hạn tới khi bị hủy (statement_timeout)
```

Cách phòng ngừa cơ bản nhất: luôn giới hạn độ sâu tối đa bằng điều kiện `WHERE cap < N` trong recursive member:

```sql title="SQL"
WITH RECURSIVE chuoi_an_toan AS (
    SELECT id, name, manager_id, 1 AS cap
    FROM employees WHERE id = 4
    UNION ALL
    SELECT e.id, e.name, e.manager_id, cql.cap + 1
    FROM employees e
    JOIN chuoi_an_toan cql ON e.id = cql.manager_id
    WHERE cql.cap < 50          -- lưới an toàn: dừng cứng ở cấp 50 dù dữ liệu có lỗi
)
SELECT * FROM chuoi_an_toan;
```

### 7.4 `UNION` so với `UNION ALL` trong recursive CTE

Nếu dùng `UNION` (không có `ALL`) thay vì `UNION ALL`, PostgreSQL sẽ khử trùng lặp sau mỗi vòng lặp — điều này giúp tự động dừng khi gặp chu trình đơn giản (vì dòng lặp lại y hệt sẽ bị loại, không sinh dòng "mới"), nhưng **chậm hơn đáng kể** vì phải so sánh toàn bộ cột để khử trùng ở mỗi vòng, và không phải chu trình nào cũng sinh ra dòng giống hệt nhau (VD có thêm cột `cap` tăng dần thì `UNION` không giúp gì vì mỗi dòng luôn khác nhau ở cột `cap`). Vì vậy `UNION ALL` kèm điều kiện dừng tường minh (`WHERE cap < N`) vẫn là cách an toàn và hiệu quả hơn trong đa số trường hợp thực chiến.

### 7.5 Ứng dụng thực tế: cây danh mục sản phẩm

Bài toán phổ biến hơn "chuỗi quản lý" trong thực chiến là **cây danh mục** (category tree) — một danh mục có thể có danh mục con, con lại có con, số cấp không cố định:

```sql title="SQL"
CREATE TABLE categories (
    id INT PRIMARY KEY,
    name TEXT,
    parent_id INT   -- NULL nếu là danh mục gốc
);

INSERT INTO categories (id, name, parent_id) VALUES
  (1, 'Điện tử',      NULL),
  (2, 'Điện thoại',   1),
  (3, 'Laptop',       1),
  (4, 'Điện thoại Android', 2),
  (5, 'Điện thoại iOS',     2);

WITH RECURSIVE cay_danh_muc AS (
    SELECT id, name, parent_id, 0 AS cap_do, name::TEXT AS duong_dan
    FROM categories
    WHERE parent_id IS NULL          -- anchor: danh mục gốc

    UNION ALL

    SELECT c.id, c.name, c.parent_id, cdm.cap_do + 1,
           (cdm.duong_dan || ' > ' || c.name)::TEXT
    FROM categories c
    JOIN cay_danh_muc cdm ON c.parent_id = cdm.id
)
SELECT id, cap_do, duong_dan
FROM cay_danh_muc
ORDER BY duong_dan;
```

```text title="Kết quả"
 id | cap_do | duong_dan
----+--------+------------------------------------
 1  |   0    | Điện tử
 3  |   1    | Điện tử > Laptop
 2  |   1    | Điện tử > Điện thoại
 4  |   2    | Điện tử > Điện thoại > Điện thoại Android
 5  |   2    | Điện tử > Điện thoại > Điện thoại iOS
```

Cột `duong_dan` (đường dẫn) tích luỹ dần qua mỗi lần đệ quy bằng `||` (nối chuỗi PostgreSQL) — một kỹ thuật thường dùng để hiển thị breadcrumb hoặc kiểm tra chu trình (nếu `id` của dòng mới đã xuất hiện trong `duong_dan`, dừng lại thay vì đệ quy tiếp).

### 7.6 Đi ngược chiều: từ lá lên gốc so với từ gốc xuống lá

Hai ví dụ trên minh hoạ hai hướng duyệt cây khác nhau, dễ nhầm nếu không phân biệt rõ:

- **Từ lá lên gốc** (mục 7.2, "chuỗi quản lý"): anchor bắt đầu từ MỘT dòng cụ thể (`WHERE id = 4`), recursive member đi theo `manager_id` để **leo lên cha**. Dùng khi biết điểm xuất phát và muốn tìm tổ tiên.
- **Từ gốc xuống lá** (mục 7.5, "cây danh mục"): anchor bắt đầu từ TẤT CẢ dòng gốc (`WHERE parent_id IS NULL`), recursive member đi theo `parent_id` để **tìm con**. Dùng khi muốn liệt kê toàn bộ cây hoặc một nhánh con cháu.

Cả hai đều hợp lệ về cú pháp `WITH RECURSIVE` — điểm khác biệt nằm ở điều kiện `WHERE` của anchor và chiều của điều kiện JOIN trong recursive member (`e.id = cql.manager_id` khi leo lên, `c.parent_id = cdm.id` khi đi xuống).

## Cạm bẫy & thực chiến

- **`NOT IN` với cột có thể NULL**: như mục 5.4, `NOT IN` trả về rỗng một cách âm thầm (không lỗi) nếu subquery chứa dù chỉ một NULL. Luôn ưu tiên `NOT EXISTS`, hoặc lọc `IS NOT NULL` bên trong subquery của `NOT IN`.
- **Correlated subquery chạy lại cho từng dòng ngoài**: với bảng lớn, một correlated subquery trong `WHERE` có thể khiến truy vấn chậm tuyến tính theo số dòng ngoài nhân số dòng subquery quét mỗi lần. Cân nhắc viết lại thành JOIN + GROUP BY (dùng derived table hoặc CTE) nếu có thể, vì optimizer thường xử lý JOIN tốt hơn vòng lặp con.
- **Recursive CTE không có điều kiện dừng rõ ràng**: nếu dữ liệu cây có khả năng bị lỗi thành chu trình (A→B→A), recursive CTE sẽ chạy vô hạn cho tới khi bị `statement_timeout` cắt hoặc hết bộ nhớ. Luôn thêm giới hạn độ sâu (`WHERE cap < 50`) làm lưới an toàn, kể cả khi tin dữ liệu sạch.
- **CTE không phải "luôn nhanh hơn"**: từ PostgreSQL 12, CTE không đệ quy mặc định có thể bị inline như subquery thường; đừng giả định `WITH` tự động tối ưu hiệu năng — dùng `EXPLAIN ANALYZE` để kiểm chứng thay vì đoán.
- **Nhầm bí danh trong correlated subquery**: lỗi kiểu `x.manager_id = x.manager_id` (tự tham chiếu chính subquery thay vì bảng ngoài) không gây lỗi cú pháp, chỉ âm thầm sai kết quả — luôn đọc kỹ từng bí danh trong subquery lồng sâu.
- **Scalar subquery trả nhiều dòng**: bất kỳ subquery nào đặt trong ngữ cảnh "một giá trị" (sau `=`, `>`, hoặc trong danh sách `SELECT`) mà trả về nhiều hơn một dòng sẽ ném lỗi runtime `more than one row returned by a subquery used as an expression` — luôn tự hỏi "subquery này có được đảm bảo tối đa 1 dòng không?" trước khi viết.
- **Nhầm "0 dòng" với "lỗi"**: scalar subquery không tìm thấy dòng nào trả về `NULL` một cách hợp lệ, không phải lỗi — nhưng nếu code sau đó không xử lý `NULL` (VD đưa vào phép cộng số học mà không `COALESCE`), kết quả toàn chuỗi tính toán sẽ âm thầm thành `NULL`.
- **Dùng `UNION` thay vì `UNION ALL` trong recursive CTE mà không hiểu vì sao**: `UNION` khử trùng toàn bộ cột sau mỗi vòng, chậm hơn và không phải lúc nào cũng ngăn được vòng lặp vô hạn (nếu có cột đếm cấp tăng dần, mỗi dòng luôn "khác nhau" nên `UNION` không loại được gì) — ưu tiên `UNION ALL` + điều kiện dừng tường minh.

## Bài tập

### Bài 1 (giàn giáo) — correlated subquery trong SELECT

Viết truy vấn liệt kê tên nhân viên và lương, kèm cột "chênh lệch so với lương trung bình của phòng ban mình" — dùng correlated subquery. Điền vào chỗ trống:

```sql title="SQL"
SELECT
    e.name,
    e.salary,
    e.salary - (
        SELECT AVG(e2.salary)
        FROM employees e2
        WHERE e2.department_id = ____________   -- <-- điền tham chiếu đúng
    ) AS chenh_lech
FROM employees e;
```

???+ success "Lời giải"
    ```sql title="SQL"
    SELECT
        e.name,
        e.salary,
        e.salary - (
            SELECT AVG(e2.salary)
            FROM employees e2
            WHERE e2.department_id = e.department_id
        ) AS chenh_lech
    FROM employees e;
    ```
    Vì sao: đây là correlated subquery — `e2.department_id = e.department_id` tham chiếu `e` (dòng đang xét của truy vấn ngoài), nên trung bình được tính riêng cho từng phòng ban, khác với subquery độc lập (chỉ có một AVG chung cho cả công ty).

### Bài 2 (giàn giáo) — EXISTS thay cho NOT IN an toàn với NULL

Bảng `orders(id, customer_id)` có thể có `customer_id` NULL (đơn khách vãng lai không đăng ký). Viết truy vấn tìm khách hàng `customers(id, name)` **chưa từng** đặt đơn nào, tránh bẫy NULL. Điền vào chỗ trống:

```sql title="SQL"
SELECT c.name
FROM customers c
WHERE NOT ____________ (
    SELECT 1 FROM orders o WHERE o.customer_id = c.id
);
```

???+ success "Lời giải"
    ```sql title="SQL"
    SELECT c.name
    FROM customers c
    WHERE NOT EXISTS (
        SELECT 1 FROM orders o WHERE o.customer_id = c.id
    );
    ```
    Vì sao: nếu dùng `NOT IN (SELECT customer_id FROM orders)` thay vì `NOT EXISTS`, một dòng `orders.customer_id IS NULL` bất kỳ (đơn khách vãng lai) sẽ khiến toàn bộ `NOT IN` trả UNKNOWN cho mọi khách hàng, làm truy vấn trả về rỗng dù có khách chưa từng đặt đơn. `NOT EXISTS` không so giá trị trực tiếp nên không bị NULL trong `orders.customer_id` ảnh hưởng.

### Bài 3 (thiết kế) — recursive CTE đếm con cháu

Bảng `categories(id, name, parent_id)` như trong chương. Viết một recursive CTE trả về **số lượng danh mục con cháu (trực tiếp và gián tiếp)** của danh mục gốc `id = 1`, cùng danh sách `id` của toàn bộ con cháu đó. Không có starter — tự thiết kế anchor và recursive member.

???+ success "Lời giải"
    ```sql title="SQL"
    WITH RECURSIVE con_chau AS (
        SELECT id
        FROM categories
        WHERE parent_id = 1        -- anchor: con trực tiếp của danh mục 1

        UNION ALL

        SELECT c.id
        FROM categories c
        JOIN con_chau cc ON c.parent_id = cc.id   -- đệ quy: con của con
    )
    SELECT COUNT(*) AS so_luong, ARRAY_AGG(id) AS danh_sach_id
    FROM con_chau;
    ```
    Vì sao: anchor bắt đầu từ các con trực tiếp (`parent_id = 1`), không phải từ chính `id = 1` — vì đề bài chỉ muốn đếm con cháu, không tính chính nó. Mỗi vòng đệ quy tìm tiếp con của các dòng vừa sinh ra ở vòng trước, dừng khi không còn `parent_id` nào khớp. `ARRAY_AGG` gộp toàn bộ `id` thành một mảng để xem danh sách, `COUNT(*)` đếm tổng số dòng CTE sinh ra.

## Tự kiểm tra

1. Subquery trong `WHERE` khác subquery trong `FROM` (derived table) ở điểm nào về vai trò trong câu lệnh?
2. Vì sao scalar subquery trong `SELECT` bắt buộc phải trả về đúng một dòng, một cột — và điều gì xảy ra nếu nó không khớp dòng nào (khác với khớp nhiều dòng)?
3. Correlated subquery khác subquery thường (không tương quan) ở điểm nào, và vì sao correlated subquery thường chạy chậm hơn với bảng lớn?
4. Vì sao `NOT IN (subquery)` có thể trả về kết quả rỗng một cách sai lệch, còn `NOT EXISTS` thì không bị vấn đề này?
5. CTE (`WITH`) có phải luôn nhanh hơn subquery lồng trực tiếp không? Giải thích ngắn gọn.
6. Recursive CTE gồm hai phần nào, nối với nhau bằng từ khoá gì, và điều kiện gì khiến nó dừng đệ quy?
7. Vì sao nên ưu tiên `UNION ALL` hơn `UNION` trong hầu hết recursive CTE thực chiến?
8. Viết truy vấn dùng `EXISTS` (không dùng `IN`) để tìm khách hàng có ít nhất một đơn hàng, cho bảng `customers(id)` và `orders(id, customer_id)`.

??? note "Đáp án"
    1. Subquery trong `WHERE` trả về một giá trị hoặc một tập giá trị dùng để **lọc** dòng của truy vấn ngoài; subquery trong `FROM` (derived table) đóng vai trò **một bảng nguồn** để truy vấn ngoài `SELECT`/`JOIN` tiếp lên trên, không dùng để so sánh trực tiếp.
    2. Vì kết quả của nó phải được đặt vừa vào **một ô** trong hàng kết quả của truy vấn ngoài — SQL không có cách nào biểu diễn "nhiều giá trị trong một ô". Nếu subquery trả về nhiều dòng, PostgreSQL báo lỗi runtime `more than one row returned`; nếu nó không khớp dòng nào, subquery trả về `NULL` một cách hợp lệ, không phải lỗi.
    3. Correlated subquery tham chiếu tới cột của truy vấn ngoài nên về mặt logic phải đánh giá lại cho từng dòng ngoài; subquery thường độc lập, chỉ cần tính một lần. Vì phải chạy lại nhiều lần (tối đa bằng số dòng ngoài), correlated subquery dễ chậm hơn khi bảng lớn, đặc biệt nếu bên trong nó lại quét toàn bảng mỗi lần.
    4. Nếu subquery của `NOT IN` trả về tập chứa NULL, so sánh giá trị với NULL cho kết quả UNKNOWN, và phép phủ định/kết hợp AND ẩn bên trong `NOT IN` khiến toàn bộ điều kiện trở thành UNKNOWN (bị coi như FALSE) cho mọi dòng — dẫn tới kết quả rỗng bất ngờ. `NOT EXISTS` không so sánh giá trị trực tiếp với tập kết quả, nó chỉ hỏi "có dòng khớp điều kiện hay không", nên không bị NULL trong subquery ảnh hưởng.
    5. Không. Từ PostgreSQL 12, CTE không đệ quy có thể được trình tối ưu **inline** (nhúng) như một subquery thường, trừ khi ép `MATERIALIZED`, dùng đệ quy, hoặc được tham chiếu nhiều lần. Hiệu năng thực tế cần kiểm chứng bằng `EXPLAIN ANALYZE`, không nên giả định.
    6. Gồm **anchor member** (truy vấn khởi tạo, không tham chiếu tên CTE) và **recursive member** (truy vấn tham chiếu lại chính tên CTE), nối bằng `UNION` hoặc `UNION ALL`. Nó dừng khi recursive member, chạy trên tập kết quả mới nhất, không còn sinh ra dòng nào nữa (VD hết dòng khớp điều kiện JOIN).
    7. Vì `UNION` khử trùng lặp bằng cách so sánh toàn bộ cột sau mỗi vòng lặp, tốn chi phí hơn hẳn `UNION ALL`; đồng thời nếu CTE có một cột luôn tăng dần (như cấp độ), mỗi dòng luôn khác nhau nên `UNION` không loại được vòng lặp — điều kiện dừng tường minh (`WHERE cap < N`) mới thực sự đáng tin cậy.
    8. ```sql title="SQL"
       SELECT c.id
       FROM customers c
       WHERE EXISTS (SELECT 1 FROM orders o WHERE o.customer_id = c.id);
       ```

??? abstract "DEEP DIVE: phát hiện chu trình, LATERAL, và CTE ghi dữ liệu"
    - **Phát hiện chu trình trong recursive CTE**: để an toàn tuyệt đối với dữ liệu cây có thể lỗi thành chu trình, tích luỹ một mảng "đường đi đã qua" (`id_path INT[]`) trong mỗi vòng đệ quy, và thêm điều kiện `WHERE NOT (c.id = ANY(cdm.id_path))` trong recursive member để dừng ngay khi phát hiện `id` đã từng xuất hiện trước đó — PostgreSQL 14+ còn hỗ trợ cú pháp `CYCLE` chuyên dụng (`WITH RECURSIVE ... CYCLE id SET is_cycle USING path`) để làm việc này gọn hơn.
    - **LATERAL**: một derived table có thể tham chiếu cột của bảng đứng trước nó trong cùng `FROM` nếu được đánh dấu `LATERAL` — về bản chất là "correlated subquery nhưng được phép trả nhiều dòng", rất hữu ích cho bài toán "lấy top-N mỗi nhóm" (VD 3 đơn hàng gần nhất của mỗi khách) mà `GROUP BY` thường không làm được gọn.
    - **Writable CTE**: PostgreSQL cho phép `WITH` chứa `INSERT`/`UPDATE`/`DELETE` có mệnh đề `RETURNING`, rồi CTE khác đọc lại kết quả đó trong cùng một câu lệnh — hữu ích để "xoá rồi lưu lại các dòng đã xoá vào bảng khác" trong một transaction ngầm định, nhưng cần cẩn trọng vì tất cả các nhánh `WITH` trong PostgreSQL nhìn thấy **cùng một snapshot** dữ liệu tại thời điểm câu lệnh bắt đầu chạy.
    - **Khi dịch sang EF Core** (chương sau): EF Core dịch subquery `Where(x => x.Prop == other.Where(...).Select(...).FirstOrDefault())` thành scalar subquery hoặc `APPLY`/`LATERAL JOIN` tuỳ ngữ cảnh; recursive CTE **không có** cú pháp LINQ tương ứng trực tiếp — thường phải viết bằng SQL thô (`FromSqlRaw`) hoặc xử lý đệ quy ở tầng ứng dụng.

Tiếp theo -> ef core
