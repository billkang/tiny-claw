"""终端输出 Reporter — 使用 Rich 实现漂亮的控制台输出。"""

from __future__ import annotations

from rich.console import Console
from rich.panel import Panel
from rich.markup import escape
from rich.syntax import Syntax
from rich.text import Text

from py_claw.engine.reporter import Reporter


class TerminalReporter(Reporter):
    """向终端输出彩色的 Agent 运行状态。"""

    def __init__(self) -> None:
        self.console = Console()

    async def on_thinking(self) -> None:
        self.console.print(Panel(
            "[dim]模型正在推理...[/dim]",
            title="[yellow]🤔 思考中[/yellow]",
            border_style="yellow",
            padding=(0, 1),
        ))

    async def on_tool_call(self, tool_name: str, args: str) -> None:
        display_args = args.replace("\n", "\\n").replace("\r", "\\r")
        if len(display_args) > 150:
            display_args = display_args[:150] + "... (已截断)"

        self.console.print(Panel(
            f"[bold cyan]{escape(tool_name)}[/bold cyan]\n[dim]{escape(display_args)}[/dim]",
            title="[blue]🛠️ 调用工具[/blue]",
            border_style="blue",
            padding=(0, 1),
        ))

    async def on_tool_result(self, tool_name: str, result: str, is_error: bool) -> None:
        if is_error:
            self.console.print(Panel(
                f"[bold red]{escape(tool_name)}[/bold red]\n{escape(result[:200])}",
                title="[red]❌ 执行失败[/red]",
                border_style="red",
                padding=(0, 1),
            ))
        else:
            self.console.print(Panel(
                f"[bold green]{escape(tool_name)}[/bold green]",
                title="[green]✅ 执行成功[/green]",
                border_style="green",
                padding=(0, 1),
            ))

    async def on_message(self, content: str) -> None:
        if not content:
            return
        panel = Panel(
            Syntax(content, "markdown", theme="default"),
            title="🤖 Agent 回复",
            border_style="cyan",
            padding=(1, 2),
        )
        self.console.print(panel)
