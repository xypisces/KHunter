"""
股票分析路由 - /api/analyze-stock, /api/analysis-history, /api/export-report
"""
from typing import Any
from flask import Blueprint, request, jsonify, send_file
from web.deps import get_db_manager, get_stock_analyzer
from utils.log_config import get_logger

analysis_bp = Blueprint("analysis", __name__)
logger = get_logger(__name__)


@analysis_bp.route("/api/analyze-stock", methods=["POST"])
def analyze_stock() -> Any:
    """分析单只股票"""
    try:
        data = request.get_json(silent=True) or {}
        stock_code = data.get("stock_code", "")
        stock_name = data.get("stock_name", "")

        if not stock_code:
            return jsonify({"success": False, "error": "股票代码不能为空"})

        stock_analyzer = get_stock_analyzer()
        result = stock_analyzer.analyze(stock_code, stock_name)

        return jsonify({"success": True, "data": result})
    except Exception as e:
        logger.error(f"分析股票失败: {str(e)}")
        return jsonify({"success": False, "error": str(e)})


@analysis_bp.route("/api/analysis-history")
def get_analysis_history() -> Any:
    """获取分析历史"""
    try:
        db_manager = get_db_manager()
        page = int(request.args.get("page", 1))
        per_page = int(request.args.get("per_page", 20))

        offset = (page - 1) * per_page

        rows = db_manager.query(
            """
            SELECT stock_code, stock_name, analysis_date, analysis_type, result
            FROM stock_analysis_record
            ORDER BY analysis_date DESC
            LIMIT ? OFFSET ?
            """,
            (per_page, offset),
        )

        count_result = db_manager.query(
            "SELECT COUNT(*) as count FROM stock_analysis_record"
        )
        total = count_result[0]["count"] if count_result else 0

        return jsonify(
            {
                "success": True,
                "data": {
                    "records": rows,
                    "total": total,
                    "page": page,
                    "per_page": per_page,
                },
            }
        )
    except Exception as e:
        logger.error(f"获取分析历史失败: {str(e)}")
        return jsonify({"success": False, "error": str(e)})


@analysis_bp.route("/api/export-report")
def export_report() -> Any:
    """导出分析报告"""
    try:
        report_id = request.args.get("report_id", "")
        if not report_id:
            return jsonify({"success": False, "error": "报告ID不能为空"})

        # 生成报告文件
        import tempfile
        import os

        # 创建临时文件
        temp_dir = tempfile.gettempdir()
        report_path = os.path.join(temp_dir, f"report_{report_id}.pdf")

        # 检查文件是否存在
        if not os.path.exists(report_path):
            return jsonify({"success": False, "error": "报告不存在"})

        return send_file(
            report_path,
            mimetype="application/pdf",
            as_attachment=True,
            download_name=f"analysis_report_{report_id}.pdf",
        )
    except Exception as e:
        logger.error(f"导出报告失败: {str(e)}")
        return jsonify({"success": False, "error": str(e)})
