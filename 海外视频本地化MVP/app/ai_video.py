"""与 overseas-loc-mvp/app/ai_video.py 保持一致的脚本侧配置。"""
from __future__ import annotations

import os
import re
from typing import Any

from .product_usage import THERMOS_USAGE_EN, THERMOS_PRODUCT_EN

AI_VIDEO_FOOTAGE = frozenset({"AI_BROLL", "AI_VIDEO"})


def ai_video_mode() -> str:
    return (os.getenv("AI_VIDEO_MODE") or "broll").strip().lower()


def default_footage_for_role(role: str) -> str:
    if ai_video_mode() == "script":
        return "AI_VIDEO"
    return "AI_BROLL" if role == "痛点" else "LIVE_ACTION"


def build_role_video_prompt(
    role: str,
    profile: dict[str, Any],
    product_name: str,
    voiceover_en: str,
) -> str:
    if role == "痛点" and profile.get("seedance"):
        return f"{profile['seedance']} {THERMOS_USAGE_EN}"
    scene_en = str(profile.get("en") or "daily baby feeding")
    vo = re.sub(r"\s+", " ", (voiceover_en or "").strip())[:120]
    safe = "no person face, no medical claim, vertical 9:16, TikTok product ad style"
    prod = product_name or THERMOS_PRODUCT_EN
    cup = THERMOS_PRODUCT_EN
    if role == "钩子":
        return (
            f"Hook shot opening, {scene_en}, sharp close-up of {cup} product hero on bedside table, "
            f"separate baby bottle beside it, cinematic soft light, subtle push-in, {safe}. "
            f"{THERMOS_USAGE_EN}. Mood: {vo or 'attention grabbing'}"
        )
    if role == "痛点":
        return (
            f"Problem moment, {scene_en}, cold milk in baby bottle, bulky old bottle warmer contrast, "
            f"moody lighting, {safe}. {THERMOS_USAGE_EN}. {vo}"
        )
    if role == "方案":
        return (
            f"Product demo, {scene_en}, flip-top lid open — pour breast milk FROM storage bag OR home baby bottle "
            f"INTO {cup} interior; after warming, tilt cup so warm milk streams OUT from small circular spout hole "
            f"in bowl-shaped lid recess into separate clear baby feeding bottle below, vertical °F display visible, {safe}. "
            f"{THERMOS_USAGE_EN}. {vo}"
        )
    if role == "证明":
        return (
            f"Proof detail, {scene_en}, macro shot of warm milk pouring OUT from circular spout hole in flip-top lid recess "
            f"of {cup} into baby feeding bottle, hinged lid open, pour-spout reference accurate, {safe}. "
            f"{THERMOS_USAGE_EN}. {vo}"
        )
    if role == "行动号召":
        return (
            f"CTA closing, {scene_en}, {cup} with flip-top lid closed on clean surface, baby bottle beside, "
            f"digital display and nurture wise band visible, {safe}. {THERMOS_USAGE_EN}. {vo}"
        )
    return f"{scene_en}, {prod}, cinematic product b-roll, {safe}. {THERMOS_USAGE_EN}. {vo}"
