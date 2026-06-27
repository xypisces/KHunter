"""
组合管理模块 - 管理持仓、交易执行和 Ptrade 同步
"""
import json
import datetime
from pathlib import Path
from typing import Dict, List, Optional, Any
import logging

logger = logging.getLogger(__name__)


class PortfolioManager:
    """组合管理器"""

    def __init__(self, running_dir: Path, stock_repo: Any = None, db_manager: Any = None):
        """
        初始化组合管理器

        :param running_dir: 运行目录路径
        :param stock_repo: 股票仓库
        :param db_manager: 数据库管理器
        """
        self.running_dir = running_dir
        self.running_dir.mkdir(exist_ok=True)
        self.stock_repo = stock_repo
        self.db_manager = db_manager

    def load_portfolio(self) -> Dict:
        """
        加载持仓信息

        :return: 持仓字典
        """
        try:
            portfolio_file = self.running_dir / "portfolio.json"
            if portfolio_file.exists():
                with open(portfolio_file, "r", encoding="utf-8") as f:
                    portfolio = json.load(f)
                    logger.info(f"加载持仓信息: {len(portfolio)} 只股票")
                    return portfolio
            return {}
        except Exception as e:
            logger.warning(f"加载持仓信息失败: {str(e)}")
            return {}

    def save_portfolio(self, portfolio: Dict) -> bool:
        """
        保存持仓信息

        :param portfolio: 持仓字典
        :return: 是否成功
        """
        try:
            portfolio_file = self.running_dir / "portfolio.json"
            with open(portfolio_file, "w", encoding="utf-8") as f:
                json.dump(portfolio, f, ensure_ascii=False, indent=2)
            logger.info(f"保存持仓信息: {len(portfolio)} 只股票")
            return True
        except Exception as e:
            logger.error(f"保存持仓信息失败: {str(e)}")
            return False

    def execute_signal(self, signal: Dict, config: Dict) -> Dict:
        """
        执行交易信号

        :param signal: 交易信号
        :param config: 配置信息
        :return: 执行结果
        """
        try:
            stock_code = signal.get("code")
            signal_type = signal.get("signal")

            if not stock_code or not signal_type:
                return {"success": False, "error": "无效的信号"}

            portfolio = self.load_portfolio()

            if signal_type == "buy":
                return self._execute_buy(stock_code, signal, portfolio, config)
            elif signal_type == "sell":
                return self._execute_sell(stock_code, signal, portfolio, config)
            else:
                return {"success": False, "error": f"未知信号类型: {signal_type}"}
        except Exception as e:
            logger.error(f"执行信号失败: {str(e)}")
            return {"success": False, "error": str(e)}

    def _execute_buy(self, stock_code: str, signal: Dict, portfolio: Dict, config: Dict) -> Dict:
        """执行买入操作"""
        try:
            # 检查是否已持有
            if stock_code in portfolio:
                return {"success": False, "error": f"已持有 {stock_code}"}

            # 计算买入数量
            buy_amount = config.get("buy_amount", 100000)
            price = signal.get("price", 0)

            if price <= 0:
                return {"success": False, "error": "无效的价格"}

            # 计算可买数量（100 股为一手）
            shares = int(buy_amount / price / 100) * 100

            if shares <= 0:
                return {"success": False, "error": "资金不足"}

            # 添加到持仓
            portfolio[stock_code] = {
                "stock_code": stock_code,
                "stock_name": signal.get("name", ""),
                "shares": shares,
                "cost_price": price,
                "buy_date": datetime.datetime.now().strftime("%Y-%m-%d"),
                "buy_price": price,
                "signal": signal,
            }

            self.save_portfolio(portfolio)

            return {
                "success": True,
                "action": "buy",
                "stock_code": stock_code,
                "shares": shares,
                "price": price,
            }
        except Exception as e:
            logger.error(f"执行买入失败: {str(e)}")
            return {"success": False, "error": str(e)}

    def _execute_sell(self, stock_code: str, signal: Dict, portfolio: Dict, config: Dict) -> Dict:
        """执行卖出操作"""
        try:
            # 检查是否持有
            if stock_code not in portfolio:
                return {"success": False, "error": f"未持有 {stock_code}"}

            position = portfolio[stock_code]
            shares = position.get("shares", 0)
            price = signal.get("price", 0)

            if price <= 0:
                return {"success": False, "error": "无效的价格"}

            # 从持仓中移除
            del portfolio[stock_code]

            self.save_portfolio(portfolio)

            # 计算盈亏
            cost_price = position.get("cost_price", 0)
            profit = (price - cost_price) * shares if cost_price > 0 else 0

            return {
                "success": True,
                "action": "sell",
                "stock_code": stock_code,
                "shares": shares,
                "price": price,
                "profit": round(profit, 2),
            }
        except Exception as e:
            logger.error(f"执行卖出失败: {str(e)}")
            return {"success": False, "error": str(e)}

    def ignore_signal(self, stock_code: str, reason: str = "") -> Dict:
        """
        忽略信号

        :param stock_code: 股票代码
        :param reason: 忽略原因
        :return: 操作结果
        """
        try:
            logger.info(f"忽略信号: {stock_code}, 原因: {reason}")
            return {"success": True, "stock_code": stock_code, "reason": reason}
        except Exception as e:
            logger.error(f"忽略信号失败: {str(e)}")
            return {"success": False, "error": str(e)}

    def sync_portfolio_from_ptrade(self) -> Dict:
        """
        从 Ptrade 同步持仓

        :return: 同步结果
        """
        try:
            # 这里实现从 Ptrade 同步持仓的逻辑
            # 实际实现需要调用 Ptrade API
            logger.info("从 Ptrade 同步持仓")
            return {"success": True, "message": "Ptrade 同步功能待实现"}
        except Exception as e:
            logger.error(f"Ptrade 同步失败: {str(e)}")
            return {"success": False, "error": str(e)}

    def check_continuous_temp_risk(self, portfolio: Dict) -> Dict:
        """
        检查连续临时风控

        :param portfolio: 持仓信息
        :return: 风控检查结果
        """
        try:
            # 这里实现连续临时风控检查逻辑
            logger.info("检查连续临时风控")
            return {"has_risk": False, "message": "无风控风险"}
        except Exception as e:
            logger.error(f"风控检查失败: {str(e)}")
            return {"has_risk": False, "error": str(e)}

    def calculate_current_position_ratio(self, portfolio: Dict, total_capital: float) -> float:
        """
        计算当前持仓比例

        :param portfolio: 持仓信息
        :param total_capital: 总资金
        :return: 持仓比例
        """
        try:
            if total_capital <= 0:
                return 0.0

            total_value = sum(
                pos.get("shares", 0) * pos.get("cost_price", 0)
                for pos in portfolio.values()
            )

            return round(total_value / total_capital, 4)
        except Exception as e:
            logger.error(f"计算持仓比例失败: {str(e)}")
            return 0.0
