"""tests for indicators/oscillator.py — 振荡指标 (RSI, KDJ, MACD)"""

import numpy as np
import pandas as pd
import pytest

from indicators.oscillator import kdj, macd, rsi


def _make_ohlc(n: int = 30, ascending: bool = True) -> pd.DataFrame:
    """生成 OHLC 测试数据。"""
    dates = pd.date_range("2024-01-01", periods=n)
    np.random.seed(42)
    close = 100.0 + np.cumsum(np.random.randn(n) * 2)
    high = close + np.abs(np.random.randn(n))
    low = close - np.abs(np.random.randn(n))
    df = pd.DataFrame({"date": dates, "open": close, "high": high, "low": low, "close": close})
    if not ascending:
        df = df.iloc[::-1].reset_index(drop=True)
    return df


class TestRSI:
    """rsi (相对强弱指标) 的测试。"""

    def test_range_0_100(self):
        """RSI 值应在 0-100 之间。"""
        df = _make_ohlc(50)
        result = rsi(df, 14)
        assert result.min() >= 0
        assert result.max() <= 100

    def test_length_preserved(self):
        """输出长度应与输入相同。"""
        df = _make_ohlc(30)
        result = rsi(df, 14)
        assert len(result) == len(df)

    def test_ascending_input(self):
        """升序输入应返回升序结果（索引 0 为最早）。"""
        df = _make_ohlc(30, ascending=True)
        result = rsi(df, 14)
        # 第一个值应为 50（无变化时的默认值）
        assert result.iloc[0] == pytest.approx(50.0)

    def test_descending_input(self):
        """降序输入应返回降序结果。"""
        df = _make_ohlc(30, ascending=False)
        result = rsi(df, 14)
        # 降序时第一个值对应最新日期
        assert len(result) == len(df)

    def test_same_result_both_orders(self):
        """升序和降序输入应产生等价结果。"""
        df_asc = _make_ohlc(30, ascending=True)
        df_desc = _make_ohlc(30, ascending=False)
        result_asc = rsi(df_asc, 14)
        result_desc = rsi(df_desc, 14)
        pd.testing.assert_series_equal(
            result_asc, result_desc.iloc[::-1].reset_index(drop=True)
        )

    def test_strong_uptrend(self):
        """强上涨趋势中 RSI 应偏高。"""
        df = pd.DataFrame({
            "date": pd.date_range("2024-01-01", periods=20),
            "open": range(100, 120),
            "high": range(101, 121),
            "low": range(99, 119),
            "close": range(100, 120),
        })
        result = rsi(df, 14)
        assert result.iloc[-1] > 70  # 强上涨应高于 70

    def test_strong_downtrend(self):
        """强下跌趋势中 RSI 应偏低。"""
        df = pd.DataFrame({
            "date": pd.date_range("2024-01-01", periods=20),
            "open": range(120, 100, -1),
            "high": range(121, 101, -1),
            "low": range(119, 99, -1),
            "close": range(120, 100, -1),
        })
        result = rsi(df, 14)
        assert result.iloc[-1] < 30  # 强下跌应低于 30


class TestKDJ:
    """kdj (随机指标) 的测试。"""

    def test_basic(self):
        """基本 KDJ 计算。"""
        df = _make_ohlc(30)
        k, d, j = kdj(df, 9, 3, 3)
        assert len(k) == 30
        assert len(d) == 30
        assert len(j) == 30

    def test_k_d_range(self):
        """K 和 D 值通常在 0-100 之间。"""
        df = _make_ohlc(50)
        k, d, j = kdj(df, 9, 3, 3)
        # 允许少量越界（边界情况）
        assert k.min() >= -5
        assert k.max() <= 105
        assert d.min() >= -5
        assert d.max() <= 105

    def test_j_formula(self):
        """J = 3*K - 2*D。"""
        df = _make_ohlc(30)
        k, d, j = kdj(df, 9, 3, 3)
        expected_j = 3 * k - 2 * d
        pd.testing.assert_series_equal(j, expected_j)

    def test_ascending_input(self):
        """升序输入应返回升序结果。"""
        df = _make_ohlc(30, ascending=True)
        k, d, j = kdj(df, 9, 3, 3)
        assert len(k) == 30

    def test_descending_input(self):
        """降序输入应返回降序结果。"""
        df = _make_ohlc(30, ascending=False)
        k, d, j = kdj(df, 9, 3, 3)
        assert len(k) == 30

    def test_same_result_both_orders(self):
        """升序和降序输入应产生等价结果。"""
        df_asc = _make_ohlc(30, ascending=True)
        df_desc = _make_ohlc(30, ascending=False)
        k_asc, d_asc, j_asc = kdj(df_asc, 9, 3, 3)
        k_desc, d_desc, j_desc = kdj(df_desc, 9, 3, 3)
        pd.testing.assert_series_equal(
            k_asc, k_desc.iloc[::-1].reset_index(drop=True)
        )
        pd.testing.assert_series_equal(
            d_asc, d_desc.iloc[::-1].reset_index(drop=True)
        )


class TestMACD:
    """macd (指数平滑异同移动平均) 的测试。"""

    def test_basic(self):
        """基本 MACD 计算。"""
        df = _make_ohlc(50)
        dif, dea, hist = macd(df, 12, 26, 9)
        assert len(dif) == 50
        assert len(dea) == 50
        assert len(hist) == 50

    def test_hist_formula(self):
        """MACD 柱状图 = 2 * (DIF - DEA)。"""
        df = _make_ohlc(50)
        dif, dea, hist = macd(df, 12, 26, 9)
        expected_hist = 2 * (dif - dea)
        pd.testing.assert_series_equal(hist, expected_hist)

    def test_ascending_input(self):
        """升序输入应返回升序结果。"""
        df = _make_ohlc(50, ascending=True)
        dif, dea, hist = macd(df, 12, 26, 9)
        assert len(dif) == 50

    def test_descending_input(self):
        """降序输入应返回降序结果。"""
        df = _make_ohlc(50, ascending=False)
        dif, dea, hist = macd(df, 12, 26, 9)
        assert len(dif) == 50

    def test_same_result_both_orders(self):
        """升序和降序输入应产生等价结果。"""
        df_asc = _make_ohlc(50, ascending=True)
        df_desc = _make_ohlc(50, ascending=False)
        dif_asc, dea_asc, hist_asc = macd(df_asc, 12, 26, 9)
        dif_desc, dea_desc, hist_desc = macd(df_desc, 12, 26, 9)
        pd.testing.assert_series_equal(
            dif_asc, dif_desc.iloc[::-1].reset_index(drop=True)
        )
        pd.testing.assert_series_equal(
            dea_asc, dea_desc.iloc[::-1].reset_index(drop=True)
        )
