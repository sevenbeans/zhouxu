#!/usr/bin/env bash
# 从 mvp/ 生成 GitHub Pages 发布目录 docs/，避免手工复制导致版本漂移。
set -euo pipefail
cd "$(dirname "$0")/.."
rm -rf docs
mkdir -p docs
cp mvp/index.html mvp/app.js mvp/parser.js mvp/styles.css docs/
cp -R mvp/assets docs/assets
cp -R mvp/case docs/case
cp mvp/README.md docs/README.md
touch docs/.nojekyll
echo "已生成 docs/（GitHub Pages 发布目录）："
find docs -type f | sort
