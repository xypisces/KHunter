# Candidate 4: 拆分 StrategyRunner 六大职责

> **优先级**: Worth exploring  \
> **涉及文件**: trading/strategy_runner.py, trading/portfolio_manager.py (新), trading/signal_store.py (新), trading/exdividend_handler.py (新)

---

## Before — 一个 4054 行的类

除权除息逻辑（240 行）嵌入在 StrategyRunner 深处，无法独立测试。组合管理、信号持久化、文件 I/O 交织在一起。

```
StrategyRunner (4054 行)
├── 接口：60+ 公共方法
└── 实现：
    ├── 策略执行
    ├── 组合管理
    ├── 信号管理
    ├── 除权除息
    ├── 文件 I/O
    └── 任务历史

接口 ≈ 实现 → 浅层模块
```

---

## After — 职责分离

StrategyRunner 变为薄编排器，委托给 5 个专用模块。每个模块有自己的接口和状态，通过构造函数注入共享依赖。

```
StrategyRunner (编排器)
├── PortfolioManager (持仓/买卖)
├── SignalStore (信号持久化)
├── ExdividendHandler (除权除息)
├── TaskHistory (任务记录)
└── StrategyExecutor (选股+评分)
```

---

## 问题

除权除息逻辑（240 行）嵌入在 StrategyRunner 深处，无法独立测试。组合管理、信号持久化、文件 I/O 交织在一起，修改一处可能影响其他。

---

## 方案

StrategyRunner 变为薄编排器，委托给 5 个专用模块。每个模块有自己的接口和状态，通过构造函数注入共享依赖。

---

## 收益

- **locality**：除权除息逻辑自包含
- 每个模块可独立测试
- 接口从 60+ 方法缩减到 ~10
- 修改组合逻辑不影响信号逻辑

---

## 验收标准

- [ ] StrategyRunner < 500 行（薄编排器）
- [ ] 除权除息逻辑在 ExdividendHandler 中
- [ ] 组合管理在 PortfolioManager 中
- [ ] 信号持久化在 SignalStore 中
- [ ] 每个模块可独立测试
- [ ] 接口从 60+ 方法缩减到 ~10
