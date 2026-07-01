#!/usr/bin/env python3
"""KIỂM TRA CHÍNH CÁC GATE (fixture test).

Bài học lớn nhất từ bản cũ: 'AI reviewer' được quảng cáo nhưng CHƯA BAO GIỜ chạy.
Ở đây ta chứng minh mỗi gate THẬT SỰ bắt được mục tiêu của nó bằng input-xấu đã biết.
CI FAIL nếu một gate KHÔNG phát hiện lỗi mà lẽ ra phải bắt.
"""
from __future__ import annotations
import sys, pathlib

SCRIPTS = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(SCRIPTS))
ROOT = SCRIPTS.parent
FIX = ROOT / "tests" / "fixtures"

import banned_terms
import qa_lint

def main() -> int:
    fails: list[str] = []

    # 1) banned_terms PHẢI bắt được file chứa 'Antigravity IDE' + version literal
    v = banned_terms.scan([FIX / "bad_banned_term.md"], banned_terms.load_banned())
    if not v:
        fails.append("banned_terms KHÔNG bắt được fixture xấu (gate hỏng!)")
    else:
        print(f"✅ banned_terms bắt được {len(v)} vi phạm trong fixture (đúng kỳ vọng)")

    # 2) qa_lint PHẢI bắt được câu hỏi thiếu đáp án + trùng prompt
    v2 = qa_lint.scan(FIX / "bad_questions.yml")
    if not v2:
        fails.append("qa_lint KHÔNG bắt được fixture xấu (gate hỏng!)")
    else:
        print(f"✅ qa_lint bắt được {len(v2)} vi phạm trong fixture (đúng kỳ vọng)")

    if fails:
        print("\n❌ GATE SELF-TEST THẤT BẠI:")
        print("\n".join("   " + f for f in fails))
        return 1
    print("\n✅ Mọi gate đều bắt đúng input-xấu — gate hoạt động thật.")
    return 0

if __name__ == "__main__":
    sys.exit(main())
