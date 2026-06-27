"""
依赖注入辅助模块 - 提供便捷的依赖获取函数
"""
from typing import Any
from flask import current_app
from utils.db_manager import DBManager
from strategy.strategy_registry import StrategyRegistry
from utils.selection_record_manager import SelectionRecordManager
from utils.ranking_manager import RankingManager
from utils.stock_filter import StockFilter
from utils.data_collection_service import DataCollectionService
from utils.kline_initializer import KlineInitializer
from utils.akshare_fetcher import AKShareFetcher
from stock_analyzer import StockAnalyzer


def get_db_manager() -> DBManager:
    """获取数据库管理器"""
    return current_app.config["db_manager"]


def get_stock_repo() -> Any:
    """获取股票仓库"""
    return current_app.config["stock_repo"]


def get_registry() -> StrategyRegistry:
    """获取策略注册器"""
    return current_app.config["registry"]


def get_selection_record_manager() -> SelectionRecordManager:
    """获取选股记录管理器"""
    return current_app.config["selection_record_manager"]


def get_ranking_manager() -> RankingManager:
    """获取排名管理器"""
    return current_app.config["ranking_manager"]


def get_stock_analyzer() -> StockAnalyzer:
    """获取股票分析器"""
    return current_app.config["stock_analyzer"]


def get_data_collection_service() -> DataCollectionService:
    """获取数据采集服务"""
    return current_app.config["data_collection_service"]


def get_kline_initializer() -> KlineInitializer:
    """获取K线初始化器"""
    return current_app.config["kline_initializer"]


def get_akshare_fetcher() -> AKShareFetcher:
    """获取AKShare数据获取器"""
    return current_app.config["akshare_fetcher"]


def get_param_lock() -> Any:
    """获取参数锁定器"""
    return current_app.config["param_lock"]


def get_param_tracker() -> Any:
    """获取参数追踪器"""
    return current_app.config["param_tracker"]
