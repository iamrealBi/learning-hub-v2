---
tier: core
status: core
owner: core-team
verified_on: "2026-07-01"
dotnet_version: "10.0"
bloom: "Áp dụng"
requires: [p2-sql]
est_minutes_fast: 35
---

# Lọc & Biểu thức nâng cao

!!! info "Bạn đang ở đây"
    cần trước: sql nền tảng (SELECT/WHERE/ORDER BY/LIMIT, kiểu dữ liệu, và cách NULL làm điều kiện trả UNKNOWN).
    mở khoá sau bài này: join/group by/subquery — vì các mệnh đề lọc và biểu thức ở đây sẽ xuất hiện lại bên trong JOIN, GROUP BY, HAVING.
    ⏱️ fast path ~35 phút · deep dive thêm ~25 phút (tuỳ chọn).

> **Mục tiêu (đo được):** Sau bài này bạn **áp dụng** được `LIKE/ILIKE`, `IN`/`NOT IN`, `BETWEEN`, `CASE WHEN`, `COALESCE`, `NULLIF`, `DISTINCT` và các hàm chuỗi cơ bản để viết điều kiện lọc và biểu thức tính toán đúng; **giải thích** được vì sao `NOT IN` cùng `NULL` trả về tập rỗng và biết cách tránh bẫy đó.

---

## 0. Kiểm tra trước (30 giây) — bạn đoán kết quả nào?

Cho bảng `products(id, name, category_id)` với 3 dòng: `(1,'Bàn phím', 10)`, `(2,'Chuột', 20)`, `(3,'Tai nghe', NULL)`.
Có một danh sách `bad_ids` (các category_id không được duyệt) lấy từ truy vấn con, và nó **chứa một NULL**. Câu này trả về bao nhiêu dòng? **Đoán trước** khi mở đáp án.

```sql title="SQL"
SELECT name
FROM products
WHERE category_id NOT IN (10, NULL);
```

??? note "Đáp án — bấm để mở SAU khi đã đoán"
    Trả về **0 dòng** — kể cả `Chuột` (category_id = 20, rõ ràng khác 10) cũng **bị loại**!
    Lý do: `NOT IN (10, NULL)` được PostgreSQL hiểu là `category_id <> 10 AND category_id <> NULL`. Vế `category_id <> NULL` luôn cho `UNKNOWN` (không phải `FALSE`), và `TRUE AND UNKNOWN = UNKNOWN`. Vì `WHERE` chỉ giữ dòng có kết quả `TRUE`, nên **mọi dòng** đều bị loại một khi danh sách `NOT IN` chứa `NULL`. Đây là bẫy kinh điển — xem mục 2.

---

## 1. `LIKE` / `ILIKE` — khớp mẫu chuỗi

**Định nghĩa:** `LIKE` là toán tử so khớp một chuỗi với một **mẫu** (pattern) có thể chứa ký tự đại diện; nó trả `TRUE` nếu chuỗi khớp mẫu, `FALSE` nếu không, và `NULL` nếu một trong hai vế là `NULL`. `ILIKE` giống hệt `LIKE` nhưng **không phân biệt hoa/thường** (chỉ có ở PostgreSQL, không phải chuẩn SQL).

Hai ký tự đại diện của `LIKE`:

| Ký tự | Ý nghĩa | Khớp bao nhiêu ký tự |
| --- | --- | --- |
| `%` | Bất kỳ chuỗi con nào | 0 hoặc nhiều ký tự |
| `_` | Bất kỳ một ký tự nào | đúng 1 ký tự |

Ví dụ cú pháp tối thiểu:

```sql title="SQL"
CREATE TABLE products (id integer GENERATED ALWAYS AS IDENTITY PRIMARY KEY, name text NOT NULL);
INSERT INTO products (name) VALUES ('Bàn phím cơ'), ('bàn di chuột'), ('Loa Bluetooth');

-- % khớp 0 hoặc nhiều ký tự bất kỳ ở đầu chuỗi
SELECT name FROM products WHERE name LIKE 'Bàn%';
```

Output kỳ vọng:

```text title="Kết quả"
    name
-------------
 Bàn phím cơ
(1 row)
```

Chỉ `Bàn phím cơ` khớp vì `LIKE` (không có `I`) **phân biệt hoa/thường** — `bàn di chuột` viết thường không khớp `Bàn%`. Dùng `ILIKE` để bỏ qua khác biệt hoa/thường:

```sql title="SQL"
SELECT name FROM products WHERE name ILIKE 'bàn%';
```

Output kỳ vọng: cả `Bàn phím cơ` và `bàn di chuột` đều khớp (2 dòng).

Điều gì xảy ra khi dùng SAI: `LIKE` chỉ so khớp được giữa hai giá trị kiểu chuỗi — dùng nó trên một cột **không phải kiểu chuỗi** (ví dụ cột `integer`) mà không ép kiểu, PostgreSQL báo lỗi cụ thể:

