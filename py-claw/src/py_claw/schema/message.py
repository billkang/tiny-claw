"""数据模型层 — Message、ToolCall、ToolResult 等核心类型。"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


class Role:
    """角色常量，避免 magic string。"""
    SYSTEM = "system"
    USER = "user"
    ASSISTANT = "assistant"


@dataclass
class Usage:
    """单次 LLM API 调用的 Token 消耗。"""
    prompt_tokens: int = 0
    completion_tokens: int = 0


@dataclass
class ToolCall:
    """大模型请求执行的工具调用。"""
    id: str
    name: str
    arguments: str  # JSON string


@dataclass
class ToolResult:
    """工具执行后的返回结果。"""
    tool_call_id: str
    output: str
    is_error: bool = False


@dataclass
class ToolDefinition:
    """工具的 Schema 定义，用于大模型 Function Calling。"""
    name: str
    description: str
    input_schema: dict[str, Any] = field(default_factory=dict)


@dataclass
class Message:
    """对话消息，支持多种角色与工具调用。"""
    role: str
    content: str = ""
    tool_calls: list[ToolCall] = field(default_factory=list)
    tool_call_id: str = ""
    usage: Usage | None = None
