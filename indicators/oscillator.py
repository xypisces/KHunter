"""indicators/oscillator.py — 振荡指标

提供 RSI、KDJ、MACD 三个振荡指标函数。
所有函数自动检测输入排序方向，内部统一在升序数据上计算，输出保持与输入相同的排序。
"""

from __future__ import annotations

import pandas as pd

from indicators._order import is_ascending
from indicators.ma import sma as _sma


def rsi(df: pd.DataFrame, period: int = 14) -> pd.Series:
    """相对强弱指标 (RSI)。

    通达信公式：RSI = SMA(MAX(CLOSE-LC,0), N, 1) / SMA(ABS(CLOSE-LC), N, 1) * 100
    这里使用 EWM 实现，等价于通达信的 SMA 加权方式。

    Args:
        df: DataFrame，必须包含 'close' 列
        period: RSI 周期，默认 14

    Returns:
        RSI 序列，值域 0-100，长度与输入相同，索引与输入相同
    """
    original_index = df.index
    ascending = is_ascending(df["date"])
    if not ascending:
        df = df.iloc[::-1].reset_index(drop=True)

    close = df["close"]
    delta = close.diff()
    gain = delta.where(delta > 0, 0.0)
    loss = (-delta).where(delta < 0, 0.0)

    avg_gain = gain.ewm(com=period - 1, adjust=False, min_periods=1).mean()
    avg_loss = loss.ewm(com=period - 1, adjust=False, min_periods=1).mean()

    rs = avg_gain / avg_loss
    result = 100 - (100 / (1 + rs))
    result = result.fillna(50.0)

    if not ascending:
        result = result.iloc[::-1].reset_index(drop=True)

    # 恢复原始索引
    result.index = original_index
    return result


def kdj(
    df: pd.DataFrame, n: int = 9, m1: int = 3, m2: int = 3
) -> tuple[pd.Series, pd.Series, pd.Series]:
    """KDJ 随机指标。

    通达信公式：
        RSV = (CLOSE - LLV(LOW, N)) / (HHV(HIGH, N) - LLV(LOW, N)) * 100
        K = SMA(RSV, M1, 1)
        D = SMA(K, M2, 1)
        J = 3*K - 2*D

    Args:
        df: DataFrame，必须包含 'high', 'low', 'close' 列
        n: RSV 周期，默认 9
        m1: K 平滑周期，默认 3
        m2: D 平滑周期，默认 3

    Returns:
        (K, D, J) 三个 Series，长度与输入相同，索引与输入相同
    """
    original_index = df.index
    ascending = is_ascending(df["date"])
    if not ascending:
        df = df.iloc[::-1].reset_index(drop=True)

    low_min = df["low"].rolling(window=n, min_periods=1).min()
    high_max = df["high"].rolling(window=n, min_periods=1).max()

    rsv = (df["close"] - low_min) / (high_max - low_min) * 100
    rsv = rsv.fillna(50.0)

    k = _sma(rsv, m1, 1)
    d = _sma(k, m2, 1)
    j = 3 * k - 2 * d

    if not ascending:
        k = k.iloc[::-1].reset_index(drop=True)
        d = d.iloc[::-1].reset_index(drop=True)
        j = j.iloc[::-1].reset_index(drop=True)

    # 恢复原始索引
    k.index = original_index
    d.index = original_index
    j.index = original_index
    return k, d, j


def macd(
    df: pd.DataFrame,
    fast: int = 12,
    slow: int = 26,
    signal: int = 9,
) -> tuple[pd.Series, pd.Series, pd.Series]:
    """MACD 指标。

    标准公式：
        DIF = EMA(CLOSE, fast) - EMA(CLOSE, slow)
        DEA = EMA(DIF, signal)
        MACD = 2 * (DIF - DEA)

    Args:
        df: DataFrame，必须包含 'close' 列
        fast: 快线周期，默认 12
        slow: 慢线周期，默认 26
        signal: 信号线周期，默认 9

    Returns:
        (DIF, DEA, MACD) 三个 Series，长度与输入相同，索引与输入相同
    """
    original_index = df.index
    ascending = is_ascending(df["date"])
    if not ascending:
        df = df.iloc[::-1].reset_index(drop=True)

    ema_fast = df["close"].ewm(span=fast, adjust=False, min_periods=1).mean()
    ema_slow = df["close"].ewm(span=slow, adjust=False, min_periods=1).mean()

    dif = ema_fast - ema_slow
    dea = dif.ewm(span=signal, adjust=False, min_periods=1).mean()
    hist = 2 * (dif - dea)

    if not ascending:
        dif = dif.iloc[::-1].reset_index(drop=True)
        dea = dea.iloc[::-1].reset_index(drop=True)
        hist = hist.iloc[::-1].reset_index(drop=True)

    # 恢复原始索引
    dif.index = original_index
    dea.index = original_index
    hist.index = original_index
    return dif, dea, hist
