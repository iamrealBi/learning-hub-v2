#!/usr/bin/env bash
# Compile/chạy mọi snippet C# đã trích. Chạy trong CI (cần .NET SDK).
# - snippet 'run'     : chương trình top-level tự chứa -> dotnet run, phải PASS.
# - snippet 'compile' : đoạn cần package (vd JWT) -> build trong web project có ref.
# Code bịa/API sai/không compile  ->  bước này FAIL  ->  không merge được.
#
# Không dùng `set -e` cho vòng lặp: một snippet lỗi không được phép dừng cả
# script giữa đường, vì như vậy CI chỉ lộ ra lỗi ĐẦU TIÊN mỗi lần chạy — sửa
# xong lại phải chờ CI chạy lại ~10 phút mới thấy lỗi tiếp theo. Thay vào đó,
# chạy hết mọi snippet, gom toàn bộ lỗi, rồi báo cáo tất cả một lần ở cuối.
set -uo pipefail

EX="verify/extracted"
[ -d "$EX" ] || { echo "Chưa có snippet (chạy python scripts/tangle.py trước)"; exit 1; }

FAILED=()

echo "=== RUN snippets (console, net10.0) ==="
dotnet new console -o verify/run >/dev/null
for f in "$EX"/snippet_*_run.cs; do
  [ -e "$f" ] || continue
  cp "$f" verify/run/Program.cs
  echo "-- run: $f"
  if ! ( cd verify/run && dotnet run -c Release ); then
    FAILED+=("$f")
    echo "❌ FAIL: $f"
  fi
done

echo "=== COMPILE snippets (web project + package auth) ==="
dotnet new web -o verify/web >/dev/null
( cd verify/web
  dotnet add package Microsoft.AspNetCore.Authentication.JwtBearer >/dev/null
  dotnet add package System.IdentityModel.Tokens.Jwt >/dev/null )
for f in "$EX"/snippet_*_compile.cs; do
  [ -e "$f" ] || continue
  echo "-- build: $f"
  # Nếu snippet có top-level statements, nó THAY Program.cs; nếu là class thì thêm file.
  if grep -qE '^\s*(var|using )' "$f" && ! grep -qE '^\s*(public|internal|sealed) ' "$(head -1 <<<"$f")" 2>/dev/null; then
    cp "$f" verify/web/Program.cs
  else
    cp "$f" verify/web/Snippet.cs
  fi
  if ! ( cd verify/web && dotnet build -c Release ); then
    FAILED+=("$f")
    echo "❌ FAIL: $f"
  fi
  rm -f verify/web/Snippet.cs
done

if [ "${#FAILED[@]}" -gt 0 ]; then
  echo ""
  echo "❌ verify_dotnet: ${#FAILED[@]} snippet lỗi compile/chạy:"
  printf '   %s\n' "${FAILED[@]}"
  exit 1
fi

echo "✅ verify_dotnet: mọi snippet compile/chạy OK"
