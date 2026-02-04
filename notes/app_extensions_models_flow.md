# 项目架构与数据库调用逻辑说明（app / extensions / models）

这份文档用于解释当前项目里 `app.py`、`extensions.py`、`models.py`、`config.py`、`scrapers/main_scraper.py`、`scrapers/fetch_stations.py` 的关系，以及你运行项目时到底会执行什么、数据库如何创建、是否需要每次创建等核心问题。

---

## 1. 总体设计思路：单一 DB 实例 + 工厂模式

当前项目采用的是 Flask 常见结构：

- `extensions.py`：只定义扩展对象（`db`、`migrate`），不直接绑定应用。
- `models.py`：只定义模型（表结构），统一使用 `extensions.py` 里的同一个 `db`。
- `app.py`：通过 `create_app()` 创建 Flask 应用并绑定扩展（当前未注册路由）。
- `config.py`：存放 JCDecaux API 与本地输出路径等配置，供 scrapers 使用。
- `scrapers/main_scraper.py`：作为独立脚本，创建 app 上下文后使用同一个 `db` 入库。
- `scrapers/fetch_stations.py`：独立脚本，仅请求 API 并写入 JSON 文件，不操作数据库。

核心原则只有一句话：

> 全项目只保留一个 `SQLAlchemy()` 实例（在 `extensions.py`）。

这样做可以保证：

- 模型 metadata 一致；
- session 一致；
- Flask-Migrate/Alembic 能正确识别所有模型；
- Web 服务和抓取脚本不会出现“连的是同一数据库但不是同一 ORM 上下文”的隐性问题。

---

## 2. 每个文件的职责与调用关系

## `extensions.py`

作用：提供全局扩展对象。

```python
db = SQLAlchemy()
migrate = Migrate()
```

注意：这里只是“声明对象”，还没有和 Flask app 绑定。

---

## `models.py`

作用：定义 ORM 模型（数据库表）。

- `Station`：静态站点信息（number 为主键，contract_name、name、address、经纬度、banking、bonus、bike_stands 等）。
- `Availability`：动态可用性快照（id 自增主键，外键 number 关联 Station，available_bikes、available_bike_stands、status、last_update、timestamp 等）。

关键点：

- 所有模型都基于 `from extensions import db`。
- 这意味着所有表都归属于同一个 metadata。

---

## `app.py`

作用：创建应用 + 绑定扩展。

主要流程：

1. 导入 `db/migrate`（来自 `extensions.py`）。
2. `import models`（保证模型注册到 `db`，供 Flask-Migrate 识别）。
3. `create_app()` 里配置数据库连接（当前数据库 URI 写死在 `app.py`）并执行：
   - `db.init_app(app)`
   - `migrate.init_app(app, db)`
4. 创建全局 `app = create_app()`。
5. 当前未注册任何路由；若直接运行文件，则 `app.run(debug=True)`。

---

## `config.py`

作用：API 与输出相关配置（与 Flask app 解耦，主要给 scrapers 用）。

- `BASE_URL`、`PARAMS`（contract、apiKey）：JCDecaux 站点 API。
- `OUTPUT_JSON`：本地 JSON 输出文件名（如 `stations.json`），供 `fetch_stations.py` 使用。

注意：数据库连接 URI 仍在 `app.py` 中写死，未从 `config` 或环境变量读取。

---

## `scrapers/main_scraper.py`

作用：定时抓取并写入数据库（后台采集脚本）。

主要流程：

1. `from app import create_app`，`from config import BASE_URL, PARAMS`
2. `app = create_app()`
3. 用 `requests.get(BASE_URL, params=PARAMS)` 拉取 JCDecaux API 数据
4. `with app.app_context():` 中遍历每条数据：若 `Station` 不存在则插入，每条都插入一条 `Availability`，最后 `db.session.commit()`
5. `if __name__ == "__main__":` 下 `while True`，成功则 `time.sleep(300)`，异常则 `time.sleep(60)` 再试

这说明：

- 抓取脚本和 Web 不是同一个进程；
- 但它们共享同一套模型和 DB 配置。

---

## `scrapers/fetch_stations.py`

作用：独立脚本，仅请求 JCDecaux API 并将结果写入本地 JSON 文件，不操作数据库。

- 使用 `config.py` 中的 `BASE_URL`、`PARAMS`、`OUTPUT_JSON`。
- 直接运行 `python scrapers/fetch_stations.py` 即可拉取一次并保存到 `stations.json`。
- 与 `main_scraper.py` 的区别：不依赖 Flask app、不写数据库，适合一次性导出或调试 API。

---

## 3. 运行项目时，Python 实际执行顺序

## 情况 A：运行 Web 服务（`python app.py`）

