"""编辑文件工具 — 带模糊匹配的字符串替换。"""

from __future__ import annotations

import json
from pathlib import Path

from py_claw.schema.message import ToolDefinition
from py_claw.tools.base import BaseTool


class EditFileTool(BaseTool):
    def __init__(self, work_dir: str) -> None:
        self.work_dir = Path(work_dir)

    def name(self) -> str:
        return "edit_file"

    def definition(self) -> ToolDefinition:
        return ToolDefinition(
            name=self.name(),
            description="对现有文件进行局部的字符串替换。这比重写整个文件更安全、更快速。请提供足够的 old_text 上下文以确保匹配的唯一性。",
            input_schema={
                "type": "object",
                "properties": {
                    "path": {
                        "type": "string",
                        "description": "要修改的文件路径",
                    },
                    "old_text": {
                        "type": "string",
                        "description": "文件中原有的文本，必须包含足够的上下文以确保唯一性",
                    },
                    "new_text": {
                        "type": "string",
                        "description": "要替换成的新文本",
                    },
                },
                "required": ["path", "old_text", "new_text"],
            },
        )

    async def execute(self, arguments: str) -> str:
        args = json.loads(arguments)
        filepath = self.work_dir / args["path"]
        old_text = args["old_text"]
        new_text = args["new_text"]

        if not filepath.exists():
            raise FileNotFoundError(f"文件不存在: {filepath}")

        content = filepath.read_text(encoding="utf-8")

        # L1: 精确匹配
        count = content.count(old_text)
        if count == 1:
            new_content = content.replace(old_text, new_text, 1)
        elif count > 1:
            raise ValueError(
                f"old_text 匹配到了 {count} 处，请提供更多的上下文代码以确保唯一性"
            )
        else:
            # L2: 换行符归一化
            normalized = content.replace("\r\n", "\n")
            normalized_old = old_text.replace("\r\n", "\n")
            count = normalized.count(normalized_old)

            if count == 1:
                new_content = normalized.replace(normalized_old, new_text, 1)
            elif count > 1:
                raise ValueError(
                    f"归一化后匹配到了 {count} 处，请提供更多上下文"
                )
            else:
                # L3: 逐行去缩进匹配
                new_content = self._line_by_line_replace(normalized, normalized_old, new_text)

        filepath.write_text(new_content, encoding="utf-8")
        return f"✅ 成功修改文件: {args['path']}"

    def _line_by_line_replace(self, content: str, old_text: str, new_text: str) -> str:
        content_lines = content.splitlines(keepends=True)
        old_lines = [l.strip() for l in old_text.strip().splitlines()]

        if not old_lines or len(content_lines) < len(old_lines):
            raise ValueError("找不到该代码片段")

        match_count = 0
        match_start = -1
        match_end = -1

        for i in range(len(content_lines) - len(old_lines) + 1):
            is_match = True
            for j in range(len(old_lines)):
                if content_lines[i + j].strip() != old_lines[j]:
                    is_match = False
                    break
            if is_match:
                match_count += 1
                match_start = i
                match_end = i + len(old_lines)

        if match_count == 0:
            raise ValueError("在文件中未找到 old_text，请检查内容和缩进")
        if match_count > 1:
            raise ValueError(f"模糊匹配到了 {match_count} 处代码，请提供更多上下文以定位")

        result = content_lines[:match_start] + [new_text] + content_lines[match_end:]
        return "".join(result)
