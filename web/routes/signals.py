"""
选股信号路由 - /api/select, /api/save_selection, /api/selection-history
"""
from typing import Any
import logging
import traceback
from datetime import datetime as dt
from pathlib import Path
from flask import Blueprint, request, jsonify
from web.deps import (
    get_db_manager,
    get_registry,
    get_selection_record_manager,
    get_param_lock,
    get_param_tracker,
)
from utils.log_config import get_logger

signals_bp = Blueprint("signals", __name__)
logger = get_logger(__name__)


def _analyze_intersection(results: dict) -> dict:
    """分析多策略选股结果的交集"""
    try:
        import yaml

        config_file = Path("config/strategy_params.yaml")
        with open(config_file, "r", encoding="utf-8") as f:
            config = yaml.safe_load(f) or {}

        strategies_config = config.get("strategies", {})
        strategy_display_names = {}
        for strategy_name, strategy_config in strategies_config.items():
            strategy_display_names[strategy_name] = strategy_config.get(
                "display_name", strategy_name
            )

        # 构建股票->策略映射
        stock_strategies: dict = {}
        for strategy_name, signals in results.items():
            if not isinstance(signals, list):
                logger.warning(f"策略 {strategy_name} 的信号不是列表，跳过")
                continue

            for signal in signals:
                if not isinstance(signal, dict) or "code" not in signal:
                    logger.warning(f"无效的信号结构: {signal}")
                    continue

                code = signal["code"]
                if code not in stock_strategies:
                    stock_strategies[code] = {
                        "code": code,
                        "name": signal.get("name", "未知"),
                        "strategies": [],
                        "strategy_display_names": [],
                        "count": 0,
                        "signals": signal.get("signals", []),
                    }

                stock_strategies[code]["strategies"].append(strategy_name)
                stock_strategies[code]["strategy_display_names"].append(
                    strategy_display_names.get(strategy_name, strategy_name)
                )
                stock_strategies[code]["count"] += 1

        # 按交集数量分组
        by_count: dict = {}
        for code, data in stock_strategies.items():
            count = data["count"]
            if count not in by_count:
                by_count[count] = []
            by_count[count].append(data)

        # 计算统计信息
        total_strategies = len(results)
        stocks_by_strategy = {
            name: len(signals) if isinstance(signals, list) else 0
            for name, signals in results.items()
        }
        multi_strategy_count = sum(
            len(stocks) for count, stocks in by_count.items() if count > 1
        )
        intersection_rate = (
            (multi_strategy_count / len(stock_strategies))
            if stock_strategies
            else 0
        )

        return {
            "total": len(stock_strategies),
            "by_count": by_count,
            "intersection_stats": {
                "total_strategies": total_strategies,
                "stocks_by_strategy": stocks_by_strategy,
                "intersection_rate": round(intersection_rate, 2),
            },
        }
    except Exception as e:
        logger.error(f"交集分析失败: {str(e)}")
        logger.error(f"错误堆栈: {traceback.format_exc()}")
        return {
            "total": 0,
            "by_count": {},
            "intersection_stats": {
                "total_strategies": 0,
                "stocks_by_strategy": {},
                "intersection_rate": 0,
            },
        }


