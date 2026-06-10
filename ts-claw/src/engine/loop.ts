/** 核心 ReAct 主循环 — AgentEngine。 */

import pino from 'pino';
import { PromptComposer } from '../context/composer.js';
import { Compactor } from '../context/compactor.js';
import { RecoveryManager } from '../context/recovery.js';
import type { Session } from '../context/session.js';
import { Message, Role, ToolCall, ToolDefinition } from '../schema/message.js';
import type { BaseTool, Registry } from '../tools/base.js';
import { ReminderInjector } from './reminder.js';
import type { Reporter } from './reporter.js';
import type { LLMProvider } from '../provider/interface.js';

const logger = pino({ name: 'engine' });

const SUBAGENT_SYSTEM_PROMPT = `你是一个专门负责深度探索的探路者 (Explorer Subagent)。
你的任务是根据主架构师的指令，在当前工作区内仔细阅读代码、查阅日志，搜集足够的信息。

【核心纪律】
1. 你必须、且只能依靠内置工具（如 bash 的 find/grep，或 read_file）去寻找答案。绝对不允许凭空捏造或猜测！
2. 如果你没有找到确切的答案，你必须继续使用工具深入搜索。
3. 当且仅当你找到了确切的线索后，停止调用工具，直接输出一段纯文本作为你的终极汇报。主架构师会根据你的汇报来做下一步决策。`;

interface ToolResultWithMsg {
  message: Message;
  result: import('../schema/message.js').ToolResult;
}

export class AgentEngine {
  private compactor: Compactor;
  private recovery: RecoveryManager;
  private injector: ReminderInjector;

  constructor(
    private provider: LLMProvider,
    private registry: Registry,
    public enableThinking = false,
    public planMode = false,
  ) {
    this.compactor = new Compactor(200_000, 6);
    this.recovery = new RecoveryManager();
    this.injector = new ReminderInjector();
  }

  async run(session: Session, reporter?: Reporter): Promise<void> {
    logger.info({ sessionId: session.id, workDir: session.workDir, planMode: this.planMode }, '唤醒会话');

    const composer = new PromptComposer(session.workDir, this.planMode);
    const systemMsg = composer.build();

    let turnCount = 0;
    while (true) {
      turnCount++;

      const availableTools = this.registry.getAvailableTools();
      let workingMemory = session.getWorkingMemory(20);

      // 保底占位
      if (workingMemory.length > 0 && workingMemory[0].role !== Role.USER) {
        workingMemory = [
          { role: Role.USER, content: '[系统占位符] 这是为了保持上下文连贯性而注入的断点标记。请继续执行你刚才的任务。' },
          ...workingMemory,
        ];
      }

      let contextHistory: Message[] = [systemMsg, ...workingMemory];
      let compacted = this.compactor.compact(contextHistory);

      // Phase 1: Thinking
      if (this.enableThinking) {
        reporter?.onThinking();
        const thinkResp = await this.provider.generate(compacted);
        if (thinkResp && thinkResp.content) {
          compacted = [...compacted, thinkResp];
        }
      }

      // Phase 2: Action
      const actionResp = await this.provider.generate(compacted, availableTools);

      const finalAssistant: Message = {
        role: Role.ASSISTANT,
        content: actionResp.content,
        toolCalls: actionResp.toolCalls,
      };
      session.append(finalAssistant);

      if (actionResp.content && reporter) {
        await reporter.onMessage(actionResp.content);
      }

      if (!actionResp.toolCalls || actionResp.toolCalls.length === 0) break;

      // 并发执行工具
      const results = await Promise.all(
        actionResp.toolCalls.map(tc => this._executeTool(turnCount, tc, reporter)),
      );

      for (const r of results) {
        session.append(r.message);
      }

      // 死循环检测
      const lastTc = actionResp.toolCalls[actionResp.toolCalls.length - 1];
      const lastTr = results[results.length - 1].result;
      const reminder = this.injector.checkAndInject(lastTc, lastTr);
      if (reminder) session.append(reminder);
    }
  }

  private async _executeTool(turn: number, call: ToolCall, reporter?: Reporter): Promise<ToolResultWithMsg> {
    reporter?.onToolCall(call.name, call.arguments);

    const result = await this.registry.execute(call);
    let finalOutput = result.output;
    if (result.isError) {
      finalOutput = this.recovery.analyzeAndInject(call.name, result.output);
    }

    reporter?.onToolResult(
      call.name,
      finalOutput.length > 200 ? finalOutput.slice(0, 200) + '...' : finalOutput,
      result.isError,
    );

    return {
      message: { role: Role.USER, content: finalOutput, toolCallId: call.id },
      result,
    };
  }

  async runSub(
    taskPrompt: string,
    readOnlyRegistry: Registry,
    reporter?: Reporter,
  ): Promise<string> {
    const contextHistory: Message[] = [
      { role: Role.SYSTEM, content: SUBAGENT_SYSTEM_PROMPT },
      { role: Role.USER, content: taskPrompt },
    ];

    const MAX_SUB_TURNS = 10;
    for (let turn = 1; turn <= MAX_SUB_TURNS; turn++) {
      const availableTools = readOnlyRegistry.getAvailableTools();
      const compacted = this.compactor.compact(contextHistory);

      const actionResp = await this.provider.generate(compacted, availableTools);
      contextHistory.push(actionResp);

      if (!actionResp.toolCalls || actionResp.toolCalls.length === 0) {
        return actionResp.content;
      }

      const results = await Promise.all(
        actionResp.toolCalls.map(tc => this._executeTool(turn, tc, reporter)),
      );
      for (const r of results) {
        contextHistory.push(r.message);
      }
    }

    throw new Error(`子智能体探索过于深入，超过 ${MAX_SUB_TURNS} 轮被强制召回`);
  }
}
