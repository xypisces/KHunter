"""应用主配置管理器 — 统一 config/config.yaml 的加载、读取、写回。

用法::

    from utils.app_config import get_app_config

    config = get_app_config()
    value = config.get("dingtalk.webhook_url")
    config.set("schedule.time", "18:00")
"""

from __future__ import annotations

import logging
import os
import tempfile
import threading
from pathlib import Path
from typing import Any, Optional

import yaml

logger = logging.getLogger(__name__)

# 项目根目录（utils/ 的父目录）
_PROJECT_ROOT = Path(__file__).parent.parent
_CONFIG_PATH = _PROJECT_ROOT / "config" / "config.yaml"


class AppConfig:
    """应用主配置（config/config.yaml）。

    线程安全，支持原子写回。
    """

    def __init__(self, config_path: Optional[Path] = None) -> None:
        self._path = config_path or _CONFIG_PATH
        self._lock = threading.Lock()
        self._data: dict[str, Any] = {}
        self._load()

    # ── 读取 ──────────────────────────────────────────────

    def get(self, key: str, default: Any = None) -> Any:
        """读取配置项。支持点号分隔的嵌套键（如 ``'dingtalk.webhook_url'``）。"""
        parts = key.split(".")
        node: Any = self._data
        for part in parts:
            if isinstance(node, dict) and part in node:
                node = node[part]
            else:
                return default
        return node

    def get_all(self) -> dict[str, Any]:
        """返回完整配置 dict 的副本。"""
        with self._lock:
            return dict(self._data)

    # ── 写入 ──────────────────────────────────────────────

    def set(self, key: str, value: Any) -> None:
        """设置配置项并原子写回磁盘。支持点号分隔的嵌套键。"""
        with self._lock:
            parts = key.split(".")
            node = self._data
            for part in parts[:-1]:
                if part not in node or not isinstance(node[part], dict):
                    node[part] = {}
                node = node[part]
            node[parts[-1]] = value
            self._save()

    def update(self, data: dict[str, Any]) -> None:
        """批量更新配置并原子写回磁盘（浅合并顶层 key）。"""
        with self._lock:
            self._data.update(data)
            self._save()

    # ── 重新加载 ──────────────────────────────────────────

    def reload(self) -> None:
        """从磁盘重新加载配置。"""
        with self._lock:
            self._load()

    # ── 内部方法 ──────────────────────────────────────────

    def _load(self) -> None:
        """从磁盘加载配置文件（调用方需持有锁）。"""
        if not self._path.exists():
            logger.warning("配置文件不存在: %s，使用空配置", self._path)
            self._data = {}
            return
        try:
            with open(self._path, "r", encoding="utf-8") as f:
                data = yaml.safe_load(f)
            self._data = data if isinstance(data, dict) else {}
            logger.info("配置加载成功: %s", self._path)
        except Exception as e:
            logger.error("加载配置失败: %s，使用空配置", e)
            self._data = {}

    def _save(self) -> None:
        """原子写回配置文件（调用方需持有锁）。"""
        try:
            # 确保目录存在
            self._path.parent.mkdir(parents=True, exist_ok=True)
            # 先写临时文件，再 rename（原子操作）
            fd, tmp_path = tempfile.mkstemp(
                dir=str(self._path.parent), suffix=".tmp"
            )
            try:
                with os.fdopen(fd, "w", encoding="utf-8") as f:
                    yaml.dump(
                        self._data, f,
                        allow_unicode=True,
                        default_flow_style=False,
                    )
                os.replace(tmp_path, str(self._path))
                logger.debug("配置已写回: %s", self._path)
            except BaseException:
                # 写入失败时清理临时文件
                try:
                    os.unlink(tmp_path)
                except OSError:
                    pass
                raise
        except Exception as e:
            logger.error("写回配置失败: %s", e)


# ── 单例 ──────────────────────────────────────────────────

_instance: Optional[AppConfig] = None


def get_app_config() -> AppConfig:
    """获取 AppConfig 单例。首次调用时加载配置文件。"""
    global _instance
    if _instance is None:
        _instance = AppConfig()
    return _instance
