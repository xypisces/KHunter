# 统一技术指标模块 PRD

> **状态**: 待实施 | **优先级**: Strong | **创建日期**: 2026-06-25

---

## 背景

KHunter 代码库中存在至少 8 个独立位置计算技术指标（MA、EMA、RSI、KDJ、MACD 等），它们对数据排序的假设不同、算法实现不一致、缺乏统一缓存。这导致：

- 同一指标在不同模块产生不同数值
- 开发者理解"MA 怎么算"需要检查多个文件
- 排序假设不一致产生潜在 bug
- 重复计算浪费性能

---

## 目标

创建 `indicators/` 顶级包，统一所有技术指标实现。内部处理升序/降序转换，对外暴露统一接口。

---

## 涉及文件清单

### 需要迁移的模块（8+ 处）

| # | 文件 | 当前指标 | 排序假设 | 使用方 |
|---|---|---|---|---|
| 1 | `utils/technical.py` | MA, EMA, SMA, LLV, HHV, REF, EXIST, KDJ, RSI, MACD, zhixing_trend | 降序（反转计算） | 16+ 策略文件 |
| 2 | `trading/technical_indicators.py` | MA, ATR, RSI, Bollinger, KDJ, MACD | 升序 | `limit_up_sideways_strategy.py` |
| 3 | `utils/support_level_calculator.py` | MA（内联 rolling） | 升序 | 支撑位计算 |
| 4 | `stock_analyzer/technical_analyzer.py` | MA, MACD, RSI, Bollinger, KDJ | 升序 | 技术分析模块 |
| 5 | `utils/kline_chart.py` | MA14/28/57/114（内联） | 升序 | K 线图生成 |
| 6 | `utils/stock_filter.py` | MA（内联） | 升序 | 股票筛选 |
| 7 | `utils/buy_signal_judger.py` | MA（内联） | 升序 | 买入信号判断 |
| 8 | `trading/support_strategy.py` | MA20（内联） | 升序 | 支撑策略 |

### 其他包含内联指标计算的文件

- `utils/market_temperature.py` — MA5
- `trading/vectorbt_strategies.py` — rolling min/max/MA
- `trading/turtle_strategy.py` — rolling high/low
- `trading/ptrade/ptradesample.py` — rolling high/low
- `web_server.py` — KDJ 调用

---

## 设计决策

### 1. 内部排序约定：升序

`pandas` 的 `.rolling()` / `.ewm()` 天然按索引顺序工作，升序是最自然的。当前大多数内联实现已经是升序，`utils/technical.py` 内部也是先转成升序再算。

### 2. 排序检测与处理

`_order.py` 提供排序检测工具函数。**每个指标函数内部封装完整的排序处理流程**（检测 → 转换 → 计算 → 恢复），不依赖调用方保证排序。

```python
def ma(series: pd.Series, n: int) -> pd.Series:
    ascending = _is_ascending(series)
    if not ascending:
        series = series.iloc[::-1].reset_index(drop=True)
    result = series.rolling(window=n, min_periods=1).mean()
    if not ascending:
        result = result.iloc[::-1].reset_index(drop=True)
    return result
```

边界情况处理：
- 单行数据：不做处理
- 空 DataFrame：抛异常
- Series 输入：调用方自行保证排序，或通过参数指定
- 日期相同：按索引顺序处理

### 3. 算法统一

| 指标 | 统一算法 | 理由 |
|---|---|---|
| RSI | EWM（指数加权） | Wilder 原始定义，通达信标准 |
| KDJ | 滚动 + 循环（递推公式） | 通达信标准，`K = 2/3 * K_prev + 1/3 * RSV` |
| ATR | 标准公式（含前一日收盘价） | `max(high - low, abs(high - close_prev), abs(low - close_prev))` |
| MA/EMA | 标准 pandas rolling/ewm | 无争议 |
| MACD | 标准 EWM | 无争议 |
| Bollinger | rolling mean ± k * std | 无争议 |

**注意**：RSI 和 KDJ 的算法变更会导致数值变化，与旧实现不兼容。这是有意为之——统一到正确算法比保持错误一致性更重要。

### 4. API 风格：纯函数 + 可选缓存包装器

```python
# indicators/__init__.py

# 核心：纯函数，无状态，直接调用
def ma(series: pd.Series, n: int) -> pd.Series: ...
def ema(series: pd.Series, n: int) -> pd.Series: ...
def rsi(series: pd.Series, period: int) -> pd.Series: ...
def kdj(df: pd.DataFrame, n=9, m1=3, m2=3) -> tuple[pd.Series, pd.Series, pd.Series]: ...
def atr(df: pd.DataFrame, period: int) -> pd.Series: ...

# 可选：缓存包装器
class CachedIndicators: ...
```

