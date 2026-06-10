/** OpenAI 兼容协议 Provider — 适配智谱、DeepSeek、OpenAI 等。 */

import OpenAI from 'openai';
import pino from 'pino';
import type { Message, ToolDefinition } from '../schema/message.js';
import { Role, Usage } from '../schema/message.js';

const logger = pino({ name: 'openai-provider' });

export class OpenAICompatProvider {
  private client: OpenAI;
  private model: string;

  constructor(model = 'glm-4.5-air', opts?: { baseURL?: string; apiKey?: string }) {
    const apiKey = opts?.apiKey ?? process.env['ZHIPU_API_KEY'];
    if (!apiKey) throw new Error('请设置 ZHIPU_API_KEY 环境变量或在初始化时传入 apiKey');

    const baseURL = opts?.baseURL ?? process.env['OPENAI_BASE_URL'] ?? 'https://open.bigmodel.cn/api/paas/v4/';
    this.client = new OpenAI({ apiKey, baseURL });
    this.model = model;
  }

  async generate(messages: Message[], availableTools?: ToolDefinition[]): Promise<Message> {
    const openaiMsgs: OpenAI.Chat.Completions.ChatCompletionMessageParam[] = [];

    for (const msg of messages) {
      if (msg.role === Role.SYSTEM) {
        openaiMsgs.push({ role: 'system', content: msg.content });
      } else if (msg.role === Role.USER) {
        if (msg.toolCallId) {
          openaiMsgs.push({ role: 'tool', content: msg.content, tool_call_id: msg.toolCallId });
        } else {
          openaiMsgs.push({ role: 'user', content: msg.content });
        }
      } else if (msg.role === Role.ASSISTANT) {
        const entry: OpenAI.Chat.Completions.ChatCompletionAssistantMessageParam = {
          role: 'assistant',
          content: msg.content,
        };
        if (msg.toolCalls && msg.toolCalls.length > 0) {
          entry.tool_calls = msg.toolCalls.map(tc => ({
            id: tc.id,
            type: 'function' as const,
            function: { name: tc.name, arguments: tc.arguments },
          }));
        }
        openaiMsgs.push(entry);
      }
    }

    const kwargs: OpenAI.Chat.Completions.ChatCompletionCreateParams = {
      model: this.model,
      messages: openaiMsgs,
    };

    if (availableTools && availableTools.length > 0) {
      kwargs.tools = availableTools.map(t => ({
        type: 'function' as const,
        function: {
          name: t.name,
          description: t.description,
          parameters: t.inputSchema as Record<string, unknown>,
        },
      }));
    }

    try {
      const response = await this.client.chat.completions.create(kwargs);
      const choice = response.choices[0];
      const data = choice.message;

      const result: Message = { role: Role.ASSISTANT, content: data.content ?? '' };

      if (response.usage) {
        result.usage = {
          promptTokens: response.usage.prompt_tokens ?? 0,
          completionTokens: response.usage.completion_tokens ?? 0,
        };
      }

      if (data.tool_calls) {
        result.toolCalls = data.tool_calls
          .filter(tc => tc.type === 'function')
          .map(tc => ({
            id: tc.id,
            name: tc.function.name,
            arguments: tc.function.arguments ?? '{}',
          }));
      }

      return result;
    } catch (err) {
      logger.error(err, 'API 请求失败');
      throw err;
    }
  }
}
