/** 链路追踪 — 简单的 Span 树。 */

import crypto from 'node:crypto';
import { mkdirSync, writeFileSync } from 'node:fs';
import { join } from 'node:path';

export interface TraceAttributes {
  [key: string]: unknown;
}

export class Span {
  spanId: string;
  name: string;
  startTime: number;
  endTime?: number;
  durationMs?: number;
  attributes: TraceAttributes = {};
  children: Span[] = [];

  constructor(name: string, attributes?: TraceAttributes) {
    this.spanId = crypto.randomUUID().slice(0, 8);
    this.name = name;
    this.startTime = Date.now();
    if (attributes) this.attributes = attributes;
  }

  addAttribute(key: string, value: unknown): void {
    this.attributes[key] = value;
  }

  end(): void {
    this.endTime = Date.now();
    this.durationMs = this.endTime - this.startTime;
  }

  toJSON(): Record<string, unknown> {
    return {
      name: this.name,
      spanId: this.spanId,
      startTime: this.startTime,
      endTime: this.endTime,
      durationMs: this.durationMs,
      attributes: this.attributes,
      children: this.children.map(c => c.toJSON()),
    };
  }
}

export function exportTraceToFile(rootSpan: Span, workDir: string, sessionId: string): void {
  const traceDir = join(workDir, '.claw', 'traces');
  mkdirSync(traceDir, { recursive: true });

  const filename = join(traceDir, `trace_${sessionId}_${Date.now()}.json`);
  writeFileSync(filename, JSON.stringify(rootSpan.toJSON(), null, 2), 'utf-8');
}
