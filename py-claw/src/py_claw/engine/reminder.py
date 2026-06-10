"""死循环检测 — 监控连续相同工具失败并注入干预。"""

from __future__ import annotations

import hashlib
import json

from loguru import logger

from py_claw.schema.message import Message, Role, ToolCall, ToolResult


class ReminderInjector:
    """检测连续相同参数的工具执行失败，超过阈值则注入提醒。"""

    def __init__(self) -> None:
        self._consecutive_failures: dict[str, int] = {}

    def check_and_inject(self, last_tool_call: ToolCall, last_result: ToolResult) -> Message | None:
        fingerprint = self._fingerprint(last_tool_call)

        if not last_result.is_error:
            self._consecutive_failures.clear()
            return None

        self._consecutive_failures[fingerprint] = (
            self._consecutive_failures.get(fingerprint, 0) + 1
        )
        fail_count = self._consecutive_failures[fingerprint]

        logger.info(
            "监控到工具 {} 执行失败，该参数特征连续失败次数: {}",
            last_tool_call.name, fail_count,
        )

        if fail_count >= 3:
            logger.warning("触发死循环干预！注入强力修正指令。")

            nudge = (
                f"[SYSTEM REMINDER 警告]\n"
                f"你似乎陷入了死循环。你刚刚连续 {fail_count} 次使用相同的参数调用了 "
                f"'{last_tool_call.name}' 工具，并且都失败了。\n"
                f"请立即停止这种无效的重试！你的注意力被当前的报错过度吸引了。\n"
                f"你需要：\n"
                f"1. 停止猜测参数。跳出当前的局部思维。\n"
                f"2. 彻底改变你的策略。\n"
                f"3. 如果你确实无法通过系统工具解决当前问题，请直接结束任务并向用户说明你需要什么人工帮助，"
                f"而不是继续盲目消耗 API 资源尝试。"
            )
            return Message(role=Role.USER, content=nudge)

        return None

    def _fingerprint(self, call: ToolCall) -> str:
        raw = f"{call.name}:{call.arguments}"
        return hashlib.md5(raw.encode()).hexdigest()
