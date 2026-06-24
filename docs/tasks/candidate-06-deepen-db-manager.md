# Candidate 6: 深化 DBManager — 分离通用与领域逻辑

> **优先级**: Worth exploring  \
> **涉及文件**: utils/db_manager.py, utils/global_db.py, data/stock_repo.py (新)

---

## Before — 浅层：接口 ≈ 实现

DBManager 混合了通用 SQLite 操作和股票领域查询。47+ 处调用 `get_global_db()` 直接使用领域方法，接口宽泛。

```
DBManager 接口：
├── connect / execute / insert / update / delete / query
└── read_stock / write_stock / list_all_stocks / get_stock_name ...

实现：
├── SQLite 连接池
├── 事务管理
├── stock_kline SQL
└── stock_basic SQL

两层职责混在一个接口中
```

---

## After — 深层：窄接口，厚实现

DBManager 只保留通用数据库操作。股票相关查询提取到 `StockRepo`，通过构造函数注入 DBManager。

```
StockRepo (深层: read/write/list)
    ↓
DBManager (薄: connect/execute)
    ↓
SQLite

其他 Repo (未来扩展)
    ↓
DBManager
```

---

## 问题

DBManager 混合了通用 SQLite 操作和股票领域查询。47+ 处调用 `get_global_db()` 直接使用领域方法，接口宽泛。单例在导入时创建，无法测试替换。

---

## 方案

DBManager 只保留通用数据库操作。股票相关查询提取到 `StockRepo`，通过构造函数注入 DBManager。单例改为延迟初始化。

---

## 收益

- DBManager 接口从 ~30 方法缩减到 ~10
- StockRepo 可用内存 DB 测试
- **locality**：股票 SQL 集中一处
- 未来可扩展其他 Repo

---

## 验收标准

- [ ] DBManager 只保留通用操作（connect/execute/query）
- [ ] 股票查询在 StockRepo 中
- [ ] 单例改为延迟初始化
- [ ] 47+ 处调用迁移到 StockRepo
- [ ] StockRepo 可用内存 DB 测试
