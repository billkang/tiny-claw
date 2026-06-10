"""LLM 提供商接口 — 采用 typing.Protocol 实现静态鸭子类型。"""

from __future__ import annotations

from typing import Protocol, runtime_checkable

from py_claw.schema.message import Message, ToolDefinition


@runtime_checkable
class LLMProvider(Protocol):
    """大模型提供商的统一协议。"""

    async def generate(
        self,
        messages: list[Message],
        available_tools: list[ToolDefinition] | None = None,
    ) -> Message:
        """接收对话历史与可用工具列表，返回模型响应。"""
        ...
