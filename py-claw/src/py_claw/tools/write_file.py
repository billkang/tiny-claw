"""创建/覆写文件工具。"""

from __future__ import annotations

import json
from pathlib import Path

from py_claw.schema.message import ToolDefinition
from py_claw.tools.base import BaseTool


class WriteFileTool(BaseTool):
    def __init__(self, work_dir: str) -> None:
        self.work_dir = Path(work_dir)

    def name(self) -> str:
        return "write_file"

    def definition(self) -> ToolDefinition:
        return ToolDefinition(
            name=self.name(),
            description="创建或覆盖写入一个文件。如果目录不存在会自动创建。请提供相对于工作区的相对路径。",
            input_schema={
                "type": "object",
                "properties": {
                    "path": {
                        "type": "string",
                        "description": "要写入的文件路径, 如 src/main.py",
                    },
                    "content": {
                        "type": "string",
                        "description": "要写入的完整文件内容",
                    },
                },
                "required": ["path", "content"],
            },
        )

    async def execute(self, arguments: str) -> str:
        args = json.loads(arguments)
        filepath = self.work_dir / args["path"]
        content = args["content"]

        filepath.parent.mkdir(parents=True, exist_ok=True)
        filepath.write_text(content, encoding="utf-8")

        return f"成功将内容写入到文件: {args['path']}"
