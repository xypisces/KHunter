"""
狩猎场路由 - /api/khunter/*
从 trading/routes.py 拆分
"""
from typing import Any
from flask import Blueprint, request, jsonify
from web.deps import get_db_manager
from utils.log_config import get_logger

khunter_bp = Blueprint("khunter", __name__, url_prefix="/api/khunter")
logger = get_logger(__name__)


def _get_khunter_api() -> Any:
    """获取KHunter API（延迟初始化）"""
    from trading.khunter_api import KHunterAPI
    from trading.khunter_data_processor import KHunterDataProcessor
    from trading.khunter_dao import KHunterDAO
    from trading.khunter_support_calculator import KHunterSupportCalculator
    from trading.khunter_buy_point_judge import KHunterBuyPointJudge
    from utils.strategy_config_manager import StrategyConfigManager

    db_manager = get_db_manager()
    strategy_config_manager = StrategyConfigManager()
    khunter_dao = KHunterDAO(db_manager)
    khunter_support_calculator = KHunterSupportCalculator(
        db_manager, strategy_config_manager
    )
    khunter_buy_point_judge = KHunterBuyPointJudge(db_manager)
    khunter_data_processor = KHunterDataProcessor(
        db_manager, khunter_support_calculator, khunter_buy_point_judge
    )

    return KHunterAPI(db_manager, khunter_data_processor, khunter_dao)


@khunter_bp.route("/calculate", methods=["POST"])
def calculate() -> Any:
    """计算狩猎场数据"""
    try:
        data = request.get_json(silent=True) or {}
        hunting_date = data.get("hunting_date")
        tracking_days = data.get("tracking_days", 10)

        if not hunting_date:
            return jsonify({"success": False, "error": "狩猎日期不能为空"})

        khunter_api = _get_khunter_api()
        result = khunter_api.calculate(hunting_date, tracking_days)

        return jsonify({"success": True, "data": result})
    except Exception as e:
        logger.error(f"计算狩猎场数据失败: {str(e)}")
        return jsonify({"success": False, "error": str(e)})


@khunter_bp.route("/save", methods=["POST"])
def save() -> Any:
    """保存狩猎场数据"""
    try:
        data = request.get_json(silent=True) or {}

        khunter_api = _get_khunter_api()
        result = khunter_api.save(data)

        return jsonify({"success": True, "data": result})
    except Exception as e:
        logger.error(f"保存狩猎场数据失败: {str(e)}")
        return jsonify({"success": False, "error": str(e)})


@khunter_bp.route("/query", methods=["GET"])
def query() -> Any:
    """查询狩猎场数据"""
    try:
        hunting_date = request.args.get("hunting_date")
        stock_code = request.args.get("stock_code")

        khunter_api = _get_khunter_api()
        result = khunter_api.query(hunting_date=hunting_date, stock_code=stock_code)

        return jsonify({"success": True, "data": result})
    except Exception as e:
        logger.error(f"查询狩猎场数据失败: {str(e)}")
        return jsonify({"success": False, "error": str(e)})


@khunter_bp.route("/check-cache", methods=["GET"])
def check_cache() -> Any:
    """检查缓存状态"""
    try:
        hunting_date = request.args.get("hunting_date")

        khunter_api = _get_khunter_api()
        result = khunter_api.check_cache(hunting_date)

        return jsonify({"success": True, "data": result})
    except Exception as e:
        logger.error(f"检查缓存失败: {str(e)}")
        return jsonify({"success": False, "error": str(e)})


@khunter_bp.route("/track", methods=["GET"])
def track() -> Any:
    """获取跟踪数据"""
    try:
        stock_code = request.args.get("stock_code")
        days = int(request.args.get("days", 10))

        khunter_api = _get_khunter_api()
        result = khunter_api.track(stock_code, days)

        return jsonify({"success": True, "data": result})
    except Exception as e:
        logger.error(f"获取跟踪数据失败: {str(e)}")
        return jsonify({"success": False, "error": str(e)})


@khunter_bp.route("/latest_kline_date", methods=["GET"])
def get_latest_kline_date() -> Any:
    """获取最新K线日期"""
    try:
        khunter_api = _get_khunter_api()
        result = khunter_api.get_latest_kline_date()

        return jsonify({"success": True, "data": result})
    except Exception as e:
        logger.error(f"获取最新K线日期失败: {str(e)}")
        return jsonify({"success": False, "error": str(e)})


@khunter_bp.route("/generate_plan", methods=["POST"])
def generate_plan() -> Any:
    """生成执行计划"""
    try:
        data = request.get_json(silent=True) or {}

        khunter_api = _get_khunter_api()
        result = khunter_api.generate_plan(data)

        return jsonify({"success": True, "data": result})
    except Exception as e:
        logger.error(f"生成执行计划失败: {str(e)}")
        return jsonify({"success": False, "error": str(e)})