高层执行顺序：

1. 加载 `app.py`
2. 导入 `extensions.py`，创建全局 `db/migrate` 对象
3. 导入 `models.py`，模型类注册到 `db`
4. 执行 `create_app()`，把 `db/migrate` 绑定到 Flask app
5. 当前未注册路由；若直接运行则启动开发服务器

当前无注册路由，请求进来后不会命中业务逻辑；后续可在 `app.py` 中注册路由（例如首页、站点列表、可用性查询等）。

---

## 情况 B：运行抓取器（`python scrapers/main_scraper.py`）

高层执行顺序：

1. 加载抓取脚本（将项目根目录加入 `sys.path`）
2. 导入并调用 `create_app()`，以及 `config` 中的 `BASE_URL`、`PARAMS`
3. 进入 `while True` 循环
4. 每次调用 `scrape_stations()`（请求 API → 在 `app.app_context()` 内更新 Station、插入 Availability → `commit()`）
5. 成功后 `time.sleep(300)`，异常时打印错误并 `time.sleep(60)` 再试

数据库写入策略：

- `Station`：如果站点不存在就插入（静态维度）
- `Availability`：每次抓取都新增一条（时序快照）

---

## 4. 数据库是怎么“创建”的？

这里要分清 2 层概念：

1. **数据库（schema）**：例如 MySQL 里的 `dublinbikes`
2. **表结构（tables）**：`station`、`availability`

---

## 数据库（`dublinbikes`）创建

这是 MySQL 层面的事情，一般手工做一次即可，例如：

```sql
CREATE DATABASE dublinbikes CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
```

---

## 表结构创建/变更

由 Flask-Migrate（Alembic）管理，核心命令：

```bash
flask --app app.py db migrate -m "message"
flask --app app.py db upgrade
```

- `migrate`：根据模型变化生成迁移脚本
- `upgrade`：把迁移应用到数据库

---

## 5. 是不是每次运行都要创建数据库/表？

不是。

- `python app.py`：不会自动建表，只是启动服务。
- `python scrapers/main_scraper.py`：不会自动建表，只是尝试写数据。
- 只有在以下情况下才需要迁移：
  - 第一次初始化项目数据库；
  - 模型发生变化（新增表、字段、约束等）。

日常开发里，通常流程是：

1. 模型改动
2. `flask db migrate`
3. `flask db upgrade`
4. 再运行服务或脚本

---

## 6. 推荐运行方式（你当前项目）

## 第一次在新环境启动

1. 确保 MySQL 服务可用  
2. 确保数据库 `dublinbikes` 已存在  
3. 安装依赖（Flask、Flask-SQLAlchemy、Flask-Migrate、PyMySQL、requests 等）  
4. 执行迁移：

```bash
flask --app app.py db upgrade
```

5. 启动 Web：

```bash
python app.py
```

6. 启动抓取器（新终端）：

```bash
python scrapers/main_scraper.py
```

---

## 日常开发

- 只启动 Web（调接口）：`python app.py`
- 只跑采集：`python scrapers/main_scraper.py`
- 模型改了才做迁移：`flask db migrate` + `flask db upgrade`

---

## 7. 为什么这次重构能解决之前冲突

之前冲突是“两个 `db` 实例”：

- 一个在 `app.py`；
- 一个在 `models.py`。

风险包括：

- 模型挂在 A，session 却用 B；
- Alembic 看不到全部模型；
- 运行时行为不一致、难排查。

现在统一后：

- `extensions.py` 是唯一 `db` 来源；
- `models.py`、`app.py`、`scraper` 都使用同一实例；
- 迁移和运行时都走同一条链路。

---

## 8. 目前仍建议你后续优化的点（与本说明相关）

1. 把数据库 URL 和 API key 从代码里移到环境变量（如 `config.py` 或 `.env`）。  
2. 给 `Availability` 加防重复策略（如 `number + last_update` 唯一约束）。  
3. 抓取脚本异常时做 `db.session.rollback()`。  
4. 在 `app.py` 中注册路由（例如首页、站点列表、历史可用性查询），如需用户功能再考虑 POST 与密码哈希。  
5. 补充 `README` 和依赖文件（如 `requirements.txt`），方便他人一键跑起来。  

---

## 9. 一句话记忆版

`extensions.py` 提供唯一 `db`，`models.py` 定义 `Station` 与 `Availability` 两张表，`app.py` 绑定扩展并启动 Web（当前无路由），`config.py` 提供 API 等配置给 scrapers，`main_scraper.py` 在 app 上下文里定时写库，`fetch_stations.py` 仅拉 API 写 JSON；数据库和表不是每次运行都创建，只有初始化或模型变化时才通过迁移创建/更新。
