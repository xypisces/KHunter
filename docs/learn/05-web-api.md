# Web API 与前端详解

## Web 服务器架构

`web_server.py` — Flask + SocketIO 应用，约 4173 行。

### 初始化流程

```python
# 模块级初始化（导入时执行）
Flask app = Flask(template_folder='web/templates', static_folder='web/static')
SocketIO = SocketIO(async_mode='threading', ping_timeout=3600)

# 数据库初始化
init_databases_if_needed()
ensure_database_schema()

# 全局单例创建
db_manager = get_global_db()
registry = get_registry()
registry.auto_register_from_directory("strategy")
# ... 更多单例

# Blueprint 注册
app.register_blueprint(trading_bp, url_prefix='/api/trading')
app.register_blueprint(stock_score_bp)
app.register_blueprint(khunter_bp)
```

### 自定义 JSON 处理

```python
class NumpyEncoder(JSONEncoder):
    """处理 numpy 类型、NaN/Inf 的 JSON 序列化"""

def clean_data_for_json(data):
    """递归清理数据中的 numpy 类型，确保可 JSON 序列化"""
```

## API 路由总览

### Dashboard 端点

| 方法 | 路径 | 说明 |
|------|------|------|
| GET | `/api/dashboard/my-golden-stocks` | 我的金股 |
| GET | `/api/dashboard/hot-industries` | 热门行业 |
| GET | `/api/dashboard/hot-areas` | 热门地区 |
| GET | `/api/dashboard/industry-stocks` | 行业股票 |
| GET | `/api/dashboard/area-stocks` | 地区股票 |

### 股票数据端点

| 方法 | 路径 | 说明 |
|------|------|------|
| GET | `/api/stocks` | 股票列表（分页） |
| GET | `/api/stock/<code>` | 股票详情（含 KDJ） |
| POST | `/api/analyze-stock` | 股票分析 |

### 选股端点（核心）

| 方法 | 路径 | 说明 |
|------|------|------|
| GET | `/api/select` | 选股（GET 方式） |
| POST | `/api/select` | 选股（POST 方式，支持更多参数） |

POST 请求体：
```json
{
    "strategies": ["BottomTrendInflectionStrategy", "MorningStarStrategy"],
    "logic": "OR",           // OR=并集, AND=交集
    "end_date": "2026-06-03",
    "b1_match": true,        // 可选: B1 模式匹配
    "min_similarity": 60.0,  // 可选: 最低相似度
    "lookback_days": 25      // 可选: 回看天数
}
```

### 策略管理端点

| 方法 | 路径 | 说明 |
|------|------|------|
| GET | `/api/strategies` | 所有策略列表 |
| GET | `/api/strategies/<name>` | 策略详情 |
| POST | `/api/strategies/<name>/params` | 更新策略参数 |
| POST | `/api/strategies/<name>/validate` | 验证策略参数 |
| GET | `/api/strategies/names` | 策略名称列表 |
| GET | `/api/config` | 获取配置 |
| POST | `/api/config` | 更新配置 |

### 数据管理端点

| 方法 | 路径 | 说明 |
|------|------|------|
| POST | `/api/data/init/start` | 启动数据初始化 |
| GET | `/api/data/init/progress` | 初始化进度 |
| POST | `/api/data/init/cancel` | 取消初始化 |
| POST | `/api/data/init/pause` | 暂停初始化 |
| POST | `/api/data/init/resume` | 恢复初始化 |
| POST | `/api/data/update/start` | 启动数据更新 |
| GET | `/api/data/check` | 检查数据状态 |
| GET | `/api/data/status` | 数据状态 |
| POST | `/api/data/reinit` | 重新初始化 |
| POST | `/api/data/kline/init` | K 线数据初始化 |

### 排名端点

| 方法 | 路径 | 说明 |
|------|------|------|
| GET | `/api/ranking/dates` | 排名日期列表 |
| POST | `/api/ranking/generate` | 生成排名 |
| GET | `/api/ranking/track` | 排名追踪 |
| POST | `/api/ranking/regenerate` | 重新生成排名 |

### 选股历史端点

| 方法 | 路径 | 说明 |
|------|------|------|
| GET | `/api/selection-history` | 选股历史 |
| POST | `/api/save_selection` | 保存选股结果 |

### 交易/策略执行端点

