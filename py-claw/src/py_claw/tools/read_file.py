"""读取文件工具。"""

from __future__ import annotations

import json
from pathlib import Path

from py_claw.schema.message import ToolDefinition
from py_claw.tools.base import BaseTool


class ReadFileTool(BaseTool):
    def __init__(self, work_dir: str) -> None:
        self.work_dir = Path(work_dir)

    def name(self) -> str:
        return "read_file"

    def definition(self) -> ToolDefinition:
        return ToolDefinition(
            name=self.name(),
            description="读取指定路径的文件内容。请提供相对工作区的路径。",
            input_schema={
                "type": "object",
                "properties": {
                    "path": {
                        "type": "string",
                        "description": "要读取的文件路径, 如 src/main.py",
                    },
                },
                "required": ["path"],
            },
        )

    async def execute(self, arguments: str) -> str:
        args = json.loads(arguments)
        filepath = self.work_dir / args["path"]

        if not filepath.exists():
            raise FileNotFoundError(f"文件不存在: {filepath}")

        content = filepath.read_text(encoding="utf-8")

        MAX_LEN = 8000
        if len(content) > MAX_LEN:
            return f"{content[:MAX_LEN]}\n\n...[内容过长，已被系统截断至前 {MAX_LEN} 字节]..."

        return content
