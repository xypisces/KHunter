"""
数据获取器统一接口

定义 DataFetcher 抽象基类，所有数据获取器都应实现此接口。
"""
from abc import ABC, abstractmethod
from typing import Dict, List, Optional, Any
import pandas as pd
import logging

logger = logging.getLogger(__name__)


class DataFetcher(ABC):
    """
    数据获取器统一接口

    所有数据获取器都应继承此类并实现抽象方法。
    使用依赖注入，测试时可使用 MockDataFetcher 替换。
    """

    @abstractmethod
    def fetch_stock_basic(self, **kwargs) -> Optional[pd.DataFrame]:
        """
        获取股票基础数据

        :return: DataFrame，包含 code, name, industry, area 等字段
        """
        pass

    @abstractmethod
    def fetch_stock_history(
        self, code: str, days: int = 100, **kwargs
    ) -> Optional[pd.DataFrame]:
        """
        获取股票历史数据

        :param code: 股票代码
        :param days: 获取天数
        :return: DataFrame，包含 date, open, high, low, close, volume 等字段
        """
        pass

    @abstractmethod
    def fetch_fund_flow(self, code: str, **kwargs) -> Optional[pd.DataFrame]:
        """
        获取资金流向

        :param code: 股票代码
        :return: DataFrame，包含资金流向数据
        """
        pass

    @abstractmethod
    def fetch_industry_data(self, **kwargs) -> Optional[pd.DataFrame]:
        """
        获取行业数据

        :return: DataFrame，包含行业分类数据
        """
        pass

    @abstractmethod
    def fetch_sector_data(self, **kwargs) -> Optional[pd.DataFrame]:
        """
        获取板块数据

        :return: DataFrame，包含板块分类数据
        """
        pass

    def fetch_index_data(
        self, code: str = "000001", days: int = 100, **kwargs
    ) -> Optional[pd.DataFrame]:
        """
        获取指数数据（可选实现）

        :param code: 指数代码
        :param days: 获取天数
        :return: DataFrame，包含指数数据
        """
        logger.warning("fetch_index_data 未实现")
        return None

    def fetch_event_data(self, code: str, **kwargs) -> Optional[pd.DataFrame]:
        """
        获取事件数据（可选实现）

        :param code: 股票代码
        :return: DataFrame，包含事件数据
        """
        logger.warning("fetch_event_data 未实现")
        return None


class MockDataFetcher(DataFetcher):
    """
    内存适配器，用于测试

    所有方法返回空 DataFrame 或预设数据。
    """

    def __init__(self, data: Optional[Dict[str, pd.DataFrame]] = None):
        """
        初始化 MockDataFetcher

        :param data: 预设数据 {method_name: DataFrame}
        """
        self.data = data or {}

    def fetch_stock_basic(self, **kwargs) -> Optional[pd.DataFrame]:
        """返回预设的股票基础数据"""
        if "stock_basic" in self.data:
            return self.data["stock_basic"]
        return pd.DataFrame(
            {
                "code": ["000001", "600000"],
                "name": ["平安银行", "浦发银行"],
                "industry": ["银行", "银行"],
                "area": ["深圳", "上海"],
            }
        )

    def fetch_stock_history(
        self, code: str, days: int = 100, **kwargs
    ) -> Optional[pd.DataFrame]:
        """返回预设的历史数据"""
        key = f"history_{code}"
        if key in self.data:
            return self.data[key]
        return pd.DataFrame(
            {
                "date": pd.date_range(end="2026-06-27", periods=days),
                "open": [10.0] * days,
                "high": [10.5] * days,
                "low": [9.5] * days,
                "close": [10.2] * days,
                "volume": [1000000] * days,
            }
        )

    def fetch_fund_flow(self, code: str, **kwargs) -> Optional[pd.DataFrame]:
        """返回预设的资金流向数据"""
        key = f"fund_flow_{code}"
        if key in self.data:
            return self.data[key]
        return pd.DataFrame(
            {
                "date": pd.date_range(end="2026-06-27", periods=5),
                "main_net_inflow": [1000000, -500000, 200000, -100000, 300000],
            }
        )

    def fetch_industry_data(self, **kwargs) -> Optional[pd.DataFrame]:
        """返回预设的行业数据"""
        if "industry" in self.data:
            return self.data["industry"]
        return pd.DataFrame(
            {
                "code": ["000001", "600000"],
                "industry": ["银行", "银行"],
            }
        )

    def fetch_sector_data(self, **kwargs) -> Optional[pd.DataFrame]:
        """返回预设的板块数据"""
        if "sector" in self.data:
            return self.data["sector"]
        return pd.DataFrame(
            {
                "code": ["000001", "600000"],
                "sector": ["金融", "金融"],
            }
        )


# 全局数据获取器实例
_data_fetcher: Optional[DataFetcher] = None


def get_data_fetcher() -> DataFetcher:
    """
    获取全局数据获取器实例

    :return: DataFetcher 实例
    """
    global _data_fetcher
    if _data_fetcher is None:
        from utils.akshare_adapter import AKShareDataAdapter

        _data_fetcher = AKShareDataAdapter()
    return _data_fetcher


def set_data_fetcher(fetcher: DataFetcher) -> None:
    """
    设置全局数据获取器（用于测试）

    :param fetcher: DataFetcher 实例
    """
    global _data_fetcher
    _data_fetcher = fetcher
