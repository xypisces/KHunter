#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
策略名称映射工具

将策略的英文类名转换为中文名称，反之亦然。
唯一真相源：config/strategy_params.yaml 的 display_name 字段。
"""

import yaml
from pathlib import Path

# 配置文件路径
_PARAMS_FILE = Path(__file__).parent.parent / "config" / "strategy_params.yaml"
_MAPPING_FILE = Path(__file__).parent.parent / "config" / "strategy_name_mapping.yaml"

# 缓存映射表
_STRATEGY_NAME_MAP: dict[str, str] | None = None
_STRATEGY_NAME_REVERSE_MAP: dict[str, str] | None = None


def _load_mapping_from_params() -> tuple[dict[str, str], dict[str, str]]:
    """
    从 strategy_params.yaml 的 display_name 自动提取映射。

    Returns:
        tuple: (正向映射表: 英文类名→中文名称, 反向映射表: 中文名称→英文类名)
    """
    try:
        if _PARAMS_FILE.exists():
            with open(_PARAMS_FILE, "r", encoding="utf-8") as f:
                config = yaml.safe_load(f) or {}

            strategies = config.get("strategies", {})
            mapping: dict[str, str] = {}
            for class_name, cfg in strategies.items():
                display_name = cfg.get("display_name") if isinstance(cfg, dict) else None
                if display_name:
                    mapping[class_name] = display_name

            if mapping:
                reverse_mapping = {v: k for k, v in mapping.items()}
                return mapping, reverse_mapping
    except Exception as e:
        print(f"警告: 无法从 strategy_params.yaml 加载策略名称映射: {e}")

    # 降级：尝试从 strategy_name_mapping.yaml 加载
    return _load_mapping_from_mapping_file()


def _load_mapping_from_mapping_file() -> tuple[dict[str, str], dict[str, str]]:
    """
    降级方案：从 strategy_name_mapping.yaml 加载映射。

    Returns:
        tuple: (正向映射表, 反向映射表)
    """
    try:
        if _MAPPING_FILE.exists():
            with open(_MAPPING_FILE, "r", encoding="utf-8") as f:
                config = yaml.safe_load(f) or {}

            strategy_names = config.get("strategy_names", {})
            if strategy_names:
                reverse_mapping = {v: k for k, v in strategy_names.items()}
                return strategy_names, reverse_mapping
    except Exception as e:
        print(f"警告: 无法从 strategy_name_mapping.yaml 加载策略名称映射: {e}")

    return {}, {}


def _get_strategy_name_map() -> dict[str, str]:
    """获取策略名称映射表（正向：英文类名→中文名称）"""
    global _STRATEGY_NAME_MAP
    if _STRATEGY_NAME_MAP is None:
        _STRATEGY_NAME_MAP, _ = _load_mapping_from_params()
    return _STRATEGY_NAME_MAP


def _get_strategy_name_reverse_map() -> dict[str, str]:
    """获取策略名称映射表（反向：中文名称→英文类名）"""
    global _STRATEGY_NAME_REVERSE_MAP
    if _STRATEGY_NAME_REVERSE_MAP is None:
        _, _STRATEGY_NAME_REVERSE_MAP = _load_mapping_from_params()
    return _STRATEGY_NAME_REVERSE_MAP


# 初始化映射表
STRATEGY_NAME_MAP = _get_strategy_name_map()
STRATEGY_NAME_REVERSE_MAP = _get_strategy_name_reverse_map()


def get_chinese_name(english_name: str) -> str:
    """
    将英文策略名称转换为中文名称
    
    Args:
        english_name: 英文策略名称（类名）
        
    Returns:
        中文策略名称，如果不存在则返回原名称
    """
    return STRATEGY_NAME_MAP.get(english_name, english_name)


def get_english_name(chinese_name: str) -> str:
    """
    将中文策略名称转换为英文名称
    
    Args:
        chinese_name: 中文策略名称
        
    Returns:
        英文策略名称（类名），如果不存在则返回原名称
    """
    return STRATEGY_NAME_REVERSE_MAP.get(chinese_name, chinese_name)


def is_english_name(name: str) -> bool:
    """
    判断是否为英文策略名称
    
    Args:
        name: 策略名称
        
    Returns:
        True 如果是英文名称，False 如果是中文名称
    """
    return name in STRATEGY_NAME_MAP


def is_chinese_name(name: str) -> bool:
    """
    判断是否为中文策略名称
    
    Args:
        name: 策略名称
        
    Returns:
        True 如果是中文名称，False 如果是英文名称
    """
    return name in STRATEGY_NAME_REVERSE_MAP


def reload_mapping():
    """
    重新加载策略名称映射（用于配置文件更新后）
    """
    global _STRATEGY_NAME_MAP, _STRATEGY_NAME_REVERSE_MAP
    _STRATEGY_NAME_MAP = None
    _STRATEGY_NAME_REVERSE_MAP = None
    
    # 重新初始化
    globals()['STRATEGY_NAME_MAP'] = _get_strategy_name_map()
    globals()['STRATEGY_NAME_REVERSE_MAP'] = _get_strategy_name_reverse_map()