| 方法 | 路径 | 说明 |
|------|------|------|
| POST | `/api/strategy/run` | 运行策略 |
| POST | `/api/strategy/run-batch` | 批量运行策略 |
| POST | `/api/strategy/initialize` | 初始化策略运行器 |
| GET | `/api/strategy/status` | 策略运行状态 |
| GET | `/api/portfolio` | 当前持仓 |
| POST | `/api/portfolio/sell` | 卖出操作 |
| GET | `/api/signals` | 当前信号 |
| POST | `/api/signals/<id>/execute` | 执行信号 |
| POST | `/api/signals/<id>/ignore` | 忽略信号 |
| GET | `/api/stock-pool` | 股票池 |
| GET | `/api/task/history` | 任务历史 |
| GET | `/api/task/last` | 最近任务 |
| POST | `/api/task/save` | 保存任务 |

### 市场温度端点

| 方法 | 路径 | 说明 |
|------|------|------|
| POST | `/api/market-temperature/calculate` | 计算市场温度 |
| GET | `/api/market-temperature/query` | 查询市场温度 |
| GET | `/api/market-temperature/latest` | 最新市场温度 |
| GET | `/api/market-temperature/trend` | 温度趋势 |
| GET | `/api/market-temperature/position-ratio` | 仓位比例建议 |

### 资金流端点

| 方法 | 路径 | 说明 |
|------|------|------|
| POST | `/api/money-flow/select` | 资金流选股 |

### 回测约束端点

| 方法 | 路径 | 说明 |
|------|------|------|
| GET | `/api/backtest/constraints` | 获取约束 |
| POST | `/api/backtest/constraint` | 设置约束 |

### 风控端点

| 方法 | 路径 | 说明 |
|------|------|------|
| GET | `/api/risk/status` | 风控状态 |
| GET | `/api/risk/history` | 风控历史 |
| GET | `/api/risk/config` | 风控配置 |
| POST | `/api/risk/config` | 更新风控配置 |

## WebSocket 事件

```python
# 数据更新进度推送
emit('update_progress', {
    'current': 100,
    'total': 5000,
    'stock_code': '000001',
    'status': 'updating'
})

# 数据初始化进度推送
emit('init_progress', {
    'current': 100,
    'total': 5000,
    'phase': 'fetching',
    'status': 'running'
})
```

## StrategyRunner 懒加载

```python
# web_server.py 中的懒加载单例
_strategy_runner = None

def get_strategy_runner(auto_init=False):
    global _strategy_runner
    if _strategy_runner is None:
        _strategy_runner = StrategyRunner(...)
    return _strategy_runner
```

大多数交易端点需要先调用 `POST /api/strategy/initialize` 初始化。

## 前端架构

### 技术栈

- 纯 JavaScript（无框架）
- 单页应用 (SPA)
- WebSocket 实时通信

### 文件结构

```
web/
├── templates/
│   └── index.html           # SPA 主页面
└── static/
    ├── css/
    │   ├── khunter.css       # 主样式
    │   └── style.css         # 辅助样式
    ├── images/
    │   ├── favicon.svg
    │   └── logo.svg
    └── js/
        ├── app.js            # 应用入口
        ├── dashboard_stats.js # 仪表盘统计
        ├── data_update.js    # 数据更新
        ├── kline_chart.js    # K 线图表
        ├── trading.js        # 交易功能
        ├── selection_history.js # 选股历史
        ├── error_handler.js  # 错误处理
        ├── retry_policy.js   # 重试策略
        └── modules/          # 功能模块
            ├── analysis.js   # 股票分析
            ├── backtest*.js  # 回测相关 (7 个文件)
            ├── execution-plan.js # 执行计划
            ├── history.js    # 历史记录
            ├── khunter.js    # KHunter 核心
            ├── market_temperature.js # 市场温度
            ├── money_flow.js # 资金流
            ├── navigation.js # 导航
            ├── ranking.js    # 排名
            ├── risk.js       # 风控
            ├── selection.js  # 选股
            ├── stocks.js     # 股票列表
            ├── strategies.js # 策略管理
            ├── strategy-runner.js # 策略运行
            ├── utils.js      # 工具函数
            └── websocket.js  # WebSocket
```

### 前端模块加载

`app.js` 作为入口，加载各功能模块。各模块通过 `modules/` 目录组织，按功能划分。
