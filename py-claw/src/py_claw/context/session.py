"""会话管理 — 维护多轮对话的持久化历史与账单。"""

from __future__ import annotations

import time
from asyncio import Lock
from dataclasses import dataclass, field

from py_claw.schema.message import Message


@dataclass
class Session:
    """一次 Agent 任务的会话，维护消息历史与累计消耗。"""
    id: str
    work_dir: str = "."
    created_at: float = field(default_factory=time.time)
    updated_at: float = field(default_factory=time.time)

    total_prompt_tokens: int = 0
    total_completion_tokens: int = 0
    total_cost_cny: float = 0.0

    _history: list[Message] = field(default_factory=list, repr=False)
    _lock: Lock = field(default_factory=Lock, repr=False)

    async def append(self, *msgs: Message) -> None:
        async with self._lock:
            self._history.extend(msgs)
            self.updated_at = time.time()

    async def get_working_memory(self, limit: int = 0) -> list[Message]:
        """获取最近的 N 条消息作为工作记忆。
        自动丢弃截断边缘的孤儿 ToolResult。
        """
        async with self._lock:
            total = len(self._history)
            if total <= limit or limit <= 0:
                return list(self._history)

            result = list(self._history[total - limit:])

            # 丢弃截断边缘的孤儿 ToolResult
            while result and result[0].role == "user" and result[0].tool_call_id:
                result.pop(0)

            return result

    async def record_usage(self, prompt: int, completion: int, cost: float) -> None:
        async with self._lock:
            self.total_prompt_tokens += prompt
            self.total_completion_tokens += completion
            self.total_cost_cny += cost

    @property
    def history(self) -> list[Message]:
        return list(self._history)


class SessionManager:
    """全局会话管理器，按 ID 复用。"""

    def __init__(self) -> None:
        self._sessions: dict[str, Session] = {}
        self._lock = Lock()

    async def get_or_create(self, session_id: str, work_dir: str = ".") -> Session:
        async with self._lock:
            if session_id in self._sessions:
                return self._sessions[session_id]
            sess = Session(id=session_id, work_dir=work_dir)
            self._sessions[session_id] = sess
            return sess


# 全局单例
global_session_mgr = SessionManager()
