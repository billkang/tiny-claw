/** LLM 提供商接口。 */

import type { Message, ToolDefinition } from '../schema/message.js';

export interface LLMProvider {
  generate(
    messages: Message[],
    availableTools?: ToolDefinition[],
  ): Promise<Message>;
}
