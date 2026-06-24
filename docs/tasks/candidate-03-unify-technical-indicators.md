# Candidate 3: 统一技术指标模块

> **优先级**: Strong  \
> **涉及文件**: utils/technical.py, trading/technical_indicators.py, utils/support_level_calculator.py

---

## Before — 三处计算 MA，三种假设

三个模块各自计算移动平均线，对数据排序的假设不同。开发者理解"MA 怎么算"需要检查三个位置。

```
utils/technical.py
└── MA() — 反转数据处理降序

trading/technical_indicators.py
└── calculate_ma() — 标准 rolling，带缓存

utils/support_level_calculator.py
└── 内联 rolling() — 假设升序

⚠ 数据排序假设不一致 → 潜在 bug
```

---

## After — 一个深层模块

创建 `indicators/` 模块，统一所有技术指标实现。内部处理升序/降序转换，对外暴露统一接口。

```
indicators/ (深层模块)
├── MA / EMA / ATR / RSI (统一实现 + 排序处理)
├── 缓存层 (可选)
└── 支撑位计算
    ↑       ↑       ↑
策略    回测引擎  实盘运行器  KHunter 狩猎场
```

---

## 问题

三个模块各自计算移动平均线，对数据排序的假设不同。开发者理解"MA 怎么算"需要检查三个位置。utils/technical.py 被策略使用却放在 utils/ 而非 strategy/。

---

## 方案

创建 `indicators/` 模块，统一所有技术指标实现。内部处理升序/降序转换，对外暴露统一接口。缓存作为内部实现细节。

---

## 收益

- **locality**：指标逻辑集中一处
- 消除排序假设不一致的 bug 风险
- **leverage**：一个接口覆盖所有调用方
- 测试只需覆盖一个模块

---

## 验收标准

- [ ] 所有 MA/EMA/ATR/RSI 计算在 indicators/ 模块中
- [ ] 内部处理升序/降序转换
- [ ] 对外暴露统一接口
- [ ] 三处调用方全部迁移到新接口
- [ ] 单元测试覆盖所有指标
