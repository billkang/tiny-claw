/** 数据模型 — Message、ToolCall、ToolResult 等核心类型。 */

// ─── 角色常量 ───────────────────────────────────────────
export const Role = {
  SYSTEM: 'system' as const,
  USER: 'user' as const,
  ASSISTANT: 'assistant' as const,
} as const;

export type Role = (typeof Role)[keyof typeof Role];

// ─── 数据模型 ───────────────────────────────────────────

export interface Usage {
  promptTokens: number;
  completionTokens: number;
}

export interface ToolCall {
  id: string;
  name: string;
  /** JSON 字符串 */
  arguments: string;
}

export interface ToolResult {
  toolCallId: string;
  output: string;
  isError: boolean;
}

export interface ToolDefinition {
  name: string;
  description: string;
  inputSchema: Record<string, unknown>;
}

export interface Message {
  role: Role;
  content: string;
  toolCalls?: ToolCall[];
  toolCallId?: string;
  usage?: Usage;
}
