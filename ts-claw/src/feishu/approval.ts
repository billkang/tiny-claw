/** 人工审批 — 高危操作挂起等待人类裁决。 */

export interface ApprovalResult {
  allowed: boolean;
  reason: string;
}

type ResolveFn = (result: ApprovalResult) => void;

export class ApprovalManager {
  private pending = new Map<string, ResolveFn>();

  waitForApproval(
    taskId: string,
    toolName: string,
    args: string,
    sendNotification?: (text: string) => void,
  ): Promise<ApprovalResult> {
    return new Promise(resolve => {
      this.pending.set(taskId, resolve);

      const notice =
        `⚠️ 高危操作审批请求\n` +
        `Agent 试图执行以下动作:\n` +
        `- 工具: ${toolName}\n` +
        `- 参数: ${args}\n\n` +
        `任务 ID: ${taskId}\n\n` +
        `👉 请回复 "approve ${taskId}" 或 "reject ${taskId}" 决定是否放行。`;

      if (sendNotification) {
        sendNotification(notice);
      } else {
        console.log(`\n[需要审批 TaskID: ${taskId}] ${notice}\n`);
      }
    });
  }

  resolveApproval(taskId: string, allowed: boolean, reason: string): void {
    const resolve = this.pending.get(taskId);
    if (resolve) {
      this.pending.delete(taskId);
      resolve({ allowed, reason });
    }
  }
}

export const globalApprovalMgr = new ApprovalManager();

/** 简单规则判断是否触发人工审批。 */
export function isDangerousCommand(toolName: string, args: string): boolean {
  if (toolName === 'read_file') return false;
  if (toolName === 'write_file' || toolName === 'edit_file') return true;

  if (toolName === 'bash') {
    const patterns = [
      /rm\s+-r/,
      /sudo\s+/,
      /drop\s+/,
      />.*\.ts/,
      /nginx\s+-s/,
      /systemctl\s+/,
      /kill\s+/,
    ];
    for (const p of patterns) {
      if (p.test(args)) return true;
    }
  }

  return false;
}
