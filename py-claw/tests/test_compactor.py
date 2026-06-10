"""Compactor 单元测试。"""

from py_claw.context.compactor import Compactor
from py_claw.schema.message import Message, ToolCall


def test_no_compaction_needed():
    """消息总长未超过阈值时原样返回。"""
    c = Compactor(max_chars=1000, retain_last_msgs=2)
    msgs = [
        Message(role="system", content="sys"),
        Message(role="user", content="hello"),
    ]
    result = c.compact(msgs)
    assert len(result) == 2
    assert result[0].content == "sys"
    assert result[1].content == "hello"


def test_truncates_early_tool_output():
    """早期工具输出超出保留区时折叠。"""
    c = Compactor(max_chars=50, retain_last_msgs=1)
    long_content = "x" * 500
    msgs = [
        Message(role="system", content="sys"),
        Message(role="user", content=long_content, tool_call_id="tc1"),
        Message(role="user", content="final"),
    ]
    result = c.compact(msgs)
    assert len(result) == 3
    # 早期的 tool result 被折叠
    assert "早期工具输出已折叠" in result[1].content
    # 最后一条保持不变
    assert result[2].content == "final"


def test_preserves_system_message():
    """System 消息永远不被压缩。"""
    c = Compactor(max_chars=10, retain_last_msgs=1)
    msgs = [
        Message(role="system", content="long system prompt"),
        Message(role="user", content="hello"),
    ]
    result = c.compact(msgs)
    assert result[0].content == "long system prompt"


def test_working_memory_kept_intact():
    """工作记忆区 (最后 N 条) 的消息被保留。"""
    c = Compactor(max_chars=10, retain_last_msgs=2)
    msgs = [
        Message(role="user", content="old", tool_call_id="t1"),
        Message(role="user", content="new", tool_call_id="t2"),
    ]
    result = c.compact(msgs)
    assert "早期工具输出已折叠" not in result[0].content
