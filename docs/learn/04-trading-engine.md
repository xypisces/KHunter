# 交易引擎详解

## 架构概览

交易引擎是 KHunter 的核心，包含回测引擎、实盘运行器、评分系统、风控系统四大组件。

```
trading/
├── backtest_engine.py      # 回测引擎 (123KB)
├── strategy_runner.py      # 实盘运行器 (198KB)
├── timing_strategies.py    # 择时策略
├── backtest_scorer.py      # 回测评分器
├── stock_score_calculator.py # 实盘评分器
├── stock_score_models.py   # 评分模型
├── technical_scorer.py     # 技术面评分
├── moneyflow_scorer.py     # 资金流评分
├── fundamental_scorer.py   # 基本面评分
├── sector_scorer.py        # 板块评分
├── event_scorer.py         # 事件评分
├── khunter_support_calculator.py # 支撑位计算
├── routes.py               # API 路由 (96KB)
└── ...
```

## 一、回测引擎 BacktestEngine

`trading/backtest_engine.py` — 约 2500 行，是系统最核心的模块。

### 关键设计

- **单例锁**：`_backtest_lock` 确保同一时间只有一个回测任务运行
- **全量预加载**：启动时将所有股票数据加载到内存（`stock_filtered_cache`）
- **交易日历**：从 Tushare 获取，用二分查找定位前一交易日

### 每日循环结构 (`run_backtest`)

```
for 每个交易日:
    │
    ├── 1. 处理卖出 (择时策略信号)
    │      └── TimingStrategy.get_timing_result() → is_sell?
    │
    ├── 2. 检查池移除条件 (_check_pool_removal)
    │      ├── 支撑位跌破: close < support × 0.98
    │      ├── 趋势失败: close < MA10 或回归斜率 ≤ 0
    │      └── 资金流异常: 5 日主力净流出 < 阈值
    │
    ├── 3. 执行选股 (前一交易日)
    │      └── StrategyRegistry.run_all() → 信号列表
    │
    ├── 4. 评分筛选
    │      └── BacktestScoreCalculator → 5 维评分 + 一票否决
    │
    ├── 5. 过滤并加入买入候选池
    │      ├── 评分 ≥ 阈值
    │      ├── 无一票否决
    │      └── BuyPreFilter (K 线形态过滤)
    │
    ├── 6. 处理买入
    │      ├── KellyCalculator → 仓位计算
    │      ├── 计算交易成本
    │      └── 更新持仓
    │
    └── 7. 计算当日总资产
           └── 现金 + 持仓市值
```

### 交易成本计算

```python
def calculate_backtest_cost(amount, price, is_sell=False):
    # 佣金: 0.015%, 最低 5 元
    commission = max(amount * price * 0.00015, 5)
    # 印花税: 0.1% (仅卖出)
    stamp_tax = amount * price * 0.001 if is_sell else 0
    # 过户费: 0.001% (上海股票)
    transfer_fee = amount * price * 0.00001 if is_shanghai else 0
    return commission + stamp_tax + transfer_fee
```

### Kelly 仓位管理

使用 Kelly 公式计算最优仓位：

```
Kelly% = (胜率 × 盈亏比 - 败率) / 盈亏比
实际仓位 = Kelly% × 缩放系数
```

通过 `KellyCalculator.calculate_position_amount_with_params()` 实现，参数在 `config/strategy_kelly_config.yaml`。

### 风控机制

| 机制 | 说明 |
|------|------|
| 移动止损 | 跟踪持仓最高盈利，回撤触发止损 |
| 亏损冷却池 | 止损后进入冷却期，避免频繁交易 |
| 连续亏损计数 | 连续亏损 N 次后暂停买入 |
| 资金流冷却池 | 资金流异常后 3 个交易日内可恢复 |
| 单股最大买入次数 | 默认 6 次 |
| 每日最大买入数 | 默认 5 次 |
| 最低现金阈值 | 2000 元 |

---

