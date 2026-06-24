# Candidate 1: 合并回测引擎与实盘运行器

> **优先级**: Strong  \
> **涉及文件**: trading/backtest_engine.py, trading/strategy_runner.py, trading/stock_data_mixin.py (新)

---

## Before — 浅层模块，接口≈实现

两个模块共享 7 个相同职责（交易日历、股价、卖出、池移除、成本、支撑位），但实现已漂移——参数名、默认值、日志各不相同。

```
BacktestEngine (2508 行)          StrategyRunner (4054 行)
├── __init__: 注册表/获取器/缓存    ├── __init__: 注册表/获取器/缓存
├── _load_trading_calendar        ├── _load_trading_calendar
├── _get_stock_price              ├── _get_stock_price
├── _process_sell                 ├── _process_sell
├── _check_pool_removal           ├── _check_pool_removal
├── calculate_backtest_cost       ├── calculate_trading_cost
└── _calculate_support_level      └── _calculate_support_level
         ↓ 漂移的实现 ↓
```

---

## After — 深层模块，共享实现

提取 `TradingCoreMixin`，包含所有共享逻辑。BacktestEngine 和 StrategyRunner 各自只保留特有部分（回测循环 vs 实盘持久化/除权除息）。

```
TradingCoreMixin (深层模块)
├── 交易日历管理
├── 股价查询
├── 卖出处理
├── 池移除检查
├── 交易成本计算
└── 支撑位计算
        ↑               ↑
BacktestEngine      StrategyRunner
(回测特有逻辑)      (实盘特有逻辑)
```

---

## 问题

两个模块共享 7 个相同职责（交易日历、股价、卖出、池移除、成本、支撑位），但实现已漂移——参数名、默认值、日志各不相同。每次 bug 修复必须做两遍。

---

## 方案

提取 `TradingCoreMixin`，包含所有共享逻辑。BacktestEngine 和 StrategyRunner 各自只保留特有部分（回测循环 vs 实盘持久化/除权除息）。

---

## 收益

- **locality**：bug 修复集中在一处
- **leverage**：一个接口，两个调用方
- 删除 ~2000 行重复代码
- 测试只需覆盖一个模块

---

## 验收标准

- [ ] TradingCoreMixin 包含所有 7 个共享职责
- [ ] BacktestEngine 只保留回测特有逻辑
- [ ] StrategyRunner 只保留实盘特有逻辑
- [ ] 所有现有测试通过
- [ ] 无重复代码（grep 确认）
