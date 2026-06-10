"""人工审批 — 高危操作挂起等待人类裁决。"""

from __future__ import annotations

import asyncio
import re
from dataclasses import dataclass, field


@dataclass
class ApprovalResult:
    allowed: bool
    reason: str = ""


class ApprovalManager:
    """审批管理器，挂起高危工具调用直到收到审批结果。"""

    def __init__(self) -> None:
        self._pending: dict[str, asyncio.Future[ApprovalResult]] = {}
        self._lock = asyncio.Lock()

    async def wait_for_approval(
        self,
        task_id: str,
        tool_name: str,
        args: str,
        reporter: object | None = None,
    ) -> tuple[bool, str]:
        future: asyncio.Future[ApprovalResult] = asyncio.get_event_loop().create_future()

        async with self._lock:
            self._pending[task_id] = future

        notice = (
            f"⚠️ **高危操作审批请求**\n"
            f"Agent 试图执行以下动作:\n"
            f"- 工具: {tool_name}\n"
            f"- 参数: {args}\n\n"
            f"任务 ID: **{task_id}**\n\n"
            f"👉 请回复 \"approve {task_id}\" 或 \"reject {task_id}\" 决定是否放行。"
        )

        # 如果有 Feishu Reporter 则发飞书消息
        if reporter and hasattr(reporter, "send_msg"):
            reporter.send_msg(notice)
        else:
            print(f"\n[需要审批 TaskID: {task_id}] {notice}\n")

        result = await future

        async with self._lock:
            self._pending.pop(task_id, None)

        return result.allowed, result.reason

    async def resolve_approval(self, task_id: str, allowed: bool, reason: str) -> None:
        async with self._lock:
            future = self._pending.get(task_id)
        if future and not future.done():
            future.set_result(ApprovalResult(allowed=allowed, reason=reason))


# 全局单例
global_approval_mgr = ApprovalManager()


def is_dangerous_command(tool_name: str, args: str) -> bool:
    """简单规则判断是否触发人工审批。"""
    if tool_name == "read_file":
        return False

    if tool_name in ("write_file", "edit_file"):
        return True

    if tool_name == "bash":
        dangerous_patterns = [
            r"rm\s+-r",
            r"sudo\s+",
            r"drop\s+",
            r">.*\.py",
            r"nginx\s+-s",
            r"systemctl\s+",
            r"kill\s+",
        ]
        for p in dangerous_patterns:
            if re.search(p, args):
                return True

    return False
