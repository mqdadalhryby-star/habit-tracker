#!/usr/bin/env bash
# ينشر ملفات الموقع إلى فرع gh-pages — وهو المصدر الرسمي لـ GitHub Pages في هذا المستودع.
# الاستخدام:  GITHUB_TOKEN=<pat> bash scripts/publish-gh-pages.sh
set -euo pipefail

REPO_SLUG="${REPO_SLUG:-mqdadalhryby-star/habit-tracker}"
LOCAL_DIR="${LOCAL_DIR:-$(cd "$(dirname "$0")/.." && pwd)}"
GITHUB_USER="${GITHUB_USER:-mqdadalhryby-star}"

if [[ -z "${GITHUB_TOKEN:-}" ]]; then
  echo "خطأ: GITHUB_TOKEN غير مضبوط." >&2
  exit 1
fi

BUILD_DIR="$(mktemp -d)"
trap 'rm -rf "$BUILD_DIR"' EXIT

# نجمع ملفات الموقع الثابتة فقط (بدون مصدر النموذج)
cp "$LOCAL_DIR/index.html" "$LOCAL_DIR/styles.css" "$LOCAL_DIR/app.js" "$BUILD_DIR/"
mkdir -p "$BUILD_DIR/docs"
cp "$LOCAL_DIR/docs/screenshot.png" "$BUILD_DIR/docs/"
cat > "$BUILD_DIR/README.md" <<'EOF'
# متتبع العادات — النسخة المنشورة

هذا الفرع (`gh-pages`) هو مصدر GitHub Pages.
المصدر الأساسي (كود التطبيق + نموذج `ai-builder`) موجود على فرع `main`.
EOF

cd "$BUILD_DIR"
git init -q -b gh-pages
git config user.name "MiniMax Code"
git config user.email "minimax-code@users.noreply.github.com"
git remote add origin "https://${GITHUB_USER}@github.com/${REPO_SLUG}.git"
git config credential.helper '!f() { echo "username='"${GITHUB_USER}"'"; echo "password=${GITHUB_TOKEN}"; }; f'

git add -A
git commit -q -m "deploy: تحديث النسخة المنشورة"
git push -q --force origin gh-pages
echo "✓ نُشرت ملفات الموقع إلى فرع gh-pages"
