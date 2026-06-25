# KHunter

A 股量化交易系统，覆盖数据管理、策略选股、择时交易、风险控制、回测验证。

## Language

**策略（Strategy）**:
一个独立的选股逻辑单元，继承 `BaseStrategy`，实现 `calculate_indicators` 和 `select_stocks` 两个方法。
_Avoid_: 规则、模型、算法

**指标（Indicator）**:
从原始行情数据（OHLCV）计算得出的技术数值，如 MA、RSI、KDJ。指标是策略的输入，不是策略的一部分。
_Avoid_: 因子、特征、信号

**信号（Signal）**:
策略 `select_stocks` 的输出，表示某只股票在某日满足特定条件。一个策略可以产生多个信号。
_Avoid_: 推荐、提示、触发

**狩猎场（Hunting Ground）**:
经过策略筛选后的候选股票池，按评分排名展示。
_Avoid_: 股票池、候选列表

**择时（Market Timing）**:
判断市场整体环境是否适合交易，影响仓位和风控决策。
_Avoid_: 大盘判断、市场情绪

**支撑位（Support Level）**:
价格下跌时可能止跌回升的位置，由 MA、前低、百分比等方法计算。
_Avoid_: 底部、防线

## Data

**行情数据**:
从 akshare 获取的 OHLCV 日线数据，存入 SQLite。排序约定：升序（oldest first）为标准，降序（newest first）为 `base_strategy` 的历史约定。
_Avoid_: K 线数据、日线数据

**stock_selection.db**:
主数据库，SQLite 格式，存储行情数据、选股结果、回测记录。
_Avoid_: 主库、数据库

## Module

**indicators/**:
技术指标的统一实现层。所有 MA/EMA/RSI/KDJ/MACD/ATR/Bollinger 计算集中在此。内部处理升序/降序转换，对外暴露纯函数接口。
_Avoid_: 技术指标模块、指标库

**utils/technical.py**:
技术指标的旧实现（通达信公式风格），已被 `indicators/` 替代，保留 deprecation warning 转发层。
_Avoid_: 旧指标模块
