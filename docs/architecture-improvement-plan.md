# KHunter 架构改进计划

> 基于 2026-06-25 架构审查报告，按依赖关系和风险梯度排序。

## 总览

10 个改进候选分为 5 个阶段执行，原则：**先删后建 → 统一接口 → 核心重构 → Web 拆分 → 领域整合**。

```
阶段 1  地基清理      #10 CSVManager 移除
阶段 2  统一基础设施   #3 技术指标统一 → #6 DBManager 深化
阶段 3  核心重构      #1 回测/实盘引擎合并 → #8 StrategyRegistry 优化
阶段 4  Web 层拆分    #2 web_server.py 拆分 + #7 routes.py 拆分
阶段 5  领域整合      #5 数据获取层 → #4 StrategyRunner 拆分 → #9 stock_analyzer 统一
```

---

## 依赖关系图

```
#10 ──→ (无下游依赖，独立完成)

#3  ──→ #1  (统一指标 → 引擎合并)
   └──→ #9  (统一指标 → analyzer 复用)

#6  ──→ #2  (可注入 DB → web 工厂)
   └──→ #5  (DB 接口 → 数据获取整合)

#2  ←──→ #7  (协同实施)

#1  ──→ #4  (共享逻辑提取 → Runner 拆分)
#5  ──→ #9  (统一数据源 → analyzer 统一)
```

---

## 阶段 1：地基清理

### #10 移除 CSVManager 遗留模块

| 属性 | 值 |
|------|-----|
| 强度 | Speculative |
| 改动量 | ~100 行 |
| 风险 | 低 |

**涉及文件：**
- `utils/csv_manager.py` — 删除
- `main.py` — 移除 `self.csv_manager` 实例化
- `strategy/b1_pattern_library.py` — 改用 `DBManager.read_stock()`

**目标：** 消除双存储后端（CSV vs SQLite），确保 B1 模式匹配的数据源与其他模块一致。

**收益：**
- 消除数据不一致风险
- 删除 80 行遗留代码
- 接口统一，无隐式依赖

---

## 阶段 2：统一基础设施

### #3 统一技术指标模块

| 属性 | 值 |
|------|-----|
| 强度 | Strong |
| 改动量 | ~300 行 |
| 风险 | 中 |

**涉及文件：**
- `utils/technical.py` — 整合
- `trading/technical_indicators.py` — 整合
- `utils/support_level_calculator.py` — 整合
- `indicators/__init__.py` — 新建

**问题：** 三处计算移动平均线，对数据排序假设不同：
- `utils/technical.py` — MA() 反转数据处理降序
- `trading/technical_indicators.py` — calculate_ma() 标准 rolling，带缓存
- `utils/support_level_calculator.py` — 内联 rolling()，假设升序

**目标：** 创建 `indicators/` 深层模块，统一所有技术指标实现。内部处理升序/降序转换，对外暴露统一接口。

**收益：**
- locality：指标逻辑集中一处
- 消除排序假设不一致的 bug 风险
- leverage：一个接口覆盖所有调用方
- 测试只需覆盖一个模块

---

### #6 深化 DBManager — 分离通用与领域逻辑

| 属性 | 值 |
|------|-----|
| 强度 | Worth exploring |
| 改动量 | ~200 行 |
| 风险 | 中 |

**涉及文件：**
- `utils/db_manager.py` — 拆分
- `utils/global_db.py` — 改为延迟初始化
- `data/stock_repo.py` — 新建

**问题：** DBManager 混合了通用 SQLite 操作（connect/execute/insert）和股票领域查询（read_stock/write_stock/list_all_stocks）。47+ 处调用 `get_global_db()` 直接使用领域方法。单例在导入时创建，无法测试替换。

**目标：** DBManager 只保留通用数据库操作（~10 方法）。股票相关查询提取到 `StockRepo`，通过构造函数注入 DBManager。

**收益：**
- DBManager 接口从 ~30 方法缩减到 ~10
- StockRepo 可用内存 DB 测试
- locality：股票 SQL 集中一处
- 为 #2（web_server 拆分）的依赖注入铺路

---

## 阶段 3：核心重构

### #1 合并回测引擎与实盘运行器

