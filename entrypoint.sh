#!/bin/sh

# 遇到错误立即退出
set -e

# 1. 应用数据库迁移 (只执行 upgrade，不执行 migrate)
echo "Running DB migrations..."
flask db upgrade

# 2. 启动 Gunicorn
echo "Starting Gunicorn..."
# exec 能够让 gunicorn 替换当前 shell 进程，接收系统信号
exec gunicorn -w 4 -b 0.0.0.0:5000 --access-logfile - app:app
