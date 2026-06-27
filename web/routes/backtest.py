"""
回测路由 - /api/trading/backtest/*
从 trading/routes.py 拆分
"""
from typing import Any
from flask import Blueprint, request, jsonify
from web.deps import get_db_manager, get_akshare_fetcher
from utils.log_config import get_logger

backtest_bp = Blueprint("backtest", __name__, url_prefix="/api/trading")
logger = get_logger(__name__)


def _get_backtest_dao() -> Any:
    """获取回测DAO（延迟初始化）"""
    from trading.backtest_dao import BacktestDAO

    return BacktestDAO()


def _get_backtest_engine() -> Any:
    """获取回测引擎（延迟初始化）"""
    from trading.backtest_engine import BacktestEngine

    return BacktestEngine()


def _get_batch_queue(batch_id: str) -> Any:
    """获取批量队列（延迟初始化）"""
    from trading.backtest_batch_queue import BacktestBatchQueue

    return BacktestBatchQueue(batch_id)


# ==================== 回测配置接口 ====================


@backtest_bp.route("/backtest/configs", methods=["GET"])
def get_backtest_configs() -> Any:
    """获取回测配置列表"""
    try:
        backtest_dao = _get_backtest_dao()
        configs = backtest_dao.get_all_configs()

        return jsonify(
            {
                "success": True,
                "data": {
                    "configs": configs,
                    "total_count": len(configs),
                },
            }
        )
    except Exception as e:
        logger.error(f"获取回测配置列表失败: {str(e)}")
        return jsonify({"success": False, "error": str(e)})


@backtest_bp.route("/backtest/configs", methods=["POST"])
def create_backtest_config() -> Any:
    """创建回测配置"""
    try:
        data = request.get_json(silent=True) or {}
        backtest_dao = _get_backtest_dao()

        config_id = backtest_dao.create_config(data)

        return jsonify(
            {
                "success": True,
                "data": {"config_id": config_id},
                "message": "配置创建成功",
            }
        )
    except Exception as e:
        logger.error(f"创建回测配置失败: {str(e)}")
        return jsonify({"success": False, "error": str(e)})


@backtest_bp.route("/backtest/configs/<int:config_id>", methods=["GET"])
def get_backtest_config(config_id: int) -> Any:
    """获取单个回测配置"""
    try:
        backtest_dao = _get_backtest_dao()
        config = backtest_dao.get_config(config_id)

        if config:
            return jsonify({"success": True, "data": config})
        else:
            return jsonify({"success": False, "error": "配置不存在"})
    except Exception as e:
        logger.error(f"获取回测配置失败: {str(e)}")
        return jsonify({"success": False, "error": str(e)})


@backtest_bp.route("/backtest/configs/<int:config_id>", methods=["PUT"])
def update_backtest_config(config_id: int) -> Any:
    """更新回测配置"""
    try:
        data = request.get_json(silent=True) or {}
        backtest_dao = _get_backtest_dao()

        backtest_dao.update_config(config_id, data)

        return jsonify({"success": True, "message": "配置更新成功"})
    except Exception as e:
        logger.error(f"更新回测配置失败: {str(e)}")
        return jsonify({"success": False, "error": str(e)})


@backtest_bp.route("/backtest/configs/<int:config_id>", methods=["DELETE"])
def delete_backtest_config(config_id: int) -> Any:
    """删除回测配置"""
    try:
        backtest_dao = _get_backtest_dao()
        backtest_dao.delete_config(config_id)

        return jsonify({"success": True, "message": "配置删除成功"})
    except Exception as e:
        logger.error(f"删除回测配置失败: {str(e)}")
        return jsonify({"success": False, "error": str(e)})


# ==================== 回测执行接口 ====================


