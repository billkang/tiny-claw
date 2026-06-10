/** 死循环检测 — 监控连续相同工具失败并注入干预。 */

import crypto from 'node:crypto';
import pino from 'pino';
import type { Message, ToolCall, ToolResult } from '../schema/message.js';
import { Role } from '../schema/message.js';

const logger = pino({ name: 'reminder' });

export class ReminderInjector {
  private consecutiveFailures = new Map<string, number>();

  checkAndInject(lastToolCall: ToolCall, lastResult: ToolResult): Message | null {
    const fingerprint = this._fingerprint(lastToolCall);

    if (!lastResult.isError) {
      this.consecutiveFailures.clear();
      return null;
    }

    const failCount = (this.consecutiveFailures.get(fingerprint) ?? 0) + 1;
    this.consecutiveFailures.set(fingerprint, failCount);

    logger.info({ tool: lastToolCall.name, failCount }, '监控到工具执行失败');

    if (failCount >= 3) {
      logger.warn('触发死循环干预！注入强力修正指令。');

      const nudge =
        `[SYSTEM REMINDER 警告]\n` +
        `你似乎陷入了死循环。你刚刚连续 ${failCount} 次使用相同的参数调用了 ` +
        `'${lastToolCall.name}' 工具，并且都失败了。\n` +
        `请立即停止这种无效的重试！你的注意力被当前的报错过度吸引了。\n` +
        `你需要：\n` +
        `1. 停止猜测参数。跳出当前的局部思维。\n` +
        `2. 彻底改变你的策略。\n` +
        `3. 如果你确实无法通过系统工具解决当前问题，请直接结束任务并向用户说明你需要什么人工帮助，` +
        `而不是继续盲目消耗 API 资源尝试。`;

      return { role: Role.USER, content: nudge };
    }

    return null;
  }

  private _fingerprint(call: ToolCall): string {
    return crypto.createHash('md5').update(`${call.name}:${call.arguments}`).digest('hex');
  }
}