## 二、实盘运行器 StrategyRunner

`trading/strategy_runner.py` — 约 4165 行，回测引擎的实盘版本。

### 与回测引擎的关键区别

| 特性 | BacktestEngine | StrategyRunner |
|------|---------------|----------------|
| 数据来源 | 历史数据预加载 | 实时行情 + 历史数据 |
| 状态持久化 | 无 | JSON 文件 (data/running/) |
| 交易日确定 | 交易日历 | `get_working_date()` 智能判断 |
| 除权除息 | 无 | `_daily_exdividend_check()` |
| PTrade 导出 | 无 | CSV 格式信号导出 |
| 信号执行 | 模拟 | `execute_signal()` 序列化执行 |

### 持久化文件

```
data/running/
├── portfolio_2026-06-03.json    # 当日持仓
├── signals_2026-06-03.json     # 当日信号
├── buy_candidate_pool.json     # 买入候选池
└── KHunter_signals_20260603.csv # PTrade 导出
```

### 工作日期逻辑

```python
def get_working_date():
    now = datetime.now()
    if is_trading_day(now):
        if now.hour >= 15:  # 收盘后
            return today
        else:              # 盘中
            return yesterday
    else:                  # 非交易日
        return last_trading_day
```

### 除权除息处理

`_daily_exdividend_check()` 在每日初始化时检查：
- 调整持仓成本价
- 调整信号价格
- 调整支撑位

---

## 三、评分系统

### 五维评分架构

```
StockScore / BacktestScoreCalculator
    │
    ├── TechnicalScorer (技术面)    -- 权重 35%
    ├── MoneyflowScorer (资金流)    -- 权重 35%
    ├── FundamentalScorer (基本面)  -- 权重 10%
    ├── SectorScorer (板块)         -- 权重 10%
    └── EventScorer (事件)          -- 权重 10%
```

### 评分等级

| 分数 | 等级 | 含义 |
|------|------|------|
| ≥ 80 | 强烈推荐 | 多维度高度一致 |
| 60-79 | 推荐 | 多数维度正面 |
| 40-59 | 中性 | 维度分化 |
| 20-39 | 谨慎 | 多数维度负面 |
| < 20 | 回避 | 全面负面 |
| -100 | 淘汰 | 一票否决 |

### 各评分器详解

#### TechnicalScorer（技术面评分）

```
得分 = Σ(策略权重 × 命中标志)
```

- 权重来自 `config/strategy_weights.json`
- 每个策略命中 +50 分（正面）或 -80/-50 分（负面）
- **一票否决**：M 头策略 + 多死叉共振策略同时命中 → 直接 -100

#### MoneyflowScorer（资金流评分）

四个子维度：
| 子维度 | 权重 | 数据来源 |
|--------|------|----------|
| 主力净流入 | 55% | Tushare moneyflow_ths |
| 大单占比 | 10% | Tushare moneyflow_ths |
| 北向资金 | 10% | Tushare hk_hold |
| 资金方向 | 25% | 综合计算 |

一票否决：5 日主力净流出 < -10000 万元 或 分发出货信号

#### FundamentalScorer（基本面评分）

三个子维度：
| 子维度 | 数据来源 |
|--------|----------|
| 净利润同比增长 | Tushare fina_indicator |
| ROE | Tushare fina_indicator |
| 经营现金流/营收 | Tushare fina_indicator |

一票否决：净利润下降 > 50% 或 ROE < -5%

#### SectorScorer（板块评分）

两个子维度：
| 子维度 | 数据来源 |
|--------|----------|
| 板块排名 | Tushare ths_daily |
| 板块资金流 | Tushare moneyflow_ind_ths |

一票否决：板块得分 = -100

#### EventScorer（事件评分）

