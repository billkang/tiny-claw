/** 会话管理 — 维护多轮对话的消息历史与累计消耗。 */

import type { Message } from '../schema/message.js';

export class Session {
  id: string;
  workDir: string;
  createdAt: number;
  updatedAt: number;

  totalPromptTokens = 0;
  totalCompletionTokens = 0;
  totalCostCny = 0;

  private _history: Message[] = [];

  constructor(id: string, workDir = '.') {
    this.id = id;
    this.workDir = workDir;
    this.createdAt = Date.now();
    this.updatedAt = Date.now();
  }

  append(...msgs: Message[]): void {
    this._history.push(...msgs);
    this.updatedAt = Date.now();
  }

  /** 获取最近的 N 条消息作为工作记忆，自动丢弃截断边缘的孤儿 ToolResult。 */
  getWorkingMemory(limit = 0): Message[] {
    const total = this._history.length;
    if (total <= limit || limit <= 0) return [...this._history];

    let result = this._history.slice(total - limit);

    // 丢弃截断边缘的孤儿 ToolResult
    while (result.length > 0 && result[0].role === 'user' && result[0].toolCallId) {
      result = result.slice(1);
    }

    return result;
  }

  recordUsage(prompt: number, completion: number, cost: number): void {
    this.totalPromptTokens += prompt;
    this.totalCompletionTokens += completion;
    this.totalCostCny += cost;
  }

  get history(): readonly Message[] {
    return this._history;
  }
}

/** 全局会话管理器 */
export class SessionManager {
  private sessions = new Map<string, Session>();

  getOrCreate(id: string, workDir = '.'): Session {
    const existing = this.sessions.get(id);
    if (existing) return existing;
    const sess = new Session(id, workDir);
    this.sessions.set(id, sess);
    return sess;
  }
}

export const globalSessionMgr = new SessionManager();
