# 架构改进路线图

> 基于 2026-06-27 架构审查，按依赖关系和风险梯度排序。
> 详细报告：[architecture-review-20260627.html](./architecture-review-20260627.html)

## 执行顺序总览

```
Phase 1 ──→ Phase 2 ──→ Phase 3 ──→ Phase 4 ──→ Phase 5
低风险       中风险       中风险       中高风险     高风险
无依赖       依赖 P1      依赖 P1+2    无硬依赖     依赖全部
```

---

## Phase 1：零风险快速胜利

### #1 清理 5000+ 行死代码

- **风险**：🟢 零风险（删除后零运行时影响）
- **依赖**：无
- **文件**：`trading/routes.py` · `trading/strategy_runner_v2.py` · `trading/vectorbt_prototype.py` · `trading/vectorbt_demo.py` · `strategy/__init__.py`
- **动作**：`git rm` 这些文件，清理 `strategy/__init__.py` 的 STRATEGIES dict
- **收益**：搜索结果不再被死代码污染，目录结构真实反映运行时依赖

### #5 修复评分权重不一致

- **风险**：🟢 低风险（修正 docstring + 删除内联重复权重）
- **依赖**：无
- **文件**：`trading/stock_score_models.py` · `trading/backtest_scorer.py`
- **动作**：
  1. 修正 `StockScore` docstring 为实际权重 0.35/0.35/0.10/0.10/0.10
  2. `backtest_scorer.py` 统一从 `SCORE_WEIGHTS` 导入，删除内联权重
  3. 将 veto check 下沉到共享层
- **收益**：消除 docstring 与代码的不一致，backtest 和实盘评分逻辑统一

---

## Phase 2：中风险基础重构

### #4 统一策略名称解析

- **风险**：🟡 中风险（涉及 5+ 文件，但逻辑简单）
- **依赖**：Phase 1 完成（死代码清理后才能看清真实依赖）
- **文件**：`trading/stock_score_models.py` · `trading/technical_scorer.py` · `utils/strategy_name_mapper.py` · `trading/strategy_runner.py` · `trading/backtest_scorer.py`
- **动作**：
  1. 提升 `utils/strategy_name_mapper.py` 为唯一解析源
  2. 映射表从 `StrategyRegistry` 自动生成
  3. 删除各文件中的重复映射和后缀匹配逻辑
- **收益**：新增策略自动生效，无需手动更新 5 处映射

### #7 删除 7 个 import * 转发层

- **风险**：🟡 中风险（一次性导入路径迁移）
- **依赖**：Phase 1 完成（死代码清理后才能确认真实使用者）
- **文件**：`utils/stock_data_fetcher.py` · `utils/kline_fetcher.py` · `utils/fund_flow_fetcher.py` · `utils/industry_fetcher.py` · `utils/sector_fetcher.py` · `utils/event_fetcher.py` · `utils/index_data_fetcher.py`
- **动作**：
  1. 更新所有消费者导入路径到子包位置（`utils/market_data/` · `utils/fund_flow/` · `utils/fundamental/` · `utils/event/`）
  2. 删除 7 个 shim 文件
- **收益**：每个名字只有一个定义位置，消除 import * 的命名空间污染

---

## Phase 3：策略层统一

### #3 激活 indicators/ 模块

- **风险**：🟡 中风险（15+ 策略文件需逐个迁移，但每个策略独立）
- **依赖**：Phase 1 + Phase 2 完成（清理死代码和 shim 后，才能确认所有策略的真实导入路径）
- **文件**：`indicators/__init__.py` · `utils/technical.py` · `strategy/*.py`（15+ 文件）
- **动作**：
  1. 逐策略将 `from utils.technical import ...` 改为 `from indicators import ...`
  2. 在 `BaseStrategy.calculate_indicators()` 中明确合约：输入为升序 DataFrame
  3. 最后删除 `utils/technical.py` 的 deprecated 转发层
- **收益**：指标计算集中在一个模块，消除 15+ 策略中的排序方向隐式合约
- **注意**：与 ADR-0001 一致，可逐策略渐进迁移

---

## Phase 4：配置层统一

### #6 统一配置加载

- **风险**：🟠 中高风险（影响启动流程，多个消费者）
- **依赖**：无硬依赖，但 Phase 1 完成后更容易看清真实配置使用者
- **文件**：`config/` · `main.py` · `web/app_factory.py` · `trading/trading_core_mixin.py` · `web/routes/system.py`
- **动作**：
  1. 引入 `AppConfig` 单例，统一加载、验证和写回
  2. 所有模块通过同一接口访问配置
  3. 写操作通过 `set()` 方法，自动同步磁盘
- **收益**：配置加载集中在一个模块，消除 split-brain 问题

---

## Phase 5：核心逻辑重构

### #2 统一卖出逻辑

- **风险**：🔴 高风险（核心交易逻辑，必须保证回测和实盘行为一致）
- **依赖**：Phase 1-4 完成（代码库清理干净后才能安全重构核心逻辑）
- **文件**：`trading/backtest_engine.py` · `trading/strategy_runner.py` · `trading/trading_core_mixin.py`
- **动作**：
  1. 将 `_process_sell()` 和 `_execute_sell_operations()` 统一到 `TradingCoreMixin`
  2. 统一成本模型（当前两者已漂移）
  3. 通过测试验证回测和实盘行为一致
- **收益**：回测和实盘结果一致性得到保证，卖出逻辑集中在一个模块

### #8 拆解 DataCollectionService

- **风险**：🔴 高风险（53KB 上帝模块，复杂状态管理）
- **依赖**：Phase 1 + Phase 7（shim 清理后才能看清真实依赖图）
- **文件**：`utils/data_collection_service.py` · `utils/akshare_fetcher.py` · `utils/kline_updater.py` · `utils/fund_flow_updater.py`
- **动作**：
  1. 拆分为 `DataUpdateOrchestrator`（编排/进度/状态）+ 已有子模块
  2. 状态管理从 dict 散布改为集中管理
- **收益**：每个更新类型有自己的模块，可独立测试

---

## 依赖关系图

```
#1 死代码清理 ─────────────────────────────────────┐
#5 评分权重修复 ────────────────────────────────────┤
                                                   ↓
#4 策略名称统一 ←── 依赖 P1 ──→ #7 shim 清理 ←── 依赖 P1
         │                          │
         └──────────┬───────────────┘
                    ↓
           #3 indicators/ 迁移 ←── 依赖 P1+2
                    │
                    ↓
           #6 配置加载统一 ←── 无硬依赖，建议 P1 后
                    │
                    ↓
        #2 卖出逻辑统一 ←── 依赖全部
        #8 DataCollectionService ←── 依赖 P1+7
```

## 风险-收益矩阵

| 候选 | 风险 | 收益 | 建议时机 |
|------|------|------|----------|
| #1 死代码清理 | 🟢 零 | 中 | 立即 |
| #5 评分权重修复 | 🟢 低 | 中 | 立即 |
| #4 策略名称统一 | 🟡 中 | 高 | P1 后 |
| #7 shim 清理 | 🟡 中 | 中 | P1 后 |
| #3 indicators/ 迁移 | 🟡 中 | 高 | P2 后 |
| #6 配置加载统一 | 🟠 中高 | 中 | 随时 |
| #2 卖出逻辑统一 | 🔴 高 | 高 | 最后 |
| #8 DataCollectionService | 🔴 高 | 中 | 最后 |
