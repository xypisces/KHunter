# 策略层迁移至 indicators/ 模块 PRD

> **状态**: 待实施 | **优先级**: P1 | **创建日期**: 2026-06-27
> **依赖**: Phase 1（死代码清理）+ Phase 2（shim 清理）完成

---

## 背景

`indicators/` 模块已建立为技术指标的唯一规范实现（参见 ADR-0001 和 `unify-technical-indicators.md`），但 7 个策略文件和 1 个 web 路由仍在通过 `utils/technical.py` 这个 deprecated shim 调用指标函数。需要完成最后一步迁移，然后删除 shim 层。

当前 `utils/technical.py` 与 `indicators/` 的关键差异：

| 方面 | `indicators/`（规范） | `utils/technical.py`（shim） |
|---|---|---|
| 命名 | 小写 `ma`, `kdj`, `rsi` | 大写 `MA`, `KDJ`, `RSI` |
| 返回值 | 原始 Series/tuple | 包装为 DataFrame |
| 排序处理 | 自动检测并适配 | 同（委托给 indicators） |
| 独有函数 | 无 | `FINANCE`, `calculate_zhixing_trend`, `calculate_price_change`, `calculate_daily_return`, `calculate_intraday_return` |

---

## 目标

1. 将所有策略文件的指标导入从 `utils.technical` 迁移到 `indicators`
2. 将 `utils/technical.py` 中 3 个被实际使用的函数迁移到 `indicators/`
3. 删除 `utils/technical.py`
4. 在 `BaseStrategy.calculate_indicators()` 中明确排序方向合约

---

## 设计决策

### D1: 未迁移函数的归属

将以下 3 个函数迁移到 `indicators/`（被策略文件实际使用）：
- `calculate_zhixing_trend` → `indicators/trend.py`（新文件）
- `calculate_price_change` → `indicators/returns.py`（新文件）
- `calculate_daily_return` → `indicators/returns.py`（作为 `calculate_price_change` 的便捷封装）

以下 2 个函数**无任何外部调用者**，随 `utils/technical.py` 一起删除：
- `FINANCE` — 无策略使用
- `calculate_intraday_return` — 无策略使用

### D2: 排序方向合约

`calculate_indicators()` 的输入合约为**倒序（最新在前）**，与 `BaseStrategy` 其他方法一致。`indicators/` 内部通过 `ensure_ascending()` 自动处理方向转换，调用方无需关心。

### D3: 命名规范

迁移后统一使用 `indicators/` 的小写命名：`ma`, `ema`, `kdj`, `rsi`, `macd`, `llv`, `hhv`, `ref`。

### D4: 返回值适配

`indicators/` 返回原始 tuple（如 `kdj()` 返回 `(K, D, J)`），策略代码需适配解包方式。原 `utils/technical.py` 的 `KDJ()` 返回 DataFrame 的包装不再存在。

### D5: 迁移方式

一次性批量迁移 8 个文件，每个文件独立改动，可逐文件验证。迁移完成后删除 `utils/technical.py`。

---

## 涉及文件清单

### 新建文件（2 个）

| 文件 | 内容 |
|---|---|
| `indicators/trend.py` | `calculate_zhixing_trend()` — 知行趋势指标 |
| `indicators/returns.py` | `calculate_price_change()`, `calculate_daily_return()` |

### 修改文件（9 个）

| # | 文件 | 改动 |
|---|---|---|
| 1 | `indicators/__init__.py` | 导出新增的 3 个函数 |
| 2 | `strategy/base_strategy.py` | `calculate_indicators()` docstring 明确倒序合约 |
| 3 | `strategy/w_bottom_strategy.py` | `from utils.technical import MA, KDJ, EMA, LLV, calculate_zhixing_trend` → `from indicators import ...` |
| 4 | `strategy/trend_resonance_reversal.py` | `from utils.technical import MA, MACD, RSI` → `from indicators import ...` |
| 5 | `strategy/morning_star.py` | `from utils.technical import calculate_daily_return` → `from indicators import ...` |
| 6 | `strategy/trend_acceleration_inflection.py` | `from utils.technical import MA, EMA, KDJ, calculate_zhixing_trend` → `from indicators import ...` |
| 7 | `strategy/multi_party_cannon.py` | `from utils.technical import REF, MA, KDJ, calculate_daily_return, calculate_zhixing_trend` → `from indicators import ...` |
| 8 | `strategy/pattern_feature_extractor.py` | `from utils.technical import MA, EMA, KDJ, REF, LLV, HHV, calculate_zhixing_trend` → `from indicators import ...` |
| 9 | `web/routes/stocks.py` | `from utils.technical import KDJ` → `from indicators import kdj` |

