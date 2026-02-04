# Flask 应用镜像：启动时自动执行 db upgrade，再启动 Gunicorn
FROM python:3.12-slim

WORKDIR /app

# 安装依赖
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# 应用代码（含 entrypoint.sh）
COPY . .

# 入口脚本必须在 COPY . . 之后赋予执行权限，否则会被覆盖
RUN chmod +x entrypoint.sh

# 通过环境变量指定 Flask 应用（也可在运行时覆盖）
ENV FLASK_APP=app.py

EXPOSE 5000

# 使用脚本作为入口：先 upgrade 再启动 Gunicorn
ENTRYPOINT ["./entrypoint.sh"]
