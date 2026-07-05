---
title: "Ôn tập — Quiz tự chấm"
---

# Ôn tập: Quiz tự chấm

Chọn một chương, hệ thống lấy ngẫu nhiên vài câu hỏi từ đúng bộ Q&A của chương đó (cùng nguồn `data/questions.yml` đang bảo vệ bởi gate `qa_lint.py`) — không có gì được viết thêm ở đây, chỉ đọc lại dữ liệu đã có. Đoán trước, rồi bấm để xem đáp án.

<div id="quiz-app" markdown="0">
  <div class="quiz-controls">
    <label for="quiz-node">Chương:</label>
    <select id="quiz-node"></select>
    <label for="quiz-count">Số câu:</label>
    <select id="quiz-count">
      <option value="5">5</option>
      <option value="10" selected>10</option>
      <option value="20">20</option>
    </select>
    <button id="quiz-start" type="button">Bắt đầu / Đổi câu khác</button>
  </div>
  <div id="quiz-cards"></div>
</div>

<script>
(function () {
  "use strict";
  var data = null;

  function assetUrl(path) {
    // Đường dẫn TƯƠNG ĐỐI, không phải tuyệt đối — tự đúng bất kể site host ở
    // domain gốc hay dưới 1 tiền tố (GitHub Pages /learning-hub-v2/, mkdocs
    // serve, domain riêng...). on-tap.md nằm ở docs/ (root), URL dạng
    // .../on-tap/ (use_directory_urls) nên lùi 1 cấp tới root rồi vào assets/.
    return "../" + path;
  }

  function loadData() {
    return fetch(assetUrl('assets/quiz-data.json')).then(function (r) {
      if (!r.ok) throw new Error('Không tải được quiz-data.json (' + r.status + ')');
      return r.json();
    });
  }

  function shuffle(arr) {
    var a = arr.slice();
    for (var i = a.length - 1; i > 0; i--) {
      var j = Math.floor(Math.random() * (i + 1));
      var tmp = a[i]; a[i] = a[j]; a[j] = tmp;
    }
    return a;
  }

  function populateSelect(select, nodes) {
    select.innerHTML = "";
    nodes.sort().forEach(function (node) {
      var opt = document.createElement("option");
      opt.value = node;
      opt.textContent = node.replace(/-/g, " ");
      select.appendChild(opt);
    });
  }

  function renderQuiz(questions) {
    var container = document.getElementById("quiz-cards");
    container.innerHTML = "";
    if (questions.length === 0) {
      container.innerHTML = "<p><em>Chương này chưa có câu hỏi.</em></p>";
      return;
    }
    questions.forEach(function (q, idx) {
      var card = document.createElement("div");
      card.className = "quiz-card";

      var promptEl = document.createElement("p");
      promptEl.className = "quiz-prompt";
      promptEl.textContent = (idx + 1) + ". " + q.prompt;
      card.appendChild(promptEl);

      var btn = document.createElement("button");
      btn.type = "button";
      btn.className = "quiz-reveal-btn";
      btn.textContent = "Hiện đáp án";

      var answerEl = document.createElement("p");
      answerEl.className = "quiz-answer";
      answerEl.textContent = q.answer;
      answerEl.style.display = "none";

      btn.addEventListener("click", function () {
        var showing = answerEl.style.display !== "none";
        answerEl.style.display = showing ? "none" : "block";
        btn.textContent = showing ? "Hiện đáp án" : "Ẩn đáp án";
      });

      card.appendChild(btn);
      card.appendChild(answerEl);
      container.appendChild(card);
    });
  }

  function start() {
    var nodeSelect = document.getElementById("quiz-node");
    var countSelect = document.getElementById("quiz-count");
    var node = nodeSelect.value;
    var count = parseInt(countSelect.value, 10);
    var pool = (data && data[node]) ? data[node] : [];
    var chosen = shuffle(pool).slice(0, count);
    renderQuiz(chosen);
  }

  loadData().then(function (json) {
    data = json;
    var nodeSelect = document.getElementById("quiz-node");
    populateSelect(nodeSelect, Object.keys(data));
    document.getElementById("quiz-start").addEventListener("click", start);
    start();
  }).catch(function (err) {
    document.getElementById("quiz-cards").innerHTML =
      "<p><em>Lỗi tải dữ liệu quiz: " + err.message + "</em></p>";
  });
})();
</script>