| 属性 | 值 |
|------|-----|
| 强度 | Strong |
| 改动量 | ~3000 行 |
| 风险 | 高 |
| 依赖 | #3（统一技术指标） |

**涉及文件：**
- `trading/backtest_engine.py` (2508 行)
- `trading/strategy_runner.py` (4054 行)
- `trading/trading_core.py` — 新建（TradingCoreMixin）

**问题：** 两个模块共享 7 个相同职责（交易日历、股价查询、卖出处理、池移除检查、交易成本计算、支撑位计算），但实现已漂移——参数名、默认值、日志各不相同。每次 bug 修复必须做两遍。

**共享职责清单：**

| 方法 | BacktestEngine | StrategyRunner | 状态 |
|------|---------------|----------------|------|
| `__init__` 注册表/获取器/缓存 | ✅ | ✅ | 近似 |
| `_load_trading_calendar` | ✅ | ✅ | 漂移 |
| `_get_stock_price` | ✅ | ✅ | 漂移 |
| `_process_sell` | ✅ | ✅ | 漂移 |
| `_check_pool_removal` | ✅ | ✅ | 漂移 |
| `calculate_trading_cost` | ✅ | ✅ | 参数不同 |
| `_calculate_support_level` | ✅ | ✅ | 漂移 |

**目标：** 提取 `TradingCoreMixin`，包含所有共享逻辑。BacktestEngine 和 StrategyRunner 各自只保留特有部分：
- BacktestEngine：回测循环、历史数据预加载、回测评分
- StrategyRunner：实盘持久化、除权除息、PTrade 导出、任务历史

**收益：**
- locality：bug 修复集中在一处
- leverage：一个接口，两个调用方
- 删除 ~2000 行重复代码
- 测试只需覆盖一个模块

---

### #8 优化 StrategyRegistry 热加载机制

| 属性 | 值 |
|------|-----|
| 强度 | Speculative |
| 改动量 | ~100 行 |
| 风险 | 低 |
| 依赖 | 无（与 #1 协同效果更好） |

**涉及文件：**
- `strategy/strategy_registry.py`

**问题：** 每次 `get_strategy()` 都读取 YAML 文件并重新实例化策略。策略对象是临时的，设置的状态会丢失。难以测试。

**目标：** 使用文件 mtime 检测变更，未变则返回缓存实例。提供 `force_reload()` 方法。测试时可注入不读文件的适配器。

**收益：**
- 减少磁盘 I/O
- 策略实例可保持状态
- 测试可跳过文件系统
- 保留热加载能力

---

## 阶段 4：Web 层拆分

### #2 拆分 web_server.py 上帝模块

| 属性 | 值 |
|------|-----|
| 强度 | Strong |
| 改动量 | ~1000 行 |
| 风险 | 高 |
| 依赖 | #6（DBManager 可注入） |

**涉及文件：**
- `web_server.py` (4442 行) — 拆分
- `web/app_factory.py` — 新建
- `web/routes/dashboard.py` — 新建
- `web/routes/stocks.py` — 新建
- `web/routes/signals.py` — 新建

**问题：** 导入 web_server 即触发数据库初始化和策略加载。50+ 路由、WebSocket、业务逻辑全在一个 4442 行文件中，无法单独测试任何端点。

**目标：** 引入 `create_app()` 工厂函数，依赖通过参数注入。按领域拆分 Blueprint 到独立文件。模块级初始化移入工厂。

**收益：**
- leverage：工厂注入，测试可替换依赖
- locality：每个 Blueprint 自包含
- 消除导入副作用
- 可独立启动子集路由

---

### #7 拆分 trading/routes.py 路由模块

| 属性 | 值 |
|------|-----|
| 强度 | Worth exploring |
| 改动量 | ~500 行 |
| 风险 | 中 |
| 依赖 | 与 #2 协同实施 |

**涉及文件：**
- `trading/routes.py` (2775 行) — 拆分
- `trading/routes/backtest.py` — 新建
- `trading/routes/khunter.py` — 新建

**问题：** 回测和狩猎场是不同领域，却共享模块级初始化（backtest_dao、db_manager、akshare_fetcher）。修改狩猎场路由必须加载回测 DAO。无法单独测试任一 Blueprint。

