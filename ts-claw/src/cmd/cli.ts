/**
 * CLI 入口 — ts-claw 命令行工具。
 * 使用: tsx src/cmd/cli.ts -prompt "..."
 * 或: npx tsx src/cmd/cli.ts -prompt "..."
 */

import { parseArgs } from 'node:util';
import { resolve } from 'node:path';
import pino from 'pino';
import { OpenAICompatProvider } from '../provider/openai-compat.js';
import { globalSessionMgr } from '../context/session.js';
import { CostTracker } from '../observability/tracker.js';
import { Registry } from '../tools/base.js';
import { ReadFileTool } from '../tools/read-file.js';
import { WriteFileTool } from '../tools/write-file.js';
import { BashTool } from '../tools/bash.js';
import { EditFileTool } from '../tools/edit-file.js';
import { AgentEngine } from '../engine/loop.js';
import { TerminalReporter } from '../engine/terminal-reporter.js';
import { Role } from '../schema/message.js';
import { exportTraceToFile, Span } from '../observability/trace.js';

const logger = pino({ name: 'cli' });

async function main() {
  const args = parseArgs({
    options: {
      prompt: { type: 'string', short: 'p' },
      dir: { type: 'string', default: '.' },
      session: { type: 'string', default: 'cli_default_session' },
      plan: { type: 'boolean', default: false },
      thinking: { type: 'boolean', default: false },
      model: { type: 'string', default: 'glm-4.5-air' },
      'api-key': { type: 'string' },
      'base-url': { type: 'string' },
    },
  });

  if (!args.values.prompt) {
    console.error('用法: tsx src/cmd/cli.ts --prompt "任务描述" [--dir /path] [--session id] [--plan] [--thinking]');
    process.exit(1);
  }

  const workDir = resolve(args.values.dir!);

  console.log('='.repeat(50));
  console.log(`🚀 启动 ts-claw CLI 引擎...`);
  console.log(`📁 锁定工作区: ${workDir}`);
  console.log('='.repeat(50));

  // 初始化 Provider
  const provider = new OpenAICompatProvider(args.values.model!, {
    apiKey: args.values['api-key'],
    baseURL: args.values['base-url'],
  });

  // 获取 Session
  const sess = globalSessionMgr.getOrCreate(args.values.session!, workDir);

  // Cost Tracker
  const tracked = new CostTracker(provider, args.values.model!, sess);

  // 注册工具
  const registry = new Registry();
  registry.register(new ReadFileTool(workDir));
  registry.register(new WriteFileTool(workDir));
  registry.register(new BashTool(workDir));
  registry.register(new EditFileTool(workDir));

  // 引擎
  const eng = new AgentEngine(tracked, registry, args.values.thinking ?? false, args.values.plan ?? false);

  const rootSpan = new Span('CLI.TaskRun', { Prompt: args.values.prompt });
  const reporter = new TerminalReporter();

  console.log(`\n🎯 收到任务: ${args.values.prompt}\n`);
  sess.append({ role: Role.USER, content: args.values.prompt });

  const startTime = Date.now();

  try {
    await eng.run(sess, reporter);
  } catch (err) {
    logger.error(err, '💥 引擎运行崩溃');
    process.exit(1);
  } finally {
    rootSpan.end();
    exportTraceToFile(rootSpan, workDir, sess.id);
  }

  const elapsed = (Date.now() - startTime) / 1000;
  console.log('\n' + '='.repeat(50));
  console.log(`✨ 任务圆满结束。总耗时: ${elapsed.toFixed(2)}s`);
  console.log(`💰 Session 累计消耗: ¥${sess.totalCostCny.toFixed(6)} | Token: Input ${sess.totalPromptTokens}, Output ${sess.totalCompletionTokens}`);
  console.log('='.repeat(50));
}

main().catch(err => {
  console.error(err);
  process.exit(1);
});
