# 快速上手指南

## 环境要求

- Python 3.12+
- uv 包管理器（非 pip）

## 安装

```bash
# 克隆项目
git clone <repo-url>
cd KHunter

# 安装依赖（uv 会自动创建虚拟环境）
uv sync
```

## 首次运行

### 1. 创建配置文件

```bash
cp config/config.yaml.template config/config.yaml
# 编辑 config.yaml，填入 Tushare token 等配置
```

### 2. 初始化数据

```bash
# 全量数据抓取（首次运行需要较长时间）
uv run main.py init

# 限制股票数量（快速测试）
uv run main.py init --max-stocks 100
```

### 3. 运行选股

```bash
# 完整流程：智能更新数据 + 选股
uv run main.py run

# 限制股票数量
uv run main.py run --max-stocks 100

# 指定分类
uv run main.py run --category bowl_center   # 回落碗中
uv run main.py run --category near_duokong  # 靠近多空线

# 带 B1 模式匹配
uv run main.py run --b1-match --min-similarity 60
```

### 4. 启动 Web 界面

```bash
uv run main.py web
# 浏览器访问 http://localhost:8080
```

## CLI 命令参考

```bash
# 查看版本
uv run main.py --version

# 全量初始化
uv run main.py init [--max-stocks N]

# 智能更新 + 选股
uv run main.py run [--max-stocks N] [--category CATEGORY] [--b1-match]

# 启动 Web 服务器
uv run main.py web [--host HOST] [--port PORT]
```

## Web 界面功能

启动 Web 服务器后，可通过浏览器访问以下功能：

### 数据管理
- 数据初始化（支持暂停/恢复/取消）
- 数据增量更新
- K 线数据管理

### 策略选股
- 选择策略组合（单选/多选）
- 选股逻辑（OR 并集 / AND 交集）
- 实时选股结果展示

### 策略管理
- 查看所有策略详情
- 调整策略参数（热加载）
- 参数验证

### 回测验证
- 历史回测
- 收益曲线
- 风险指标

### 交易管理
- 策略运行器初始化
- 信号管理（执行/忽略）
- 持仓管理
- PTrade 信号导出

### 风险控制
- 风控状态监控
- 风控配置调整

### 市场温度
- 市场温度计算
- 仓位比例建议

## 常见工作流

### 日常选股流程

```bash
# 1. 更新当天数据（15:00 后自动跳过）
uv run main.py run

# 2. 查看结果
# CLI 输出会显示符合条件的股票列表

# 3. 或通过 Web 界面查看
uv run main.py web
# 浏览器打开 http://localhost:8080
```

### 策略调优流程

1. 通过 Web 界面调整策略参数
2. 运行回测验证效果
3. 满意后保存参数配置

### 新增策略流程

1. 在 `strategy/` 目录创建新 `.py` 文件
2. 继承 `BaseStrategy`，实现 `calculate_indicators()` 和 `select_stocks()`
3. 在 `config/strategy_params.yaml` 添加配置
4. 在 `config/strategy_order.yaml` 添加顺序
5. 运行 `uv run main.py run` 测试

## Windows 用户

双击 `start.bat` 即可启动。

## 目录结构速查

```
KHunter/
├── main.py              # CLI 入口
├── web_server.py        # Web 入口
├── strategy/            # 选股策略
├── trading/             # 交易引擎
├── utils/               # 工具模块
├── stock_analyzer/      # 股票分析
├── config/              # 配置文件
├── web/                 # 前端代码
├── data/                # 数据库（gitignored）
├── logs/                # 日志（gitignored）
└── docs/                # 文档（本目录）
```

## 文档索引

| 文档 | 内容 |
|------|------|
| [01-architecture-overview.md](01-architecture-overview.md) | 项目架构总览 |
| [02-data-layer.md](02-data-layer.md) | 数据层详解 |
| [03-strategy-system.md](03-strategy-system.md) | 策略系统详解 |
| [04-trading-engine.md](04-trading-engine.md) | 交易引擎详解 |
| [05-web-api.md](05-web-api.md) | Web API 与前端详解 |
| [06-config-guide.md](06-config-guide.md) | 配置文件指南 |
| [07-getting-started.md](07-getting-started.md) | 本文档 |
