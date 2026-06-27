# PRD: 合并回测引擎与实盘运行器 — 提取 TradingCoreMixin

> **状态**: ✅ 已完成
> **优先级**: Strong
> **创建日期**: 2026-06-26

---

## 1. 问题

`BacktestEngine`（2504 行）和 `StrategyRunner`（4053 行）共享 ~15 个相同实例属性和 9 个同名方法，但实现已漂移：

| 漂移类型 | 示例 |
|---------|------|
| 参数顺序不同 | `_calculate_support_level`: `(stock, selection_date, strategy_name)` vs `(stock, strategy_name, current_date)` |
| 参数存在性不同 | `_check_pool_removal`: backtest 多一个未使用的 `config` 参数 |
| 数据模型不同 | 冷却池：backtest 用 `dict[str, date]`，runner 用池项上的 `is_cooling`/`cool_down_end` 属性 |
| 错误处理哲学不同 | `_load_pool_removal_config`: backtest 抛异常，runner 静默回退 |
| 外部依赖不同 | 交易日：backtest 内部实现，runner 调用 `trade_date_utils` |
| 默认值不同 | `fund_flow_min_hold_days`: backtest 默认 5，runner 默认 1 |
| 滑点支持不同 | 成本计算：backtest 无滑点，runner 有滑点 |

每次 bug 修复必须做两遍，且无测试覆盖。

---

## 2. 方案

提取 `TradingCoreMixin` 到 `trading/trading_core_mixin.py`，包含所有共享逻辑。`BacktestEngine` 和 `StrategyRunner` 各自只保留特有部分。

### 2.1 决策记录

| # | 决策 | 理由 |
|---|------|------|
| D1 | 类名 `TradingCoreMixin`，文件 `trading/trading_core_mixin.py` | 这些方法的核心目的是"执行交易"，数据获取只是支撑 |
| D2 | 错误处理采用回退策略（log warning + 默认值） | 实盘环境不应因配置缺失而崩溃；回测作为开发工具也应容忍 |
| D3 | 冷却池统一为 `dict[str, date]` 模型 | 更简洁、可测试；StrategyRunner 持久化层适配序列化/反序列化 |
| D4 | 移除 `_check_pool_removal` 的 `config` 参数 | backtest 中该参数未使用（vestigial） |
| D5 | 成本计算统一支持滑点，backtest 传入 `config=None` 时跳过 | 更通用；回测可选择性启用滑点 |
| D6 | 交易日逻辑统一使用 `utils/trade_date_utils` | 消除 backtest 的内部重复实现 |
| D7 | `fund_flow_min_hold_days` 默认值统一为 1 | 更保守（更早触发保护），且是 runner 的现有行为 |
| D8 | `_load_pool_removal_config` 使用类级缓存 | 两个引擎都需要，避免重复读文件 |

### 2.2 提取范围

**移入 `TradingCoreMixin` 的方法（9 个）：**

| 方法 | 来源 | 统一后签名 |
|------|------|-----------|
| `__init__` 共享部分 | 两者 | `__init__(self, db_path)` — 初始化 17 个共享属性 |
| `_load_support_methods_config` | 两者 | `-> Dict` — 功能一致，加类型注解 |
| `_get_support_method_for_strategy` | 两者 | `(strategy_name: str) -> str` — 功能一致 |
| `_load_pool_removal_config` | 两者 | `-> Dict` — 类级缓存 + 回退策略 |
| `_get_strategy_removal_config` | 两者 | `(strategy_name: str) -> Dict` — 回退而非抛异常 |
| `_calculate_support_level` | 两者 | `(stock: Dict, strategy_name: str, current_date: str) -> float` — 统一参数顺序 |
| `_check_pool_removal` | 两者 | `(current_date: str) -> List[Dict]` — 移除 config 参数 |
| `_check_fund_flow_condition` | 两者 | `(stock_code: str, stock_name: str, current_date: str) -> Dict` — 统一 3 参数 |
| `_check_cool_down` | 两者 | `(stock_code: str, current_date: str) -> bool` — 统一 dict 模型 |

