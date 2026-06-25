"""tests for indicators/range.py — 区间辅助函数 (LLV, HHV, REF, EXIST)"""

import pandas as pd
import pytest

from indicators.range import exist, hhv, llv, ref


class TestLLV:
    """llv (N 周期最低值) 的测试。"""

    def test_basic_ascending(self):
        """升序数据的 LLV 计算。"""
        s = pd.Series([1.0, 2.0, 5.0, 3.0, 4.0])
        result = llv(s, 3)
        # 向后看窗口: [1], [1,2], [1,2,5], [2,5,3], [5,3,4]
        assert result.iloc[0] == pytest.approx(1.0)
        assert result.iloc[1] == pytest.approx(1.0)
        assert result.iloc[2] == pytest.approx(1.0)
        assert result.iloc[3] == pytest.approx(2.0)
        assert result.iloc[4] == pytest.approx(3.0)

    def test_basic_descending(self):
        """降序数据的 LLV 计算。"""
        s = pd.Series([4.0, 3.0, 5.0, 2.0, 1.0])
        result = llv(s, 3)
        # 反转为升序 [1,2,5,3,4] → rolling min → [1,1,1,2,3] → 反转回 [3,2,1,1,1]
        assert result.iloc[0] == pytest.approx(3.0)
        assert result.iloc[1] == pytest.approx(2.0)
        assert result.iloc[2] == pytest.approx(1.0)
        assert result.iloc[3] == pytest.approx(1.0)
        assert result.iloc[4] == pytest.approx(1.0)

    def test_window_one(self):
        """窗口为 1 时应返回原值。"""
        s = pd.Series([10.0, 20.0, 30.0])
        result = llv(s, 1)
        pd.testing.assert_series_equal(result, s)

    def test_length_preserved(self):
        """输出长度应与输入相同。"""
        s = pd.Series([1.0, 2.0, 3.0, 4.0, 5.0])
        result = llv(s, 3)
        assert len(result) == len(s)

    def test_ascending_descending_same_result(self):
        """升序和降序输入应产生等价结果。"""
        asc = pd.Series([1.0, 2.0, 5.0, 3.0, 4.0])
        desc = pd.Series([4.0, 3.0, 5.0, 2.0, 1.0])
        result_asc = llv(asc, 3)
        result_desc = llv(desc, 3)
        pd.testing.assert_series_equal(
            result_asc, result_desc.iloc[::-1].reset_index(drop=True)
        )


class TestHHV:
    """hhv (N 周期最高值) 的测试。"""

    def test_basic_ascending(self):
        """升序数据的 HHV 计算。"""
        s = pd.Series([1.0, 2.0, 5.0, 3.0, 4.0])
        result = hhv(s, 3)
        # 向后看窗口: [1], [1,2], [1,2,5], [2,5,3], [5,3,4]
        assert result.iloc[0] == pytest.approx(1.0)
        assert result.iloc[1] == pytest.approx(2.0)
        assert result.iloc[2] == pytest.approx(5.0)
        assert result.iloc[3] == pytest.approx(5.0)
        assert result.iloc[4] == pytest.approx(5.0)

    def test_basic_descending(self):
        """降序数据的 HHV 计算。"""
        s = pd.Series([4.0, 3.0, 5.0, 2.0, 1.0])
        result = hhv(s, 3)
        # 反转为升序 [1,2,5,3,4] → rolling max → [1,2,5,5,5] → 反转回 [5,5,5,2,1]
        assert result.iloc[0] == pytest.approx(5.0)
        assert result.iloc[1] == pytest.approx(5.0)
        assert result.iloc[2] == pytest.approx(5.0)
        assert result.iloc[3] == pytest.approx(2.0)
        assert result.iloc[4] == pytest.approx(1.0)

    def test_window_one(self):
        """窗口为 1 时应返回原值。"""
        s = pd.Series([10.0, 20.0, 30.0])
        result = hhv(s, 1)
        pd.testing.assert_series_equal(result, s)

    def test_length_preserved(self):
        """输出长度应与输入相同。"""
        s = pd.Series([1.0, 2.0, 3.0, 4.0, 5.0])
        result = hhv(s, 3)
        assert len(result) == len(s)

    def test_ascending_descending_same_result(self):
        """升序和降序输入应产生等价结果。"""
        asc = pd.Series([1.0, 2.0, 5.0, 3.0, 4.0])
        desc = pd.Series([4.0, 3.0, 5.0, 2.0, 1.0])
        result_asc = hhv(asc, 3)
        result_desc = hhv(desc, 3)
        pd.testing.assert_series_equal(
            result_asc, result_desc.iloc[::-1].reset_index(drop=True)
        )


class TestREF:
    """ref (向前引用 N 周期) 的测试。"""

    def test_basic(self):
        """基本 REF 计算——引用前一个值。"""
        s = pd.Series([10.0, 20.0, 30.0, 40.0])
        result = ref(s, 1)
        assert pd.isna(result.iloc[0])
        assert result.iloc[1] == pytest.approx(10.0)
        assert result.iloc[2] == pytest.approx(20.0)
        assert result.iloc[3] == pytest.approx(30.0)

    def test_ref_2(self):
        """引用前 2 个值。"""
        s = pd.Series([10.0, 20.0, 30.0, 40.0])
        result = ref(s, 2)
        assert pd.isna(result.iloc[0])
        assert pd.isna(result.iloc[1])
        assert result.iloc[2] == pytest.approx(10.0)
        assert result.iloc[3] == pytest.approx(20.0)

    def test_length_preserved(self):
        """输出长度应与输入相同。"""
        s = pd.Series([1.0, 2.0, 3.0, 4.0, 5.0])
        result = ref(s, 1)
        assert len(result) == len(s)

    def test_ascending_descending_same_result(self):
        """升序和降序输入应产生等价结果。"""
        asc = pd.Series([10.0, 20.0, 30.0, 40.0])
        desc = pd.Series([40.0, 30.0, 20.0, 10.0])
        result_asc = ref(asc, 1)
        result_desc = ref(desc, 1)
        pd.testing.assert_series_equal(
            result_asc, result_desc.iloc[::-1].reset_index(drop=True)
        )


class TestEXIST:
    """exist (N 周期内是否存在) 的测试。"""

    def test_basic(self):
        """基本 EXIST 计算。"""
        cond = pd.Series([False, True, False, False, True])
        result = exist(cond, 3)
        # 向后看窗口: [F], [F,T], [F,T,F], [T,F,F], [F,F,T]
        assert result.iloc[0] == False
        assert result.iloc[1] == True
        assert result.iloc[2] == True
        assert result.iloc[3] == True
        assert result.iloc[4] == True

    def test_all_false(self):
        """全 False 时应返回全 False。"""
        cond = pd.Series([False, False, False, False])
        result = exist(cond, 3)
        assert not result.any()

    def test_all_true(self):
        """全 True 时应返回全 True。"""
        cond = pd.Series([True, True, True, True])
        result = exist(cond, 3)
        assert result.all()

    def test_length_preserved(self):
        """输出长度应与输入相同。"""
        cond = pd.Series([True, False, True, False, True])
        result = exist(cond, 3)
        assert len(result) == len(cond)

    def test_ascending_descending_same_result(self):
        """升序和降序输入应产生等价结果。"""
        asc = pd.Series([False, True, False, False, True])
        desc = pd.Series([True, False, False, True, False])
        result_asc = exist(asc, 3)
        result_desc = exist(desc, 3)
        pd.testing.assert_series_equal(
            result_asc, result_desc.iloc[::-1].reset_index(drop=True)
        )
