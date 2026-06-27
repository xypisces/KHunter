#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
数据获取模块 - 使用统一数据源

此模块使用 utils/data_fetcher.py 的统一接口获取数据，
避免重复实现和同名类冲突。
"""
import pandas as pd
from typing import Dict, List, Optional, Any
import logging

from utils.data_fetcher import DataFetcher, get_data_fetcher

logger = logging.getLogger(__name__)


class StockAnalyzerDataFetcher:
    """
    股票分析器数据获取 - 使用统一数据源

    通过依赖注入使用 DataFetcher 接口，测试时可替换为 MockDataFetcher。
    """

    def __init__(self, fetcher: Optional[DataFetcher] = None):
        """
        初始化数据获取器

        :param fetcher: DataFetcher 实例，None 则使用全局实例
        """
        self.fetcher = fetcher or get_data_fetcher()

    def get_stock_basic(self, code: str) -> Dict:
        """
        获取股票基本信息

        :param code: 股票代码
        :return: 股票基本信息字典
        """
        try:
            df = self.fetcher.fetch_stock_basic()
            if df is not None and not df.empty:
                stock = df[df["code"] == code]
                if not stock.empty:
                    return stock.iloc[0].to_dict()
            return {"code": code, "name": "未知"}
        except Exception as e:
            logger.error(f"获取股票基本信息失败: {e}")
            return {"code": code, "name": "未知"}

    def get_stock_quote(self, code: str) -> Dict:
        """
        获取股票行情

        :param code: 股票代码
        :return: 股票行情字典
        """
        try:
            df = self.fetcher.fetch_stock_history(code, days=1)
            if df is not None and not df.empty:
                latest = df.iloc[-1]
                return {
                    "code": code,
                    "price": float(latest.get("close", 0)),
                    "open": float(latest.get("open", 0)),
                    "high": float(latest.get("high", 0)),
                    "low": float(latest.get("low", 0)),
                    "volume": int(latest.get("volume", 0)),
                }
            return {"code": code, "price": 0}
        except Exception as e:
            logger.error(f"获取股票行情失败: {e}")
            return {"code": code, "price": 0}

    def get_financial_data(self, code: str) -> Dict:
        """
        获取财务数据

        :param code: 股票代码
        :return: 财务数据字典
        """
        # 暂时返回空，后续可扩展
        return {"code": code}

    def get_fund_flow(self, code: str) -> Dict:
        """
        获取资金流向

        :param code: 股票代码
        :return: 资金流向字典
        """
        try:
            df = self.fetcher.fetch_fund_flow(code)
            if df is not None and not df.empty:
                latest = df.iloc[0]
                return {
                    "code": code,
                    "main_net_inflow": float(latest.get("main_net_inflow", 0)),
                }
            return {"code": code, "main_net_inflow": 0}
        except Exception as e:
            logger.error(f"获取资金流向失败: {e}")
            return {"code": code, "main_net_inflow": 0}

    def get_sector_data(self, code: str) -> Dict:
        """
        获取板块数据

        :param code: 股票代码
        :return: 板块数据字典
        """
        try:
            df = self.fetcher.fetch_sector_data()
            if df is not None and not df.empty:
                stock = df[df["code"] == code]
                if not stock.empty:
                    return stock.iloc[0].to_dict()
            return {"code": code, "sector": "未知"}
        except Exception as e:
            logger.error(f"获取板块数据失败: {e}")
            return {"code": code, "sector": "未知"}

    def get_event_data(self, code: str) -> List[Dict]:
        """
        获取事件数据

        :param code: 股票代码
        :return: 事件数据列表
        """
        try:
            df = self.fetcher.fetch_event_data(code)
            if df is not None and not df.empty:
                return df.to_dict("records")
            return []
        except Exception as e:
            logger.error(f"获取事件数据失败: {e}")
            return []
