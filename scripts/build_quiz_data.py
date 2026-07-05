#!/usr/bin/env python3
"""MkDocs hook: sinh docs/assets/quiz-data.json từ data/questions.yml lúc build.

Chạy tự động qua "hooks:" trong mkdocs.yml (event on_pre_build) — không cần
bước build riêng, không thể quên chạy, và nếu questions.yml hỏng thì
mkdocs build (đã --strict trong CI) sẽ fail ngay tại đây.
"""
from __future__ import annotations
import json
import pathlib
import yaml

ROOT = pathlib.Path(__file__).resolve().parent.parent
QUESTIONS = ROOT / "data" / "questions.yml"
OUT = ROOT / "docs" / "assets" / "quiz-data.json"


def build() -> dict:
    data = yaml.safe_load(QUESTIONS.read_text(encoding="utf-8")) or {}
    by_node: dict[str, list[dict]] = {}
    for q in data.get("questions", []):
        node = q["node"]
        by_node.setdefault(node, []).append({
            "id": q["id"],
            "prompt": q["prompt"],
            "answer": q["answer"],
        })
    return by_node


def on_pre_build(config, **kwargs):  # noqa: ARG001 - MkDocs hook signature
    by_node = build()
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(by_node, ensure_ascii=False, indent=1), encoding="utf-8")
    total = sum(len(v) for v in by_node.values())
    print(f"[build_quiz_data] {len(by_node)} chương, {total} câu hỏi -> {OUT.relative_to(ROOT)}")


if __name__ == "__main__":
    on_pre_build(None)
