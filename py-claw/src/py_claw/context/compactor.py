"""上下文压缩 — 当消息历史超过阈值时智能截断。"""

from __future__ import annotations

from loguru import logger

from py_claw.schema.message import Message


class Compactor:
    """上下文压缩器，在历史消息超长时折叠早期内容。"""

    def __init__(self, max_chars: int = 200_000, retain_last_msgs: int = 6) -> None:
        self.max_chars = max_chars
        self.retain_last_msgs = retain_last_msgs

    def compact(self, msgs: list[Message]) -> list[Message]:
        current_length = self._estimate_length(msgs)
        if current_length < self.max_chars:
            return msgs

        logger.warning(
            "上下文超限: {} 字符 > 阈值 {}, 触发压缩",
            current_length, self.max_chars,
        )

        compacted: list[Message] = []
        protect_start = len(msgs) - self.retain_last_msgs

        for i, msg in enumerate(msgs):
            if msg.role == "system":
                compacted.append(msg)
                continue

            is_working = i >= protect_start
            new_msg = Message(role=msg.role, tool_calls=list(msg.tool_calls))

            if msg.role == "user" and msg.tool_call_id:
                if not is_working:
                    new_msg.content = (
                        f"[早期工具输出已折叠，原始长度: {len(msg.content)} 字节]"
                    )
                else:
                    MAX_KEEP = 1000
                    if len(msg.content) > MAX_KEEP:
                        head = msg.content[:500]
                        tail = msg.content[-500:]
                        new_msg.content = f"{head}\n\n...[中间 {len(msg.content) - MAX_KEEP} 字节已截断]...\n\n{tail}"
                    else:
                        new_msg.content = msg.content
                new_msg.tool_call_id = msg.tool_call_id
            elif msg.role == "assistant" and msg.content:
                if not is_working and len(msg.content) > 200:
                    new_msg.content = "[早期推理思考已折叠]..."
                else:
                    new_msg.content = msg.content
                new_msg.tool_calls = list(msg.tool_calls)
            else:
                new_msg.content = msg.content

            compacted.append(new_msg)

        new_length = self._estimate_length(compacted)
        logger.info("压缩完成: {} → {} 字符", current_length, new_length)
        return compacted

    def _estimate_length(self, msgs: list[Message]) -> int:
        length = 0
        for msg in msgs:
            length += len(msg.content)
            for tc in msg.tool_calls:
                length += len(tc.name) + len(tc.arguments)
        return length
