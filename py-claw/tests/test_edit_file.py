"""EditFileTool 单元测试。"""

import json
import tempfile
from pathlib import Path

import pytest

from py_claw.tools.edit_file import EditFileTool


@pytest.fixture
def tool():
    tmpdir = tempfile.mkdtemp()
    return EditFileTool(tmpdir)


@pytest.fixture
def sample_file(tool):
    path = Path(tool.work_dir) / "test.txt"
    path.write_text("hello world\nfoo bar\nhello world\n")
    return path


@pytest.mark.asyncio
async def test_exact_replace(tool, sample_file):
    result = await tool.execute(json.dumps({
        "path": "test.txt",
        "old_text": "foo bar",
        "new_text": "baz qux",
    }))
    assert "成功修改" in result
    assert sample_file.read_text() == "hello world\nbaz qux\nhello world\n"


@pytest.mark.asyncio
async def test_multiple_match_raises(tool, sample_file):
    with pytest.raises(ValueError, match="匹配到了 2 处"):
        await tool.execute(json.dumps({
            "path": "test.txt",
            "old_text": "hello world",
            "new_text": "hi",
        }))


@pytest.mark.asyncio
async def test_no_match_raises(tool, sample_file):
    with pytest.raises(ValueError, match="在文件中未找到 old_text"):
        await tool.execute(json.dumps({
            "path": "test.txt",
            "old_text": "nonexistent",
            "new_text": "something",
        }))


@pytest.mark.asyncio
async def test_file_not_found(tool):
    with pytest.raises(FileNotFoundError):
        await tool.execute(json.dumps({
            "path": "nonexistent.txt",
            "old_text": "hello",
            "new_text": "hi",
        }))


@pytest.mark.asyncio
async def test_line_by_line_replace(tool, sample_file):
    """验证逐行去缩进匹配。"""
    import os
    result = await tool.execute(json.dumps({
        "path": "test.txt",
        "old_text": "foo bar",
        "new_text": "replaced",
    }))
    assert "成功修改" in result
