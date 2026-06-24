# Candidate 9: 统一 stock_analyzer 与 trading 的数据/评分

> **优先级**: Speculative  \
> **涉及文件**: stock_analyzer/__init__.py, stock_analyzer/data_fetcher.py, stock_analyzer/technical_analyzer.py

---

## Before — 独立数据路径 + 重复评分

stock_analyzer 有独立的数据获取和评分逻辑，与 trading/ 的 5 维评分系统概念重复。`_convert_technical_result()` 是因为两边格式不统一才存在的翻译层。

```
StockAnalyzer
├── stock_analyzer/DataFetcher (独立 akshare 调用)
├── technical_analyzer (独立评分逻辑)
└── _convert_technical_result (格式转换层)

trading/ 评分系统 (5 维评分)
         ↓ 概念重复 ↓
```

---

## After — 共享数据源 + 适配层

依赖候选 #5（统一数据获取）和候选 #3（统一技术指标）。stock_analyzer 改为复用 trading/ 的评分系统，通过适配层转换输出格式。

```
StockAnalyzer
├── DataPort (共享数据接口)
└── ScoringAdapter (复用 5 维评分)
    ↑
    akshare
    ↑
trading/ 评分系统
```

---

## 问题

stock_analyzer 有独立的数据获取和评分逻辑，与 trading/ 的 5 维评分系统概念重复。`_convert_technical_result()` 是因为两边格式不统一才存在的翻译层。

---

## 方案

依赖候选 #5（统一数据获取）和候选 #3（统一技术指标）。stock_analyzer 改为复用 trading/ 的评分系统，通过适配层转换输出格式。

---

## 收益

- 消除翻译层
- 评分逻辑不再重复
- **leverage**：复用已有评分模块
- 依赖候选 #5, #3 先行完成

---

## 验收标准

- [ ] 依赖 Candidate #5 和 #3 完成
- [ ] stock_analyzer 复用 DataPort 接口
- [ ] stock_analyzer 复用 trading/ 评分系统
- [ ] `_convert_technical_result()` 翻译层删除
- [ ] 通过适配层转换输出格式
