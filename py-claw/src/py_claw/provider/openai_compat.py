"""OpenAI 兼容协议 Provider — 适配智谱、DeepSeek、OpenAI 等。"""

from __future__ import annotations

import json
import os

from openai import AsyncOpenAI
from loguru import logger

from py_claw.schema.message import Message, Role, ToolCall, Usage, ToolDefinition


class OpenAICompatProvider:
    """兼容 OpenAI API 协议的大模型提供商。

    通过配置 base_url 可对接 Zhipu / DeepSeek / OpenAI 等。
    """

    def __init__(
        self,
        model: str = "glm-4.5-air",
        base_url: str | None = None,
        api_key: str | None = None,
    ) -> None:
        api_key = api_key or os.getenv("ZHIPU_API_KEY")
        if not api_key:
            raise RuntimeError("请设置 ZHIPU_API_KEY 环境变量或在初始化时传入 api_key")

        base_url = base_url or os.getenv("OPENAI_BASE_URL", "https://open.bigmodel.cn/api/paas/v4/")

        self.client = AsyncOpenAI(api_key=api_key, base_url=base_url)
        self.model = model

    async def generate(
        self,
        messages: list[Message],
        available_tools: list[ToolDefinition] | None = None,
    ) -> Message:
        openai_msgs: list[dict] = []
        for msg in messages:
            if msg.role == Role.SYSTEM:
                openai_msgs.append({"role": "system", "content": msg.content})
            elif msg.role == Role.USER:
                if msg.tool_call_id:
                    openai_msgs.append({
                        "role": "tool",
                        "content": msg.content,
                        "tool_call_id": msg.tool_call_id,
                    })
                else:
                    openai_msgs.append({"role": "user", "content": msg.content})
            elif msg.role == Role.ASSISTANT:
                entry: dict = {"role": "assistant", "content": msg.content}
                if msg.tool_calls:
                    entry["tool_calls"] = [
                        {
                            "id": tc.id,
                            "type": "function",
                            "function": {
                                "name": tc.name,
                                "arguments": tc.arguments,
                            },
                        }
                        for tc in msg.tool_calls
                    ]
                openai_msgs.append(entry)

        kwargs = {
            "model": self.model,
            "messages": openai_msgs,
        }

        if available_tools:
            tools = []
            for t in available_tools:
                tools.append({
                    "type": "function",
                    "function": {
                        "name": t.name,
                        "description": t.description,
                        "parameters": t.input_schema,
                    },
                })
            kwargs["tools"] = tools

        try:
            response = await self.client.chat.completions.create(**kwargs)  # type: ignore
        except Exception as e:
            logger.error("API 请求失败: {}", e)
            raise

        choice = response.choices[0]
        data = choice.message

        result = Message(role=Role.ASSISTANT, content=data.content or "")

        if response.usage:
            result.usage = Usage(
                prompt_tokens=response.usage.prompt_tokens or 0,
                completion_tokens=response.usage.completion_tokens or 0,
            )

        if data.tool_calls:
            for tc in data.tool_calls:
                if tc.type == "function":
                    result.tool_calls.append(ToolCall(
                        id=tc.id,
                        name=tc.function.name,
                        arguments=tc.function.arguments or "{}",
                    ))

        return result
