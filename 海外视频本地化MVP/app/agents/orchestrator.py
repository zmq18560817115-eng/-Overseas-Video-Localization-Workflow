"""主控 Agent 第一版：只判断状态、给下一步建议，不执行任何任务。

状态来源全部复用 app.data 现有函数：
- 采集：videos_meta.csv 是否有该素材（material_detail 是否命中）+ fetch_status
- 拆解：material_already_analyzed / load_analysis（video_analysis.csv analyze_status==ok
        或 AI拆解结果/{id}/shots.json / analysis.json）
- 脚本：link_has_script（脚本快照/{id}/script-pack.json 或 runs/ref-xxx/script-pack.json）
- 出片：olm_bridge.delivery_ready（data.load_materials 已计算 delivery_ready 字段）
- 归档：03_产出库/ref-xxx 是否存在版本目录
- 资产：复用 output_standards.build_asset_manifest / product_assets.get_product_white_hero_image，
        不重新实现资产规则；硬规则原样保留——缺已批准的白底主图 = 出片 blocked。
"""
from __future__ import annotations

from typing import Any

from paths import PRODUCTION_ARCHIVE_DIR  # scripts/paths.py，运行时已在 sys.path

from .. import data
from ..output_standards import build_asset_manifest
from ..product_assets import get_product_white_hero_image
from .contracts import AgentName, AgentState, OrchestratorDecision, TaskStatus

# 阶段顺序：主控 Agent 按此顺序找第一个未完成项作为 next_agent
STAGE_ORDER = [
    AgentName.COLLECTOR,
    AgentName.ANALYSIS,
    AgentName.SCRIPT,
    AgentName.ASSET,
    AgentName.PRODUCTION,
    AgentName.ARCHIVE,
]


def _collector_state(payload: dict[str, Any]) -> AgentState:
    state = AgentState(agent=AgentName.COLLECTOR)
    fetch_status = str(payload.get("fetch_status") or "")
    state.detail = {"fetch_status": fetch_status, "url": payload.get("url", "")}
    if fetch_status and fetch_status not in ("ok", "success", "done"):
        state.status = TaskStatus.NEEDS_REVIEW
        state.warnings.append(f"采集状态为 {fetch_status}，建议复核元数据")
        state.ready = True  # 有元数据即可进入拆解，仅提示复核
        state.next_suggestion = "元数据存在但采集状态异常，可先复核再拆解"
        return state
    state.status = TaskStatus.SUCCEEDED
    state.ready = True
    state.next_suggestion = "采集已完成"
    return state


def _analysis_state(payload: dict[str, Any]) -> AgentState:
    state = AgentState(agent=AgentName.ANALYSIS)
    link_id = str(payload["link_id"])
    has_analysis = bool(payload.get("has_analysis")) or data.material_already_analyzed(link_id)
    shot_count = data.shot_count_for(link_id)
    state.detail = {
        "has_analysis": has_analysis,
        "shot_count": shot_count,
        "analyze_provider": payload.get("analyze_provider", ""),
    }
    if not has_analysis:
        # PRD 6.4 验收项：videos_meta 有数据但 video_analysis 为空时必须明确提示
        state.status = TaskStatus.BLOCKED
        state.blockers.append("video_analysis.csv 无该素材拆解记录，拆解缺失")
        state.next_suggestion = "下一步建议运行拆解 Agent（页面「拆解」或 /api/materials/{id}/analyze）"
        return state
    state.status = TaskStatus.SUCCEEDED
    state.ready = True
    if shot_count < 1:
        state.warnings.append("已有拆解但缺少分镜（shots.json 为空），脚本质量可能受影响")
    state.next_suggestion = "拆解已就绪，可生成脚本"
    return state


def _script_state(payload: dict[str, Any], analysis: AgentState) -> AgentState:
    state = AgentState(agent=AgentName.SCRIPT)
    link_id = int(payload["link_id"])
    has_script = bool(payload.get("has_script")) or data.link_has_script(link_id)
    state.detail = {"has_script": has_script}
    if not analysis.ready:
        # PRD 6.5 验收项：没有 analysis 时不能静默生成脚本
        state.status = TaskStatus.BLOCKED
        state.blockers.append("等待拆解完成，未拆解素材不允许生成脚本")
        state.next_suggestion = "先运行拆解 Agent"
        return state
    if not has_script:
        state.status = TaskStatus.QUEUED
        state.next_suggestion = "拆解已完成，可生成脚本（页面「生成脚本」）"
        return state
    pack = payload.get("script_pack") or {}
    missing = [
        key
        for key in ("product_sources", "shot_asset_map")
        if isinstance(pack, dict) and key not in pack
    ]
    state.detail["pack_missing_keys"] = missing
    state.status = TaskStatus.SUCCEEDED
    state.ready = True
    if missing:
        state.warnings.append(
            "script_pack 缺少字段：" + "、".join(missing) + "，建议重新生成以补全出稿契约"
        )
    state.next_suggestion = "脚本已生成，可进入资产检查"
    return state


