"""
Flask 应用工厂 - 创建应用和注入依赖
"""
import sys
import math
from pathlib import Path
from typing import Any
from flask import Flask
from flask_socketio import SocketIO
import numpy as np
import pandas as pd
import logging
from json import JSONEncoder

# 添加项目根目录到路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from utils.db_manager import DBManager
from strategy.strategy_registry import StrategyRegistry, get_registry
from utils.selection_record_manager import SelectionRecordManager
from utils.ranking_manager import RankingManager
from utils.db_initializer import init_databases_if_needed
from utils.stock_filter import StockFilter
from utils.data_collection_service import get_data_collection_service
from utils.kline_initializer import KlineInitializer
from utils.akshare_fetcher import AKShareFetcher
from stock_analyzer import StockAnalyzer
from strategy.param_lock import get_param_lock
from strategy.param_tracker import get_param_tracker
from utils.log_config import LogConfig, get_logger
from utils.db_migration_helper import ensure_database_schema
from utils.global_db import get_global_db, get_stock_repo


class NumpyEncoder(JSONEncoder):
    """自定义JSON编码器，处理numpy类型和NaN值"""

    def default(self, o: Any) -> Any:
        if isinstance(o, np.integer):
            return int(o)
        elif isinstance(o, np.floating):
            if np.isnan(o):
                return None
            elif np.isinf(o):
                return None
            else:
                return float(o)
        elif isinstance(o, np.ndarray):
            return o.tolist()
        elif isinstance(o, pd.Timestamp):
            return o.strftime("%Y-%m-%d %H:%M:%S")
        return super().default(o)

    def encode(self, o: Any) -> str:
        result = super().encode(o)
        result = result.replace("NaN", "null")
        result = result.replace("Infinity", "null")
        result = result.replace("-Infinity", "null")
        return result


def clean_data_for_json(obj: Any) -> Any:
    """
    递归清理数据中的NaN和Inf值，确保可以序列化为JSON
    """
    if isinstance(obj, dict):
        return {k: clean_data_for_json(v) for k, v in obj.items()}
    elif isinstance(obj, list):
        return [clean_data_for_json(item) for item in obj]
    elif isinstance(obj, float):
        if math.isnan(obj) or math.isinf(obj):
            return None
        return obj
    elif isinstance(obj, np.floating):
        if np.isnan(obj) or np.isinf(obj):
            return None
        return float(obj)
    elif isinstance(obj, np.integer):
        return int(obj)
    elif isinstance(obj, np.bool_):
        return bool(obj)
    elif isinstance(obj, np.ndarray):
        return clean_data_for_json(obj.tolist())
    elif isinstance(obj, pd.Timestamp):
        return obj.strftime("%Y-%m-%d %H:%M:%S")
    else:
        return obj


def _init_dependencies(app: Flask) -> None:
    """初始化依赖并注入到 app.config"""
    logger = get_logger(__name__)

    # 初始化数据库
    logger.info("初始化数据库...")
    init_databases_if_needed()
    logger.info("数据库初始化完成")

    # 检查数据库模式
    logger.info("检查数据库模式...")
    ensure_database_schema()
    logger.info("数据库模式检查完成")

    # 全局实例
    app.config["db_manager"] = get_global_db()
    app.config["stock_repo"] = get_stock_repo()
    app.config["registry"] = get_registry("config/strategy_params.yaml")
    app.config["selection_record_manager"] = SelectionRecordManager()
    app.config["ranking_manager"] = RankingManager()
    app.config["stock_analyzer"] = StockAnalyzer()
    app.config["data_collection_service"] = get_data_collection_service("data")

    # 初始化 K线初始化器
    akshare_fetcher = AKShareFetcher("data")
    app.config["akshare_fetcher"] = akshare_fetcher
    app.config["kline_initializer"] = KlineInitializer(
        app.config["db_manager"], akshare_fetcher
    )

    # 初始化参数锁定和追踪
    app.config["param_lock"] = get_param_lock("config/strategy_params.yaml")
    app.config["param_tracker"] = get_param_tracker("config/strategy_params.yaml")

    # 加载策略
    logger.info("正在加载策略...")
    try:
        app.config["registry"].auto_register_from_directory("strategy")
        logger.info(f"已加载 {len(app.config['registry'].strategies)} 个策略")
    except Exception as e:
        logger.error(f"加载策略失败: {str(e)}")
        import traceback
        logger.error(traceback.format_exc())


def _register_blueprints(app: Flask) -> None:
    """注册所有 Blueprint"""
    from web.routes.views import views_bp
    from web.routes.dashboard import dashboard_bp
    from web.routes.stocks import stocks_bp
    from web.routes.signals import signals_bp
    from web.routes.strategies import strategies_bp
    from web.routes.system import system_bp
    from web.routes.analysis import analysis_bp
    from web.routes.risk import risk_bp
    from web.routes.backtest import backtest_bp
    from web.routes.khunter import khunter_bp

    app.register_blueprint(views_bp)
    app.register_blueprint(dashboard_bp)
    app.register_blueprint(stocks_bp)
    app.register_blueprint(signals_bp)
    app.register_blueprint(strategies_bp)
    app.register_blueprint(system_bp)
    app.register_blueprint(analysis_bp)
    app.register_blueprint(risk_bp)
    app.register_blueprint(backtest_bp)
    app.register_blueprint(khunter_bp)


def create_app() -> tuple[Flask, SocketIO]:
    """
    创建 Flask 应用和 SocketIO 实例

    :return: (app, socketio) 元组
    """
    # 配置日志
    LogConfig.setup_logging(log_dir="logs", log_file="app.log")
    logger = get_logger(__name__)
    logger.info("=" * 60)
    logger.info("Web服务器启动")
    logger.info("=" * 60)

    # 创建 Flask 应用
    app = Flask(
        __name__,
        template_folder=str(project_root / "web" / "templates"),
        static_folder=str(project_root / "web" / "static"),
    )

    # 配置 JSON 编码器
    app.json_encoder = NumpyEncoder  # type: ignore[assignment]

    # 创建 SocketIO
    socketio = SocketIO(
        app,
        cors_allowed_origins="*",
        async_mode="threading",
        ping_timeout=3600,
        ping_interval=60,
        max_http_buffer_size=int(1e8),
    )

    # 初始化依赖
    _init_dependencies(app)

    # 注册 Blueprint
    _register_blueprints(app)

    # 注册 WebSocket 事件
    _register_socketio_events(socketio, app)

    return app, socketio


def _register_socketio_events(socketio: SocketIO, app: Flask) -> None:
    """注册 WebSocket 事件"""
    from flask_socketio import emit

    @socketio.on("connect")
    def handle_connect() -> None:
        """客户端连接"""
        logger = get_logger(__name__)
        logger.info("客户端已连接")
        emit("connected", {"status": "ok"})

    @socketio.on("disconnect")
    def handle_disconnect() -> None:
        """客户端断开"""
        logger = get_logger(__name__)
        logger.info("客户端已断开")
