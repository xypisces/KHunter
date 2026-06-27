# Phase 2：中风险基础重构 PRD

## 概述

统一策略名称解析 + 删除 import * 转发层，消除重复映射和命名空间污染。

---

## 任务 4：统一策略名称解析

### 4.1 问题描述

当前存在三个独立的策略名称映射源，数据不一致：

| 来源 | 条目数 | 位置 |
|------|--------|------|
| `config/strategy_params.yaml` (display_name) | 19 | 策略配置文件 |
| `config/strategy_name_mapping.yaml` | 18 | 专用映射文件 |
| `trading/stock_score_models.py` (STRATEGY_CLASS_NAME_MAP) | 17 | 代码内硬编码 |

差异示例：
- `MultiGoldenCrossStrategy`: "多金叉共振" (mapping.yaml) vs "多金叉共振策略" (score_models)
- `StrongWashWeakToStrongStrategy`: "强势洗盘弱转强" (mapping.yaml) vs "强势洗盘弱转强策略" (score_models)
- `MTopStrategy`, `MultiDeathCrossStrategy` 只在 score_models 中存在

### 4.2 执行计划

**唯一真相源**：`config/strategy_params.yaml` 的 `display_name`

**迁移步骤**：

1. **更新 `utils/strategy_name_mapper.py`**：
   - 从 `StrategyRegistry` 的配置文件自动提取 `display_name` 映射
   - 删除 `_get_default_mapping()` 中的硬编码备用映射
   - 保留 `config/strategy_name_mapping.yaml` 作为缓存/备用，但自动生成

2. **删除 `trading/stock_score_models.py` 的 `STRATEGY_CLASS_NAME_MAP`**：
   - 移除整个字典定义（第 36-54 行）
   - 更新 `trading/technical_scorer.py`：用 `get_chinese_name()` 替换 4 处 `STRATEGY_CLASS_NAME_MAP.get()`
   - 更新 `trading/backtest_scorer.py`：用 `get_chinese_name()` 替换 3 处 `STRATEGY_CLASS_NAME_MAP.get()`

3. **统一配置文件 key 格式**：
   - 检查 `config/strategy_weights.json` 的 key 是否与 `strategy_params.yaml` 一致
   - 删除 `backtest_scorer.py` 和 `technical_scorer.py` 中的后缀匹配逻辑

### 4.3 验收标准

- [ ] `STRATEGY_CLASS_NAME_MAP` 已从 `stock_score_models.py` 删除
- [ ] `technical_scorer.py` 和 `backtest_scorer.py` 使用 `get_chinese_name()` 函数
- [ ] 后缀匹配逻辑已删除
- [ ] `uv run pyright` 零新增 errors
- [ ] 策略名称映射只有一个维护点（`config/strategy_params.yaml`）

---

## 任务 7：删除 7 个 import * 转发层

### 7.1 问题描述

7 个 shim 文件只是 `from xxx import *` 的转发，没有独有逻辑：

| Shim 文件 | 目标位置 | 消费者数 |
|-----------|---------|---------|
| `utils/stock_data_fetcher.py` | `utils/market_data/stock_fetcher.py` | 4 |
| `utils/kline_fetcher.py` | `utils/market_data/kline_fetcher.py` | 3 |
| `utils/fund_flow_fetcher.py` | `utils/fund_flow/fund_flow_fetcher.py` | 2 |
| `utils/index_data_fetcher.py` | `utils/market_data/index_fetcher.py` | 1 |
| `utils/industry_fetcher.py` | `utils/fundamental/industry_fetcher.py` | 1 |
| `utils/sector_fetcher.py` | `utils/fundamental/sector_fetcher.py` | 0 |
| `utils/event_fetcher.py` | `utils/event/event_fetcher.py` | 0 |

### 7.2 执行计划

**迁移消费者到子包位置，然后删除 shim 文件**：

1. **更新消费者导入路径**（共 11 处）：
   - `utils/akshare_fetcher.py`: stock_data_fetcher, kline_fetcher, fund_flow_fetcher
   - `utils/data_collection_service.py`: stock_data_fetcher, fund_flow_fetcher
   - `utils/exdividend_utils.py`: stock_data_fetcher
   - `utils/kline_updater.py`: kline_fetcher
   - `utils/risk_controller.py`: index_data_fetcher
   - `utils/selection_record_manager.py`: industry_fetcher
   - `trading/trading_core_mixin.py`: stock_data_fetcher, kline_fetcher

2. **删除 7 个 shim 文件**

3. **特殊处理**：
   - `stock_data_fetcher.py` 中的 `_tushare_limiter`, `_TushareRateLimiter` 导入是多余的（`fund_flow_fetcher.py` 已直接从源导入）
   - `sector_fetcher.py` 和 `event_fetcher.py` 零消费者，直接删除

### 7.3 验收标准

- [ ] 7 个 shim 文件已删除
- [ ] 所有消费者已更新到子包导入路径
- [ ] `uv run pyright` 零新增 errors
- [ ] `grep -rn "from utils.stock_data_fetcher\|from utils.kline_fetcher\|..."` 无结果

---

## 风险评估

| 任务 | 风险 | 缓解措施 |
|------|------|----------|
| 统一策略名称映射 | 🟡 中风险 | 涉及 5+ 文件，但逻辑简单 |
| 删除 import * 转发层 | 🟡 中风险 | 一次性导入路径迁移，需更新 11 处 |

## 实施顺序

### Commit 1：任务 4 - 统一策略名称解析
1. 更新 `utils/strategy_name_mapper.py` 从 strategy_params.yaml 提取映射
2. 删除 `STRATEGY_CLASS_NAME_MAP`
3. 更新 `technical_scorer.py` 使用 `get_chinese_name()`
4. 更新 `backtest_scorer.py` 使用 `get_chinese_name()`
5. 统一配置文件 key 格式，删除后缀匹配逻辑

### Commit 2：任务 7 - 删除 import * 转发层
1. 更新 11 处消费者导入路径
2. 删除 7 个 shim 文件
