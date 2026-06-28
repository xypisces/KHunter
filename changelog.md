# Changelog

## 2026-06-27（架构重构 Phase 3-5）

### Phase 3：策略层统一 — 激活 indicators/ 模块

**背景：** 7 个策略文件和 1 个 web 路由仍通过已废弃的 `utils/technical.py` shim 调用指标函数，需要完成最后一步迁移。

**变更内容：**

- 新建 `indicators/trend.py`：迁移 `calculate_zhixing_trend` 知行趋势指标
- 新建 `indicators/returns.py`：迁移 `calculate_price_change`、`calculate_daily_return` 收益率指标
- 迁移 7 个策略文件 + 1 个 web 路由的导入路径（`utils.technical` → `indicators`）
- 适配 KDJ/MACD 返回值从 DataFrame 包装改为 tuple 解包
- 更新 `BaseStrategy.calculate_indicators()` docstring 明确倒序合约
- 删除 `utils/technical.py` deprecated 兼容层

### Phase 4：配置层统一 — AppConfig 单例

**背景：** `config/config.yaml` 被至少 4 个独立位置各自加载，形成 split-brain 问题。Web UI 修改配置后，其他加载方的内存缓存不会更新。

**变更内容：**

- 新建 `utils/app_config.py`：`AppConfig` 类 + `get_app_config()` 单例
  - 支持 `get(key)` 点号分隔嵌套键、`set(key, value)` 原子写回、`update(data)` 批量更新
  - 原子写入（临时文件 + `os.replace`）+ 线程锁
- `web/routes/system.py`：GET/POST `/api/config` 改用 `AppConfig`
- `main.py`：`QuantSystem` 改用 `AppConfig`，删除 `_load_config()`
- `web/app_factory.py`：删除未使用的 `config_file` 死参数

### Phase 5a：DataCollectionService 死代码清理

**背景：** `utils/data_collection_service.py`（1301 行）是上帝模块，其中 14 个方法（~500 行）无任何外部调用者。

**变更内容：**

- 删除 14 个无调用者方法（初始化流程、配置查询、状态查询等）
- 移除 `init_status`、`init_lock`、重复定义的 `_add_init_log`
- 清理未使用导入（`DBManager`、`DatabaseInitializer`、`AKShareFetcher`）
- 文件从 1301 行减少到 562 行（-57%）

### Phase 5b：统一卖出基础设施

**背景：** 回测引擎（`backtest_engine._process_sell`）和实盘组合管理器（`portfolio_manager._execute_sell`）的卖出逻辑已完全漂移。回测有完整的成本模型和风控，实盘无成本计算、无止损止盈。

**变更内容：**

- `TradingCoreMixin` 新增三个共享方法：
  - `get_sell_price()` — 抽象方法，由子类实现价格来源（回测用开盘价，实盘用实时价格）
  - `calculate_sell_cost()` — 统一卖出成本计算（佣金+过户费+印花税）
  - `create_sell_record()` — 标准化 19 字段卖出记录
- `backtest_engine._create_sell_record` 委托给 mixin
- `portfolio_manager._execute_sell` 使用 mixin 的成本模型和标准化记录格式

**注意：** 5 层卖出决策逻辑（止盈/止损/追踪止损/持仓过期/择时信号）仍留在 backtest_engine 中，因其深度耦合回测特有状态（价格缓存、择时策略等）。portfolio_manager 通过外部信号驱动卖出，使用 mixin 共享基础设施处理成本和记录。

---

## 2026-06-27

### refactor: 消除 4 个上帝模块，系统架构全面重构

**背景：** 系统存在多个大型单文件模块（`web_server.py` 4439 行、`strategy_runner.py` 3416 行、`trading/routes.py` 2775 行），职责交织、无法测试、导入即副作用。本次通过 6 个候选任务系统性消除上帝模块。

**变更内容：**

#### 1. StrategyRegistry 缓存优化
- 添加文件 mtime 检测，未变时返回缓存实例（零 I/O）
- 提取 `_instantiate_strategy()` 统一实例化逻辑
- 新增 `force_reload()` 和 `clear_cache()` 方法
- 支持 `params_loader` 注入以便测试

#### 2. web_server.py Blueprint 拆分
- 引入 `create_app()` 工厂函数，消除模块级初始化副作用
- 按领域拆分为 10 个 Blueprint：dashboard/stocks/signals/strategies/system/analysis/risk/backtest/khunter/views
- 依赖通过 Flask `app.config` 注入，支持测试替换
- `web_server.py` 从 4439 行缩减至 31 行
- 拆分 `trading/routes.py` 到独立的 `backtest.py` 和 `khunter.py`

#### 3. StrategyRunner 职责分离
- 新增 `TaskHistory`：任务历史 + 日报生成（180 行）
- 新增 `SignalStore`：信号持久化（130 行）
- 新增 `ExdividendHandler`：除权除息处理（180 行）
- 新增 `PortfolioManager`：持仓管理 + 交易执行 + Ptrade 同步（250 行）
- 新增 `StrategyExecutor`：选股 + 评分 + 批量执行（220 行）
- 新增 `StrategyRunnerV2`：薄编排器（280 行）

#### 4. 数据获取层整合
- 定义统一 `DataFetcher` 接口 + `MockDataFetcher` 测试适配器
- 新增 `AKShareDataAdapter` 适配器
- `stock_analyzer` 改用统一数据源，删除重复实现
- 按领域分组：`market_data/`、`fundamental/`、`fund_flow/`、`event/`

#### 5. stock_analyzer 统一
- `comprehensive_technical_analysis()` 直接返回前端格式
- 删除 `_convert_technical_result()` 翻译层（~65 行）
- 使用统一 `indicators/` 模块

#### 6. 类型检查修复
- 修复全部 Pylance 类型错误
- 添加 lint 审查规则

**影响：**
- 消除 4 个上帝模块（web_server、strategy_runner、trading/routes、data_fetcher）
- 所有模块可独立测试
- 代码行数净减少 ~2000 行
- 导入不再触发副作用

---

## 2026-06-25

### refactor: 移除 CSVManager 遗留模块，统一数据层为 SQLite

**背景：** 系统从 CSV 迁移到 SQLite 后，`CSVManager` 模块未被完全移除。`data/` 目录下已无 CSV 文件，该模块实际不可用，但仍被 `B1PatternLibrary` 和 `DataFetcher` 引用。

**变更内容：**

- 删除 `utils/csv_manager.py`
- `B1PatternLibrary` 改用 `DBManager`（通过 `get_global_db()`），修复缓存路径为 `data/cache/`
- `main.py` 移除 CSVManager 导入和实例化
- `web_server.py` 移除 CSVManager 导入和实例化，B1 匹配改用 `db_manager`
- `stock_analyzer/data_fetcher.py` 修复两处未初始化的 `self.csv_manager` → `self.db_manager`
- `utils/db_manager.py` 清理"替代 CSVManager"相关注释

**影响：**
- B1 完美图形匹配功能首次在当前环境下可用（此前因数据源为空而完全不工作）
- `DataFetcher` 消除了 `AttributeError` 崩溃风险
- 数据层统一为 SQLite 单一后端，消除数据不一致隐患
