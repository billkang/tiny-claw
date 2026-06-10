/** 技能加载 — 从工作区 .claw/skills/ 目录加载 SKILL.md。 */

import { readdirSync, readFileSync, statSync } from 'node:fs';
import { join } from 'node:path';

export interface Skill {
  name: string;
  description: string;
  body: string;
}

export class SkillLoader {
  constructor(private workDir: string) {}

  loadAll(): string {
    const skillBase = join(this.workDir, '.claw', 'skills');
    try {
      if (!statSync(skillBase).isDirectory()) return '';
    } catch {
      return '';
    }

    const lines: string[] = [];
    lines.push('\n### 可用专业技能 (Agent Skills)');
    lines.push('以下是你拥有的标准化外挂技能，请在符合描述的场景下严格遵循其正文指令：\n');

    this._walkSkills(skillBase, lines);

    const result = lines.join('\n');
    return result.length < 50 ? '' : result;
  }

  private _walkSkills(dir: string, lines: string[]): void {
    let entries: import('node:fs').Dirent[];
    try {
      entries = readdirSync(dir, { withFileTypes: true });
    } catch {
      return;
    }

    for (const entry of entries) {
      const full = join(dir, entry.name);
      if (entry.isDirectory()) {
        this._walkSkills(full, lines);
      } else if (entry.name === 'SKILL.md') {
        const content = readFileSync(full, 'utf-8');
        const skill = this._parseSkillMd(content);
        lines.push(`#### 技能名称: ${skill.name}`);
        lines.push(`**触发条件**: ${skill.description}\n`);
        lines.push('**执行指南**:');
        lines.push(skill.body);
        lines.push('\n---\n');
      }
    }
  }

  private _parseSkillMd(content: string): Skill {
    const skill: Skill = { name: 'Unknown Skill', description: 'No description provided.', body: content };
    const trimmed = content.trimStart();
    if (trimmed.startsWith('---')) {
      const parts = trimmed.split('---', 3);
      if (parts.length === 3) {
        skill.body = parts[2].trim();
        for (const line of parts[1].trim().split('\n')) {
          const l = line.trim();
          if (l.startsWith('name:')) skill.name = l.slice(5).trim();
          else if (l.startsWith('description:')) skill.description = l.slice(12).trim();
        }
      }
    }
    return skill;
  }
}
