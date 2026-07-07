#!/usr/bin/env python3
"""MkDocs hook: sinh docs/assets/quiz-data.json từ data/questions.yml lúc build.

Chạy tự động qua "hooks:" trong mkdocs.yml (event on_pre_build) — không cần
bước build riêng, không thể quên chạy, và nếu questions.yml hỏng thì
mkdocs build (đã --strict trong CI) sẽ fail ngay tại đây.

Cũng đọc nav của mkdocs.yml để gắn TÊN CHƯƠNG người-đọc-được (không phải slug
thô) cho mỗi node — dùng trong dropdown của on-tap.md.
"""
from __future__ import annotations
import json
import pathlib
import yaml

ROOT = pathlib.Path(__file__).resolve().parent.parent
QUESTIONS = ROOT / "data" / "questions.yml"
MKDOCS = ROOT / "mkdocs.yml"
OUT = ROOT / "docs" / "assets" / "quiz-data.json"


class _IgnoreUnknown(yaml.SafeLoader):
    """Bỏ qua tag !!python/name: ... trong mkdocs.yml (chỉ cần đọc nav)."""


def _ignore(loader, suffix, node):
    return None


_IgnoreUnknown.add_multi_constructor("tag:yaml.org,2002:python/name:", _ignore)
_IgnoreUnknown.add_multi_constructor("!!python/name:", _ignore)


def node_titles_from_nav(nav) -> dict[str, str]:
    """node key = basename file (không đuôi .md) -> tên hiển thị trong nav."""
    titles: dict[str, str] = {}
    def walk(node, current_title):
        if isinstance(node, str):
            if node.endswith(".md"):
                key = pathlib.Path(node).stem
                titles[key] = current_title
        elif isinstance(node, dict):
            for title, v in node.items():
                walk(v, title)
        elif isinstance(node, list):
            for v in node:
                walk(v, current_title)
    walk(nav, "")
    return titles


def build(nav) -> tuple[dict[str, list[dict]], dict[str, str]]:
    data = yaml.safe_load(QUESTIONS.read_text(encoding="utf-8")) or {}
    by_node: dict[str, list[dict]] = {}
    for q in data.get("questions", []):
        node = q["node"]
        by_node.setdefault(node, []).append({
            "id": q["id"],
            "prompt": q["prompt"],
            "answer": q["answer"],
        })
    titles = node_titles_from_nav(nav)
    return by_node, titles


def on_pre_build(config, **kwargs):  # noqa: ARG001 - MkDocs hook signature
    nav = config.nav if config is not None else yaml.load(
        MKDOCS.read_text(encoding="utf-8"), Loader=_IgnoreUnknown
    ).get("nav", [])
    by_node, titles = build(nav)
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(
        json.dumps({"questions": by_node, "titles": titles}, ensure_ascii=False, indent=1),
        encoding="utf-8",
    )
    total = sum(len(v) for v in by_node.values())
    print(f"[build_quiz_data] {len(by_node)} chương, {total} câu hỏi -> {OUT.relative_to(ROOT)}")


if __name__ == "__main__":
    on_pre_build(None)
