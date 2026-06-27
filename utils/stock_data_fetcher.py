"""
股票基础数据采集器 - 兼容性垫片

此文件已迁移至 utils/market_data/stock_fetcher.py
保留此文件以兼容现有导入。
"""
from utils.market_data.stock_fetcher import *  # noqa: F401,F403
from utils.market_data.stock_fetcher import _tushare_limiter, _TushareRateLimiter  # noqa: F401
