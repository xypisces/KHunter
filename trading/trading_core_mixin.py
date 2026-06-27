"""
交易核心混入模块
提供 BacktestEngine 和 StrategyRunner 共享的交易逻辑：
交易日历、股价查询、卖出处理、池移除检查、交易成本计算、支撑位计算、冷却池管理
"""

import datetime
import logging
import yaml
import numpy as np
from pathlib import Path
from scipy import stats
from typing import List, Dict, Optional, Tuple

logger = logging.getLogger(__name__)


def calculate_cost(stock_code: str, price: float, quantity: int, is_buy: bool, config: Optional[dict] = None) -> dict:
    """统一交易成本计算（支持可选滑点）

    Args:
        stock_code: 股票代码
        price: 交易价格
        quantity: 交易数量
        is_buy: 是否为买入操作
        config: 交易成本配置（None 时使用硬编码费率，无滑点）

    Returns:
        成本明细字典
    """
    if config is not None:
        trading_config = config.get('trading', {})
        commission_rate = trading_config.get('commission_rate', 0.00015)
        min_commission = trading_config.get('min_commission', 5)
        stamp_tax_rate = trading_config.get('stamp_tax_rate', 0.001)
        transfer_fee_rate = trading_config.get('transfer_fee_rate', 0.00001)
        slippage_config = trading_config.get('slippage', {})
        slippage_enabled = slippage_config.get('enabled', True)
        buy_slippage = slippage_config.get('buy_slippage', 0.01)
        sell_slippage = slippage_config.get('sell_slippage', 0.005)
    else:
        commission_rate = 0.00015
        min_commission = 5
        stamp_tax_rate = 0.001
        transfer_fee_rate = 0.00001
        slippage_enabled = False
        buy_slippage = 0
        sell_slippage = 0

    is_shanghai = stock_code.startswith('6')
    original_amount = price * quantity

    if slippage_enabled:
        slippage_rate = buy_slippage if is_buy else sell_slippage
        adjusted_price = price * (1 + slippage_rate if is_buy else 1 - slippage_rate)
    else:
        slippage_rate = 0
        adjusted_price = price

    slippage_cost = abs(adjusted_price - price) * quantity
    adjusted_amount = adjusted_price * quantity

    commission = adjusted_amount * commission_rate
    commission = max(commission, min_commission)

    transfer_fee = adjusted_amount * transfer_fee_rate if is_shanghai else 0
    stamp_tax = adjusted_amount * stamp_tax_rate if not is_buy else 0

    if is_buy:
        total_cost = slippage_cost + commission + transfer_fee
    else:
        total_cost = slippage_cost + commission + transfer_fee + stamp_tax

    return {
        'original_price': price,
        'adjusted_price': round(adjusted_price, 3),
        'slippage_rate': slippage_rate,
        'slippage_cost': round(slippage_cost, 2),
        'commission': round(commission, 2),
        'transfer_fee': round(transfer_fee, 2) if is_shanghai else 0,
        'stamp_tax': round(stamp_tax, 2) if not is_buy else 0,
        'total_cost': round(total_cost, 2),
        'is_shanghai': is_shanghai,
        'original_amount': round(original_amount, 2),
        'adjusted_amount': round(adjusted_amount, 2),
    }


