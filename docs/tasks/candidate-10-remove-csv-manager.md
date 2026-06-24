# Candidate 10: 移除 CSVManager 遗留模块

> **优先级**: Speculative  \
> **涉及文件**: utils/csv_manager.py, main.py, strategy/b1_pattern_library.py

---

## Before — 双存储后端

CSVManager 是从 CSV 迁移到 SQLite 后的遗留代码。B1PatternLibrary 仍通过它读取数据，而其他所有模块使用 DBManager。两个后端可能返回不同数据。

```
main.py
├── CSVManager (CSV 文件)
└── DBManager (SQLite)

B1PatternLibrary → CSVManager
其他策略 → DBManager
         ↓ 可能返回不同数据 ↓
```

---

## After — 单一存储后端

B1PatternLibrary 改用 DBManager 的 `read_stock()`。删除 CSVManager 及其在 main.py 中的实例化。

```
main.py → DBManager (SQLite)

B1PatternLibrary → DBManager
其他策略 → DBManager
```

---

## 问题

CSVManager 是从 CSV 迁移到 SQLite 后的遗留代码。B1PatternLibrary 仍通过它读取数据，而其他所有模块使用 DBManager。两个后端可能返回不同数据。

---

## 方案

B1PatternLibrary 改用 DBManager 的 `read_stock()`。删除 CSVManager 及其在 main.py 中的实例化。确保 B1 的数据源与其他模块一致。

---

## 收益

- 消除双存储后端歧义
- 删除 80 行遗留代码
- B1 数据与其他策略一致
- 接口统一，无隐式依赖

---

## 验收标准

- [ ] CSVManager 删除
- [ ] B1PatternLibrary 改用 DBManager
- [ ] main.py 中 CSVManager 实例化删除
- [ ] 所有现有测试通过
- [ ] grep 确认无 CSVManager 引用