@backtest_bp.route("/backtest/run", methods=["POST"])
def run_backtest() -> Any:
    """运行回测"""
    try:
        data = request.get_json(silent=True) or {}

        config_id = data.get("config_id")
        if not config_id:
            return jsonify({"success": False, "error": "配置ID不能为空"})

        backtest_dao = _get_backtest_dao()
        config = backtest_dao.get_config(config_id)

        if not config:
            return jsonify({"success": False, "error": "配置不存在"})

        # 启动回测任务
        import threading

        backtest_engine = _get_backtest_engine()

        def run_backtest_task() -> None:
            try:
                result = backtest_engine.run(config)
                # 保存结果
                backtest_dao.save_result(config_id, result)
            except Exception as e:
                logger.error(f"回测执行失败: {str(e)}")

        thread = threading.Thread(target=run_backtest_task)
        thread.daemon = True
        thread.start()

        return jsonify({"success": True, "message": "回测任务已启动"})
    except Exception as e:
        logger.error(f"启动回测失败: {str(e)}")
        return jsonify({"success": False, "error": str(e)})


@backtest_bp.route("/backtest/results", methods=["GET"])
def get_backtest_results() -> Any:
    """获取回测结果列表"""
    try:
        backtest_dao = _get_backtest_dao()
        page = int(request.args.get("page", 1))
        per_page = int(request.args.get("per_page", 20))

        results = backtest_dao.get_results(page=page, per_page=per_page)

        return jsonify({"success": True, "data": results})
    except Exception as e:
        logger.error(f"获取回测结果失败: {str(e)}")
        return jsonify({"success": False, "error": str(e)})


@backtest_bp.route("/backtest/results/<int:result_id>", methods=["GET"])
def get_backtest_result(result_id: int) -> Any:
    """获取单个回测结果"""
    try:
        backtest_dao = _get_backtest_dao()
        result = backtest_dao.get_result(result_id)

        if result:
            return jsonify({"success": True, "data": result})
        else:
            return jsonify({"success": False, "error": "结果不存在"})
    except Exception as e:
        logger.error(f"获取回测结果失败: {str(e)}")
        return jsonify({"success": False, "error": str(e)})


@backtest_bp.route("/backtest/results/<int:result_id>", methods=["DELETE"])
def delete_backtest_result(result_id: int) -> Any:
    """删除回测结果"""
    try:
        backtest_dao = _get_backtest_dao()
        backtest_dao.delete_result(result_id)

        return jsonify({"success": True, "message": "结果删除成功"})
    except Exception as e:
        logger.error(f"删除回测结果失败: {str(e)}")
        return jsonify({"success": False, "error": str(e)})


@backtest_bp.route("/backtest/results/<int:result_id>/trades", methods=["GET"])
def get_backtest_trades(result_id: int) -> Any:
    """获取回测交易记录"""
    try:
        backtest_dao = _get_backtest_dao()
        trades = backtest_dao.get_trades(result_id)

        return jsonify({"success": True, "data": trades})
    except Exception as e:
        logger.error(f"获取交易记录失败: {str(e)}")
        return jsonify({"success": False, "error": str(e)})


@backtest_bp.route("/backtest/results/<int:result_id>/export", methods=["GET"])
def export_backtest_result(result_id: int) -> Any:
    """导出回测结果"""
    try:
        backtest_dao = _get_backtest_dao()
        result = backtest_dao.get_result(result_id)

        if not result:
            return jsonify({"success": False, "error": "结果不存在"})

        # 生成CSV文件
        import csv
        import tempfile
        import os

        temp_dir = tempfile.gettempdir()
        file_path = os.path.join(temp_dir, f"backtest_{result_id}.csv")

        with open(file_path, "w", newline="", encoding="utf-8-sig") as f:
            writer = csv.writer(f)
            writer.writerow(["日期", "操作", "股票代码", "股票名称", "价格", "数量", "金额"])
            # TODO: 写入交易记录

        return jsonify(
            {
                "success": True,
                "data": {"file_path": file_path},
            }
        )
    except Exception as e:
        logger.error(f"导出回测结果失败: {str(e)}")
        return jsonify({"success": False, "error": str(e)})


# ==================== 批量回测接口 ====================


