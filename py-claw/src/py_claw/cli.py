"""CLI 入口 — python -m py_claw.cli 或 py-claw 命令。"""

from __future__ import annotations

import argparse
import asyncio
import os
import sys
import time

from loguru import logger

from py_claw.context.session import global_session_mgr
from py_claw.engine.loop import AgentEngine
from py_claw.engine.terminal_reporter import TerminalReporter
from py_claw.observability.tracker import CostTracker
from py_claw.observability.trace import start_span, end_span, export_trace_to_file
from py_claw.provider.openai_compat import OpenAICompatProvider
from py_claw.schema.message import Message, Role
from py_claw.tools.base import Registry
from py_claw.tools.bash import BashTool
from py_claw.tools.edit_file import EditFileTool
from py_claw.tools.read_file import ReadFileTool
from py_claw.tools.write_file import WriteFileTool


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="py-claw: 极简智能体驾驭引擎")
    parser.add_argument("-prompt", required=True, help="要交给 Agent 执行的任务描述")
    parser.add_argument("-dir", default=".", help="Agent 运行的工作区目录路径")
    parser.add_argument("-session", default="cli_default_session", help="指定会话 ID")
    parser.add_argument("--plan", action="store_true", help="启用长程规划模式")
    parser.add_argument("--thinking", action="store_true", help="启用慢思考模式")
    parser.add_argument("--model", default="glm-4.5-air", help="模型名称")
    parser.add_argument("--api-key", help="API Key (默认使用 ZHIPU_API_KEY 环境变量)")
    parser.add_argument("--base-url", help="API Base URL")
    return parser


async def async_main() -> None:
    parser = build_parser()
    args = parser.parse_args()

    work_dir = os.path.abspath(args.dir)

    print("=" * 50)
    print(f"🚀 启动 py-claw CLI 引擎...")
    print(f"📁 锁定工作区: {work_dir}")
    print("=" * 50)

    # 初始化 Provider
    provider = OpenAICompatProvider(
        model=args.model,
        base_url=args.base_url,
        api_key=args.api_key,
    )

    # 获取 Session
    sess = await global_session_mgr.get_or_create(args.session, work_dir)

    # Cost Tracker 装饰
    tracked = CostTracker(provider, args.model, sess)

    # 注册工具
    registry = Registry()
    registry.register(ReadFileTool(work_dir))
    registry.register(WriteFileTool(work_dir))
    registry.register(BashTool(work_dir))
    registry.register(EditFileTool(work_dir))

    # 初始化引擎
    eng = AgentEngine(
        provider=tracked,
        registry=registry,
        enable_thinking=args.thinking,
        plan_mode=args.plan,
    )

    root_span = start_span("CLI.TaskRun", {"Prompt": args.prompt})

    reporter = TerminalReporter()
    print(f"\n🎯 收到任务: {args.prompt}\n")

    await sess.append(Message(role=Role.USER, content=args.prompt))

    start_time = time.time()
    try:
        await eng.run(sess, reporter)
    except Exception as e:
        logger.error("💥 引擎运行崩溃: {}", e)
        sys.exit(1)
    finally:
        end_span(root_span)
        export_trace_to_file(root_span, work_dir, sess.id)

    elapsed = time.time() - start_time
    print("\n" + "=" * 50)
    print(f"✨ 任务圆满结束。总耗时: {elapsed:.2f}s")
    print(f"💰 Session 累计消耗: ¥{sess.total_cost_cny:.6f} | Token: Input {sess.total_prompt_tokens}, Output {sess.total_completion_tokens}")
    print("=" * 50)


def main() -> None:
    asyncio.run(async_main())


if __name__ == "__main__":
    main()
