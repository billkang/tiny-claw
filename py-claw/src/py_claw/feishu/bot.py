"""飞书 Bot 集成 — 通过 FastAPI Webhook 接收飞书消息并调度 Agent。"""

from __future__ import annotations

import asyncio
import json
import os
from typing import Callable

from fastapi import APIRouter, Request
from loguru import logger

from py_claw.context.session import Session, global_session_mgr
from py_claw.engine.loop import AgentEngine
from py_claw.engine.reporter import Reporter
from py_claw.feishu.approval import global_approval_mgr
from py_claw.schema.message import Message, Role

# AgentEngineFactory: 根据 Session 动态创建引擎
AgentEngineFactory = Callable[[Session], AgentEngine]


class FeishuReporter(Reporter):
    """向飞书群聊发送 Agent 状态消息。"""

    def __init__(self, webhook_url: str) -> None:
        self.webhook_url = webhook_url
        self._session = None  # 可选 httpx.AsyncClient session

    def send_msg(self, text: str) -> None:
        """发送消息到飞书（同步抛给后台事件循环）。"""
        try:
            loop = asyncio.get_event_loop()
            if loop.is_running():
                asyncio.ensure_future(self._send_async(text))
        except RuntimeError:
            pass

    async def _send_async(self, text: str) -> None:
        import httpx
        payload = {
            "msg_type": "text",
            "content": {"text": text},
        }
        async with httpx.AsyncClient() as client:
            await client.post(self.webhook_url, json=payload)

    async def on_thinking(self) -> None:
        self.send_msg("🤔 模型正在慢思考 (Thinking)...")

    async def on_tool_call(self, tool_name: str, args: str) -> None:
        self.send_msg(f"🛠️ **正在执行工具**: `{tool_name}`\n参数: `{args}`")

    async def on_tool_result(self, tool_name: str, result: str, is_error: bool) -> None:
        if is_error:
            self.send_msg(f"⚠️ **执行报错** ({tool_name}):\n{result[:200]}")
        else:
            self.send_msg(f"✅ **执行成功** ({tool_name})")

    async def on_message(self, content: str) -> None:
        self.send_msg(content)


class FeishuBot:
    """飞书 Bot 调度器，通过 FastAPI 路由接入。"""

    def __init__(
        self,
        factory: AgentEngineFactory,
        work_dir: str,
        webhook_url: str | None = None,
    ) -> None:
        self.factory = factory
        self.work_dir = work_dir
        self.webhook_url = webhook_url or os.getenv("FEISHU_WEBHOOK_URL", "")

    def get_router(self) -> APIRouter:
        router = APIRouter()

        @router.post("/webhook/event")
        async def handle_event(request: Request) -> dict:
            body = await request.json()
            logger.debug("收到飞书事件: {}", body)

            # 简化处理：仅处理消息事件
            event = body.get("event", {})
            msg = event.get("message", {})
            content_str = msg.get("content", "{}")
            chat_id = msg.get("chat_id", "")

            try:
                content_data = json.loads(content_str)
                text = content_data.get("text", "")
            except (json.JSONDecodeError, KeyError):
                text = content_str

            text = text.strip()

            # 拦截审批指令
            if text.startswith("approve ") or text.startswith("reject "):
                await self._handle_approval(text)
                return {"code": 0}

            # 异步启动 Agent 执行
            if text:
                asyncio.ensure_future(self._handle_agent_run(chat_id, text))

            return {"code": 0}

        return router

    async def _handle_approval(self, text: str) -> None:
        parts = text.split(maxsplit=1)
        if len(parts) < 2:
            return
        action, task_id = parts[0], parts[1]
        allowed = action == "approve"
        reason = "人类管理员已批准操作" if allowed else "人类管理员已拒绝操作"
        await global_approval_mgr.resolve_approval(task_id, allowed, reason)
        logger.info("审批处理: {} {} ({})", action, task_id, reason)

    async def _handle_agent_run(self, chat_id: str, prompt: str) -> None:
        reporter = FeishuReporter(self.webhook_url)
        sess = await global_session_mgr.get_or_create(chat_id, self.work_dir)
        await sess.append(Message(role=Role.USER, content=prompt))

        eng = self.factory(sess)
        try:
            await eng.run(sess, reporter)
        except Exception as e:
            reporter.send_msg(f"❌ Agent 运行崩溃: {e}")
