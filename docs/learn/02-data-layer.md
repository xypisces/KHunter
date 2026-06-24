# 数据层详解

## 数据源

KHunter 使用两个主要数据源，按优先级排列：

### 1. akshare（主数据源）

- **用途**：股票列表、实时行情、历史 K 线、资金流向
- **入口**：`utils/akshare_fetcher.py` 的 `AKShareFetcher` 类
- **特点**：免费、无需 token、数据全面

关键 API 调用：
```python
ak.stock_zh_a_spot_em()      # 获取所有 A 股实时行情
ak.stock_zh_a_hist()         # 获取历史 K 线数据
ak.stock_zh_a_hist_min_em()  # 获取分钟级 K 线
```

### 2. Tushare Pro（辅助数据源）

- **用途**：评分系统所需的财务数据、资金流、板块数据
- **配置**：`config/tushare_config.json` 中的 token
- **限流**：`_TushareRateLimiter` 类控制调用频率

使用的 Tushare 接口：
```
moneyflow_ths    # 同花顺资金流向
hk_hold          # 北向资金持仓
fina_indicator   # 财务指标
ths_daily        # 板块行情
moneyflow_ind_ths # 板块资金流
ths_member       # 板块成分股
trade_cal        # 交易日历
```

### 3. 备用数据源

`utils/data_fetcher.py` 的 `DataFetcher` 类实现了多源降级：
```
Tushare Pro → 腾讯财经 → 东方财富
```

## 数据获取器架构

```
AKShareFetcher (门面类)
  ├── StockDataFetcher     # 股票列表 + 实时行情 + 历史 K 线
  ├── KlineFetcher         # K 线数据持久化
  ├── FundFlowFetcher      # 资金流向数据
  ├── DataInitializer      # 初始数据加载编排
  └── CollectorManager     # 数据收集管理
```

## 数据库层：DBManager

### 单例获取

```python
from utils.global_db import get_global_db
db = get_global_db()  # 全局唯一实例
```

### 核心特性

| 特性 | 实现 |
|------|------|
| 线程安全 | 按线程 ID 的连接池 + RLock 写锁 |
| WAL 模式 | 启用 SQLite WAL，支持并发读写 |
| 事务支持 | `BEGIN IMMEDIATE` + 嵌套事务计数器 |
| 重试机制 | 指数退避，最多 3 次重试 `database is locked` |
| 连接池 | `_connection_pool` 按线程 ID 管理连接 |

### 核心表结构

**stock_kline** — K 线数据主表
```sql
code, date, open, high, low, close, volume, market_cap, K, D, J
```

**stock_basic** — 股票基本信息
```sql
code, name, ...  -- 通过 get_stock_name() / get_all_stock_names() 访问
```

**stock_selection_record** — 选股记录
```sql
-- 保存历史选股结果，用于回溯和分析
```

### 核心方法

```python
# 读写股票数据
db.read_stock(code, start_date, end_date) -> DataFrame
db.write_stock(code, df)
db.update_stock(code, df)
db.list_all_stocks() -> list[str]

# 股票名称
db.get_stock_name(code) -> str
db.get_all_stock_names() -> dict[str, str]

# 通用操作
db.execute(sql, params)
db.query(sql, params) -> list[dict]
db.begin_transaction()  # 支持嵌套
```

## 数据初始化流程

### 全量初始化 (`main.py init`)

```
1. init_databases_if_needed()  -- 创建数据库和表结构
2. AKShareFetcher.fetch_all_stocks()  -- 获取所有 A 股代码
3. 遍历每只股票:
   a. 获取历史 K 线 (akshare)
   b. 计算 KDJ 指标
   c. 写入 stock_kline 表
4. 更新 stock_basic 表
```

### 智能更新 (`main.py run`)

```
1. 检查当前时间 (15:00 前不更新)
2. 随机抽样 100 只股票检查是否有当天数据
3. 如已有当天数据 → 跳过更新
4. 否则 → 增量更新当天数据
```

## 数据流详解

```
外部 API                    本地存储                    应用层
─────────                  ─────────                  ──────
akshare ──┐
           ├──→ AKShareFetcher ──→ DBManager ──→ stock_kline
Tushare ──┘         │                    │
                    │                    ├──→ stock_basic
                    │                    │
                    ▼                    ▼
            StockFilter          StrategyRegistry
            (过滤 ST/退市)       (读取股票数据)
                                        │
                                        ▼
                                 选股策略执行
                                 评分系统计算
```

## 技术指标计算

`utils/technical.py` 实现了通达信公式风格的技术指标函数：

| 函数 | 说明 |
|------|------|
| `MA(series, n)` | 移动平均线 |
| `EMA(series, n)` | 指数移动平均 |
| `LLV(series, n)` | N 周期最低值 |
| `HHV(series, n)` | N 周期最高值 |
| `SMA(series, n, m)` | 加权移动平均 |
| `REF(series, n)` | 前 N 周期值 |
| `EXIST(series, n)` | N 周期内是否存在 |
| `KDJ(df, n, m1, m2)` | KDJ 指标 |
| `RSI(series, period)` | RSI 指标 |
| `MACD(series, fast, slow, signal)` | MACD 指标 |
| `calculate_zhixing_trend(df)` | 执行趋势指标 |

**重要特性**：所有函数自动检测数据是升序还是降序，内部统一处理后再计算。

## 缓存管理

- `utils/cache_manager.py` — 通用缓存管理
- `utils/csv_manager.py` — CSV 文件导出
- `utils/selection_record_manager.py` — 选股记录管理

## 关键文件索引

| 文件 | 职责 |
|------|------|
| `utils/global_db.py` | DBManager 单例获取 |
| `utils/db_manager.py` | SQLite 管理器核心实现 |
| `utils/db_initializer.py` | 数据库初始化 |
| `utils/db_config.py` | 数据库配置 |
| `utils/akshare_fetcher.py` | akshare 数据获取门面 |
| `utils/stock_data_fetcher.py` | 股票数据获取 |
| `utils/kline_fetcher.py` | K 线数据获取 |
| `utils/fund_flow_fetcher.py` | 资金流数据获取 |
| `utils/data_fetcher.py` | 多源降级获取器 |
| `utils/technical.py` | 技术指标计算 |
| `utils/stock_filter.py` | 股票过滤器 |
| `utils/trade_date_utils.py` | 交易日工具 |
