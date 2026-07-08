"""脚本 Agent：判断某条素材有没有生成过脚本、有没有具备生成条件。"""
from __future__ import annotations

from ..data import material_already_analyzed, material_detail
from .contracts import AgentResult


def evaluate(link_id: int) -> AgentResult:
    detail = material_detail(link_id)
    if not detail:
        return AgentResult(
            agent="script",
            status="blocked",
            summary="素材不存在",
            blockers=[f"未找到 link_id={link_id} 对应的素材"],
        )

    lid = str(link_id)
    if not material_already_analyzed(lid, detail):
        return AgentResult(
            agent="script",
            status="blocked",
            summary="缺少结构拆解结果，无法生成脚本",
            blockers=["video_analysis 里还没有这条素材的拆解结果"],
            next_suggestion="请先运行拆解 Agent（点「拆解素材」）",
            refs=[f"link_id={link_id}"],
        )

    if detail.get("has_script") and detail.get("script_pack"):
        title = str((detail.get("script_pack") or {}).get("title") or "")
        return AgentResult(
            agent="script",
            status="succeeded",
            summary=f"已生成脚本包{f'：{title}' if title else ''}",
            next_suggestion="可继续资产检查 / 出片",
            refs=[f"link_id={link_id}"],
        )

    return AgentResult(
        agent="script",
        status="not_started",
        summary="已具备拆解结果，尚未生成脚本",
        next_suggestion="在「视频生成」页选对标、点生成脚本",
        refs=[f"link_id={link_id}"],
    )