```text title="Lỗi PostgreSQL"
ERROR:  operator does not exist: integer ~~ unknown
LINE 1: SELECT id FROM products WHERE id LIKE '1%';
HINT:  No operator matches the given name and argument types. You might need to add explicit type casts.
```

Phải ép kiểu tường minh, ví dụ `id::text LIKE '1%'`, nếu thật sự cần so khớp mẫu chuỗi trên một cột số.

### Ký tự `_` khớp đúng một ký tự

Định nghĩa: `_` trong mẫu `LIKE` chiếm chỗ cho **chính xác một** ký tự bất kỳ (khác `%` là 0-hoặc-nhiều).

```sql title="SQL"
-- Tìm mã sản phẩm dạng "A" + đúng 1 chữ số, ví dụ A1, A2 nhưng không phải A10
SELECT * FROM (VALUES ('A1'), ('A2'), ('A10')) AS t(code)
WHERE code LIKE 'A_';
```

Output kỳ vọng: chỉ `A1` và `A2` khớp — `A10` có 2 ký tự sau `A` nên không khớp `A_` (đúng 1 ký tự).

Nếu dùng sai — quên rằng `_` là đại diện và muốn tìm dấu gạch dưới **thật sự** trong chuỗi (ví dụ cột `user_name` chứa giá trị `an_binh`) mà không escape, `_` sẽ vô tình khớp bất kỳ ký tự nào ở vị trí đó, không báo lỗi cú pháp nhưng cho **kết quả sai** (khớp thừa những chuỗi không có dấu gạch dưới thật). Cách xử lý đúng: escape bằng `ESCAPE`, ví dụ `LIKE 'an\_binh' ESCAPE '\'`.

---

## 2. `IN` / `NOT IN` — và bẫy `NULL`

**Định nghĩa:** `IN (danh_sách)` là cách viết gọn cho nhiều điều kiện `=` nối bằng `OR`; nó trả `TRUE` nếu giá trị bên trái bằng **ít nhất một** phần tử trong danh sách.

Ví dụ cú pháp tối thiểu (chỉ minh hoạ `IN`, không trộn `NOT IN`):

```sql title="SQL"
CREATE TABLE orders (id integer GENERATED ALWAYS AS IDENTITY PRIMARY KEY, status text);
INSERT INTO orders (status) VALUES ('paid'), ('pending'), ('cancelled');

SELECT * FROM orders WHERE status IN ('paid', 'pending');
```

Output kỳ vọng: 2 dòng (`paid`, `pending`); `cancelled` bị loại.

`IN` tương đương `status = 'paid' OR status = 'pending'` — nếu viết sai kiểu, ví dụ so sánh cột `text` với danh sách toàn số nguyên không ép kiểu được, PostgreSQL báo lỗi cụ thể:

```text title="Lỗi PostgreSQL"
ERROR:  invalid input syntax for type integer: "paid"
```

(xảy ra khi cột thực chất là `integer` nhưng bạn truyền chuỗi trong danh sách `IN`).

### `NOT IN` — bẫy `NULL` trả rỗng

Định nghĩa: `NOT IN (danh_sách)` là phủ định của `IN`, tương đương nối nhiều điều kiện `<>` bằng `AND`. Đây chính là nguồn gốc của bẫy đã thấy ở mục 0.

Ví dụ cú pháp tối thiểu (độc lập, không trộn với `IN` phía trên):

```sql title="SQL"
CREATE TABLE bad_status (status text);
INSERT INTO bad_status VALUES ('cancelled'), (NULL);   -- có 1 NULL trong danh sách loại trừ

SELECT * FROM orders WHERE status NOT IN (SELECT status FROM bad_status);
```

Output kỳ vọng: **0 dòng** — kể cả `paid` và `pending` cũng bị loại, dù chúng rõ ràng không phải `cancelled`.

Vì sao: `NOT IN (v1, v2, ...)` giãn ra thành `x <> v1 AND x <> v2 AND ...`. Khi một `vi` là `NULL`, `x <> NULL` luôn là `UNKNOWN`, và `UNKNOWN` lan trong `AND` khiến **toàn bộ biểu thức** thành `UNKNOWN` bất kể các điều kiện khác là gì — hàng đó bị `WHERE` loại. Nếu danh sách bên trong `NOT IN` có nguy cơ chứa `NULL` (đặc biệt khi lấy từ subquery), **không** dùng `NOT IN` — dùng `NOT EXISTS` thay thế, vì `NOT EXISTS` không bị ảnh hưởng bởi `NULL` trong bảng con:

```sql title="SQL"
SELECT * FROM orders o
WHERE NOT EXISTS (
    SELECT 1 FROM bad_status b WHERE b.status = o.status
);
```

Output kỳ vọng: 2 dòng (`paid`, `pending`) — đúng như kỳ vọng ban đầu, `NOT EXISTS` không bị NULL "đầu độc".