**目标：** 拆分为独立文件，依赖通过 Flask app.config 或工厂函数注入。与 #2 协同实施。

**收益：**
- 消除跨领域导入耦合
- 每个 Blueprint 可独立测试
- locality：路由与领域逻辑就近

---

## 阶段 5：领域整合

### #5 整合数据获取层

| 属性 | 值 |
|------|-----|
| 强度 | Worth exploring |
| 改动量 | ~800 行 |
| 风险 | 高 |
| 依赖 | #6（DB 接口稳定） |

**涉及文件：**
- `utils/akshare_fetcher.py` — 重构或删除
- `utils/base_fetcher.py` — 统一基类
- `utils/data_fetcher.py` — 消除同名歧义
- `stock_analyzer/data_fetcher.py` — 复用统一数据源
- 10+ 子 fetcher 文件

**问题：** 两个同名 `DataFetcher` 类完全不同。AKShareFetcher 是纯委托门面。基类只被 5/14 个 fetcher 继承。stock_analyzer 有独立的数据获取路径。

**目标：** 定义 `DataPort` 绥一接口，按领域分组实现（MarketData/FundFlow/Analysis）。消除 AKShareFetcher 纯委托层。stock_analyzer 复用同一数据源。

**收益：**
- 消除同名类歧义
- leverage：一个接口覆盖所有数据需求
- 删除纯委托门面
- 测试可用内存适配器替换

---

### #4 拆分 StrategyRunner 六大职责

| 属性 | 值 |
|------|-----|
| 强度 | Worth exploring |
| 改动量 | ~1200 行 |
| 风险 | 高 |
| 依赖 | #1（共享逻辑提取完成） |

**涉及文件：**
- `trading/strategy_runner.py` (4054 行) — 拆分
- `trading/portfolio_manager.py` — 新建
- `trading/signal_store.py` — 新建
- `trading/exdividend_handler.py` — 新建
- `trading/task_history.py` — 新建

**问题：** StrategyRunner 包含 6 个独立职责：策略执行、组合管理、信号管理、除权除息（240 行）、文件 I/O、任务历史。除权除息逻辑嵌入深处，无法独立测试。

**目标：** StrategyRunner 变为薄编排器，委托给 5 个专用模块。每个模块有自己的接口和状态，通过构造函数注入共享依赖。

**收益：**
- locality：除权除息逻辑自包含
- 每个模块可独立测试
- 接口从 60+ 方法缩减到 ~10
- 修改组合逻辑不影响信号逻辑

---

### #9 统一 stock_analyzer 与 trading 的数据/评分

| 属性 | 值 |
|------|-----|
| 强度 | Speculative |
| 改动量 | ~500 行 |
| 风险 | 中 |
| 依赖 | #3 + #5 先完成 |

**涉及文件：**
- `stock_analyzer/__init__.py` — 重构
- `stock_analyzer/data_fetcher.py` — 复用统一数据源
- `stock_analyzer/technical_analyzer.py` — 复用评分系统

**问题：** stock_analyzer 有独立的数据获取和评分逻辑，与 trading/ 的 5 维评分系统概念重复。`_convert_technical_result()` 是因为两边格式不统一才存在的翻译层。

**目标：** 依赖 #5（统一数据获取）和 #3（统一技术指标）。stock_analyzer 改为复用 trading/ 的评分系统，通过适配层转换输出格式。

**收益：**
- 消除翻译层
- 评分逻辑不再重复
- leverage：复用已有评分模块

---

## 每阶段预期收益

| 阶段 | 改动量 | 收益 |
|------|--------|------|
| 1 地基清理 | ~100 行 | 消除数据不一致风险 |
| 2 统一基础设施 | ~500 行 | 统一接口，为后续铺路 |
| 3 核心重构 | ~3100 行 | 消除最大重复源，测试覆盖集中 |
| 4 Web 层拆分 | ~1500 行 | 消除导入副作用，可独立测试路由 |
| 5 领域整合 | ~2500 行 | 架构完全统一，无冗余路径 |

**总计：** ~7700 行改动，消除 ~4500 行重复代码。
