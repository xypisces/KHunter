"""
全局数据库管理器模块

提供全局的 DBManager 和 StockRepo 实例，供所有模块共享，
避免创建多个数据库连接导致的死锁问题。
"""

from utils.db_manager import DBManager

# 创建全局 DBManager 实例
global_db_manager = DBManager()


def get_global_db() -> DBManager:
    """
    获取全局数据库管理器实例

    Returns:
        DBManager: 全局数据库管理器实例
    """
    return global_db_manager


# 延迟初始化的 StockRepo 单例
_stock_repo = None


def get_stock_repo():
    """
    获取全局股票数据仓库实例（延迟初始化）

    Returns:
        StockRepo: 全局股票数据仓库实例
    """
    global _stock_repo
    if _stock_repo is None:
        from utils.stock_repo import StockRepo
        _stock_repo = StockRepo(get_global_db())
    return _stock_repo
