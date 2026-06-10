import { describe, it, expect } from 'vitest';
import { Session } from '../src/context/session.js';

describe('Session', () => {
  it('should append and retrieve messages', () => {
    const sess = new Session('test');
    sess.append({ role: 'user', content: 'hello' });
    sess.append({ role: 'assistant', content: 'hi' });

    const mem = sess.getWorkingMemory();
    expect(mem).toHaveLength(2);
    expect(mem[0].content).toBe('hello');
    expect(mem[1].content).toBe('hi');
  });

  it('should respect working memory limit', () => {
    const sess = new Session('test');
    for (let i = 0; i < 10; i++) {
      sess.append({ role: 'user', content: `msg${i}` });
    }

    const mem = sess.getWorkingMemory(3);
    expect(mem).toHaveLength(3);
    expect(mem[0].content).toBe('msg7');
  });

  it('should remove orphan tool results at truncation edge', () => {
    const sess = new Session('test');
    sess.append({ role: 'user', content: 'first' });
    sess.append({ role: 'assistant', content: 'ok' });
    sess.append({ role: 'user', content: 'tool result', toolCallId: 'tc1' });
    sess.append({ role: 'user', content: 'normal' });

    const mem = sess.getWorkingMemory(2);
    expect(mem).toHaveLength(1);
    expect(mem[0].content).toBe('normal');
  });

  it('should accumulate usage', () => {
    const sess = new Session('test');
    sess.recordUsage(100, 50, 0.001);
    expect(sess.totalPromptTokens).toBe(100);
    expect(sess.totalCompletionTokens).toBe(50);
    expect(sess.totalCostCny).toBe(0.001);

    sess.recordUsage(200, 100, 0.002);
    expect(sess.totalPromptTokens).toBe(300);
    expect(sess.totalCompletionTokens).toBe(150);
    expect(sess.totalCostCny).toBe(0.003);
  });
});
