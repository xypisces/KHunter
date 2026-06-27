"""
策略运行引擎 V2 - 薄编排器版本

使用组合模式将职责委托给专用模块：
- PortfolioManager: 持仓管理 + 交易执行
- SignalStore: 信号持久化
- ExdividendHandler: 除权除息处理
- TaskHistory: 任务历史 + 日报生成
- StrategyExecutor: 选股 + 评分 + 批量执行
"""
import datetime
import logging
import threading
from pathlib import Path
from typing import List, Dict, Optional, Any

from trading.portfolio_manager import PortfolioManager
from trading.signal_store import SignalStore
from trading.exdividend_handler import ExdividendHandler
from trading.task_history import TaskHistory
from trading.strategy_executor import StrategyExecutor

logger = logging.getLogger(__name__)


class StrategyRunnerV2:
    """策略运行引擎 V2 - 薄编排器"""

    _is_running = False

    def __init__(
        self,
        db_manager: Any = None,
        stock_repo: Any = None,
        registry: Any = None,
        config: Optional[Dict] = None,
    ):
        """
        初始化策略运行引擎

        :param db_manager: 数据库管理器
        :param stock_repo: 股票仓库
        :param registry: 策略注册器
        :param config: 配置信息
        """
        self.db_manager = db_manager
        self.stock_repo = stock_repo
        self.registry = registry
        self.config = config or {}

        # 运行目录
        self.running_dir = Path(__file__).resolve().parent.parent / "data/running"
        self.running_dir.mkdir(exist_ok=True)

        # 初始化子模块
        self.portfolio_manager = PortfolioManager(
            self.running_dir, stock_repo, db_manager
        )
        self.signal_store = SignalStore(self.running_dir)
        self.exdividend_handler = ExdividendHandler(self.running_dir, stock_repo)
        self.task_history = TaskHistory(self.running_dir)
        self.strategy_executor = StrategyExecutor(db_manager, stock_repo, registry)

        # 当前总资金
        self.current_total_capital = self.config.get("initial_capital", 300000.0)

        logger.info("StrategyRunnerV2 初始化完成")

    # ── 持仓管理委托 ──────────────────────────────────────────

    def load_portfolio(self) -> Dict:
        """加载持仓信息"""
        return self.portfolio_manager.load_portfolio()

    def save_portfolio(self, portfolio: Dict) -> bool:
        """保存持仓信息"""
        return self.portfolio_manager.save_portfolio(portfolio)

    def execute_signal(self, signal: Dict) -> Dict:
        """执行交易信号"""
        return self.portfolio_manager.execute_signal(signal, self.config)

    def ignore_signal(self, stock_code: str, reason: str = "") -> Dict:
        """忽略信号"""
        return self.portfolio_manager.ignore_signal(stock_code, reason)

    def sync_portfolio_from_ptrade(self) -> Dict:
        """从 Ptrade 同步持仓"""
        return self.portfolio_manager.sync_portfolio_from_ptrade()

    # ── 信号管理委托 ──────────────────────────────────────────

    def load_signals(self) -> List[Dict]:
        """加载信号列表"""
        return self.signal_store.load_signals()

    def save_signals(self, signals: List[Dict]) -> bool:
        """保存信号列表"""
        return self.signal_store.save_signals(signals)

    def get_pending_signals(self) -> List[Dict]:
        """获取待执行信号"""
        return self.signal_store.get_pending_signals()

    # ── 除权除息委托 ──────────────────────────────────────────

    def check_portfolio_exdividend(self) -> List[Dict]:
        """检查持仓的除权除息"""
        portfolio = self.load_portfolio()
        return self.exdividend_handler.check_portfolio_exdividend(portfolio)

    def check_signals_exdividend(self) -> List[Dict]:
        """检查信号的除权除息"""
        signals = self.load_signals()
        return self.exdividend_handler.check_signals_exdividend(signals)

    # ── 任务历史委托 ──────────────────────────────────────────

    def save_task_record(self, task_config: Dict) -> Dict:
        """保存任务记录"""
        return self.task_history.save_task_record(task_config)

    def get_task_history(self) -> List[Dict]:
        """获取任务历史"""
        return self.task_history.get_task_history()

    def get_last_task(self) -> Optional[Dict]:
        """获取最后一个任务"""
        return self.task_history.get_last_task()

    def generate_daily_report(self) -> Dict:
        """生成每日报告"""
        portfolio = self.load_portfolio()
        signals = self.load_signals()
        return self.task_history.generate_daily_report(portfolio, signals, self.config)

    # ── 策略执行委托 ──────────────────────────────────────────

    def execute_selection(self, strategy_name: str, stock_data: Dict) -> List[Dict]:
        """执行选股"""
        return self.strategy_executor.execute_selection(
            strategy_name, stock_data, self.config
        )

    def score_stocks(self, signals: List[Dict]) -> List[Dict]:
        """对股票进行评分"""
        return self.strategy_executor.score_stocks(signals, self.config)

    def run_strategies_batch(
        self,
        strategy_names: List[str],
        stock_data: Dict,
        timing_strategy: Optional[str] = None,
    ) -> Dict:
        """批量运行策略"""
        return self.strategy_executor.run_strategies_batch(
            strategy_names, stock_data, self.config, timing_strategy
        )

    # ── 风控检查委托 ──────────────────────────────────────────

    def check_risk(self) -> Dict:
        """检查风控"""
        portfolio = self.load_portfolio()
        return self.portfolio_manager.check_continuous_temp_risk(portfolio)

    def get_position_ratio(self) -> float:
        """获取持仓比例"""
        portfolio = self.load_portfolio()
        return self.portfolio_manager.calculate_current_position_ratio(
            portfolio, self.current_total_capital
        )

    # ── 编排方法 ─────────────────────────────────────────────

    def initialize_daily(self) -> Dict:
        """
        每日初始化

        :return: 初始化结果
        """
        try:
            logger.info("开始每日初始化")

            # 检查除权除息
            exdividends = self.check_portfolio_exdividend()
            if exdividends:
                logger.info(f"发现 {len(exdividends)} 个除权除息事件")

            # 生成日报
            report = self.generate_daily_report()

            # 同步 Ptrade 持仓
            ptrade_result = self.sync_portfolio_from_ptrade()

            return {
                "success": True,
                "exdividends": exdividends,
                "report": report,
                "ptrade_sync": ptrade_result,
            }
        except Exception as e:
            logger.error(f"每日初始化失败: {str(e)}")
            return {"success": False, "error": str(e)}

    def execute_pending_signals(self) -> Dict:
        """
        执行待处理信号

        :return: 执行结果
        """
        try:
            signals = self.get_pending_signals()
            if not signals:
                return {"success": True, "message": "没有待执行信号"}

            results = []
            for signal in signals:
                result = self.execute_signal(signal)
                results.append(result)

            return {
                "success": True,
                "total": len(signals),
                "results": results,
            }
        except Exception as e:
            logger.error(f"执行待处理信号失败: {str(e)}")
            return {"success": False, "error": str(e)}

    def run(
        self,
        strategy_names: List[str],
        stock_data: Dict,
        timing_strategy: Optional[str] = None,
    ) -> Dict:
        """
        完整运行流程

        :param strategy_names: 策略名称列表
        :param stock_data: 股票数据
        :param timing_strategy: 择时策略
        :return: 运行结果
        """
        try:
            # 防止并发执行
            if StrategyRunnerV2._is_running:
                return {"success": False, "error": "策略正在运行中"}

            StrategyRunnerV2._is_running = True

            try:
                logger.info("=" * 60)
                logger.info("开始策略运行")
                logger.info(f"策略: {strategy_names}")
                logger.info(f"择时: {timing_strategy}")
                logger.info("=" * 60)

                # 1. 每日初始化
                init_result = self.initialize_daily()
                logger.info(f"每日初始化: {init_result.get('success')}")

                # 2. 批量运行策略
                batch_result = self.run_strategies_batch(
                    strategy_names, stock_data, timing_strategy
                )

                # 3. 执行待处理信号
                exec_result = self.execute_pending_signals()

                # 4. 保存任务记录
                task_config = {
                    "strategies": strategy_names,
                    "timing_strategy": timing_strategy,
                    "initial_capital": self.current_total_capital,
                }
                self.save_task_record(task_config)

                return {
                    "success": True,
                    "init": init_result,
                    "batch": batch_result,
                    "execution": exec_result,
                }
            finally:
                StrategyRunnerV2._is_running = False

        except Exception as e:
            logger.error(f"策略运行失败: {str(e)}")
            StrategyRunnerV2._is_running = False
            return {"success": False, "error": str(e)}
