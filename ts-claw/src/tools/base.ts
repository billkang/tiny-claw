/** 工具系统基础 — BaseTool 接口 + Registry（含中间件链）。 */

import pino from 'pino';
import type { ToolCall, ToolDefinition, ToolResult } from '../schema/message.js';

const logger = pino({ name: 'registry' });

export interface BaseTool {
  name(): string;
  definition(): ToolDefinition;
  execute(arguments: string): Promise<string>;
}

export type ToolMiddleware = (call: ToolCall) => { allowed: boolean; reason: string };

export class Registry {
  private tools = new Map<string, BaseTool>();
  private middlewares: ToolMiddleware[] = [];

  register(tool: BaseTool): void {
    const n = tool.name();
    if (this.tools.has(n)) logger.warn({ tool: n }, '工具已注册，将被覆盖');
    this.tools.set(n, tool);
    logger.info({ tool: n }, '成功挂载工具');
  }

  use(mw: ToolMiddleware): void {
    this.middlewares.push(mw);
  }

  getAvailableTools(): ToolDefinition[] {
    return Array.from(this.tools.values()).map(t => t.definition());
  }

  async execute(call: ToolCall): Promise<ToolResult> {
    const tool = this.tools.get(call.name);
    if (!tool) {
      return { toolCallId: call.id, output: `Error: 系统中不存在名为 '${call.name}' 的工具。`, isError: true };
    }

    // 中间件链
    for (const mw of this.middlewares) {
      const { allowed, reason } = mw(call);
      if (!allowed) {
        logger.warn({ tool: call.name, reason }, '工具被中间件拦截');
        return { toolCallId: call.id, output: `执行被系统拦截。原因: ${reason}`, isError: true };
      }
    }

    try {
      const output = await tool.execute(call.arguments);
      return { toolCallId: call.id, output, isError: false };
    } catch (err) {
      return { toolCallId: call.id, output: `Error executing ${call.name}: ${err}`, isError: true };
    }
  }
}
