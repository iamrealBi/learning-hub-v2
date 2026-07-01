# Đưa lên GitHub Pages (3 bước)

Repo đã `git init` + commit sẵn. Chỉ cần đẩy lên và bật Pages.

> ⚠️ **Đừng ghi đè repo cũ `iamrealBi/learning-hub`** — nó có nội dung khác. Tạo **repo mới**.

## 1. Tạo repo mới trên GitHub
Vào github.com → New repository → tên vd `learning-hub-v2` → **để trống** (đừng thêm README).

## 2. Đẩy code lên
```bash
cd "learning-hub-v2"
git branch -M main
git remote add origin https://github.com/<TÊN-GITHUB-CỦA-BẠN>/learning-hub-v2.git
git push -u origin main
```

## 3. Bật GitHub Pages
- **Settings → Actions → General → Workflow permissions →** chọn *Read and write permissions* (để workflow đẩy được nhánh `gh-pages`).
- Push lên `main` sẽ tự chạy workflow `.github/workflows/ci.yml`:
  - job `gates` xanh → job `deploy` chạy `mkdocs gh-deploy --force` → tạo nhánh `gh-pages`.
- **Settings → Pages → Source:** *Deploy from a branch* → chọn `gh-pages` / `(root)` → Save.
- Vài phút sau site lên tại: `https://<TÊN-GITHUB>.github.io/learning-hub-v2/`

## (Tuỳ chọn) đặt site_url
Trong `mkdocs.yml`, bỏ chú thích và sửa:
```yaml
site_url: "https://<TÊN-GITHUB>.github.io/learning-hub-v2/"
```

## Nếu có `gh` CLI (nhanh hơn)
```bash
gh repo create learning-hub-v2 --public --source=. --remote=origin --push
```
