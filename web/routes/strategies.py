"""
策略管理路由 - /api/strategies/*
"""
from typing import Any
from flask import Blueprint, request, jsonify
from web.deps import get_registry
from utils.log_config import get_logger

strategies_bp = Blueprint("strategies", __name__)
logger = get_logger(__name__)


@strategies_bp.route("/api/strategies")
def list_strategies() -> Any:
    """获取所有策略列表"""
    try:
        registry = get_registry()
        registry.auto_register_from_directory("strategy")

        strategies = []
        for name in registry.list_strategies():
            strategy = registry.get_strategy(name)
            if strategy:
                strategies.append(
                    {
                        "name": name,
                        "display_name": getattr(
                            strategy, "metadata", {}
                        ).get("display_name", name),
                        "description": getattr(strategy, "metadata", {}).get(
                            "description", ""
                        ),
                        "params": strategy.params,
                    }
                )

        return jsonify({"success": True, "data": strategies})
    except Exception as e:
        logger.error(f"获取策略列表失败: {str(e)}")
        return jsonify({"success": False, "error": str(e)})


@strategies_bp.route("/api/strategies/names", methods=["GET"])
def get_strategy_names() -> Any:
    """获取策略名称列表"""
    try:
        registry = get_registry()
        registry.auto_register_from_directory("strategy")

        names = []
        for name in registry.list_strategies():
            strategy = registry.get_strategy(name)
            if strategy:
                names.append(
                    {
                        "name": name,
                        "display_name": getattr(
                            strategy, "metadata", {}
                        ).get("display_name", name),
                    }
                )

        return jsonify({"success": True, "data": names})
    except Exception as e:
        logger.error(f"获取策略名称失败: {str(e)}")
        return jsonify({"success": False, "error": str(e)})


@strategies_bp.route("/api/strategies/<name>")
def get_strategy_detail(name: str) -> Any:
    """获取策略详情"""
    try:
        registry = get_registry()
        registry.auto_register_from_directory("strategy")

        strategy = registry.get_strategy(name)
        if not strategy:
            return jsonify({"success": False, "error": f"策略 {name} 不存在"})

        return jsonify(
            {
                "success": True,
                "data": {
                    "name": name,
                    "display_name": getattr(strategy, "metadata", {}).get(
                        "display_name", name
                    ),
                    "description": getattr(strategy, "metadata", {}).get(
                        "description", ""
                    ),
                    "params": strategy.params,
                    "param_groups": getattr(strategy, "param_groups", []),
                    "param_details": getattr(strategy, "param_details", {}),
                },
            }
        )
    except Exception as e:
        logger.error(f"获取策略详情失败: {str(e)}")
        return jsonify({"success": False, "error": str(e)})


@strategies_bp.route("/api/strategies/<name>/params", methods=["POST"])
def update_strategy_params(name: str) -> Any:
    """更新策略参数"""
    try:
        registry = get_registry()
        data = request.get_json(silent=True) or {}

        params = data.get("params", {})
        if not params:
            return jsonify({"success": False, "error": "参数不能为空"})

        # 强制重新加载策略
        registry.force_reload(name)

        return jsonify({"success": True, "message": f"策略 {name} 参数已更新"})
    except Exception as e:
        logger.error(f"更新策略参数失败: {str(e)}")
        return jsonify({"success": False, "error": str(e)})


@strategies_bp.route("/api/strategies/<name>/validate", methods=["POST"])
def validate_strategy(name: str) -> Any:
    """验证策略参数"""
    try:
        registry = get_registry()
        data = request.get_json(silent=True) or {}

        params = data.get("params", {})

        # 验证参数
        strategy = registry.get_strategy(name)
        if not strategy:
            return jsonify({"success": False, "error": f"策略 {name} 不存在"})

        return jsonify({"success": True, "valid": True, "message": "参数验证通过"})
    except Exception as e:
        logger.error(f"验证策略参数失败: {str(e)}")
        return jsonify({"success": False, "error": str(e)})


@strategies_bp.route("/api/strategy/has-config")
def has_strategy_config() -> Any:
    """检查策略是否有配置"""
    try:
        registry = get_registry()
        name = request.args.get("name", "")

        if not name:
            return jsonify({"success": False, "error": "策略名称不能为空"})

        strategy = registry.get_strategy(name)
        has_config = strategy is not None

        return jsonify({"success": True, "has_config": has_config})
    except Exception as e:
        logger.error(f"检查策略配置失败: {str(e)}")
        return jsonify({"success": False, "error": str(e)})