@backtest_bp.route("/backtest/batch/submit", methods=["POST"])
def submit_batch_backtest() -> Any:
    """提交批量回测任务"""
    try:
        data = request.get_json(silent=True) or {}
        tasks = data.get("tasks", [])
        config = data.get("config", {})

        if not tasks:
            return jsonify({"success": False, "error": "任务列表为空"})

        from trading.backtest_batch_queue import BacktestBatchQueue

        batch = BacktestBatchQueue.create_batch(tasks, config)

        logger.info(f"提交批量回测任务: {batch._data.get('batch_id')}, 任务数: {len(tasks)}")

        return jsonify(
            {
                "success": True,
                "data": {
                    "batch_id": batch._data.get("batch_id"),
                    "total_tasks": len(tasks),
                },
            }
        )
    except Exception as e:
        logger.error(f"提交批量回测任务失败: {str(e)}")
        return jsonify({"success": False, "error": str(e)})


@backtest_bp.route("/backtest/batch/start", methods=["POST"])
def start_batch_backtest() -> Any:
    """启动批量回测"""
    try:
        data = request.get_json(silent=True) or {}
        batch_id = data.get("batch_id")

        if not batch_id:
            return jsonify({"success": False, "error": "批次ID不能为空"})

        batch_queue = _get_batch_queue(batch_id)
        batch_queue.start()

        return jsonify({"success": True, "message": "批量回测已启动"})
    except Exception as e:
        logger.error(f"启动批量回测失败: {str(e)}")
        return jsonify({"success": False, "error": str(e)})


@backtest_bp.route("/backtest/batch/status", methods=["GET"])
def get_batch_status() -> Any:
    """获取批量回测状态"""
    try:
        batch_id = request.args.get("batch_id")

        if not batch_id:
            return jsonify({"success": False, "error": "批次ID不能为空"})

        batch_queue = _get_batch_queue(batch_id)
        status = batch_queue.get_status()

        return jsonify({"success": True, "data": status})
    except Exception as e:
        logger.error(f"获取批量状态失败: {str(e)}")
        return jsonify({"success": False, "error": str(e)})


@backtest_bp.route("/backtest/batch/results", methods=["GET"])
def get_batch_results() -> Any:
    """获取批量回测结果"""
    try:
        batch_id = request.args.get("batch_id")

        if not batch_id:
            return jsonify({"success": False, "error": "批次ID不能为空"})

        batch_queue = _get_batch_queue(batch_id)
        results = batch_queue.get_results()

        return jsonify({"success": True, "data": results})
    except Exception as e:
        logger.error(f"获取批量结果失败: {str(e)}")
        return jsonify({"success": False, "error": str(e)})


@backtest_bp.route("/backtest/batch/cancel", methods=["POST"])
def cancel_batch() -> Any:
    """取消批量回测"""
    try:
        data = request.get_json(silent=True) or {}
        batch_id = data.get("batch_id")

        if not batch_id:
            return jsonify({"success": False, "error": "批次ID不能为空"})

        batch_queue = _get_batch_queue(batch_id)
        batch_queue.stop()

        return jsonify({"success": True, "message": "批量回测已取消"})
    except Exception as e:
        logger.error(f"取消批量回测失败: {str(e)}")
        return jsonify({"success": False, "error": str(e)})


@backtest_bp.route("/backtest/batch/list", methods=["GET"])
def list_batches() -> Any:
    """获取批量回测列表"""
    try:
        batch_queue = _get_batch_queue("list")
        batches = batch_queue.status()

        return jsonify({"success": True, "data": batches})
    except Exception as e:
        logger.error(f"获取批量列表失败: {str(e)}")
        return jsonify({"success": False, "error": str(e)})


@backtest_bp.route("/backtest/strategies", methods=["GET"])
def get_backtest_strategies() -> Any:
    """获取回测可用策略"""
    try:
        from utils.strategy_name_mapper import STRATEGY_NAME_MAP

        strategies = [
            {"name": k, "display_name": v} for k, v in STRATEGY_NAME_MAP.items()
        ]

        return jsonify({"success": True, "data": strategies})
    except Exception as e:
        logger.error(f"获取回测策略失败: {str(e)}")
        return jsonify({"success": False, "error": str(e)})
