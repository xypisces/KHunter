"""indicators/_order.py — 排序检测与转换

提供数据排序方向的自动检测和转换功能。
所有指标函数内部使用此模块，确保计算在升序数据上进行。
"""

from __future__ import annotations

import pandas as pd


def is_ascending(series: pd.Series) -> bool:
    """判断 Series 是否为升序排列。

    单元素或所有值相同时视为升序。

    Args:
        series: 待检测的 Series

    Returns:
        True 表示升序，False 表示降序
    """
    if len(series) <= 1:
        return True
    return bool(series.iloc[0] <= series.iloc[-1])


def ensure_ascending(df: pd.DataFrame) -> tuple[pd.DataFrame, bool]:
    """确保 DataFrame 按日期升序排列。

    如果存在 'date' 列，通过比较首尾日期判断排序方向。
    如果不存在 'date' 列，假设已是升序（调用方自行保证）。

    Args:
        df: 待检查的 DataFrame，必须非空

    Returns:
        (df_ascending, was_reversed) 元组。
        df_ascending 为升序版本，was_reversed 表示是否执行了反转。

    Raises:
        ValueError: 空 DataFrame
    """
    if len(df) == 0:
        raise ValueError("ensure_ascending: 传入的 DataFrame 为空")

    if "date" not in df.columns:
        return df, False

    if is_ascending(df["date"]):
        return df, False

    return df.iloc[::-1].reset_index(drop=True), True
