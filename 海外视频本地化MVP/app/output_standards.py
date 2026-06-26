"""overseas-video-output-standards skill 的结构化出稿契约（写入 script-pack）。"""
from __future__ import annotations

from pathlib import Path
from typing import Any

from paths import PRODUCT_MATERIALS_DIR, WORKFLOW_ROOT

from .product_assets import get_product_hero_image, list_product_images, product_listing_dir
from .scene_script import resolve_scenario_profile, scenario_conflict_note

KNOWLEDGE_PRODUCTS = WORKFLOW_ROOT / "overseas-loc-mvp" / "knowledge" / "products"
COMPLIANCE_DOC = WORKFLOW_ROOT / "overseas-loc-mvp" / "knowledge" / "processes" / "海外短视频合规禁词.md"


def _rel(path: Path | None) -> str:
    if not path:
        return ""
    try:
        return path.relative_to(WORKFLOW_ROOT).as_posix()
    except ValueError:
        return str(path)


def build_product_sources(product_id: str) -> list[dict[str, str]]:
    sources: list[dict[str, str]] = []
    md = PRODUCT_MATERIALS_DIR / f"{product_id}.md"
    if md.is_file():
        sources.append({"type": "product_doc", "path": _rel(md)})
    listing = product_listing_dir(product_id)
    if listing.is_dir():
        sources.append({"type": "listing_assets", "path": _rel(listing)})
    kbase = KNOWLEDGE_PRODUCTS / f"{product_id}.md"
    if kbase.is_file():
        sources.append({"type": "knowledge_fallback", "path": _rel(kbase)})
    if COMPLIANCE_DOC.is_file():
        sources.append({"type": "compliance", "path": _rel(COMPLIANCE_DOC)})
    sources.append({"type": "skill", "path": "overseas-video-output-standards/SKILL.md"})
    return sources


def build_asset_manifest(product_id: str) -> list[dict[str, Any]]:
    listing = product_listing_dir(product_id)
    hero = get_product_hero_image(product_id)
    manifest: list[dict[str, Any]] = []

    def add(path: Path | None, asset_type: str, allowed: str, forbidden: str = "") -> None:
        if not path or not path.is_file():
            return
        manifest.append({
            "asset_id": f"{product_id}:{path.name}",
            "product": product_id,
            "source_path": _rel(path),
            "asset_type": asset_type,
            "approval_status": "approved",
            "allowed_use": allowed,
            "forbidden_use": forbidden,
        })

    add(hero, "product_identity", "SeedDance 垫图、产品外观锚点")
    pour = listing / "主图" / "倒出口参考.png"
    if not pour.is_file():
        pour = listing / "主图" / "倒出口参考.jpg"
    add(pour, "usage_step", "倒出口/翻盖/倾斜出液演示", "宽口直倒、奶瓶入杯")
    white = listing / "主图" / "白底主图.png"
    add(white, "product_identity", "产品身份白底图")

    for path in list_product_images(product_id)[:12]:
        if hero and path.resolve() == hero.resolve():
            continue
        sub = path.parent.name
        atype = "scene" if sub in ("M端", "副图", "A+") else "detail_proof"
        add(path, atype, f"场景/细节参考（{sub}）", "unsupported efficacy claim")

    if not manifest:
        manifest.append({
            "asset_id": f"{product_id}:missing",
            "product": product_id,
            "source_path": "",
            "asset_type": "product_identity",
            "approval_status": "needs_review",
            "allowed_use": "",
            "forbidden_use": "missing approved hero image",
        })
    return manifest


def build_scene_continuity(market: dict[str, Any], profile: dict[str, Any]) -> dict[str, Any]:
    scene_zh = profile.get("zh") or profile.get("primary_tag") or "日常喂养"
    scene_en = profile.get("en") or "daily baby feeding"
    tags = market.get("scenario_tags") or []
    note = scenario_conflict_note(tags)
    props = ["baby feeding bottle", "milk storage bag", "bedside table"]
    if profile.get("id") == "car":
        props = ["car cup holder", "baby bottle", "diaper bag"]
    elif profile.get("id") == "travel":
        props = ["travel bag", "baby bottle", "airport lounge"]
    elif profile.get("id") == "office":
        props = ["office desk", "baby bottle", "pumping bag"]
    return {
        "main_scene_zh": scene_zh,
        "main_scene_en": scene_en,
        "time_of_day": "night" if profile.get("id") == "bedroom" else "daytime",
        "lighting": "soft home light" if profile.get("id") == "bedroom" else "natural daylight",
        "props": props,
        "allowed_transitions": "single-scene only unless scripted",
        "conflict_note": note,
        "constraints": "Do not mix bedroom/car/airport in one video without scripted reason",
    }


def build_character_continuity(market: dict[str, Any], product_id: str) -> dict[str, Any]:
    audience = market.get("audience_tags") or []
    role = "caregiver parent"
    if any("背奶" in t or "办公" in t for t in audience):
        role = "working mother"
    if product_id == "吸奶器":
        role = "pumping mother"
    return {
        "role": role,
        "age_range": "25-38",
        "wardrobe": "casual home loungewear or travel casual",
        "visibility": "hands-only or over-shoulder preferred; no full face unless approved ref",
        "emotional_state": "calm, practical, relieved",
        "relationship_to_product": "prepares milk with product as separate thermos cup",
        "allowed_scene_changes": [],
        "notes": "Use product-only shots if identity cannot be kept consistent across 5 shots",
    }