def _asset_state(payload: dict[str, Any], script: AgentState, product_id: str) -> AgentState:
    """硬规则不可绕过：缺已批准的白底主图 → 出片状态必须 blocked。
    场景图/倒出口图只能进 Prompt、不能当垫图，由 build_asset_manifest 的
    forbidden_use 字段承载，这里只读取它的结论，不重复判断细节。
    """
    state = AgentState(agent=AgentName.ASSET)
    if not script.ready:
        state.status = TaskStatus.QUEUED
        state.next_suggestion = "等待脚本生成后检查产品素材"
        return state
    if not product_id:
        state.status = TaskStatus.BLOCKED
        state.blockers.append("未选择产品，无法核对白底主图")
        state.next_suggestion = "请先在底部配置「产品」"
        return state

    hero = get_product_white_hero_image(product_id)
    manifest = build_asset_manifest(product_id)
    has_approved_hero = any(
        a.get("asset_type") == "product_identity" and a.get("source_path") and a.get("approval_status") == "approved"
        for a in manifest
    )
    state.detail = {"product_id": product_id, "manifest_count": len(manifest)}

    if not hero or not hero.is_file() or not has_approved_hero:
        state.status = TaskStatus.BLOCKED
        state.blockers.append(f"未在 01_素材库/产品资料/{product_id}/**/主图/白底主图.png 找到可用的白底主图")
        state.next_suggestion = "补齐白底主图后，在 8788 重新「生成脚本」或跑 refresh_project_seedance_source 刷新垫图"
        return state

    scene_or_pour_count = sum(
        1 for a in manifest if a.get("asset_type") in ("scene", "usage_step", "detail_proof")
    )
    state.status = TaskStatus.SUCCEEDED if scene_or_pour_count else TaskStatus.NEEDS_REVIEW
    state.ready = True
    if scene_or_pour_count == 0:
        state.warnings.append("没有场景图/倒出口参考，出片时缺少环境与用法演示素材（不阻断，仅提示）")
    state.next_suggestion = "可继续出片" if scene_or_pour_count else "可以出片，但建议补充场景图/倒出口参考"
    return state


def _production_state(payload: dict[str, Any], asset: AgentState) -> AgentState:
    state = AgentState(agent=AgentName.PRODUCTION)
    ready_flag = bool(payload.get("delivery_ready"))
    state.detail = {"delivery_ready": ready_flag, "bridged_slug": payload.get("bridged_slug", "")}
    if ready_flag:
        state.status = TaskStatus.SUCCEEDED
        state.ready = True
        state.next_suggestion = "成片已生成，可归档或下载 zip"
        return state
    if not asset.ready:
        state.status = TaskStatus.QUEUED
        state.next_suggestion = "等待资产检查"
        return state
    state.status = TaskStatus.QUEUED
    state.next_suggestion = "可进入 SeedDance 出片"
    return state


def _archive_state(payload: dict[str, Any], production: AgentState) -> AgentState:
    state = AgentState(agent=AgentName.ARCHIVE)
    slug = f"ref-{int(payload['link_id']):03d}"
    archive_dir = PRODUCTION_ARCHIVE_DIR / slug
    versions = (
        sorted(p.name for p in archive_dir.iterdir() if p.is_dir())
        if archive_dir.exists()
        else []
    )
    state.detail = {"slug": slug, "versions": versions}
    if versions:
        state.status = TaskStatus.SUCCEEDED
        state.ready = True
        state.next_suggestion = f"已归档 {len(versions)} 个版本（03_产出库/{slug}）"
        return state
    if production.ready:
        state.status = TaskStatus.QUEUED
        state.next_suggestion = "成片就绪但未归档，出片完成后交付引擎会自动写入 03_产出库"
        return state
    state.status = TaskStatus.QUEUED
    state.next_suggestion = "等待出片完成"
    return state


def evaluate_material(link_id: int, *, product_id: str = "") -> OrchestratorDecision:
    """主控 Agent 入口：给出某条素材的整体判断。纯读，不执行任务。

    product_id 用于资产阶段核对白底主图——素材本身不绑定固定产品，由调用方
    （页面当前选中的产品）传入；不传则资产阶段会因缺产品而 blocked。
    """
    decision = OrchestratorDecision(link_id=link_id)
    payload = data.material_detail(link_id)
    if payload is None:
        decision.current_stage = "material_missing"
        decision.next_agent = AgentName.COLLECTOR.value
        decision.blockers.append(f"素材 {link_id} 不存在于 videos_meta.csv，请先采集")
        return decision

    collector = _collector_state(payload)
    analysis = _analysis_state(payload)
    script = _script_state(payload, analysis)
    asset = _asset_state(payload, script, product_id)
    production = _production_state(payload, asset)
    archive = _archive_state(payload, production)

    decision.agents = {
        AgentName.COLLECTOR.value: collector,
        AgentName.ANALYSIS.value: analysis,
        AgentName.SCRIPT.value: script,
        AgentName.ASSET.value: asset,
        AgentName.PRODUCTION.value: production,
        AgentName.ARCHIVE.value: archive,
    }

    # 按阶段顺序找第一个未完成项
    ordered = [collector, analysis, script, asset, production, archive]
    stage_names = ["collected", "analysis", "script", "asset", "production", "archived"]
    decision.current_stage = "archived"
    decision.next_agent = ""
    decision.can_continue = True
    for name, state in zip(stage_names, ordered):
        decision.warnings.extend(state.warnings)
        if state.status == TaskStatus.SUCCEEDED and state.ready:
            continue
        decision.current_stage = f"{name}_{state.status.value}"
        decision.next_agent = state.agent.value
        decision.can_continue = state.status not in (TaskStatus.BLOCKED, TaskStatus.FAILED)
        decision.blockers.extend(state.blockers)
        break
    return decision
