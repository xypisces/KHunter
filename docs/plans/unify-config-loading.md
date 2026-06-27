# 统一配置加载 PRD

> **状态**: 待实施 | **优先级**: P1 | **创建日期**: 2026-06-27

---

## 背景

`config/config.yaml` 在代码库中被 **至少 4 个独立位置** 各自加载，形成 split-brain 问题：

| 加载方 | 路径解析 | 缓存 | 写回 |
|---|---|---|---|
| `main.py` → `QuantSystem._load_config()` | CWD-relative | `self.config` 实例变量 | ❌ |
| `web/routes/system.py` → `get_config()` | CWD-relative | ❌ 每次请求重新读 | ✅ POST 直接写文件 |
| `trading/ptrade/ptrade_feedback.py` | `__file__`-relative | 构造函数缓存 | ❌ |
| `web/app_factory.py` | 死参数，从未使用 | — | — |

核心问题：
1. Web UI 通过 POST 修改 config.yaml 后，其他加载方的内存缓存不会更新
2. `create_app()` 的 `config_file` 参数是死参数，从未被使用
3. 路径解析策略不一致（CWD-relative vs `__file__`-relative）

---

## 目标

1. 引入 `AppConfig` 单例，统一 `config.yaml` 的加载、读取、写回
2. 所有模块通过 `get_app_config()` 访问配置
3. 写操作通过 `set()` 方法，原子写入磁盘
4. 删除 `create_app()` 的死参数

---

## 设计决策

### D1: 单例模式

模块级变量 + `get_app_config()` getter 函数，与项目中 `get_global_db()` 模式一致。

### D2: 作用域

仅统一 `config/config.yaml`。其他配置文件（`strategy_params.yaml`、`risk_config.yaml` 等）有各自专用的 loader（`StrategyConfigManager`、`RiskConfigLoader`），暂不改动。

### D3: 写回策略

每次 `set()` 立即原子写回磁盘（先写临时文件再 rename）+ 线程锁。配置修改频率极低（用户手动在 Web UI 改），不需要批量优化。

### D4: 路径解析

统一使用项目根目录（`Path(__file__).parent.parent`）解析 `config/config.yaml` 路径，与 `DatabaseConfig` 一致。

### D5: 验证

加载时做基本验证（文件可解析为 dict），不做 schema 级验证。缺失文件返回空 dict。

---

## 涉及文件清单

### 新建文件（1 个）

| 文件 | 内容 |
|---|---|
| `config/app_config.py` | `AppConfig` 类 + `get_app_config()` 单例 getter |

### 修改文件（3 个）

| # | 文件 | 改动 |
|---|---|---|
| 1 | `web/routes/system.py` | `get_config()` 和 `update_config()` 改用 `get_app_config()` |
| 2 | `main.py` | `QuantSystem.__init__()` 改用 `get_app_config()`，删除 `_load_config()` |
| 3 | `web/app_factory.py` | 删除 `create_app()` 的死参数 `config_file` |

---

## AppConfig 接口设计

```python
class AppConfig:
    """应用主配置单例（config/config.yaml）"""

    def get(self, key: str, default: Any = None) -> Any:
        """读取配置项，支持点号分隔的嵌套键（如 'dingtalk.webhook_url'）"""

    def set(self, key: str, value: Any) -> None:
        """设置配置项并原子写回磁盘"""

    def get_all(self) -> dict:
        """返回完整配置 dict（副本）"""

    def reload(self) -> None:
        """从磁盘重新加载"""

def get_app_config() -> AppConfig:
    """获取 AppConfig 单例"""
```

---

## 实施步骤

### Step 1: 创建 AppConfig

1. 创建 `config/app_config.py`，实现 `AppConfig` 类和 `get_app_config()` 单例

### Step 2: 迁移调用方

2. `web/routes/system.py` — 改用 `get_app_config().get_all()` 和 `get_app_config().set()`
3. `main.py` — 改用 `get_app_config()`，删除 `_load_config()` 方法
4. `web/app_factory.py` — 删除 `config_file` 参数

### Step 3: 验证

5. `uv run pyright config/app_config.py web/routes/system.py main.py web/app_factory.py`
6. 验证导入正常

---

## 验收标准

- [ ] `config/app_config.py` 存在，提供 `get_app_config()` 单例
- [ ] `web/routes/system.py` 不再直接读写 config.yaml
- [ ] `main.py` 不再有 `_load_config()` 方法
- [ ] `create_app()` 无 `config_file` 参数
- [ ] `uv run pyright` 对所有修改文件 0 新增 errors
