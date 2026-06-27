# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## 项目概述

KHunter 是一套开箱即用的 A 股量化交易系统，集数据管理、策略选股、择时交易、风险控制、回测验证于一体。技术栈：Python 3.12+、Flask、SQLite、akshare、pandas/numpy。

## 常用命令

```bash
# 安装依赖（uv 会自动创建虚拟环境）
uv sync

# 启动 Web 界面（默认 http://localhost:8080）
uv run main.py web

# 首次全量数据抓取
uv run main.py init

# 完整流程：智能更新数据 + 选股
uv run main.py run

# 完整流程 + B1 完美图形匹配排序
uv run main.py run --b1-match

# 限制处理股票数量（快速测试）
uv run main.py run --max-stocks 100

# 指定分类筛选
uv run main.py run --category bowl_center  # 回落碗中
uv run main.py run --category near_duokong  # 靠近多空线

# Windows 用户可双击 start.bat 启动
```

## 架构概览

### 核心模块

- **main.py** - CLI 入口，`QuantSystem` 类编排整个流程：数据更新 → 选股 → 输出
- **web_server.py** - Flask + SocketIO Web 服务器，提供前端界面和 REST API
- **strategy/** - 选股策略模块，所有策略继承 `BaseStrategy`
- **trading/** - 交易相关：回测引擎、评分系统、狩猎场、策略运行器
- **stock_analyzer/** - 股票分析器：技术面、基本面、资金流、板块分析
- **utils/** - 工具模块：数据获取、数据库管理、技术指标、K 线图生成
- **config/** - YAML/JSON 配置文件
- **data/** - SQLite 数据库和缓存目录

### 数据流

```
akshare API → utils/数据获取 → SQLite (data/stock_selection.db)
                                      ↓
                              strategy/选股策略
                                      ↓
                              trading/评分排名 → 狩猎场
                                      ↓
                              web_server.py → 前端展示
```

### 策略系统

策略基类：`strategy/base_strategy.py` 的 `BaseStrategy`

必须实现两个方法：
- `calculate_indicators(df)` - 计算技术指标
- `select_stocks(df, stock_name)` - 选股逻辑，返回信号列表

策略通过 `strategy/strategy_registry.py` 自动注册，参数配置在 `config/strategy_params.yaml`。扩展新策略只需在 `strategy/` 目录创建文件继承 `BaseStrategy`，系统自动识别。

### 数据库

- 主数据库：`data/stock_selection.db`（SQLite）
- 全局访问：`utils/global_db.py` 的 `get_global_db()` 获取 `DBManager` 单例，`get_stock_repo()` 获取 `StockRepo` 单例
- DBManager 提供通用 SQLite 操作（连接池、事务管理、CRUD）
- StockRepo 封装股票领域查询（K 线读写、股票名称等），通过构造函数注入 DBManager
- 股票相关操作统一使用 `StockRepo`，DBManager 上的旧股票方法已 deprecated
- B1 图形库缓存：`data/cache/b1_pattern_library_cache.json`

### Web 前端

- 单页面应用：`web/templates/index.html`
- 静态资源：`web/static/`（CSS、JS、图片）
- API 路由：`trading/routes.py`（Blueprint，前缀 `/api/trading`）

## 编码规范

- 遵循 PEP 8，4 空格缩进，最大行长 100 字符
- 使用简体中文注释和 docstring
- 函数必须有 docstring，说明参数和返回值
- Commit message 格式：`<type>(<scope>): <subject>`（feat/fix/docs/refactor/perf/test/chore）

## Lint 审查规则

**每个提交的 Python 文件都必须经过 Pyright 类型检查审查。**

```bash
# 检查单个文件
uv run pyright <file_path>

# 检查多个文件
uv run pyright file1.py file2.py file3.py
```

- 提交前必须对所有修改的 `.py` 文件运行 `uv run pyright`，确保 0 errors
- 常见修复模式：
  - `param: str = None` → `param: Optional[str] = None`
  - `return None` 与返回类型不匹配 → 改为 `Optional[返回类型]`
  - 变量可能未绑定 → 在使用前初始化默认值
  - 第三方库无类型存根 → `import xxx  # type: ignore[import-untyped]`
  - `date` 对象传入 `str` 参数 → 使用 `.strftime('%Y-%m-%d')` 转换

## 配置文件

- `config/config.yaml` - 主配置（从 `config.yaml.template` 复制）
- `config/strategy_params.yaml` - 策略参数（51KB，包含所有策略的详细配置）
- `config/strategy_order.yaml` - 策略执行顺序
- `config/strategy_weights.json` - 策略权重
- `config/risk_config.yaml` - 风险控制参数

## 注意事项

- Python 版本要求 3.12+，包管理使用 uv（非 pip）
- 数据目录 `data/` 在 `.gitignore` 中，不提交到仓库
- `config/config.yaml` 包含敏感信息（钉钉 webhook），不要提交
- Web 服务器默认端口 8080（通过 `main.py web` 启动）
- 智能数据更新：15:00 前不更新，检查是否有当天数据后决定是否增量更新
