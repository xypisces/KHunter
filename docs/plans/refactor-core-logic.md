# 核心逻辑重构 PRD

> **状态**: 待实施 | **优先级**: P0 | **创建日期**: 2026-06-27

---

## 背景

本 PRD 涵盖两个高风险重构任务，均涉及核心交易逻辑。

---

## 任务 #2：统一卖出逻辑

### 问题

回测引擎（`backtest_engine._process_sell`）和实盘组合管理器（`portfolio_manager._execute_sell`）的卖出逻辑已完全漂移：

| 方面 | 回测引擎 | 实盘组合管理器 |
|---|---|---|
| 成本模型 | 完整（佣金+过户费+印花税） | 无 |
| 止损/止盈 | 固定止损-6%，追踪止损，止盈21% | 无 |
| 部分卖出 | 支持 | 不支持 |
| 持仓过期 | 10天+收益率阈值 | 无 |
| 冷却池 | 连续亏损+单笔亏损冷却 | 无 |
| T+1 强制 | 有 | 无 |
| 交易记录 | 19 个字段 | 5 个字段 |

### 目标

将回测引擎的完整 5 层卖出决策提取到 `TradingCoreMixin`，让实盘获得同等风控能力。

### 设计决策

- **统一范围**：5 层卖出决策（T+1 → 止盈 → 止损/追踪止损 → 持仓过期 → 择时信号）全部统一
- **价格抽象**：`get_sell_price()` 方法由子类各自实现（回测用开盘价，实盘用实时价格）
- **文件更正**：实盘卖出逻辑在 `portfolio_manager.py`，非 `strategy_runner.py`

### 涉及文件

| # | 文件 | 改动 |
|---|---|---|
| 1 | `trading/trading_core_mixin.py` | 新增：`evaluate_sell_decision()`, `execute_sell()`, `get_sell_price()`（抽象）, `_create_sell_record()` |
| 2 | `trading/backtest_engine.py` | `_process_sell()` 改为调用 mixin 方法，实现 `get_sell_price()` 返回开盘价 |
| 3 | `trading/portfolio_manager.py` | `_execute_sell()` 改为调用 mixin 方法，实现 `get_sell_price()` 返回实时价格 |

### 统一卖出决策层次

```python
def evaluate_sell_decision(self, position, current_date, config) -> dict:
    """
    统一卖出决策（5 层）
    返回: {'action': 'hold'|'sell'|'reduce', 'reason': str, 'reduce_quantity': int}
    """
    # 1. T+1 门控
    # 2. 止盈检查
    # 3. 止损/追踪止损检查
    # 4. 持仓过期检查
    # 5. 择时策略信号
```

### 验收标准

- [ ] `TradingCoreMixin` 包含完整的 5 层卖出决策逻辑
- [ ] `backtest_engine._process_sell()` 调用 mixin 方法
- [ ] `portfolio_manager._execute_sell()` 调用 mixin 方法
- [ ] 回测结果与重构前一致（回归测试）
- [ ] 实盘卖出记录包含完整的成本信息（19 字段）

---

## 任务 #8：拆解 DataCollectionService

### 问题

`utils/data_collection_service.py`（1301 行）是上帝模块：
- 14 个方法（~500 行）无任何外部调用者（死代码）
- `_add_init_log` 重复定义（第 386 行和第 1259 行）
- `init_status` 和 `update_status` 是近乎相同的 dict 结构
- WebSocket 推送模式重复 8 次
- `_run_update()` 方法 434 行

### 目标

1. 删除死代码
2. 提取共享数据结构和辅助方法
3. 保持 `_run_update` 在原类中（不额外提取编排层）

### 设计决策

- **先删后改**：删除 14 个无调用者方法，再做结构优化
- **TaskStatus 数据类**：统一 init_status/update_status 的重复 dict
- **WebSocket 辅助**：消除 8 处重复的 try/except 模式
- **不提取编排层**：10 步中 8 步已委托给子模块，无需再加间接层

### 涉及文件

| # | 文件 | 改动 |
|---|---|---|
| 1 | `utils/data_collection_service.py` | 删除死代码，重构状态管理 |
| 2 | `utils/task_status.py`（新建） | `TaskStatus` 数据类 |

### 死代码删除清单（14 个方法）

| 方法 | 行数 | 原因 |
|---|---|---|
| `start_initialization` | ~45 | 0 外部调用 |
| `_run_initialization` | ~120 | 0 外部调用 |
| `get_init_progress` | ~25 | 0 外部调用 |
| `cancel_initialization` | ~10 | 0 外部调用 |
| `pause_initialization` | ~25 | 0 外部调用 |
| `resume_initialization` | ~25 | 0 外部调用 |
| `start_reinit` | ~40 | 0 外部调用 |
| `_run_reinit` | ~70 | 0 外部调用 |
| `_delete_all_data` | ~10 | 0 外部调用 |
| `get_init_config` | ~25 | 0 外部调用 |
| `get_update_config` | ~35 | 0 外部调用 |
| `check_data_completeness` | ~45 | 0 外部调用 |
| `get_data_status` | ~15 | 0 外部调用 |
| `update_task_stats` | ~20 | 0 外部调用 |

### TaskStatus 数据类设计

```python
@dataclass
class TaskStatus:
    """统一的任务状态跟踪"""
    running: bool = False
    paused: bool = False
    progress: int = 0
    total: int = 0
    current_task: str = ''
    success: int = 0
    failed: int = 0
    message: str = ''
    start_time: Optional[str] = None
    end_time: Optional[str] = None
    logs: list = field(default_factory=list)
    status: str = 'idle'  # idle|running|paused|completed|failed|cancelled

    def add_log(self, message: str): ...
    def to_dict(self) -> dict: ...
```

### 验收标准

- [ ] `data_collection_service.py` 从 1301 行减少到 ~700 行
- [ ] 0 个方法有重复定义
- [ ] `init_status` 和 `update_status` 使用 `TaskStatus` 数据类
- [ ] WebSocket 推送通过辅助方法调用，不再有 try/except 重复
- [ ] `start_update()` 和 `get_update_progress()` 功能不变

---

## 实施顺序

1. **#8 先行**：删除 DataCollectionService 死代码 + 提取 TaskStatus（低风险清理）
2. **#2 后行**：统一卖出逻辑（高风险核心重构）

---

## 风险与缓解

| 风险 | 影响 | 缓解 |
|---|---|---|
| 卖出逻辑统一后回测结果变化 | 🔴 高 | 重构前后运行相同回测，对比结果 |
| 实盘缺少卖出价格数据 | 🟡 中 | `get_sell_price()` 返回 0 时跳过卖出 |
| 删除死代码后功能缺失 | 🟢 低 | 已确认 0 外部调用，git 历史可恢复 |
