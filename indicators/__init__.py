"""indicators/ — 统一技术指标模块

所有技术指标函数自动检测输入排序方向（升序/降序），
内部统一在升序数据上计算，输出保持与输入相同的排序。

用法示例::

    from indicators import ma, rsi, kdj

    # 直接调用，无需关心排序
    ma_series = ma(close_series, 20)
    rsi_series = rsi(df, 14)
    k, d, j = kdj(df, 9, 3, 3)
"""

# 排序检测工具
from indicators._order import ensure_ascending, is_ascending

# 移动平均线
from indicators.ma import ema, ma, sma

# 振荡指标
from indicators.oscillator import kdj, macd, rsi

# 波动率指标
from indicators.volatility import atr, bollinger

# 区间辅助函数
from indicators.range import exist, hhv, llv, ref

# 缓存包装器
from indicators._cache import CachedIndicators

__all__ = [
    # 排序检测
    "is_ascending",
    "ensure_ascending",
    # 移动平均线
    "ma",
    "ema",
    "sma",
    # 振荡指标
    "rsi",
    "kdj",
    "macd",
    # 波动率指标
    "atr",
    "bollinger",
    # 区间辅助函数
    "llv",
    "hhv",
    "ref",
    "exist",
    # 缓存
    "CachedIndicators",
]
