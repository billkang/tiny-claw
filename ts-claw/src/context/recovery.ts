/** 错误恢复 — 分析工具执行失败的特征并注入恢复建议。 */

export class RecoveryManager {
  analyzeAndInject(toolName: string, rawError: string): string {
    const lower = rawError.toLowerCase();

    if (toolName === 'edit_file') {
      if (rawError.includes('在文件中未找到') || rawError.includes('找不到该代码片段')) {
        return (
          `${rawError}\n\n[系统救援指南]: ` +
          '你提供的 old_text 与文件当前内容不一致，或者缺少必要的缩进。' +
          '请先使用 read_file 工具重新读取该文件，获取最新、准确的内容后，再重新发起编辑。'
        );
      }
      if (rawError.includes('匹配到了多处') || rawError.includes('提供更多上下文')) {
        return (
          `${rawError}\n\n[系统救援指南]: ` +
          '你的 old_text 不够具体，命中了多个相同代码块。' +
          '请在 old_text 中增加上下相邻的几行代码，以确保替换的唯一性。'
        );
      }
    }

    if (toolName === 'read_file' || toolName === 'write_file') {
      if (lower.includes('no such file') || lower.includes('eacces')) {
        return (
          `${rawError}\n\n[系统救援指南]: ` +
          '路径似乎不正确。请先使用 bash 执行 ls -la 或 find 命令查找正确的目录结构和文件名。'
        );
      }
      if (lower.includes('permission denied')) {
        return `${rawError}\n\n[系统救援指南]: 你没有权限操作该文件。请检查工作区限制。`;
      }
    }

    if (toolName === 'bash') {
      if (lower.includes('command not found')) {
        return (
          `${rawError}\n\n[系统救援指南]: ` +
          '系统中未安装该命令。请先思考是否有替代命令，或需要先安装。'
        );
      }
      if (lower.includes('timeout') || lower.includes('超时')) {
        return (
          `${rawError}\n\n[系统救援指南]: ` +
          '该命令执行超时。如果是常驻服务，请将其转入后台执行。'
        );
      }
    }

    return rawError;
  }
}
