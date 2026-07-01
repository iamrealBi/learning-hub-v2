#!/usr/bin/env python3
"""Gate CẤU TRÚC: 0 trang mồ côi, 0 nav trỏ file thiếu.

Bản cũ có 26 trang mồ côi + 51 link gãy vì không có gate này.
So khớp nav trong mkdocs.yml với cây file thực trong docs/.
"""
from __future__ import annotations
import sys, pathlib
import yaml

ROOT = pathlib.Path(__file__).resolve().parent.parent
DOCS = ROOT / "docs"
MKDOCS = ROOT / "mkdocs.yml"

class _IgnoreUnknown(yaml.SafeLoader):
    """Bỏ qua tag !!python/name: ... trong mkdocs.yml."""
def _ignore(loader, suffix, node):
    return None
_IgnoreUnknown.add_multi_constructor("tag:yaml.org,2002:python/name:", _ignore)
_IgnoreUnknown.add_multi_constructor("!!python/name:", _ignore)

def nav_md(nav) -> set[str]:
    found: set[str] = set()
    def walk(node):
        if isinstance(node, str):
            if node.endswith(".md"):
                found.add(node)
        elif isinstance(node, dict):
            for v in node.values():
                walk(v)
        elif isinstance(node, list):
            for v in node:
                walk(v)
    walk(nav)
    return found

def main() -> int:
    cfg = yaml.load(MKDOCS.read_text(encoding="utf-8"), Loader=_IgnoreUnknown)
    in_nav = nav_md(cfg.get("nav", []))
    on_disk = {str(p.relative_to(DOCS)).replace("\\", "/") for p in DOCS.rglob("*.md")}

    orphans = sorted(on_disk - in_nav)
    broken = sorted(f for f in in_nav if not (DOCS / f).exists())

    ok = True
    if orphans:
        ok = False
        print("❌ TRANG MỒ CÔI (có file, không trong nav):")
        print("\n".join("   " + o for o in orphans))
    if broken:
        ok = False
        print("❌ NAV GÃY (trong nav, thiếu file):")
        print("\n".join("   " + b for b in broken))
    if ok:
        print(f"✅ nav_audit: {len(on_disk)} trang, 0 mồ côi, 0 nav gãy")
        return 0
    return 1

if __name__ == "__main__":
    sys.exit(main())
