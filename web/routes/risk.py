"""
风控模块路由 - /api/risk/*
"""
from typing import Any
from flask import Blueprint, request, jsonify
from web.deps import get_db_manager
from utils.log_config import get_logger

risk_bp = Blueprint("risk", __name__, url_prefix="/api/risk")
logger = get_logger(__name__)


@risk_bp.route("/status")
def get_risk_status() -> Any:
    """获取当日风控状态"""
    try:
        db_manager = get_db_manager()
        date = request.args.get("date")
        force_refresh = request.args.get("force_refresh", "false").lower() == "true"

        # 获取风控数据
        if date:
            rows = db_manager.query(
                """
                SELECT date, var_1d, var_5d, es_1d, risk_level,
                       position_limit, stop_loss_multiplier, liquidate
                FROM risk_status
                WHERE date = ?
                """,
                (date,),
            )
        else:
            rows = db_manager.query(
                """
                SELECT date, var_1d, var_5d, es_1d, risk_level,
                       position_limit, stop_loss_multiplier, liquidate
                FROM risk_status
                ORDER BY date DESC
                LIMIT 1
                """
            )

        if rows:
            row = rows[0]
            return jsonify(
                {
                    "success": True,
                    "data": {
                        "date": row["date"],
                        "var_1d": row["var_1d"],
                        "var_5d": row["var_5d"],
                        "es_1d": row["es_1d"],
                        "risk_level": row["risk_level"],
                        "position_limit": row["position_limit"],
                        "stop_loss_multiplier": row["stop_loss_multiplier"],
                        "liquidate": bool(row["liquidate"]),
                    },
                }
            )
        else:
            return jsonify(
                {
                    "success": True,
                    "data": None,
                    "message": "暂无风控数据",
                }
            )
    except Exception as e:
        logger.error(f"获取风控状态失败: {str(e)}")
        return jsonify({"success": False, "error": str(e)})


@risk_bp.route("/history")
def get_risk_history() -> Any:
    """获取风控历史记录"""
    try:
        db_manager = get_db_manager()
        days = int(request.args.get("days", 30))

        rows = db_manager.query(
            """
            SELECT date, var_1d, var_5d, es_1d, risk_level,
                   position_limit, stop_loss_multiplier, liquidate
            FROM risk_status
            ORDER BY date DESC
            LIMIT ?
            """,
            (days,),
        )

        return jsonify({"success": True, "data": [dict(r) for r in rows]})
    except Exception as e:
        logger.error(f"获取风控历史失败: {str(e)}")
        return jsonify({"success": False, "error": str(e)})


@risk_bp.route("/alerts")
def get_risk_alerts() -> Any:
    """获取风控预警"""
    try:
        db_manager = get_db_manager()
        limit = int(request.args.get("limit", 20))

        # risk_alerts 表可能不存在，做兼容处理
        table_check = db_manager.query(
            "SELECT name FROM sqlite_master WHERE type='table' AND name='risk_alerts'"
        )
        if not table_check:
            return jsonify({"success": True, "data": [], "message": "预警表尚未创建"})

        rows = db_manager.query(
            """
            SELECT date as alert_date, '' as alert_type, '' as stock_code,
                   '' as stock_name, '' as message, risk_level as level
            FROM risk_status
            ORDER BY date DESC
            LIMIT ?
            """,
            (limit,),
        )

        return jsonify({"success": True, "data": [dict(r) for r in rows]})
    except Exception as e:
        logger.error(f"获取风控预警失败: {str(e)}")
        return jsonify({"success": False, "error": str(e)})
