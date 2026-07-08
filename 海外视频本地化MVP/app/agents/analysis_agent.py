"""拆解 Agent：判断某条素材是否已完成结构拆解，要不要跑、能不能用豆包跑。"""
from __future__ import annotations

from ..data import material_already_analyzed, material_detail, needs_doubao_analysis
from ..doubao_config import doubao_config
from .contracts import AgentResult


def evaluate(link_id: int) -> AgentResult:
    detail = material_detail(link_id)
    if not detail:
        return AgentResult(
            agent="analysis",
            status="blocked",
            summary="素材不存在",
            blockers=[f"未找到 link_id={link_id} 对应的素材，请先确认已采集入库"],
            next_suggestion="回素材库确认该素材是否还在，或重新采集",
        )

    lid = str(link_id)
    if material_already_analyzed(lid, detail):
        provider = str(detail.get("analyze_provider") or detail.get("analysis", {}).get("analyze_provider") or "")
        return AgentResult(
            agent="analysis",
            status="succeeded",
            summary=f"已完成结构拆解（provider={provider or '未知'}）",
            next_suggestion="可继续生成脚本",
            refs=[f"link_id={link_id}"],
        )

    doubao_ok = bool(doubao_config().get("configured"))
    will_use_doubao = doubao_ok and needs_doubao_analysis(lid, detail)
    summary = (
        "素材已入库但尚未拆解；点「拆解素材」时会自动使用已配置的豆包"
        if will_use_doubao
        else "素材已入库但尚未拆解；豆包未配置或未开启自动拆解，点「拆解素材」将使用免费规则模板"
    )
    return AgentResult(
        agent="analysis",
        status="not_started",
        summary=summary,
        blockers=["videos_meta 已有数据，但 video_analysis 里还没有这条素材的拆解结果"],
        next_suggestion="点顶栏/设置里的「拆解素材」，等待后台任务完成",
        refs=[f"link_id={link_id}"],
    )
