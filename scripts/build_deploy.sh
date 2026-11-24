#!/usr/bin/env bash
# 从 mvp/ 生成发布目录 deploy/，避免手工复制导致版本漂移。
set -euo pipefail
cd "$(dirname "$0")/.."
rm -rf deploy
mkdir -p deploy
cp mvp/index.html mvp/app.js mvp/parser.js mvp/styles.css deploy/
cp -R mvp/assets deploy/assets
cp mvp/README.md deploy/README.md
echo "已生成 deploy/："
find deploy -type f | sort
