/** 编辑文件工具 — 带模糊匹配的字符串替换。 */

import { readFile, writeFile } from 'node:fs/promises';
import { join } from 'node:path';
import type { ToolDefinition } from '../schema/message.js';
import type { BaseTool } from './base.js';

export class EditFileTool implements BaseTool {
  constructor(private workDir: string) {}

  name(): string {
    return 'edit_file';
  }

  definition(): ToolDefinition {
    return {
      name: this.name(),
      description: '对现有文件进行局部的字符串替换。这比重写整个文件更安全、更快速。请提供足够的 old_text 上下文以确保匹配的唯一性。',
      inputSchema: {
        type: 'object',
        properties: {
          path: { type: 'string', description: '要修改的文件路径' },
          old_text: { type: 'string', description: '文件中原有的文本，必须包含足够的上下文以确保唯一性' },
          new_text: { type: 'string', description: '要替换成的新文本' },
        },
        required: ['path', 'old_text', 'new_text'],
      },
    };
  }

  async execute(arguments: string): Promise<string> {
    const args = JSON.parse(arguments) as { path: string; old_text: string; new_text: string };
    const filepath = join(this.workDir, args.path);

    const content = await readFile(filepath, 'utf-8');
    const oldText = args.old_text;
    const newText = args.new_text;

    let result: string;

    // L1: 精确匹配
    const count = countOccurrences(content, oldText);
    if (count === 1) {
      result = content.replace(oldText, newText);
    } else if (count > 1) {
      throw new Error(`old_text 匹配到了 ${count} 处，请提供更多的上下文代码以确保唯一性`);
    } else {
      // L2: 换行符归一化
      const normalized = content.replace(/\r\n/g, '\n');
      const normalizedOld = oldText.replace(/\r\n/g, '\n');
      const nCount = countOccurrences(normalized, normalizedOld);

      if (nCount === 1) {
        result = normalized.replace(normalizedOld, newText);
      } else if (nCount > 1) {
        throw new Error(`归一化后匹配到了 ${nCount} 处，请提供更多上下文`);
      } else {
        // L3: 逐行去缩进匹配
        result = this._lineByLineReplace(normalized, normalizedOld, newText);
      }
    }

    await writeFile(filepath, result, 'utf-8');
    return `✅ 成功修改文件: ${args.path}`;
  }

  private _lineByLineReplace(content: string, oldText: string, newText: string): string {
    const contentLines = content.split('\n');
    const oldLines = oldText.trim().split('\n').map(l => l.trim());

    if (oldLines.length === 0 || contentLines.length < oldLines.length) {
      throw new Error('找不到该代码片段');
    }

    let matchCount = 0;
    let matchStart = -1;
    let matchEnd = -1;

    for (let i = 0; i <= contentLines.length - oldLines.length; i++) {
      let isMatch = true;
      for (let j = 0; j < oldLines.length; j++) {
        if (contentLines[i + j].trim() !== oldLines[j]) {
          isMatch = false;
          break;
        }
      }
      if (isMatch) {
        matchCount++;
        matchStart = i;
        matchEnd = i + oldLines.length;
      }
    }

    if (matchCount === 0) throw new Error('在文件中未找到 old_text，请检查内容和缩进');
    if (matchCount > 1) throw new Error(`模糊匹配到了 ${matchCount} 处代码，请提供更多上下文以定位`);

    const before = contentLines.slice(0, matchStart);
    const after = contentLines.slice(matchEnd);
    return [...before, newText, ...after].join('\n');
  }
}

function countOccurrences(str: string, substr: string): number {
  let count = 0;
  let idx = 0;
  while ((idx = str.indexOf(substr, idx)) !== -1) {
    count++;
    idx += substr.length;
  }
  return count;
}
