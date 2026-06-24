# Candidate 7: 拆分 trading/routes.py 路由模块

> **优先级**: Worth exploring  \
> **涉及文件**: trading/routes.py, trading/routes/backtest.py (新), trading/routes/khunter.py (新)

---

## Before — 两个 Blueprint 共享初始化

回测和狩猎场是不同领域，却共享模块级初始化。修改狩猎场路由必须加载回测 DAO 和 AKShareFetcher。

```
routes.py (2775 行)
├── 模块级初始化
│   ├── backtest_dao
│   ├── db_manager
│   └── akshare_fetcher
├── trading_bp (回测/执行计划)
└── khunter_bp (狩猎场)

导入即加载 → 跨领域耦合
```

---

## After — 独立 Blueprint，延迟初始化

拆分为独立文件，依赖通过 Flask app.config 或工厂函数注入。与候选 #2（web_server 拆分）协同实施。

```
app_factory (register_blueprints())
├── routes/backtest.py (trading_bp)
│   └── 依赖注入 (app.config)
└── routes/khunter.py (khunter_bp)
    └── 依赖注入 (app.config)
```

---

## 问题

回测和狩猎场是不同领域，却共享模块级初始化。修改狩猎场路由必须加载回测 DAO 和 AKShareFetcher。无法单独测试任一 Blueprint。

---

## 方案

拆分为独立文件，依赖通过 Flask app.config 或工厂函数注入。与候选 #2（web_server 拆分）协同实施。

---

## 收益

- 消除跨领域导入耦合
- 每个 Blueprint 可独立测试
- 与 web_server 拆分协同
- **locality**：路由与领域逻辑就近

---

## 验收标准

- [ ] trading_bp 和 khunter_bp 在独立文件中
- [ ] 依赖通过 Flask app.config 注入
- [ ] 模块级初始化移除
- [ ] 每个 Blueprint 可独立测试
- [ ] 与 Candidate #2 协同实施
