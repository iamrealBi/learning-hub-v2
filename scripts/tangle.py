#!/usr/bin/env python3
"""Trích code block để CI COMPILE/CHẠY (literate testing).

Mọi block ```csharp phải mang tag ở dòng đầu:
    // test:run        -> CI chạy `dotnet run`, phải PASS
    // test:compile    -> CI chỉ `dotnet build` (đoạn thư-viện)
    // test:skip <lý do> -> cố ý bỏ (phải nêu lý do)
Block ```csharp KHÔNG tag  ->  tangle BÁO LỖI (không cho code chưa kiểm chứng lọt).

Script này trích ra verify/ + in thống kê; bước `dotnet` trong CI sẽ build/chạy.
(Chạy được không cần .NET SDK — chỉ trích xuất; SDK cần ở bước CI sau.)
"""
from __future__ import annotations
import re, sys, pathlib

ROOT = pathlib.Path(__file__).resolve().parent.parent
DOCS = ROOT / "docs"
OUT = ROOT / "verify" / "extracted"
FENCE = re.compile(r"^```csharp(\s|$)")
TAG = re.compile(r"//\s*test:(run|compile|skip)\b(.*)$")

def extract(md_files):
    blocks = []          # (source, kind, code)
    untagged = []        # (source, line)
    for p in md_files:
        lines = p.read_text(encoding="utf-8").splitlines()
        i = 0
        while i < len(lines):
            if FENCE.match(lines[i].strip()):
                start = i + 1
                j = start
                while j < len(lines) and not lines[j].strip().startswith("```"):
                    j += 1
                body = lines[start:j]
                first = body[0] if body else ""
                m = TAG.search(first)
                if not m:
                    untagged.append(f"{p.relative_to(ROOT)}:{start}")
                else:
                    blocks.append((p.relative_to(ROOT), m.group(1), "\n".join(body)))
                i = j
            i += 1
    return blocks, untagged

def main() -> int:
    md = sorted(DOCS.rglob("*.md"))
    blocks, untagged = extract(md)
    if untagged:
        print("❌ tangle: code C# KHÔNG có tag test: (thêm // test:run|compile|skip):")
        print("\n".join("   " + u for u in untagged))
        return 1
    OUT.mkdir(parents=True, exist_ok=True)
    run = comp = skip = 0
    for idx, (src, kind, code) in enumerate(blocks):
        if kind == "skip":
            skip += 1
            continue
        run += (kind == "run")
        comp += (kind == "compile")
        (OUT / f"snippet_{idx:03d}_{kind}.cs").write_text(code, encoding="utf-8")
    print(f"✅ tangle: trích {len(blocks)} block (run={run}, compile={comp}, skip={skip}) -> {OUT}")
    print("   (bước CI kế tiếp: dotnet build/run trên các snippet run/compile)")
    return 0

if __name__ == "__main__":
    sys.exit(main())
