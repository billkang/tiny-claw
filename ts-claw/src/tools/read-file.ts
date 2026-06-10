/** 读取文件工具。 */

import { readFile } from 'node:fs/promises';
import { join } from 'node:path';
import type { ToolDefinition } from '../schema/message.js';
import type { BaseTool } from './base.js';

export class ReadFileTool implements BaseTool {
  constructor(private workDir: string) {}

  name(): string {
    return 'read_file';
  }

  definition(): ToolDefinition {
    return {
      name: this.name(),
      description: '读取指定路径的文件内容。请提供相对工作区的路径。',
      inputSchema: {
        type: 'object',
        properties: {
          path: { type: 'string', description: '要读取的文件路径, 如 src/main.ts' },
        },
        required: ['path'],
      },
    };
  }

  async execute(arguments: string): Promise<string> {
    const args = JSON.parse(arguments) as { path: string };
    const filepath = join(this.workDir, args.path);

    const content = await readFile(filepath, 'utf-8');

    const MAX_LEN = 8000;
    if (content.length > MAX_LEN) {
      return `${content.slice(0, MAX_LEN)}\n\n...[内容过长，已被系统截断至前 ${MAX_LEN} 字节]...`;
    }

    return content;
  }
}
