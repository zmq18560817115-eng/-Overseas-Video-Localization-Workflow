"""Agent v1 的最小状态契约：所有 agent 都返回同一种结构，前端/接口只认这一种形状。"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

AGENT_NAMES = (
    "collector",
    "library",
    "analysis",
    "script",
    "asset",
    "production",
    "archive",
    "maintenance",
)

STATUSES = (
    "queued",
    "running",
    "succeeded",
    "failed",
    "blocked",
    "needs_review",
    "not_started",
)

OVERALL_STATUSES = ("blocked", "ready", "in_progress", "completed")


@dataclass(slots=True)
class AgentResult:
    agent: str
    status: str
    summary: str = ""
    blockers: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    next_suggestion: str = ""
    refs: list[str] = field(default_factory=list)

    def __post_init__(self) -> None:
        if self.agent not in AGENT_NAMES:
            raise ValueError(f"未知 agent 名称: {self.agent}（允许值: {AGENT_NAMES}）")
        if self.status not in STATUSES:
            raise ValueError(f"未知状态: {self.status}（允许值: {STATUSES}）")

    def to_dict(self) -> dict[str, Any]:
        return {
            "agent": self.agent,
            "status": self.status,
            "summary": self.summary,
            "blockers": list(self.blockers),
            "warnings": list(self.warnings),
            "next_suggestion": self.next_suggestion,
            "refs": list(self.refs),
        }
