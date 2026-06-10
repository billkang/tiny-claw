"""技能加载 — 从工作区 .claw/skills/ 目录加载 SKILL.md。"""

from __future__ import annotations

from pathlib import Path


class Skill:
    name: str
    description: str
    body: str


class SkillLoader:
    """加载工作区下的技能外挂文件。"""

    def __init__(self, work_dir: str) -> None:
        self.work_dir = work_dir

    def load_all(self) -> str:
        skill_dir = Path(self.work_dir) / ".claw" / "skills"
        if not skill_dir.is_dir():
            return ""

        lines: list[str] = []
        lines.append("\n### 可用专业技能 (Agent Skills)")
        lines.append("以下是你拥有的标准化外挂技能，请在符合描述的场景下严格遵循其正文指令：\n")

        for skill_file in sorted(skill_dir.rglob("SKILL.md")):
            content = skill_file.read_text(encoding="utf-8")
            skill = self._parse_skill_md(content)
            lines.append(f"#### 技能名称: {skill.name}")
            lines.append(f"**触发条件**: {skill.description}\n")
            lines.append("**执行指南**:")
            lines.append(skill.body)
            lines.append("\n---\n")

        result = "\n".join(lines)
        if len(result) < 50:
            return ""
        return result

    def _parse_skill_md(self, content: str) -> Skill:
        skill = Skill()
        skill.name = "Unknown Skill"
        skill.description = "No description provided."
        skill.body = content

        stripped = content.lstrip()
        if stripped.startswith("---"):
            parts = stripped.split("---", 2)
            if len(parts) == 3:
                skill.body = parts[2].strip()
                for line in parts[1].strip().splitlines():
                    line = line.strip()
                    if line.startswith("name:"):
                        skill.name = line[len("name:"):].strip()
                    elif line.startswith("description:"):
                        skill.description = line[len("description:"):].strip()

        return skill
