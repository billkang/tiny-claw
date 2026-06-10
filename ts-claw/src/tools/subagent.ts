/** 子智能体工具 — 主 Agent 可派出子 Agent 进行深度探索。 */

import pino from 'pino';
import type { ToolDefinition } from '../schema/message.js';
import type { BaseTool, Registry } from './base.js';
import type { AgentEngine } from '../engine/loop.js';
import type { Reporter } from '../engine/reporter.js';

const logger = pino({ name: 'subagent' });

export class SubagentTool implements BaseTool {
  constructor(
    private engine: AgentEngine,
    private readOnlyRegistry: Registry,
    private reporter?: Reporter,
  ) {}

  name(): string {
    return 'spawn_subagent';
  }

  definition(): ToolDefinition {
    return {
      name: this.name(),
      description: '派出一个专门用于深度探索（Exploration）的子智能体。当你需要阅读大量代码、跨文件查找逻辑时请调用此工具。它在探索完毕后，会给你返回一份极度精炼的摘要报告。',
      inputSchema: {
        type: 'object',
        properties: {
          task_prompt: { type: 'string', description: '给子智能体下达的明确探索指令。' },
        },
        required: ['task_prompt'],
      },
    };
  }

  async execute(arguments: string): Promise<string> {
    const args = JSON.parse(arguments) as { task_prompt: string };
    logger.info('🚀 主 Agent 发起委派！正在拉起探路者: [{}]...', args.task_prompt);

    try {
      const summary = await this.engine.runSub(args.task_prompt, this.readOnlyRegistry, this.reporter);
      logger.info('✅ 子智能体任务结束。报告返回给主干...');
      return `【子智能体探索报告】:\n${summary}`;
    } catch (err) {
      return `子智能体执行失败: ${err}`;
    }
  }
}
