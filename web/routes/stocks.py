"""
股票数据路由 - /api/stocks, /api/stock/<code>
"""
from typing import Any
import pandas as pd
from datetime import datetime as dt, timedelta
from flask import Blueprint, request, jsonify
from web.deps import get_db_manager, get_stock_repo
from utils.log_config import get_logger

stocks_bp = Blueprint("stocks", __name__)
logger = get_logger(__name__)


@stocks_bp.route("/api/stocks")
def get_stocks() -> Any:
    """获取股票列表 - 从 stock_basic 表获取基础数据"""
    try:
        db_manager = get_db_manager()

        # 获取分页参数
        page = int(request.args.get("page", 1))
        per_page = int(request.args.get("per_page", 500))
        offset = (page - 1) * per_page

        # 从 stock_basic 表获取总数
        total_result = db_manager.query("SELECT COUNT(*) as count FROM stock_basic")
        total = total_result[0]["count"] if total_result else 0

        # 从 stock_basic 表获取分页数据
        query = """
            SELECT code, name, industry, area, market, list_date, market_cap
            FROM stock_basic
            ORDER BY code
            LIMIT ? OFFSET ?
        """
        basic_stocks = db_manager.query(query, (per_page, offset))

        stock_list = []
        for stock in basic_stocks:
            # 处理 market_cap
            market_cap = stock.get("market_cap", 0)
            if market_cap is None or (
                isinstance(market_cap, float) and market_cap != market_cap
            ):
                market_cap = 0

            # 单位转换：如果市值 > 10000，说明是万元单位，需要转换为亿元
            if market_cap > 10000:
                market_cap = market_cap / 10000

            # 从 stock_kline 表获取最新价格和日期
            kline_query = """
                SELECT close, date FROM stock_kline
                WHERE code = ?
                ORDER BY date DESC
                LIMIT 1
            """
            kline_result = db_manager.query(kline_query, (stock["code"],))

            latest_price = 0
            latest_date = ""
            data_count = 0

            if kline_result:
                latest_price = round(kline_result[0]["close"], 2)
                latest_date = kline_result[0]["date"]

                count_query = "SELECT COUNT(*) as count FROM stock_kline WHERE code = ?"
                count_result = db_manager.query(count_query, (stock["code"],))
                data_count = count_result[0]["count"] if count_result else 0

            stock_list.append(
                {
                    "code": stock["code"],
                    "name": stock["name"],
                    "latest_price": latest_price,
                    "latest_date": latest_date,
                    "market_cap": round(market_cap, 2),
                    "data_count": data_count,
                }
            )

        return jsonify(
            {
                "success": True,
                "data": stock_list,
                "total": total,
                "page": page,
                "per_page": per_page,
                "total_pages": (total + per_page - 1) // per_page,
            }
        )
    except Exception as e:
        return jsonify({"success": False, "error": str(e)})


@stocks_bp.route("/api/stock/<code>")
def get_stock_detail(code: str) -> Any:
    """获取单只股票详情"""
    try:
        stock_repo = get_stock_repo()

        # 从数据库读取股票数据
        df = stock_repo.read_stock(code)

        # 如果数据库没有数据，尝试从Tushare实时获取
        if df.empty:
            logger.info(f"数据库中无 {code} 数据，尝试从Tushare获取")
            try:
                import tushare as ts  # type: ignore[import-untyped]

                pro = ts.pro_api()
                # 转换代码格式
                if not code.endswith((".SH", ".SZ")):
                    if code.startswith("6"):
                        code_fmt = f"{code}.SH"
                    else:
                        code_fmt = f"{code}.SZ"
                else:
                    code_fmt = code

                end_date = dt.now().strftime("%Y%m%d")
                start_date = (dt.now() - timedelta(days=400)).strftime("%Y%m%d")

                df = pro.daily(
                    ts_code=code_fmt, start_date=start_date, end_date=end_date
                )

                if df is not None and not df.empty:
                    df = df.rename(
                        columns={
                            "trade_date": "date",
                            "vol": "volume",
                            "pct_chg": "pct_change",
                        }
                    )
                    df["date"] = pd.to_datetime(df["date"], format="%Y%m%d")
                    df = df.sort_values("date")
                    df = df.reset_index(drop=True)
                    logger.info(f"从Tushare获取 {code} 数据成功，共 {len(df)} 条")
                else:
                    return jsonify(
                        {"success": False, "error": "股票不存在或数据获取失败"}
                    )
            except Exception as e:
                logger.error(f"从Tushare获取 {code} 数据失败: {e}")
                return jsonify({"success": False, "error": "股票不存在"})

        # 确保数据按日期升序排列
        df = df.sort_values("date", ascending=True).reset_index(drop=True)

        # 计算KDJ指标
        from utils.technical import KDJ

        kdj_df = KDJ(df, n=9, m1=3, m2=3)

        # 转换为列表格式，返回最近100条数据
        data = []
        start_idx = max(0, len(df) - 100)
        for i in range(start_idx, len(df)):
            row = df.iloc[i]
            kdj_row = kdj_df.iloc[i]
            data.append(
                {
                    "date": row["date"].strftime("%Y-%m-%d"),
                    "open": round(row["open"], 2) if pd.notna(row["open"]) else None,
                    "high": round(row["high"], 2) if pd.notna(row["high"]) else None,
                    "low": round(row["low"], 2) if pd.notna(row["low"]) else None,
                    "close": round(row["close"], 2) if pd.notna(row["close"]) else None,
                    "volume": int(row["volume"]) if pd.notna(row["volume"]) else 0,
                    "turnover": (
                        round(row.get("turnover", 0), 2)
                        if "turnover" in row and pd.notna(row.get("turnover"))
                        else 0
                    ),
                    "market_cap": (
                        round(row.get("market_cap", 0) / 1e8, 2)
                        if "market_cap" in row and pd.notna(row.get("market_cap"))
                        else 0
                    ),
                    "K": round(kdj_row["K"], 2) if pd.notna(kdj_row["K"]) else None,
                    "D": round(kdj_row["D"], 2) if pd.notna(kdj_row["D"]) else None,
                    "J": round(kdj_row["J"], 2) if pd.notna(kdj_row["J"]) else None,
                }
            )

        return jsonify({"success": True, "code": code, "data": data})
    except Exception as e:
        logger.error(f"获取股票详情失败: {e}")
        return jsonify({"success": False, "error": str(e)})
