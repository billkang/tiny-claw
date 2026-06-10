"""Session 单元测试。"""

import pytest

from py_claw.context.session import Session
from py_claw.schema.message import Message, ToolCall


@pytest.fixture
def session():
    return Session(id="test-session", work_dir="/tmp")


@pytest.mark.asyncio
async def test_append_and_get_working_memory(session):
    msg1 = Message(role="user", content="hello")
    msg2 = Message(role="assistant", content="hi")
    await session.append(msg1, msg2)

    mem = await session.get_working_memory()
    assert len(mem) == 2
    assert mem[0].content == "hello"
    assert mem[1].content == "hi"


@pytest.mark.asyncio
async def test_working_memory_limit(session):
    msgs = [Message(role="user", content=f"msg{i}") for i in range(10)]
    await session.append(*msgs)

    mem = await session.get_working_memory(3)
    assert len(mem) == 3
    assert mem[0].content == "msg7"


@pytest.mark.asyncio
async def test_orphan_tool_result_removal(session):
    """截断边缘的孤儿 ToolResult 应被自动丢弃。"""
    msgs = [
        Message(role="user", content="first"),
        Message(role="assistant", content="ok"),
        Message(role="user", content="tool result", tool_call_id="tc1"),
        Message(role="user", content="normal"),
    ]
    await session.append(*msgs)

    mem = await session.get_working_memory(2)
    # 取最后2条: tc1(tool_result), normal → 应丢弃 tc1
    assert len(mem) == 1
    assert mem[0].content == "normal"


@pytest.mark.asyncio
async def test_record_usage(session):
    await session.record_usage(100, 50, 0.001)
    assert session.total_prompt_tokens == 100
    assert session.total_completion_tokens == 50
    assert session.total_cost_cny == 0.001

    await session.record_usage(200, 100, 0.002)
    assert session.total_prompt_tokens == 300
    assert session.total_completion_tokens == 150
    assert session.total_cost_cny == pytest.approx(0.003)
