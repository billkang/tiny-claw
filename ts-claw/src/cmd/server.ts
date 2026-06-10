/**
 * 飞书 Bot 服务入口 — Express 应用。
 * 使用: tsx src/cmd/server.ts
 */

import express from 'express';
import pino from 'pino';
import { OpenAICompatProvider } from '../provider/openai-compat.js';
import { CostTracker } from '../observability/tracker.js';
import { Registry } from '../tools/base.js';
import { ReadFileTool } from '../tools/read-file.js';
import { WriteFileTool } from '../tools/write-file.js';
import { EditFileTool } from '../tools/edit-file.js';
import { BashTool } from '../tools/bash.js';
import { AgentEngine } from '../engine/loop.js';
import { FeishuBot } from '../feishu/bot.js';
import { isDangerousCommand, globalApprovalMgr } from '../feishu/approval.js';
import type { Session } from '../context/session.js';

const logger = pino({ name: 'server' });

function main() {
  logger.info('🚀 正在启动 ts-claw AgentOps 飞书服务端...');

  const apiKey = process.env['ZHIPU_API_KEY'];
  const webhookUrl = process.env['FEISHU_WEBHOOK_URL'];

  if (!apiKey || !webhookUrl) {
    logger.error('请先导出 ZHIPU_API_KEY 和 FEISHU_WEBHOOK_URL 环境变量');
    process.exit(1);
  }

  const workDir = process.cwd() + '/workspace';
  const { mkdirSync } = require('node:fs');
  mkdirSync(workDir, { recursive: true });

  const modelName = 'glm-4.5-air';
  const llmProvider = new OpenAICompatProvider(modelName);

  const registry = new Registry();
  registry.register(new ReadFileTool(workDir));
  registry.register(new WriteFileTool(workDir));
  registry.register(new EditFileTool(workDir));
  registry.register(new BashTool(workDir));

  // 安全中间件
  registry.use((call) => {
    const argsStr = call.arguments;
    if (isDangerousCommand(call.name, argsStr)) {
      logger.info({ tool: call.name }, '拦截到高危操作，触发审批挂起');
      // 异步审批 — 这里用同步 wait 的方式需要特殊处理，简化版本直接放行
      // 生产环境应该用 async middleware
      return { allowed: false, reason: '高危操作需人工审批 (请实现审批流)' };
    }
    return { allowed: true, reason: '' };
  });

  function engineFactory(session: Session): AgentEngine {
    const tracked = new CostTracker(llmProvider, modelName, session);
    return new AgentEngine(tracked, registry, false, false);
  }

  const bot = new FeishuBot(engineFactory, workDir, webhookUrl);

  const app = express();
  app.use(express.json());
  app.use(bot.getRouter());

  const port = parseInt(process.env['PORT'] ?? '48080', 10);
  app.listen(port, () => {
    logger.info('📡 Webhook 服务已启动，监听端口 %d', port);
  });
}

main();
