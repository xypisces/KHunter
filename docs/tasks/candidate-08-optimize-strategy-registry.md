# Candidate 8: 优化 StrategyRegistry 热加载机制

> **优先级**: Speculative  \
> **涉及文件**: strategy/strategy_registry.py

---

## Before — 每次访问重新实例化

每次 `get_strategy()` 都读取 YAML 文件并重新实例化。策略对象是临时的，设置的状态会丢失。难以测试。

```
调用方 → StrategyRegistry.get_strategy("MA")
         ├── 读取 strategy_params.yaml
         ├── 创建新实例 + 复制元数据
         └── 返回策略实例 (临时)
         
下次调用重复整个流程
```

---

## After — 文件变更检测 + 缓存

使用文件 mtime 检测变更，未变则返回缓存实例。提供 `force_reload()` 方法。

```
调用方 → StrategyRegistry.get_strategy("MA")
         ├── 检查缓存 + mtime
         ├── 文件未变 → 返回缓存实例
         └── 文件已变 → 读取 YAML → 重建实例 → 返回新实例
```

---

## 问题

每次 `get_strategy()` 都读取 YAML 文件并重新实例化。策略对象是临时的，设置的状态会丢失。难以测试。

---

## 方案

使用文件 mtime 检测变更，未变则返回缓存实例。提供 `force_reload()` 方法。测试时可注入不读文件的适配器。

---

## 收益

- 减少磁盘 I/O
- 策略实例可保持状态
- 测试可跳过文件系统
- 保留热加载能力

---

## 验收标准

- [ ] 使用文件 mtime 检测变更
- [ ] 文件未变时返回缓存实例
- [ ] 提供 `force_reload()` 方法
- [ ] 测试时可注入不读文件的适配器
- [ ] 保留热加载能力