!!! danger "Quy tắc nhớ"
    Chỉ dùng `NOT IN (danh_sách)` khi bạn **chắc chắn 100%** danh sách không có `NULL` (ví dụ danh sách hằng số tay). Với danh sách lấy từ subquery hoặc cột nullable, luôn dùng `NOT EXISTS` để an toàn.

---

## 3. `BETWEEN` — khoảng đóng hai đầu

**Định nghĩa:** `BETWEEN a AND b` kiểm tra một giá trị có nằm trong khoảng từ `a` đến `b` hay không, **bao gồm cả hai đầu mút** (khoảng đóng), tương đương `x >= a AND x <= b`.

Ví dụ cú pháp tối thiểu:

```sql title="SQL"
CREATE TABLE items (id integer GENERATED ALWAYS AS IDENTITY PRIMARY KEY, price numeric(10,2));
INSERT INTO items (price) VALUES (100), (200), (300), (400);

SELECT * FROM items WHERE price BETWEEN 200 AND 300;
```

Output kỳ vọng: 2 dòng (`200`, `300`) — cả hai đầu mút **đều được tính**, khác với nhiều ngôn ngữ lập trình coi khoảng là nửa-mở.

Điều gì xảy ra khi dùng SAI thứ tự (viết `BETWEEN 300 AND 200`, đầu lớn trước đầu nhỏ): PostgreSQL **không báo lỗi cú pháp**, nhưng biểu thức giãn thành `price >= 300 AND price <= 200` — không giá trị nào thoả cả hai, nên luôn trả **0 dòng**, một lỗi logic âm thầm chứ không phải lỗi cú pháp:

```sql title="SQL"
SELECT * FROM items WHERE price BETWEEN 300 AND 200;  -- luôn 0 dòng, không báo lỗi
```

---

## 4. `CASE WHEN` — biểu thức rẽ nhánh

**Định nghĩa:** `CASE WHEN ... THEN ... ELSE ... END` là một **biểu thức** (không phải câu lệnh) trả về một giá trị tuỳ theo điều kiện nào đúng trước tiên — dùng được ở bất cứ đâu một biểu thức được phép, ví dụ trong `SELECT`, `WHERE`, `ORDER BY`.

Ví dụ cú pháp tối thiểu:

```sql title="SQL"
CREATE TABLE students (id integer GENERATED ALWAYS AS IDENTITY PRIMARY KEY, score integer);
INSERT INTO students (score) VALUES (95), (72), (40);

SELECT score,
       CASE
           WHEN score >= 90 THEN 'Giỏi'
           WHEN score >= 60 THEN 'Trung bình'
           ELSE 'Yếu'
       END AS xep_loai
FROM students
ORDER BY score DESC;
```

Output kỳ vọng:

```text title="Kết quả"
 score | xep_loai
-------+------------
    95 | Giỏi
    72 | Trung bình
    40 | Yếu
(3 rows)
```

`CASE` xét các `WHEN` **theo thứ tự viết** và dừng ở điều kiện đúng đầu tiên — nếu không có `WHEN` nào đúng và không có `ELSE`, kết quả là `NULL` (không lỗi). Điều gì xảy ra khi dùng SAI — quên từ khoá `END`:

```text title="Lỗi PostgreSQL"
ERROR:  syntax error at end of input
```

PostgreSQL cần `END` để biết biểu thức `CASE` kết thúc ở đâu; thiếu nó gây lỗi cú pháp ngay khi parse.

---

## 5. `COALESCE` — lấy giá trị không-NULL đầu tiên

**Định nghĩa:** `COALESCE(v1, v2, ..., vn)` trả về giá trị **đầu tiên khác `NULL`** trong danh sách đối số, xét từ trái sang phải; nếu tất cả đều `NULL`, kết quả là `NULL`.

Ví dụ cú pháp tối thiểu:

```sql title="SQL"
CREATE TABLE profiles (id integer GENERATED ALWAYS AS IDENTITY PRIMARY KEY, nickname text, full_name text);
INSERT INTO profiles (nickname, full_name) VALUES (NULL, 'Nguyễn Văn An'), ('Bin', 'Trần Văn Bình');

SELECT COALESCE(nickname, full_name, 'Ẩn danh') AS ten_hien_thi
FROM profiles;
```

Output kỳ vọng:

```text title="Kết quả"
 ten_hien_thi
----------------
 Nguyễn Văn An
 Bin
(2 rows)
```

Dòng đầu `nickname` là `NULL` nên `COALESCE` "rơi" xuống `full_name`; dòng hai có `nickname` nên dùng luôn giá trị đó.

Điều gì xảy ra khi dùng SAI kiểu dữ liệu giữa các đối số (ví dụ trộn `text` và `integer` không ép kiểu ngầm được):

```text title="Lỗi PostgreSQL"
ERROR:  COALESCE types text and integer cannot be matched
```

Các đối số của `COALESCE` phải cùng kiểu hoặc ép kiểu ngầm được với nhau.

---

## 6. `NULLIF` — biến một giá trị cụ thể thành `NULL`

