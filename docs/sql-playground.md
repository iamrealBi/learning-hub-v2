---
title: "SQL Playground"
---

# SQL Playground

Chạy SQL thật, ngay trong trình duyệt — không cần cài PostgreSQL, không gửi gì lên server nào.

!!! warning "Đây là SQLite, không phải PostgreSQL"
    Toàn bộ chương P2 dạy PostgreSQL {{ postgres.current }}. Playground này chạy **SQLite** (qua [sql.js](https://sql.js.org), SQLite biên dịch sang WebAssembly) vì SQLite đủ nhỏ để tải trong trình duyệt — không có bản PostgreSQL-trong-WASM nào nhẹ và ổn định tương đương tại thời điểm viết bài này.

    Phần lớn cú pháp `SELECT`/`WHERE`/`ORDER BY`/`JOIN`/`GROUP BY`/`HAVING`/subquery/CTE bạn học ở P2 chạy **giống hệt** ở đây. Một số cú pháp **riêng của PostgreSQL sẽ KHÔNG chạy nguyên văn** trong SQLite, ví dụ `GENERATED ALWAYS AS IDENTITY`, `ILIKE`, hay kiểu `timestamptz` — đây là khác biệt thật giữa hai hệ quản trị CSDL, không phải lỗi của playground. Dùng chỗ này để luyện **tư duy SQL** (đọc/viết truy vấn), không phải để kiểm tra cú pháp PostgreSQL chính xác 100%.

Schema có sẵn dưới đây giống đúng ví dụ `khach_hang`/`don_hang` ở chương [JOIN, GROUP BY & Subquery](p2-du-lieu/joins-aggregation.md) — chạy thử lại các truy vấn bạn đã đọc trong bài để kiểm tra mình hiểu đúng.

<div id="sql-app" markdown="0">
  <div class="sql-playground">
    <label for="sql-input"><strong>Câu lệnh SQL</strong> (có thể nhiều câu, ngăn bằng <code>;</code>):</label>
    <textarea id="sql-input" spellcheck="false">SELECT k.ten, d.so_tien
FROM khach_hang k
INNER JOIN don_hang d ON d.khach_hang_id = k.id;</textarea>
    <div class="sql-playground-toolbar">
      <button id="sql-run" type="button">▶ Chạy (Ctrl/Cmd+Enter)</button>
      <button id="sql-reset" type="button" class="secondary">↺ Reset schema mẫu</button>
    </div>
    <div id="sql-result" class="sql-playground-result">
      <p><em>Đang tải SQLite (WebAssembly)...</em></p>
    </div>
  </div>
</div>

<script src="https://cdnjs.cloudflare.com/ajax/libs/sql.js/1.13.0/sql-wasm.js"></script>
<script>
(function () {
  "use strict";
  var SAMPLE_SQL = [
    "CREATE TABLE khach_hang (",
    "    id INTEGER PRIMARY KEY,",
    "    ten TEXT NOT NULL",
    ");",
    "CREATE TABLE don_hang (",
    "    id INTEGER PRIMARY KEY,",
    "    khach_hang_id INTEGER NOT NULL REFERENCES khach_hang(id),",
    "    so_tien NUMERIC(10,2)",
    ");",
    "INSERT INTO khach_hang (id, ten) VALUES (1,'An'), (2,'Binh'), (3,'Chi');",
    "-- Chi (id=3) KHONG co don hang nao",
    "INSERT INTO don_hang (id, khach_hang_id, so_tien) VALUES (1,1,100.00), (2,2,200.00);"
  ].join("\n");

  var db = null;
  var resultEl = document.getElementById("sql-result");
  var inputEl = document.getElementById("sql-input");

  function resetDb() {
    if (db) db.close();
    db = new window.SQL.Database();
    db.run(SAMPLE_SQL);
  }

  function renderResults(results) {
    resultEl.innerHTML = "";
    if (!results || results.length === 0) {
      resultEl.innerHTML = "<p><em>Chạy xong, không có bảng kết quả để hiển thị (ví dụ: CREATE TABLE, INSERT).</em></p>";
      return;
    }
    results.forEach(function (res) {
      var table = document.createElement("table");
      var thead = document.createElement("thead");
      var headRow = document.createElement("tr");
      res.columns.forEach(function (col) {
        var th = document.createElement("th");
        th.textContent = col;
        headRow.appendChild(th);
      });
      thead.appendChild(headRow);
      table.appendChild(thead);

      var tbody = document.createElement("tbody");
      res.values.forEach(function (row) {
        var tr = document.createElement("tr");
        row.forEach(function (cell) {
          var td = document.createElement("td");
          td.textContent = cell === null ? "NULL" : String(cell);
          tr.appendChild(td);
        });
        tbody.appendChild(tr);
      });
      table.appendChild(tbody);
      resultEl.appendChild(table);
    });
  }

  function runQuery() {
    var sql = inputEl.value;
    try {
      var results = db.exec(sql);
      renderResults(results);
    } catch (err) {
      resultEl.innerHTML = "<p class=\"sql-playground-error\">Lỗi SQLite: " + err.message + "</p>";
    }
  }

  window.initSqlJs({
    locateFile: function (file) {
      return "https://cdnjs.cloudflare.com/ajax/libs/sql.js/1.13.0/" + file;
    }
  }).then(function (SQL) {
    window.SQL = SQL;
    resetDb();
    resultEl.innerHTML = "<p><em>Đã tải xong. Bấm \"Chạy\" để thử truy vấn mẫu.</em></p>";
    document.getElementById("sql-run").addEventListener("click", runQuery);
    document.getElementById("sql-reset").addEventListener("click", function () {
      resetDb();
      resultEl.innerHTML = "<p><em>Đã reset lại schema mẫu (khach_hang, don_hang).</em></p>";
    });
    inputEl.addEventListener("keydown", function (e) {
      if ((e.ctrlKey || e.metaKey) && e.key === "Enter") {
        e.preventDefault();
        runQuery();
      }
    });
  }).catch(function (err) {
    resultEl.innerHTML = "<p class=\"sql-playground-error\">Không tải được SQLite WebAssembly: " + err.message + "</p>";
  });
})();
</script>

## Vài truy vấn để tự luyện

Dán từng câu vào ô trên rồi bấm Chạy — đoán kết quả trước khi bấm, giống cách bạn đã luyện ở mục "Đoán nhanh" của mỗi chương P2.

```sql title="Anti-join: khách chưa có đơn hàng nào"
SELECT k.ten
FROM khach_hang k
LEFT JOIN don_hang d ON d.khach_hang_id = k.id
WHERE d.id IS NULL;
```

```sql title="Tổng tiền theo từng khách (kể cả khách chưa mua)"
SELECT k.ten, COALESCE(SUM(d.so_tien), 0) AS tong_tien
FROM khach_hang k
LEFT JOIN don_hang d ON d.khach_hang_id = k.id
GROUP BY k.ten;
```

```sql title="Thêm dữ liệu rồi truy vấn lại"
INSERT INTO don_hang (id, khach_hang_id, so_tien) VALUES (3, 3, 50.00);
SELECT k.ten, COUNT(d.id) AS so_don
FROM khach_hang k
LEFT JOIN don_hang d ON d.khach_hang_id = k.id
GROUP BY k.ten
HAVING COUNT(d.id) > 0;
```
