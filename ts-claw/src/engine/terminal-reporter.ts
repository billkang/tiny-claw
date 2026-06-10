/** 终端输出 Reporter — 使用 chalk 实现彩色控制台输出。 */

import chalk from 'chalk';
import type { Reporter } from './reporter.js';

export class TerminalReporter implements Reporter {
  onThinking(): void {
    console.log(`\n${chalk.yellow('🤔 思考中')} 模型正在推理...`);
  }

  onToolCall(toolName: string, args: string): void {
    let displayArgs = args.replace(/\n/g, '\\n').replace(/\r/g, '\\r');
    if (displayArgs.length > 150) displayArgs = displayArgs.slice(0, 150) + '... (已截断)';

    console.log(
      `${chalk.blue('🛠️ 调用工具')} ${chalk.cyan(toolName)}\n` +
      `  ${chalk.dim(displayArgs)}`,
    );
  }

  onToolResult(toolName: string, result: string, isError: boolean): void {
    if (isError) {
      const display = result.length > 200 ? result.slice(0, 200) + '...' : result;
      console.log(
        `${chalk.red('❌ 执行失败')} ${chalk.bold(toolName)}\n` +
        `  ${chalk.red(display)}`,
      );
    } else {
      console.log(`${chalk.green('✅ 执行成功')} ${chalk.bold(toolName)}`);
    }
  }

  onMessage(content: string): void {
    if (!content) return;
    console.log(`\n${chalk.cyan('🤖 Agent 回复:')}\n${content}\n`);
  }
}