**Định nghĩa:** `NULLIF(a, b)` trả về `NULL` nếu `a` bằng `b`, ngược lại trả về chính `a`. Nó là chiều **ngược** của `COALESCE`: thay vì thay `NULL` bằng giá trị khác, nó thay một giá trị cụ thể thành `NULL`.

Ví dụ cú pháp tối thiểu — trường hợp kinh điển: tránh chia cho 0.

```sql title="SQL"
CREATE TABLE stats (total integer, count_ integer);
INSERT INTO stats VALUES (100, 5), (50, 0);

SELECT total, count_, total / NULLIF(count_, 0) AS trung_binh
FROM stats;
```

Output kỳ vọng:

```text title="Kết quả"
 total | count_ | trung_binh
-------+--------+------------
   100 |      5 |         20
    50 |      0 |       (null)
(2 rows)
```

Khi `count_ = 0`, `NULLIF(count_, 0)` trả `NULL`, và bất kỳ phép chia nào cho `NULL` cho kết quả `NULL` — **không** ném lỗi runtime, khác hẳn với chia trực tiếp cho `0`.

Điều gì xảy ra khi dùng SAI — chia trực tiếp cho `count_` mà không bọc `NULLIF` khi `count_` có thể là `0`:

```sql title="SQL"
SELECT total / count_ FROM stats WHERE count_ = 0;
```

```text title="Lỗi PostgreSQL runtime"
ERROR:  division by zero
```

Đây là lỗi **runtime** (xảy ra khi thực thi, không phải khi parse), vì PostgreSQL không thể biết trước giá trị `count_` lúc phân tích cú pháp.

---

## 7. `DISTINCT` — loại bỏ dòng trùng lặp

**Định nghĩa:** `DISTINCT` trong `SELECT` loại bỏ các dòng kết quả **trùng lặp hoàn toàn** trên tất cả các cột được chọn, chỉ giữ lại một bản mỗi tổ hợp giá trị.

Ví dụ cú pháp tối thiểu:

```sql title="SQL"
CREATE TABLE visits (city text);
INSERT INTO visits VALUES ('Hà Nội'), ('Hồ Chí Minh'), ('Hà Nội'), ('Đà Nẵng'), ('Hà Nội');

SELECT DISTINCT city FROM visits ORDER BY city;
```

Output kỳ vọng:

```text title="Kết quả"
    city
-------------
 Đà Nẵng
 Hà Nội
 Hồ Chí Minh
(3 rows)
```

`Hà Nội` xuất hiện 3 lần trong bảng gốc nhưng chỉ 1 lần trong kết quả `DISTINCT`.

Cạm bẫy đặt vị trí sai: `DISTINCT` phải đứng **ngay sau `SELECT`**, áp dụng cho toàn bộ danh sách cột — viết `SELECT city, DISTINCT country FROM visits` (đặt `DISTINCT` giữa danh sách cột) là sai cú pháp:

```text title="Lỗi PostgreSQL"
ERROR:  syntax error at or near "DISTINCT"
```

`DISTINCT` không áp dụng cho từng cột riêng lẻ — nếu chọn nhiều cột, nó xét tổ hợp **cả bộ** cột đó có trùng nhau không, chứ không loại trùng theo từng cột độc lập.

---

## 8. Hàm chuỗi cơ bản

**Định nghĩa chung:** đây là các hàm/toán tử thao tác trên giá trị kiểu `text`, dùng để nối, đổi hoa/thường, cắt chuỗi con, và đo độ dài.

### Nối chuỗi bằng `||`

Định nghĩa: `||` là toán tử nối hai chuỗi thành một.

```sql title="SQL"
SELECT 'Xin' || ' ' || 'chào' AS loi_chao;
```

Output kỳ vọng: `Xin chào` (1 dòng).

Điều gì xảy ra khi dùng SAI — nối chuỗi với `NULL`:

```sql title="SQL"
SELECT 'Xin chào ' || NULL AS ket_qua;
```

Output kỳ vọng: `ket_qua` là `NULL` (không lỗi) — bất kỳ chuỗi nào nối với `NULL` bằng `||` cho kết quả `NULL`. Muốn tránh, bọc `COALESCE(cot, '')` trước khi nối.

### `lower` / `upper` — đổi hoa/thường

Định nghĩa: `lower(s)` trả về chuỗi `s` viết thường toàn bộ; `upper(s)` trả về chuỗi viết hoa toàn bộ.

```sql title="SQL"
SELECT lower('Xin CHÀO') AS thuong, upper('Xin CHÀO') AS hoa;
```

Output kỳ vọng: `thuong = 'xin chào'`, `hoa = 'XIN CHÀO'`.

### `substring` — cắt chuỗi con

Định nghĩa: `substring(s FROM vi_tri FOR do_dai)` trả về đoạn chuỗi con của `s`, bắt đầu từ `vi_tri` (đếm từ 1), dài `do_dai` ký tự.