@signals_bp.route("/api/select", methods=["GET", "POST"])
def run_selection() -> Any:
    """执行选股"""
    try:
        request_start_time = dt.now()
        logger.info("=" * 60)
        logger.info("选股请求开始")

        # 检查参数是否被修改
        param_lock = get_param_lock()
        param_tracker = get_param_tracker()

        is_modified, restored_params = param_lock.check_and_restore()
        if is_modified:
            logger.warning("⚠️  检测到参数被修改，已自动恢复")

        is_changed, changes = param_tracker.check_changes()
        if is_changed:
            logger.warning("⚠️  检测到参数变化")

        strategies_to_run = None
        logic = "or"
        end_date = None

        # 解析请求参数
        if request.method == "POST":
            data = request.get_json(silent=True) or {}
            strategies_to_run = data.get("strategies")
            logic = data.get("logic", "or").lower()
            end_date = data.get("end_date")
        else:
            strategies_param = request.args.get("strategies")
            if strategies_param:
                strategies_to_run = [s.strip() for s in strategies_param.split(",")]
            logic = request.args.get("logic", "or").lower()
            end_date = request.args.get("end_date")

        # 获取依赖
        registry = get_registry()
        db_manager = get_db_manager()

        # 加载策略
        registry.auto_register_from_directory("strategy")

        if not registry.list_strategies():
            return jsonify({"success": False, "error": "没有可用策略"})

        # 获取所有策略名称
        all_strategy_names = registry.list_strategies()

        # 如果指定了策略，过滤
        if strategies_to_run:
            invalid = [s for s in strategies_to_run if s not in all_strategy_names]
            if invalid:
                return jsonify(
                    {
                        "success": False,
                        "error": f"未知策略: {', '.join(invalid)}",
                    }
                )
            all_strategy_names = strategies_to_run

        logger.info(f"选中策略列表: {all_strategy_names}")

        # 加载股票数据
        from utils.global_db import get_stock_repo as _get_stock_repo

        stock_repo = _get_stock_repo()
        stock_codes = stock_repo.list_all_stocks()

        if not stock_codes:
            return jsonify({"success": False, "error": "没有股票数据"})

        # 加载股票名称
        stock_names: dict = {}
        try:
            stock_names = stock_repo.get_all_stock_names()
        except Exception:
            pass

        if not stock_names:
            stock_names = {code: f"股票{code}" for code in stock_codes}

        # 流式选股
        import gc

        results: dict = {}
        all_signals: dict = {}

        for strategy_name in all_strategy_names:
            strategy = registry.get_strategy(strategy_name)
            if not strategy:
                continue

            logger.info(f"开始执行策略: {strategy_name}")
            signals = []
            error_count = 0
            success_count = 0
            strategy_start_time = dt.now()

            total_stocks = len(stock_codes)
            for idx, code in enumerate(stock_codes, 1):
                try:
                    df = stock_repo.read_stock(code)
                    if df.empty or len(df) < 60:
                        continue

                    name = stock_names.get(code, "未知")
                    result = strategy.analyze_stock(code, name, df)
                    if result:
                        success_count += 1
                        signals.append(
                            {
                                "code": result["code"],
                                "name": result.get("name", name),
                                "signals": result["signals"],
                            }
                        )
                except Exception as e:
                    error_count += 1
                    if error_count <= 5:
                        logger.warning(
                            f"策略 {strategy_name} 分析股票 {code} 失败: {str(e)}"
                        )

                if idx % 500 == 0:
                    logger.info(
                        f"  策略 {strategy_name} 进度: [{idx}/{total_stocks}] - 选中 {len(signals)} 只"
                    )

            strategy_time = (dt.now() - strategy_start_time).total_seconds()
            logger.info(
                f"策略 {strategy_name} 执行完成: 选中 {len(signals)} 只，耗时 {strategy_time:.1f}秒"
            )

            results[strategy_name] = signals

            # 计算交集
            if logic == "and":
                if not all_signals:
                    all_signals = {s["code"]: s for s in signals}
                else:
                    all_signals = {
                        code: s
                        for code, s in all_signals.items()
                        if any(sig["code"] == code for sig in signals)
                    }

            del signals
            gc.collect()

        # 构建响应
        total_time = (dt.now() - request_start_time).total_seconds()

        if logic == "and":
            final_signals = list(all_signals.values())
        else:
            final_signals = []
            seen_codes: set = set()
            for strategy_name, signals in results.items():
                for signal in signals:
                    if signal["code"] not in seen_codes:
                        seen_codes.add(signal["code"])
                        final_signals.append(signal)

        intersection = _analyze_intersection(results)

        logger.info(f"选股完成，总耗时: {total_time:.1f}秒")

        return jsonify(
            {
                "success": True,
                "data": {
                    "signals": final_signals,
                    "total": len(final_signals),
                    "strategies": all_strategy_names,
                    "logic": logic,
                    "intersection": intersection,
                    "elapsed_time": round(total_time, 2),
                },
            }
        )
    except Exception as e:
        logger.error(f"选股失败: {str(e)}")
        logger.error(traceback.format_exc())
        return jsonify({"success": False, "error": str(e)})


@signals_bp.route("/api/save_selection", methods=["POST"])
def save_selection() -> Any:
    """保存选股结果"""
    try:
        data = request.get_json(silent=True) or {}
        selection_record_manager = get_selection_record_manager()

        records = data.get("records", [])
        if not records:
            return jsonify({"success": False, "error": "没有记录可保存"})

        from datetime import datetime as dt

        strategy_names = data.get("strategy_names", [])
        selection_time = dt.now()
        end_date = data.get("end_date") or ""

        result = selection_record_manager.save_selection_result(
            strategy_names, records, selection_time, end_date
        )

        return jsonify(
            {"success": True, "message": f"保存成功", "data": result}
        )
    except Exception as e:
        logger.error(f"保存选股结果失败: {str(e)}")
        return jsonify({"success": False, "error": str(e)})


@signals_bp.route("/api/selection-history", methods=["GET"])
def get_selection_history() -> Any:
    """获取选股历史"""
    try:
        db_manager = get_db_manager()
        page = int(request.args.get("page", 1))
        per_page = int(request.args.get("per_page", 20))
        date = request.args.get("date")

        offset = (page - 1) * per_page

        if date:
            rows = db_manager.query(
                """
                SELECT DISTINCT selection_date
                FROM stock_selection_record
                WHERE selection_date = ?
                ORDER BY selection_date DESC
                LIMIT ? OFFSET ?
                """,
                (date, per_page, offset),
            )
            count_result = db_manager.query(
                "SELECT COUNT(DISTINCT selection_date) as count FROM stock_selection_record WHERE selection_date = ?",
                (date,),
            )
        else:
            rows = db_manager.query(
                """
                SELECT DISTINCT selection_date
                FROM stock_selection_record
                ORDER BY selection_date DESC
                LIMIT ? OFFSET ?
                """,
                (per_page, offset),
            )
            count_result = db_manager.query(
                "SELECT COUNT(DISTINCT selection_date) as count FROM stock_selection_record"
            )

        total = count_result[0]["count"] if count_result else 0
        dates = [row["selection_date"] for row in rows]

        return jsonify(
            {
                "success": True,
                "data": {
                    "dates": dates,
                    "total": total,
                    "page": page,
                    "per_page": per_page,
                },
            }
        )
    except Exception as e:
        logger.error(f"获取选股历史失败: {str(e)}")
        return jsonify({"success": False, "error": str(e)})
