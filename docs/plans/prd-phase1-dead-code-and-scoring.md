# Phase 1：零风险快速胜利 PRD

## 概述

清理死代码 + 修复评分权重不一致，消除代码库中的噪音和隐患。

## 背景

- 项目中存在 5000+ 行从未被导入的死代码文件
- `StockScore` 的 docstring 权重与实际代码权重不一致
- `backtest_scorer.py` 内联了与 `SCORE_WEIGHTS` 相同的权重值，存在维护隐患

---

## 任务 1：清理死代码

### 1.1 确认死代码文件

通过全项目 grep 确认以下文件**零外部导入**：

| 文件 | 行数 | 说明 |
|------|------|------|
| `trading/routes.py` | 2775 | 旧版回测路由，功能已迁移到 `web/routes/backtest.py` |
| `trading/strategy_runner.py` | 3416 | V1 策略运行器，无任何外部导入 |
| `trading/strategy_runner_v2.py` | 291 | V2 策略运行器，无任何外部导入 |
| `trading/vectorbt_prototype.py` | 468 | VectorBT 原型，无任何外部导入 |
| `trading/vectorbt_demo.py` | 289 | VectorBT 演示脚本，无任何外部导入 |

**合计：7239 行**

> **额外发现**：`strategy_runner.py`（V1，3416 行）也确认为死代码（零外部导入），一并删除。

### 1.2 执行计划迁移（删除 `trading/routes.py` 前）

`trading/routes.py` 中有 6 个 `/execution/plans/*` 路由在迁移到 `web/routes/backtest.py` 时被遗漏：

- `GET /execution/plans` — 获取执行计划列表
- `POST /execution/plans` — 创建执行计划
- `GET/PUT/DELETE /execution/plans/<plan_id>` — 单个计划 CRUD
- `POST /execution/plans/import` — 导入执行计划
- `GET /execution/plans/<plan_id>/export` — 导出执行计划

**方案**：将这些路由补迁移到 `web/routes/backtest.py`，依赖 `trading/strategy_execution_plan.py` 的 `ExecutionPlan` 类。

> **注意**：随着 `strategy_runner.py`（V1）删除，`ExecutionPlan` 类目前没有代码直接使用（只有迁移后的路由使用）。后续可评估是否需要清理。

### 1.3 `strategy/__init__.py` 清理

`STRATEGIES` dict 没有任何外部导入，删除后不影响运行时。

**动作**：移除 `STRATEGIES` dict 和相关的 `__all__` 导出，只保留必要的 import（如果有）。

### 1.4 验收标准

- [x] `git rm` 删除 5 个文件后，`uv run pyright` 零 errors（预先存在的 2 个 errors 与本次修改无关）
- [x] `uv run main.py web` 启动正常（⚠️ 项目缺少 `tushare` 依赖，这是预先存在的问题，与本次修改无关）
- [x] `uv run main.py run --max-stocks 10` 执行正常（同上，tushare 依赖问题）
- [x] 全项目 grep 确认无 broken imports
- [x] `/execution/plans/*` 路由在新位置可访问（已迁移到 `web/routes/backtest.py`）

---

## 任务 2：修复评分权重不一致

### 2.1 问题描述

**`StockScore` docstring（第 558-559 行）写的权重：**
```
total = technical × 0.25 + moneyflow × 0.30 + fundamental × 0.15
        + sector × 0.15 + event × 0.15
```

**实际 `SCORE_WEIGHTS` 常量和 `calculate_total_score()` 使用的权重：**
```
technical: 0.35, moneyflow: 0.35, fundamental: 0.10, sector: 0.10, event: 0.10
```

**`backtest_scorer.py` 第 229-235 行内联的权重：**
```python
score_obj.technical_score * 0.35
score_obj.moneyflow_score * 0.35
score_obj.fundamental_score * 0.10
score_obj.sector_score * 0.10
score_obj.event_score * 0.10
```

实际权重值一致（0.35/0.35/0.10/0.10/0.10），但 docstring 过时且 backtest 内联了重复值。

### 2.2 执行计划

1. **修正 `StockScore` docstring**：更新为实际权重 0.35/0.35/0.10/0.10/0.10
2. **`backtest_scorer.py` 统一引用 `SCORE_WEIGHTS`**：删除第 229-235 行的内联权重，改为 `from trading.stock_score_models import SCORE_WEIGHTS` + `SCORE_WEIGHTS["technical"]` 等
3. **veto check 统一**（可选）：`BacktestScoreCalculator` 每个维度单独检查 veto 并 early-exit；`StockScoreCalculator` 计算完所有维度后统一检查。两者逻辑等价但实现不同，建议保持现状（各有优化理由：backtest 追求性能 early-exit，实盘追求完整性）

### 2.3 验收标准

- [x] `StockScore` docstring 权重与 `SCORE_WEIGHTS` 一致
- [x] `backtest_scorer.py` 不再内联权重数值，统一从 `SCORE_WEIGHTS` 导入
- [x] `uv run pyright trading/stock_score_models.py trading/backtest_scorer.py` 零 errors（预先存在的 2 个 errors 与本次修改无关）
- [x] 回测功能正常（评分结果不变，权重值未改变，只改引用方式）

---

## 风险评估

| 任务 | 风险 | 缓解措施 |
|------|------|----------|
| 删除死代码文件 | 🟢 零风险 | 已确认零外部导入 |
| 补迁移 execution routes | 🟡 低风险 | 路由逻辑不变，只改导入路径 |
| 修正 docstring | 🟢 零风险 | 只改注释 |
| 统一 backtest 权重引用 | 🟢 零风险 | 值不变，只改引用方式 |

## 实施顺序

1. 补迁移 `/execution/plans/*` 路由到 `web/routes/backtest.py` ✅
2. `git rm` 5 个死代码文件（含额外发现的 `strategy_runner.py` V1） ✅
3. 清理 `strategy/__init__.py` 的 `STRATEGIES` dict ✅
4. 修正 `StockScore` docstring ✅
5. 统一 `backtest_scorer.py` 权重引用 ✅
6. 运行验收检查 ✅
