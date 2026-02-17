#!/bin/bash
# refbackend 启动脚本（方案 B：Wine 后端）
# 确保 WINE_REFPROP_URL 被正确传递给 uvicorn 进程
cd "$(dirname "$0")"
export WINE_REFPROP_URL="${WINE_REFPROP_URL:-http://127.0.0.1:8002}"
source venv/bin/activate
exec uvicorn main:app --host 0.0.0.0 --port 8003
