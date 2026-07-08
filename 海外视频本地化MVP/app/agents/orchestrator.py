"""主控 Agent：把拆解/脚本/资产三个 agent 的结果合并成一份"这条素材现在卡在哪"的判断。

v1 不调度任何新任务——判断完，实际执行仍然是用户去点现有的按钮
（拆解素材 / 生成脚本 / 出片）。这里只回答"下一步该点哪个"。
"""
from __future__ import annotations

from typing import Any

from ..data import material_detail
from ..jobs import job_status
from . import analysis_agent, asset_agent, script_agent
from .contracts import AgentResult

# agent 之间的先后顺序，决定"下一步建议"该指向谁
PIPELINE_ORDER = ("analysis", "script", "asset")


def _running_job_agent() -> str | None:
    """把后台 pipeline 任务名映射回 agent 名，用于标注 in_progress。"""
    state = job_status()
    if state.get("status") != "running":
        return None
    job_name = str(state.get("job") or "")
    if job_name == "decompose":
        return "analysis"
    return None


def evaluate_material(link_id: int, *, product_id: str = "") -> dict[str, Any]:
    detail = material_detail(link_id)
    resolved_product_id = product_id or str((detail or {}).get("product_id") or "")

    running_agent = _running_job_agent()

    results: list[AgentResult] = [
        analysis_agent.evaluate(link_id),
        script_agent.evaluate(link_id),
        asset_agent.evaluate(resolved_product_id),
    ]

    by_name = {r.agent: r for r in results}
    if running_agent and running_agent in by_name and by_name[running_agent].status == "not_started":
        by_name[running_agent].status = "running"
        by_name[running_agent].summary = "后台任务正在运行，请稍候"

    blocked = [r for r in results if r.status == "blocked"]
    running = [r for r in results if r.status == "running"]
    not_started = [r for r in results if r.status == "not_started"]
    needs_review = [r for r in results if r.status == "needs_review"]

    if blocked:
        overall = "blocked"
        next_agent = blocked[0].agent
        next_suggestion = blocked[0].next_suggestion or blocked[0].blockers[0] if blocked[0].blockers else "存在阻断项"
    elif running:
        overall = "in_progress"
        next_agent = running[0].agent
        next_suggestion = "等待当前后台任务完成"
    elif not_started:
        # 按 PIPELINE_ORDER 顺序找第一个还没开始的，作为下一步建议
        next_result = next(
            (by_name[name] for name in PIPELINE_ORDER if name in by_name and by_name[name].status == "not_started"),
            not_started[0],
        )
        overall = "ready"
        next_agent = next_result.agent
        next_suggestion = next_result.next_suggestion or f"运行 {next_result.agent} agent"
    elif needs_review:
        overall = "ready"
        next_agent = needs_review[0].agent
        next_suggestion = needs_review[0].next_suggestion or "有非阻断提示待关注"
    else:
        overall = "completed"
        next_agent = ""
        next_suggestion = "拆解/脚本/资产均已就绪，可以出片"

    return {
        "material_id": f"ref-{link_id:03d}" if isinstance(link_id, int) else str(link_id),
        "link_id": link_id,
        "product_id": resolved_product_id,
        "overall_status": overall,
        "next_agent": next_agent,
        "next_suggestion": next_suggestion,
        "agents": [r.to_dict() for r in results],
    }
