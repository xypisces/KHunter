"""
策略注册器 - 支持动态加载策略，带文件 mtime 缓存
"""
import importlib
import sys
from pathlib import Path
from typing import Any, Callable, Optional
import yaml
from utils.feature_config_checker import FeatureConfigChecker


class StrategyRegistry:
    """策略注册器（带 mtime 缓存）"""

    def __init__(
        self,
        params_file: str = "config/strategy_params.yaml",
        order_file: str = "config/strategy_order.yaml",
        params_loader: Optional[Callable[[str], dict[str, Any]]] = None,
    ):
        """
        初始化策略注册器

        :param params_file: 策略参数配置文件路径
        :param order_file: 策略排序配置文件路径
        :param params_loader: 可选的参数加载器（测试注入用），
                              接收文件路径，返回解析后的 dict
        """
        self.strategies: dict[str, Any] = {}
        self.display_name_map: dict[str, str] = {}
        self.params_file = Path(params_file)
        self.order_file = Path(order_file)

        # 缓存相关
        self._cache: dict[str, Any] = {}  # {strategy_name: strategy_instance}
        self._params_mtime: float = 0.0
        self._order_mtime: float = 0.0

        # 参数加载器（支持测试注入）
        self._params_loader = params_loader or self._default_params_loader

        # 初始加载
        self.params = self._load_params()
        self.strategy_order = self._load_strategy_order()

    # ── 文件 I/O ──────────────────────────────────────────────

    @staticmethod
    def _default_params_loader(file_path: str) -> dict[str, Any]:
        """默认参数加载器：从 YAML 文件读取"""
        with open(file_path, "r", encoding="utf-8") as f:
            return yaml.safe_load(f) or {}

    def _get_file_mtime(self, path: Path) -> float:
        """获取文件修改时间，不存在则返回 0"""
        return path.stat().st_mtime if path.exists() else 0.0

    def _needs_reload(self) -> bool:
        """检查文件是否已变更"""
        params_mtime = self._get_file_mtime(self.params_file)
        order_mtime = self._get_file_mtime(self.order_file)
        return params_mtime != self._params_mtime or order_mtime != self._order_mtime

    def _load_params(self) -> dict[str, Any]:
        """加载策略参数配置"""
        self._params_mtime = self._get_file_mtime(self.params_file)
        if self.params_file.exists():
            return self._params_loader(str(self.params_file))
        return {}

    def _load_strategy_order(self) -> dict[str, int]:
        """加载策略排序配置"""
        self._order_mtime = self._get_file_mtime(self.order_file)
        if not self.order_file.exists():
            return {}
        try:
            with open(self.order_file, "r", encoding="utf-8") as f:
                config = yaml.safe_load(f) or {}
                order_map: dict[str, int] = {}
                for item in config.get("strategy_order", []):
                    order_map[item["name"]] = item["order"]
                return order_map
        except Exception as e:
            print(f"[WARNING] 加载策略排序配置失败: {e}")
            return {}

    # ── 参数类型转换 ──────────────────────────────────────────

    def _convert_param_types(self, params: dict[str, Any], strategy_name: str) -> dict[str, Any]:
        """
        转换参数类型，确保配置文件中的字符串格式正确转换为 Python 类型
        """
        if not params:
            return {}
        converted: dict[str, Any] = {}
        for key, value in params.items():
            if key == "ma_periods" and value is not None:
                converted[key] = self._parse_ma_periods(value)
            elif key == "volume_ratio_max" and value == "null":
                converted[key] = None
            else:
                converted[key] = value
        return converted

    def _parse_ma_periods(self, value: Any) -> list[int]:
        """解析 ma_periods 参数，支持多种格式"""
        if isinstance(value, list):
            return value
        if isinstance(value, str):
            value = value.strip()
            if value.startswith("[") and value.endswith("]"):
                value = value[1:-1]
            parts = [p.strip() for p in value.split(",")]
            return [int(p) for p in parts if p]
        return value  # type: ignore[return-value]

    # ── 策略实例化（统一逻辑）────────────────────────────────

    def _get_strategy_params(self, strategy_name: str) -> dict[str, Any]:
        """从配置中获取指定策略的参数（使用当前已加载的 self.params）"""
        strategies_config = self.params.get("strategies", {})
        strategy_config = strategies_config.get(strategy_name, {})
        params = strategy_config.get("params", {})
        return self._convert_param_types(params, strategy_name)

    def _instantiate_strategy(
        self, strategy_class: type, strategy_name: str, params: dict[str, Any]
    ) -> Any:
        """
        统一的策略实例化逻辑：创建实例 + 复制元数据

        :param strategy_class: 策略类
        :param strategy_name: 策略名称
        :param params: 策略参数
        :return: 策略实例
        """
        strategy = strategy_class(params=params)

        # 如果缓存中有旧实例，复制元数据
        old = self._cache.get(strategy_name)
        if old is not None:
            strategy.metadata = getattr(old, "metadata", {})
            strategy.param_groups = getattr(old, "param_groups", [])
            strategy.param_details = getattr(old, "param_details", {})

        return strategy

    def _refresh_cache_if_needed(self) -> None:
        """如果文件已变更，重新加载参数并刷新所有缓存实例"""
        if not self._needs_reload():
            return

        # 重新加载配置文件
        self.params = self._load_params()
        self.strategy_order = self._load_strategy_order()

        # 重建所有缓存实例
        for name, old_instance in list(self._cache.items()):
            strategy_class = type(old_instance)
            params = self._get_strategy_params(name)
            self._cache[name] = self._instantiate_strategy(strategy_class, name, params)
            # 同步到 strategies 字典
            self.strategies[name] = self._cache[name]

    # ── 公开 API ─────────────────────────────────────────────

    def register(self, strategy_class: type, name: Optional[str] = None) -> Any:
        """
        注册策略

        :param strategy_class: 策略类
        :param name: 策略名称（默认使用类名）
        """
        strategy_name = name or strategy_class.__name__

        # 获取该策略的配置
        strategies_config = self.params.get("strategies", {})
        strategy_config = strategies_config.get(strategy_name, {})

        # 元数据字段
        metadata_fields = {"display_name", "description", "icon", "color"}

        # 提取参数值
        params = strategy_config.get("params", {})
        params = self._convert_param_types(params, strategy_name)

        # 实例化策略
        strategy = strategy_class(params=params)

        # 存储元数据
        strategy.metadata = {k: strategy_config.get(k) for k in metadata_fields if k in strategy_config}
        strategy.param_groups = strategy_config.get("param_groups", [])
        strategy.param_details = strategy_config.get("param_details", {})

        # 同步到缓存和 strategies 字典
        self._cache[strategy_name] = strategy
        self.strategies[strategy_name] = strategy

        return strategy

    def get_strategy(self, name: str) -> Optional[Any]:
        """
        获取策略实例（带 mtime 缓存）

        文件未变时返回缓存实例，文件已变时自动重新加载。

        :param name: 策略名称
        :return: 策略实例，未注册时返回 None
        """
        if name not in self.strategies:
            return None

        # 检查文件是否变更
        self._refresh_cache_if_needed()

        return self._cache.get(name)

    def force_reload(self, name: Optional[str] = None) -> None:
        """
        强制重新加载策略（忽略缓存）

        :param name: 指定策略名称，None 表示重新加载所有策略
        """
        # 强制刷新配置文件
        self.params = self._load_params()
        self.strategy_order = self._load_strategy_order()

        if name is not None:
            # 重新加载单个策略
            if name in self.strategies:
                strategy_class = type(self.strategies[name])
                params = self._get_strategy_params(name)
                self._cache[name] = self._instantiate_strategy(strategy_class, name, params)
                self.strategies[name] = self._cache[name]
        else:
            # 重新加载所有策略
            for strategy_name, old_instance in list(self._cache.items()):
                strategy_class = type(old_instance)
                params = self._get_strategy_params(strategy_name)
                self._cache[strategy_name] = self._instantiate_strategy(
                    strategy_class, strategy_name, params
                )
                self.strategies[strategy_name] = self._cache[strategy_name]

    def clear_cache(self) -> None:
        """清空所有缓存（下次 get_strategy 会重新实例化）"""
        self._cache.clear()
        self._params_mtime = 0.0
        self._order_mtime = 0.0

    def list_strategies(self) -> list[str]:
        """列出所有已注册的策略（按排序顺序）"""
        if self.strategy_order:
            return sorted(
                self.strategies.keys(),
                key=lambda x: self.strategy_order.get(x, float("inf")),
            )
        return list(self.strategies.keys())

    def auto_register_from_directory(self, strategy_dir: str = "strategy") -> None:
        """
        自动从目录加载策略

        导入所有非 _ 开头的 .py 文件。
        注意：择时策略不在此注册，选股策略不需要配置文件检查。
        """
        strategy_path = Path(strategy_dir)
        if not strategy_path.exists():
            strategy_path = Path(__file__).parent

        # 添加策略目录到路径
        if str(strategy_path) not in sys.path:
            sys.path.insert(0, str(strategy_path))

        # 遍历策略文件
        for py_file in strategy_path.glob("*.py"):
            if py_file.name.startswith("_"):
                continue

            module_name = py_file.stem

            try:
                # 动态导入模块
                if module_name in sys.modules:
                    module = sys.modules[module_name]
                else:
                    module = importlib.import_module(module_name)

                # 查找策略类
                from strategy.base_strategy import BaseStrategy

                for attr_name in dir(module):
                    attr = getattr(module, attr_name)
                    if (
                        isinstance(attr, type)
                        and issubclass(attr, BaseStrategy)
                        and attr is not BaseStrategy
                    ):
                        strategy_class_name = attr.__name__

                        # 跳过事件驱动策略
                        strategy_instance = attr()  # type: ignore[call-arg]
                        if strategy_instance.name == "事件驱动策略":
                            print(f"  [SKIP] 跳过策略: {strategy_instance.name}")
                            continue

                        # 注册策略
                        self.register(attr, name=strategy_class_name)
                        print(
                            f"  [OK] 注册策略: {strategy_instance.name} (类名: {strategy_class_name})"
                        )

            except Exception as e:
                print(f"  [ERROR] 加载 {module_name} 失败: {e}")
                import traceback

                traceback.print_exc()

    def run_strategy(self, strategy_name: str, stock_data_dict: dict) -> dict:
        """
        运行单个策略

        :param strategy_name: 策略名称
        :param stock_data_dict: {code: (name, df)} 格式的股票数据
        :return: {strategy_name: [signals]} 格式的结果
        """
        if strategy_name not in self.strategies:
            return {}

        # 获取策略实例（自动处理缓存）
        strategy = self.get_strategy(strategy_name)
        if not strategy:
            return {}

        total_stocks = len(stock_data_dict)

        # 展示选股条件
        print(f"\n{'=' * 80}")
        print(f"执行策略: {strategy_name}")
        print(f"{'=' * 80}")

        criteria = strategy.get_selection_criteria()
        if criteria:
            print("\n选股条件:")
            for criterion in criteria:
                print(f"  {criterion}")
        else:
            print("\n选股条件: 未定义")

        print(f"\n共 {total_stocks} 只股票待分析...")
        print(f"{'-' * 80}")

        signals: list[dict] = []
        processed = 0

        for code, (name, df) in stock_data_dict.items():
            result = strategy.analyze_stock(code, name, df)
            if result:
                signals.append(result)

            processed += 1
            if processed % 100 == 0 or processed == total_stocks:
                print(f"  进度: [{processed}/{total_stocks}] 已分析 {processed} 只，选出 {len(signals)} 只...")

        print(f"{'-' * 80}")
        print(f"✓ 选股完成: 共 {len(signals)} 只股票符合策略")
        print(f"{'=' * 80}\n")

        return {strategy_name: signals}

    def run_all(
        self, stock_data_dict: dict, return_indicators: bool = False
    ) -> dict | tuple[dict, dict]:
        """
        运行所有策略（按排序顺序）

        :param stock_data_dict: {code: (name, df)} 格式的股票数据
        :param return_indicators: 是否返回计算了指标的数据
        :return: {strategy_name: [signals]} 格式的结果，或 (results, indicators_dict)
        """
        results: dict[str, list] = {}
        indicators_dict: dict[str, Any] = {}
        total_stocks = len(stock_data_dict)

        strategy_names = self.list_strategies()

        for strategy_name in strategy_names:
            # 获取策略实例（自动处理缓存）
            strategy = self.get_strategy(strategy_name)
            if not strategy:
                continue

            print(f"\n{'=' * 80}")
            print(f"执行策略: {strategy_name}")
            print(f"{'=' * 80}")

            criteria = strategy.get_selection_criteria()
            if criteria:
                print("\n选股条件:")
                for criterion in criteria:
                    print(f"  {criterion}")
            else:
                print("\n选股条件: 未定义")

            print(f"\n共 {total_stocks} 只股票待分析...")
            print(f"{'-' * 80}")

            signals: list[dict] = []
            processed = 0

            for code, (name, df) in stock_data_dict.items():
                if return_indicators:
                    df_with_indicators = strategy.calculate_indicators(df)
                    indicators_dict[code] = df_with_indicators
                    result = strategy.select_stocks(df_with_indicators, name)
                    if result:
                        signals.append({"code": code, "name": name, "signals": result})
                else:
                    result = strategy.analyze_stock(code, name, df)
                    if result:
                        signals.append(result)

                processed += 1
                if processed % 100 == 0 or processed == total_stocks:
                    print(f"  进度: [{processed}/{total_stocks}] 已分析 {processed} 只，选出 {len(signals)} 只...")

            results[strategy_name] = signals

            print(f"{'-' * 80}")
            print(f"✓ 选股完成: 共 {len(signals)} 只股票符合策略")
            print(f"{'=' * 80}\n")

        if return_indicators:
            return results, indicators_dict
        return results


# 全局注册器实例
_registry: Optional[StrategyRegistry] = None


def get_registry(
    params_file: str = "config/strategy_params.yaml",
    order_file: str = "config/strategy_order.yaml",
) -> StrategyRegistry:
    """获取全局策略注册器"""
    global _registry
    if _registry is None:
        _registry = StrategyRegistry(params_file, order_file)
    return _registry
