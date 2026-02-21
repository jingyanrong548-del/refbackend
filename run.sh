#!/bin/bash
# refbackend 本地开发启动脚本
cd "$(dirname "$0")"
[ -d venv ] && source venv/bin/activate
exec uvicorn main:app --host 0.0.0.0 --port 8003