```sql title="SQL"
SELECT substring('PostgreSQL' FROM 1 FOR 4) AS ket_qua;
```

Output kỳ vọng: `Post` (4 ký tự đầu).

Điều gì xảy ra khi dùng SAI — vị trí bắt đầu là `0` hoặc âm: PostgreSQL **không báo lỗi**, nó tự động giới hạn về đầu chuỗi và trừ phần độ dài tương ứng ở đầu ra, dễ gây kết quả bất ngờ hơn là lỗi:

```sql title="SQL"
SELECT substring('PostgreSQL' FROM 0 FOR 4) AS ket_qua;
```

Output kỳ vọng: `Pos` (chỉ 3 ký tự, không phải 4) — vì PostgreSQL coi vị trí `0` là "trước ký tự đầu tiên 1 bước", nên `FOR 4` tính từ đó chỉ còn phủ 3 ký tự thật sự tồn tại. Đây là lý do nên luôn kiểm tra thủ công khi vị trí có thể là 0 hoặc âm (ví dụ tính từ `position()`).

### `length` — đếm ký tự

Định nghĩa: `length(s)` trả về số **ký tự** (không phải byte) trong chuỗi `s`.

```sql title="SQL"
SELECT length('Xin chào') AS so_ky_tu;
```

Output kỳ vọng: `8` (đếm cả dấu cách, tính ký tự Unicode chứ không phải byte — `chào` gồm các ký tự có dấu vẫn được đếm là 1 ký tự/chữ).

Điều gì xảy ra khi dùng SAI — gọi `length()` không đối số:

```text title="Lỗi PostgreSQL"
ERROR:  function length() does not exist
HINT:  No function matches the given name and argument types. You might need to add explicit type casts.
```

`length` bắt buộc đúng 1 đối số kiểu chuỗi (hoặc kiểu nhị phân với cú pháp khác); gọi thiếu đối số không khớp bất kỳ overload nào.

---

## 9. Toán tử regex `~` (giới thiệu ngắn)

**Định nghĩa:** `~` là toán tử kiểm tra một chuỗi có khớp một **biểu thức chính quy (regular expression)** hay không, trả `TRUE`/`FALSE`/`NULL` — mạnh hơn `LIKE` vì regex hỗ trợ các mẫu phức tạp (lặp, nhóm, lớp ký tự) mà `LIKE` không có.

Ví dụ cú pháp tối thiểu:

```sql title="SQL"
-- Tìm chuỗi có chứa ít nhất 1 chữ số
SELECT * FROM (VALUES ('abc'), ('abc123'), ('xyz')) AS t(code)
WHERE code ~ '[0-9]+';
```

Output kỳ vọng: chỉ `abc123` khớp (1 dòng) — vì nó là chuỗi duy nhất chứa ký tự số.

Biến thể thường gặp: `~*` (khớp không phân biệt hoa/thường, giống quan hệ giữa `LIKE` và `ILIKE`), `!~` (KHÔNG khớp), `!~*` (KHÔNG khớp, không phân biệt hoa/thường).

### Bốn ký hiệu regex hay dùng: `^`, `$`, `{n}`, và escape `\`

Định nghĩa từng ký hiệu:

| Ký hiệu | Ý nghĩa |
| --- | --- |
| `^` | Neo vào **đầu** chuỗi — mẫu phải khớp bắt đầu từ đó |
| `$` | Neo vào **cuối** chuỗi — mẫu phải khớp kết thúc tại đó |
| `{n}` | Ký tự/nhóm đứng trước phải lặp lại **đúng `n` lần** |
| `\` | Escape — biến một ký tự đặc biệt của regex (như `.`) thành ký tự **thường**, khớp đúng chính nó |

Ví dụ: `^SKU-[0-9]{4}$` nghĩa là "từ đầu chuỗi (`^`) là `SKU-`, theo sau đúng 4 ký tự số (`[0-9]{4}`), rồi hết chuỗi (`$`)" — không neo `^`/`$` thì regex chỉ cần khớp một đoạn con bất kỳ trong chuỗi, có thể lẫn cả chuỗi dài hơn dự kiến.

```sql title="SQL"
SELECT * FROM (VALUES ('SKU-1234'), ('SKU-12345'), ('XSKU-1234')) AS t(code)
WHERE code ~ '^SKU-[0-9]{4}$';
```

Output kỳ vọng: chỉ `SKU-1234` khớp (1 dòng) — `SKU-12345` có 5 chữ số (thừa so với `{4}`, và `$` chặn không cho dư ký tự) nên không khớp; `XSKU-1234` không bắt đầu đúng bằng `SKU-` (bị `^` chặn) nên cũng không khớp.

Dấu `.` trong regex mặc định khớp **bất kỳ ký tự nào**, không phải dấu chấm theo nghĩa đen — muốn khớp dấu chấm thật sự (ví dụ trong domain `congty.vn`), phải escape thành `\.`:

```sql title="SQL"
SELECT * FROM (VALUES ('a@congty.vn'), ('a@congtyXvn')) AS t(email)
WHERE email ~ '@congty\.vn$';
```

Output kỳ vọng: chỉ `a@congty.vn` khớp (1 dòng) — nếu quên escape (`@congty.vn$` không có `\`), `.` sẽ khớp cả ký tự `X` nên `a@congtyXvn` cũng khớp nhầm.

Điều gì xảy ra khi dùng SAI — biểu thức regex không hợp lệ (ví dụ ngoặc vuông không đóng):

```text title="Lỗi PostgreSQL"
ERROR:  invalid regular expression: brackets [] not balanced
```

PostgreSQL kiểm tra cú pháp regex tại thời điểm thực thi và báo lỗi cụ thể nếu mẫu sai định dạng.

!!! info "Khi nào dùng `~` thay vì `LIKE`"
    Dùng `LIKE`/`ILIKE` cho các trường hợp đơn giản (bắt đầu bằng, kết thúc bằng, chứa một chuỗi con cố định) — nó dễ đọc và PostgreSQL có thể dùng index (`text_pattern_ops`) hiệu quả hơn cho một số dạng. Dùng `~` khi cần mẫu phức tạp mà `%`/`_` không diễn tả được, ví dụ "chuỗi gồm đúng 3 chữ số theo sau bởi 2 chữ cái".

---

## 10. Kết hợp nhiều khái niệm (chỉ sau khi đã hiểu từng cái riêng)

Bây giờ các khái niệm ở trên đã được giới thiệu độc lập, đây là ví dụ thực chiến kết hợp chúng để giải một bài toán báo cáo thật.

```sql title="SQL"
CREATE TABLE employees (
    id          integer GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    full_name   text NOT NULL,
    email       text,
    department  text,
    salary      numeric(10,2)
);

