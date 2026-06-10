"""子智能体工具 — 主 Agent 可派出子 Agent 进行深度探索。"""

from __future__ import annotations

import json
from typing import TYPE_CHECKING, Any

from loguru import logger

from py_claw.schema.message import ToolDefinition
from py_claw.tools.base import BaseTool, Registry

if TYPE_CHECKING:
    from py_claw.engine.loop import AgentEngine


class SubagentTool(BaseTool):
    """派出一个子智能体进行深度探索。"""

    def __init__(
        self,
        engine: AgentEngine,
        read_only_registry: Registry,
        reporter: Any = None,
    ) -> None:
        self.engine = engine
        self.read_only_registry = read_only_registry
        self.reporter = reporter

    def name(self) -> str:
        return "spawn_subagent"

    def definition(self) -> ToolDefinition:
        return ToolDefinition(
            name=self.name(),
            description="派出一个专门用于深度探索（Exploration）的子智能体。当你需要阅读大量代码、跨文件查找逻辑时请调用此工具。它在探索完毕后，会给你返回一份极度精炼的摘要报告。",
            input_schema={
                "type": "object",
                "properties": {
                    "task_prompt": {
                        "type": "string",
                        "description": "给子智能体下达的明确探索指令。",
                    },
                },
                "required": ["task_prompt"],
            },
        )

    async def execute(self, arguments: str) -> str:
        args = json.loads(arguments)
        task_prompt = args["task_prompt"]

        logger.info("🚀 主 Agent 发起委派！正在拉起探路者: [{}]...", task_prompt)

        try:
            summary = await self.engine.run_sub(
                task_prompt=task_prompt,
                read_only_registry=self.read_only_registry,
                reporter=self.reporter,
            )
            logger.info("✅ 子智能体任务结束。报告返回给主干...")
            return f"【子智能体探索报告】:\n{summary}"
        except Exception as e:
            return f"子智能体执行失败: {e}"