class TradingCoreMixin:
    """BacktestEngine 和 StrategyRunner 共享的交易核心逻辑"""

    # 配置文件缓存（类级别，所有实例共享）
    _pool_removal_config_cache = None

    # ========== 共享初始化 ==========

    def _init_shared_state(self):
        """初始化共享实例属性（由子类 __init__ 调用）"""
        from utils.global_db import get_global_db, get_stock_repo
        from utils.akshare_fetcher import AKShareFetcher
        from strategy.strategy_registry import StrategyRegistry
        from trading.backtest_scorer import BacktestScoreCalculator
        from trading.preload_manager import PreloadManager

        self.db_manager = get_global_db()
        self.stock_repo = get_stock_repo()
        self.akshare_fetcher = AKShareFetcher("data")
        self.strategy_registry = StrategyRegistry()

        from utils.stock_data_fetcher import StockDataFetcher
        self.stock_data_fetcher = StockDataFetcher("data")
        from utils.kline_fetcher import KlineFetcher
        self.kline_fetcher = KlineFetcher(self.db_manager, self.stock_data_fetcher)

        self.score_calculator = BacktestScoreCalculator(db_manager=self.db_manager)

        self.stock_data_cache = {}
        self.stock_name_cache = {}
        self.stock_filtered_cache = {}

        self.buy_candidate_pool = []

        self.trading_calendar_cache = {}
        self._sorted_trading_dates = []

        self.timing_strategy = None

        self._support_methods_config = self._load_support_methods_config()

        self.preload_manager = PreloadManager(self)

        self.consecutive_loss_count = {}

        # 冷却池（统一 dict 模型：{stock_code: cool_down_end_date_str}）
        self.loss_cool_down_pool = {}
        self.fund_flow_cool_down_pool = {}

    # ========== 配置加载 ==========

    def _load_support_methods_config(self) -> Dict:
        """加载策略支撑位方法配置

        Returns:
            策略名称 -> 支撑位配置字典
        """
        try:
            config_path = Path(__file__).parent.parent / "config" / "support_methods.yaml"
            if not config_path.exists():
                logger.warning(f"支撑位方法配置文件不存在: {config_path}")
                return {}

            with open(config_path, 'r', encoding='utf-8') as f:
                config = yaml.safe_load(f) or {}

            strategies_config = config.get('strategies', {})
            logger.info(f"加载支撑位方法配置: {len(strategies_config)} 个策略")
            return strategies_config
        except Exception as e:
            logger.warning(f"加载支撑位方法配置失败: {str(e)}")
            return {}

    def _load_pool_removal_config(self) -> Dict[str, Dict]:
        """加载股票池移除策略配置（类级缓存）

        Returns:
            策略名称 -> 配置字典的映射
        """
        if TradingCoreMixin._pool_removal_config_cache is not None:
            return TradingCoreMixin._pool_removal_config_cache

        try:
            config_path = Path(__file__).parent.parent / "config" / "pool_removal_config.yaml"
            if not config_path.exists():
                logger.warning(f"股票池移除配置文件不存在: {config_path}")
                self._fund_flow_rules = {'is_enabled': True, 'net_flow_threshold': -10000, 'min_hold_days': 1}
                return {}

            with open(config_path, 'r', encoding='utf-8') as f:
                yaml_config = yaml.safe_load(f) or {}

            self._fund_flow_rules = yaml_config.get('fund_flow_rules', {})
            logger.info(
                f"加载资金流向移除规则: enabled={self._fund_flow_rules.get('is_enabled', False)}, "
                f"threshold={self._fund_flow_rules.get('net_flow_threshold', -10000)}万元, "
                f"min_hold_days={self._fund_flow_rules.get('min_hold_days', 1)}"
            )

            config_map = {}
            strategies = yaml_config.get('removal_strategies', {})
            strategy_count = 0
            for name, cfg in strategies.items():
                if cfg.get('is_enabled', True):
                    strategy_count += 1
                    config_map[name] = {
                        'min_hold_days': cfg.get('min_hold_days', 2),
                        'display_name': cfg.get('display_name', ''),
                    }
                    display_name = cfg.get('display_name', '')
                    if display_name:
                        config_map[display_name] = config_map[name]
                        if display_name.endswith('策略'):
                            config_map[display_name[:-2]] = config_map[name]

            logger.info(f"加载股票池移除策略: {strategy_count} 个策略")
            TradingCoreMixin._pool_removal_config_cache = config_map
            return config_map
        except Exception as e:
            logger.warning(f"加载股票池移除配置失败: {str(e)}")
            self._fund_flow_rules = {'is_enabled': True, 'net_flow_threshold': -10000, 'min_hold_days': 1}
            return {}

    def _get_strategy_removal_config(self, strategy_name: str) -> Dict:
        """获取策略的移除配置

        Args:
            strategy_name: 策略名称

        Returns:
            移除配置字典
        """
        config = self._load_pool_removal_config()

        if strategy_name in config:
            return config[strategy_name]

        if not strategy_name.endswith('策略'):
            with_strategy = strategy_name + '策略'
            if with_strategy in config:
                return config[with_strategy]

        if strategy_name.endswith('策略'):
            without_strategy = strategy_name[:-2]
            if without_strategy in config:
                return config[without_strategy]

        return {'min_hold_days': 2}

    # ========== 支撑位计算 ==========

    def _get_support_method_for_strategy(self, strategy_name: str) -> str:
        """获取策略的支撑位计算方法

        Args:
            strategy_name: 策略名称

        Returns:
            支撑位计算方法（ma20/key_close_5/key_open/key_close）
        """
        strategy_config = self._support_methods_config.get(strategy_name, {})
        if isinstance(strategy_config, dict):
            return strategy_config.get('support_method', 'ma20')
        elif isinstance(strategy_config, str):
            return strategy_config
        return 'ma20'

    def _calculate_support_level(self, stock: Dict, strategy_name: str, current_date: str) -> float:
        """计算候选股票的支撑位

        Args:
            stock: 股票信息（包含 signal 字段，signal 中包含 key_date）
            strategy_name: 策略名称（类名），也可以是支撑位方法名称
            current_date: 选股日期

        Returns:
            支撑位价格，计算失败返回 0.0
        """
        stock_code = stock['stock_code']

        valid_support_methods = ['ma20', 'key_close_5', 'key_open', 'key_close']
        if strategy_name is None:
            support_method = 'ma20'
        elif strategy_name in valid_support_methods:
            support_method = strategy_name
        else:
            support_method = self._get_support_method_for_strategy(strategy_name)

        df = self.stock_filtered_cache.get(stock_code)
        if df is None:
            logger.debug(f"支撑位计算: {stock_code} 无K线数据")
            return 0.0

        date_str = current_date if isinstance(current_date, str) else current_date.strftime('%Y-%m-%d')
        df_to_date = df[df['date'] <= date_str].copy()
        if df_to_date.empty:
            logger.debug(f"支撑位计算: {stock_code} 选股日期 {date_str} 无数据")
            return 0.0

        if len(df_to_date) > 1 and df_to_date['date'].iloc[0] > df_to_date['date'].iloc[1]:
            df_to_date = df_to_date.iloc[::-1].reset_index(drop=True)

        if support_method == 'ma20':
            if len(df_to_date) >= 20:
                ma20_value = round(df_to_date['close'].tail(20).mean(), 2)
                logger.debug(f"支撑位计算: {stock_code} ma20={ma20_value}")
                return ma20_value

        elif support_method in ['key_close_5', 'key_open', 'key_close']:
            signal = stock.get('signal', {})
            key_date = signal.get('key_date') if isinstance(signal, dict) else None

            if key_date:
                key_date_str = str(key_date)[:10]
                key_date_data = df_to_date[df_to_date['date'].astype(str).str[:10] == key_date_str]

                if not key_date_data.empty:
                    if support_method == 'key_close_5':
                        support = round(float(key_date_data.iloc[0]['close']) * 0.95, 2)
                        logger.debug(f"支撑位计算: {stock_code} key_close_5={support} (关键日={key_date_str})")
                        return support
                    elif support_method == 'key_open':
                        support = round(float(key_date_data.iloc[0]['open']), 2)
                        logger.debug(f"支撑位计算: {stock_code} key_open={support} (关键日={key_date_str})")
                        return support
                    elif support_method == 'key_close':
                        support = round(float(key_date_data.iloc[0]['close']), 2)
                        logger.debug(f"支撑位计算: {stock_code} key_close={support} (关键日={key_date_str})")
                        return support
                else:
                    logger.debug(f"支撑位计算: {stock_code} 关键日 {key_date_str} 未在K线数据中找到")
            else:
                logger.debug(f"支撑位计算: {stock_code} 策略 {strategy_name} 需要关键日但信号中无key_date")

        # fallback: 使用20日均线
        if len(df_to_date) >= 20:
            fallback_value = round(df_to_date['close'].tail(20).mean(), 2)
            logger.debug(f"支撑位计算: {stock_code} fallback ma20={fallback_value}")
            return fallback_value

        logger.debug(f"支撑位计算: {stock_code} 数据不足，无法计算")
        return 0.0

    # ========== 资金流向检查 ==========

    def _check_fund_flow_condition(self, stock_code: str, stock_name: str, current_date: str) -> Dict:
        """检查资金流向移除条件

        规则：
        - 如果5日主力净额 < 阈值 或者 大单净流出小单净流入：
          - 如果股票不在冷却池 → 加入冷却池3天，不移除
          - 如果股票已经在冷却池 → 直接移除

        Args:
            stock_code: 股票代码
            stock_name: 股票名称
            current_date: 当前日期（字符串或 date 对象）

        Returns:
            包含 should_remove 和 reason 的字典
        """
        from trading.moneyflow_scorer import MoneyflowScorer

        try:
            # 先清理已过期的冷却池条目
            if stock_code in self.fund_flow_cool_down_pool:
                cool_down_end = self.fund_flow_cool_down_pool.get(stock_code, '')
                if cool_down_end:
                    try:
                        cool_down_end_obj = self._parse_date(cool_down_end)
                        current_date_obj = self._parse_date(current_date)
                        if current_date_obj > cool_down_end_obj:
                            del self.fund_flow_cool_down_pool[stock_code]
                            logger.info(f"股票 {stock_code}: 资金流向冷却期结束，股票出狱")
                    except Exception as e:
                        logger.debug(f"解析冷却结束日期失败: {cool_down_end}, {e}")

            date_str = current_date.strftime('%Y%m%d') if isinstance(current_date, datetime.date) else str(current_date).replace('-', '')

            scorer = MoneyflowScorer()
            df = scorer._fetch_moneyflow_data(stock_code, date_str)

            if df is None or df.empty:
                return {'should_remove': False, 'reason': ''}

            metrics = scorer._extract_flow_metrics(df)
            net_flow_5d = metrics['net_flow_5d']
            large_net = metrics['large_net']
            small_net = metrics['small_net']

            threshold = int(getattr(self, '_fund_flow_rules', {}).get('net_flow_threshold', -10000))

            condition1 = net_flow_5d < threshold
            condition2 = (large_net < 0) and (small_net > 0)

            if condition1 or condition2:
                if condition1 and condition2:
                    reason_detail = f"5日主力净额{net_flow_5d:.0f}万元<{threshold}万元且大单净流出小单净流入"
                elif condition1:
                    reason_detail = f"5日主力净额{net_flow_5d:.0f}万元<{threshold}万元"
                else:
                    reason_detail = "大单净流出且小单净流入（出货信号）"

                is_in_cool_down = stock_code in self.fund_flow_cool_down_pool

                if is_in_cool_down:
                    cool_down_end = self.fund_flow_cool_down_pool.get(stock_code, '')
                    reason = f"{stock_code}资金流向异常[{reason_detail}]，且已在冷却池(至{cool_down_end})，直接移除"
                    del self.fund_flow_cool_down_pool[stock_code]
                    logger.warning(reason)
                    return {'should_remove': True, 'reason': reason}
                else:
                    current_date_obj = self._parse_date(current_date)
                    cool_down_end = self._get_future_trading_day(current_date_obj, 3)
                    self.fund_flow_cool_down_pool[stock_code] = cool_down_end
                    reason = f"{stock_code}资金流向异常[{reason_detail}]，加入冷却池至{cool_down_end}"
                    logger.warning(reason)
                    return {'should_remove': False, 'reason': reason}

            return {'should_remove': False, 'reason': ''}

        except Exception as e:
            logger.warning(f"检查资金流向条件失败: {stock_code} {stock_name}, {str(e)}")
            return {'should_remove': False, 'reason': ''}

    # ========== 冷却池管理 ==========

    def _check_cool_down(self, stock_code: str, current_date: str) -> bool:
        """检查股票是否在亏损冷却期内

        Args:
            stock_code: 股票代码
            current_date: 当前日期（字符串或 date 对象）

        Returns:
            True 表示在冷却期内
        """
        if stock_code not in self.loss_cool_down_pool:
            return False

        cool_down_end = self.loss_cool_down_pool[stock_code]
        try:
            cool_down_end_obj = self._parse_date(cool_down_end)
            current_date_obj = self._parse_date(current_date)

            if current_date_obj <= cool_down_end_obj:
                return True
            else:
                del self.loss_cool_down_pool[stock_code]
                return False
        except Exception:
            del self.loss_cool_down_pool[stock_code]
            return False

    def _update_stock_cool_down_status(self, stock_code: str, is_cooling: bool, cool_down_end: Optional[str] = None):
        """更新冷却池状态

        Args:
            stock_code: 股票代码
            is_cooling: 是否加入冷却
            cool_down_end: 冷却结束日期字符串
        """
        if is_cooling and cool_down_end:
            self.loss_cool_down_pool[stock_code] = cool_down_end
        elif not is_cooling:
            self.loss_cool_down_pool.pop(stock_code, None)

    # ========== 工具方法 ==========

    @staticmethod
    def _parse_date(value) -> datetime.date:
        """将字符串或 date 对象统一转换为 date 对象

        Args:
            value: 日期字符串（YYYY-MM-DD）或 date 对象

        Returns:
            date 对象
        """
        if isinstance(value, datetime.date):
            return value
        if isinstance(value, datetime.datetime):
            return value.date()
        return datetime.datetime.strptime(str(value)[:10], '%Y-%m-%d').date()

    def _get_future_trading_day(self, start_date, days: int):
        """获取指定日期之后的第N个交易日

        Args:
            start_date: 起始日期（字符串或 date 对象）
            days: 往后多少个交易日

        Returns:
            与输入类型一致的日期
        """
        from utils.trade_date_utils import is_trading_day

        was_date_obj = isinstance(start_date, (datetime.date, datetime.datetime))
        current = self._parse_date(start_date)
        trading_days_found = 0

        while trading_days_found < days:
            current += datetime.timedelta(days=1)
            if is_trading_day(current.strftime('%Y-%m-%d')):
                trading_days_found += 1

        return current if was_date_obj else current.strftime('%Y-%m-%d')

    # ========== 股票池移除检查 ==========

    def _check_pool_removal(self, current_date: str) -> List[Dict]:
        """检查股票池中需要移除的股票

        移除条件（满足任一即移除）：
        1. 破支撑位：收盘价 < 支撑位 × 0.98（始终生效）
        2. 不满足上升趋势条件（持有 min_hold_days 天后生效）
        3. 资金流向条件

        Args:
            current_date: 当前交易日期（字符串）

        Returns:
            移除的候选列表
        """
        from utils.trade_date_utils import get_previous_trading_day

        removed = []
        remaining = []

        prev_date_str = get_previous_trading_day(current_date)

        fund_flow_enabled = getattr(self, '_fund_flow_rules', {}).get('is_enabled', True)
        fund_flow_min_hold_days = getattr(self, '_fund_flow_rules', {}).get('min_hold_days', 1)

        for candidate in self.buy_candidate_pool:
            stock_code = candidate['stock']['stock_code']
            stock_name = candidate['stock']['stock_name']
            strategy_name = candidate.get('strategy_name', '')

            # 更新过期冷却状态
            self._check_cool_down(stock_code, current_date)

            # 更新股票池现价
            try:
                df_price = self.stock_filtered_cache.get(stock_code)
                if df_price is not None and not df_price.empty:
                    price_row = df_price[df_price['date'] == current_date]
                    if not price_row.empty:
                        latest_price = float(price_row['close'].values[0])
                    else:
                        latest_price = float(df_price['close'].values[0])
                    if 'signal' in candidate['stock']:
                        candidate['stock']['signal']['close'] = latest_price
                    elif 'close' in candidate['stock']:
                        candidate['stock']['close'] = latest_price
                    logger.debug(f"【股票池】{stock_code} 现价更新为: {latest_price:.2f}")
            except Exception as e:
                logger.debug(f"【股票池】更新 {stock_code} 现价失败: {str(e)}")

            removal_config = self._get_strategy_removal_config(strategy_name)
            min_hold_days = removal_config.get('min_hold_days', 2)

            # 计算持有天数
            added_date = candidate.get('added_date', '')
            hold_days = 0
            if added_date:
                if hasattr(added_date, 'strftime'):
                    added_date = added_date.strftime('%Y-%m-%d')
                try:
                    added_dt = datetime.datetime.strptime(str(added_date)[:10], '%Y-%m-%d')
                    current_dt = datetime.datetime.strptime(str(current_date)[:10], '%Y-%m-%d')
                    hold_days = (current_dt - added_dt).days
                except Exception:
                    hold_days = 0

            # 获取股票数据
            df = self.stock_filtered_cache.get(stock_code)
            if df is None:
                remaining.append(candidate)
                continue

            # 日期切片
            df_for_support = df[df['date'] <= current_date].copy()
            if len(df_for_support) < 20:
                remaining.append(candidate)
                continue

            # 获取收盘价（兼容正序/倒序）
            if df_for_support['date'].iloc[0] > df_for_support['date'].iloc[-1]:
                price_for_check = df_for_support.iloc[0]['close']
                trend_df = df_for_support.iloc[::-1].reset_index(drop=True)
            else:
                price_for_check = df_for_support.iloc[-1]['close']
                trend_df = df_for_support

            # 移除判断
            removal_reasons = []
            should_remove = False

            # 条件1: 破支撑位
            support_level = candidate.get('support_level', 0.0)
            if support_level > 0 and price_for_check > 0:
                if price_for_check < support_level * 0.98:
                    should_remove = True
                    drop_pct = (price_for_check - support_level) / support_level * 100
                    removal_reasons.append(f"跌破支撑位{support_level:.2f}{drop_pct:.1f}%")

            # 条件2: 趋势验证
            if hold_days >= min_hold_days and len(trend_df) >= 20:
                ma10 = trend_df['close'].tail(10).mean()
                prices = trend_df['close'].tail(20).values
                x = np.arange(len(prices))
                linregress_result = stats.linregress(x, prices)
                slope: float = linregress_result[0]  # type: ignore[assignment]
                r_value: float = linregress_result[2]  # type: ignore[assignment]
                r_squared = r_value ** 2

                trend_ok = (price_for_check >= ma10 and slope > 0 and r_squared >= 0.3)

                if not trend_ok:
                    should_remove = True
                    if price_for_check < ma10:
                        removal_reasons.append(f"收盘价{price_for_check:.2f}<MA10{ma10:.2f}")
                    if slope <= 0:
                        removal_reasons.append(f"斜率{slope:.4f}<=0")
                    if r_squared < 0.3:
                        removal_reasons.append(f"R²{r_squared:.4f}<0.3")

            # 条件3: 资金流向
            if fund_flow_enabled and hold_days >= fund_flow_min_hold_days:
                fund_flow_result = self._check_fund_flow_condition(stock_code, stock_name, current_date)
                if fund_flow_result['should_remove']:
                    should_remove = True
                    removal_reasons.append(fund_flow_result['reason'])

            if should_remove:
                removed.append(candidate)
                logger.info(f"【移除】{current_date} {stock_code} {stock_name}: "
                           f"收盘={price_for_check:.2f}, 策略={strategy_name}, 持{hold_days}日, "
                           f"原因: {'; '.join(removal_reasons)}")
            else:
                remaining.append(candidate)
                keep_reasons = []
                if support_level > 0:
                    keep_reasons.append('支撑位OK' if price_for_check >= support_level * 0.98 else '破支撑位但未移除')
                if hold_days < min_hold_days:
                    keep_reasons.append(f'持有{hold_days}<{min_hold_days}天，跳过趋势检查')
                elif len(trend_df) >= 20:
                    keep_reasons.append('趋势OK')
                logger.debug(f"【保留】{stock_code} {stock_name}: 持{hold_days}日, {', '.join(keep_reasons)}")

        if removed:
            logger.info(f"股票池移除: {len(removed)} 只, 剩余: {len(remaining)} 只")
            self.buy_candidate_pool = remaining

        return removed
