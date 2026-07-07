#!/usr/bin/env python3
"""Gate CẤU TRÚC: 0 trang mồ côi, 0 nav trỏ file thiếu, 0 lệch với DAG.

Bản cũ có 26 trang mồ côi + 51 link gãy vì không có gate này.
So khớp nav trong mkdocs.yml với cây file thực trong docs/, VÀ đối chiếu với
curriculum/curriculum.yml (nguồn sự thật cho DAG prerequisite) — đúng như
comment ở đầu curriculum.yml và mkdocs.yml đã hứa nhưng trước đây chưa làm:
  - mọi file trong curriculum.yml phải nằm trong nav (và ngược lại, trong
    phạm vi chuỗi bài học P0..Capstone — không tính "Luyện tập"/"Về hệ thống").
  - DAG không có chu trình (cycle).
  - mọi `requires` trỏ tới node id có thật.
  - thứ tự xuất hiện trong nav phải tôn trọng `requires` (prerequisite phải
    đứng TRƯỚC trong nav, không phải chỉ đúng trên giấy tờ curriculum.yml).
"""
from __future__ import annotations
import sys, pathlib
import yaml

ROOT = pathlib.Path(__file__).resolve().parent.parent
DOCS = ROOT / "docs"
MKDOCS = ROOT / "mkdocs.yml"
CURRICULUM = ROOT / "curriculum" / "curriculum.yml"
NON_CHAIN_SECTIONS = {"🧪 Luyện tập", "Về hệ thống"}

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

def nav_chain_order(nav) -> list[str]:
    """Thứ tự file THẬT trong nav, chỉ tính chuỗi bài học.

    Bỏ mọi entry top-level KHÔNG phải một section lồng (ví dụ "Trang chủ":
    index.md, "Fast Path": FAST-PATH-2-NGAY.md — một trang đơn, không phải
    danh sách con), và bỏ hai section lồng không thuộc chuỗi bài học
    ('Luyện tập', 'Về hệ thống').
    """
    order: list[str] = []
    def walk(node):
        if isinstance(node, str):
            if node.endswith(".md"):
                order.append(node)
        elif isinstance(node, dict):
            for v in node.values():
                walk(v)
        elif isinstance(node, list):
            for v in node:
                walk(v)
    for entry in nav:
        if not isinstance(entry, dict):
            continue
        for section_title, body in entry.items():
            if section_title in NON_CHAIN_SECTIONS or not isinstance(body, list):
                continue
            walk(body)
    return order

def curriculum_check(in_nav: set[str], nav_order: list[str], curriculum_cfg: dict) -> tuple[bool, list[str]]:
    errors: list[str] = []
    nodes = [n for phase in curriculum_cfg.get("phases", []) for n in phase.get("nodes", [])]
    by_id = {n["id"]: n for n in nodes}

    curriculum_files = {n["file"] for n in nodes}
    missing_from_curriculum = sorted(curriculum_files - in_nav)
    if missing_from_curriculum:
        errors.append("file trong curriculum.yml nhưng KHÔNG có trong nav: " + ", ".join(missing_from_curriculum))

    extra_in_chain = sorted(set(nav_order) - curriculum_files)
    if extra_in_chain:
        errors.append("file trong chuỗi bài học của nav nhưng KHÔNG có trong curriculum.yml: " + ", ".join(extra_in_chain))

    nav_position = {f: i for i, f in enumerate(nav_order)}
    for n in nodes:
        if n["file"] not in nav_position:
            errors.append(f"node '{n['id']}' (file {n['file']}) không nằm trong chuỗi bài học của nav")

    # DAG: mọi requires phải trỏ tới id có thật, và không có chu trình.
    for n in nodes:
        for req in n.get("requires", []) or []:
            if req not in by_id:
                errors.append(f"node '{n['id']}' requires '{req}' — id này không tồn tại trong curriculum.yml")

    WHITE, GRAY, BLACK = 0, 1, 2
    color = {n["id"]: WHITE for n in nodes}
    cycle_path: list[str] = []
    def visit(node_id: str) -> bool:
        color[node_id] = GRAY
        cycle_path.append(node_id)
        for req in by_id.get(node_id, {}).get("requires", []) or []:
            if req not in by_id:
                continue
            if color[req] == GRAY:
                errors.append("CHU TRÌNH trong DAG: " + " -> ".join(cycle_path + [req]))
                return False
            if color[req] == WHITE and not visit(req):
                return False
        cycle_path.pop()
        color[node_id] = BLACK
        return True
    for n in nodes:
        if color[n["id"]] == WHITE:
            visit(n["id"])

    # Thứ tự nav phải tôn trọng requires: prerequisite phải đứng TRƯỚC trong nav.
    for n in nodes:
        this_pos = nav_position.get(n["file"])
        if this_pos is None:
            continue
        for req in n.get("requires", []) or []:
            req_node = by_id.get(req)
            if req_node is None:
                continue
            req_pos = nav_position.get(req_node["file"])
            if req_pos is not None and req_pos >= this_pos:
                errors.append(
                    f"nav sai thứ tự: '{n['id']}' ({n['file']}) cần '{req}' ({req_node['file']}) "
                    f"nhưng '{req}' lại đứng SAU (hoặc cùng vị trí) trong nav"
                )

    return (len(errors) == 0, errors)

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

    nav_order = nav_chain_order(cfg.get("nav", []))
    curriculum_cfg = yaml.safe_load(CURRICULUM.read_text(encoding="utf-8"))
    curr_ok, curr_errors = curriculum_check(in_nav, nav_order, curriculum_cfg)
    if not curr_ok:
        ok = False
        print("❌ LỆCH VỚI curriculum.yml (DAG):")
        print("\n".join("   " + e for e in curr_errors))

    if ok:
        print(f"✅ nav_audit: {len(on_disk)} trang, 0 mồ côi, 0 nav gãy, 0 lệch DAG")
        return 0
    return 1

if __name__ == "__main__":
    sys.exit(main())
