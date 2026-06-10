"""基准测试 CLI — python -m py_claw.bench_cli。"""

from __future__ import annotations

import asyncio
import os

from py_claw.eval.benchmark import BenchmarkRunner, TestCase


async def async_main() -> None:
    if not os.getenv("ZHIPU_API_KEY"):
        print("请先导出 ZHIPU_API_KEY 环境变量进行跑分测试")
        return

    test_cases = [
        TestCase(
            id="test_001_edit",
            name="测试编辑工具的准确性",
            setup_script="""echo '{"name": "py-claw", "version": "v1.0.0"}' > config.json""",
            task_prompt="当前目录下有一个 config.json。请你使用 edit_file 工具，将其中的 version 从 v1.0.0 改为 v2.0.0。不要做其他多余操作。",
            validate_script="grep '\"version\": \"v2.0.0\"' config.json",
        ),
        TestCase(
            id="test_002_code_gen",
            name="测试代码阅读与创建新文件的综合能力",
            setup_script="""cat > math.py << 'EOF'
def multiply(a: int, b: int) -> int:
    return a * b
EOF""",
            task_prompt="当前目录下有一个 math.py。请你仔细阅读它，然后在同级目录下，帮我写一份规范的单元测试文件 test_math.py。请务必包含正常的测试用例。",
            validate_script="python -m pytest test_math.py -v",
        ),
    ]

    runner = BenchmarkRunner(model="glm-4.5-air")
    await runner.run_suite(test_cases)


def main() -> None:
    asyncio.run(async_main())


if __name__ == "__main__":
    main()
