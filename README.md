# flask-app

从原项目 `1st-flask-proj` 抽离出的 Flask Web 后端（不包含 scraper）。与同仓下的 **scraper** 共用同一数据库（如 `station`、`availability` 等表），**数据库迁移在本项目维护**；scraper 主要写入站点与可用性数据，本应用还使用 `user`、`weather_forecast`、`sessions`、`message_store` 等表。

主要功能包括：用户注册/登录（JWT）、邮箱验证、站点与可用性查询、全站最新状态、**可用车数量预测**（随机森林模型）、天气预报、**路径规划**（Google Maps Geocoding + 服务端路线计算）、**AI 聊天**（阿里云 Qwen，支持 SSE 流式）等。

### 项目结构概览

| 路径 | 说明 |
|------|------|
| `app/` | 应用主包：`api/` 路由、`models/` ORM、`services/` 业务、`contracts/` Pydantic 请求与响应、`schemas/` 遗留校验、`utils/` 工具 |
| `config.py` | 配置（从环境变量读取；缺少数个必填项会在导入时抛错，见下文） |
| `run.py` | 本地开发入口（`python run.py`） |
| `wsgi.py` | WSGI 入口（Gunicorn / Docker 使用） |
| `entrypoint.sh` | Docker 入口：先 `flask db upgrade`，再启动 Gunicorn（见 `Dockerfile`） |
| `migrations/` | Flask-Migrate 数据库迁移 |
| `machine_learning/` | 训练 notebook 与线上 `.pkl` 模型（预测接口依赖，CI 会从 Hugging Face 拉取） |
| `templates/` | 少量 HTML 模板（如邮件相关） |
| `Jenkinsfile` | Jenkins 流水线（语法检查、测试、镜像、可选部署） |
| `requirements.txt` | 生产/运行期 Python 依赖（**不含** pytest，见测试章节） |

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

`.env.example` 中含 **JCDecaux / scraper** 等变量，仅供与同仓 scraper 共用一份模板时使用；**本 Flask 应用运行时可忽略** `JCDECAUX_*`、`SCRAPE_INTERVAL_SECONDS` 等与采集相关的项。

编辑 `.env`。`config.py` 在导入时会**强制要求**以下变量已设置（否则会 `ValueError`）：

