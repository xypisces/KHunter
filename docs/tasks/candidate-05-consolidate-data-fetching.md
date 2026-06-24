# Candidate 5: 整合数据获取层

> **优先级**: Worth exploring  \
> **涉及文件**: utils/akshare_fetcher.py, utils/base_fetcher.py, utils/data_fetcher.py, stock_analyzer/data_fetcher.py, + 10 个子 fetcher

---

## Before — 14+ 类，继承层次混乱

两个同名 `DataFetcher` 类完全不同。AKShareFetcher 是纯委托门面，不增加逻辑。基类只被 5/14 个 fetcher 继承。

```
AKShareFetcher (门面，纯委托)
├── StockDataFetcher
├── KlineFetcher
├── FundFlowFetcher
└── IndexDataFetcher

DataFetcher (utils/data_fetcher.py)    DataFetcher (stock_analyzer/)
└── 多源回退                            └── 直接 akshare
         ↓ 同名不同类 ↓

base_fetcher.py (DataFetcher 基类)
└── 部分继承
```

---

## After — 统一接口 + 领域分组

定义 `DataPort` 接口（统一数据访问），按领域分组实现。消除 AKShareFetcher 纯委托层。

```
data/ (深层模块)
├── DataPort (统一接口)
│   ├── MarketData (行情/K线)
│   ├── FundFlow (资金流)
│   └── Analysis (分析数据)
└── ↑       ↑       ↑
StrategyRunner  BacktestEngine  StockAnalyzer
```

---

## 问题

两个同名 `DataFetcher` 类完全不同。AKShareFetcher 是纯委托门面，不增加逻辑。基类只被 5/14 个 fetcher 继承。stock_analyzer 有独立的数据获取路径。

---

## 方案

定义 `DataPort` 接口（统一数据访问），按领域分组实现。消除 AKShareFetcher 纯委托层。stock_analyzer 复用同一数据源。

---

## 收益

- 消除同名类歧义
- **leverage**：一个接口覆盖所有数据需求
- 删除纯委托门面
- 测试可用内存适配器替换

---

## 验收标准

- [ ] 只有一个 DataFetcher/DataPort 接口
- [ ] AKShareFetcher 纯委托层删除
- [ ] stock_analyzer 复用统一数据源
- [ ] 所有 fetcher 按领域分组
- [ ] 测试可用内存适配器替换
