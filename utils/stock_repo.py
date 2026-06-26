"""
股票数据仓库模块

提供股票 K 线数据和基本信息的访问接口，封装 stock_kline 和 stock_basic 表的操作。
通过依赖注入获取 DBManager 实例，便于测试替换。
"""

import logging
from typing import Dict, List, Optional

import pandas as pd

from utils.db_manager import DBManager

logger = logging.getLogger(__name__)


class StockRepo:
    """
    股票数据仓库

    封装 stock_kline 和 stock_basic 表的所有查询操作。
    通过构造函数注入 DBManager，支持用内存 DB 测试。
    """

    def __init__(self, db: DBManager):
        """
        初始化股票数据仓库

        Args:
            db: DBManager 实例
        """
        self._db = db

    # ==================== stock_kline 相关 ====================

    def read_stock(
        self,
        stock_code: str,
        start_date: str = None,
        end_date: str = None,
        limit: int = None,
        order: str = 'desc',
    ) -> pd.DataFrame:
        """
        读取股票K线数据

        Args:
            stock_code: 股票代码，例如000001
            start_date: 开始日期，格式为YYYY-MM-DD，None表示无限制
            end_date: 结束日期，格式为YYYY-MM-DD，None表示无限制
            limit: 限制返回的行数，None表示无限制
            order: 排序方式，'asc'升序或'desc'降序(默认)

        Returns:
            pd.DataFrame: 股票数据，包含date, open, high, low, close, volume等列
        """
        try:
            sql = """
                SELECT code, date, open, high, low, close, volume, market_cap, K, D, J
                FROM stock_kline
                WHERE code = ?
            """
            params: list = [stock_code]

            if start_date:
                start_date_formatted = (
                    start_date if '-' in start_date
                    else f"{start_date[:4]}-{start_date[4:6]}-{start_date[6:]}"
                )
                sql += " AND date >= ?"
                params.append(start_date_formatted)

            if end_date:
                end_date_formatted = (
                    end_date if '-' in end_date
                    else f"{end_date[:4]}-{end_date[4:6]}-{end_date[6:]}"
                )
                sql += " AND date <= ?"
                params.append(end_date_formatted)

            sql += " ORDER BY date DESC" if order == 'desc' else " ORDER BY date ASC"

            if limit:
                sql += f" LIMIT {limit}"

            results = self._db.query(sql, tuple(params))

            if not results:
                logger.debug(f"股票数据为空: {stock_code}")
                return pd.DataFrame()

            df = pd.DataFrame(results)
            df['date'] = pd.to_datetime(df['date'])
            logger.debug(f"读取股票数据成功: {stock_code}, 行数: {len(df)}")
            return df
        except Exception as e:
            logger.error(f"读取股票数据失败: {stock_code} - {str(e)}")
            return pd.DataFrame()

    def write_stock(self, stock_code: str, df: pd.DataFrame) -> bool:
        """
        写入股票K线数据

        Args:
            stock_code: 股票代码
            df: 股票数据DataFrame，必须包含date列

        Returns:
            bool: 是否写入成功
        """
        if df.empty:
            logger.warning(f"股票数据为空，跳过写入: {stock_code}")
            return False

        try:
            from utils.date_utils import normalize_date

            df = df.drop_duplicates(subset=['date'], keep='last')

            data_list = []
            for _, row in df.iterrows():
                normalized_date = normalize_date(row['date'])
                data = {
                    'code': stock_code,
                    'date': normalized_date,
                    'open': float(row.get('open', 0)) if pd.notna(row.get('open')) else None,
                    'high': float(row.get('high', 0)) if pd.notna(row.get('high')) else None,
                    'low': float(row.get('low', 0)) if pd.notna(row.get('low')) else None,
                    'close': float(row.get('close', 0)) if pd.notna(row.get('close')) else None,
                    'volume': int(row.get('volume', 0)) if pd.notna(row.get('volume')) else None,
                    'market_cap': float(row.get('market_cap', 0)) if pd.notna(row.get('market_cap')) else None,
                    'K': float(row.get('K', 0)) if pd.notna(row.get('K')) else None,
                    'D': float(row.get('D', 0)) if pd.notna(row.get('D')) else None,
                    'J': float(row.get('J', 0)) if pd.notna(row.get('J')) else None,
                }
                data_list.append(data)

            with self._db.transaction():
                for data in data_list:
                    self._db.delete('stock_kline', {'code': stock_code, 'date': data['date']})
                    self._db.insert('stock_kline', data)

            logger.debug(f"写入股票数据成功: {stock_code}, 行数: {len(data_list)}")
            return True
        except Exception as e:
            logger.error(f"写入股票数据失败: {stock_code} - {str(e)}")
            return False

    def update_stock(self, stock_code: str, new_df: pd.DataFrame) -> bool:
        """
        增量更新股票数据

        Args:
            stock_code: 股票代码
            new_df: 新的股票数据DataFrame

        Returns:
            bool: 是否更新成功
        """
        if new_df.empty:
            logger.warning(f"新股票数据为空，跳过更新: {stock_code}")
            return False

        try:
            existing_df = self.read_stock(stock_code)

            if not existing_df.empty:
                combined_df = pd.concat([existing_df, new_df], ignore_index=True)
            else:
                combined_df = new_df

            return self.write_stock(stock_code, combined_df)
        except Exception as e:
            logger.error(f"更新股票数据失败: {stock_code} - {str(e)}")
            return False

    def list_all_stocks(self) -> List[str]:
        """
        列出所有已保存的股票代码

        Returns:
            List[str]: 股票代码列表，已排序
        """
        try:
            sql = "SELECT DISTINCT code FROM stock_kline ORDER BY code"
            results = self._db.query(sql)
            stocks = [row['code'] for row in results]
            logger.debug(f"列出所有股票成功，共{len(stocks)}只")
            return stocks
        except Exception as e:
            logger.debug(f"列出所有股票失败: {str(e)}")
            return []

    def stock_exists(self, stock_code: str) -> bool:
        """
        检查股票数据是否存在

        Args:
            stock_code: 股票代码

        Returns:
            bool: 股票数据是否存在
        """
        try:
            sql = "SELECT COUNT(*) as count FROM stock_kline WHERE code = ?"
            result = self._db.query_one(sql, (stock_code,))
            exists = result and result['count'] > 0
            logger.debug(f"检查股票存在性: {stock_code}, 存在: {exists}")
            return exists
        except Exception as e:
            logger.debug(f"检查股票存在性失败: {stock_code} - {str(e)}")
            return False

    def get_stock_count(self) -> int:
        """
        获取已保存的股票数量

        Returns:
            int: 股票数量
        """
        try:
            sql = "SELECT COUNT(DISTINCT code) as count FROM stock_kline"
            result = self._db.query_one(sql)
            count = result['count'] if result else 0
            logger.debug(f"获取股票数量成功: {count}")
            return count
        except Exception as e:
            logger.debug(f"获取股票数量失败: {str(e)}")
            return 0

    def get_latest_trading_date(self) -> Optional[str]:
        """
        获取数据库中所有股票的最晚交易日期（统一交易日）

        Returns:
            str: 最晚交易日期（YYYY-MM-DD格式），如果失败返回None
        """
        try:
            from utils.date_utils import normalize_date
            sql = "SELECT MAX(date) as max_date FROM stock_kline"
            result = self._db.query_one(sql)
            max_date = result['max_date'] if result and result.get('max_date') else None
            if max_date:
                max_date = normalize_date(max_date)
            logger.debug(f"获取最晚交易日期成功: {max_date}")
            return max_date
        except Exception as e:
            logger.debug(f"获取最晚交易日期失败: {str(e)}")
            return None

    # ==================== stock_basic 相关 ====================

    def get_stock_name(self, stock_code: str) -> str:
        """
        从 stock_basic 表获取股票名称

        Args:
            stock_code: 股票代码（6位数字）

        Returns:
            str: 股票名称，如果不存在则返回 '未知'
        """
        try:
            sql = "SELECT name FROM stock_basic WHERE code = ?"
            result = self._db.query_one(sql, (stock_code,))
            if result and result.get('name'):
                return result['name']
            return '未知'
        except Exception as e:
            logger.debug(f"获取股票名称失败: {stock_code} - {str(e)}")
            return '未知'

    def get_all_stock_names(self) -> Dict[str, str]:
        """
        获取所有股票的代码和名称映射

        Returns:
            dict: {代码: 名称} 的字典
        """
        try:
            sql = "SELECT code, name FROM stock_basic WHERE code IS NOT NULL"
            results = self._db.query(sql)
            stock_names: Dict[str, str] = {}
            for row in results:
                code = row.get('code')
                name = row.get('name', '未知')
                if code:
                    stock_names[code] = name
            logger.debug(f"获取所有股票名称成功: {len(stock_names)} 只")
            return stock_names
        except Exception as e:
            logger.debug(f"获取所有股票名称失败: {str(e)}")
            return {}
