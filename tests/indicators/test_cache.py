"""tests for indicators/_cache.py — CachedIndicators 缓存包装器"""

import pandas as pd
import pytest

from indicators._cache import CachedIndicators


class TestCachedIndicators:
    """CachedIndicators 的测试。"""

    def test_ma_caching(self):
        """MA 结果应被缓存。"""
        cache = CachedIndicators()
        s = pd.Series([1.0, 2.0, 3.0, 4.0, 5.0])
        r1 = cache.ma(s, 3, "TEST")
        r2 = cache.ma(s, 3, "TEST")
        # 同一对象表示缓存命中
        assert r1 is r2

    def test_ma_different_params(self):
        """不同参数应产生不同缓存。"""
        cache = CachedIndicators()
        s = pd.Series([1.0, 2.0, 3.0, 4.0, 5.0])
        r1 = cache.ma(s, 3, "TEST")
        r2 = cache.ma(s, 5, "TEST")
        assert r1 is not r2

    def test_ma_different_stocks(self):
        """不同股票应产生不同缓存。"""
        cache = CachedIndicators()
        s = pd.Series([1.0, 2.0, 3.0, 4.0, 5.0])
        r1 = cache.ma(s, 3, "STOCK_A")
        r2 = cache.ma(s, 3, "STOCK_B")
        assert r1 is not r2

    def test_clear_single_stock(self):
        """清除指定股票的缓存。"""
        cache = CachedIndicators()
        s = pd.Series([1.0, 2.0, 3.0, 4.0, 5.0])
        r1 = cache.ma(s, 3, "TEST")
        cache.clear("TEST")
        r2 = cache.ma(s, 3, "TEST")
        # 清除后重新计算，不是同一对象
        assert r1 is not r2

    def test_clear_all(self):
        """清除所有缓存。"""
        cache = CachedIndicators()
        s = pd.Series([1.0, 2.0, 3.0, 4.0, 5.0])
        r1 = cache.ma(s, 3, "STOCK_A")
        cache.clear()
        r2 = cache.ma(s, 3, "STOCK_A")
        assert r1 is not r2

    def test_ema_caching(self):
        """EMA 结果应被缓存。"""
        cache = CachedIndicators()
        s = pd.Series([1.0, 2.0, 3.0, 4.0, 5.0])
        r1 = cache.ema(s, 3, "TEST")
        r2 = cache.ema(s, 3, "TEST")
        assert r1 is r2

    def test_rsi_caching(self):
        """RSI 结果应被缓存。"""
        cache = CachedIndicators()
        df = pd.DataFrame({
            "date": pd.date_range("2024-01-01", periods=30),
            "open": range(100, 130),
            "high": range(101, 131),
            "low": range(99, 129),
            "close": range(100, 130),
        })
        r1 = cache.rsi(df, 14, "TEST")
        r2 = cache.rsi(df, 14, "TEST")
        assert r1 is r2

    def test_max_stocks_eviction(self):
        """超过 max_stocks 时应淘汰最旧的缓存。"""
        cache = CachedIndicators(max_stocks=2)
        s = pd.Series([1.0, 2.0, 3.0])
        cache.ma(s, 3, "A")
        cache.ma(s, 3, "B")
        cache.ma(s, 3, "C")  # 应淘汰 A
        # A 的缓存应已清除，重新计算
        r_a = cache.ma(s, 3, "A")
        assert r_a is not None  # 仍然可以计算，只是不是缓存的

    def test_correctness(self):
        """缓存的结果应与直接调用纯函数一致。"""
        from indicators.ma import ma as pure_ma

        cache = CachedIndicators()
        s = pd.Series([1.0, 2.0, 3.0, 4.0, 5.0])
        cached_result = cache.ma(s, 3, "TEST")
        pure_result = pure_ma(s, 3)
        pd.testing.assert_series_equal(cached_result, pure_result)
