"""基准评测框架 — 自动化 Agent 能力测试。"""

from __future__ import annotations

import asyncio
import subprocess
import tempfile
import time
from dataclasses import dataclass, field

from loguru import logger

from py_claw.context.composer import PromptComposer
from py_claw.context.session import Session
from py_claw.engine.loop import AgentEngine
from py_claw.observability.tracker import CostTracker
from py_claw.provider.openai_compat import OpenAICompatProvider
from py_claw.schema.message import Message, Role
from py_claw.tools.base import Registry
from py_claw.tools.bash import BashTool
from py_claw.tools.edit_file import EditFileTool
from py_claw.tools.read_file import ReadFileTool
from py_claw.tools.write_file import WriteFileTool


@dataclass
class TestCase:
    """一个独立的 Agent 评测用例。"""
    id: str
    name: str
    task_prompt: str
    setup_script: str = ""
    validate_script: str = ""
    max_turns: int = 20


@dataclass
class TestResult:
    """单次评测结果。"""
    test_case_id: str
    passed: bool = False
    total_cost_cny: float = 0.0
    duration_ms: float = 0.0
    error_msg: str = ""


class BenchmarkRunner:
    """评测运行器。"""

    def __init__(self, model: str = "glm-4.5-air") -> None:
        self.model = model

    async def run_suite(self, test_cases: list[TestCase]) -> None:
        logger.info("=" * 50)
        logger.info("🚀 启动自动化 Harness Benchmark 评估... | 模型: {}", self.model)
        logger.info("=" * 50)

        results: list[TestResult] = []
        passed_count = 0
        total_cost = 0.0

        for tc in test_cases:
            logger.info(">>> ⏳ 正在执行用例 [{}]: {}", tc.id, tc.name)
            result = await self._run_single(tc)
            results.append(result)
            if result.passed:
                passed_count += 1
                logger.info(">>> ✅ 用例 [{}] 测试通过! | 耗时: {:.0f}ms | 花费: ¥{:.6f}",
                            tc.id, result.duration_ms, result.total_cost_cny)
            else:
                logger.info(">>> ❌ 用例 [{}] 测试失败! | 错误: {}", tc.id, result.error_msg)
            total_cost += result.total_cost_cny

        logger.info("\n================ 🏆 跑分终极报告 ================")
        logger.info("总用例数: {} | 成功数: {} | 成功率: {:.2f}%",
                    len(test_cases), passed_count,
                    passed_count / len(test_cases) * 100 if test_cases else 0)
        logger.info("总消耗成本: ¥{:.6f}", total_cost)
        logger.info("=" * 50)

    async def _run_single(self, tc: TestCase) -> TestResult:
        start = time.time()

        # 创建独立沙箱
        work_dir = tempfile.mkdtemp(prefix=f"bench_{tc.id}_")

        # 执行 Setup
        if tc.setup_script:
            proc = await asyncio.create_subprocess_shell(
                tc.setup_script,
                cwd=work_dir,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
            _, _ = await proc.communicate()
            if proc.returncode != 0:
                return TestResult(test_case_id=tc.id, error_msg="靶机 Setup 失败")

        # 组装引擎
        provider = OpenAICompatProvider(model=self.model)
        session = Session(id=tc.id, work_dir=work_dir)
        tracked = CostTracker(provider, self.model, session)

        registry = Registry()
        registry.register(ReadFileTool(work_dir))
        registry.register(WriteFileTool(work_dir))
        registry.register(BashTool(work_dir))
        registry.register(EditFileTool(work_dir))

        eng = AgentEngine(tracked, registry, enable_thinking=False, plan_mode=False)

        await session.append(Message(role=Role.USER, content=tc.task_prompt))

        try:
            await eng.run(session, reporter=None)
        except Exception as e:
            return TestResult(test_case_id=tc.id, passed=False,
                              error_msg=f"Agent 崩溃: {e}",
                              total_cost_cny=session.total_cost_cny)

        # 执行验证脚本
        if tc.validate_script:
            proc = await asyncio.create_subprocess_shell(
                tc.validate_script,
                cwd=work_dir,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
            stdout, stderr = await proc.communicate()
            if proc.returncode != 0:
                err_msg = f"验证脚本执行失败: {stdout.decode()}{stderr.decode()}"
                return TestResult(test_case_id=tc.id, passed=False,
                                  total_cost_cny=session.total_cost_cny,
                                  duration_ms=(time.time() - start) * 1000,
                                  error_msg=err_msg)

        return TestResult(
            test_case_id=tc.id, passed=True,
            total_cost_cny=session.total_cost_cny,
            duration_ms=(time.time() - start) * 1000,
        )
