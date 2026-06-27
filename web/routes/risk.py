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
                SELECT risk_date, var_1d, var_5d, max_drawdown, volatility, risk_level
                FROM risk_status
                WHERE risk_date = ?
                """,
                (date,),
            )
        else:
            rows = db_manager.query(
                """
                SELECT risk_date, var_1d, var_5d, max_drawdown, volatility, risk_level
                FROM risk_status
                ORDER BY risk_date DESC
                LIMIT 1
                """
            )

        if rows:
            row = rows[0]
            return jsonify(
                {
                    "success": True,
                    "data": {
                        "date": row["risk_date"],
                        "var_1d": row["var_1d"],
                        "var_5d": row["var_5d"],
                        "max_drawdown": row["max_drawdown"],
                        "volatility": row["volatility"],
                        "risk_level": row["risk_level"],
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


@risk_bp.route("/alerts")
def get_risk_alerts() -> Any:
    """获取风控预警"""
    try:
        db_manager = get_db_manager()
        limit = int(request.args.get("limit", 20))

        rows = db_manager.query(
            """
            SELECT alert_date, alert_type, stock_code, stock_name, message, level
            FROM risk_alerts
            ORDER BY alert_date DESC
            LIMIT ?
            """,
            (limit,),
        )

        return jsonify({"success": True, "data": rows})
    except Exception as e:
        logger.error(f"获取风控预警失败: {str(e)}")
        return jsonify({"success": False, "error": str(e)})
