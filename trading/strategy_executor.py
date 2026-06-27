"""
策略执行模块 - 处理选股、评分和批量执行
"""
import datetime
from typing import Dict, List, Optional, Any
import logging

logger = logging.getLogger(__name__)


class StrategyExecutor:
    """策略执行器"""

    def __init__(self, db_manager: Any = None, stock_repo: Any = None, registry: Any = None):
        """
        初始化策略执行器

        :param db_manager: 数据库管理器
        :param stock_repo: 股票仓库
        :param registry: 策略注册器
        """
        self.db_manager = db_manager
        self.stock_repo = stock_repo
        self.registry = registry

    def execute_selection(
        self, strategy_name: str, stock_data: Dict, config: Dict
    ) -> List[Dict]:
        """
        执行选股

        :param strategy_name: 策略名称
        :param stock_data: 股票数据 {code: (name, df)}
        :param config: 配置信息
        :return: 选股结果列表
        """
        try:
            if not self.registry:
                logger.error("策略注册器未初始化")
                return []

            strategy = self.registry.get_strategy(strategy_name)
            if not strategy:
                logger.error(f"策略 {strategy_name} 不存在")
                return []

            signals = []
            total_stocks = len(stock_data)

            for idx, (code, (name, df)) in enumerate(stock_data.items(), 1):
                try:
                    result = strategy.analyze_stock(code, name, df)
                    if result:
                        signals.append(result)
                except Exception as e:
                    logger.debug(f"策略 {strategy_name} 分析股票 {code} 失败: {str(e)}")

                if idx % 100 == 0:
                    logger.info(
                        f"  策略 {strategy_name} 进度: [{idx}/{total_stocks}] - 选中 {len(signals)} 只"
                    )

            logger.info(f"策略 {strategy_name} 选股完成: {len(signals)} 只")
            return signals
        except Exception as e:
            logger.error(f"执行选股失败: {str(e)}")
            return []

    def score_stocks(self, signals: List[Dict], config: Dict) -> List[Dict]:
        """
        对股票进行评分

        :param signals: 信号列表
        :param config: 配置信息
        :return: 评分后的信号列表
        """
        try:
            scored_signals = []

            for signal in signals:
                # 计算综合评分
                score = self._calculate_score(signal, config)
                signal["score"] = score
                scored_signals.append(signal)

            # 按评分排序
            scored_signals.sort(key=lambda x: x.get("score", 0), reverse=True)

            logger.info(f"评分完成: {len(scored_signals)} 只股票")
            return scored_signals
        except Exception as e:
            logger.error(f"评分失败: {str(e)}")
            return signals

    def _calculate_score(self, signal: Dict, config: Dict) -> float:
        """
        计算股票评分

        :param signal: 信号数据
        :param config: 配置信息
        :return: 评分
        """
        try:
            score = 0.0

            # 基础分
            score += 50.0

            # 信号强度加分
            signal_strength = signal.get("signal_strength", 0)
            score += signal_strength * 20

            # 策略数量加分
            strategies = signal.get("strategies", [])
            score += len(strategies) * 10

            return round(score, 2)
        except Exception as e:
            logger.error(f"计算评分失败: {str(e)}")
            return 0.0

    def select_and_score_stocks(
        self, strategy_names: List[str], stock_data: Dict, config: Dict
    ) -> List[Dict]:
        """
        选股并评分

        :param strategy_names: 策略名称列表
        :param stock_data: 股票数据
        :param config: 配置信息
        :return: 评分后的信号列表
        """
        try:
            all_signals = []

            for strategy_name in strategy_names:
                signals = self.execute_selection(strategy_name, stock_data, config)
                all_signals.extend(signals)

            # 去重
            unique_signals = self._deduplicate_signals(all_signals)

            # 评分
            scored_signals = self.score_stocks(unique_signals, config)

            return scored_signals
        except Exception as e:
            logger.error(f"选股评分失败: {str(e)}")
            return []

    def _deduplicate_signals(self, signals: List[Dict]) -> List[Dict]:
        """
        信号去重

        :param signals: 信号列表
        :return: 去重后的信号列表
        """
        seen = set()
        unique_signals = []

        for signal in signals:
            code = signal.get("code")
            if code and code not in seen:
                seen.add(code)
                unique_signals.append(signal)

        return unique_signals

    def run_strategies_batch(
        self,
        strategy_names: List[str],
        stock_data: Dict,
        config: Dict,
        timing_strategy: Optional[str] = None,
    ) -> Dict:
        """
        批量运行策略

        :param strategy_names: 策略名称列表
        :param stock_data: 股票数据
        :param config: 配置信息
        :param timing_strategy: 择时策略名称
        :return: 运行结果
        """
        try:
            start_time = datetime.datetime.now()
            logger.info(f"开始批量运行策略: {strategy_names}")

            # 选股评分
            signals = self.select_and_score_stocks(strategy_names, stock_data, config)

            # 应用择时策略
            if timing_strategy:
                signals = self._apply_timing_strategy(signals, timing_strategy, stock_data)

            end_time = datetime.datetime.now()
            elapsed = (end_time - start_time).total_seconds()

            result = {
                "success": True,
                "signals": signals,
                "total_signals": len(signals),
                "strategies": strategy_names,
                "timing_strategy": timing_strategy,
                "elapsed_time": round(elapsed, 2),
                "timestamp": end_time.strftime("%Y-%m-%d %H:%M:%S"),
            }

            logger.info(f"批量运行完成: {len(signals)} 个信号, 耗时 {elapsed:.2f}秒")
            return result
        except Exception as e:
            logger.error(f"批量运行失败: {str(e)}")
            return {"success": False, "error": str(e)}

    def _apply_timing_strategy(
        self, signals: List[Dict], timing_strategy: str, stock_data: Dict
    ) -> List[Dict]:
        """
        应用择时策略

        :param signals: 信号列表
        :param timing_strategy: 择时策略名称
        :param stock_data: 股票数据
        :return: 过滤后的信号列表
        """
        try:
            # 这里实现择时策略的逻辑
            # 实际实现需要根据择时策略过滤信号
            logger.info(f"应用择时策略: {timing_strategy}")
            return signals
        except Exception as e:
            logger.error(f"应用择时策略失败: {str(e)}")
            return signals
