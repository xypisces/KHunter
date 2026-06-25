"""tests for indicators/volatility.py — 波动率指标 (ATR, Bollinger)"""

import numpy as np
import pandas as pd
import pytest

from indicators.volatility import atr, bollinger


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


class TestATR:
    """atr (平均真实波幅) 的测试。"""

    def test_positive_values(self):
        """ATR 值应始终为正。"""
        df = _make_ohlc(30)
        result = atr(df, 14)
        assert (result > 0).all()

    def test_length_preserved(self):
        """输出长度应与输入相同。"""
        df = _make_ohlc(30)
        result = atr(df, 14)
        assert len(result) == len(df)

    def test_standard_formula(self):
        """ATR 应使用标准公式：TR = max(H-L, |H-C_prev|, |L-C_prev|)，EWM 平滑。"""
        df = pd.DataFrame({
            "date": pd.date_range("2024-01-01", periods=5),
            "open": [100.0, 102.0, 101.0, 103.0, 104.0],
            "high": [103.0, 104.0, 103.0, 105.0, 106.0],
            "low":  [99.0, 101.0, 100.0, 102.0, 103.0],
            "close": [102.0, 101.0, 103.0, 104.0, 105.0],
        })
        result = atr(df, 3)
        # TR[0] = 103-99 = 4
        # TR[1] = max(104-101, |104-102|, |101-102|) = max(3, 2, 1) = 3
        # TR[2] = max(103-100, |103-101|, |100-101|) = max(3, 2, 1) = 3
        # EWM(span=3): alpha=0.5, ATR[0]=4, ATR[1]=0.5*3+0.5*4=3.5, ATR[2]=0.5*3+0.5*3.5=3.25
        assert result.iloc[0] == pytest.approx(4.0)
        assert result.iloc[1] == pytest.approx(3.5)
        assert result.iloc[2] == pytest.approx(3.25)

    def test_ascending_input(self):
        """升序输入应返回升序结果。"""
        df = _make_ohlc(30, ascending=True)
        result = atr(df, 14)
        assert len(result) == 30

    def test_descending_input(self):
        """降序输入应返回降序结果。"""
        df = _make_ohlc(30, ascending=False)
        result = atr(df, 14)
        assert len(result) == 30

    def test_same_result_both_orders(self):
        """升序和降序输入应产生等价结果。"""
        df_asc = _make_ohlc(30, ascending=True)
        df_desc = _make_ohlc(30, ascending=False)
        result_asc = atr(df_asc, 14)
        result_desc = atr(df_desc, 14)
        pd.testing.assert_series_equal(
            result_asc, result_desc.iloc[::-1].reset_index(drop=True)
        )


class TestBollinger:
    """bollinger (布林带) 的测试。"""

    def test_basic(self):
        """基本布林带计算。"""
        df = _make_ohlc(30)
        mid, upper, lower = bollinger(df, 20, 2.0)
        assert len(mid) == 30
        assert len(upper) == 30
        assert len(lower) == 30

    def test_mid_is_ma(self):
        """中轨应等于 MA。"""
        df = _make_ohlc(30)
        mid, _, _ = bollinger(df, 20, 2.0)
        expected_mid = df["close"].rolling(window=20, min_periods=1).mean()
        pd.testing.assert_series_equal(mid, expected_mid)

    def test_upper_above_lower(self):
        """上轨应始终高于下轨。"""
        df = _make_ohlc(30)
        _, upper, lower = bollinger(df, 20, 2.0)
        assert (upper >= lower).all()

    def test_upper_above_mid(self):
        """上轨应高于或等于中轨。"""
        df = _make_ohlc(30)
        mid, upper, _ = bollinger(df, 20, 2.0)
        assert (upper >= mid).all()

    def test_lower_below_mid(self):
        """下轨应低于或等于中轨。"""
        df = _make_ohlc(30)
        mid, _, lower = bollinger(df, 20, 2.0)
        assert (lower <= mid).all()

    def test_ascending_input(self):
        """升序输入应返回升序结果。"""
        df = _make_ohlc(30, ascending=True)
        mid, upper, lower = bollinger(df, 20, 2.0)
        assert len(mid) == 30

    def test_descending_input(self):
        """降序输入应返回降序结果。"""
        df = _make_ohlc(30, ascending=False)
        mid, upper, lower = bollinger(df, 20, 2.0)
        assert len(mid) == 30

    def test_same_result_both_orders(self):
        """升序和降序输入应产生等价结果。"""
        df_asc = _make_ohlc(30, ascending=True)
        df_desc = _make_ohlc(30, ascending=False)
        mid_asc, _, _ = bollinger(df_asc, 20, 2.0)
        mid_desc, _, _ = bollinger(df_desc, 20, 2.0)
        pd.testing.assert_series_equal(
            mid_asc, mid_desc.iloc[::-1].reset_index(drop=True)
        )
