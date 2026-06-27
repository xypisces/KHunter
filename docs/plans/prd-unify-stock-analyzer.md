# PRD: 统一 stock_analyzer 数据/评分

> **状态**: 已完成
> **创建日期**: 2026-06-27
> **涉及文件**: stock_analyzer/__init__.py, stock_analyzer/data_fetcher.py

---

## 问题陈述

1. `stock_analyzer/data_fetcher.py` 已改用统一 `DataFetcher` 接口（Candidate #5 已完成）
2. `stock_analyzer/technical_analyzer.py` 已使用统一 `indicators/` 模块
3. 但仍存在 `_convert_technical_result()` 翻译层，因为 `comprehensive_technical_analysis()` 返回格式与前端期望不一致

---

## 设计方案

### 1. 消除翻译层

修改 `comprehensive_technical_analysis()` 直接返回前端期望的格式：

```python
# Before: 返回内部格式，需要翻译
def comprehensive_technical_analysis(self, data):
    return {
        "trend_analysis": {...},
        "volatility_analysis": {...},
        "momentum_analysis": {...},
        "volume_analysis": {...},
        "technical_score": 75,
        "technical_opinion": "看多"
    }

# After: 直接返回前端格式
def comprehensive_technical_analysis(self, data):
    return {
        "trend": "上升趋势",
        "indicators": {
            "MACD": "多头",
            "KDJ": "金叉",
            "RSI": 55.0,
            "Bollinger": "正常"
        },
        "patterns": [],
        "score": 75,
        "opinion": "看多"
    }
```

### 2. 删除翻译层

删除 `_convert_technical_result()` 方法，`analyze()` 直接使用 `comprehensive_technical_analysis()` 的返回值。

---

## 验收标准

- [x] stock_analyzer 使用统一 DataFetcher 接口（Candidate #5 已完成）
- [x] stock_analyzer 使用统一 indicators/ 模块（已完成）
- [x] `_convert_technical_result()` 翻译层删除
- [x] `comprehensive_technical_analysis()` 直接返回前端格式
- [x] 通过 `uv run pyright` 类型检查
