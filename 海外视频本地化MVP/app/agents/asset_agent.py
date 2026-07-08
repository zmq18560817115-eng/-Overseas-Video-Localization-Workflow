"""资产 Agent：产品外观闸门。复用 output_standards.py 里已有的资产清单/风险判断，
不重新实现——这里只是把结果套进 Agent 的统一状态格式。

硬规则（不可绕过）：白底主图缺失 → 出片状态必须 blocked。
场景图、倒出口图只能进 Prompt，不能当产品外观垫图——这条由
output_standards.build_asset_manifest 的 forbidden_use 字段承载，
本文件不重复判断细节，只读取它的结论。
"""
from __future__ import annotations

from ..output_standards import build_asset_manifest
from ..product_assets import get_product_white_hero_image
from .contracts import AgentResult


def evaluate(product_id: str) -> AgentResult:
    if not product_id:
        return AgentResult(
            agent="asset",
            status="blocked",
            summary="未选择产品",
            blockers=["请先在底部配置「产品」"],
        )

    hero = get_product_white_hero_image(product_id)
    manifest = build_asset_manifest(product_id)
    has_approved_hero = any(
        a.get("asset_type") == "product_identity" and a.get("source_path") and a.get("approval_status") == "approved"
        for a in manifest
    )

    if not hero or not hero.is_file() or not has_approved_hero:
        return AgentResult(
            agent="asset",
            status="blocked",
            summary="缺少已批准的白底主图，出片必须阻断",
            blockers=[
                f"未在 01_素材库/产品资料/{product_id}/**/主图/白底主图.png 找到可用的白底主图"
            ],
            next_suggestion="补齐白底主图后，在 8788 重新「生成脚本」或跑 refresh_project_seedance_source 刷新垫图",
            refs=[f"product_id={product_id}"],
        )

    scene_or_pour_count = sum(
        1 for a in manifest if a.get("asset_type") in ("scene", "usage_step", "detail_proof")
    )
    warnings: list[str] = []
    if scene_or_pour_count == 0:
        warnings.append("没有场景图/倒出口参考，出片时缺少环境与用法演示素材（不阻断，仅提示）")

    return AgentResult(
        agent="asset",
        status="succeeded" if not warnings else "needs_review",
        summary=f"白底主图就绪 · 资产清单共 {len(manifest)} 项",
        warnings=warnings,
        next_suggestion="可继续出片" if not warnings else "可以出片，但建议补充场景图/倒出口参考",
        refs=[f"product_id={product_id}", f"hero={hero}"],
    )