INSERT INTO employees (full_name, email, department, salary) VALUES
    ('Nguyễn Văn An',  'an.nguyen@congty.vn',  'Sales', 15000000),
    ('Trần Thị Bình',  NULL,                    'Sales', 22000000),
    ('Lê Văn Cường',   'cuong@congty.vn',       'IT',    NULL),
    ('Phạm Thị Dung',  'dung99@congty.vn',      NULL,    18000000);

SELECT
    upper(full_name)                                  AS ten_in_hoa,
    COALESCE(email, '(chưa có email)')                AS email_hien_thi,
    COALESCE(department, 'Chưa phân bổ')               AS phong_ban,
    CASE
        WHEN salary IS NULL           THEN 'Chưa có lương'
        WHEN salary BETWEEN 0 AND 16000000 THEN 'Bậc 1'
        WHEN salary BETWEEN 16000001 AND 20000000 THEN 'Bậc 2'
        ELSE 'Bậc 3'
    END                                                AS bac_luong
FROM employees
WHERE department IN ('Sales', 'IT')
  AND (email ~ '@congty\.vn$' OR email IS NULL)
ORDER BY full_name;
```

Output kỳ vọng:

```text title="Kết quả"
   ten_in_hoa     |     email_hien_thi      | phong_ban |   bac_luong
-------------------+-------------------------+-----------+---------------
 LÊ VĂN CƯỜNG      | cuong@congty.vn         | IT        | Chưa có lương
 NGUYỄN VĂN AN     | an.nguyen@congty.vn     | Sales     | Bậc 1
 TRẦN THỊ BÌNH     | (chưa có email)         | Sales     | Bậc 3
(3 rows)
```

`Phạm Thị Dung` bị loại vì `department` là `NULL`, không nằm trong `IN ('Sales', 'IT')` (nhớ: `NULL` không khớp bất kỳ giá trị nào kể cả trong `IN`). `Trần Thị Bình` có `salary = 22000000` — lớn hơn cả hai ngưỡng `BETWEEN` nên rơi vào `ELSE` (`Bậc 3`). Ví dụ này trộn `CASE WHEN` + `BETWEEN` + `COALESCE` + `~` + `IN` + `upper` — chỉ hợp lý xem SAU KHI đã hiểu từng khái niệm riêng lẻ ở các mục trên.

---

## Cạm bẫy & thực chiến

- **`NOT IN` với danh sách có thể chứa `NULL`**: luôn trả tập rỗng bất ngờ. Luôn thay bằng `NOT EXISTS` khi danh sách đến từ subquery hoặc cột nullable (xem mục 2).
- **`LIKE` phân biệt hoa/thường, quên dùng `ILIKE`**: một lỗi rất phổ biến khi lọc theo tên người dùng nhập tự do — luôn cân nhắc `ILIKE` hoặc chuẩn hoá bằng `lower()` cả hai vế nếu cần so khớp không phân biệt hoa/thường trên cột không có index phù hợp.
- **`BETWEEN` với thứ tự đầu-cuối sai** không báo lỗi, chỉ âm thầm trả 0 dòng — luôn đảm bảo `BETWEEN nhỏ AND lớn`.
- **Nối chuỗi `||` với cột có thể `NULL`** làm cả biểu thức thành `NULL` — bọc `COALESCE(cot, '')` trước khi nối nếu cột có thể `NULL` nhưng bạn muốn giữ phần còn lại của chuỗi.
- **Chia có mẫu số có thể bằng 0**: dùng `NULLIF(mau_so, 0)` để biến `0` thành `NULL` trước khi chia, tránh lỗi runtime `division by zero`.
- **`DISTINCT` không lọc trùng theo từng cột riêng** khi `SELECT` nhiều cột — nó xét trùng trên toàn bộ tổ hợp cột. Muốn đếm/lọc trùng chỉ theo một cột trong khi vẫn hiển thị các cột khác, cần cách tiếp cận khác (ví dụ `DISTINCT ON` — xem DEEP DIVE).
- **`%` và `_` trong `LIKE` là ký tự đặc biệt** — nếu dữ liệu thực sự chứa dấu `%` hoặc `_` (ví dụ mã giảm giá `"50%_OFF"`), phải escape bằng `ESCAPE` hoặc dùng `position()`/`~` với ký tự đã escape.

---

## Bài tập

**Bài 1 (giàn giáo).** Cho lại bảng `employees` ở mục 10. Viết truy vấn lấy `full_name` và một cột `trang_thai_email`: nếu `email` là `NULL` thì hiển thị `'Thiếu email'`, ngược lại hiển thị chính email đó viết thường toàn bộ.

```sql title="SQL"
SELECT full_name,
       CASE
           WHEN ____ THEN ____
           ELSE ____
       END AS trang_thai_email
