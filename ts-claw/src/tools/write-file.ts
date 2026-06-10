/** 创建/覆写文件工具。 */

import { mkdir, writeFile } from 'node:fs/promises';
import { dirname, join } from 'node:path';
import type { ToolDefinition } from '../schema/message.js';
import type { BaseTool } from './base.js';

export class WriteFileTool implements BaseTool {
  constructor(private workDir: string) {}

  name(): string {
    return 'write_file';
  }

  definition(): ToolDefinition {
    return {
      name: this.name(),
      description: '创建或覆盖写入一个文件。如果目录不存在会自动创建。请提供相对于工作区的相对路径。',
      inputSchema: {
        type: 'object',
        properties: {
          path: { type: 'string', description: '要写入的文件路径, 如 src/main.ts' },
          content: { type: 'string', description: '要写入的完整文件内容' },
        },
        required: ['path', 'content'],
      },
    };
  }

  async execute(arguments: string): Promise<string> {
    const args = JSON.parse(arguments) as { path: string; content: string };
    const filepath = join(this.workDir, args.path);

    await mkdir(dirname(filepath), { recursive: true });
    await writeFile(filepath, args.content, 'utf-8');

    return `成功将内容写入到文件: ${args.path}`;
  }
}
