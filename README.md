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

**生产方式**（本地用 Gunicorn 多进程 + 多线程，适合 SSE 流式输出与高并发）：

```bash
gunicorn -w 4 -b 127.0.0.1:5000 --worker-class gthread --threads 4 --timeout 120 wsgi:app
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

## 四、单元测试

项目使用 **pytest** 框架，所有测试位于 `tests/` 目录，覆盖率 **97%**（目标 80%+）。测试运行时使用 **SQLite 内存数据库**，无需启动 MySQL 或配置任何外部服务。

### 1. 目录结构

```
tests/
├── conftest.py                      # 共享 fixtures（测试应用、数据库、工厂函数、鉴权头）
├── test_utils.py                    # 工具函数：calculateDistance、api_retry
├── test_contracts.py                # Pydantic DTO / VO 契约校验
├── test_schemas.py                  # 遗留 user_schema.py 校验器
├── test_user_service.py             # 用户服务业务逻辑（注册、登录、验证码、刷新 Token 等）
├── test_station_service.py          # 站点查询服务
├── test_weather_service.py          # 天气预报服务
├── test_email_utils.py              # 邮件工具函数
├── test_user_routes.py              # 用户路由 HTTP 层（注册、登录、修改密码等端点）
├── test_station_routes.py           # 站点路由 HTTP 层
├── test_weather_routes.py           # 天气路由 HTTP 层
├── test_weather_routes_validation.py# 天气路由参数校验辅助函数
├── test_journey_routes.py           # 行程路由 HTTP 层
├── test_journey_service.py          # 行程服务：最优路线计算
├── test_journey_service_matrix.py   # 行程服务：Google Maps 矩阵时长
├── test_chat_routes.py              # 聊天路由 HTTP 层（SSE 流式 & 普通响应）
├── test_chat_service.py             # 聊天服务：会话消息、session ID 生成
├── test_chat_service_llm.py         # 聊天服务：LLM 调用路径（Qwen / OpenAI）
└── test_prediction_service.py       # 可用性预测服务（随机森林模型）
```

### 2. 安装测试依赖

测试依赖已包含在 `requirements.txt` 中。若单独安装：

```bash
pip install pytest pytest-cov
```

### 3. 执行测试

确保已激活虚拟环境，在项目根目录执行：

**运行全部测试：**

```bash
pytest tests/
```

**运行单个测试文件：**

```bash
pytest tests/test_user_routes.py
```

**运行单个测试函数：**

```bash
pytest tests/test_user_routes.py::test_register_success
```

**显示详细输出（每条测试用例名称）：**

```bash
pytest tests/ -v
```

**显示 print 输出（调试时使用）：**

```bash
pytest tests/ -s
```

### 4. 查看测试覆盖率

**终端输出覆盖率摘要（含未覆盖行号）：**

```bash
pytest tests/ --cov=app --cov-report=term-missing
```

**生成 HTML 覆盖率报告（推荐，可视化查看每行覆盖情况）：**

```bash
pytest tests/ --cov=app --cov-report=html
open htmlcov/index.html   # macOS
# xdg-open htmlcov/index.html  # Linux
# start htmlcov/index.html     # Windows
```

**生成 XML 报告（供 CI/CD 工具消费）：**

```bash
pytest tests/ --cov=app --cov-report=xml
```

### 5. 测试设计说明

**数据库隔离**

所有测试使用 SQLite 内存数据库（`sqlite:///:memory:`），每条测试结束后通过 `db` fixture 自动回滚并清空所有表，测试间完全隔离，不会影响生产 MySQL 数据库。

**外部依赖 Mock**

| 外部服务 | Mock 方式 |
|----------|-----------|
| Google Maps API | 在 `conftest.py` 中 patch `googlemaps.Client`，返回 `MagicMock` |
| Qwen / OpenAI LLM | 在各 LLM 测试中 patch `openai.OpenAI` |
| SMTP 邮件发送 | Flask 配置 `MAIL_SUPPRESS_SEND=True`，发送 executor 另行 patch |

**共享 Fixtures（`conftest.py`）**

| Fixture | 作用域 | 说明 |
|---------|--------|------|
| `app` | session | 创建测试用 Flask 应用实例（含内存数据库） |
| `db` | function | 提供数据库会话，测试后自动清理 |
| `client` | function | Flask 测试客户端，用于 HTTP 路由测试 |
| `make_user` | function | 工厂函数：创建并持久化 User 对象 |
| `make_station` | function | 工厂函数：创建并持久化 Station 对象 |
| `make_availability` | function | 工厂函数：创建并持久化 Availability 对象 |
| `make_weather_forecast` | function | 工厂函数：创建并持久化 WeatherForecast 对象 |
| `auth_headers` | function | 返回已登录用户和 JWT Bearer Token 请求头 |

**测试命名约定**

测试函数遵循 `test_<操作>_<条件>_<期望结果>` 的命名规则，例如：

```
test_register_success
test_register_duplicate_email_returns_409
test_login_wrong_password_returns_401
test_get_stations_empty_db_returns_empty_list
```

---

## 五、Jenkins CI/CD

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
