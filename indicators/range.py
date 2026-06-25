"""indicators/range.py — 区间辅助函数

提供 LLV、HHV、REF、EXIST 四个通达信风格的辅助函数。
所有函数自动检测输入排序方向，内部统一在升序数据上计算，输出保持与输入相同的排序。
"""

from __future__ import annotations

import pandas as pd

from indicators._order import is_ascending


def llv(series: pd.Series, n: int) -> pd.Series:
    """N 周期最低值。

    Args:
        series: 价格序列
        n: 窗口周期

    Returns:
        每个位置的 N 周期最低值，长度与输入相同，索引与输入相同
    """
    original_index = series.index
    ascending = is_ascending(series)
    if not ascending:
        series = series.iloc[::-1].reset_index(drop=True)
    result = series.rolling(window=n, min_periods=1).min()
    if not ascending:
        result = result.iloc[::-1].reset_index(drop=True)
    # 恢复原始索引
    result.index = original_index
    return result


def hhv(series: pd.Series, n: int) -> pd.Series:
    """N 周期最高值。

    Args:
        series: 价格序列
        n: 窗口周期

    Returns:
        每个位置的 N 周期最高值，长度与输入相同，索引与输入相同
    """
    original_index = series.index
    ascending = is_ascending(series)
    if not ascending:
        series = series.iloc[::-1].reset_index(drop=True)
    result = series.rolling(window=n, min_periods=1).max()
    if not ascending:
        result = result.iloc[::-1].reset_index(drop=True)
    # 恢复原始索引
    result.index = original_index
    return result


def ref(series: pd.Series, n: int) -> pd.Series:
    """向前引用 N 周期。

    Args:
        series: 价格序列
        n: 向前引用的周期数

    Returns:
        前 N 个周期的值，前 N 个位置为 NaN，长度与输入相同，索引与输入相同
    """
    original_index = series.index
    ascending = is_ascending(series)
    if not ascending:
        series = series.iloc[::-1].reset_index(drop=True)
    result = series.shift(n)
    if not ascending:
        result = result.iloc[::-1].reset_index(drop=True)
    # 恢复原始索引
    result.index = original_index
    return result


def exist(cond: pd.Series, n: int) -> pd.Series:
    """N 周期内是否存在 True。

    Args:
        cond: 布尔条件序列
        n: 窗口周期

    Returns:
        每个位置的 N 周期内是否有 True，长度与输入相同，索引与输入相同
    """
    original_index = cond.index
    ascending = is_ascending(cond)
    if not ascending:
        cond = cond.iloc[::-1].reset_index(drop=True)
    result = cond.rolling(window=n, min_periods=1).max().astype(bool)
    if not ascending:
        result = result.iloc[::-1].reset_index(drop=True)
    # 恢复原始索引
    result.index = original_index
    return result
