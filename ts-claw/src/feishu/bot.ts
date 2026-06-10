/** 飞书 Bot 集成 — 通过 Express Webhook 接收飞书消息并调度 Agent。 */

import pino from 'pino';
import type { Router, Request, Response } from 'express';
import { Router as ExpressRouter } from 'express';
import type { Session } from '../context/session.js';
import { globalSessionMgr } from '../context/session.js';
import type { AgentEngine } from '../engine/loop.js';
import type { Reporter } from '../engine/reporter.js';
import { Role } from '../schema/message.js';
import { globalApprovalMgr } from './approval.js';

const logger = pino({ name: 'feishu-bot' });

export type AgentEngineFactory = (session: Session) => AgentEngine;

export class FeishuReporter implements Reporter {
  constructor(private webhookUrl: string) {}

  sendMsg(text: string): void {
    // 简化实现：用 fetch 发送飞书 webhook
    fetch(this.webhookUrl, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ msg_type: 'text', content: { text } }),
    }).catch(err => logger.error(err, '发送飞书消息失败'));
  }

  async onThinking(): void { this.sendMsg('🤔 模型正在慢思考 (Thinking)...'); }
  async onToolCall(toolName: string, args: string): void { this.sendMsg(`🛠️ **正在执行工具**: \`${toolName}\`\n参数: \`${args}\``); }
  async onToolResult(toolName: string, result: string, isError: boolean): void {
    if (isError) this.sendMsg(`⚠️ **执行报错** (${toolName}):\n${result.slice(0, 200)}`);
    else this.sendMsg(`✅ **执行成功** (${toolName})`);
  }
  async onMessage(content: string): void { this.sendMsg(content); }
}

export class FeishuBot {
  constructor(
    private factory: AgentEngineFactory,
    private workDir: string,
    private webhookUrl: string,
  ) {}

  getRouter(): Router {
    const router = ExpressRouter();

    router.post('/webhook/event', async (req: Request, res: Response) => {
      const body = req.body;
      logger.debug({ body }, '收到飞书事件');

      const event = body?.event ?? {};
      const msg = event?.message ?? {};
      let text = '';

      try {
        const contentData = typeof msg.content === 'string' ? JSON.parse(msg.content) : msg.content;
        text = contentData?.text ?? '';
      } catch {
        text = msg.content ?? '';
      }

      const chatId = msg.chat_id ?? '';

      text = text.trim();

      // 拦截审批指令
      if (text.startsWith('approve ') || text.startsWith('reject ')) {
        const [action, taskId] = text.split(/\s+/);
        const allowed = action === 'approve';
        const reason = allowed ? '人类管理员已批准操作' : '人类管理员已拒绝操作';
        globalApprovalMgr.resolveApproval(taskId, allowed, reason);
        logger.info('审批处理: {} {} ({})', action, taskId, reason);
        res.json({ code: 0 });
        return;
      }

      if (text) {
        // 异步启动 Agent
        setImmediate(() => this._handleAgentRun(chatId, text));
      }

      res.json({ code: 0 });
    });

    return router;
  }

  private async _handleAgentRun(chatId: string, prompt: string): Promise<void> {
    const reporter = new FeishuReporter(this.webhookUrl);
    const sess = globalSessionMgr.getOrCreate(chatId, this.workDir);
    sess.append({ role: Role.USER, content: prompt });

    const eng = this.factory(sess);
    try {
      await eng.run(sess, reporter);
    } catch (err) {
      reporter.sendMsg(`❌ Agent 运行崩溃: ${err}`);
    }
  }
}
