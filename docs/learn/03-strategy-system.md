# 策略系统详解

## 架构概览

KHunter 的策略系统分为两层：
- **选股策略**（`strategy/`）— 继承 `BaseStrategy`，决定"买什么"
- **择时策略**（`trading/timing_strategies.py`）— 继承 `TimingStrategy`，决定"何时买卖"

## 一、选股策略系统

### BaseStrategy 基类

`strategy/base_strategy.py` 定义了所有选股策略的统一接口。

#### 必须实现的方法

```python
class BaseStrategy(ABC):
    def calculate_indicators(self, df: pd.DataFrame) -> pd.DataFrame:
        """计算技术指标，返回增强后的 DataFrame"""
        ...

    def select_stocks(self, df: pd.DataFrame, stock_name: str = '') -> list:
        """选股逻辑，返回信号列表"""
        ...
```

#### 标准执行流程（模板方法）

`execute_selection()` 定义了所有策略共享的执行管道：

```
1. _validate_data()           -- 数据完整性检查
   ├── 空数据/None 检查
   ├── 最少 20 行数据
   ├── 必需列检查 (date, open, high, low, close, volume)
   └── 退市股过滤 (最新数据超过 5 年)

2. _validate_stock_name()     -- 股票名称过滤
   └── 过滤 ST、*ST、退市股

3. quick_filter()             -- 快速预筛选（可选覆盖）
   └── 基于价格的粗筛，默认通过所有

4. calculate_indicators()     -- 计算技术指标（子类实现）

5. select_stocks()            -- 选股逻辑（子类实现）
```

### StrategyRegistry 注册器

`strategy/strategy_registry.py` 负责策略的发现、注册和管理。

#### 自动注册流程

```
auto_register_from_directory("strategy")
  │
  ├── 1. 扫描 strategy/*.py（排除 _ 开头的文件）
  ├── 2. importlib.import_module() 动态导入
  ├── 3. 查找 BaseStrategy 的子类
  ├── 4. 跳过 "事件驱动策略"
  └── 5. register(strategy_class, name)
         ├── 从 strategy_params.yaml 加载参数
         ├── 实例化策略类
         ├── 附加元数据（display_name, icon, color 等）
         └── 缓存到 self.strategies[name]
```

#### 热加载机制

```python
def get_strategy(self, name):
    # 每次调用都重新读取 YAML 并重新实例化
    # → 修改 strategy_params.yaml 后无需重启即可生效
```

#### 全局单例

```python
from strategy.strategy_registry import get_registry
registry = get_registry()  # 全局唯一
registry.auto_register_from_directory("strategy")
```

### 14 个选股策略一览

| # | 类名 | 中文名 | 核心逻辑 |
|---|------|--------|----------|
| 1 | `BottomTrendInflectionStrategy` | 底部趋势拐点 | 深跌 >45% + MACD 底背离 + 放量 >2.5x + 涨幅 >8% |
| 2 | `ImmortalGuidanceStrategy` | 仙人指路 | 涨幅 >8% + 长上影线 >4% + 放量 >1.5x + 上升趋势 |
| 3 | `LimitUpPullbackStrategy` | 涨停回马枪 | 涨停 + 回调 (1-9天, 0-15%) + 缩量 + 支撑守住 |
| 4 | `LimitUpSidewaysStrategy` | 涨停横盘 | 涨停 + 横盘整理 (1-10天) + 缩量 + KDJ/MACD 金叉 |
| 5 | `MorningStarStrategy` | 启明星 | 3 K 线启明星形态 + 放量 >1.5x |
| 6 | `MultiGoldenCrossStrategy` | 多金叉共振 | MA 金叉 + KDJ 金叉 + MACD 金叉 (1 天内共振) |
| 7 | `MultiPartyCannonStrategy` | 多方炮 | 两阳夹一阴 + 阴线缩量 + 第三阳放量 |
| 8 | `ResistanceBreakoutStrategy` | 阻力位突破 | 突破 60 日高点 + 涨幅 >9% + 放量 >2x |
| 9 | `Strategy2560Selection` | 2560 战法 | 站上 25 日均线 + 5 日量能上穿 60 日量能 |
| 10 | `StrongWashWeakToStrongStrategy` | 强势洗盘弱转强 | 大阳线 >8% + 洗盘阴线 + 反转阳线 (3 天内) |
| 11 | `TrendAccelerationInflectionStrategy` | 趋势加速拐点 | 线性回归上升 (R2>0.5) + 放量长阳 + 距低点 <15% |
| 12 | `TrendResonanceReversalStrategy` | 趋势共振反转 | RSI 超卖突破 + MA5/MA20 金叉 + MACD 金叉 (3 天内) |
| 13 | `TrendStartStrategy` | 趋势起点 | MACD 零轴上金叉 + 布林中轨上穿 + 阳线 + 站上 MA5 |
| 14 | `WBottomStrategy` | W 底 | 双底形态 + 颈线突破放量 + 趋势反转确认 |

### 信号数据结构

每个策略的 `select_stocks()` 返回信号列表，每个信号是一个 dict：

```python
{
    "signal_type": "buy",           # 信号类型
    "strategy_name": "策略名",      # 产生信号的策略
    "date": "2026-06-03",          # 信号日期
    "price": 15.50,                # 信号价格
    "reason": "MACD 底背离 + 放量", # 信号原因描述
    "support_level": 14.20,        # 支撑位（可选）
    "resistance_level": 17.80,     # 阻力位（可选）
    # ... 其他策略特有字段
}
```

