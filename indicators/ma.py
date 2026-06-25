"""indicators/ma.py — 移动平均线指标

提供 MA、EMA、SMA 三个移动平均线函数。
所有函数自动检测输入排序方向，内部统一在升序数据上计算，输出保持与输入相同的排序。
"""

from __future__ import annotations

import pandas as pd

from indicators._order import is_ascending


def ma(series: pd.Series, n: int) -> pd.Series:
    """简单移动平均线 (SMA)。

    对输入排序方向自动检测。升序/降序输入均可，输出与输入同序。

    Args:
        series: 价格序列
        n: 窗口周期

    Returns:
        MA 序列，长度与输入相同，索引与输入相同
    """
    original_index = series.index
    ascending = is_ascending(series)
    if not ascending:
        series = series.iloc[::-1].reset_index(drop=True)
    result = series.rolling(window=n, min_periods=1).mean()
    if not ascending:
        result = result.iloc[::-1].reset_index(drop=True)
    # 恢复原始索引
    result.index = original_index
    return result


def ema(series: pd.Series, n: int) -> pd.Series:
    """指数移动平均线 (EMA)。

    对输入排序方向自动检测。升序/降序输入均可，输出与输入同序。

    Args:
        series: 价格序列
        n: 窗口周期（span）

    Returns:
        EMA 序列，长度与输入相同，索引与输入相同
    """
    original_index = series.index
    ascending = is_ascending(series)
    if not ascending:
        series = series.iloc[::-1].reset_index(drop=True)
    result = series.ewm(span=n, adjust=False, min_periods=1).mean()
    if not ascending:
        result = result.iloc[::-1].reset_index(drop=True)
    # 恢复原始索引
    result.index = original_index
    return result


def sma(series: pd.Series, n: int, m: int) -> pd.Series:
    """通达信风格加权移动平均。

    公式: Y = (X * M + Y_prev * (N - M)) / N
    通达信 KDJ、RSI 等指标内部使用的递推平均。

    Args:
        series: 价格序列
        n: 窗口周期
        m: 权重

    Returns:
        SMA 序列，长度与输入相同，索引与输入相同
    """
    original_index = series.index
    ascending = is_ascending(series)
    if not ascending:
        series = series.iloc[::-1].reset_index(drop=True)

    result = pd.Series(index=series.index, dtype=float)
    result.iloc[0] = series.iloc[0]
    for i in range(1, len(series)):
        result.iloc[i] = (series.iloc[i] * m + result.iloc[i - 1] * (n - m)) / n

    if not ascending:
        result = result.iloc[::-1].reset_index(drop=True)
    # 恢复原始索引
    result.index = original_index
    return result
