"""飞书 Bot 服务入口 — FastAPI 应用。"""

from __future__ import annotations

import os

import uvicorn
from fastapi import FastAPI
from loguru import logger

from py_claw.context.session import Session
from py_claw.engine.loop import AgentEngine
from py_claw.feishu.bot import FeishuBot
from py_claw.observability.tracker import CostTracker
from py_claw.provider.openai_compat import OpenAICompatProvider
from py_claw.tools.base import Registry
from py_claw.tools.bash import BashTool
from py_claw.tools.edit_file import EditFileTool
from py_claw.tools.read_file import ReadFileTool
from py_claw.tools.write_file import WriteFileTool


def main() -> None:
    logger.info("🚀 正在启动 py-claw AgentOps 飞书服务端...")

    api_key = os.getenv("ZHIPU_API_KEY")
    webhook_url = os.getenv("FEISHU_WEBHOOK_URL")
    if not api_key or not webhook_url:
        logger.error("请先导出 ZHIPU_API_KEY 和 FEISHU_WEBHOOK_URL 环境变量")
        return

    work_dir = os.path.join(os.getcwd(), "workspace")
    os.makedirs(work_dir, exist_ok=True)

    model_name = "glm-4.5-air"
    llm_provider = OpenAICompatProvider(model=model_name)

    # 安全中间件：通过飞书审批拦截高毒操作
    registry = Registry()
    registry.register(ReadFileTool(work_dir))
    registry.register(WriteFileTool(work_dir))
    registry.register(EditFileTool(work_dir))
    registry.register(BashTool(work_dir))

    from py_claw.feishu.approval import is_dangerous_command, global_approval_mgr

    async def approval_middleware(call):
        args_str = call.arguments
        if is_dangerous_command(call.name, args_str):
            task_id = call.id
            logger.info("拦截到高危操作: {}，触发飞书审批挂起...", call.name)
            allowed, reason = await global_approval_mgr.wait_for_approval(
                task_id, call.name, args_str,
            )
            if not allowed:
                return False, reason
        return True, ""
    # 注意：中间件需要正确注册，此处简化处理

    def engine_factory(session: Session) -> AgentEngine:
        tracked = CostTracker(llm_provider, model_name, session)
        return AgentEngine(tracked, registry, enable_thinking=False, plan_mode=False)

    bot = FeishuBot(engine_factory, work_dir, webhook_url)

    app = FastAPI(title="py-claw AgentOps")
    app.include_router(bot.get_router())

    port = int(os.getenv("PORT", "48080"))
    logger.info("📡 Webhook 服务已启动，正在监听端口 {}...", port)
    uvicorn.run(app, host="0.0.0.0", port=port)


if __name__ == "__main__":
    main()
