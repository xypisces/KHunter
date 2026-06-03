# KHunter 项目架构总览

## 项目定位

KHunter 是一套 **A 股量化交易系统**，集数据管理、策略选股、择时交易、风险控制、回测验证于一体。技术栈：Python 3.12+、Flask、SQLite、akshare、pandas/numpy。

## 整体架构图

```
┌─────────────────────────────────────────────────────────────────┐
│                        用户入口层                                │
│  ┌──────────────────┐          ┌──────────────────────────┐     │
│  │   main.py (CLI)   │          │  web_server.py (Web UI)  │     │
│  │  QuantSystem 类   │          │  Flask + SocketIO        │     │
│  │  init/run/web     │          │  REST API + WebSocket    │     │
│  └────────┬─────────┘          └────────────┬─────────────┘     │
│           │                                 │                    │
├───────────┼─────────────────────────────────┼────────────────────┤
│           │        核心引擎层                │                    │
│  ┌────────▼─────────────────────────────────▼─────────────┐     │
│  │              StrategyRegistry (单例)                    │     │
│  │         策略自动发现 → 参数热加载 → 执行                  │     │
│  └────────┬──────────────────────────┬────────────────────┘     │
│           │                          │                           │
│  ┌────────▼─────────┐    ┌──────────▼──────────┐               │
│  │  选股策略层        │    │  择时/交易引擎层     │               │
│  │  strategy/        │    │  trading/            │               │
│  │  14 个策略类       │    │  BacktestEngine      │               │
│  │  继承 BaseStrategy│    │  StrategyRunner      │               │
│  │  + B1 模式匹配    │    │  5 维评分系统        │               │
│  └────────┬─────────┘    │  5 种择时策略        │               │
│           │              │  Kelly 仓位管理      │               │
│           │              └──────────┬──────────┘               │
│           │                         │                           │
├───────────┼─────────────────────────┼───────────────────────────┤
│           │        数据层            │                           │
│  ┌────────▼─────────────────────────▼──────────────────────┐   │
│  │                    DBManager (单例)                      │   │
│  │              SQLite + WAL 模式 + 线程安全                 │   │
│  │    stock_kline / stock_basic / stock_selection_record    │   │
│  └──────────────────────────┬──────────────────────────────┘   │
│                              │                                  │
│  ┌───────────────────────────▼──────────────────────────────┐  │
│  │              数据获取层 (utils/)                          │  │
│  │  AKShareFetcher / StockDataFetcher / FundFlowFetcher     │  │
│  │  数据源: akshare (主) / Tushare Pro (辅) / EastMoney     │  │
│  └──────────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────────┘
```

## 目录结构与职责

| 目录 | 文件数 | 职责 |
|------|--------|------|
| `/` (根目录) | 2 | `main.py` CLI 入口 + `web_server.py` Web 入口 |
| `strategy/` | 24 | 选股策略：基类、注册器、14 个策略实现、B1 模式匹配 |
| `trading/` | 47 | 交易引擎：回测、实盘、评分、择时、风控、API 路由 |
| `utils/` | 55 | 工具层：数据获取、数据库、技术指标、风险管理 |
| `stock_analyzer/` | 8 | 股票分析报告生成（独立于交易引擎） |
| `config/` | 12 | YAML/JSON 配置文件（策略参数、权重、风控） |
| `web/` | - | 前端：SPA 单页应用 (index.html + JS modules) |
| `data/` | - | SQLite 数据库 + 缓存（gitignored） |

## 两大入口的关系

### main.py — CLI 入口

`QuantSystem` 类是 CLI 模式的核心编排器：

```python
# 构造时初始化
QuantSystem.__init__()
  → LogConfig.setup_logging()
  → _load_config("config/config.yaml")
  → init_databases_if_needed()
  → get_global_db()           # DBManager 单例
  → AKShareFetcher()          # 数据获取器
  → get_registry()            # StrategyRegistry 单例
  → CSVManager()
```

CLI 命令：
- `uv run main.py init` — 全量数据抓取
- `uv run main.py run` — 智能更新 + 选股
- `uv run main.py run --b1-match` — 选股 + B1 模式匹配
- `uv run main.py web` — 启动 Web 服务器

### web_server.py — Web 入口

Flask + SocketIO 应用，模块级初始化（导入时即执行）：
- 创建 Flask app 和 SocketIO 实例
- 初始化数据库、注册策略
- 创建全局单例（db_manager, registry, stock_analyzer 等）
- 注册 3 个 Blueprint（trading_bp, stock_score_bp, khunter_bp）
- 暴露 50+ REST API 端点 + WebSocket 事件

## 共享单例

两个入口共享以下核心单例：

| 单例 | 模块 | 获取方式 |
|------|------|----------|
| DBManager | `utils/global_db.py` | `get_global_db()` |
| StrategyRegistry | `strategy/strategy_registry.py` | `get_registry()` |

## 数据流全景

```
akshare API ──→ AKShareFetcher ──→ DBManager (SQLite)
                                         │
                                         ▼
                              StrategyRegistry.run_all()
                                         │
                    ┌────────────────────┼────────────────────┐
                    ▼                    ▼                    ▼
            14 个选股策略          评分系统 (5维)         B1 模式匹配
            BaseStrategy          TechnicalScorer         DTW 相似度
            .select_stocks()      MoneyflowScorer         历史案例库
                                  FundamentalScorer
                                  SectorScorer
                                  EventScorer
                    │                    │                    │
                    └────────────────────┼────────────────────┘
                                         ▼
                                   买入候选池
                                         │
                                         ▼
                              择时策略 (TimingStrategy)
                              Turtle / RSI / Bollinger / Support
                                         │
                                         ▼
                              风控系统 (止损/趋势/资金流)
                                         │
                                         ▼
                              Web 前端 / CLI 输出
```

## 关键设计模式

1. **单例模式** — DBManager、StrategyRegistry 全局唯一
2. **策略模式** — 所有选股策略继承 BaseStrategy，统一接口
3. **工厂模式** — TimingStrategyFactory 创建择时策略实例
4. **自动注册** — 放 .py 文件到 strategy/ 目录即自动发现注册
5. **热加载** — 策略参数每次执行时重新读取 YAML，无需重启
6. **模板方法** — BaseStrategy.execute_selection() 定义标准执行流程
7. **门面模式** — AKShareFetcher 协调多个子获取器

## 文件大小 Top 10（需要重点关注的巨型文件）

| 文件 | 大小 | 行数 | 问题 |
|------|------|------|------|
| `trading/strategy_runner.py` | 198KB | ~4165 | 职责过多，建议拆分 |
| `trading/backtest_engine.py` | 123KB | ~2500 | 同上 |
| `trading/routes.py` | 96KB | - | API 路由过于集中 |
| `config/strategy_params.yaml` | 51KB | - | 配置文件过大 |
| `web/templates/index.html` | - | - | SPA 所有页面在一个文件 |