| 事件类型 | 有效期 | 分值 |
|----------|--------|------|
| 预增公告 | 30 天 | +30 |
| 回购公告 | 50 天 | +25 |
| 机构买入 | 20 天 | +20 |
| 预减公告 | 30 天 | -30 |
| 股东减持 | 30 天 | -25 |
| 异常波动 | 5 天 | -15 |
| ST 状态 | 持续 | 一票否决 |
| 业绩暴跌 (>80%) | 持续 | 一票否决 |

### 评分器对比

| 特性 | StockScoreCalculator | BacktestScoreCalculator |
|------|---------------------|------------------------|
| 使用场景 | 实盘 | 回测 |
| 缓存 | 无 | 按日期缓存 |
| 短路评估 | 无 | 有（首个否决即停止） |
| 结果持久化 | 保存到数据库 | 不保存 |
| Tushare 不可用 | 报错 | 降级为简化评分 |
| 并发 | ThreadPoolExecutor (5) | 单线程 |

---

## 四、支撑位与池移除

### 支撑位计算

`trading/khunter_support_calculator.py` — 4 种方法：

```python
# 通过 config/support_methods.yaml 按策略映射
"ma20"        → df['close'].rolling(20).mean().iloc[-1]
"key_close_5" → 关键日收盘价 × 0.95
"key_open"    → 关键日开盘价
"key_close"   → 关键日收盘价
```

### 池移除条件 (`_check_pool_removal`)

三个移除条件，配置在 `config/pool_removal_config.yaml`：

```
1. 支撑位跌破 (始终生效)
   条件: close < support_level × 0.98

2. 趋势失败 (持仓 ≥ min_hold_days 后生效)
   条件: close < MA10
         或 20 日线性回归斜率 ≤ 0
         或 R² < 0.3

3. 资金流异常 (持仓 ≥ min_hold_days 后生效)
   条件: 5 日主力净流出 < 阈值
         或 分发出货信号
   机制: 首次触发进入 3 交易日冷却期
         冷却期内再次触发才真正移除
```

---

## 五、关键算法

### 1. Kelly 公式仓位管理

```
f* = (p × b - q) / b

其中:
  f* = 最优仓位比例
  p  = 胜率
  q  = 败率 (1-p)
  b  = 盈亏比

实际仓位 = f* × 缩放系数 (通常 0.5)
```

### 2. 趋势验证 (线性回归)

```python
from scipy.stats import linregress
slope, intercept, r_value, p_value, std_err = linregress(x, y)
# 上升趋势: slope > 0 且 R² ≥ 0.3 且 p < 0.05
```

### 3. 资金流冷却机制

```
首次触发 → 记录触发日，进入冷却期 (3 交易日)
冷却期内未再次触发 → 退出冷却期，继续持有
冷却期内再次触发 → 执行移除
```

### 4. 评分短路评估 (回测优化)

```python
# BacktestScoreCalculator 的优化策略
for scorer in [technical, moneyflow, fundamental, sector, event]:
    score = scorer.score(stock)
    if score.is_veto:  # 一票否决
        return Score(veto=True)  # 跳过后续评分
```

---

## 六、关键文件索引

| 文件 | 行数 | 职责 |
|------|------|------|
| `strategy_runner.py` | ~4165 | 实盘运行器 |
| `backtest_engine.py` | ~2500 | 回测引擎 |
| `routes.py` | - | API 路由 (96KB) |
| `timing_strategies.py` | - | 5 种择时策略 |
| `stock_score_calculator.py` | - | 实盘评分器 |
| `backtest_scorer.py` | - | 回测评分器 |
| `stock_score_models.py` | - | 评分数据模型 |
| `technical_scorer.py` | - | 技术面评分 |
| `moneyflow_scorer.py` | - | 资金流评分 |
| `fundamental_scorer.py` | - | 基本面评分 |
| `sector_scorer.py` | - | 板块评分 |
| `event_scorer.py` | - | 事件评分 |
| `khunter_support_calculator.py` | - | 支撑位计算 |
| `buy_filter.py` | - | 买入前 K 线过滤 |
| `trading_plan_generator.py` | - | 交易计划生成 |
