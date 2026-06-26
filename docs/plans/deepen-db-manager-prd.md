# PRD: 深化 DBManager — 分离通用与领域逻辑

> **状态**: ✅ 已完成
> **创建日期**: 2026-06-26
> **来源**: docs/tasks/candidate-06-deepen-db-manager.md

---

## 1. 背景与动机

`DBManager` 当前混合了两类职责：

1. **通用 SQLite 操作**：connect、execute、query、insert、update、delete、事务管理
2. **股票领域查询**：read_stock、write_stock、list_all_stocks、get_stock_name 等 9 个方法

这导致：
- 接口宽泛（~30 方法），调用方只需其中一小部分
- 股票 SQL 分散在 DBManager 中，难以定位和修改
- 单例在模块导入时立即创建（`global_db.py` 第 10 行），无法用内存 DB 替换做测试

---

## 2. 目标

将股票相关查询从 DBManager 提取到独立的 `StockRepo`，通过依赖注入获取 DBManager 实例。

**Before**:
```
调用方 → get_global_db() → DBManager（通用 + 股票）
```

**After**:
```
调用方 → get_stock_repo() → StockRepo（股票查询）
                ↓
            DBManager（通用操作）
                ↓
              SQLite
```

---

## 3. 设计决策

### 3.1 StockRepo 位置

`utils/stock_repo.py`

理由：stock_kline/stock_basic 是基础数据层，被 main.py、web_server.py、strategy/、trading/ 多处引用，不是 trading 模块独有的。

### 3.2 方法边界

StockRepo 包含 DBManager 上全部 9 个股票相关方法：

| 方法 | 查询的表 | 返回类型 |
|---|---|---|
| `read_stock` | stock_kline | DataFrame |
| `write_stock` | stock_kline | bool |
| `update_stock` | stock_kline | bool |
| `list_all_stocks` | stock_kline | List[str] |
| `stock_exists` | stock_kline | bool |
| `get_stock_count` | stock_kline | int |
| `get_latest_trading_date` | stock_kline | str |
| `get_stock_name` | stock_basic | str |
| `get_all_stock_names` | stock_basic | dict |

stock_basic 和 stock_kline 同属"股票基础数据"聚合根，对外统一接口。

### 3.3 获取方式

新增 `get_stock_repo()` 单例函数（在 `utils/global_db.py` 中），延迟初始化：

```python
def get_stock_repo():
    global _stock_repo
    if _stock_repo is None:
        _stock_repo = StockRepo(get_global_db())
    return _stock_repo
```

### 3.4 迁移策略

一个 PR 完成全部迁移：
1. 创建 `utils/stock_repo.py`，实现 StockRepo
2. 在 `utils/global_db.py` 添加 `get_stock_repo()`
3. 迁移所有 47+ 处调用方
4. DBManager 上旧方法标 deprecated，内部委托给 StockRepo

### 3.5 Deprecation 策略

DBManager 上的旧方法保留，添加 `warnings.warn(..., DeprecationWarning)`，内部委托给 StockRepo。后续版本再删除。

### 3.6 测试策略

为 StockRepo 编写单元测试，使用内存 SQLite（`:memory:`），覆盖全部 9 个公共方法。

---

## 4. 调用方影响分析

### 需要迁移的文件（使用股票相关方法）

| 文件 | 使用的方法 |
|---|---|
| `stock_analyzer/data_fetcher.py` | read_stock, update_stock |
| `utils/kline_chart_fast.py` | read_stock |
| `utils/ranking_manager.py` | read_stock |
| `utils/selection_record_manager.py` | read_stock |
| `utils/new_stock_detector.py` | list_all_stocks |
| `web_server.py` | read_stock, list_all_stocks, get_all_stock_names |
| `main.py` | list_all_stocks, read_stock, get_all_stock_names |
| `trading/strategy_runner.py` | list_all_stocks, read_stock |
| `trading/backtest_engine.py` | list_all_stocks, read_stock |
| `trading/vectorbt_backtest_engine.py` | read_stock, list_all_stocks |
| `trading/vectorbt_prototype.py` | read_stock |
| `strategy/immortal_guidance_strategy.py` | get_latest_trading_date |
| `strategy/pattern_library.py` | read_stock |

### 不需要迁移的文件

`trading/` 下的 7 个 DAO（stock_score_dao、khunter_dao 等）已经通过 DBManager 的通用方法（query、insert、transaction）操作各自的领域表，不使用股票相关方法，无需迁移。

---

## 5. 验收标准

- [x] DBManager 只保留通用操作（connect/execute/query/insert/update/delete/事务管理）
- [x] 股票查询在 `utils/stock_repo.py` 的 StockRepo 中
- [x] `utils/global_db.py` 提供 `get_stock_repo()` 延迟初始化单例
- [x] 47+ 处调用迁移到 StockRepo
- [x] DBManager 上旧方法标 deprecated（委托给 StockRepo）
- [x] StockRepo 可用内存 DB 测试（23 个单元测试全部通过）
- [x] 所有现有测试通过（114/114）
- [x] 模块导入正常验证

---

## 6. 实施步骤

1. 创建 `utils/stock_repo.py`，实现 StockRepo 类（9 个方法）
2. 修改 `utils/global_db.py`，添加 `get_stock_repo()`
3. DBManager 上 9 个旧方法改为 deprecated 委托
4. 逐文件迁移调用方（按模块分批）
5. 编写 StockRepo 单元测试
6. 验证：运行测试 + 启动 Web 服务器
