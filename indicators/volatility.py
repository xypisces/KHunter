"""indicators/volatility.py — 波动率指标

提供 ATR 和 Bollinger Bands 两个波动率指标函数。
所有函数自动检测输入排序方向，内部统一在升序数据上计算，输出保持与输入相同的排序。
"""

from __future__ import annotations

import pandas as pd

from indicators._order import is_ascending


def atr(df: pd.DataFrame, period: int = 14) -> pd.Series:
    """平均真实波幅 (ATR)。

    标准公式：
        TR = max(HIGH - LOW, |HIGH - CLOSE_prev|, |LOW - CLOSE_prev|)
        ATR = EWM(TR, period)

    Args:
        df: DataFrame，必须包含 'high', 'low', 'close' 列
        period: ATR 周期，默认 14

    Returns:
        ATR 序列，长度与输入相同
    """
    ascending = is_ascending(df["date"])
    if not ascending:
        df = df.iloc[::-1].reset_index(drop=True)

    high = df["high"]
    low = df["low"]
    close_prev = df["close"].shift(1)

    tr1 = high - low
    tr2 = (high - close_prev).abs()
    tr3 = (low - close_prev).abs()
    tr = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)
    # 第一行没有前收盘价，TR = HIGH - LOW
    tr.iloc[0] = high.iloc[0] - low.iloc[0]

    result = tr.ewm(span=period, adjust=False, min_periods=1).mean()

    if not ascending:
        result = result.iloc[::-1].reset_index(drop=True)
    return result


def bollinger(
    df: pd.DataFrame, period: int = 20, multiplier: float = 2.0
) -> tuple[pd.Series, pd.Series, pd.Series]:
    """布林带 (Bollinger Bands)。

    公式：
        中轨 = MA(CLOSE, period)
        上轨 = 中轨 + multiplier * STD(CLOSE, period)
        下轨 = 中轨 - multiplier * STD(CLOSE, period)

    Args:
        df: DataFrame，必须包含 'close' 列
        period: 周期，默认 20
        multiplier: 标准差倍数，默认 2.0

    Returns:
        (mid, upper, lower) 三个 Series，长度与输入相同
    """
    ascending = is_ascending(df["date"])
    if not ascending:
        df = df.iloc[::-1].reset_index(drop=True)

    mid = df["close"].rolling(window=period, min_periods=1).mean()
    std = df["close"].rolling(window=period, min_periods=1).std().fillna(0.0)
    upper = mid + multiplier * std
    lower = mid - multiplier * std

    if not ascending:
        mid = mid.iloc[::-1].reset_index(drop=True)
        upper = upper.iloc[::-1].reset_index(drop=True)
        lower = lower.iloc[::-1].reset_index(drop=True)
    return mid, upper, lower
