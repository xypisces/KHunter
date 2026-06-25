"""tests for indicators/_order.py — 排序检测与转换"""

import pandas as pd
import pytest

from indicators._order import ensure_ascending, is_ascending


class TestIsAscending:
    """is_ascending 的测试。"""

    def test_ascending_series(self):
        """升序 Series 应返回 True。"""
        s = pd.Series([1, 2, 3, 4, 5])
        assert is_ascending(s) is True

    def test_descending_series(self):
        """降序 Series 应返回 False。"""
        s = pd.Series([5, 4, 3, 2, 1])
        assert is_ascending(s) is False

    def test_single_element(self):
        """单元素 Series 应返回 True（视为升序）。"""
        s = pd.Series([42])
        assert is_ascending(s) is True

    def test_equal_values(self):
        """所有值相同时应返回 True。"""
        s = pd.Series([3, 3, 3, 3])
        assert is_ascending(s) is True

    def test_ascending_dates(self):
        """升序日期 Series 应返回 True。"""
        dates = pd.Series(pd.date_range("2024-01-01", periods=5))
        assert is_ascending(dates) is True

    def test_descending_dates(self):
        """降序日期 Series 应返回 False。"""
        dates = pd.Series(pd.date_range("2024-01-01", periods=5)[::-1])
        assert is_ascending(dates) is False


class TestEnsureAscending:
    """ensure_ascending 的测试。"""

    def test_already_ascending(self):
        """升序 DataFrame 应原样返回，was_reversed=False。"""
        df = pd.DataFrame({
            "date": pd.date_range("2024-01-01", periods=5),
            "close": [10.0, 11.0, 12.0, 13.0, 14.0],
        })
        result, was_reversed = ensure_ascending(df)
        assert was_reversed is False
        pd.testing.assert_frame_equal(result, df)

    def test_descending_to_ascending(self):
        """降序 DataFrame 应反转，was_reversed=True。"""
        df = pd.DataFrame({
            "date": pd.date_range("2024-01-01", periods=5)[::-1],
            "close": [14.0, 13.0, 12.0, 11.0, 10.0],
        })
        result, was_reversed = ensure_ascending(df)
        assert was_reversed is True
        assert result["date"].iloc[0] < result["date"].iloc[-1]
        assert result["close"].iloc[0] == 10.0
        assert result["close"].iloc[-1] == 14.0

    def test_single_row(self):
        """单行 DataFrame 应原样返回，was_reversed=False。"""
        df = pd.DataFrame({
            "date": [pd.Timestamp("2024-01-01")],
            "close": [10.0],
        })
        result, was_reversed = ensure_ascending(df)
        assert was_reversed is False
        assert len(result) == 1

    def test_empty_raises(self):
        """空 DataFrame 应抛出 ValueError。"""
        df = pd.DataFrame({"date": pd.Series(dtype="datetime64[ns]"), "close": pd.Series(dtype="float")})
        with pytest.raises(ValueError, match="空"):
            ensure_ascending(df)

    def test_no_date_column_ascending(self):
        """没有 date 列的升序 DataFrame 应原样返回。"""
        df = pd.DataFrame({"close": [10.0, 11.0, 12.0]})
        result, was_reversed = ensure_ascending(df)
        assert was_reversed is False

    def test_no_date_column_descending(self):
        """没有 date 列的降序 DataFrame 应原样返回（无法检测）。"""
        df = pd.DataFrame({"close": [12.0, 11.0, 10.0]})
        result, was_reversed = ensure_ascending(df)
        assert was_reversed is False

    def test_index_preserved(self):
        """反转后索引应重置为 0-based。"""
        df = pd.DataFrame({
            "date": pd.date_range("2024-01-01", periods=3)[::-1],
            "close": [30.0, 20.0, 10.0],
        })
        result, _ = ensure_ascending(df)
        assert list(result.index) == [0, 1, 2]
