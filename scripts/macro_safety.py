#!/usr/bin/env python3
"""Gate chống LỖI MACRO-SYNTAX (mkdocs-macros/Jinja).

Bản build từng sập vì một ví dụ C# dùng '{{' / '}}' (escape ngoặc nhọn trong
string interpolation, cú pháp C# hợp lệ) — nhưng plugin macros coi MỌI '{{ }}'
trong toàn bộ markdown (kể cả trong code fence) là biểu thức Jinja cần parse,
nên build vỡ với 'Macro Syntax Error'.

Gate này quét MỌI file .md: nếu có '{{' hoặc '}}' KHÔNG phải là macro hợp lệ
(dotnet.current/csharp.version/postgres.current/model(...)) và KHÔNG nằm trong
khối '{% raw %} ... {% endraw %}', thì FAIL kèm gợi ý sửa.
"""
from __future__ import annotations
import re, sys, pathlib

ROOT = pathlib.Path(__file__).resolve().parent.parent
DOCS = ROOT / "docs"

# Macro hợp lệ đã biết (mở rộng khi facts.yml có thêm biến mới).
VALID_MACRO = re.compile(
    r"\{\{\s*(dotnet\.\w+|csharp\.\w+|postgres\.\w+|model\([^)]*\)(\.\w+)?)\s*\}\}"
)
DOUBLE_BRACE = re.compile(r"\{\{|\}\}")

def scan(paths: list[pathlib.Path]) -> list[str]:
    violations: list[str] = []
    for p in paths:
        text = p.read_text(encoding="utf-8")
        in_raw = False
        for i, line in enumerate(text.splitlines(), 1):
            if "{% raw %}" in line:
                in_raw = True
            if "{% endraw %}" in line:
                in_raw = False
                continue
            if in_raw:
                continue
            # Bỏ mọi occurrence hợp lệ, xem còn '{{' hay '}}' trần không.
            stripped = VALID_MACRO.sub("", line)
            if DOUBLE_BRACE.search(stripped):
                violations.append(
                    f"{p}:{i}  '{{{{' hoặc '}}}}' KHÔNG phải macro hợp lệ và KHÔNG trong "
                    f"{{% raw %}} -> sẽ vỡ build (Macro Syntax Error). Bọc bằng {{% raw %}}...{{% endraw %}} "
                    f"quanh đoạn code, hoặc đổi code tránh double-brace.  ->  {line.strip()[:90]}"
                )
    return violations

def main(argv: list[str]) -> int:
    target = pathlib.Path(argv[1]) if len(argv) > 1 else DOCS
    md = sorted(target.rglob("*.md")) if target.is_dir() else [target]
    v = scan(md)
    if v:
        print("❌ macro_safety: %d vi phạm" % len(v))
        print("\n".join(v))
        return 1
    print(f"✅ macro_safety: sạch ({len(md)} file)")
    return 0

if __name__ == "__main__":
    sys.exit(main(sys.argv))
