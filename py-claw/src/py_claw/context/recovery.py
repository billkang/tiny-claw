"""错误恢复 — 分析工具执行失败的特征并注入恢复建议。"""

from __future__ import annotations


class RecoveryManager:
    """分析错误信息，匹配已知模式，注入恢复建议。"""

    def analyze_and_inject(self, tool_name: str, raw_error: str) -> str:
        lower_error = raw_error.lower()

        hint = ""

        if tool_name == "edit_file":
            if "在文件中未找到" in raw_error or "找不到该代码片段" in raw_error:
                hint = (
                    "你提供的 old_text 与文件当前内容不一致，或者缺少必要的缩进。"
                    "请先使用 read_file 工具重新读取该文件，获取最新、准确的内容后，再重新发起编辑。"
                )
            elif "匹配到了多处" in raw_error or "提供更多上下文" in raw_error:
                hint = (
                    "你的 old_text 不够具体，命中了多个相同代码块。"
                    "请在 old_text 中增加上下相邻的几行代码，以确保替换的唯一性。"
                )

        elif tool_name in ("read_file", "write_file"):
            if "no such file or directory" in lower_error:
                hint = (
                    "路径似乎不正确。请先使用 bash 执行 ls -la 或 find 命令查找正确的目录结构和文件名。"
                )
            elif "permission denied" in lower_error:
                hint = "你没有权限操作该文件。请检查工作区限制。"

        elif tool_name == "bash":
            if "command not found" in lower_error:
                hint = "系统中未安装该命令。请先思考是否有替代命令，或需要先安装。"
            elif "超时" in raw_error or "deadline" in lower_error:
                hint = (
                    "该命令执行超时。如果是常驻服务，请将其转入后台执行（例如使用 nohup ... &）。"
                )
            elif "syntax error" in lower_error:
                hint = "Bash 语法错误。请检查引号转义或特殊字符。"

        if not hint:
            return raw_error

        return f"{raw_error}\n\n[系统救援指南]: {hint}"
