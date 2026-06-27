"""indicators/returns.py — 收益率指标

提供价格变化率和日收益率计算。
自动检测输入排序方向，内部统一在升序数据上计算，输出保持与输入相同的排序。
"""

from __future__ import annotations

import pandas as pd

from indicators._order import is_ascending


def calculate_price_change(df: pd.DataFrame, method: str = 'prev_close') -> pd.Series:
    """计算价格变化率。

    Args:
        df: 股票数据 DataFrame，必须包含 'close' 列；
            method='prev_close' 时还需要 'date' 列用于排序检测；
            method='open' 时还需要 'open' 列
        method: 计算方法
            - 'prev_close': 相对于前一天收盘价的涨幅（标准定义）
            - 'open': 相对于当天开盘价的涨幅（日内涨幅）

    Returns:
        价格变化率 Series

    Raises:
        ValueError: 不支持的 method
    """
    if df is None or df.empty:
        return pd.Series(dtype=float)

    ascending = is_ascending(df['close'])  # type: ignore[arg-type]

    if method == 'prev_close':
        if ascending:
            prev_close = df['close'].shift(1)
        else:
            prev_close = df['close'].shift(-1)
        return (df['close'] - prev_close) / prev_close

    elif method == 'open':
        return (df['close'] - df['open']) / df['open']

    else:
        raise ValueError(f"不支持的计算方法: {method}")


def calculate_daily_return(df: pd.DataFrame) -> pd.Series:
    """计算日收益率（相对于前一天收盘价的涨幅）。

    等价于 ``calculate_price_change(df, method='prev_close')``。

    Args:
        df: 股票数据 DataFrame，必须包含 'close' 和 'date' 列

    Returns:
        日收益率 Series
    """
    return calculate_price_change(df, method='prev_close')
