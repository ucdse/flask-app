#!/bin/sh

# 遇到错误立即退出
set -e

# 1. 应用数据库迁移 (只执行 upgrade，不执行 migrate)
echo "Running DB migrations..."
flask db upgrade

# 2. 启动 Gunicorn
echo "Starting Gunicorn..."
# exec 能够让 gunicorn 替换当前 shell 进程，接收系统信号
# gthread 多线程模式：适合长时间 I/O（如 SSE 流式输出），避免单请求霸占进程导致超时
exec gunicorn -w 2 -b 0.0.0.0:5000 --worker-class gthread --threads 4 --timeout 120 --access-logfile - wsgi:app
