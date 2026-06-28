"""
数据采集服务模块
管理数据更新的业务逻辑
"""

import logging
import threading
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Optional, Any

from utils.trading_time_validator import TradingTimeValidator
from utils.new_stock_detector import NewStockDetector
from utils.market_data.stock_fetcher import StockDataFetcher
from utils.data_initializer import DataInitializer
from utils.kline_updater import KlineUpdater
from utils.fund_flow_updater import FundFlowUpdater
from utils.fund_flow.fund_flow_fetcher import FundFlowFetcher
from utils.market_temperature import DataNotAvailableError

logger = logging.getLogger(__name__)


class DataCollectionService:
    """数据采集服务类 — 管理数据更新流程"""

    def __init__(self, data_dir: str = 'data'):
        """
        初始化数据采集服务

        Args:
            data_dir: 数据目录路径
        """
        self.data_dir = Path(data_dir)
        self.data_dir.mkdir(parents=True, exist_ok=True)

        # 数据库路径
        self.selection_db_path = self.data_dir / 'stock_selection.db'

        # 初始化数据库管理器
        from utils.global_db import get_global_db
        self.db_manager = get_global_db()

        # 初始化股票数据获取器
        self.stock_data_fetcher = StockDataFetcher()

        # 更新状态
        self.update_status: Dict[str, Any] = {
            'running': False,
            'paused': False,
            'progress': 0,
            'total': 0,
            'current_task': '',
            'success': 0,
            'failed': 0,
            'message': '',
            'start_time': None,
            'end_time': None,
            'logs': [],
            'status': 'idle',  # idle, running, paused, completed, failed, cancelled
            'statistics': {},
            'tasks': [],
            'totalStats': {
                'added': 0,
                'updated': 0,
                'deleted': 0,
                'processed': 0,
                'new_stock_detected': 0,
                'new_stock_initialized': 0
            }
        }

        # 线程锁
        self.update_lock = threading.Lock()

    def start_update(self, update_types: Optional[List[str]] = None) -> Dict[str, Any]:
        """
        开始数据更新

        Args:
            update_types: 更新类型列表

        Returns:
            dict: 更新任务信息
        """
        if self.update_status['running']:
            return {
                'success': False,
                'message': '已有更新任务正在运行',
                'taskId': None
            }

        task_id = f"UPDATE_{datetime.now().strftime('%Y%m%d_%H%M%S')}"

        thread = threading.Thread(
            target=self._run_update,
            args=(task_id, update_types),
            daemon=True
        )
        thread.start()

        return {
            'success': True,
            'message': '更新任务已启动',
            'taskId': task_id
        }

    def _run_update(self, task_id: str, update_types: Optional[List[str]]):
        """
        执行更新任务（在后台线程中运行）

        流程:
        1. 检查交易时间和更新条件
        2. 检测并初始化新股票
        3. 获取所有股票列表
        4. 查询上次更新日期
        5. 更新K线数据
        6. 更新资金流向数据
        7. 更新股票市值信息
        8. 记录更新完成时间
        9. 计算并保存市场温度
        10. 计算并保存风控状态

        Args:
            task_id: 任务ID
            update_types: 更新类型列表（可选）
        """
        target_date = None
        validator = None
        stats: Dict[str, Any] = {}
        trade_date_yyyymmdd = ""

        try:
            # 初始化状态
            with self.update_lock:
                self.update_status['running'] = True
                self.update_status['paused'] = False
                self.update_status['status'] = 'running'
                self.update_status['start_time'] = datetime.now().isoformat()
                self.update_status['logs'] = []
                self.update_status['message'] = ''
                self.update_status['totalStats'] = {
                    'new_stock_detected': 0,
                    'new_stock_initialized': 0,
                    'kline_added': 0,
                    'kline_updated': 0,
                    'kline_failed': 0,
                    'fund_flow_added': 0,
                    'fund_flow_updated': 0,
                    'fund_flow_failed': 0,
                    'market_cap_updated': 0,
                    'market_cap_failed': 0
                }

            self._add_update_log(f"✓ 更新任务 {task_id} 已启动")

            # 【第1步】检查交易时间和更新条件
            self._add_update_log("【第1步】检查交易时间和更新条件...")
            validator = TradingTimeValidator(self.db_manager)
            is_valid, error_msg, target_date = validator.validate_update_time()

            if not is_valid:
                with self.update_lock:
                    self.update_status['status'] = 'failed'
                    self.update_status['message'] = error_msg
                self._add_update_log(f"✗ 错误: {error_msg}")
                logger.warning(f"更新任务 {task_id} 被拒绝: {error_msg}")
                return

            self._add_update_log(f"✓ 目标更新日期: {target_date}")
            validator.record_update_start(target_date)

            # 【第2步】检测并初始化新股票
            self._add_update_log("【第2步】检测并初始化新股票...")
            try:
                stock_data_fetcher = StockDataFetcher()
                data_initializer = DataInitializer(
                    self.db_manager, stock_data_fetcher, None, None
                )
                detector = NewStockDetector(
                    self.db_manager, stock_data_fetcher, data_initializer
                )
                new_stock_result = detector.detect_and_init_new_stocks(years=3, days=30)

                with self.update_lock:
                    self.update_status['totalStats']['new_stock_detected'] = new_stock_result.get('detected', 0)
                    self.update_status['totalStats']['new_stock_initialized'] = new_stock_result.get('initialized', 0)

                if new_stock_result['success']:
                    self._add_update_log(
                        f"✓ 新股票检测完成: 检测 {new_stock_result['detected']} 只，"
                        f"初始化 {new_stock_result['initialized']} 只，"
                        f"失败 {new_stock_result['failed']} 只"
                    )
                    if new_stock_result['failed'] > 0:
                        failed_stocks = new_stock_result.get('failed_stocks', [])
                        self._add_update_log(f"⚠ 初始化失败的股票: {', '.join(failed_stocks[:5])}")
                else:
                    self._add_update_log(f"⚠ 新股票检测失败: {new_stock_result.get('message', '未知错误')}")
                    logger.warning(f"新股票检测失败: {new_stock_result.get('message', '未知错误')}")
            except Exception as e:
                self._add_update_log(f"⚠ 新股票检测异常: {str(e)}")
                logger.warning(f"新股票检测异常: {str(e)}")

            # 【第3步】获取所有股票列表
            self._add_update_log("【第3步】获取所有股票列表...")
            try:
                sql = "SELECT DISTINCT code FROM stock_basic ORDER BY code"
                result = self.db_manager.query(sql)
                stock_codes = [row['code'] for row in result] if result else []
                self._add_update_log(f"✓ 获取股票列表完成: {len(stock_codes)} 只股票")
            except Exception as e:
                self._add_update_log(f"✗ 获取股票列表失败: {str(e)}")
                logger.error(f"获取股票列表失败: {str(e)}")
                stock_codes = []

            # 【第4步】查询上次更新日期
            self._add_update_log("【第4步】查询上次更新日期...")
            try:
                last_update_date = validator.get_last_update_date()
                if not last_update_date:
                    last_update_date = (datetime.now() - timedelta(days=3)).strftime('%Y-%m-%d')
                self._add_update_log(f"✓ 上次更新日期: {last_update_date}")
            except Exception as e:
                self._add_update_log(f"✗ 查询上次更新日期失败: {str(e)}")
                logger.error(f"查询上次更新日期失败: {str(e)}")
                last_update_date = (datetime.now() - timedelta(days=3)).strftime('%Y-%m-%d')

            # 【第5步】更新K线数据
            if not update_types or 'kline' in update_types:
                self._add_update_log("【第5步】更新K线数据...")
                try:
                    stock_data_fetcher = StockDataFetcher()
                    kline_updater = KlineUpdater(self.db_manager, stock_data_fetcher)
                    kline_result = kline_updater.update_kline_data(
                        stock_codes=stock_codes,
                        last_update_date=last_update_date,
                        target_date=target_date,
                        batch_size=100
                    )

                    with self.update_lock:
                        self.update_status['totalStats']['kline_added'] = kline_result.get('added', 0)
                        self.update_status['totalStats']['kline_updated'] = kline_result.get('updated', 0)
                        self.update_status['totalStats']['kline_failed'] = kline_result.get('failed', 0)

                    if kline_result['success']:
                        self._add_update_log(
                            f"✓ K线数据更新完成: 新增 {kline_result['added']} 条，"
                            f"更新 {kline_result['updated']} 条，失败 {kline_result['failed']} 条，"
                            f"耗时 {kline_result['total_time']:.1f}秒"
                        )
                        if '数据源尚未就绪' in kline_result.get('message', ''):
                            self._add_update_log("⚠ 数据源尚未就绪，跳过本次更新")
                            logger.info("数据源尚未就绪，跳过本次更新")
                            self.update_status['status'] = 'completed'
                            self.update_status['end_time'] = datetime.now().isoformat()
                            self.update_status['message'] = '数据源尚未就绪，已跳过本次更新'
                            return
                except Exception as e:
                    self._add_update_log(f"✗ K线数据更新异常: {str(e)}")
                    logger.error(f"K线数据更新异常: {str(e)}")
                    with self.update_lock:
                        self.update_status['totalStats']['kline_failed'] = len(stock_codes)

            # 【第6步】更新资金流向数据
            if not update_types or 'fund_flow' in update_types:
                self._add_update_log("【第6步】更新资金流向数据...")
                try:
                    fund_flow_fetcher = FundFlowFetcher(self.db_manager)
                    fund_flow_updater = FundFlowUpdater(self.db_manager, fund_flow_fetcher)
                    fund_flow_result = fund_flow_updater.update_fund_flow_data(
                        last_update_date=last_update_date,
                        target_date=target_date
                    )

                    with self.update_lock:
                        self.update_status['totalStats']['fund_flow_added'] = fund_flow_result.get('added', 0)
                        self.update_status['totalStats']['fund_flow_updated'] = fund_flow_result.get('updated', 0)
                        self.update_status['totalStats']['fund_flow_failed'] = fund_flow_result.get('failed', 0)

                    if fund_flow_result['success']:
                        self._add_update_log(
                            f"✓ 资金流向数据更新完成: 新增 {fund_flow_result['added']} 条，"
                            f"更新 {fund_flow_result['updated']} 条，失败 {fund_flow_result['failed']} 条，"
                            f"耗时 {fund_flow_result['total_time']:.1f}秒"
                        )
                    else:
                        self._add_update_log(f"✗ 资金流向数据更新失败: {fund_flow_result.get('message', '未知错误')}")
                        logger.warning(f"资金流向数据更新失败: {fund_flow_result.get('message', '未知错误')}")
                except Exception as e:
                    self._add_update_log(f"✗ 资金流向数据更新异常: {str(e)}")
                    logger.error(f"资金流向数据更新异常: {str(e)}")
                    with self.update_lock:
                        self.update_status['totalStats']['fund_flow_failed'] = 1

            # 【第7步】更新股票市值信息
            self._add_update_log("【第7步】更新股票市值信息...")
            try:
                stock_data_fetcher = StockDataFetcher()
                market_cap_result = stock_data_fetcher.update_stock_market_cap(
                    db_manager=self.db_manager, max_retries=3
                )

                with self.update_lock:
                    self.update_status['totalStats']['market_cap_updated'] = market_cap_result.get('updated', 0)
                    self.update_status['totalStats']['market_cap_failed'] = market_cap_result.get('failed', 0)

                if market_cap_result['updated'] > 0:
                    self._add_update_log(f"✓ 股票市值更新完成: 更新 {market_cap_result['updated']} 只，失败 {market_cap_result['failed']} 只")
                else:
                    self._add_update_log(f"⚠ 股票市值更新: 更新 {market_cap_result['updated']} 只，失败 {market_cap_result['failed']} 只")
                    logger.warning(f"股票市值更新: 更新 {market_cap_result['updated']} 只，失败 {market_cap_result['failed']} 只")
            except Exception as e:
                self._add_update_log(f"✗ 股票市值更新异常: {str(e)}")
                logger.error(f"股票市值更新异常: {str(e)}")
                with self.update_lock:
                    self.update_status['totalStats']['market_cap_failed'] = len(stock_codes)

            # 【第8步】记录更新完成
            self._add_update_log("【第8步】记录更新完成...")
            try:
                stats = {
                    'new_stock_detected': self.update_status['totalStats']['new_stock_detected'],
                    'new_stock_initialized': self.update_status['totalStats']['new_stock_initialized'],
                    'kline_added': self.update_status['totalStats']['kline_added'],
                    'kline_updated': self.update_status['totalStats']['kline_updated'],
                    'fund_flow_added': self.update_status['totalStats']['fund_flow_added'],
                    'fund_flow_updated': self.update_status['totalStats']['fund_flow_updated'],
                    'market_cap_updated': self.update_status['totalStats']['market_cap_updated'],
                    'market_cap_failed': self.update_status['totalStats']['market_cap_failed']
                }
                validator.record_update_complete(target_date, stats)
                self._add_update_log("✓ 更新统计信息已记录")
            except Exception as e:
                self._add_update_log(f"✗ 记录更新完成失败: {str(e)}")
                logger.error(f"记录更新完成失败: {str(e)}")

            # 【第9步】计算并保存市场温度
            self._add_update_log("【第9步】计算并保存市场温度...")
            try:
                from utils.market_temperature import MarketTemperature
                from trading.market_temperature_dao import MarketTemperatureDAO

                trade_date_yyyymmdd = target_date.replace('-', '')
                mt = MarketTemperature()
                temp_result = mt.calculate(trade_date_yyyymmdd, use_cache=False)

                dao = MarketTemperatureDAO()
                dao.save(temp_result)

                self._add_update_log(
                    f"✓ 市场温度计算完成: {temp_result.get('temperature', 'N/A')}° - "
                    f"{temp_result.get('status', '未知')} - "
                    f"仓位{temp_result.get('position_ratio', 0) * 100:.0f}%"
                )
                logger.info(f"市场温度已保存: {trade_date_yyyymmdd} - {temp_result.get('temperature')}°")
            except DataNotAvailableError as e:
                self._add_update_log(f"ℹ 市场温度跳过: {str(e)}")
                logger.info(f"市场温度跳过（非交易日或数据不可用）: {trade_date_yyyymmdd} - {str(e)}")
            except Exception as e:
                self._add_update_log(f"⚠ 市场温度计算失败: {str(e)}")
                logger.warning(f"市场温度计算失败: {str(e)}")

            # 【第10步】计算并保存风控状态
            self._add_update_log("【第10步】计算并保存风控状态...")
            try:
                from utils.risk_controller import RiskController

                controller = RiskController()
                risk_status = controller.get_risk_status(date=target_date, force_refresh=True)

                if risk_status:
                    self._add_update_log(
                        f"✓ 风控状态计算完成: VaR(1d)={risk_status.var_1d*100:.2f}% - "
                        f"风险等级={risk_status.risk_level.value} - "
                        f"仓位上限={risk_status.position_limit*100:.0f}%"
                    )
                    logger.info(f"风控状态已保存: {target_date} - VaR={risk_status.var_1d*100:.2f}%")
                else:
                    self._add_update_log("⚠ 风控状态计算失败: 返回空值")
                    logger.warning(f"风控状态计算失败: {target_date} - 返回空值")
            except Exception as e:
                self._add_update_log(f"⚠ 风控状态计算失败: {str(e)}")
                logger.warning(f"风控状态计算失败: {str(e)}")

            # 检查是否有数据被成功更新
            total_added = self.update_status['totalStats']['kline_added'] + self.update_status['totalStats']['fund_flow_added']
            total_updated = self.update_status['totalStats']['kline_updated'] + self.update_status['totalStats']['fund_flow_updated']
            total_success = total_added + total_updated
            total_failed = self.update_status['totalStats']['kline_failed'] + self.update_status['totalStats']['fund_flow_failed']

            # 更新任务状态
            with self.update_lock:
                if total_failed > 1000:
                    self.update_status['status'] = 'failed'
                    self.update_status['end_time'] = datetime.now().isoformat()
                    self.update_status['message'] = f'更新失败: 失败股票数量({total_failed})超过1000，请重新更新'
                    self.update_status['success'] = 0
                elif total_success > 0:
                    self.update_status['status'] = 'completed'
                    self.update_status['end_time'] = datetime.now().isoformat()
                    self.update_status['message'] = '更新完成'
                    self.update_status['success'] = 1
                else:
                    self.update_status['status'] = 'failed'
                    self.update_status['end_time'] = datetime.now().isoformat()
                    self.update_status['message'] = '更新失败: 没有数据被成功更新'

            if total_failed > 1000:
                self._add_update_log(f"✗ 更新任务失败: 失败股票数量({total_failed})超过1000")
                logger.warning(f"更新任务 {task_id} 失败: 失败股票数量({total_failed})超过1000")
            elif total_success > 0:
                self._add_update_log("✓ 更新任务完成")
                logger.info(f"更新任务 {task_id} 完成")
            else:
                self._add_update_log("✗ 更新任务失败: 没有数据被成功更新")
                logger.warning(f"更新任务 {task_id} 失败: 没有数据被成功更新")

            # 记录更新完成或失败
            if validator and target_date:
                try:
                    if total_failed <= 1000 and total_success > 0:
                        validator.record_update_complete(target_date, stats)
                    else:
                        if total_failed > 1000:
                            validator.record_update_failed(target_date, f'失败股票数量({total_failed})超过1000')
                        else:
                            validator.record_update_failed(target_date, '没有数据被成功更新')
                except Exception as log_e:
                    logger.error(f"记录更新状态失败: {str(log_e)}")

        except Exception as e:
            total_added = self.update_status['totalStats']['kline_added'] + self.update_status['totalStats']['fund_flow_added']
            total_updated = self.update_status['totalStats']['kline_updated'] + self.update_status['totalStats']['fund_flow_updated']
            total_success = total_added + total_updated
            total_failed = self.update_status['totalStats']['kline_failed'] + self.update_status['totalStats']['fund_flow_failed']

            with self.update_lock:
                if total_failed > 1000:
                    self.update_status['status'] = 'failed'
                    self.update_status['end_time'] = datetime.now().isoformat()
                    self.update_status['message'] = f'更新失败: 失败股票数量({total_failed})超过1000，请重新更新'
                    self.update_status['success'] = 0
                elif total_success > 0:
                    self.update_status['status'] = 'completed'
                    self.update_status['end_time'] = datetime.now().isoformat()
                    self.update_status['message'] = f'更新完成（部分步骤失败）: {str(e)}'
                    self.update_status['success'] = 1
                else:
                    self.update_status['status'] = 'failed'
                    self.update_status['end_time'] = datetime.now().isoformat()
                    self.update_status['message'] = f'更新失败: {str(e)}'

            if total_failed > 1000:
                self._add_update_log(f"✗ 更新任务失败: 失败股票数量({total_failed})超过1000")
                logger.warning(f"更新任务 {task_id} 失败: 失败股票数量({total_failed})超过1000")
            elif total_success > 0:
                self._add_update_log(f"✓ 更新任务完成（部分步骤失败）: {str(e)}")
                logger.warning(f"更新任务 {task_id} 完成（部分步骤失败）: {str(e)}")
            else:
                self._add_update_log(f"✗ 错误: {str(e)}")
                logger.error(f"更新任务 {task_id} 失败: {str(e)}")

            if validator and target_date:
                try:
                    if total_failed <= 1000 and total_success > 0:
                        validator.record_update_complete(target_date, stats)
                    else:
                        if total_failed > 1000:
                            validator.record_update_failed(target_date, f'失败股票数量({total_failed})超过1000')
                        else:
                            validator.record_update_failed(target_date, str(e))
                except Exception as log_e:
                    logger.error(f"记录更新状态失败: {str(log_e)}")

        finally:
            with self.update_lock:
                self.update_status['running'] = False

    def get_update_progress(self) -> Dict[str, Any]:
        """
        获取更新进度

        Returns:
            dict: 更新进度信息
        """
        elapsed_time = 0
        if self.update_status['start_time']:
            try:
                start = datetime.fromisoformat(self.update_status['start_time'])
                elapsed_time = int((datetime.now() - start).total_seconds())
            except Exception:
                elapsed_time = 0

        return {
            'running': self.update_status['running'],
            'status': self.update_status['status'],
            'message': self.update_status['message'],
            'startTime': self.update_status['start_time'],
            'endTime': self.update_status['end_time'],
            'elapsedTime': elapsed_time,
            'logs': self.update_status['logs'][-50:],
            'totalStats': self.update_status['totalStats']
        }

    def cancel_update(self) -> Dict[str, Any]:
        """
        取消更新任务

        Returns:
            dict: 取消结果
        """
        if not self.update_status['running'] and not self.update_status.get('paused', False):
            return {
                'success': False,
                'message': '没有正在运行的更新任务'
            }

        self.update_status['running'] = False
        self.update_status['paused'] = False
        self.update_status['message'] = '更新已取消'
        self.update_status['status'] = 'cancelled'
        self._add_update_log("✕ 更新任务已取消")
        logger.info("更新任务已取消")

        return {
            'success': True,
            'message': '更新任务已取消'
        }

    def _add_update_log(self, message: str):
        """
        添加更新日志

        Args:
            message: 日志消息
        """
        self.update_status['logs'].append(message)
        logger.info(f"[更新] {message}")


# 全局服务实例
_data_collection_service = None


def get_data_collection_service(data_dir: str = 'data') -> DataCollectionService:
    """
    获取数据采集服务实例（单例模式）

    Args:
        data_dir: 数据目录路径

    Returns:
        DataCollectionService: 数据采集服务实例
    """
    global _data_collection_service

    if _data_collection_service is None:
        _data_collection_service = DataCollectionService(data_dir)

    return _data_collection_service
