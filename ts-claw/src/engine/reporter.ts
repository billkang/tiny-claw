/** Reporter 接口 — 输出抽象的鸭子类型。 */

export interface Reporter {
  onThinking(): Promise<void> | void;
  onToolCall(toolName: string, args: string): Promise<void> | void;
  onToolResult(toolName: string, result: string, isError: boolean): Promise<void> | void;
  onMessage(content: string): Promise<void> | void;
}
