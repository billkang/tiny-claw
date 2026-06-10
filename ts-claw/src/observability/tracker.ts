/** 成本追踪器 — 装饰 LLM Provider，自动记录 Token 消耗和费用。 */

import pino from 'pino';
import type { LLMProvider } from '../provider/interface.js';
import type { Message, ToolDefinition } from '../schema/message.js';
import type { Session } from '../context/session.js';

const logger = pino({ name: 'tracker' });

// 定价模型 (元/百万 tokens)
const PRICING: Record<string, { input: number; output: number }> = {
  'glm-4.5-air': { input: 0.15, output: 0.15 },
  'glm-4-plus': { input: 0.50, output: 0.50 },
  'deepseek-chat': { input: 0.14, output: 0.28 },
  'gpt-4o-mini': { input: 0.15, output: 0.60 },
};

export class CostTracker implements LLMProvider {
  constructor(
    private next: LLMProvider,
    private model: string,
    private session: Session,
  ) {}

  async generate(messages: Message[], availableTools?: ToolDefinition[]): Promise<Message> {
    const start = Date.now();
    const resp = await this.next.generate(messages, availableTools);
    const latency = Date.now() - start;

    if (resp.usage) {
      const pt = resp.usage.promptTokens;
      const ct = resp.usage.completionTokens;

      let cost = 0;
      const price = PRICING[this.model];
      if (price) {
        cost = (pt * price.input + ct * price.output) / 1_000_000;
      }

      logger.info({ latency: `${latency}ms`, promptTokens: pt, completionTokens: ct, cost: `¥${cost.toFixed(6)}` }, 'API 调用完成');
      this.session.recordUsage(pt, ct, cost);
      logger.info({ sessionId: this.session.id, totalCost: `¥${this.session.totalCostCny.toFixed(6)}` }, '累计花费');
    } else {
      logger.warn({ latency: `${latency}ms` }, 'API 调用完成，但未返回 Usage 数据');
    }

    return resp;
  }
}