def build_shot_asset_map(
    storyboard: list[dict[str, Any]],
    *,
    product_id: str,
    asset_manifest: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    hero_path = next(
        (a["source_path"] for a in asset_manifest if a.get("asset_type") == "product_identity" and a.get("source_path")),
        "",
    )
    usage_path = next(
        (a["source_path"] for a in asset_manifest if a.get("asset_type") == "usage_step" and a.get("source_path")),
        hero_path,
    )
    rows: list[dict[str, Any]] = []
    for shot in storyboard:
        role = str(shot.get("role") or "")
        ft = str(shot.get("footage_type") or "LIVE_ACTION")
        is_ai = ft in ("AI_BROLL", "AI_VIDEO")
        if role in ("方案", "证明"):
            asset_path = usage_path or hero_path or "missing"
            asset_type = "usage_step"
        elif role in ("钩子", "行动号召"):
            asset_path = hero_path or "missing"
            asset_type = "product_identity"
        else:
            asset_path = hero_path or "missing"
            asset_type = "product_identity" if is_ai else "scene"
        method = "SeedDance" if is_ai else "live_action_or_edit"
        rows.append({
            "shot_id": int(shot.get("number", len(rows) + 1)),
            "time_range": shot.get("timing", ""),
            "script_role": role,
            "dialogue_or_subtitle": shot.get("subtitle_en") or shot.get("voiceover_en", ""),
            "visual_description": shot.get("visual") or shot.get("visual_prompt", ""),
            "required_asset_type": asset_type,
            "asset_path_or_status": asset_path if asset_path else "missing",
            "generation_or_edit_method": method,
            "prompt_guardrails": shot.get("seedance_prompt") or shot.get("visual_prompt", ""),
            "compliance_note": "",
        })
    return rows


def build_claim_guardrails(product_id: str) -> dict[str, Any]:
    if product_id == "便携恒温杯":
        return {
            "allowed_claims": [
                "portable rechargeable warming",
                "pour into cup to warm then pour to bottle",
                "fits cup holder / diaper bag (if selected in tags)",
            ],
            "forbidden_claims": [
                "medical grade",
                "guaranteed",
                "sterilization guarantee",
                "bottle inside cup",
                "commercial milk bottle as input",
            ],
            "rewrites": {
                "pain-free": "designed for a calmer routine",
                "best": "handy for travel",
            },
        }
    if product_id == "吸奶器":
        return {
            "allowed_claims": ["adjustable suction", "portable", "easier cleaning"],
            "forbidden_claims": [
                "medical grade",
                "pain-free",
                "increase milk supply",
                "FDA approved",
                "通乳",
                "催奶",
            ],
            "rewrites": {"pain-free": "gentler-feeling routine"},
        }
    return {"allowed_claims": [], "forbidden_claims": ["unsupported medical claims"], "rewrites": {}}


def build_delivery_risks(
    *,
    asset_manifest: list[dict[str, Any]],
    shot_asset_map: list[dict[str, Any]],
    scene_continuity: dict[str, Any],
) -> dict[str, Any]:
    blockers: list[str] = []
    warnings: list[str] = []
    if any(a.get("approval_status") == "needs_review" for a in asset_manifest):
        blockers.append("缺少已批准产品主图/垫图")
    if any(s.get("asset_path_or_status") == "missing" for s in shot_asset_map):
        blockers.append("部分镜头缺少素材路径")
    if scene_continuity.get("conflict_note"):
        warnings.append(str(scene_continuity["conflict_note"]))
    status = "BLOCKED" if blockers else ("WARNING" if warnings else "PASS")
    return {"status": status, "blockers": blockers, "warnings": warnings}


def enrich_pack_with_standards(
    pack: dict[str, Any],
    *,
    product: dict[str, str],
    market: dict[str, Any],
    analysis: dict[str, str] | None = None,
) -> dict[str, Any]:
    """将 skill 要求的 7 段契约写入 script-pack。"""
    _ = analysis
    product_id = str(product.get("product_id") or "")
    profile = resolve_scenario_profile(market.get("scenario_tags") or [])
    storyboard = pack.get("storyboard") or []

    asset_manifest = build_asset_manifest(product_id)
    scene_continuity = build_scene_continuity(market, profile)
    character_continuity = build_character_continuity(market, product_id)
    shot_asset_map = build_shot_asset_map(
        storyboard,
        product_id=product_id,
        asset_manifest=asset_manifest,
    )
    claim_guardrails = build_claim_guardrails(product_id)
    delivery_risks = build_delivery_risks(
        asset_manifest=asset_manifest,
        shot_asset_map=shot_asset_map,
        scene_continuity=scene_continuity,
    )

    pack["product_sources"] = build_product_sources(product_id)
    pack["asset_manifest"] = asset_manifest
    pack["shot_asset_map"] = shot_asset_map
    pack["scene_continuity"] = scene_continuity
    pack["character_continuity"] = character_continuity
    pack["claim_guardrails"] = claim_guardrails
    pack["delivery_risks"] = delivery_risks
    pack["output_standards_version"] = "overseas-video-output-standards-v1"
    return pack
