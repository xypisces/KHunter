# PRD: 优化 StrategyRegistry 缓存机制

> **状态**: 已完成
> **创建日期**: 2026-06-27
> **涉及文件**: `strategy/strategy_registry.py`

---

## 问题陈述

当前 `StrategyRegistry` 的实现存在以下问题：

1. **重复文件 I/O**：每次调用 `get_strategy()` 都重新读取 `strategy_params.yaml` 文件
2. **重复对象实例化**：每次调用都创建新的策略实例，即使配置未变化
3. **代码重复**：`get_strategy()`、`run_strategy()`、`run_all()` 中存在相同的参数加载和实例化逻辑
4. **测试困难**：无法绕过文件系统进行单元测试

注意：策略对象本身是无状态的（纯函数式），因此"状态丢失"不是核心问题。

---

## 设计方案

### 1. 文件 mtime 检测

```python
class StrategyRegistry:
    def __init__(self):
        self._cache = {}           # {strategy_name: strategy_instance}
        self._params_mtime = 0.0   # params 文件的最后修改时间
        self._order_mtime = 0.0    # order 文件的最后修改时间
```

- 每次 `get_strategy()` 检查文件 mtime
- mtime 未变 → 返回缓存实例
- mtime 已变 → 重新加载参数并实例化

### 2. 缓存作用域

采用**实例级缓存**：
- 每个 `StrategyRegistry` 实例维护独立缓存
- 与当前单例模式兼容
- 支持测试时创建独立实例

### 3. 统一的实例化逻辑

提取私有方法 `_instantiate_strategy()`，统一处理：
- 参数加载
- 类型转换
- 实例创建
- 元数据复制

消除 `get_strategy()`、`run_strategy()`、`run_all()` 中的重复代码。

### 4. API 设计

```python
class StrategyRegistry:
    def get_strategy(self, name: str) -> Optional[BaseStrategy]:
        """获取策略实例（带缓存）"""

    def force_reload(self, name: Optional[str] = None) -> None:
        """强制重新加载指定策略或所有策略"""

    def clear_cache(self) -> None:
        """清空所有缓存"""
```

### 5. 测试支持

通过构造函数注入参数加载器：

```python
class StrategyRegistry:
    def __init__(self, params_file="config/strategy_params.yaml",
                 order_file="config/strategy_order.yaml",
                 params_loader=None):  # 新增：可注入的参数加载器
        self._params_loader = params_loader or self._default_params_loader
```

测试时可注入不读文件的 mock loader。

---

## 验收标准

- [x] 使用文件 mtime 检测变更
- [x] 文件未变时返回缓存实例（不重新读取 YAML）
- [x] 文件变更时自动重新加载
- [x] 提供 `force_reload()` 方法
- [x] 提供 `clear_cache()` 方法
- [x] 消除 `get_strategy()`、`run_strategy()`、`run_all()` 中的重复代码
- [x] 支持测试时注入不读文件的参数加载器
- [x] 保留热加载能力（文件修改后自动生效）
- [x] 通过 `uv run pyright strategy/strategy_registry.py` 类型检查

---

## 不在范围内

- 修改策略基类或具体策略实现
- 修改 `main.py` 或 `web_server.py` 的调用方式
- 添加策略状态保持功能（策略本身是无状态的）
