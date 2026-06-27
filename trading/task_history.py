"""
任务历史模块 - 管理任务记录和日报生成
"""
import json
import datetime
from pathlib import Path
from typing import Dict, List, Optional, Any
import logging

logger = logging.getLogger(__name__)


class TaskHistory:
    """任务历史管理器"""

    def __init__(self, running_dir: Path):
        """
        初始化任务历史管理器

        :param running_dir: 运行目录路径
        """
        self.running_dir = running_dir
        self.running_dir.mkdir(exist_ok=True)

    def load_task_history(self) -> List[Dict]:
        """加载任务历史记录"""
        try:
            history_file = self.running_dir / "task_history.json"
            if history_file.exists():
                with open(history_file, "r", encoding="utf-8") as f:
                    history = json.load(f)
                    logger.info(f"加载任务历史记录: {len(history)} 条")
                    return history
            return []
        except Exception as e:
            logger.warning(f"加载任务历史记录失败: {str(e)}")
            return []

    def save_task_history(self, history: List[Dict]) -> None:
        """保存任务历史记录"""
        try:
            history_file = self.running_dir / "task_history.json"
            with open(history_file, "w", encoding="utf-8") as f:
                json.dump(history, f, ensure_ascii=False, indent=2)
            logger.info(f"保存任务历史记录: {len(history)} 条")
        except Exception as e:
            logger.error(f"保存任务历史记录失败: {str(e)}")

    def save_task_record(self, task_config: Dict) -> Dict:
        """
        保存任务运行记录

        :param task_config: 任务配置
        :return: 操作结果
        """
        try:
            record = {
                "id": datetime.datetime.now().strftime("%Y%m%d_%H%M%S"),
                "timestamp": datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                "strategies": task_config.get("strategies", []),
                "timing_strategy": task_config.get("timing_strategy", "support"),
                "initial_capital": task_config.get("initial_capital", 300000),
                "mode": task_config.get("mode", "realtime"),
                "status": "completed",
            }

            history = self.load_task_history()
            history.append(record)

            # 只保留最近 100 条记录
            if len(history) > 100:
                history = history[-100:]

            self.save_task_history(history)

            return {"success": True, "record": record}
        except Exception as e:
            logger.error(f"保存任务记录失败: {str(e)}")
            return {"success": False, "error": str(e)}

    def get_task_history(self) -> List[Dict]:
        """获取任务历史列表"""
        return self.load_task_history()

    def get_last_task(self) -> Optional[Dict]:
        """获取最后一个任务"""
        history = self.load_task_history()
        return history[-1] if history else None

    def save_daily_record(self, record: Dict) -> bool:
        """
        保存每日记录

        :param record: 每日记录
        :return: 是否成功
        """
        try:
            date_str = record.get("date", datetime.datetime.now().strftime("%Y-%m-%d"))
            record_file = self.running_dir / f"daily_record_{date_str}.json"
            with open(record_file, "w", encoding="utf-8") as f:
                json.dump(record, f, ensure_ascii=False, indent=2)
            logger.info(f"保存每日记录: {date_str}")
            return True
        except Exception as e:
            logger.error(f"保存每日记录失败: {str(e)}")
            return False

    def generate_daily_report(self, portfolio: Dict, signals: List[Dict], config: Dict) -> Dict:
        """
        生成每日报告

        :param portfolio: 持仓信息
        :param signals: 信号列表
        :param config: 配置信息
        :return: 每日报告
        """
        try:
            # 计算持仓统计
            total_positions = len(portfolio)
            total_value = sum(
                pos.get("market_value", 0) for pos in portfolio.values()
            )

            # 计算信号统计
            total_signals = len(signals)
            buy_signals = sum(1 for s in signals if s.get("signal") == "buy")
            sell_signals = sum(1 for s in signals if s.get("signal") == "sell")

            report = {
                "date": datetime.datetime.now().strftime("%Y-%m-%d"),
                "timestamp": datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                "portfolio": {
                    "total_positions": total_positions,
                    "total_value": round(total_value, 2),
                },
                "signals": {
                    "total": total_signals,
                    "buy": buy_signals,
                    "sell": sell_signals,
                },
                "config": {
                    "initial_capital": config.get("initial_capital", 300000),
                    "take_profit_threshold": config.get("take_profit_threshold", 0.21),
                    "stop_loss_threshold": config.get("stop_loss_threshold", -0.05),
                },
            }

            # 保存报告
            report_file = (
                self.running_dir
                / f"daily_report_{report['date']}.json"
            )
            with open(report_file, "w", encoding="utf-8") as f:
                json.dump(report, f, ensure_ascii=False, indent=2)

            logger.info(f"生成每日报告: {report['date']}")
            return report
        except Exception as e:
            logger.error(f"生成每日报告失败: {str(e)}")
            return {}
