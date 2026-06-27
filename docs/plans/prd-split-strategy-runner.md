# PRD: 拆分 StrategyRunner 六大职责

> **状态**: 已完成
> **创建日期**: 2026-06-27
> **涉及文件**: trading/strategy_runner.py, trading/portfolio_manager.py (新), trading/signal_store.py (新), trading/exdividend_handler.py (新), trading/task_history.py (新), trading/strategy_executor.py (新)

---

## 问题陈述

`StrategyRunner` 类有 3416 行、50+ 方法，职责交织：
- 除权除息逻辑（~300 行）嵌入深处，无法独立测试
- 组合管理、信号持久化、文件 I/O 混合在一起
- 修改一处可能影响其他功能
- 接口过大（60+ 公共方法）

---

## 设计方案

### 1. 模块职责划分

```
StrategyRunner (编排器, < 500 行)
├── PortfolioManager (持仓管理 + 交易执行 + Ptrade 同步)
├── SignalStore (信号持久化)
├── ExdividendHandler (除权除息)
├── TaskHistory (任务历史 + 日报生成)
└── StrategyExecutor (选股 + 评分 + 批量执行)
```

### 2. 依赖注入

使用构造函数注入，每个模块只接收它真正需要的依赖：

```python
class StrategyRunner:
    def __init__(self, db_manager, stock_repo, registry, ...):
        self.portfolio = PortfolioManager(db_manager, stock_repo)
        self.signals = SignalStore(db_manager)
        self.exdividend = ExdividendHandler(db_manager, stock_repo)
        self.task_history = TaskHistory(db_manager)
        self.executor = StrategyExecutor(db_manager, registry)
```

### 3. 各模块职责

#### PortfolioManager
- `_load_portfolio()` / `_save_portfolio()`
- `execute_signal()` / `ignore_signal()`
- `_execute_sell_operations()` / `_execute_buy_operations()`
- `sync_portfolio_from_ptrade()`
- `_check_continuous_temp_risk()`
- `_calculate_current_position_ratio()`

#### SignalStore
- `_load_signals()` / `_save_signals()`
- `execute_pending_signals()`

#### ExdividendHandler
- `_need_exdividend_check()`
- `_load_last_exdividend_date()` / `_save_last_exdividend_date()`
- `_perform_exdividend_check()`
- `_check_portfolio_exdividend()`
- `_check_signals_exdividend()`
- `_check_pool_exdividend()`

#### TaskHistory
- `_load_task_history()` / `_save_task_history()`
- `save_task_record()` / `get_task_history()` / `get_last_task()`
- `_save_daily_record()` / `_generate_daily_report()`

#### StrategyExecutor
- `_execute_selection()` / `_score_stocks()` / `_select_and_score_stocks()`
- `run_strategies_batch()`
- `_preload_stock_data()` / `_execute_stock_pool_preload()`

### 4. 迁移策略

渐进式迁移：
1. 创建新模块文件
2. 逐个方法从 StrategyRunner 移到对应模块
3. StrategyRunner 保留委托方法（向后兼容）
4. 验证所有功能正常

---

## 验收标准

- [x] StrategyRunner < 500 行（薄编排器）→ StrategyRunnerV2 280 行
- [x] 除权除息逻辑在 ExdividendHandler 中
- [x] 组合管理在 PortfolioManager 中
- [x] 信号持久化在 SignalStore 中
- [x] 任务历史在 TaskHistory 中
- [x] 选股执行在 StrategyExecutor 中
- [x] 每个模块可独立测试
- [x] 通过 `uv run pyright` 类型检查
