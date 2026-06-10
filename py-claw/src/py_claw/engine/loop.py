"""核心 ReAct 主循环 — AgentEngine。"""

from __future__ import annotations

import asyncio
from typing import Any

from loguru import logger

from py_claw.context.composer import PromptComposer
from py_claw.context.compactor import Compactor
from py_claw.context.recovery import RecoveryManager
from py_claw.context.session import Session
from py_claw.engine.reminder import ReminderInjector
from py_claw.engine.reporter import Reporter
from py_claw.schema.message import Message, Role, ToolCall, ToolDefinition
from py_claw.tools.base import Registry

SUBAGENT_SYSTEM_PROMPT = """你是一个专门负责深度探索的探路者 (Explorer Subagent)。
你的任务是根据主架构师的指令，在当前工作区内仔细阅读代码、查阅日志，搜集足够的信息。

【核心纪律】
1. 你必须、且只能依靠内置工具（如 bash 的 find/grep，或 read_file）去寻找答案。绝对不允许凭空捏造或猜测！
2. 如果你没有找到确切的答案，你必须继续使用工具深入搜索。
3. 当且仅当你找到了确切的线索后，停止调用工具，直接输出一段纯文本作为你的终极汇报。主架构师会根据你的汇报来做下一步决策。"""


class AgentEngine:
    """Agent 引擎，执行 ReAct (Think → Act → Observe) 主循环。"""

    def __init__(
        self,
        provider: Any,
        registry: Registry,
        enable_thinking: bool = False,
        plan_mode: bool = False,
    ) -> None:
        self.provider = provider
        self.registry = registry
        self.enable_thinking = enable_thinking
        self.plan_mode = plan_mode
        self.compactor = Compactor(max_chars=200_000, retain_last_msgs=6)
        self.recovery = RecoveryManager()
        self.injector = ReminderInjector()

    async def run(self, session: Session, reporter: Reporter | None = None) -> None:
        logger.info("唤醒会话 [{}]，锁定工作区: {} (PlanMode: {})",
                    session.id, session.work_dir, self.plan_mode)

        composer = PromptComposer(session.work_dir, self.plan_mode)
        system_msg = composer.build()

        turn_count = 0
        while True:
            turn_count += 1

            available_tools = self.registry.get_available_tools()
            working_memory = await session.get_working_memory(20)

            # 保底占位
            if working_memory and working_memory[0].role != Role.USER:
                dummy = Message(
                    role=Role.USER,
                    content="[系统占位符] 这是为了保持上下文连贯性而注入的断点标记。请继续执行你刚才的任务。",
                )
                working_memory.insert(0, dummy)

            context_history = [system_msg] + working_memory
            compacted = self.compactor.compact(context_history)

            # Phase 1: Thinking
            if self.enable_thinking:
                if reporter:
                    await reporter.on_thinking()

                think_resp = await self.provider.generate(compacted, None)
                if think_resp and think_resp.content:
                    compacted.append(think_resp)

            # Phase 2: Action
            action_resp = await self.provider.generate(compacted, available_tools)

            final_assistant = Message(
                role=Role.ASSISTANT,
                content=action_resp.content,
                tool_calls=list(action_resp.tool_calls),
            )
            await session.append(final_assistant)

            if action_resp.content and reporter:
                await reporter.on_message(action_resp.content)

            if not action_resp.tool_calls:
                break  # 模型不再调用工具 → 任务结束

            # 并发执行工具
            task_results = await asyncio.gather(*[
                self._execute_tool(turn_count, tc, reporter)
                for tc in action_resp.tool_calls
            ])

            for result in task_results:
                await session.append(result.message)

            # 死循环检测（使用最后一个工具）
            last_tc = action_resp.tool_calls[-1]
            last_tr = task_results[-1]
            reminder = self.injector.check_and_inject(last_tc, last_tr)
            if reminder:
                await session.append(reminder)

    async def _execute_tool(
        self,
        turn: int,
        call: ToolCall,
        reporter: Reporter | None,
    ) -> ToolResultWithMsg:
        if reporter:
            await reporter.on_tool_call(call.name, call.arguments)

        result = await self.registry.execute(call)

        final_output = result.output
        if result.is_error:
            final_output = self.recovery.analyze_and_inject(call.name, result.output)

        if reporter:
            display = final_output[:200] + "..." if len(final_output) > 200 else final_output
            await reporter.on_tool_result(call.name, display, result.is_error)

        return ToolResultWithMsg(
            message=Message(
                role=Role.USER,
                content=final_output,
                tool_call_id=call.id,
            ),
            result=result,
        )

    async def run_sub(
        self,
        task_prompt: str,
        read_only_registry: Registry,
        reporter: Any = None,
    ) -> str:
        """为子智能体执行一次性受限循环。"""
        context_history = [
            Message(role=Role.SYSTEM, content=SUBAGENT_SYSTEM_PROMPT),
            Message(role=Role.USER, content=task_prompt),
        ]

        MAX_SUB_TURNS = 10
        for turn in range(1, MAX_SUB_TURNS + 1):
            available_tools = read_only_registry.get_available_tools()
            compacted = self.compactor.compact(context_history)

            action_resp = await self.provider.generate(compacted, available_tools)

            context_history.append(action_resp)

            if not action_resp.tool_calls:
                return action_resp.content

            results = await asyncio.gather(*[
                self._execute_tool(turn, tc, reporter)
                for tc in action_resp.tool_calls
            ])
            for r in results:
                context_history.append(r.message)

        raise RuntimeError(
            f"子智能体探索过于深入，超过 {MAX_SUB_TURNS} 轮被强制召回"
        )


class ToolResultWithMsg:
    """工具执行结果 + 对应的 Message 封装。"""
    def __init__(self, message: Message, result: Any) -> None:
        self.message = message
        self.result = result
