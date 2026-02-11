# flask-app

从原项目 `1st-flask-proj` 抽离出的 Flask Web 后端（不包含 scraper）。与同仓下的 **scraper** 共用同一数据库（`station`、`availability` 表），迁移在此维护，scraper 只负责写入数据。

主要功能包括：用户注册/登录（JWT）、邮箱验证、站点与可用性查询、天气预报接口等。

### 项目结构概览

| 路径 | 说明 |
|------|------|
| `app/` | 应用主包：`api/` 路由、`models/` 数据模型、`services/` 业务逻辑、`schemas/` 序列化、`utils/` 工具 |
| `config.py` | 配置（从环境变量读取） |
| `run.py` | 本地开发入口（`python run.py`） |
| `wsgi.py` | WSGI 入口（Gunicorn / Docker 使用） |
| `migrations/` | Flask-Migrate 数据库迁移 |
| `requirements.txt` | Python 依赖 |

---

## 一、本地运行（不用 Docker）

在本地机器上直接运行，适合开发与调试。

### 1. 环境要求

- **Anaconda 或 Miniconda**：已安装 [Anaconda](https://www.anaconda.com/) 或 [Miniconda](https://docs.conda.io/en/latest/miniconda.html)
- **Python**：3.10 或以上（推荐 3.12，与 Docker 镜像一致），由 conda 环境提供
- **数据库**：MySQL（或与 `DATABASE_URL` 兼容的数据库），需事先创建好数据库
- **可选**：若需邮件验证码，需可用的 SMTP 配置；否则验证码仅输出到控制台

### 2. 使用 Anaconda 创建并激活虚拟环境（推荐）

```bash
# 进入项目目录
cd /path/to/flask-app

# 使用 conda 创建虚拟环境（指定 Python 版本，如 3.12）
conda create -n flask-app python=3.12 -y

# 激活虚拟环境
# macOS / Linux:
conda activate flask-app
# Windows (CMD):
# conda activate flask-app
# Windows (PowerShell):
# conda activate flask-app
```

激活后终端提示符前会显示 `(flask-app)`。退出环境使用 `conda deactivate`。

### 3. 配置环境变量

复制示例文件并按需修改：

```bash
cp .env.example .env
```

编辑 `.env`，**必填项**如下：

| 变量名 | 说明 |
|--------|------|
| `DATABASE_URL` | 数据库连接 URL，如 `mysql+pymysql://user:password@localhost:3306/dbname` |
| `SECRET_KEY` | Flask 会话密钥，建议随机字符串 |
| `JWT_SECRET_KEY` | JWT Access Token 签名密钥 |
| `JWT_REFRESH_SECRET_KEY` | JWT Refresh Token 签名密钥 |
| `OPENWEATHER_API_BASE_URL` | OpenWeatherMap API 基础 URL（如 `https://api.openweathermap.org/data/3.0/onecall`） |
| `OPENWEATHER_API_KEY` | OpenWeatherMap API Key（[官网](https://openweathermap.org/api) 申请） |

可选：邮箱验证、前端激活链接等见 `.env.example` 内注释。若需在终端直接使用 `flask db upgrade` 而不带 `--app`，可在 `.env` 中增加一行：

```bash
FLASK_APP=app:create_app
```

### 4. 安装依赖

```bash
pip install -r requirements.txt
```

### 5. 执行数据库迁移

与 scraper 共用数据库时，**必须先在本项目执行迁移**：

```bash
flask --app app:create_app db upgrade
```

若已在 `.env` 中设置 `FLASK_APP=app:create_app`，可简写为：

```bash
flask db upgrade
```

### 6. 启动服务

**开发模式**（带调试、自动重载）：

```bash
python run.py
```

默认监听 `http://127.0.0.1:5000`。

**生产方式**（本地用 Gunicorn 多进程）：

```bash
gunicorn -w 4 -b 127.0.0.1:5000 wsgi:app
```

### 本地运行常见问题

- **`ValueError: DATABASE_URL 环境变量未设置`**  
  确保项目根目录存在 `.env`，且其中已填写 `DATABASE_URL=...`（可参考 `.env.example`）。若在虚拟环境外运行，请先 `conda activate flask-app` 再执行命令。

- **`ValueError: JWT_SECRET_KEY / OPENWEATHER_API_KEY 未设置`**  
  在 `.env` 中补全 `JWT_SECRET_KEY`、`JWT_REFRESH_SECRET_KEY` 和 `OPENWEATHER_API_KEY`。

- **`flask: command not found`**  
  先激活 conda 环境（`conda activate flask-app`），或使用 `python -m flask --app app:create_app db upgrade`。

- **数据库连接失败**  
  检查 MySQL 是否已启动、数据库是否已创建、`DATABASE_URL` 中的主机/端口/用户名/密码/库名是否正确。

---

## 二、Docker 运行

容器启动后会先执行 `flask db upgrade`，再启动 Gunicorn（`wsgi:app`）。

**构建镜像：**
```bash
docker build -t flask-app .
```

**运行 Flask 应用：**
```bash
docker run --rm --env-file .env -p 5000:5000 flask-app
```

**加入 Docker 网络（生产环境推荐）：**
```bash
# 先创建网络（如尚未创建）
docker network create flask-app

# 运行时加入网络
docker run -d --name flask-app --network flask-app --env-file .env -p 5000:5000 flask-app
```

需在镜像同目录准备 `.env`（含 `DATABASE_URL`、`SECRET_KEY` 等），或改用 `-e DATABASE_URL=...` 传环境变量。

---

## 三、API 示例

### 用户注册接口

```bash
curl -X POST http://127.0.0.1:5000/api/users/register \
  -H "Content-Type: application/json" \
  -d '{
    "username": "alice_01",
    "email": "alice@example.com",
    "password": "password123",
    "avatar_url": "https://example.com/avatar.png"
  }'
```

---

## 四、Jenkins CI/CD

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
