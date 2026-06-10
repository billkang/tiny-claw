"""Reporter 协议 — 输出抽象的鸭子类型。"""

from __future__ import annotations

from typing import Protocol, runtime_checkable


@runtime_checkable
class Reporter(Protocol):
    """负责在 Agent 执行过程中向用户输出状态信息。"""

    async def on_thinking(self) -> None: ...

    async def on_tool_call(self, tool_name: str, args: str) -> None: ...

    async def on_tool_result(self, tool_name: str, result: str, is_error: bool) -> None: ...

    async def on_message(self, content: str) -> None: ...
