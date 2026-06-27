# Changelog

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
