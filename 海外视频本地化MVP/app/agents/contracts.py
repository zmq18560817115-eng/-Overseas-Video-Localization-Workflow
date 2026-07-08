"""Agent 统一契约：名称、任务状态、状态返回结构。

对应 docs/Agent化工作台产品需求文档-20260708.md 第 5.3 / 6.1 节。
本文件只做结构定义，不接业务逻辑。
"""
from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any


class AgentName(str, Enum):
    COLLECTOR = "collector"      # 采集 Agent
    LIBRARY = "library"          # 素材库 Agent（第二阶段）
    ANALYSIS = "analysis"        # 拆解 Agent
    SCRIPT = "script"            # 脚本 Agent
    ASSET = "asset"              # 资产 Agent
    PRODUCTION = "production"    # 出片 Agent
    ARCHIVE = "archive"          # 归档反馈 Agent
    MAINTENANCE = "maintenance"  # 维护 Agent


class TaskStatus(str, Enum):
    QUEUED = "queued"            # 未开始 / 等待前置
    RUNNING = "running"          # 运行中（第一阶段暂未使用）
    SUCCEEDED = "succeeded"      # 已完成
    FAILED = "failed"            # 失败
    BLOCKED = "blocked"          # 被前置条件或规则阻塞
    NEEDS_REVIEW = "needs_review"  # 需人工复核


# 前端状态条中文文案（web/app.js 可直接取用）
STATUS_LABELS: dict[str, str] = {
    TaskStatus.QUEUED: "未开始",
    TaskStatus.RUNNING: "运行中",
    TaskStatus.SUCCEEDED: "已完成",
    TaskStatus.FAILED: "失败",
    TaskStatus.BLOCKED: "阻塞",
    TaskStatus.NEEDS_REVIEW: "需复核",
}

AGENT_LABELS: dict[str, str] = {
    AgentName.COLLECTOR: "采集",
    AgentName.LIBRARY: "素材库",
    AgentName.ANALYSIS: "拆解",
    AgentName.SCRIPT: "脚本",
    AgentName.ASSET: "资产",
    AgentName.PRODUCTION: "出片",
    AgentName.ARCHIVE: "归档",
    AgentName.MAINTENANCE: "维护",
}


@dataclass
class AgentState:
    """单个 Agent 对某条素材的状态判断结果。"""

    agent: AgentName
    status: TaskStatus = TaskStatus.QUEUED
    ready: bool = False
    blockers: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    next_suggestion: str = ""
    detail: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "agent": self.agent.value,
            "label": AGENT_LABELS.get(self.agent, self.agent.value),
            "status": self.status.value,
            "status_label": STATUS_LABELS.get(self.status, self.status.value),
            "ready": self.ready,
            "blockers": self.blockers,
            "warnings": self.warnings,
            "next_suggestion": self.next_suggestion,
            "detail": self.detail,
        }


@dataclass
class OrchestratorDecision:
    """主控 Agent 对某条素材的整体判断（PRD 6.1 示例结构）。"""

    link_id: int
    current_stage: str = "unknown"
    next_agent: str = ""
    can_continue: bool = False
    blockers: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    agents: dict[str, AgentState] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "link_id": self.link_id,
            "current_stage": self.current_stage,
            "next_agent": self.next_agent,
            "can_continue": self.can_continue,
            "blockers": self.blockers,
            "warnings": self.warnings,
            "agents": {name: state.to_dict() for name, state in self.agents.items()},
        }
