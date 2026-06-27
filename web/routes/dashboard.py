"""
仪表盘路由 - /api/dashboard/*
"""
from typing import Any
from datetime import datetime
from flask import Blueprint, request, jsonify
from web.deps import get_db_manager
from utils.log_config import get_logger

dashboard_bp = Blueprint("dashboard", __name__, url_prefix="/api/dashboard")
logger = get_logger(__name__)


def _get_latest_trading_date() -> str:
    """获取最近交易日（考虑收盘时间）"""
    now = datetime.now()
    today_str = now.strftime("%Y-%m-%d")
    is_market_closed = now.hour >= 15

    from utils.trade_date_utils import is_trading_day, get_previous_trading_day

    if is_trading_day(today_str) and is_market_closed:
        return today_str
    elif is_trading_day(today_str) and not is_market_closed:
        return get_previous_trading_day(today_str)
    else:
        return get_previous_trading_day(today_str)


@dashboard_bp.route("/my-golden-stocks")
def get_my_golden_stocks() -> Any:
    """获取我的金股 - 最近交易日的top5股票"""
    try:
        db_manager = get_db_manager()
        target_date = _get_latest_trading_date()

        rows = db_manager.query(
            """
            SELECT stock_code, stock_name, industry, sector, score, rank_position
            FROM stock_selection_record
            WHERE selection_date = ?
            ORDER BY rank_position ASC
            LIMIT 5
            """,
            (target_date,),
        )

        if not rows:
            return jsonify({"success": True, "date": target_date, "stocks": []})

        items = []
        for row in rows:
            items.append(
                {
                    "stock_code": row["stock_code"],
                    "stock_name": row["stock_name"],
                    "industry": row["industry"] or "-",
                    "area": row["sector"] or "-",
                    "total_score": row["score"] or 0,
                }
            )

        return jsonify({"success": True, "date": target_date, "stocks": items})
    except Exception as e:
        logger.error(f"获取我的金股失败: {str(e)}")
        return jsonify({"success": False, "error": str(e)})


@dashboard_bp.route("/hot-industries")
def get_hot_industries() -> Any:
    """获取最热行业 - top50股票的行业分布"""
    try:
        db_manager = get_db_manager()
        score_date = _get_latest_trading_date()

        rows = db_manager.query(
            """
            SELECT industry
            FROM stock_selection_record
            WHERE selection_date = ?
            ORDER BY rank_position ASC
            LIMIT 50
            """,
            (score_date,),
        )

        if not rows:
            return jsonify({"success": True, "date": score_date, "industries": []})

        industry_count: dict[str, int] = {}
        for row in rows:
            industry = row["industry"] or "未知"
            industry_count[industry] = industry_count.get(industry, 0) + 1

        industries = []
        total = len(rows)
        for industry, count in industry_count.items():
            industries.append(
                {
                    "industry": industry,
                    "count": count,
                    "percentage": round(count / total * 100, 2),
                }
            )

        industries.sort(key=lambda x: x["count"], reverse=True)

        return jsonify({"success": True, "date": score_date, "industries": industries})
    except Exception as e:
        logger.error(f"获取最热行业失败: {str(e)}")
        return jsonify({"success": False, "error": str(e)})


@dashboard_bp.route("/hot-areas")
def get_hot_areas() -> Any:
    """获取最热板块 - top50股票的板块分布"""
    try:
        db_manager = get_db_manager()
        score_date = _get_latest_trading_date()

        rows = db_manager.query(
            """
            SELECT sector
            FROM stock_selection_record
            WHERE selection_date = ?
            ORDER BY rank_position ASC
            LIMIT 50
            """,
            (score_date,),
        )

        if not rows:
            return jsonify({"success": True, "date": score_date, "areas": []})

        area_count: dict[str, int] = {}
        for row in rows:
            area = row["sector"] or "未知"
            area_count[area] = area_count.get(area, 0) + 1

        areas = []
        total = len(rows)
        for area, count in area_count.items():
            areas.append(
                {
                    "area": area,
                    "count": count,
                    "percentage": round(count / total * 100, 2),
                }
            )

        areas.sort(key=lambda x: x["count"], reverse=True)

        return jsonify({"success": True, "date": score_date, "areas": areas})
    except Exception as e:
        logger.error(f"获取最热板块失败: {str(e)}")
        return jsonify({"success": False, "error": str(e)})


@dashboard_bp.route("/industry-stocks")
def get_industry_stocks() -> Any:
    """获取指定行业的股票列表"""
    try:
        db_manager = get_db_manager()
        industry = request.args.get("industry", "")
        limit = int(request.args.get("limit", 50))

        if not industry:
            return jsonify({"success": False, "error": "行业参数不能为空"})

        date_result = db_manager.query(
            "SELECT DISTINCT selection_date FROM stock_selection_record ORDER BY selection_date DESC LIMIT 1"
        )
        if not date_result:
            return jsonify({"success": True, "stocks": []})

        score_date = date_result[0]["selection_date"]

        rows = db_manager.query(
            """
            SELECT stock_code, stock_name, industry, sector, score, rank_position, selection_price
            FROM stock_selection_record
            WHERE selection_date = ? AND industry = ?
            ORDER BY score DESC
            LIMIT ?
            """,
            (score_date, industry, limit),
        )

        stocks = []
        for row in rows:
            stocks.append(
                {
                    "stock_code": row["stock_code"],
                    "stock_name": row["stock_name"],
                    "industry": row["industry"] or "-",
                    "sector": row["sector"] or "-",
                    "score": row["score"] or 0,
                    "rank_position": row["rank_position"] or 0,
                    "selection_price": row["selection_price"] or 0,
                }
            )

        return jsonify({"success": True, "stocks": stocks})
    except Exception as e:
        logger.error(f"获取行业股票失败: {str(e)}")
        return jsonify({"success": False, "error": str(e)})


@dashboard_bp.route("/area-stocks")
def get_area_stocks() -> Any:
    """获取指定板块的股票列表"""
    try:
        db_manager = get_db_manager()
        area = request.args.get("area", "")
        limit = int(request.args.get("limit", 50))

        if not area:
            return jsonify({"success": False, "error": "板块参数不能为空"})

        date_result = db_manager.query(
            "SELECT DISTINCT selection_date FROM stock_selection_record ORDER BY selection_date DESC LIMIT 1"
        )
        if not date_result:
            return jsonify({"success": True, "stocks": []})

        score_date = date_result[0]["selection_date"]

        rows = db_manager.query(
            """
            SELECT stock_code, stock_name, industry, sector, score, rank_position, selection_price
            FROM stock_selection_record
            WHERE selection_date = ? AND sector = ?
            ORDER BY score DESC
            LIMIT ?
            """,
            (score_date, area, limit),
        )

        stocks = []
        for row in rows:
            stocks.append(
                {
                    "stock_code": row["stock_code"],
                    "stock_name": row["stock_name"],
                    "industry": row["industry"] or "-",
                    "sector": row["sector"] or "-",
                    "score": row["score"] or 0,
                    "rank_position": row["rank_position"] or 0,
                    "selection_price": row["selection_price"] or 0,
                }
            )

        return jsonify({"success": True, "stocks": stocks})
    except Exception as e:
        logger.error(f"获取板块股票失败: {str(e)}")
        return jsonify({"success": False, "error": str(e)})