**额外移入的辅助方法（3 个）：**

| 方法 | 说明 |
|------|------|
| `_get_support_method_for_strategy` | 支撑位方法查找 |
| `_update_stock_cool_down_status` | 冷却状态更新（原仅 runner，统一后两者都需要） |
| `_check_fund_flow_cool_down` | 从 `_check_fund_flow_condition` 中拆出的冷却逻辑 |

**保留在各引擎的方法：**

| 引擎 | 保留方法 | 说明 |
|------|---------|------|
| BacktestEngine | `_process_sell`, `run_backtest`, `_execute_buy_operations`, `_load_trading_calendar`, `_get_stock_price`, `_get_trading_dates`, `_get_previous_trading_day` | 回测循环特有 |
| StrategyRunner | `_execute_sell_operations`, `_execute_buy_operations`, `_process_ex_dividend`, `_save_running_state`, `_load_running_state` | 实盘持久化/除权除息特有 |

**模块级函数：**

| 函数 | 统一后 |
|------|--------|
| `calculate_cost(stock_code, price, quantity, is_buy, config=None)` | 放入 mixin 作为类方法；config=None 时使用硬编码费率（无滑点） |

### 2.3 `_check_cool_down` 统一模型

**统一为 dict 模型（backtest 风格）：**

```python
# TradingCoreMixin
self.loss_cool_down_pool = {}    # {stock_code: cool_down_end_date_str}
self.fund_flow_cool_down_pool = {}  # {stock_code: cool_down_end_date_str}
```

**StrategyRunner 持久化适配：**
- `_save_running_state`：将 `loss_cool_down_pool` 序列化到 JSON
- `_load_running_state`：从 JSON 反序列化到 dict
- 移除 `buy_candidate_pool` 项上的 `is_cooling`/`cool_down_end` 字段

### 2.4 继承结构

```
TradingCoreMixin (trading/trading_core_mixin.py)
├── 共享 __init__
├── 交易日历管理
├── 股价查询接口
├── 卖出处理接口
├── 池移除检查
├── 交易成本计算
├── 支撑位计算
├── 冷却池管理
└── 资金流向检查
        ↑               ↑
BacktestEngine      StrategyRunner
(回测特有逻辑)      (实盘特有逻辑)
```

---

## 3. 收益

- **Locality**：bug 修复集中在一处
- **Leverage**：一个接口，两个调用方
- 删除 ~800 行重复代码（保守估计）
- 统一行为：冷却池、成本计算、错误处理不再有两套逻辑
- 测试只需覆盖一个模块

---

## 4. 验收标准

- [x] `TradingCoreMixin` 包含所有 10 个共享方法（含 `_check_pool_removal`）
- [x] `BacktestEngine` 继承 `TradingCoreMixin`，只保留回测特有逻辑
- [x] `StrategyRunner` 继承 `TradingCoreMixin`，只保留实盘特有逻辑
- [x] 所有现有测试通过（114 passed）
- [x] 无重复代码（grep 确认 10 个方法均仅在 mixin 中定义）
- [x] `BacktestEngine()` 和 `StrategyRunner()` 的公共 API 不变
- [x] 冷却池统一为 dict 模型（`self.loss_cool_down_pool`）
- [x] 成本计算统一支持滑点，backtest 可选择性启用

---

## 5. 风险与缓解

| 风险 | 缓解 |
|------|------|
| 冷却池模型变更导致 StrategyRunner 状态丢失 | 实施前备份 `data/` 目录；实现双向兼容的加载逻辑 |
| 回测结果因行为统一而变化 | 记录变更前后的回测对比结果 |
| 无测试覆盖，回归风险高 | 实施后补充 mixin 的单元测试 |

---

## 6. 实施步骤

1. 创建 `trading/trading_core_mixin.py`，实现 `TradingCoreMixin`
2. 修改 `BacktestEngine` 继承 `TradingCoreMixin`，删除重复代码
3. 修改 `StrategyRunner` 继承 `TradingCoreMixin`，删除重复代码，适配冷却池模型
4. 运行测试验证
5. grep 确认无重复
