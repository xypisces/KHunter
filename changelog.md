# Changelog

## 2026-06-25

### refactor: 移除 CSVManager 遗留模块，统一数据层为 SQLite

**背景：** 系统从 CSV 迁移到 SQLite 后，`CSVManager` 模块未被完全移除。`data/` 目录下已无 CSV 文件，该模块实际不可用，但仍被 `B1PatternLibrary` 和 `DataFetcher` 引用。

**变更内容：**

- 删除 `utils/csv_manager.py`
- `B1PatternLibrary` 改用 `DBManager`（通过 `get_global_db()`），修复缓存路径为 `data/cache/`
- `main.py` 移除 CSVManager 导入和实例化
- `web_server.py` 移除 CSVManager 导入和实例化，B1 匹配改用 `db_manager`
- `stock_analyzer/data_fetcher.py` 修复两处未初始化的 `self.csv_manager` → `self.db_manager`
- `utils/db_manager.py` 清理"替代 CSVManager"相关注释

**影响：**
- B1 完美图形匹配功能首次在当前环境下可用（此前因数据源为空而完全不工作）
- `DataFetcher` 消除了 `AttributeError` 崩溃风险
- 数据层统一为 SQLite 单一后端，消除数据不一致隐患
