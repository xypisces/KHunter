"""indicators/_cache.py — CachedIndicators 缓存包装器

提供可选的缓存层，用于批量处理场景避免重复计算。
模块级单例 + LRU 上限，按股票代码分组缓存。
"""

from __future__ import annotations

from collections import OrderedDict

import pandas as pd

from indicators import oscillator, volatility
from indicators.ma import ema as _ema, ma as _ma, sma as _sma


class CachedIndicators:
    """带缓存的技术指标计算器。

    内部调用 indicators 的纯函数，结果按 (stock_code, indicator_key) 缓存。
    超过 max_stocks 上限时淘汰最旧的股票缓存。

    Args:
        max_stocks: 最大缓存股票数量，默认 1000
    """

    def __init__(self, max_stocks: int = 1000):
        self._cache: OrderedDict[str, dict[str, pd.Series]] = OrderedDict()
        self._max_stocks = max_stocks

    def _get(self, stock_code: str, key: str) -> pd.Series | None:
        """获取缓存值，不存在返回 None。"""
        if stock_code in self._cache and key in self._cache[stock_code]:
            # 移到末尾（最近使用）
            self._cache.move_to_end(stock_code)
            return self._cache[stock_code][key]
        return None

    def _set(self, stock_code: str, key: str, value: pd.Series) -> None:
        """设置缓存值，必要时淘汰最旧的股票。"""
        if stock_code not in self._cache:
            # 淘汰最旧的股票
            while len(self._cache) >= self._max_stocks:
                self._cache.popitem(last=False)
            self._cache[stock_code] = {}
        self._cache[stock_code][key] = value
        self._cache.move_to_end(stock_code)

    def clear(self, stock_code: str | None = None) -> None:
        """清除缓存。

        Args:
            stock_code: 指定股票代码清除，None 则清除全部
        """
        if stock_code:
            self._cache.pop(stock_code, None)
        else:
            self._cache.clear()

    def ma(self, series: pd.Series, n: int, stock_code: str) -> pd.Series:
        """带缓存的简单移动平均线。"""
        key = f"ma_{n}"
        cached = self._get(stock_code, key)
        if cached is not None:
            return cached
        result = _ma(series, n)
        self._set(stock_code, key, result)
        return result

    def ema(self, series: pd.Series, n: int, stock_code: str) -> pd.Series:
        """带缓存的指数移动平均线。"""
        key = f"ema_{n}"
        cached = self._get(stock_code, key)
        if cached is not None:
            return cached
        result = _ema(series, n)
        self._set(stock_code, key, result)
        return result

    def sma(self, series: pd.Series, n: int, m: int, stock_code: str) -> pd.Series:
        """带缓存的通达信加权移动平均。"""
        key = f"sma_{n}_{m}"
        cached = self._get(stock_code, key)
        if cached is not None:
            return cached
        result = _sma(series, n, m)
        self._set(stock_code, key, result)
        return result

    def rsi(self, df: pd.DataFrame, period: int, stock_code: str) -> pd.Series:
        """带缓存的 RSI。"""
        key = f"rsi_{period}"
        cached = self._get(stock_code, key)
        if cached is not None:
            return cached
        result = oscillator.rsi(df, period)
        self._set(stock_code, key, result)
        return result

    def kdj(
        self, df: pd.DataFrame, n: int, m1: int, m2: int, stock_code: str
    ) -> tuple[pd.Series, pd.Series, pd.Series]:
        """带缓存的 KDJ。"""
        key = f"kdj_{n}_{m1}_{m2}"
        cached_k = self._get(stock_code, key + "_k")
        cached_d = self._get(stock_code, key + "_d")
        cached_j = self._get(stock_code, key + "_j")
        if cached_k is not None and cached_d is not None and cached_j is not None:
            return cached_k, cached_d, cached_j
        k, d, j = oscillator.kdj(df, n, m1, m2)
        self._set(stock_code, key + "_k", k)
        self._set(stock_code, key + "_d", d)
        self._set(stock_code, key + "_j", j)
        return k, d, j

    def macd(
        self, df: pd.DataFrame, fast: int, slow: int, signal: int, stock_code: str
    ) -> tuple[pd.Series, pd.Series, pd.Series]:
        """带缓存的 MACD。"""
        key = f"macd_{fast}_{slow}_{signal}"
        cached_dif = self._get(stock_code, key + "_dif")
        cached_dea = self._get(stock_code, key + "_dea")
        cached_hist = self._get(stock_code, key + "_hist")
        if cached_dif is not None and cached_dea is not None and cached_hist is not None:
            return cached_dif, cached_dea, cached_hist
        dif, dea, hist = oscillator.macd(df, fast, slow, signal)
        self._set(stock_code, key + "_dif", dif)
        self._set(stock_code, key + "_dea", dea)
        self._set(stock_code, key + "_hist", hist)
        return dif, dea, hist

    def atr(self, df: pd.DataFrame, period: int, stock_code: str) -> pd.Series:
        """带缓存的 ATR。"""
        key = f"atr_{period}"
        cached = self._get(stock_code, key)
        if cached is not None:
            return cached
        result = volatility.atr(df, period)
        self._set(stock_code, key, result)
        return result

    def bollinger(
        self, df: pd.DataFrame, period: int, multiplier: float, stock_code: str
    ) -> tuple[pd.Series, pd.Series, pd.Series]:
        """带缓存的布林带。"""
        key = f"bollinger_{period}_{multiplier}"
        cached_mid = self._get(stock_code, key + "_mid")
        cached_upper = self._get(stock_code, key + "_upper")
        cached_lower = self._get(stock_code, key + "_lower")
        if cached_mid is not None and cached_upper is not None and cached_lower is not None:
            return cached_mid, cached_upper, cached_lower
        mid, upper, lower = volatility.bollinger(df, period, multiplier)
        self._set(stock_code, key + "_mid", mid)
        self._set(stock_code, key + "_upper", upper)
        self._set(stock_code, key + "_lower", lower)
        return mid, upper, lower