策略文件用纯函数（最简单），回测/批量场景用 CachedIndicators。

### 5. 返回值：tuple + 类型注解

多个返回值统一用 tuple，配合类型注解：

```python
def kdj(df: pd.DataFrame, n: int = 9, m1: int = 3, m2: int = 3) -> tuple[pd.Series, pd.Series, pd.Series]:
    """返回 (K, D, J)"""
    ...
```

### 6. 模块结构

```
indicators/
├── __init__.py          # 对外暴露所有函数
├── _order.py            # 排序检测与转换（内部模块）
├── ma.py                # MA, EMA, SMA（通达信风格加权）
├── oscillator.py        # RSI, KDJ, MACD
├── volatility.py        # ATR, Bollinger Bands
├── range.py             # LLV, HHV, REF, EXIST（通达信辅助函数）
├── support.py           # 支撑位/阻力位计算（从 support_level_calculator.py 迁移）
├── zhixing.py           # 执行趋势（项目特有自定义指标）
└── _cache.py            # CachedIndicators 包装器
```

### 7. 缓存设计

模块级单例 + LRU 上限：

```python
class CachedIndicators:
    def __init__(self, max_stocks: int = 1000):
        self._cache: dict[str, dict[str, pd.Series]] = {}
        self._max_stocks = max_stocks

    def ma(self, series: pd.Series, n: int, stock_code: str) -> pd.Series: ...
    def clear(self, stock_code: str | None = None) -> None: ...
```

- 全局共享，所有调用方共享同一份缓存
- LRU 上限 1000 只股票，避免内存爆炸
- 支持按股票代码清除缓存

---

## 迁移策略

按策略逐个完整迁移：每个策略一次性切到新接口，一个策略改完、测试通过后才改下一个。

### 执行顺序

1. 创建 `indicators/` 模块，实现所有指标函数
2. 写单元测试验证新模块的正确性
3. 逐个策略迁移：改一个策略 → 跑回测验证 → 下一个
4. 迁移工具模块（kline_chart、stock_filter 等）
5. 迁移 stock_analyzer
6. 清理旧模块（标记废弃 + deprecation warning）

### 旧模块处理

迁移完成后，旧模块标记废弃，保留 deprecation warning 转发层，约定下个大版本删除：

```python
# utils/technical.py（迁移完成后）
import warnings
from indicators import ma as _ma

def MA(series, n):
    warnings.warn("utils.technical.MA 已废弃，请使用 indicators.ma",
                  DeprecationWarning, stacklevel=2)
    return _ma(series, n)
```

---

## 验收标准

- [ ] 所有 MA/EMA/ATR/RSI/KDJ/MACD/Bollinger 计算在 `indicators/` 模块中
- [ ] 内部处理升序/降序转换，每个函数自包含
- [ ] 对外暴露统一纯函数接口
- [ ] RSI 统一为 EWM 算法
- [ ] KDJ 统一为滚动+循环算法
- [ ] ATR 使用标准公式
- [ ] 8+ 处调用方全部迁移到新接口
- [ ] 单元测试覆盖所有指标（正确性 + 回归 + 排序一致性 + 集成）
- [ ] CachedIndicators 提供可选缓存层
- [ ] 旧模块标记废弃并保留 deprecation warning

---

## 测试策略

### 第一层：指标正确性测试
- 每个指标函数用已知输入/输出验证
- 对比业界标准库的结果

### 第二层：回归测试
- 从数据库取真实股票数据
- 对比旧实现和新实现的结果（允许浮点误差 1e-10）
- RSI 和 KDJ 因算法变更，不做新旧对比

### 第三层：排序一致性测试
- 同一份数据，分别传入升序和降序版本
- 验证新模块的输出一致

### 第四层：集成测试
- 逐个策略跑完整选股流程
- 对比迁移前后的选股结果

---

## 风险

| 风险 | 影响 | 缓解措施 |
|---|---|---|
| RSI/KDJ 算法变更导致回测结果不可复现 | 高 | 记录变更前后差异，必要时保留旧算法作为可选参数 |
| 迁移过程中引入 bug | 中 | 逐策略迁移 + 回归测试 |
| 缓存导致内存占用过高 | 低 | LRU 上限 + 支持按股票清除 |
| 性能问题（KDJ 循环） | 低 | 缓存优化，必要时引入 numba |
