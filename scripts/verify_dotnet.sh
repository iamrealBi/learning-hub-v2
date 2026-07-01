#!/usr/bin/env bash
# Compile/chạy mọi snippet C# đã trích. Chạy trong CI (cần .NET SDK).
# - snippet 'run'     : chương trình top-level tự chứa -> dotnet run, phải PASS.
# - snippet 'compile' : đoạn cần package (vd JWT) -> build trong web project có ref.
# Code bịa/API sai/không compile  ->  bước này FAIL  ->  không merge được.
set -euo pipefail

EX="verify/extracted"
[ -d "$EX" ] || { echo "Chưa có snippet (chạy python scripts/tangle.py trước)"; exit 1; }

echo "=== RUN snippets (console, net10.0) ==="
dotnet new console -o verify/run >/dev/null
for f in "$EX"/snippet_*_run.cs; do
  [ -e "$f" ] || continue
  cp "$f" verify/run/Program.cs
  echo "-- run: $f"
  ( cd verify/run && dotnet run -c Release )
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
  ( cd verify/web && dotnet build -c Release )
  rm -f verify/web/Snippet.cs
done

echo "✅ verify_dotnet: mọi snippet compile/chạy OK"
