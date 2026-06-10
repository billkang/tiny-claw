"""链路追踪 — 使用 contextvars 实现隐式 Span 树。"""

from __future__ import annotations

import json
import time
import uuid
from contextvars import ContextVar
from pathlib import Path

_current_span: ContextVar[Span | None] = ContextVar("_current_span", default=None)


class Span:
    """追踪跨度，代表一次操作的时间片段。"""

    def __init__(self, name: str, attributes: dict | None = None) -> None:
        self.span_id = uuid.uuid4().hex[:12]
        self.name = name
        self.start_time = time.time()
        self.end_time: float | None = None
        self.duration_ms: float | None = None
        self.attributes: dict[str, object] = attributes or {}
        self.children: list[Span] = []

    def add_attribute(self, key: str, value: object) -> None:
        self.attributes[key] = value

    def end(self) -> None:
        self.end_time = time.time()
        self.duration_ms = (self.end_time - self.start_time) * 1000

    def to_dict(self) -> dict:
        return {
            "name": self.name,
            "span_id": self.span_id,
            "start_time": self.start_time,
            "end_time": self.end_time,
            "duration_ms": self.duration_ms,
            "attributes": self.attributes,
            "children": [c.to_dict() for c in self.children],
        }


def start_span(name: str, attributes: dict | None = None) -> Span:
    """开启一个新的追踪跨度，自动挂到当前 Span 下。"""
    span = Span(name, attributes)
    parent = _current_span.get()
    if parent is not None:
        parent.children.append(span)
    _current_span.set(span)
    return span


def end_span(span: Span) -> None:
    """结束当前跨度，恢复父跨度。"""
    span.end()
    # 恢复父跨度，需要遍历找到上一个
    # 简化实现：不恢复 contextvar，调用方自行管理


def export_trace_to_file(root_span: Span, work_dir: str, session_id: str) -> None:
    """将链路追踪导出为 JSON 文件。"""
    trace_dir = Path(work_dir) / ".claw" / "traces"
    trace_dir.mkdir(parents=True, exist_ok=True)

    filename = trace_dir / f"trace_{session_id}_{int(time.time() * 1_000_000)}.json"
    data = json.dumps(root_span.to_dict(), indent=2, ensure_ascii=False)
    filename.write_text(data, encoding="utf-8")
