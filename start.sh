#!/bin/bash
# 生产级高并发启动脚本
# 使用 gunicorn + UvicornWorker，多进程模式
# REFPROP 底层 Fortran 非线程安全，多进程是保证高并发不崩溃的唯一方式

set -e

# 工作目录：脚本所在目录
cd "$(dirname "$0")"

# 若存在 .env，加载（python-dotenv 也会加载，此处供 shell 使用）
if [ -f .env ]; then
  set -a
  source .env
  set +a
fi

# gunicorn 配置
# -w 4: 至少 4 个 worker 进程
# -k uvicorn.workers.UvicornWorker: 使用 Uvicorn 的 ASGI worker
# -b 0.0.0.0:8003: 绑定所有网卡，端口 8003
# --timeout: 长时间计算请求超时（秒），按需调整
# --access-logfile -: 访问日志输出到 stdout
exec gunicorn main:app \
  -w 4 \
  -k uvicorn.workers.UvicornWorker \
  -b 0.0.0.0:8003 \
  --timeout 120 \
  --access-logfile - \
  --error-logfile -
