/** Bash 命令执行工具 — 使用 child_process exec。 */

import { execFile } from 'node:child_process';
import { promisify } from 'node:util';
import type { ToolDefinition } from '../schema/message.js';
import type { BaseTool } from './base.js';

const execAsync = promisify(execFile);

export class BashTool implements BaseTool {
  private static TIMEOUT = 30_000;
  private static MAX_LEN = 8000;

  constructor(private workDir: string) {}

  name(): string {
    return 'bash';
  }

  definition(): ToolDefinition {
    return {
      name: this.name(),
      description: '在当前工作区执行任意的 bash 命令。支持链式命令(如 &&)。返回标准输出和标准错误。',
      inputSchema: {
        type: 'object',
        properties: {
          command: { type: 'string', description: '要执行的 bash 命令' },
        },
        required: ['command'],
      },
    };
  }

  async execute(arguments: string): Promise<string> {
    const args = JSON.parse(arguments) as { command: string };

    try {
      const { stdout, stderr } = await execAsync('bash', ['-c', args.command], {
        cwd: this.workDir,
        timeout: BashTool.TIMEOUT,
        maxBuffer: BashTool.MAX_LEN * 2,
      });

      let output = '';
      if (stdout) output += stdout;
      if (stderr) output += stderr;

      if (!output.trim()) return '命令执行成功，无终端输出。';

      if (output.length > BashTool.MAX_LEN) {
        return `${output.slice(0, BashTool.MAX_LEN)}\n\n...[终端输出过长，已截断至前 ${BashTool.MAX_LEN} 字节]...`;
      }

      return output.trim();
    } catch (err: any) {
      if (err.killed || err.code === 'ETIMEOUT') {
        return `[警告: 命令执行超时(${BashTool.TIMEOUT / 1000}s)，已被系统强制终止。]\n${err.stdout ?? ''}`;
      }
      return `执行报错: ${err.message}\n${err.stdout ?? ''}${err.stderr ?? ''}`;
    }
  }
}
