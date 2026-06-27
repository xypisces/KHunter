# PRD: 拆分 web_server.py 和 trading/routes.py

> **状态**: 已完成
> **创建日期**: 2026-06-27
> **涉及文件**: web_server.py, trading/routes.py, web/app_factory.py (新), web/routes/*.py (新)

---

## 问题陈述

1. `web_server.py`（4439 行）：50+ 路由、模块级初始化、业务逻辑全在一个文件
2. `trading/routes.py`（2775 行）：回测和狩猎场两个不同领域共享模块级初始化
3. 导入即触发副作用（数据库初始化、策略加载）
4. 无法单独测试任何端点

---

## 设计方案

### 1. 文件结构

```
web/
├── app_factory.py              # create_app() 工厂函数
├── routes/
│   ├── __init__.py             # 导出所有 Blueprint
│   ├── views.py                # 页面渲染（/），后续可删
│   ├── dashboard.py            # /api/dashboard/*
│   ├── stocks.py               # /api/stocks/*, /api/stock/<code>
│   ├── signals.py              # /api/signals/*, /api/select, /api/save_selection
│   ├── strategies.py           # /api/strategies/*
│   ├── system.py               # /api/stats, /api/config, /api/update
│   ├── analysis.py             # /api/analyze-stock, /api/analysis-history
│   ├── risk.py                 # /api/risk/*
│   ├── backtest.py             # /api/trading/backtest/*（从 trading/routes.py 拆出）
│   └── khunter.py              # /api/khunter/*（从 trading/routes.py 拆出）
└── ...
```

### 2. 依赖注入

使用 Flask `app.config` 注入依赖：

```python
# web/app_factory.py
def create_app():
    app = Flask(...)
    
    # 初始化依赖
    app.config['db_manager'] = get_global_db()
    app.config['stock_repo'] = get_stock_repo()
    app.config['registry'] = get_registry(...)
    # ... 其他依赖
    
    # 注册 Blueprint
    from web.routes import register_blueprints
    register_blueprints(app)
    
    return app
```

### 3. 工厂函数

```python
# web/app_factory.py
def create_app(config_file="config/config.yaml") -> tuple[Flask, SocketIO]:
    """创建 Flask 应用和 SocketIO 实例"""
    app = Flask(__name__, 
                template_folder='web/templates',
                static_folder='web/static')
    
    # 配置
    app.json_encoder = NumpyEncoder
    
    # SocketIO
    socketio = SocketIO(app, ...)
    
    # 依赖注入
    _init_dependencies(app)
    
    # 注册 Blueprint
    _register_blueprints(app)
    
    # WebSocket 事件
    _register_socketio_events(socketio)
    
    return app, socketio
```

### 4. 迁移策略

渐进式迁移：
1. 创建 `web/app_factory.py` 和 `web/routes/__init__.py`
2. 逐个创建 Blueprint 文件，从 `web_server.py` 迁移路由
3. 从 `trading/routes.py` 拆分 backtest 和 khunter
4. 更新 `web_server.py` 使用工厂函数
5. 验证所有路由正常工作

### 5. 入口点

```python
# web_server.py（最终形态）
from web.app_factory import create_app

app, socketio = create_app()

def run_web_server(host='0.0.0.0', port=8080, debug=False):
    socketio.run(app, host=host, port=port, debug=debug)

if __name__ == '__main__':
    run_web_server()
```

---

## 路由映射表

### 从 web_server.py 迁移

| 原路由 | 目标 Blueprint | 新文件 |
|--------|---------------|--------|
| `/` | views_bp | web/routes/views.py |
| `/api/stocks` | stocks_bp | web/routes/stocks.py |
| `/api/stock/<code>` | stocks_bp | web/routes/stocks.py |
| `/api/dashboard/*` | dashboard_bp | web/routes/dashboard.py |
| `/api/select` | signals_bp | web/routes/signals.py |
| `/api/save_selection` | signals_bp | web/routes/signals.py |
| `/api/selection-history` | signals_bp | web/routes/signals.py |
| `/api/strategies/*` | strategies_bp | web/routes/strategies.py |
| `/api/stats` | system_bp | web/routes/system.py |
| `/api/config` | system_bp | web/routes/system.py |
| `/api/update` | system_bp | web/routes/system.py |
| `/api/analyze-stock` | analysis_bp | web/routes/analysis.py |
| `/api/analysis-history` | analysis_bp | web/routes/analysis.py |
| `/api/export-report` | analysis_bp | web/routes/analysis.py |
| `/api/risk/*` | risk_bp | web/routes/risk.py |

### 从 trading/routes.py 迁移

| 原路由 | 目标 Blueprint | 新文件 |
|--------|---------------|--------|
| `/api/trading/backtest/*` | backtest_bp | web/routes/backtest.py |
| `/api/khunter/*` | khunter_bp | web/routes/khunter.py |

---

## 验收标准

- [x] web_server.py < 100 行（仅保留启动逻辑）→ 31 行
- [x] 每个 Blueprint 可独立测试
- [x] 导入 web_server 不触发副作用
- [x] 所有现有路由正常工作
- [x] 依赖通过 app.config 注入
- [x] trading/routes.py 拆分为独立文件（backtest.py, khunter.py）
- [x] 通过 `uv run pyright` 类型检查