### 删除文件（1 个）

| 文件 | 原因 |
|---|---|
| `utils/technical.py` | 所有调用方已迁移，shim 层不再需要 |

---

## 返回值适配详情

迁移时需注意以下返回值变化：

| 函数 | `utils/technical.py` 返回 | `indicators/` 返回 | 适配方式 |
|---|---|---|---|
| `KDJ` / `kdj` | DataFrame(columns=['K','D','J']) | `(K, D, J)` tuple | 解包：`k, d, j = kdj(df)` |
| `MACD` / `macd` | DataFrame(columns=['DIF','DEA','MACD']) | `(DIF, DEA, MACD)` tuple | 解包：`dif, dea, macd_val = macd(df)` |
| `RSI` / `rsi` | Series（无变化） | Series（无变化） | 仅改名 |
| `MA` / `ma` | Series（无变化） | Series（无变化） | 仅改名 |
| `EMA` / `ema` | Series（无变化） | Series（无变化） | 仅改名 |
| `LLV` / `llv` | Series（无变化） | Series（无变化） | 仅改名 |
| `HHV` / `hhv` | Series（无变化） | Series（无变化） | 仅改名 |
| `REF` / `ref` | Series（无变化） | Series（无变化） | 仅改名 |

---

## 实施步骤

### Step 1: 迁移函数到 indicators/

1. 创建 `indicators/trend.py`，从 `utils/technical.py` 迁移 `calculate_zhixing_trend`
2. 创建 `indicators/returns.py`，从 `utils/technical.py` 迁移 `calculate_price_change` 和 `calculate_daily_return`
3. 更新 `indicators/__init__.py` 导出新函数

### Step 2: 更新 BaseStrategy 合约

4. 更新 `strategy/base_strategy.py` 的 `calculate_indicators()` docstring，明确输入为倒序 DataFrame

### Step 3: 逐策略迁移（7 个文件）

5. `strategy/trend_resonance_reversal.py` — 最简单，仅 MA/MACD/RSI
6. `strategy/morning_star.py` — 仅 calculate_daily_return
7. `strategy/trend_acceleration_inflection.py` — MA/EMA/KDJ/calculate_zhixing_trend
8. `strategy/w_bottom_strategy.py` — MA/KDJ/EMA/LLV/calculate_zhixing_trend（含方法内局部导入）
9. `strategy/multi_party_cannon.py` — REF/MA/KDJ/calculate_daily_return/calculate_zhixing_trend（含方法内局部导入）
10. `strategy/pattern_feature_extractor.py` — MA/EMA/KDJ/REF/LLV/HHV/calculate_zhixing_trend
11. `web/routes/stocks.py` — KDJ → kdj

### Step 4: 删除 shim

12. 删除 `utils/technical.py`
13. 全局搜索确认无残留引用

### Step 5: 验证

14. `uv run pyright` 检查所有修改文件
15. `uv run main.py run --max-stocks 10` 验证端到端流程

---

## 风险与缓解

| 风险 | 影响 | 缓解 |
|---|---|---|
| KDJ/MACD 返回值类型变化导致策略逻辑错误 | 🟡 中 | 逐文件迁移 + pyright 检查 + 端到端测试 |
| `calculate_zhixing_trend` 迁移后行为不一致 | 🟡 中 | 从 shim 中直接搬运实现，保持算法不变 |
| 方法内局部导入遗漏 | 🟢 低 | grep 全局搜索确认 |

---

## 验收标准

- [ ] 0 个文件引用 `utils.technical`
- [ ] `utils/technical.py` 已删除
- [ ] `indicators/__init__.py` 导出 `calculate_zhixing_trend`, `calculate_price_change`, `calculate_daily_return`
- [ ] `uv run pyright` 对所有修改文件 0 errors
- [ ] `uv run main.py run --max-stocks 10` 正常运行
