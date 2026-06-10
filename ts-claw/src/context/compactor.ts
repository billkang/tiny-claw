/** 上下文压缩 — 当消息历史超过阈值时智能截断。 */

import pino from 'pino';
import type { Message } from '../schema/message.js';

const logger = pino({ name: 'compactor' });

export class Compactor {
  constructor(
    public maxChars = 200_000,
    public retainLastMsgs = 6,
  ) {}

  compact(msgs: Message[]): Message[] {
    const currentLength = this._estimateLength(msgs);
    if (currentLength < this.maxChars) return msgs;

    logger.warn(
      { currentChars: currentLength, maxChars: this.maxChars },
      '上下文超限，触发压缩',
    );

    const protectStart = msgs.length - this.retainLastMsgs;
    const compacted: Message[] = [];

    for (let i = 0; i < msgs.length; i++) {
      const msg = msgs[i];
      if (msg.role === 'system') {
        compacted.push(msg);
        continue;
      }

      const isWorking = i >= protectStart;
      const newMsg: Message = { role: msg.role, content: msg.content, toolCalls: msg.toolCalls };

      if (msg.role === 'user' && msg.toolCallId) {
        if (!isWorking) {
          newMsg.content = `[早期工具输出已折叠，原始长度: ${msg.content.length} 字节]`;
        } else {
          const MAX_KEEP = 1000;
          if (msg.content.length > MAX_KEEP) {
            const head = msg.content.slice(0, 500);
            const tail = msg.content.slice(-500);
            newMsg.content = `${head}\n\n...[中间 ${msg.content.length - MAX_KEEP} 字节已截断]...\n\n${tail}`;
          }
        }
        newMsg.toolCallId = msg.toolCallId;
      } else if (msg.role === 'assistant' && msg.content) {
        if (!isWorking && msg.content.length > 200) {
          newMsg.content = '[早期推理思考已折叠]...';
        }
      }

      compacted.push(newMsg);
    }

    const newLength = this._estimateLength(compacted);
    logger.info({ from: currentLength, to: newLength }, '压缩完成');
    return compacted;
  }

  private _estimateLength(msgs: Message[]): number {
    let len = 0;
    for (const msg of msgs) {
      len += msg.content.length;
      if (msg.toolCalls) {
        for (const tc of msg.toolCalls) {
          len += tc.name.length + tc.arguments.length;
        }
      }
    }
    return len;
  }
}
