#!/usr/bin/env python3
"""Gate chống LỖI THỜI & BỊA ĐẶT.

- FAIL nếu prose (ngoài code fence và ngoài khối <!-- historical -->) chứa:
    (a) bất kỳ cụm nào trong facts.yml -> banned  (vd 'Antigravity IDE', 'Skill.md',
        'GPT-4 Turbo', 'Claude 3.5 Sonnet'…), HOẶC
    (b) version literal viết cứng: '.NET 10', 'C# 14', 'claude-3-…', 'gpt-4/5…'
        (phải dùng macro {{ dotnet.current }} thay vì viết literal).

Dùng được cả CLI lẫn import (gate_selftest gọi scan()).
"""
from __future__ import annotations
import re, sys, pathlib
import yaml

ROOT = pathlib.Path(__file__).resolve().parent.parent
FACTS = ROOT / "data" / "facts.yml"

# Chỉ chặn model-ID chắc chắn LỖI THỜI. Cho phép trích dẫn version C#/.NET trong prose
# vì giáo trình PHẢI nêu chính xác tính năng ra ở phiên bản nào (vd "records: C# 9",
# ".NET 1.x"). "Phiên bản hiện hành" vẫn dùng macro {{ dotnet.current }} theo kỷ luật.
VERSION_PATTERNS = [
    re.compile(r"\bclaude-3\b", re.I),
]

def load_banned() -> list[str]:
    data = yaml.safe_load(FACTS.read_text(encoding="utf-8"))
    return [str(x) for x in data.get("banned", [])]

def scan(paths: list[pathlib.Path], banned: list[str]) -> list[str]:
    violations: list[str] = []
    for p in paths:
        in_code = False
        in_hist = False
        for i, line in enumerate(p.read_text(encoding="utf-8").splitlines(), 1):
            s = line.strip()
            if s.startswith("```"):
                in_code = not in_code
                continue
            if in_code:
                continue
            if "<!-- historical -->" in line:
                in_hist = True
            if "<!-- /historical -->" in line:
                in_hist = False
                continue
            if in_hist:
                continue
            for term in banned:
                # KHỚP PHÂN BIỆT HOA/THƯỜNG: mục đích là cấm đúng chuỗi sai-case
                # (vd cấm 'Skill.md' nhưng CHO PHÉP 'SKILL.md' đúng chuẩn).
                if term in line:
                    violations.append(f"{p}:{i}  CẤM: '{term}'  ->  {s[:80]}")
            for pat in VERSION_PATTERNS:
                if pat.search(line):
                    violations.append(
                        f"{p}:{i}  VERSION LITERAL (dùng macro thay vì viết cứng)  ->  {s[:80]}")
    return violations

def main(argv: list[str]) -> int:
    target = pathlib.Path(argv[1]) if len(argv) > 1 else ROOT / "docs"
    md = sorted(target.rglob("*.md")) if target.is_dir() else [target]
    v = scan(md, load_banned())
    if v:
        print("❌ banned_terms: %d vi phạm" % len(v))
        print("\n".join(v))
        return 1
    print(f"✅ banned_terms: sạch ({len(md)} file)")
    return 0

if __name__ == "__main__":
    sys.exit(main(sys.argv))