FROM employees;
```

??? success "Lời giải — Bài 1"
    ```sql title="SQL"
    SELECT full_name,
           CASE
               WHEN email IS NULL THEN 'Thiếu email'
               ELSE lower(email)
           END AS trang_thai_email
    FROM employees;
    ```
    **Vì sao:** phải dùng `email IS NULL`, không phải `email = NULL` (so sánh `= NULL` luôn cho `UNKNOWN`, không bao giờ đúng — xem lại chương SQL nền tảng). `lower(email)` chỉ chạy ở nhánh `ELSE`, nơi `email` chắc chắn không `NULL`.

**Bài 2 (thiết kế).** Bảng `products(id, sku, price, discontinued_reason)` — `discontinued_reason` là `NULL` với sản phẩm còn bán, có giá trị text (ví dụ `'hết hàng'`, `'lỗi thời'`) với sản phẩm ngừng bán. Yêu cầu: viết một truy vấn lấy `sku`, `price`, và cột `nhan` — hiển thị `'NGỪNG BÁN: <lý do in hoa>'` nếu sản phẩm ngừng bán, hoặc `'ĐANG BÁN'` nếu không. Chỉ lấy các sản phẩm có `sku` bắt đầu bằng `'SKU-'` theo sau bởi đúng 4 chữ số.

??? success "Lời giải — Bài 2"
    ```sql title="SQL"
    SELECT sku, price,
           CASE
               WHEN discontinued_reason IS NOT NULL
                   THEN 'NGỪNG BÁN: ' || upper(discontinued_reason)
               ELSE 'ĐANG BÁN'
           END AS nhan
    FROM products
    WHERE sku ~ '^SKU-[0-9]{4}$';
    ```
    **Vì sao dùng `~` thay vì `LIKE`:** `LIKE` không diễn tả được "đúng 4 chữ số" — `LIKE 'SKU-____'` (4 dấu gạch dưới) sẽ khớp cả khi các ký tự đó là chữ cái, không riêng chữ số. Regex `^SKU-[0-9]{4}$` khẳng định chính xác: đầu chuỗi (`^`) là `SKU-`, theo sau đúng 4 ký tự trong lớp `[0-9]`, rồi kết thúc chuỗi (`$`). Nối chuỗi `||` an toàn ở đây vì `discontinued_reason` đã được đảm bảo không `NULL` trong nhánh `WHEN`.

---

## Tự kiểm tra

1. `SELECT * FROM t WHERE col NOT IN (1, 2, NULL);` trả về bao nhiêu dòng bất kể `col` là gì?

    ??? note "Đáp án"
        **0 dòng.** `NOT IN` giãn thành `col<>1 AND col<>2 AND col<>NULL`; vế cuối luôn `UNKNOWN`, và `UNKNOWN` lan trong `AND` khiến toàn bộ biểu thức không bao giờ là `TRUE`.

2. Khác biệt giữa `LIKE` và `ILIKE` là gì?

    ??? note "Đáp án"
        `LIKE` phân biệt hoa/thường; `ILIKE` (chỉ có ở PostgreSQL) không phân biệt hoa/thường. Cả hai đều dùng `%` (0+ ký tự) và `_` (đúng 1 ký tự) làm đại diện.

3. `SELECT price BETWEEN 300 AND 200;` có báo lỗi cú pháp không? Kết quả là gì?

    ??? note "Đáp án"
        Không báo lỗi cú pháp. `BETWEEN a AND b` luôn giãn thành `x >= a AND x <= b`; với `a=300, b=200` không giá trị nào thoả cả hai điều kiện, nên kết quả luôn là `FALSE` (0 dòng khi dùng trong `WHERE`) — một lỗi logic âm thầm.

4. `COALESCE` và `NULLIF` khác nhau ở điểm nào?

    ??? note "Đáp án"
        `COALESCE(v1, ..., vn)` trả giá trị khác `NULL` đầu tiên (dùng để **thay `NULL`** bằng giá trị khác). `NULLIF(a, b)` trả `NULL` nếu `a = b`, ngược lại trả `a` (dùng để **biến một giá trị cụ thể thành `NULL`**, ví dụ tránh chia cho 0).

5. Vì sao `SELECT total / count_ FROM stats;` có thể ném lỗi runtime, và cách phòng tránh?

    ??? note "Đáp án"
        Nếu `count_` bằng `0`, phép chia ném lỗi `division by zero` lúc thực thi. Phòng tránh bằng `total / NULLIF(count_, 0)` — khi `count_ = 0`, `NULLIF` trả `NULL`, và chia cho `NULL` cho kết quả `NULL` thay vì lỗi.

6. `SELECT DISTINCT city, country FROM visits;` loại trùng theo cột nào?

    ??? note "Đáp án"
        Theo **tổ hợp cả hai cột** `(city, country)` — hai dòng chỉ bị coi là trùng và gộp lại khi cả `city` VÀ `country` giống hệt nhau, không lọc trùng riêng từng cột.

7. Toán tử `~` khác `LIKE` ở điểm cốt lõi nào, và khi nào nên chọn `~`?

    ??? note "Đáp án"
        `~` khớp theo biểu thức chính quy (regex) — mạnh hơn nhiều so với hai ký tự đại diện `%`/`_` của `LIKE` (hỗ trợ lớp ký tự, số lần lặp, neo đầu/cuối chuỗi...). Nên chọn `~` khi mẫu cần diễn tả phức tạp hơn "chứa chuỗi con cố định", ví dụ ràng buộc định dạng chính xác như "đúng N chữ số".

---

??? abstract "DEEP DIVE — nâng cao (không nằm trên fast path)"
    **`DISTINCT ON`.** PostgreSQL có mở rộng riêng `DISTINCT ON (cot)` để lấy **một dòng đại diện** cho mỗi giá trị của `cot`, thường kết hợp `ORDER BY` để chọn dòng nào được giữ:

    ```sql title="SQL"
    -- Mỗi department lấy 1 nhân viên lương cao nhất
    SELECT DISTINCT ON (department) department, full_name, salary
    FROM employees
    WHERE department IS NOT NULL
    ORDER BY department, salary DESC;
    ```

    Đây KHÔNG phải chuẩn SQL (chỉ PostgreSQL có) — không nên dùng nếu cần chuyển hệ quản trị khác trong tương lai.

    **`SIMILAR TO`.** Nằm giữa `LIKE` và regex đầy đủ: hỗ trợ một số cú pháp regex (`|`, `+`, `*`) trộn với `%`/`_` của `LIKE`. Ít dùng trong thực tế vì cú pháp lai gây khó nhớ — ưu tiên `LIKE` cho đơn giản, `~` cho phức tạp, tránh `SIMILAR TO`.

    **Index cho `LIKE`/`ILIKE`.** `LIKE 'abc%'` (tiền tố cố định) có thể dùng index B-tree bình thường trên cột đó (với locale `C` hoặc toán tử lớp `text_pattern_ops`). Nhưng `LIKE '%abc%'` (có `%` ở đầu) **không** dùng được index B-tree — PostgreSQL phải quét toàn bảng. Với tìm kiếm chuỗi con lớn, cân nhắc extension `pg_trgm` (trigram index) thay vì `LIKE '%...%'` trần.

    **Regex và hiệu năng.** Toán tử `~` cũng không tận dụng được index B-tree thông thường trừ khi kết hợp `pg_trgm`. Với bảng lớn, lọc trước bằng điều kiện có thể dùng index (ví dụ khoảng ngày, khoá ngoại) rồi mới áp `~`/`LIKE '%...%'` trên tập đã thu nhỏ.

    **`COALESCE` và `ORDER BY` với NULL.** Mặc định PostgreSQL xếp `NULL` **cuối** khi `ORDER BY ... ASC` và **đầu** khi `DESC`. Muốn kiểm soát rõ ràng, dùng `ORDER BY col ASC NULLS FIRST` hoặc `NULLS LAST` thay vì bọc `COALESCE` chỉ để đổi thứ tự sắp xếp (COALESCE làm thay đổi giá trị hiển thị, còn `NULLS FIRST/LAST` chỉ đổi vị trí sắp xếp mà giữ nguyên giá trị gốc).

**Tiếp theo →** [P2 · Ràng buộc dữ liệu (Constraints)](constraints.md)
