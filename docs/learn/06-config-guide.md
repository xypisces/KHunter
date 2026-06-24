# 配置文件指南

## 配置文件总览

```
config/
├── config.yaml.template      # 主配置模板
├── config.yaml               # 主配置（包含敏感信息，需手动创建）
├── database.yaml             # 数据库配置
├── data_sources.json         # 数据源配置
├── strategy_params.yaml      # 策略参数（51KB，核心配置）
├── strategy_order.yaml       # 策略执行顺序
├── strategy_weights.json     # 策略评分权重
├── strategy_kelly_config.yaml # Kelly 仓位配置
├── strategy_name_mapping.yaml # 策略名称映射
├── risk_config.yaml          # 风控参数
├── pool_removal_config.yaml  # 池移除配置
├── support_methods.yaml      # 支撑位方法配置
└── 87659999.json             # 其他配置
```

## 一、主配置 config.yaml

从 `config.yaml.template` 复制创建，包含敏感信息（钉钉 webhook 等）。

### 创建方式

```bash
cp config/config.yaml.template config/config.yaml
# 然后编辑填入实际值
```

### 主要配置项

```yaml
# 数据目录
data_dir: "data"

# 钉钉通知
dingtalk:
  webhook: "https://oapi.dingtalk.com/robot/send?access_token=YOUR_TOKEN"
  secret: "YOUR_SECRET"

# Tushare token
tushare:
  token: "YOUR_TUSHARE_TOKEN"

# 其他运行时配置...
```

## 二、策略参数 strategy_params.yaml（51KB）

这是系统最核心的配置文件，定义了所有策略的参数、元数据和显示信息。

### 结构

```yaml
strategies:
  <StrategyClassName>:
    # 元数据
    display_name: "中文名称"
    description: "策略描述"
    icon: "📈"              # 前端显示的 emoji
    color: "#4CAF50"        # 前端显示的颜色

    # 支撑位方法
    support_method: "ma20"  # ma20 | key_open | key_close | key_close_5

    # 参数分组
    param_groups:
      - name: "核心参数"
        description: "控制选股条件"

    # 参数详情
    param_details:
      <param_name>:
        default: 45           # 默认值
        description: "最小跌幅"
        display_name: "跌幅阈值"
        group: "核心参数"
        min: 20               # 最小值
        max: 80               # 最大值
        type: "float"         # int | float | bool | list | string

    # 实际参数值
    params:
      <param_name>: 45

    # 预设配置（可选）
    presets:
      classic:
        params: {...}
      aggressive:
        params: {...}

# 策略运行器全局配置
strategy_runner:
  check_interval: 60        # 检查间隔（秒）
  position_sizing:
    method: "kelly"
    scale_factor: 0.5
  stop_loss:
    trailing: true
    max_drawdown: 0.1
  take_profit:
    enabled: true
    target: 0.2
  trading_cost:
    commission_rate: 0.00015
    min_commission: 5
    stamp_tax_rate: 0.001
    transfer_fee_rate: 0.00001
```

### 热加载

策略参数支持热加载——修改此文件后，下次策略执行时自动生效，无需重启应用。

## 三、策略顺序 strategy_order.yaml

定义策略的执行优先级和前端显示顺序。

```yaml
strategy_order:
  - order: 1
    name: BottomTrendInflectionStrategy
    display_name: 底部趋势拐点
    description: "深度下跌后的反转信号"
  - order: 2
    name: TrendAccelerationInflectionStrategy
    display_name: 趋势加速拐点
    description: "趋势加速的拐点信号"
  # ... 共 16 个策略
  - order: 30
    name: MA20MA60Strategy
    display_name: 520560策略
    description: "均线系统策略"
```

## 四、策略权重 strategy_weights.json

用于技术面评分的策略权重配置。

