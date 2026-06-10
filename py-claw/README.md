# py-claw: 极简智能体驾驭引擎 (Python 版)

基于 "驾驭工程 (Harness Engineering)" 理念，由 Python 从零实现的微型 AI Agent 操作系统。
本项目是 [go-tiny-claw](https://github.com/yourname/go-tiny-claw) 的 **Pythonic 移植版**。

## 核心设计哲学

- **Harness over Framework**: 真正的壁垒不在于调用大模型 API，而在于如何调度工具、管理上下文和安全拦截。
- **极简即是正义**: 仅向大模型提供 Read、Write、Edit 和 Bash 四大图灵完备的原语。
- **状态外部化**: 抛弃内存状态机，将记忆与计划持久化在 PLAN.md 与 TODO.md 中。

## 核心特性

- 🧠 **ReAct 主循环**: Think → Act → Observe，支持可选的慢思考 (Thinking) 模式
- 🛠️ **工具系统**: Read/Write/Edit/Bash + 中间件链 + 人工审批
- 🔌 **多模型支持**: 通过 OpenAI 兼容协议对接智谱 GLM、DeepSeek、OpenAI 等
- 📦 **会话管理**: 带上下文压缩的 Session 系统，支持断点续传
- 📊 **可观测性**: Span 链路追踪 + Token 成本追踪
- 🤖 **子智能体**: 主 Agent 可派出子 Agent 进行深度探索
- 💬 **飞书集成**: 通过飞书 Bot 接收消息 + 人工审批高危操作
- 📝 **长程规划模式**: 通过 PLAN.md/TODO.md 持久化长期任务

## 快速开始

```bash
# 安装依赖
uv sync

# 设置 API Key
export ZHIPU_API_KEY="your-api-key"

# 运行 CLI
py-claw -prompt "帮我创建一个 Hello World 程序"

# 或使用长程规划模式
py-claw -prompt "构建一个 Web 服务" --plan --thinking

# 指定模型
py-claw -prompt "..." --model deepseek-chat --base-url https://api.deepseek.com/v1
```

## 启动飞书 Bot

```bash
export ZHIPU_API_KEY="..."
export FEISHU_WEBHOOK_URL="https://open.feishu.cn/open-apis/bot/v2/hook/..."
python -m py_claw.server
```

## 项目结构

```
py-claw/
├── src/py_claw/
│   ├── schema/          # 数据模型 (Message, ToolCall, ...)
│   ├── provider/        # LLM Provider (OpenAI 兼容)
│   ├── tools/           # 工具系统 (Registry + 内置工具)
│   ├── context/         # 上下文管理 (Session, Compactor, ...)
│   ├── engine/          # ReAct 主循环 (AgentEngine)
│   ├── observability/   # 可观测性 (Trace, Tracker)
│   ├── feishu/          # 飞书集成 (Bot, Approval)
│   └── eval/            # 基准评测框架
├── cmd/                 # CLI 入口
└── tests/               # 单元测试
```

## 与 Go 版的区别 (Pythonic 设计)

| Go 版 | Python 版 |
|-------|-----------|
| struct | `@dataclass` |
| interface | `typing.Protocol` |
| goroutine + channel | `asyncio.gather()` |
| context.Context | `contextvars` (隐式传播) |
| log.Printf | `loguru` 结构化日志 |
| 显式 Middleware interface | 装饰器链 |
| 色弱终端输出 | `rich` 彩输出 |

---

*本仓库由极客时间专栏《从零构建 Agent Harness》实战产出。*
*作者：Tony Bai*
