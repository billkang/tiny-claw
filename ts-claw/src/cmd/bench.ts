/**
 * 基准测试 CLI。
 * 使用: tsx src/cmd/bench.ts
 */

import { BenchmarkRunner, TestCase } from '../eval/benchmark.js';

async function main() {
  if (!process.env['ZHIPU_API_KEY']) {
    console.error('请先导出 ZHIPU_API_KEY 环境变量进行跑分测试');
    process.exit(1);
  }

  const testCases: TestCase[] = [
    {
      id: 'test_001_edit',
      name: '测试编辑工具的准确性',
      setupScript: `echo '{"name": "ts-claw", "version": "v1.0.0"}' > config.json`,
      taskPrompt: '当前目录下有一个 config.json。请你使用 edit_file 工具，将其中的 version 从 v1.0.0 改为 v2.0.0。不要做其他多余操作。',
      validateScript: `grep '"version": "v2.0.0"' config.json`,
    },
    {
      id: 'test_002_code_gen',
      name: '测试代码阅读与创建新文件的综合能力',
      setupScript: `cat > math.ts << 'EOF'
export function multiply(a: number, b: number): number {
  return a * b;
}
EOF`,
      taskPrompt: '当前目录下有一个 math.ts。请你仔细阅读它，然后在同级目录下，帮我写一份规范的单元测试文件 math.test.ts。请务必包含正常的测试用例。',
      validateScript: `npx tsx -e "import('./math.test.ts').then(() => console.log('OK'))"`,
    },
  ];

  const runner = new BenchmarkRunner('glm-4.5-air');
  await runner.runSuite(testCases);
}

main().catch(err => {
  console.error(err);
  process.exit(1);
});
