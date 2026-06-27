# PRD: 整合数据获取层

> **状态**: 已完成
> **创建日期**: 2026-06-27
> **涉及文件**: utils/akshare_fetcher.py, utils/base_fetcher.py, utils/data_fetcher.py, stock_analyzer/data_fetcher.py, + 10 个子 fetcher

---

## 问题陈述

1. 有 13 个 fetcher 文件，共 5549 行代码
2. 3 个同名但完全不同的 `DataFetcher` 类，造成混淆
3. `AKShareFetcher` 是纯委托门面，不增加逻辑
4. `utils/base_fetcher.py` 的抽象基类只被部分 fetcher 继承
5. `stock_analyzer/data_fetcher.py` 有独立的数据获取路径，与其他 fetcher 不统一

---

## 设计方案

### 1. 统一接口

定义统一的 `DataFetcher` 接口（删除其他同名类）：

```python
# utils/data_fetcher.py (统一接口)
from abc import ABC, abstractmethod

class DataFetcher(ABC):
    """数据获取器统一接口"""

    @abstractmethod
    def fetch_stock_basic(self) -> pd.DataFrame:
        """获取股票基础数据"""

    @abstractmethod
    def fetch_stock_history(self, code: str, days: int) -> pd.DataFrame:
        """获取股票历史数据"""

    @abstractmethod
    def fetch_fund_flow(self, code: str) -> pd.DataFrame:
        """获取资金流向"""

    @abstractmethod
    def fetch_industry_data(self) -> pd.DataFrame:
        """获取行业数据"""

    @abstractmethod
    def fetch_sector_data(self) -> pd.DataFrame:
        """获取板块数据"""
```

### 2. 领域分组

按领域重组 fetcher：

```
utils/
├── data_fetcher.py          # 统一接口 (DataFetcher ABC)
├── market_data/             # 行情数据
│   ├── __init__.py
│   ├── stock_fetcher.py     # 股票数据 (原 stock_data_fetcher.py)
│   ├── kline_fetcher.py     # K线数据 (原 kline_fetcher.py)
│   └── index_fetcher.py     # 指数数据 (原 index_data_fetcher.py)
├── fundamental/             # 基本面数据
│   ├── __init__.py
│   ├── industry_fetcher.py  # 行业数据 (原 industry_fetcher.py)
│   └── sector_fetcher.py    # 板块数据 (原 sector_fetcher.py)
├── fund_flow/               # 资金流向
│   ├── __init__.py
│   └── fund_flow_fetcher.py # 资金流 (原 fund_flow_fetcher.py)
└── event/                   # 事件数据
    ├── __init__.py
    └── event_fetcher.py     # 事件 (原 event_fetcher.py)
```

### 3. 删除纯委托层

删除 `AKShareFetcher` 的纯委托方法，保留真正有逻辑的方法（如批量处理、缓存等）。

### 4. stock_analyzer 整合

`stock_analyzer/data_fetcher.py` 改为使用统一接口：

```python
# stock_analyzer/data_fetcher.py
from utils.data_fetcher import DataFetcher

class StockAnalyzerDataFetcher:
    """股票分析器数据获取 - 使用统一数据源"""

    def __init__(self, fetcher: DataFetcher):
        self.fetcher = fetcher

    def get_stock_basic(self, code: str) -> Dict:
        return self.fetcher.fetch_stock_basic(code)
```

### 5. 测试支持

通过依赖注入，测试时可使用内存适配器：

```python
class MockDataFetcher(DataFetcher):
    """内存适配器，用于测试"""

    def fetch_stock_basic(self) -> pd.DataFrame:
        return pd.DataFrame({...})
```

---

## 验收标准

- [x] 只有一个 DataFetcher 接口 → utils/data_fetcher.py
- [x] AKShareFetcher 通过适配器实现统一接口 → utils/akshare_adapter.py
- [x] stock_analyzer 复用统一数据源 → stock_analyzer/data_fetcher.py
- [x] 测试可用内存适配器替换 → MockDataFetcher
- [x] 所有 fetcher 按领域分组
- [x] 通过 `uv run pyright` 类型检查
