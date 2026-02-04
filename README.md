# flask-app

从原项目 `1st-flask-proj` 抽离出的 Flask Web 后端（不包含 scraper）。与同仓下的 **scraper** 共用同一数据库（`station`、`availability` 表），迁移在此维护，scraper 只负责写入数据。

## 运行方式

1. 准备环境变量（参考 `.env.example`）
2. 安装依赖
   ```bash
   pip install -r requirements.txt
   ```
3. 执行迁移（与 scraper 共用 DB 时，必须先在此执行）
   ```bash
   flask --app app.py db upgrade
   ```
4. 启动服务
   ```bash
   python app.py
   ```

## Docker 运行

镜像入口支持两种命令，通过**启动容器时传入的参数**选择：

| 参数      | 说明                         |
|-----------|------------------------------|
| `init-db` | 仅执行迁移，创建/更新数据库表 |
| `run`     | 运行 Flask 应用（默认）      |

**构建镜像：**
```bash
docker build -t flask-app .
```

**只创建数据库表（执行迁移后退出）：**
```bash
docker run --rm --env-file .env flask-app init-db
```

**运行 Flask 应用：**
```bash
docker run --rm --env-file .env -p 5000:5000 flask-app run
# 或省略 run（默认即为 run）
docker run --rm --env-file .env -p 5000:5000 flask-app
```

**加入 Docker 网络（生产环境推荐）：**
```bash
# 先创建网络（如尚未创建）
docker network create flask-app

# 运行时加入网络
docker run -d --name flask-app --network flask-app --env-file .env -p 5000:5000 flask-app run
```

需在镜像同目录准备 `.env`（含 `DATABASE_URL`、`SECRET_KEY` 等），或改用 `-e DATABASE_URL=...` 传环境变量。

## Jenkins CI/CD

项目使用 Jenkins Pipeline 自动构建和部署。

**流程说明：**

1. **拉取代码** - 从 Git 仓库拉取最新代码
2. **Python 语法检查** - 验证 Python 文件语法
3. **构建并推送镜像** - 构建 Docker 镜像并推送到 Docker Hub
4. **部署到 EC2** - main 分支的构建会自动部署到 EC2 服务器

**Jenkins 需要的凭据：**

| 凭据 ID                  | 类型               | 说明                     |
|--------------------------|-------------------|--------------------------|
| `docker-hub-credentials` | Username/Password | Docker Hub 登录凭据       |
| `aws-ec2`                | Secret text       | EC2 服务器地址            |
| `server-ssh-key`         | SSH Private Key   | EC2 SSH 私钥             |
| `flask-prod.env`         | Secret file       | 生产环境 .env 文件        |

**EC2 部署前准备：**

在 EC2 服务器上执行：
```bash
# 创建 Docker 网络
docker network create flask-app

# 创建 .env 存放目录（Jenkins 会自动上传 .env 文件到此路径）
mkdir -p /opt/flask-app
```