```json
{
  "strategies": {
    "底部趋势拐点": {
      "weight": 50,
      "direction": "positive",
      "description": "底部反转信号"
    },
    "趋势加速拐点": {
      "weight": 50,
      "direction": "positive"
    },
    "M头策略": {
      "weight": -80,
      "direction": "negative",
      "description": "顶部反转信号"
    },
    "多死叉共振策略": {
      "weight": -50,
      "direction": "negative",
      "description": "多重死叉共振"
    }
  },
  "veto_config": {
    "enabled": true,
    "conditions": ["M头策略", "多死叉共振策略"],
    "logic": "AND",
    "score": -100,
    "description": "M头和多死叉同时出现，一票否决"
  }
}
```

## 五、风控配置 risk_config.yaml

```yaml
risk_control:
  max_position_ratio: 0.3    # 单股最大仓位比例
  max_total_position: 0.8    # 总仓位上限
  stop_loss:
    enabled: true
    method: "trailing"       # trailing | fixed
    trailing_percent: 0.05   # 移动止损回撤比例
    max_drawdown: 0.1        # 最大回撤
  take_profit:
    enabled: true
    target_percent: 0.2      # 目标收益
  cool_down:
    loss_cool_days: 3        # 亏损冷却天数
    fund_flow_cool_days: 3   # 资金流冷却天数
  max_daily_buys: 5          # 每日最大买入数
  max_buy_count_per_stock: 6 # 单股最大买入次数
  min_cash_threshold: 2000   # 最低现金阈值
```

## 六、池移除配置 pool_removal_config.yaml

```yaml
pool_removal:
  support_break:
    enabled: true
    threshold: 0.98          # 支撑位跌破比例 (close < support × 0.98)

  trend_failure:
    enabled: true
    min_hold_days: 3         # 最少持仓天数
    ma_period: 10            # MA 周期
    regression_days: 20      # 线性回归天数
    min_r_squared: 0.3       # 最低 R²

  fund_flow_anomaly:
    enabled: true
    min_hold_days: 3
    net_flow_threshold: -10000  # 主力净流出阈值（万元）
    cool_down_days: 3        # 冷却期天数
```

## 七、Kelly 仓位配置 strategy_kelly_config.yaml

```yaml
kelly:
  enabled: true
  scale_factor: 0.5          # Kelly 缩放系数
  min_position: 0.05         # 最小仓位比例
  max_position: 0.3          # 最大仓位比例
  default_win_rate: 0.5      # 默认胜率
  default_profit_loss_ratio: 1.5  # 默认盈亏比

strategies:
  BottomTrendInflectionStrategy:
    win_rate: 0.55
    profit_loss_ratio: 2.0
  # ... 每个策略可单独配置
```

## 八、支撑位方法配置 support_methods.yaml

```yaml
support_methods:
  ma20:
    description: "20日均线"
    calculation: "df['close'].rolling(20).mean()"
  key_close_5:
    description: "关键日收盘价 × 0.95"
    calculation: "key_close * 0.95"
  key_open:
    description: "关键日开盘价"
    calculation: "key_day_open"
  key_close:
    description: "关键日收盘价"
    calculation: "key_day_close"
```

## 九、数据库配置 database.yaml

```yaml
database:
  path: "data/stock_selection.db"
  wal_mode: true
  journal_mode: "WAL"
  cache_size: -64000         # 64MB
  mmap_size: 268435456       # 256MB
```

## 十、数据源配置 data_sources.json

```json
{
  "sources": [
    {
      "name": "akshare",
      "priority": 1,
      "enabled": true,
      "rate_limit": 0.5
    },
    {
      "name": "tushare",
      "priority": 2,
      "enabled": true,
      "rate_limit": 200
    },
    {
      "name": "eastmoney",
      "priority": 3,
      "enabled": true
    }
  ]
}
```

## 配置优先级

1. `config/config.yaml` — 运行时配置（敏感信息）
2. `config/strategy_params.yaml` — 策略参数（热加载）
3. `config/strategy_order.yaml` — 策略顺序
4. `config/strategy_weights.json` — 评分权重
5. `config/risk_config.yaml` — 风控参数
6. 其他配置文件

## 注意事项

- `config/config.yaml` 包含敏感信息（钉钉 webhook、Tushare token），**不要提交到 git**
- `strategy_params.yaml` 支持热加载，修改后无需重启
- 所有 YAML 配置使用 UTF-8 编码
- 数值类型的参数会自动校验 min/max 范围
