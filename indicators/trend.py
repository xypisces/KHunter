"""indicators/trend.py — 趋势指标

提供知行趋势线（ZhiXing Trend）指标。
自动检测输入排序方向，内部统一在升序数据上计算，输出保持与输入相同的排序。
"""

from __future__ import annotations

import pandas as pd

from indicators.ma import ema, ma


def calculate_zhixing_trend(
    df: pd.DataFrame,
    m1: int = 14,
    m2: int = 28,
    m3: int = 57,
    m4: int = 114,
) -> pd.DataFrame:
    """计算知行趋势线指标。

    - 知行短期趋势线 = EMA(EMA(CLOSE, 10), 10)
    - 知行多空线 = (MA(CLOSE, m1) + MA(CLOSE, m2) + MA(CLOSE, m3) + MA(CLOSE, m4)) / 4

    Args:
        df: 股票数据 DataFrame，必须包含 'close' 列
        m1: 多空线 MA 周期 1，默认 14
        m2: 多空线 MA 周期 2，默认 28
        m3: 多空线 MA 周期 3，默认 57
        m4: 多空线 MA 周期 4，默认 114

    Returns:
        DataFrame，包含 'short_term_trend' 和 'bull_bear_line' 两列
    """
    close: pd.Series = df['close']  # type: ignore[assignment]

    # 知行短期趋势线 = EMA(EMA(CLOSE, 10), 10)
    short_term_trend = ema(ema(close, 10), 10)

    # 知行多空线 = (MA(m1) + MA(m2) + MA(m3) + MA(m4)) / 4
    bull_bear_line = (
        ma(close, m1) + ma(close, m2) + ma(close, m3) + ma(close, m4)
    ) / 4

    return pd.DataFrame({
        'short_term_trend': short_term_trend,
        'bull_bear_line': bull_bear_line,
    }, index=df.index)
