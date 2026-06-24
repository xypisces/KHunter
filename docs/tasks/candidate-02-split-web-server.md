# Candidate 2: 拆分 web_server.py 上帝模块

> **优先级**: Strong  \
> **涉及文件**: web_server.py, web/app_factory.py (新), web/routes/dashboard.py (新), web/routes/stocks.py (新), web/routes/signals.py (新)

---

## Before — 单文件，导入即副作用

导入 web_server 即触发数据库初始化和策略加载。50+ 路由、WebSocket、业务逻辑全在一个 4442 行文件中，无法单独测试任何端点。

```
web_server.py (4442 行)
├── Flask 配置 + JSON 编码
├── 模块级初始化 (db/registry/fetcher/analyzer) ← 导入即执行
├── 50+ 路由处理器
├── WebSocket 事件
└── 业务逻辑编排
```

---

## After — 工厂模式 + Blueprint 拆分

引入 `create_app()` 工厂函数，依赖通过参数注入。按领域拆分 Blueprint 到独立文件。

```
app_factory.py (create_app())
├── 初始化依赖 (延迟注入)
├── dashboard_bp
├── stocks_bp
├── signals_bp
├── trading_bp
└── WebSocket 事件
```

---

## 问题

导入 web_server 即触发数据库初始化和策略加载。50+ 路由、WebSocket、业务逻辑全在一个 4442 行文件中，无法单独测试任何端点。

---

## 方案

引入 `create_app()` 工厂函数，依赖通过参数注入。按领域拆分 Blueprint 到独立文件。模块级初始化移入工厂。

---

## 收益

- **leverage**：工厂注入，测试可替换依赖
- **locality**：每个 Blueprint 自包含
- 消除导入副作用
- 可独立启动子集路由

---

## 验收标准

- [ ] web_server.py < 500 行
- [ ] 每个 Blueprint 可独立测试
- [ ] 导入 web_server 不触发副作用
- [ ] 所有现有测试通过
- [ ] 可独立启动子集路由
