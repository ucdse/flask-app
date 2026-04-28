# 🚀 Dublin Bikes Flask App

[🌐 English](./README.md) | **中文**

[![Python](https://img.shields.io/badge/Python-3.12-blue.svg)](https://www.python.org/)
[![Flask](https://img.shields.io/badge/Flask-3.1-green.svg)](https://flask.palletsprojects.com/)
[![Docker](https://img.shields.io/badge/Docker-Ready-blue.svg)](https://www.docker.com/)
[![Jenkins CI](https://img.shields.io/badge/Jenkins-CI/CD-red.svg)](https://www.jenkins.io/)

**Dublin Bikes Flask App** 是一个 ✨ 功能丰富 ✨ 的都柏林公共自行车共享系统 Flask Web 后端。从原始 `1st-flask-proj` 项目中提取（不含爬虫），与同仓库中的配套爬虫共享同一数据库（如 `station`、`availability` 等表）。数据库迁移由本项目维护；爬虫主要写入站点和可用性数据，而本应用还使用 `user`、`weather_forecast`、`sessions` 和 `message_store` 表。

---

## 📋 目录

- [✨ 功能特性](#-功能特性)
- [📁 项目结构](#-项目结构)
- [🚀 快速开始](#-快速开始)
  - [🔧 前置条件](#-前置条件)
  - [📦 安装](#-安装)
  - [⚙️ 配置](#%EF%B8%8F-配置)
- [💻 使用方法](#-使用方法)
  - [本地运行（不使用 Docker）](#本地运行不使用-docker)
  - [使用 Docker 运行](#使用-docker-运行)
  - [🔧 常见问题](#-常见问题)
- [📡 API 示例](#-api-示例)
- [🧪 测试](#-测试)
  - [测试目录结构](#测试目录结构)
  - [安装测试依赖](#安装测试依赖)
  - [运行测试](#运行测试)
  - [查看测试覆盖率](#查看测试覆盖率)
  - [测试设计说明](#测试设计说明)
- [🔄 CI/CD（Jenkins）](#-cicd-jenkins)
- [🤝 贡献指南](#-贡献指南)
- [📝 许可证](#-许可证)
- [📧 联系方式](#-联系方式)

---

## ✨ 功能特性

- **🔐 用户认证**：注册、登录（JWT）、邮箱验证、令牌刷新
- **🚲 站点与可用性**：查询站点、可用性数据及全站最新状态
- **🤖 机器学习预测**：基于决策树模型的自行车可用性预测
- **🌤️ 天气预报**：通过 OpenWeatherMap API 获取实时天气数据
- **🗺️ 路线规划**：结合 Google Maps Geocoding 的服务端路线计算
- **💬 AI 聊天**：基于阿里云通义千问的智能聊天机器人（支持 SSE 流式响应）
- **🐳 Docker 支持**：生产级容器化，启动时自动执行数据库迁移
- **🔄 CI/CD 流水线**：完整的 Jenkins 流水线，包含语法检查、测试、Docker 构建和 EC2 部署

---

## 📁 项目结构

| 路径 | 说明 |
|------|------|
| `app/` | 主应用包：`api/` 路由、`models/` ORM、`services/` 业务逻辑、`contracts/` Pydantic 请求/响应 DTO、`schemas/` 旧版验证器、`utils/` 工具函数 |
| `config.py` | 配置文件（从环境变量读取；缺少必填项时导入会抛出 `ValueError`） |
| `run.py` | 本地开发入口（`python run.py`） |
| `wsgi.py` | WSGI 入口（Gunicorn / Docker 使用） |
| `entrypoint.sh` | Docker 入口脚本：先执行 `flask db upgrade`，再启动 Gunicorn（详见 `Dockerfile`） |
| `migrations/` | Flask-Migrate 数据库迁移文件 |
| `machine_learning/` | 训练笔记本和生产 `.pkl` 模型（预测接口依赖此模型；CI 从 Hugging Face 拉取） |
| `templates/` | 少量 HTML 模板（如邮件相关） |
| `Jenkinsfile` | Jenkins 流水线（语法检查 → 测试 → Docker 镜像 → 可选部署） |
| `requirements.txt` | 生产/运行时 Python 依赖（**不含** pytest；详见测试章节） |

---

## 🚀 快速开始

### 🔧 前置条件

- **Anaconda 或 Miniconda**：已安装 [Anaconda](https://www.anaconda.com/) 或 [Miniconda](https://docs.conda.io/en/latest/miniconda.html)
- **Python**：3.10+（推荐 3.12，与 Docker 镜像一致），由 conda 环境提供
- **数据库**：MySQL（或任何兼容 `DATABASE_URL` 的数据库），需提前创建
- **可选**：可用的 SMTP 配置，用于发送邮箱验证码；否则验证码仅打印到控制台

### 📦 安装

1. **克隆仓库**：

```bash
git clone https://github.com/ucdse/flask-app.git
cd flask-app
```

2. **创建并激活 conda 虚拟环境**（推荐）：

```bash
# 创建虚拟环境（指定 Python 版本，如 3.12）
conda create -n flask-app python=3.12 -y

# 激活虚拟环境
# macOS / Linux:
conda activate flask-app
# Windows (CMD / PowerShell):
# conda activate flask-app
```

激活后，终端提示符将显示 `(flask-app)`。退出环境请使用 `conda deactivate`。

3. **安装依赖**：

```bash
pip install -r requirements.txt
```

### ⚙️ 配置

复制示例文件并按需编辑：

```bash
cp .env.example .env
```

> **注意**：`.env.example` 包含与爬虫模板共享的 `JCDECAUX_*` 和 `SCRAPE_INTERVAL_SECONDS` 变量。运行本 Flask 应用时可以**忽略**这些变量。

编辑 `.env`。以下变量为**必填**（缺少时 `config.py` 会抛出 `ValueError`）：

| 变量 | 说明 |
|------|------|
| `DATABASE_URL` | 数据库连接 URL，如 `mysql+pymysql://user:password@localhost:3306/dbname` |
| `JWT_SECRET_KEY` | JWT Access Token 签名密钥 |
| `JWT_REFRESH_SECRET_KEY` | JWT Refresh Token 签名密钥 |
| `OPENWEATHER_API_KEY` | OpenWeatherMap API 密钥（[在此申请](https://openweathermap.org/api)） |

**强烈建议 / 生产环境**：设置 `SECRET_KEY`（Flask 会话等使用）。虽非导入时强制要求，但缺少会降低安全性。

**可选**变量（有默认值或可省略）：

| 变量 | 说明 |
|------|------|
| `OPENWEATHER_API_BASE_URL` | 默认值：`https://api.openweathermap.org/data/3.0/onecall` |
| `GOOGLE_MAPS_API_KEY` | `/api/journey/plan` 地址文本地理编码所需；仅坐标模式无需此项但会打印警告 |
| `ALIYUN_API_KEY` | AI 聊天接口运行时所需 |
| 邮件 / `FRONTEND_BASE_URL` | 详见 `.env.example` 注释 |

如需直接使用 `flask db upgrade` 而不加 `--app`，在 `.env` 中添加：

```bash
FLASK_APP=app:create_app
```

---

## 💻 使用方法

### 本地运行（不使用 Docker）

**1. 执行数据库迁移**（共享数据库时，须在本项目中先于爬虫执行）：

```bash
flask --app app:create_app db upgrade
```

或，若 `.env` 中已设置 `FLASK_APP=app:create_app`：

```bash
flask db upgrade
```

**2. 启动服务器**：

**开发模式**（带调试和自动重载）：

```bash
python run.py
```

默认监听 `http://127.0.0.1:5000`。

**生产模式**（本地 Gunicorn 多进程 + 多线程，适合 SSE 流式响应和高并发）：

```bash
gunicorn -w 4 -b 127.0.0.1:5000 --worker-class gthread --threads 4 --timeout 120 wsgi:app
```

### 使用 Docker 运行

容器入口脚本（`entrypoint.sh`）先执行 `flask db upgrade`，再启动 Gunicorn（`wsgi:app`，使用 `--worker-class gthread` 和 `--preload`；具体进程数/绑定地址详见脚本）。

**构建镜像：**

```bash
docker build -t flask-app .
```

**运行 Flask 应用：**

```bash
docker run --rm --env-file .env -p 5000:5000 flask-app
```

**加入 Docker 网络**（生产环境推荐）：

```bash
# 创建网络（如尚未创建）
docker network create flask-app

# 使用网络运行
docker run -d --name flask-app --network flask-app --env-file .env -p 5000:5000 flask-app
```

项目根目录下须存在 `.env` 文件（包含 `DATABASE_URL`、`SECRET_KEY` 等），或使用 `-e DATABASE_URL=...` 直接传递环境变量。

### 🔧 常见问题

| 错误 | 解决方案 |
|------|----------|
| `ValueError: DATABASE_URL environment variable is not set` | 确保项目根目录存在 `.env` 文件且包含 `DATABASE_URL=...`（参考 `.env.example`）。先激活 conda 环境。 |
| `ValueError: JWT_SECRET_KEY / OPENWEATHER_API_KEY is not set` | 在 `.env` 中添加 `JWT_SECRET_KEY`、`JWT_REFRESH_SECRET_KEY` 和 `OPENWEATHER_API_KEY`。 |
| `flask: command not found` | 激活 conda 环境（`conda activate flask-app`），或使用 `python -m flask --app app:create_app db upgrade`。 |
| 数据库连接失败 | 检查 MySQL 是否运行、数据库是否已创建，以及 `DATABASE_URL` 中的主机/端口/用户/密码/数据库名是否正确。 |

---

## 📡 API 示例

### 用户注册

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

### 其他可用接口

| 方法 | 接口 | 需要认证 | 说明 |
|------|------|----------|------|
| `GET` | `/api/stations/` | 否 | 列出所有站点 |
| `GET` | `/api/stations/status` | 否 | 全站最新状态 |
| `GET` | `/api/weather` | 否 | 天气预报 |
| `POST` | `/api/journey/plan` | 否 | 路线规划 |
| `POST` | `/api/chat` | 是 | AI 聊天（标准响应） |
| `POST` | `/api/chat/stream` | 是 | AI 聊天（SSE 流式响应） |

> 聊天接口需在请求头中携带 `Authorization: Bearer <access_token>`。

完整 API 定义请查看 `app/api/`。

---

## 🧪 测试

本项目使用 **pytest** 框架。所有测试位于 `tests/` 目录；当前 `app` 包语句覆盖率约为 **97%**（由 `pytest --cov=app` 测得，以实际代码为准）。测试使用 **SQLite 内存数据库**，无需运行 MySQL 实例。`conftest.py` 在导入应用前注入测试环境变量，因此测试无需 `.env` 文件。

### 测试目录结构

```
tests/
├── conftest.py                      # 共享 fixtures（测试应用、数据库、工厂函数、认证头）
├── test_utils.py                    # 工具函数：calculateDistance、api_retry
├── test_contracts.py                # Pydantic DTO / VO 契约验证
├── test_schemas.py                  # 旧版 user_schema.py 验证器测试
├── test_user_service.py             # 用户服务逻辑（注册、登录、验证码、令牌刷新等）
├── test_station_service.py          # 站点查询服务
├── test_weather_service.py          # 天气预报服务
├── test_email_utils.py              # 邮件工具函数
├── test_user_routes.py              # 用户路由 HTTP 层（注册、登录、激活、令牌、/me 等）
├── test_station_routes.py           # 站点路由 HTTP 层
├── test_weather_routes.py           # 天气路由 HTTP 层
├── test_weather_routes_validation.py # 天气路由参数验证辅助
├── test_journey_routes.py           # 路线规划路由 HTTP 层
├── test_journey_service.py          # 路线规划服务：最优路线计算
├── test_journey_service_matrix.py   # 路线规划服务：Google Maps 矩阵时长
├── test_chat_routes.py              # 聊天路由 HTTP 层（SSE 流式 & 标准响应）
├── test_chat_service.py             # 聊天服务：对话消息、会话 ID 生成
├── test_chat_service_llm.py         # 聊天服务：LLM 调用路径（通义千问 / OpenAI）
└── test_prediction_service.py       # 可用性预测服务（决策树模型）
```

### 安装测试依赖

`requirements.txt` 面向运行中的 Web 服务，**不含** `pytest` / `pytest-cov`。请在本地或 CI 中运行测试前安装：

```bash
pip install pytest pytest-cov
```

### 运行测试

确保虚拟环境已激活，然后在项目根目录执行：

**运行所有测试：**

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

**显示详细输出（每个测试用例名称）：**

```bash
pytest tests/ -v
```

**显示打印输出（用于调试）：**

```bash
pytest tests/ -s
```

### 查看测试覆盖率

**终端输出（含未覆盖行号）：**

```bash
pytest tests/ --cov=app --cov-report=term-missing
```

**生成 HTML 覆盖率报告**（推荐，可逐行查看）：

```bash
pytest tests/ --cov=app --cov-report=html
open htmlcov/index.html          # macOS
# xdg-open htmlcov/index.html    # Linux
# start htmlcov/index.html        # Windows
```

**生成 XML 报告**（供 CI/CD 使用）：

```bash
pytest tests/ --cov=app --cov-report=xml
```

### 测试设计说明

**数据库隔离**

所有测试使用 SQLite 内存数据库（`sqlite:///:memory:`）。每个测试结束后，`db` fixture 自动回滚并清空所有表——测试完全隔离，绝不会影响生产 MySQL 数据库。

**外部依赖 Mock**

| 外部服务 | Mock 方式 |
|----------|-----------|
| Google Maps API | 在 `conftest.py` 中 Patch——`googlemaps.Client` 返回 `MagicMock` |
| 通义千问 / OpenAI LLM | 每个 LLM 测试中单独 Patch——`openai.OpenAI` |
| SMTP 邮件发送 | Flask 配置 `MAIL_SUPPRESS_SEND=True`；发送执行器单独 Patch |

**共享 Fixtures（`conftest.py`）**

| Fixture | 作用域 | 说明 |
|---------|--------|------|
| `app` | session | 创建测试 Flask 应用实例（使用内存数据库） |
| `db` | function | 提供数据库会话；测试后自动清理 |
| `client` | function | Flask 测试客户端，用于 HTTP 路由测试 |
| `make_user` | function | 工厂函数：创建并持久化 User 对象 |
| `make_station` | function | 工厂函数：创建并持久化 Station 对象 |
| `make_availability` | function | 工厂函数：创建并持久化 Availability 对象 |
| `make_weather_forecast` | function | 工厂函数：创建并持久化 WeatherForecast 对象 |
| `auth_headers` | function | 返回元组 `(user, headers)`，其中 `headers` 包含 `Authorization: Bearer …` |

**测试命名约定**

测试函数遵循 `test_<操作>_<条件>_<预期结果>` 模式，例如：

```
test_register_success
test_register_duplicate_email_returns_409
test_login_wrong_password_returns_401
test_get_stations_empty_db_returns_empty_list
```

---

## 🔄 CI/CD（Jenkins）

本项目使用 Kubernetes Agent + Jenkins 流水线（详见仓库根目录 `Jenkinsfile`）。

**流水线阶段：**

1. **拉取代码** — 从 Git 仓库检出
2. **Python 语法检查** — 创建虚拟环境，安装依赖，`py_compile` 验证
3. **运行测试** — `pytest tests/`，输出 JUnit 报告
4. **下载 ML 模型** — 从 Hugging Face 拉取 `bike_availability_model.pkl` 和 `model_features.pkl` 至 `machine_learning/`（Docker 镜像中的预测接口依赖此模型）
5. **构建并推送 Docker 镜像** — `docker build`；当 `PUSH_IMAGE` 或 `DEPLOY_TO_EC2` 为 `true` 时推送
6. **部署至 EC2** — 当分支为 **`main`** 且**非** Pull Request 构建时，拉取镜像至 EC2 并通过 `docker run` 启动（默认 `--network flask-app`；环境文件路径由流水线参数设置）

**Jenkins 所需凭据：**

| 凭据 ID | 类型 | 说明 |
|---------|------|------|
| `docker-hub-credentials` | 用户名/密码 | Docker Hub 登录凭据 |
| `huggingface-token` | 密文 | 用于下载预测模型的 HF Token |
| `aws-ec2` | 密文 | EC2 服务器地址 |
| `server-ssh-key` | SSH 私钥 | EC2 SSH 私钥（凭据 ID 可通过参数配置） |
| `flask-prod.env` | 密文件 | 生产环境 `.env` 文件 |

**EC2 部署准备：**

在 EC2 服务器上执行：

```bash
# 创建 Docker 网络
docker network create flask-app

# 创建 .env 目录（Jenkins 将自动上传 .env 文件至此路径）
mkdir -p /opt/flask-app
```

---

## 🤝 贡献指南

欢迎贡献！🎉 如需贡献，请遵循以下步骤：

1. **Fork** 本仓库。
2. **创建新分支**：

```bash
git checkout -b feature/your-feature-name
```

3. **提交更改**：

```bash
git commit -m "Add your awesome feature"
```

4. **推送至分支**：

```bash
git push origin feature/your-feature-name
```

5. **发起 Pull Request** 🚀

---

## 📝 许可证

本项目基于 **MIT 许可证** 授权。详见 [LICENSE](./LICENSE) 文件。

---

## 📧 联系方式

如有任何问题或反馈，欢迎联系：

- **GitHub Issues**：[提交 Issue](https://github.com/ucdse/flask-app/issues) 🐛
- **仓库地址**：[https://github.com/ucdse/flask-app](https://github.com/ucdse/flask-app)

---

Made with ❤️ by the [UCD Software Engineering](https://github.com/ucdse) team. 祝编码愉快！🎉