# 🚀 Dublin Bikes Flask App

[![Python](https://img.shields.io/badge/Python-3.12-blue.svg)](https://www.python.org/)
[![Flask](https://img.shields.io/badge/Flask-3.1-green.svg)](https://flask.palletsprojects.com/)
[![Docker](https://img.shields.io/badge/Docker-Ready-blue.svg)](https://www.docker.com/)
[![Jenkins CI](https://img.shields.io/badge/Jenkins-CI/CD-red.svg)](https://www.jenkins.io/)

**Dublin Bikes Flask App** is a ✨ feature-rich ✨ Flask web backend for the Dublin public bike sharing system. Extracted from the original `1st-flask-proj` project (excluding the scraper), it shares the same database with the companion scraper in the same repository (tables such as `station`, `availability`, etc.). Database migrations are maintained in this project; the scraper primarily writes station and availability data, while this application also uses `user`, `weather_forecast`, `sessions`, and `message_store` tables.

---

## 📋 Table of Contents

- [✨ Features](#-features)
- [📁 Project Structure](#-project-structure)
- [🚀 Getting Started](#-getting-started)
  - [🔧 Prerequisites](#-prerequisites)
  - [📦 Installation](#-installation)
  - [⚙️ Configuration](#%EF%B8%8F-configuration)
- [💻 Usage](#-usage)
  - [Run Locally (without Docker)](#run-locally-without-docker)
  - [Run with Docker](#run-with-docker)
  - [🔧 Troubleshooting](#-troubleshooting)
- [📡 API Examples](#-api-examples)
- [🧪 Testing](#-testing)
  - [Test Directory Structure](#test-directory-structure)
  - [Install Test Dependencies](#install-test-dependencies)
  - [Run Tests](#run-tests)
  - [View Test Coverage](#view-test-coverage)
  - [Test Design Notes](#test-design-notes)
- [🔄 CI/CD (Jenkins)](#-cicd-jenkins)
- [🤝 Contributing](#-contributing)
- [📝 License](#-license)
- [📧 Contact](#-contact)

---

## ✨ Features

- **🔐 User Authentication**: Registration, login (JWT), email verification, and token refresh
- **🚲 Station & Availability**: Query bike stations, availability data, and latest status across all stations
- **🤖 ML Prediction**: Bike availability prediction powered by a Random Forest model
- **🌤️ Weather Forecast**: Real-time weather data via OpenWeatherMap API
- **🗺️ Route Planning**: Server-side route calculation with Google Maps Geocoding
- **💬 AI Chat**: Intelligent chatbot powered by Alibaba Cloud Qwen (supports SSE streaming)
- **🐳 Docker Support**: Production-ready containerisation with auto-migration on startup
- **🔄 CI/CD Pipeline**: Full Jenkins pipeline with syntax checks, testing, Docker build, and EC2 deployment

---

## 📁 Project Structure

| Path | Description |
|------|-------------|
| `app/` | Main application package: `api/` routes, `models/` ORM, `services/` business logic, `contracts/` Pydantic request/response DTOs, `schemas/` legacy validators, `utils/` utilities |
| `config.py` | Configuration (reads from environment variables; missing required keys raise `ValueError` on import) |
| `run.py` | Local development entry point (`python run.py`) |
| `wsgi.py` | WSGI entry point (used by Gunicorn / Docker) |
| `entrypoint.sh` | Docker entrypoint: runs `flask db upgrade` first, then starts Gunicorn (see `Dockerfile`) |
| `migrations/` | Flask-Migrate database migrations |
| `machine_learning/` | Training notebook and production `.pkl` model (prediction endpoint depends on it; CI pulls from Hugging Face) |
| `templates/` | A small number of HTML templates (e.g. email-related) |
| `Jenkinsfile` | Jenkins pipeline (syntax check → tests → Docker image → optional deploy) |
| `requirements.txt` | Production/runtime Python dependencies (**does not** include pytest; see Testing section) |

---

## 🚀 Getting Started

### 🔧 Prerequisites

- **Anaconda or Miniconda**: [Anaconda](https://www.anaconda.com/) or [Miniconda](https://docs.conda.io/en/latest/miniconda.html) installed
- **Python**: 3.10+ (3.12 recommended, consistent with the Docker image), provided by conda environment
- **Database**: MySQL (or any database compatible with `DATABASE_URL`), created beforehand
- **Optional**: Working SMTP config for email verification codes; otherwise codes are printed to the console only

### 📦 Installation

1. **Clone the repository**:

```bash
git clone https://github.com/ucdse/flask-app.git
cd flask-app
```

2. **Create and activate a conda virtual environment** (recommended):

```bash
# Create virtual environment (specify Python version, e.g. 3.12)
conda create -n flask-app python=3.12 -y

# Activate the virtual environment
# macOS / Linux:
conda activate flask-app
# Windows (CMD / PowerShell):
# conda activate flask-app
```

After activation, your terminal prompt will show `(flask-app)`. To exit the environment, use `conda deactivate`.

3. **Install dependencies**:

```bash
pip install -r requirements.txt
```

### ⚙️ Configuration

Copy the example file and edit as needed:

```bash
cp .env.example .env
```

> **Note**: `.env.example` contains `JCDECAUX_*` and `SCRAPE_INTERVAL_SECONDS` variables shared with the scraper template. These can be **ignored** when running this Flask application.

Edit `.env`. The following variables are **required** (`config.py` will raise `ValueError` if missing):

| Variable | Description |
|----------|-------------|
| `DATABASE_URL` | Database connection URL, e.g. `mysql+pymysql://user:password@localhost:3306/dbname` |
| `JWT_SECRET_KEY` | JWT Access Token signing key |
| `JWT_REFRESH_SECRET_KEY` | JWT Refresh Token signing key |
| `OPENWEATHER_API_KEY` | OpenWeatherMap API key ([apply here](https://openweathermap.org/api)) |

**Strongly recommended / Production**: Set `SECRET_KEY` (used by Flask sessions etc.). Although not enforced at import time, missing it reduces security.

**Optional** variables (have defaults or can be omitted):

| Variable | Description |
|----------|-------------|
| `OPENWEATHER_API_BASE_URL` | Default: `https://api.openweathermap.org/data/3.0/onecall` |
| `GOOGLE_MAPS_API_KEY` | Required for `/api/journey/plan` address text geocoding; coordinate-only mode works without it but prints a warning |
| `ALIYUN_API_KEY` | Required by the AI chat endpoint at runtime |
| Mail / `FRONTEND_BASE_URL` | See `.env.example` comments |

To use `flask db upgrade` directly without `--app`, add this line to `.env`:

```bash
FLASK_APP=app:create_app
```

---

## 💻 Usage

### Run Locally (without Docker)

**1. Run database migrations** (must be done in this project before the scraper when sharing a database):

```bash
flask --app app:create_app db upgrade
```

Or, if `FLASK_APP=app:create_app` is set in `.env`:

```bash
flask db upgrade
```

**2. Start the server**:

**Development mode** (with debug and auto-reload):

```bash
python run.py
```

Listens at `http://127.0.0.1:5000` by default.

**Production mode** (local Gunicorn with multi-worker + multi-thread, suitable for SSE streaming and high concurrency):

```bash
gunicorn -w 4 -b 127.0.0.1:5000 --worker-class gthread --threads 4 --timeout 120 wsgi:app
```

### Run with Docker

The container entrypoint (`entrypoint.sh`) runs `flask db upgrade` first, then starts Gunicorn (`wsgi:app` with `--worker-class gthread` and `--preload`; see the script for exact worker count / bind address).

**Build the image:**

```bash
docker build -t flask-app .
```

**Run the Flask application:**

```bash
docker run --rm --env-file .env -p 5000:5000 flask-app
```

**Join a Docker network** (recommended for production):

```bash
# Create the network (if not already created)
docker network create flask-app

# Run with network
docker run -d --name flask-app --network flask-app --env-file .env -p 5000:5000 flask-app
```

A `.env` file (containing `DATABASE_URL`, `SECRET_KEY`, etc.) must be present in the same directory, or use `-e DATABASE_URL=...` to pass environment variables directly.

### 🔧 Troubleshooting

| Error | Solution |
|-------|----------|
| `ValueError: DATABASE_URL environment variable is not set` | Ensure `.env` exists in the project root with `DATABASE_URL=...` (see `.env.example`). Activate the conda environment first. |
| `ValueError: JWT_SECRET_KEY / OPENWEATHER_API_KEY is not set` | Add `JWT_SECRET_KEY`, `JWT_REFRESH_SECRET_KEY`, and `OPENWEATHER_API_KEY` to `.env`. |
| `flask: command not found` | Activate the conda environment (`conda activate flask-app`), or use `python -m flask --app app:create_app db upgrade`. |
| Database connection failure | Check that MySQL is running, the database has been created, and the host/port/user/password/db name in `DATABASE_URL` are correct. |

---

## 📡 API Examples

### User Registration

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

### Other Available Endpoints

| Method | Endpoint | Auth Required | Description |
|--------|----------|--------------|-------------|
| `GET` | `/api/stations/` | No | List all stations |
| `GET` | `/api/stations/status` | No | Latest status across all stations |
| `GET` | `/api/weather` | No | Weather forecast |
| `POST` | `/api/journey/plan` | No | Route planning |
| `POST` | `/api/chat` | Yes | AI chat (standard response) |
| `POST` | `/api/chat/stream` | Yes | AI chat (SSE streaming) |

> Chat endpoints require `Authorization: Bearer <access_token>` header.

For the full API definition, see `app/api/`.

---

## 🧪 Testing

The project uses the **pytest** framework. All tests are in the `tests/` directory; current `app` package statement coverage is approximately **97%** (per `pytest --cov=app`, subject to code changes). Tests run against an **SQLite in-memory database**, so no running MySQL instance is required. `conftest.py` injects test environment variables before importing the app, so no `.env` is needed for testing.

### Test Directory Structure

```
tests/
├── conftest.py                      # Shared fixtures (test app, database, factory functions, auth headers)
├── test_utils.py                    # Utility functions: calculateDistance, api_retry
├── test_contracts.py                # Pydantic DTO / VO contract validation
├── test_schemas.py                  # Legacy user_schema.py validator tests
├── test_user_service.py             # User service logic (register, login, verification code, token refresh, etc.)
├── test_station_service.py          # Station query service
├── test_weather_service.py          # Weather forecast service
├── test_email_utils.py              # Email utility functions
├── test_user_routes.py              # User route HTTP layer (register, login, activate, token, /me, etc.)
├── test_station_routes.py           # Station route HTTP layer
├── test_weather_routes.py           # Weather route HTTP layer
├── test_weather_routes_validation.py # Weather route parameter validation helpers
├── test_journey_routes.py           # Journey route HTTP layer
├── test_journey_service.py          # Journey service: optimal route calculation
├── test_journey_service_matrix.py   # Journey service: Google Maps matrix duration
├── test_chat_routes.py              # Chat route HTTP layer (SSE streaming & standard response)
├── test_chat_service.py             # Chat service: conversation messages, session ID generation
├── test_chat_service_llm.py         # Chat service: LLM call paths (Qwen / OpenAI)
└── test_prediction_service.py       # Availability prediction service (Random Forest model)
```

### Install Test Dependencies

`requirements.txt` targets the running web service and does **not** include `pytest` / `pytest-cov`. Install them before running tests locally or in CI:

```bash
pip install pytest pytest-cov
```

### Run Tests

Ensure the virtual environment is activated, then run from the project root:

**Run all tests:**

```bash
pytest tests/
```

**Run a single test file:**

```bash
pytest tests/test_user_routes.py
```

**Run a single test function:**

```bash
pytest tests/test_user_routes.py::test_register_success
```

**Show verbose output (each test case name):**

```bash
pytest tests/ -v
```

**Show print output (for debugging):**

```bash
pytest tests/ -s
```

### View Test Coverage

**Terminal output with uncovered line numbers:**

```bash
pytest tests/ --cov=app --cov-report=term-missing
```

**Generate HTML coverage report** (recommended for visual per-line inspection):

```bash
pytest tests/ --cov=app --cov-report=html
open htmlcov/index.html          # macOS
# xdg-open htmlcov/index.html    # Linux
# start htmlcov/index.html        # Windows
```

**Generate XML report** (for CI/CD consumption):

```bash
pytest tests/ --cov=app --cov-report=xml
```

### Test Design Notes

**Database Isolation**

All tests use an SQLite in-memory database (`sqlite:///:memory:`). After each test, the `db` fixture automatically rolls back and clears all tables — tests are fully isolated and never affect the production MySQL database.

**External Dependency Mocking**

| External Service | Mock Approach |
|-----------------|---------------|
| Google Maps API | Patched in `conftest.py` — `googlemaps.Client` returns `MagicMock` |
| Qwen / OpenAI LLM | Patched per LLM test — `openai.OpenAI` |
| SMTP Email Sending | Flask config `MAIL_SUPPRESS_SEND=True`; send executor patched separately |

**Shared Fixtures (`conftest.py`)**

| Fixture | Scope | Description |
|---------|-------|-------------|
| `app` | session | Creates test Flask app instance (with in-memory database) |
| `db` | function | Provides database session; auto-cleanup after test |
| `client` | function | Flask test client for HTTP route tests |
| `make_user` | function | Factory function: creates and persists a User object |
| `make_station` | function | Factory function: creates and persists a Station object |
| `make_availability` | function | Factory function: creates and persists an Availability object |
| `make_weather_forecast` | function | Factory function: creates and persists a WeatherForecast object |
| `auth_headers` | function | Returns tuple `(user, headers)` where `headers` contains `Authorization: Bearer …` |

**Test Naming Convention**

Test functions follow the `test_<action>_<condition>_<expected_result>` pattern, for example:

```
test_register_success
test_register_duplicate_email_returns_409
test_login_wrong_password_returns_401
test_get_stations_empty_db_returns_empty_list
```

---

## 🔄 CI/CD (Jenkins)

The project uses a Kubernetes Agent + Jenkins Pipeline (see `Jenkinsfile` in the repository root).

**Pipeline stages:**

1. **Pull Code** — Checkout from the Git repository
2. **Python Syntax Check** — Create venv, install dependencies, `py_compile` validation
3. **Run Tests** — `pytest tests/` with JUnit report output
4. **Download ML Model** — Pull `bike_availability_model.pkl` and `model_features.pkl` from Hugging Face into `machine_learning/` (used by the prediction endpoint in the Docker image)
5. **Build and Push Docker Image** — `docker build`; pushes when `PUSH_IMAGE` or `DEPLOY_TO_EC2` is `true`
6. **Deploy to EC2** — When the branch is **`main`** and **not** a Pull Request build, pulls the image to EC2 and starts it via `docker run` (default `--network flask-app`; env file path set by pipeline parameter)

**Jenkins credentials required:**

| Credential ID | Type | Description |
|---------------|------|-------------|
| `docker-hub-credentials` | Username/Password | Docker Hub login credentials |
| `huggingface-token` | Secret string | HF token for downloading prediction models |
| `aws-ec2` | Secret text | EC2 server address |
| `server-ssh-key` | SSH Private Key | EC2 SSH private key (credential ID configurable via parameter) |
| `flask-prod.env` | Secret file | Production `.env` file |

**EC2 deployment preparation:**

On the EC2 server, run:

```bash
# Create Docker network
docker network create flask-app

# Create .env directory (Jenkins will automatically upload the .env file to this path)
mkdir -p /opt/flask-app
```

---

## 🤝 Contributing

We welcome contributions! 🎉 If you'd like to contribute, please follow these steps:

1. **Fork** the repository.
2. **Create a new branch**:

```bash
git checkout -b feature/your-feature-name
```

3. **Commit your changes**:

```bash
git commit -m "Add your awesome feature"
```

4. **Push to the branch**:

```bash
git push origin feature/your-feature-name
```

5. **Open a Pull Request** 🚀

---

## 📝 License

This project is licensed under the **MIT License**. See the [LICENSE](LICENSE) file for details.

---

## 📧 Contact

If you have any questions or feedback, feel free to reach out:

- **GitHub Issues**: [Open an Issue](https://github.com/ucdse/flask-app/issues) 🐛
- **Repository**: [https://github.com/ucdse/flask-app](https://github.com/ucdse/flask-app)

---

Made with ❤️ by the [UCD Software Engineering](https://github.com/ucdse) team. Happy coding! 🎉