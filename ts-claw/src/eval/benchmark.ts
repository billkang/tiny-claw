/** 基准评测框架 — 自动化 Agent 能力测试。 */

import { execFile } from 'node:child_process';
import { mkdtempSync, writeFileSync } from 'node:fs';
import { promisify } from 'node:util';
import { join } from 'node:path';
import { tmpdir } from 'node:os';
import pino from 'pino';
import { Session } from '../context/session.js';
import { AgentEngine } from '../engine/loop.js';
import { CostTracker } from '../observability/tracker.js';
import { OpenAICompatProvider } from '../provider/openai-compat.js';
import { Role } from '../schema/message.js';
import { Registry } from '../tools/base.js';
import { BashTool } from '../tools/bash.js';
import { EditFileTool } from '../tools/edit-file.js';
import { ReadFileTool } from '../tools/read-file.js';
import { WriteFileTool } from '../tools/write-file.js';

const execAsync = promisify(execFile);
const logger = pino({ name: 'benchmark' });

export interface TestCase {
  id: string;
  name: string;
  taskPrompt: string;
  setupScript?: string;
  validateScript?: string;
}

export interface TestResult {
  testCaseId: string;
  passed: boolean;
  totalCostCny: number;
  durationMs: number;
  errorMsg?: string;
}

export class BenchmarkRunner {
  constructor(private model = 'glm-4.5-air') {}

  async runSuite(testCases: TestCase[]): Promise<void> {
    logger.info('🚀 启动自动化 Harness Benchmark 评估... 模型: %s', this.model);

    let passedCount = 0;
    let totalCost = 0;

    for (const tc of testCases) {
      logger.info('>>> ⏳ 正在执行用例 [%s]: %s', tc.id, tc.name);
      const result = await this._runSingle(tc);

      if (result.passed) {
        passedCount++;
        logger.info('>>> ✅ 用例 [%s] 测试通过! | 耗时: %.0fms | 花费: ¥%.6f', tc.id, result.durationMs, result.totalCostCny);
      } else {
        logger.info('>>> ❌ 用例 [%s] 测试失败! | 错误: %s', tc.id, result.errorMsg);
      }
      totalCost += result.totalCostCny;
    }

    logger.info('================ 🏆 跑分终极报告 ================');
    logger.info('总用例数: %d | 成功数: %d | 成功率: %.2f%%', testCases.length, passedCount, (passedCount / testCases.length) * 100);
    logger.info('总消耗成本: ¥%.6f', totalCost);
  }

  private async _runSingle(tc: TestCase): Promise<TestResult> {
    const start = Date.now();
    const workDir = mkdtempSync(join(tmpdir(), `bench_${tc.id}_`));

    // 执行 Setup
    if (tc.setupScript) {
      try {
        await execAsync('bash', ['-c', tc.setupScript], { cwd: workDir });
      } catch {
        return { testCaseId: tc.id, passed: false, totalCostCny: 0, durationMs: Date.now() - start, errorMsg: '靶机 Setup 失败' };
      }
    }

    // 组装引擎
    const provider = new OpenAICompatProvider(this.model);
    const session = new Session(tc.id, workDir);
    const tracked = new CostTracker(provider, this.model, session);

    const registry = new Registry();
    registry.register(new ReadFileTool(workDir));
    registry.register(new WriteFileTool(workDir));
    registry.register(new BashTool(workDir));
    registry.register(new EditFileTool(workDir));

    const eng = new AgentEngine(tracked, registry, false, false);
    session.append({ role: Role.USER, content: tc.taskPrompt });

    try {
      await eng.run(session, undefined);
    } catch (err) {
      return { testCaseId: tc.id, passed: false, totalCostCny: session.totalCostCny, durationMs: Date.now() - start, errorMsg: `Agent 崩溃: ${err}` };
    }

    // 执行验证脚本
    if (tc.validateScript) {
      try {
        await execAsync('bash', ['-c', tc.validateScript], { cwd: workDir });
      } catch (err: any) {
        return { testCaseId: tc.id, passed: false, totalCostCny: session.totalCostCny, durationMs: Date.now() - start, errorMsg: `验证脚本执行失败: ${err.message}` };
      }
    }

    return { testCaseId: tc.id, passed: true, totalCostCny: session.totalCostCny, durationMs: Date.now() - start };
  }
}
