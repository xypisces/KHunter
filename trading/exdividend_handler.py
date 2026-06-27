"""
除权除息处理模块 - 处理股票除权除息逻辑
"""
import json
import datetime
from pathlib import Path
from typing import Dict, List, Optional, Any
import logging

logger = logging.getLogger(__name__)


class ExdividendHandler:
    """除权除息处理器"""

    def __init__(self, running_dir: Path, stock_repo: Any = None):
        """
        初始化除权除息处理器

        :param running_dir: 运行目录路径
        :param stock_repo: 股票仓库
        """
        self.running_dir = running_dir
        self.running_dir.mkdir(exist_ok=True)
        self.stock_repo = stock_repo

    def need_exdividend_check(self, stock_code: str) -> bool:
        """
        检查是否需要进行除权除息检查

        :param stock_code: 股票代码
        :return: 是否需要检查
        """
        try:
            last_date = self.load_last_exdividend_date(stock_code)
            if not last_date:
                return True

            # 如果上次检查是今天，不需要再次检查
            today = datetime.datetime.now().strftime("%Y-%m-%d")
            return last_date != today
        except Exception as e:
            logger.error(f"检查除权除息需求失败: {str(e)}")
            return False

    def load_last_exdividend_date(self, stock_code: str) -> Optional[str]:
        """
        加载上次除权除息检查日期

        :param stock_code: 股票代码
        :return: 日期字符串
        """
        try:
            date_file = self.running_dir / f"exdividend_{stock_code}.json"
            if date_file.exists():
                with open(date_file, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    return data.get("last_date")
            return None
        except Exception as e:
            logger.warning(f"加载除权除息日期失败: {str(e)}")
            return None

    def save_last_exdividend_date(self, stock_code: str, date_str: str) -> bool:
        """
        保存上次除权除息检查日期

        :param stock_code: 股票代码
        :param date_str: 日期字符串
        :return: 是否成功
        """
        try:
            date_file = self.running_dir / f"exdividend_{stock_code}.json"
            data = {
                "stock_code": stock_code,
                "last_date": date_str,
                "updated_at": datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            }
            with open(date_file, "w", encoding="utf-8") as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
            return True
        except Exception as e:
            logger.error(f"保存除权除息日期失败: {str(e)}")
            return False

    def perform_exdividend_check(self, stock_code: str, stock_name: str) -> Dict:
        """
        执行除权除息检查

        :param stock_code: 股票代码
        :param stock_name: 股票名称
        :return: 检查结果
        """
        try:
            # 从数据库获取最近的除权除息信息
            if not self.stock_repo:
                return {"has_exdividend": False, "error": "stock_repo not available"}

            # 检查是否有除权除息数据
            # 这里简化处理，实际应该查询数据库中的除权除息记录
            today = datetime.datetime.now().strftime("%Y-%m-%d")

            # 保存检查日期
            self.save_last_exdividend_date(stock_code, today)

            return {
                "stock_code": stock_code,
                "stock_name": stock_name,
                "has_exdividend": False,
                "check_date": today,
            }
        except Exception as e:
            logger.error(f"执行除权除息检查失败: {str(e)}")
            return {"has_exdividend": False, "error": str(e)}

    def check_portfolio_exdividend(self, portfolio: Dict) -> List[Dict]:
        """
        检查持仓中的除权除息

        :param portfolio: 持仓信息
        :return: 除权除息列表
        """
        exdividends = []
        for stock_code, position in portfolio.items():
            if self.need_exdividend_check(stock_code):
                result = self.perform_exdividend_check(
                    stock_code, position.get("stock_name", "")
                )
                if result.get("has_exdividend"):
                    exdividends.append(result)
        return exdividends

    def check_signals_exdividend(self, signals: List[Dict]) -> List[Dict]:
        """
        检查信号中的除权除息

        :param signals: 信号列表
        :return: 除权除息列表
        """
        exdividends = []
        for signal in signals:
            stock_code = signal.get("code")
            if stock_code and self.need_exdividend_check(stock_code):
                result = self.perform_exdividend_check(
                    stock_code, signal.get("name", "")
                )
                if result.get("has_exdividend"):
                    exdividends.append(result)
        return exdividends

    def check_pool_exdividend(self, pool: Dict) -> List[Dict]:
        """
        检查股票池中的除权除息

        :param pool: 股票池
        :return: 除权除息列表
        """
        exdividends = []
        for stock_code, stock_info in pool.items():
            if self.need_exdividend_check(stock_code):
                result = self.perform_exdividend_check(
                    stock_code, stock_info.get("name", "")
                )
                if result.get("has_exdividend"):
                    exdividends.append(result)
        return exdividends
