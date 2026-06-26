"""AI 分镜视频：空镜 (AI_BROLL) 与脚本展示镜 (AI_VIDEO) 的生成策略与 Prompt。"""

from __future__ import annotations

import os
import re
from typing import Any

from .product_usage import THERMOS_USAGE_EN, THERMOS_PRODUCT_EN

AI_VIDEO_FOOTAGE = frozenset({"AI_BROLL", "AI_VIDEO"})


def ai_video_mode() -> str:
    """broll = 仅痛点空镜；script = 按脚本为各镜生成短视频展示。"""
    return (os.getenv("AI_VIDEO_MODE") or "broll").strip().lower()


def ai_video_on_finish() -> bool:
    if (os.getenv("SKIP_SEEDANCE") or "").strip().lower() in ("1", "true", "yes"):
        return False
    raw = (os.getenv("AI_VIDEO_ON_FINISH") or "1").strip().lower()
    return raw not in ("0", "false", "no", "off")


def ai_video_concat_enabled() -> bool:
    return (os.getenv("AI_VIDEO_CONCAT") or "1").strip().lower() not in ("0", "false", "no", "off")


def ai_video_concat_min_shots() -> int:
    raw = (os.getenv("AI_VIDEO_CONCAT_MIN_SHOTS") or "1").strip()
    try:
        return max(1, int(raw))
    except ValueError:
        return 1


def ai_video_max_shots() -> int:
    """0 = 不限制；正整数 = 每次最多生成几镜（按镜号顺序）。"""
    raw = (os.getenv("AI_VIDEO_MAX_SHOTS") or "0").strip()
    try:
        return max(0, int(raw))
    except ValueError:
        return 0


def shot_generates_video(footage_type: str | None, mode: str | None = None) -> bool:
    mode = mode or ai_video_mode()
    ft = (footage_type or "").strip()
    if mode == "script":
        return ft in AI_VIDEO_FOOTAGE or ft == "LIVE_ACTION"
    return ft == "AI_BROLL"


def footage_label(footage_type: str | None) -> str:
    ft = (footage_type or "").strip()
    if ft == "AI_BROLL":
        return "AI 空镜"
    if ft == "AI_VIDEO":
        return "AI 分镜"
    return "实拍"


def _clean_en(text: str, limit: int = 120) -> str:
    t = re.sub(r"\s+", " ", (text or "").strip())
    return t[:limit]


def build_shot_video_prompt(
    *,
    role: str,
    pack_shot: dict[str, Any],
    story_shot: dict[str, Any] | None = None,
    scene_en: str = "daily baby feeding",
    product_name: str = "portable milk-warming thermos cup",
) -> str:
    """从脚本镜位合成 SeedDance 英文 Prompt。"""
    story_shot = story_shot or {}
    explicit = str(pack_shot.get("seedance_prompt") or story_shot.get("notes") or "").strip()
    if len(explicit) >= 10:
        return explicit

    vo = _clean_en(
        str(pack_shot.get("voiceover_en") or pack_shot.get("subtitle_en") or story_shot.get("copy") or "")
    )
    visual = str(pack_shot.get("visual_prompt") or pack_shot.get("visual") or story_shot.get("visual") or "")
    safe = "no person face, no medical claim, vertical 9:16, TikTok product ad style"
    cup = THERMOS_PRODUCT_EN

    role_key = (role or "").strip()
    if role_key == "钩子":
        return (
            f"Hook shot opening, {scene_en}, sharp close-up of {cup} on table, baby bottle beside, "
            f"cinematic soft light, subtle push-in, {safe}. {THERMOS_USAGE_EN}. "
            f"Voiceover mood: {vo or 'attention grabbing'}"
        )
    if role_key == "痛点":
        return (
            f"Problem moment, {scene_en}, cold milk in baby bottle, bulky old bottle warmer contrast, "
            f"moody lighting, {safe}. {THERMOS_USAGE_EN}. {vo}"
        )
    if role_key == "方案":
        return (
            f"Product demo, {scene_en}, flip-top lid open — pour breast milk FROM storage bag OR home baby bottle "
            f"INTO {cup} interior; after warming, tilt cup so warm milk streams OUT from small circular spout hole "
            f"in bowl-shaped lid recess into separate clear baby feeding bottle below, vertical °F display visible, {safe}. "
            f"{THERMOS_USAGE_EN}. {vo}"
        )
    if role_key == "证明":
        return (
            f"Proof detail shot, {scene_en}, macro of warm milk pouring OUT from circular spout hole in flip-top lid recess "
            f"of {cup} into baby feeding bottle, hinged lid open, pour-spout reference accurate, {safe}. "
            f"{THERMOS_USAGE_EN}. {vo}"
        )
    if role_key == "行动号召":
        return (
            f"CTA closing shot, {scene_en}, {cup} with flip-top lid closed, baby bottle beside, "
            f"digital display and nurture wise band visible, {safe}. {THERMOS_USAGE_EN}. {vo}"
        )

    return (
        f"{scene_en}, {cup}, {_clean_en(visual, 80)}, cinematic product b-roll, {safe}. "
        f"{THERMOS_USAGE_EN}. {vo}"
    )


def pipeline_label(mode: str | None = None) -> str:
    mode = mode or ai_video_mode()
    if mode == "script":
        return "脚本生成 → 分镜 → 各镜 Prompt → SeedDance 2.0 → 分镜短视频 → 成稿 zip"
    return "脚本生成 → 分镜生成 → 视频 Prompt → SeedDance 2.0 → 输出视频 → 保存成稿"
