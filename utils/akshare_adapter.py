"""
AKShare 适配器 - 将 AKShareFetcher 适配为统一 DataFetcher 接口
"""
import logging
import pandas as pd
from typing import Optional

from utils.data_fetcher import DataFetcher
from utils.akshare_fetcher import AKShareFetcher

logger = logging.getLogger(__name__)


class AKShareDataAdapter(DataFetcher):
    """
    AKShare 适配器

    将 AKShareFetcher 的接口适配为统一的 DataFetcher 接口。
    """

    def __init__(self, fetcher: Optional[AKShareFetcher] = None):
        """
        初始化适配器

        :param fetcher: AKShareFetcher 实例，None 则自动创建
        """
        self.fetcher = fetcher or AKShareFetcher()

    def fetch_stock_basic(self, **kwargs) -> Optional[pd.DataFrame]:
        """获取股票基础数据"""
        try:
            stock_dict = self.fetcher.get_all_stock_codes()
            if not stock_dict:
                return None

            rows = []
            for code, name in stock_dict.items():
                rows.append({"code": code, "name": name})

            return pd.DataFrame(rows)
        except Exception as e:
            logger.error(f"获取股票基础数据失败: {e}")
            return None

    def fetch_stock_history(
        self, code: str, days: int = 100, **kwargs
    ) -> Optional[pd.DataFrame]:
        """获取股票历史数据"""
        try:
            # 从数据库读取历史数据
            query = """
                SELECT date, open, high, low, close, volume
                FROM stock_kline
                WHERE code = ?
                ORDER BY date DESC
                LIMIT ?
            """
            result = self.fetcher.db_manager.query(query, (code, days))
            if result:
                df = pd.DataFrame(result)
                df = df.sort_values("date").reset_index(drop=True)
                return df
            return None
        except Exception as e:
            logger.error(f"获取股票历史数据失败: {e}")
            return None

    def fetch_fund_flow(self, code: str, **kwargs) -> Optional[pd.DataFrame]:
        """获取资金流向"""
        try:
            query = """
                SELECT date, main_net_inflow
                FROM stock_fund_flow
                WHERE code = ?
                ORDER BY date DESC
                LIMIT 30
            """
            result = self.fetcher.db_manager.query(query, (code,))
            if result:
                return pd.DataFrame(result)
            return None
        except Exception as e:
            logger.error(f"获取资金流向失败: {e}")
            return None

    def fetch_industry_data(self, **kwargs) -> Optional[pd.DataFrame]:
        """获取行业数据"""
        try:
            query = """
                SELECT code, industry
                FROM stock_basic
                WHERE industry IS NOT NULL
            """
            result = self.fetcher.db_manager.query(query)
            if result:
                return pd.DataFrame(result)
            return None
        except Exception as e:
            logger.error(f"获取行业数据失败: {e}")
            return None

    def fetch_sector_data(self, **kwargs) -> Optional[pd.DataFrame]:
        """获取板块数据"""
        try:
            query = """
                SELECT code, area as sector
                FROM stock_basic
                WHERE area IS NOT NULL
            """
            result = self.fetcher.db_manager.query(query)
            if result:
                return pd.DataFrame(result)
            return None
        except Exception as e:
            logger.error(f"获取板块数据失败: {e}")
            return None
