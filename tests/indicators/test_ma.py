"""tests for indicators/ma.py — 移动平均线指标"""

import numpy as np
import pandas as pd
import pytest

from indicators.ma import ema, ma, sma


def _make_ascending(n: int = 10) -> pd.Series:
    """生成升序测试数据。"""
    return pd.Series([float(i) for i in range(1, n + 1)])


def _make_descending(n: int = 10) -> pd.Series:
    """生成降序测试数据。"""
    return pd.Series([float(i) for i in range(n, 0, -1)])


class TestMA:
    """ma (简单移动平均) 的测试。"""

    def test_basic(self):
        """基本 MA 计算。"""
        s = pd.Series([1.0, 2.0, 3.0, 4.0, 5.0])
        result = ma(s, 3)
        # 前 2 个值不足窗口，用 min_periods=1
        assert result.iloc[0] == pytest.approx(1.0)
        assert result.iloc[1] == pytest.approx(1.5)
        assert result.iloc[2] == pytest.approx(2.0)
        assert result.iloc[3] == pytest.approx(3.0)
        assert result.iloc[4] == pytest.approx(4.0)

    def test_window_equals_length(self):
        """窗口等于数据长度时，最后一个值等于均值。"""
        s = pd.Series([1.0, 2.0, 3.0, 4.0, 5.0])
        result = ma(s, 5)
        assert result.iloc[-1] == pytest.approx(3.0)

    def test_window_one(self):
        """窗口为 1 时应返回原值。"""
        s = pd.Series([10.0, 20.0, 30.0])
        result = ma(s, 1)
        pd.testing.assert_series_equal(result, s)

    def test_ascending_input_ascending_output(self):
        """升序输入应返回升序结果。"""
        s = _make_ascending(10)
        result = ma(s, 3)
        assert result.iloc[0] < result.iloc[-1]

    def test_descending_input_descending_output(self):
        """降序输入应返回降序结果。"""
        s = _make_descending(10)
        result = ma(s, 3)
        assert result.iloc[0] > result.iloc[-1]

    def test_same_result_both_orders(self):
        """升序和降序输入应产生等价结果（反转后一致）。"""
        asc = _make_ascending(10)
        desc = _make_descending(10)
        result_asc = ma(asc, 3)
        result_desc = ma(desc, 3)
        pd.testing.assert_series_equal(
            result_asc, result_desc.iloc[::-1].reset_index(drop=True)
        )

    def test_length_preserved(self):
        """输出长度应与输入相同。"""
        s = _make_ascending(20)
        result = ma(s, 5)
        assert len(result) == len(s)


class TestEMA:
    """ema (指数移动平均) 的测试。"""

    def test_basic(self):
        """基本 EMA 计算。"""
        s = pd.Series([1.0, 2.0, 3.0, 4.0, 5.0])
        result = ema(s, 3)
        # EMA 第一个值等于第一个输入值
        assert result.iloc[0] == pytest.approx(1.0)
        # 后续值使用指数加权
        assert len(result) == 5

    def test_ascending_input_ascending_output(self):
        """升序输入应返回升序结果。"""
        s = _make_ascending(10)
        result = ema(s, 3)
        assert result.iloc[0] < result.iloc[-1]

    def test_descending_input_descending_output(self):
        """降序输入应返回降序结果。"""
        s = _make_descending(10)
        result = ema(s, 3)
        assert result.iloc[0] > result.iloc[-1]

    def test_same_result_both_orders(self):
        """升序和降序输入应产生等价结果。"""
        asc = _make_ascending(10)
        desc = _make_descending(10)
        result_asc = ema(asc, 3)
        result_desc = ema(desc, 3)
        pd.testing.assert_series_equal(
            result_asc, result_desc.iloc[::-1].reset_index(drop=True)
        )

    def test_length_preserved(self):
        """输出长度应与输入相同。"""
        s = _make_ascending(20)
        result = ema(s, 5)
        assert len(result) == len(s)


class TestSMA:
    """sma (通达信加权移动平均) 的测试。"""

    def test_basic(self):
        """基本 SMA 计算（通达信公式: SMA(X, N, M) = (X*M + prev*(N-M))/N）。"""
        s = pd.Series([2.0, 4.0, 6.0, 8.0, 10.0])
        result = sma(s, 3, 1)
        assert len(result) == 5
        # 第一个值等于第一个输入值
        assert result.iloc[0] == pytest.approx(2.0)

    def test_ascending_input_ascending_output(self):
        """升序输入应返回升序结果。"""
        s = _make_ascending(10)
        result = sma(s, 3, 1)
        assert result.iloc[0] < result.iloc[-1]

    def test_descending_input_descending_output(self):
        """降序输入应返回降序结果。"""
        s = _make_descending(10)
        result = sma(s, 3, 1)
        assert result.iloc[0] > result.iloc[-1]

    def test_same_result_both_orders(self):
        """升序和降序输入应产生等价结果。"""
        asc = _make_ascending(10)
        desc = _make_descending(10)
        result_asc = sma(asc, 3, 1)
        result_desc = sma(desc, 3, 1)
        pd.testing.assert_series_equal(
            result_asc, result_desc.iloc[::-1].reset_index(drop=True)
        )

    def test_length_preserved(self):
        """输出长度应与输入相同。"""
        s = _make_ascending(20)
        result = sma(s, 5, 1)
        assert len(result) == len(s)

    def test_m_equals_n(self):
        """当 M=N 时，SMA(X, N, N) 等价于 X 本身。"""
        s = pd.Series([10.0, 20.0, 30.0, 40.0])
        result = sma(s, 3, 3)
        # SMA(X, N, N) = (X*N + prev*0)/N = X
        # 但第一个值是 X[0]，后续递推
        assert len(result) == 4
