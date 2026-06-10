import { describe, it, expect } from 'vitest';
import { Compactor } from '../src/context/compactor.js';
import { Message } from '../src/schema/message.js';

function msg(role: string, content: string, toolCallId?: string): Message {
  return { role: role as any, content, toolCallId };
}

describe('Compactor', () => {
  it('should not compact when under threshold', () => {
    const c = new Compactor(1000, 2);
    const msgs = [msg('system', 'sys'), msg('user', 'hello')];
    const result = c.compact(msgs);
    expect(result).toHaveLength(2);
    expect(result[0].content).toBe('sys');
    expect(result[1].content).toBe('hello');
  });

  it('should truncate early tool output', () => {
    const c = new Compactor(50, 1);
    const long = 'x'.repeat(500);
    const msgs = [
      msg('system', 'sys'),
      msg('user', long, 'tc1'),
      msg('user', 'final'),
    ];
    const result = c.compact(msgs);
    expect(result).toHaveLength(3);
    expect(result[1].content).toContain('早期工具输出已折叠');
    expect(result[2].content).toBe('final');
  });

  it('should preserve system messages', () => {
    const c = new Compactor(10, 1);
    const msgs = [msg('system', 'long system prompt'), msg('user', 'hello')];
    const result = c.compact(msgs);
    expect(result[0].content).toBe('long system prompt');
  });
});
