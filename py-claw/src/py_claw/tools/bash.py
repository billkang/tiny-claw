"""Bash 命令执行工具 — 使用 asyncio subprocess 实现。"""

from __future__ import annotations

import asyncio
import json

from py_claw.schema.message import ToolDefinition
from py_claw.tools.base import BaseTool


class BashTool(BaseTool):
    TIMEOUT = 30  # seconds
    MAX_LEN = 8000

    def __init__(self, work_dir: str) -> None:
        self.work_dir = work_dir

    def name(self) -> str:
        return "bash"

    def definition(self) -> ToolDefinition:
        return ToolDefinition(
            name=self.name(),
            description="在当前工作区执行任意的 bash 命令。支持链式命令(如 &&)。返回标准输出和标准错误。",
            input_schema={
                "type": "object",
                "properties": {
                    "command": {
                        "type": "string",
                        "description": "要执行的 bash 命令",
                    },
                },
                "required": ["command"],
            },
        )

    async def execute(self, arguments: str) -> str:
        args = json.loads(arguments)
        command = args["command"]

        try:
            proc = await asyncio.create_subprocess_shell(
                command,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
                cwd=self.work_dir,
            )

            try:
                stdout, stderr = await asyncio.wait_for(
                    proc.communicate(), timeout=self.TIMEOUT,
                )
            except asyncio.TimeoutError:
                proc.kill()
                await proc.wait()
                return f"[警告: 命令执行超时({self.TIMEOUT}s)，已被系统强制终止。]"

            output = ""
            if stdout:
                output += stdout.decode("utf-8", errors="replace")
            if stderr:
                error_text = stderr.decode("utf-8", errors="replace")
                if proc.returncode != 0:
                    output = f"执行报错 (exit {proc.returncode}):\n{error_text}\n{output}"
                else:
                    output += error_text

            if not output.strip():
                return "命令执行成功，无终端输出。"

            if len(output) > self.MAX_LEN:
                return f"{output[:self.MAX_LEN]}\n\n...[终端输出过长，已截断至前 {self.MAX_LEN} 字节]..."

            return output.strip()

        except Exception as e:
            return f"执行报错: {e}"
