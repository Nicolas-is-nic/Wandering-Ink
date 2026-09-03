#!/usr/bin/env bash
# 诗词行旅 · 一键部署脚本
# 流程：构建 dist → 同步到 gh-pages 工作副本 → 推送至 origin/gh-pages
# 前置：uv 环境已初始化（.venv 可用），SSH 可访问 GitHub
set -euo pipefail

ROOT="$(cd "$(dirname "$0")" && pwd)"
GHP="$ROOT/.gh-pages-work"
REMOTE="git@github.com:Nicolas-is-nic/Wandering-Ink.git"

cd "$ROOT"

echo "[1/3] 构建静态站..."
.venv/bin/python build/build.py

echo "[2/3] 同步构建产物到 gh-pages 工作副本..."
if [ ! -d "$GHP/.git" ]; then
  git clone "$REMOTE" "$GHP" --quiet
  cd "$GHP"
  git checkout --orphan gh-pages --quiet
  git rm -rf . >/dev/null 2>&1 || true
  cd "$ROOT"
fi
rsync -a --delete --exclude='.git' --exclude='.nojekyll' "$ROOT/dist/" "$GHP/"
touch "$GHP/.nojekyll"

echo "[3/3] 提交并推送 gh-pages..."
cd "$GHP"
git add -A
if git diff --cached --quiet; then
  echo "构建产物无变化，跳过推送。"
else
  git commit --quiet -m "deploy: 构建产物更新 $(date '+%Y-%m-%d %H:%M')"
  git push origin gh-pages --quiet
  echo "已推送 origin/gh-pages。Pages 将在一两分钟内自动更新。"
fi