| 变量名 | 说明 |
|--------|------|
| `DATABASE_URL` | 数据库连接 URL，如 `mysql+pymysql://user:password@localhost:3306/dbname` |
| `JWT_SECRET_KEY` | JWT Access Token 签名密钥 |
| `JWT_REFRESH_SECRET_KEY` | JWT Refresh Token 签名密钥 |
| `OPENWEATHER_API_KEY` | OpenWeatherMap API Key（[官网](https://openweathermap.org/api) 申请） |

**强烈建议 / 生产环境**：配置 `SECRET_KEY`（Flask 会话等）；虽未在 `config.py` 导入阶段校验，但缺失会降低安全性。

**可选**（有默认值或可缺省，按需配置）：

| 变量名 | 说明 |
|--------|------|
| `OPENWEATHER_API_BASE_URL` | 默认 `https://api.openweathermap.org/data/3.0/onecall` |
| `GOOGLE_MAPS_API_KEY` | `/api/journey/plan` 使用地址文本地理编码时必填；仅坐标模式可不配，但未配置时模块会打印警告 |
| `ALIYUN_API_KEY` | AI 聊天接口运行时所需 |
| 邮件 / `FRONTEND_BASE_URL` | 见 `.env.example` 注释 |

若需在终端直接使用 `flask db upgrade` 而不带 `--app`，可在 `.env` 中增加一行：

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

镜像启动由 `entrypoint.sh` 执行：先 `flask db upgrade`，再启动 Gunicorn（`wsgi:app`，`--worker-class gthread`、`--preload` 等见脚本）。与本节下方「本地 Gunicorn」示例中的 worker 数量 / 绑定地址可能不同，以 `entrypoint.sh` 为准。

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

其他蓝图前缀（便于对照代码）：`GET /api/stations/`、`GET /api/stations/status`、`GET /api/weather`、`POST /api/journey/plan`、`POST /api/chat`、`POST /api/chat/stream`（聊天需 `Authorization: Bearer <access_token>`）。完整定义见 `app/api/`。

---

## 四、单元测试

项目使用 **pytest** 框架，所有测试位于 `tests/` 目录；当前 `app` 包语句覆盖率约 **97%**（以 `pytest --cov=app` 为准，会随代码变动）。测试运行时使用 **SQLite 内存数据库**，无需启动 MySQL；`conftest.py` 会在导入应用前注入测试用环境变量，无需自备 `.env`。

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
├── test_user_routes.py              # 用户路由 HTTP 层（注册、登录、激活、Token、/me 等）
├── test_station_routes.py           # 站点路由 HTTP 层
├── test_weather_routes.py           # 天气路由 HTTP 层
├── test_weather_routes_validation.py # 天气路由参数校验辅助函数
├── test_journey_routes.py           # 行程路由 HTTP 层
├── test_journey_service.py          # 行程服务：最优路线计算
├── test_journey_service_matrix.py   # 行程服务：Google Maps 矩阵时长
├── test_chat_routes.py              # 聊天路由 HTTP 层（SSE 流式 & 普通响应）
├── test_chat_service.py             # 聊天服务：会话消息、session ID 生成
├── test_chat_service_llm.py         # 聊天服务：LLM 调用路径（Qwen / OpenAI）
└── test_prediction_service.py       # 可用性预测服务（随机森林模型）
```

### 2. 安装测试依赖

`requirements.txt` 面向运行中的 Web 服务，**未包含** `pytest` / `pytest-cov`。本地或 CI 跑测试前请先安装：

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
| `auth_headers` | function | 返回元组 `(user, headers)`，`headers` 含 `Authorization: Bearer …` |

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

项目使用 Kubernetes Agent + Jenkins Pipeline（见仓库根目录 `Jenkinsfile`）。

**流程说明（与 `Jenkinsfile` 阶段一致）：**

1. **拉取代码** - 从 Git 仓库拉取当前构建的 SCM 版本  
2. **Python 语法检查** - 创建 venv，安装依赖，`py_compile` 校验  
3. **执行测试** - `pytest tests/`，产出 JUnit 报告  
4. **下载 ML 模型** - 使用凭据从 Hugging Face 拉取 `bike_availability_model.pkl`、`model_features.pkl` 到 `machine_learning/`（供镜像内预测接口使用）  
5. **构建并推送镜像** - `docker build`，按参数决定是否 `docker push`（`PUSH_IMAGE` 或 `DEPLOY_TO_EC2` 为 true 时会推送）  
6. **部署到 EC2** - 当分支为 **`main`** 且**非** Pull Request 构建时，将镜像拉取到 EC2 并以 `docker run` 启动（默认 `--network flask-app`，环境文件路径见流水线参数）

**Jenkins 需要的凭据（与 `Jenkinsfile` / 参数默认值对应）：**

| 凭据 ID                  | 类型               | 说明                     |
|--------------------------|-------------------|--------------------------|
| `docker-hub-credentials` | Username/Password | Docker Hub 登录凭据       |
| `huggingface-token`      | Secret string     | 下载预测模型用 HF Token   |
| `aws-ec2`                | Secret text       | EC2 服务器地址            |
| `server-ssh-key`         | SSH Private Key   | EC2 SSH 私钥（参数可改凭据 ID） |
| `flask-prod.env`         | Secret file       | 生产环境 .env 文件        |

**EC2 部署前准备：**

在 EC2 服务器上执行：
```bash
# 创建 Docker 网络
docker network create flask-app

# 创建 .env 存放目录（Jenkins 会自动上传 .env 文件到此路径）
mkdir -p /opt/flask-app
```
