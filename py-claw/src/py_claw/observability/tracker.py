"""成本追踪器 — 装饰 LLM Provider，自动记录 Token 消耗和费用。"""

from __future__ import annotations

import time
from typing import Any

from loguru import logger

from py_claw.context.session import Session
from py_claw.schema.message import Message, ToolDefinition

# 定价模型 (元/百万 tokens)
PRICING: dict[str, dict[str, float]] = {
    "glm-4.5-air": {"input": 0.15, "output": 0.15},
    "glm-4-plus": {"input": 0.50, "output": 0.50},
    "deepseek-chat": {"input": 0.14, "output": 0.28},
    "gpt-4o-mini": {"input": 0.15, "output": 0.60},
}


class CostTracker:
    """Provider 装饰器，在每次 LLM 调用后记录 Token 消耗与费用。"""

    def __init__(self, next_provider: Any, model_name: str, session: Session) -> None:
        self._next = next_provider
        self._model = model_name
        self._session = session

    async def generate(
        self,
        messages: list[Message],
        available_tools: list[ToolDefinition] | None = None,
    ) -> Message:
        start = time.time()

        resp = await self._next.generate(messages, available_tools)

        latency = time.time() - start

        if resp.usage:
            pt = resp.usage.prompt_tokens
            ct = resp.usage.completion_tokens

            cost = 0.0
            if self._model in PRICING:
                p = PRICING[self._model]
                cost = (pt * p["input"] + ct * p["output"]) / 1_000_000.0

            logger.info(
                "📊 API 调用完成 | 耗时: {:.2f}s | 输入: {} tk | 输出: {} tk | 花费: ¥{:.6f}",
                latency, pt, ct, cost,
            )

            await self._session.record_usage(pt, ct, cost)
            logger.info("当前会话 ({}) 累计花费: ¥{:.6f}", self._session.id, self._session.total_cost_cny)
        else:
            logger.warning("⚠️ API 调用完成，但未返回 Usage 数据 | 耗时: {:.2f}s", latency)

        return resp
