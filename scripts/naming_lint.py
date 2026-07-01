#!/usr/bin/env python3
"""Gate ĐẶT TÊN NHẤT QUÁN (bản cũ có 5 kiểu tên lẫn lộn).

Quy tắc: file bài trong thư-mục-pha phải là kebab-case '<a-b-c>.md' hoặc 'index.md'.
Các trang meta ở gốc docs/ (index, PEDAGOGY, FAST-PATH…) được miễn.
"""
from __future__ import annotations
import re, sys, pathlib

ROOT = pathlib.Path(__file__).resolve().parent.parent
DOCS = ROOT / "docs"
KEBAB = re.compile(r"^[a-z0-9]+(-[a-z0-9]+)*\.md$")

def main() -> int:
    bad: list[str] = []
    for p in DOCS.rglob("*.md"):
        rel = p.relative_to(DOCS)
        if len(rel.parts) == 1:           # trang meta ở gốc docs/ -> miễn
            continue
        name = p.name
        if name == "index.md" or KEBAB.match(name):
            continue
        bad.append(str(rel))
    if bad:
        print("❌ naming_lint: tên không theo kebab-case:")
        print("\n".join("   " + b for b in bad))
        return 1
    print("✅ naming_lint: mọi tên file hợp lệ")
    return 0

if __name__ == "__main__":
    sys.exit(main())
