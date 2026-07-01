#!/usr/bin/env python3
"""Gate ĐẦY ĐỦ & KHÔNG TRÙNG cho Q&A.

Bản cũ có 35/55 câu hỏi KHÔNG đáp án + answer key rỗng code. Ở đây Q&A là dữ liệu
có schema (data/questions.yml). Gate FAIL nếu:
  - câu hỏi thiếu 'answer' hoặc answer rỗng,
  - trùng 'prompt',
  - thiếu trường bắt buộc (id, prompt, answer).
'code_ref' (nếu có) trỏ tới block đã được CI chạy (test:run) -> đáp án có code chạy được.
"""
from __future__ import annotations
import sys, pathlib
import yaml

ROOT = pathlib.Path(__file__).resolve().parent.parent
REQUIRED = ("id", "prompt", "answer")

def scan(qfile: pathlib.Path) -> list[str]:
    data = yaml.safe_load(qfile.read_text(encoding="utf-8")) or {}
    items = data.get("questions", [])
    violations: list[str] = []
    seen_prompt: dict[str, str] = {}
    seen_id: set[str] = set()
    for idx, q in enumerate(items):
        qid = q.get("id", f"#{idx}")
        for field in REQUIRED:
            if not str(q.get(field, "")).strip():
                violations.append(f"{qid}: thiếu/rỗng trường bắt buộc '{field}'")
        if qid in seen_id:
            violations.append(f"{qid}: trùng id")
        seen_id.add(qid)
        prompt = str(q.get("prompt", "")).strip().lower()
        if prompt and prompt in seen_prompt:
            violations.append(f"{qid}: trùng prompt với {seen_prompt[prompt]}")
        elif prompt:
            seen_prompt[prompt] = qid
    return violations

def main(argv: list[str]) -> int:
    qfile = pathlib.Path(argv[1]) if len(argv) > 1 else ROOT / "data" / "questions.yml"
    if not qfile.exists():
        print(f"❌ qa_lint: không thấy {qfile}")
        return 1
    v = scan(qfile)
    if v:
        print("❌ qa_lint: %d vi phạm" % len(v))
        print("\n".join(v))
        return 1
    n = len((yaml.safe_load(qfile.read_text(encoding="utf-8")) or {}).get("questions", []))
    print(f"✅ qa_lint: {n} câu hỏi đều có đáp án, không trùng")
    return 0

if __name__ == "__main__":
    sys.exit(main(sys.argv))
