#!/bin/bash
# 从 GitHub 拉取更新并重启服务
set -e
cd "$(dirname "$0")/.."
echo ">>> 拉取最新代码..."
git pull origin main
echo ">>> 更新依赖..."
source venv/bin/activate
pip install -r requirements.txt -q
echo ">>> 重启服务..."
sudo systemctl restart refbackend
echo ">>> 部署完成"
sudo systemctl status refbackend --no-pager
