"""工具系统基础 — BaseTool 协议 + Registry（含中间件链）。"""

from __future__ import annotations

from typing import Any, Callable, Protocol, runtime_checkable

from loguru import logger

from py_claw.schema.message import ToolCall, ToolDefinition, ToolResult


ToolMiddleware = Callable[[ToolCall], tuple[bool, str]]


@runtime_checkable
class BaseTool(Protocol):
    """工具必须实现的三件套：名称、定义、执行。"""

    def name(self) -> str: ...

    def definition(self) -> ToolDefinition: ...

    async def execute(self, arguments: str) -> str: ...


class Registry:
    """工具注册表，支持注册、中间件链和并发执行。"""

    def __init__(self) -> None:
        self._tools: dict[str, BaseTool] = {}
        self._middlewares: list[ToolMiddleware] = []

    def register(self, tool: BaseTool) -> None:
        name = tool.name()
        if name in self._tools:
            logger.warning("工具 '{}' 已注册，将被覆盖", name)
        self._tools[name] = tool
        logger.info("成功挂载工具: {}", name)

    def use(self, middleware: ToolMiddleware) -> None:
        """注册全局中间件。"""
        self._middlewares.append(middleware)

    def get_available_tools(self) -> list[ToolDefinition]:
        return [t.definition() for t in self._tools.values()]

    async def execute(self, call: ToolCall) -> ToolResult:
        # 1. 路由查找
        tool = self._tools.get(call.name)
        if tool is None:
            return ToolResult(
                tool_call_id=call.id,
                output=f"Error: 系统中不存在名为 '{call.name}' 的工具。",
                is_error=True,
            )

        # 2. 中间件链
        for mw in self._middlewares:
            allowed, reason = mw(call)
            if not allowed:
                logger.warning("工具 {} 被中间件拦截: {}", call.name, reason)
                return ToolResult(
                    tool_call_id=call.id,
                    output=f"执行被系统拦截。原因: {reason}",
                    is_error=True,
                )

        # 3. 执行
        try:
            output = await tool.execute(call.arguments)
            return ToolResult(tool_call_id=call.id, output=output, is_error=False)
        except Exception as e:
            return ToolResult(
                tool_call_id=call.id,
                output=f"Error executing {call.name}: {e}",
                is_error=True,
            )
