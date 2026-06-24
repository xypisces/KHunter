# PRD: 移除 CSVManager 遗留模块

## Problem Statement

系统从 CSV 迁移到 SQLite 后，`CSVManager` 模块未被完全移除。当前 `data/` 目录下已无任何 CSV 文件，`CSVManager.read_stock()` 永远返回空 DataFrame。然而 `B1PatternLibrary`（B1 完整图形匹配）和 `DataFetcher`（股票分析器数据获取）仍引用该模块，导致：

1. **B1 匹配功能完全不可用** — 案例库构建依赖 `CSVManager.read_stock()`，永远拿不到数据；缓存路径硬编码为旧 Linux 服务器路径 `/root/quant-csv/`，本地不存在
2. **DataFetcher 存在隐藏崩溃风险** — `self.csv_manager` 从未初始化，如果相关代码路径被执行会抛出 `AttributeError`
3. **数据一致性隐患** — 两个数据后端（CSV 和 SQLite）可能返回不同结构的数据，虽然当前 CSV 不可用，但保留这段代码会误导后续开发者

## Solution

彻底移除 `CSVManager` 模块及其所有引用，统一使用 `DBManager`（通过 `get_global_db()` 单例）作为唯一数据后端。同时修复 `B1PatternLibrary` 的缓存路径，使其在当前环境下可用。

## User Stories

1. As a 开发者, I want 移除 `utils/csv_manager.py` 文件, so that 代码库中不再保留已废弃的 CSV 数据后端
2. As a 开发者, I want `B1PatternLibrary` 使用 `DBManager` 读取股票数据, so that B1 匹配功能可以正常工作
3. As a 开发者, I want `B1PatternLibrary` 的缓存路径从旧服务器路径改为项目本地路径, so that 缓存在当前环境下可用
4. As a 开发者, I want `main.py` 中移除 `CSVManager` 的导入和实例化, so that `QuantSystem` 不再维护无用的 `csv_manager` 属性
5. As a 开发者, I want `web_server.py` 中移除 `CSVManager` 的导入和实例化, so that Web 端 B1 匹配使用统一的数据源
6. As a 开发者, I want `web_server.py` 中 B1 匹配循环使用 `db_manager` 读取股票数据, so that 数据来源与系统其他部分一致
7. As a 开发者, I want `DataFetcher` 中两处 `self.csv_manager` 替换为 `self.db_manager`, so that 股票分析器不再有未初始化变量的崩溃风险
8. As a 开发者, I want `DBManager` 中"替代 CSVManager"的注释改为直接描述方法功能, so that 后续开发者不会被已不存在的模块困惑
9. As a 用户, I want `main.py run --b1-match` 命令能正常执行 B1 匹配, so that 我可以使用完整图形匹配功能筛选股票
10. As a 用户, I want Web 界面的 B1 匹配功能正常工作, so that 我可以在 Web 端查看匹配结果
11. As a 开发者, I want 所有变更在同一个 commit 中完成, so that 不存在中间状态的不一致

## Implementation Decisions

### 模块变更清单

**删除：**
- `utils/csv_manager.py` — 整个文件

**修改：**
- `strategy/pattern_library.py` — `B1PatternLibrary` 类
- `main.py` — `QuantSystem` 类
- `web_server.py` — B1 匹配相关代码块
- `stock_analyzer/data_fetcher.py` — `DataFetcher` 类
- `utils/db_manager.py` — 注释清理

### B1PatternLibrary 接口变更

构造函数从 `__init__(self, csv_manager)` 改为 `__init__(self)`，内部通过 `get_global_db()` 获取数据库管理器。调用方从 `B1PatternLibrary(csv_manager)` 改为 `B1PatternLibrary()`。

内部数据读取统一使用 `DBManager.read_stock()`，该方法返回的 DataFrame 包含 `code, date, open, high, low, close, volume, market_cap, K, D, J` 列，与 `PatternFeatureExtractor` 所需的列（`close, volume, K, D, J`）完全兼容。

### 缓存路径修正

`CACHE_FILE` 从 `/root/quant-csv/data/b1_pattern_library_cache.json` 改为 `data/cache/b1_pattern_library_cache.json`，与项目其他缓存目录保持一致。

### DBManager.read_stock 排序行为

`DBManager.read_stock()` 默认 `order='desc'`（最新数据在前），与原 CSVManager 行为一致（CSV 按日期倒序排列）。`B1PatternLibrary._extract_window()` 使用 `df.head(lookback_days)` 取突破日期前的数据，两种排序下语义一致。

## Testing Decisions

项目当前无测试套件。本次变更为纯重构（移除死代码、统一数据源），不改变业务逻辑，通过以下方式验证：

1. `uv run main.py run --b1-match --max-stocks 10` — 验证 B1 匹配功能端到端可用
2. `grep -r "csv_manager\|CSVManager" --include="*.py"` — 验证无残留引用
3. 启动 Web 服务器，触发 B1 匹配功能，验证无报错

## Out of Scope

- B1 匹配功能的逻辑优化或性能改进
- 其他策略模块的重构
- 测试套件的建立
- DBManager 接口的统一化（如读取排序默认值的调整）

## Further Notes

- `DBManager` 的 docstring 中已标注"替代 CSVManager"的方法对应关系（第 696-895 行），移除 CSVManager 后这些注释应改为直接描述方法功能
- `B1PatternLibrary` 的缓存机制在移除 CSVManager 后将首次正常工作（之前因数据源为空，缓存永远无法生成）
