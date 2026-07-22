"""
系统管理路由 - /api/stats, /api/config, /api/update
"""
from typing import Any
from flask import Blueprint, request, jsonify
from web.deps import (
    get_db_manager,
    get_data_collection_service,
)
from utils.log_config import get_logger

system_bp = Blueprint("system", __name__)
logger = get_logger(__name__)


@system_bp.route("/api/stats")
def get_stats() -> Any:
    """获取系统统计信息"""
    try:
        db_manager = get_db_manager()

        # 获取股票总数
        stock_count_result = db_manager.query(
            "SELECT COUNT(*) as count FROM stock_basic"
        )
        stock_count = stock_count_result[0]["count"] if stock_count_result else 0

        # 获取K线数据总数
        kline_count_result = db_manager.query(
            "SELECT COUNT(*) as count FROM stock_kline"
        )
        kline_count = kline_count_result[0]["count"] if kline_count_result else 0

        # 获取最新数据日期
        latest_date_result = db_manager.query(
            "SELECT MAX(date) as latest_date FROM stock_kline"
        )
        latest_date = (
            latest_date_result[0]["latest_date"] if latest_date_result else "未知"
        )

        # 获取选股记录数
        selection_count_result = db_manager.query(
            "SELECT COUNT(*) as count FROM stock_selection_record"
        )
        selection_count = (
            selection_count_result[0]["count"] if selection_count_result else 0
        )

        return jsonify(
            {
                "success": True,
                "data": {
                    "stock_count": stock_count,
                    "kline_count": kline_count,
                    "latest_date": latest_date,
                    "selection_count": selection_count,
                },
            }
        )
    except Exception as e:
        logger.error(f"获取统计信息失败: {str(e)}")
        return jsonify({"success": False, "error": str(e)})


@system_bp.route("/api/config", methods=["GET"])
def get_config() -> Any:
    """获取系统配置"""
    try:
        from utils.app_config import get_app_config

        config = get_app_config().get_all()
        return jsonify({"success": True, "data": config})
    except Exception as e:
        logger.error(f"获取配置失败: {str(e)}")
        return jsonify({"success": False, "error": str(e)})


@system_bp.route("/api/config", methods=["POST"])
def update_config() -> Any:
    """更新系统配置"""
    try:
        from utils.app_config import get_app_config

        data = request.get_json(silent=True) or {}
        get_app_config().update(data)
        return jsonify({"success": True, "message": "配置已更新"})
    except Exception as e:
        logger.error(f"更新配置失败: {str(e)}")
        return jsonify({"success": False, "error": str(e)})


@system_bp.route("/api/update", methods=["POST"])
def update_data() -> Any:
    """更新数据"""
    try:
        data = request.get_json(silent=True) or {}
        max_stocks = data.get("max_stocks")

        data_collection_service = get_data_collection_service()

        # 启动数据更新任务
        result = data_collection_service.start_update()

        if result.get("success"):
            return jsonify({
                "success": True,
                "message": result.get("message", "数据更新已启动"),
                "taskId": result.get("taskId")
            })
        else:
            return jsonify({
                "success": False,
                "message": result.get("message", "启动更新失败")
            })
    except Exception as e:
        logger.error(f"启动数据更新失败: {str(e)}")
        return jsonify({"success": False, "error": str(e)})


@system_bp.route("/api/update/status", methods=["GET"])
def get_update_status() -> Any:
    """获取数据更新状态"""
    try:
        data_collection_service = get_data_collection_service()
        status = data_collection_service.get_update_progress()

        return jsonify({"success": True, "data": status})
    except Exception as e:
        logger.error(f"获取更新状态失败: {str(e)}")
        return jsonify({"success": False, "error": str(e)})