### 支撑位计算

每个策略可配置 `support_method`，决定如何计算买入后的止损参考位：

| 方法 | 计算方式 |
|------|----------|
| `ma20` | 20 日均线 |
| `key_close_5` | 关键日收盘价 × 0.95 |
| `key_open` | 关键日开盘价 |
| `key_close` | 关键日收盘价 |

配置在 `config/strategy_params.yaml` 的 `support_method` 字段。

### B1 模式匹配子系统

独立于规则策略的另一种选股方式，使用 DTW（动态时间规整）进行形态相似度匹配：

```
pattern_config.py         -- 10 个历史成功案例配置
pattern_feature_extractor.py -- 特征向量提取
pattern_matcher.py        -- DTW 相似度计算
pattern_library.py        -- 案例库管理
```

相似度权重：
- 趋势结构: 30%
- KDJ 状态: 20%
- 量能形态: 25%
- 价格形态: 25%

使用方式：`uv run main.py run --b1-match --min-similarity 60`

### 并行执行

`strategy/parallel_strategy_executor.py` 使用 `ProcessPoolExecutor` 多进程执行策略分析。

### 参数管理

- `param_lock.py` — 参数哈希锁，检测未授权修改
- `param_tracker.py` — 参数变更日志审计

---

## 二、择时策略系统

### TimingStrategy 基类

`trading/timing_strategies.py` 定义择时策略接口：

```python
class TimingStrategy:
    def get_timing_result(self, df, position, support_level, resistance_level):
        """返回 TimingResult 对象"""
        ...
```

### TimingResult 数据结构

```python
TimingResult:
    is_buy: bool           # 是否买入
    is_sell: bool          # 是否卖出
    buy_quantity: int      # 买入数量
    sell_quantity: int     # 卖出数量
    trade_type: str        # buy / add / sell / reduce
    support_level: float   # 支撑位
    resistance_level: float # 阻力位
```

### 5 种择时策略

| 策略 | 类名 | 核心逻辑 |
|------|------|----------|
| 海龟 | `TurtleStrategy` | 唐奇安通道突破 + ATR 仓位管理 + 金字塔加仓 |
| RSI | `RSIStrategy` | RSI 超买超卖信号 |
| 布林 | `BollingerStrategy` | 布林带均值回归 |
| 支撑 | `SupportStrategy` | 支撑位反弹 |
| MACD+布林 | `ShunShiBaoStrategy` | MACD + 布林带组合（需 feature config 校验） |

### 工厂模式创建

```python
from trading.timing_strategies import TimingStrategyFactory

strategy = TimingStrategyFactory.create("turtle")
result = strategy.get_timing_result(df, position, support, resistance)
```

---

## 三、配置文件

### strategy_params.yaml（51KB）

策略参数的中央存储，结构：

```yaml
strategies:
  BottomTrendInflectionStrategy:
    display_name: "底部趋势拐点"
    description: "策略描述"
    icon: "📈"
    color: "#4CAF50"
    support_method: "ma20"
    param_groups:
      - name: "核心参数"
        description: "控制选股条件"
    param_details:
      min_decline:
        default: 45
        description: "最小跌幅"
        display_name: "跌幅阈值"
        group: "核心参数"
        min: 20
        max: 80
        type: "float"
    params:
      min_decline: 45
      volume_ratio: 2.5
      # ...
```

### strategy_order.yaml

策略执行和显示顺序：

```yaml
strategy_order:
  - order: 1
    name: BottomTrendInflectionStrategy
    display_name: 底部趋势拐点
  - order: 2
    name: TrendAccelerationInflectionStrategy
    display_name: 趋势加速拐点
  # ... 共 16 个策略，order 1-30
```

### strategy_weights.json

技术评分权重：

```json
{
  "strategies": {
    "底部趋势拐点": {"weight": 50, "direction": "positive"},
    "M头策略": {"weight": -80, "direction": "negative"},
    "多死叉共振策略": {"weight": -50, "direction": "negative"}
  },
  "veto_config": {
    "enabled": true,
    "conditions": ["M头策略", "多死叉共振策略"],
    "score": -100
  }
}
```

---

## 四、扩展新策略

### 步骤

1. 在 `strategy/` 目录创建新 `.py` 文件
2. 继承 `BaseStrategy`，实现两个抽象方法
3. 在 `config/strategy_params.yaml` 添加配置
4. 在 `config/strategy_order.yaml` 添加顺序
5. （可选）在 `config/strategy_weights.json` 添加评分权重

### 模板

```python
from strategy.base_strategy import BaseStrategy
import pandas as pd

class MyNewStrategy(BaseStrategy):
    def __init__(self, params=None):
        super().__init__("我的新策略", params)

    def calculate_indicators(self, df: pd.DataFrame) -> pd.DataFrame:
        # 计算技术指标
        df['my_indicator'] = ...
        return df

    def select_stocks(self, df: pd.DataFrame, stock_name: str = '') -> list:
        signals = []
        # 选股逻辑
        if some_condition:
            signals.append({
                "signal_type": "buy",
                "strategy_name": self.name,
                "date": df.iloc[-1]['date'],
                "price": df.iloc[-1]['close'],
                "reason": "满足条件",
            })
        return signals
```

系统会自动发现并注册，无需修改任何注册代码。
