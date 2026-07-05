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
  dotnet add package System.IdentityModel.Tokens.Jwt >/dev/null
  dotnet add package Microsoft.AspNetCore.OpenApi >/dev/null
  dotnet add package Microsoft.EntityFrameworkCore >/dev/null
  dotnet add package Microsoft.EntityFrameworkCore.InMemory >/dev/null
  dotnet add package Npgsql.EntityFrameworkCore.PostgreSQL >/dev/null )
# Chụp lại Program.cs gốc (do `dotnet new web` sinh ra) MỘT LẦN, để khôi phục
# trước mỗi snippet — nếu không, snippet nào ghi đè Program.cs sẽ làm BẨN mọi
# snippet 'class-only' chạy SAU nó trong cùng vòng lặp (từng gây rớt hàng loạt).
cp verify/web/Program.cs verify/web/Program.cs.pristine
for f in "$EX"/snippet_*_compile.cs; do
  [ -e "$f" ] || continue
  echo "-- build: $f"
  cp verify/web/Program.cs.pristine verify/web/Program.cs
  rm -f verify/web/Snippet.cs
  # Mặc định: coi snippet là class/record thêm-vào (Snippet.cs), giữ Program.cs
  # gốc (đã có top-level statements từ `dotnet new web`). Không đoán bằng regex
  # trên nội dung file (dễ sai — vd snippet "top-level statements + class phụ
  # trợ" vẫn chứa dòng `public class ...`) — để chính compiler quyết: nếu build
  # báo CS8802 (2 compilation unit cùng có top-level statements), nghĩa là
  # snippet NÀY tự nó là top-level -> thử lại bằng cách thay hẳn Program.cs.
  cp "$f" verify/web/Snippet.cs
  build_out=$( cd verify/web && dotnet build -c Release 2>&1 )
  build_status=$?
  if [ $build_status -ne 0 ] && grep -q "CS8802" <<<"$build_out"; then
    echo "   (snippet tự thân có top-level statements -> thử lại bằng cách thay Program.cs)"
    rm -f verify/web/Snippet.cs
    cp "$f" verify/web/Program.cs
    build_out=$( cd verify/web && dotnet build -c Release 2>&1 )
    build_status=$?
  fi
  echo "$build_out"
  if [ $build_status -ne 0 ]; then
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
