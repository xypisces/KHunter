"""
信号存储模块 - 管理信号的持久化
"""
import json
from pathlib import Path
from typing import Dict, List, Optional, Any
import logging

logger = logging.getLogger(__name__)


class SignalStore:
    """信号存储管理器"""

    def __init__(self, running_dir: Path):
        """
        初始化信号存储管理器

        :param running_dir: 运行目录路径
        """
        self.running_dir = running_dir
        self.running_dir.mkdir(exist_ok=True)

    def load_signals(self) -> List[Dict]:
        """
        加载信号列表

        :return: 信号列表
        """
        try:
            signals_file = self.running_dir / "signals.json"
            if signals_file.exists():
                with open(signals_file, "r", encoding="utf-8") as f:
                    signals = json.load(f)
                    logger.info(f"加载信号列表: {len(signals)} 条")
                    return signals
            return []
        except Exception as e:
            logger.warning(f"加载信号列表失败: {str(e)}")
            return []

    def save_signals(self, signals: List[Dict]) -> bool:
        """
        保存信号列表

        :param signals: 信号列表
        :return: 是否成功
        """
        try:
            signals_file = self.running_dir / "signals.json"
            with open(signals_file, "w", encoding="utf-8") as f:
                json.dump(signals, f, ensure_ascii=False, indent=2)
            logger.info(f"保存信号列表: {len(signals)} 条")
            return True
        except Exception as e:
            logger.error(f"保存信号列表失败: {str(e)}")
            return False

    def add_signal(self, signal: Dict) -> bool:
        """
        添加信号

        :param signal: 信号数据
        :return: 是否成功
        """
        try:
            signals = self.load_signals()
            signals.append(signal)
            return self.save_signals(signals)
        except Exception as e:
            logger.error(f"添加信号失败: {str(e)}")
            return False

    def remove_signal(self, stock_code: str) -> bool:
        """
        移除信号

        :param stock_code: 股票代码
        :return: 是否成功
        """
        try:
            signals = self.load_signals()
            signals = [s for s in signals if s.get("code") != stock_code]
            return self.save_signals(signals)
        except Exception as e:
            logger.error(f"移除信号失败: {str(e)}")
            return False

    def get_pending_signals(self) -> List[Dict]:
        """
        获取待执行信号

        :return: 待执行信号列表
        """
        signals = self.load_signals()
        return [s for s in signals if s.get("status") == "pending"]

    def update_signal_status(self, stock_code: str, status: str, reason: str = "") -> bool:
        """
        更新信号状态

        :param stock_code: 股票代码
        :param status: 新状态
        :param reason: 原因
        :return: 是否成功
        """
        try:
            signals = self.load_signals()
            for signal in signals:
                if signal.get("code") == stock_code:
                    signal["status"] = status
                    signal["updated_at"] = (
                        __import__("datetime").datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                    )
                    if reason:
                        signal["reason"] = reason
            return self.save_signals(signals)
        except Exception as e:
            logger.error(f"更新信号状态失败: {str(e)}")
            return False
