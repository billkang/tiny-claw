# ts-claw: 极简智能体驾驭引擎 (TypeScript 版)

基于 "驾驭工程 (Harness Engineering)" 理念，由 TypeScript 从零实现的微型 AI Agent 操作系统。
本项目是 [go-tiny-claw](https://github.com/yourname/go-tiny-claw) 的 **TypeScript 移植版**。

## 核心设计哲学

- **Harness over Framework**: 真正的壁垒不在于调用大模型 API，而在于如何调度工具、管理上下文和安全拦截。
- **极简即是正义**: 仅向大模型提供 Read、Write、Edit 和 Bash 四大图灵完备的原语。
- **状态外部化**: 抛弃内存状态机，将记忆与计划持久化在 PLAN.md 与 TODO.md 中。

## 快速开始

```bash
# 安装依赖
npm install

# 设置 API Key
export ZHIPU_API_KEY="your-api-key"

# 运行 CLI
npx tsx src/cmd/cli.ts --prompt "帮我创建一个 Hello World 程序"
npx tsx src/cmd/cli.ts -p "帮我创建一个 Hello World 程序"

# 启用长程规划模式
npx tsx src/cmd/cli.ts --prompt "构建一个 Web 服务" --plan --thinking

# 指定模型
npx tsx src/cmd/cli.ts --prompt "..." --model deepseek-chat --base-url https://api.deepseek.com/v1
```

## 启动飞书 Bot

```bash
export ZHIPU_API_KEY="..."
export FEISHU_WEBHOOK_URL="https://open.feishu.cn/open-apis/bot/v2/hook/..."
npx tsx src/cmd/server.ts
```

## 运行基准测试

```bash
npx tsx src/cmd/bench.ts
```

## 项目结构

```
ts-claw/
├── src/
│   ├── schema/          # 数据模型
│   ├── provider/        # LLM Provider (OpenAI 兼容)
│   ├── tools/           # 工具系统
│   ├── context/         # 上下文管理
│   ├── engine/          # ReAct 主循环
│   ├── observability/   # 可观测性
│   ├── feishu/          # 飞书集成
│   └── cmd/             # CLI 入口
├── tests/
└── workspace/
```

## 与 Go 版的区别 (TypeScript 设计)

| Go 版 | TypeScript 版 |
|-------|---------------|
| struct | `interface` / `type` |
| interface | `interface` |
| goroutine + channel | `Promise.all()` |
| context.Context | 显式参数传递 |
| log.Printf | `pino` 结构化日志 |
| 色弱终端输出 | `chalk` 彩色输出 |

---

*本仓库由极客时间专栏《从零构建 Agent Harness》实战产出。*
*作者：Tony Bai*
