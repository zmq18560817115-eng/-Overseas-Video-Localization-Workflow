"""豆包视频拆解配置（复用火山方舟 ARK_API_KEY）。"""
from __future__ import annotations

import os
from pathlib import Path

from dotenv import dotenv_values

from paths import MVP_ROOT, OVERSEAS_ENV

DEFAULT_TURBO = "doubao-seed-2-1-turbo-260628"
DEFAULT_PRO = "doubao-seed-2-1-pro-260628"


def _env() -> dict[str, str]:
    merged: dict[str, str] = {}
    for path in (OVERSEAS_ENV, MVP_ROOT / ".env"):
        if path.exists():
            for k, v in dotenv_values(path).items():
                if v is not None:
                    merged[k] = str(v).strip()
    for k, v in os.environ.items():
        if v:
            merged.setdefault(k, v)
    return merged


def doubao_config() -> dict:
    env = _env()
    key = (env.get("ARK_API_KEY") or "").strip()
    mode = (env.get("DOUBAO_VIDEO_ANALYSIS_MODE") or "auto").strip().lower()
    turbo = (env.get("DOUBAO_VIDEO_ANALYSIS_MODEL") or DEFAULT_TURBO).strip()
    pro = (env.get("DOUBAO_VIDEO_ANALYSIS_MODEL_PRO") or DEFAULT_PRO).strip()
    base = (env.get("ARK_BASE_URL") or "https://ark.cn-beijing.volces.com/api/v3").rstrip("/")
    asr_on = (env.get("DOUBAO_ASR_ENABLED") or "1").strip().lower() not in ("0", "false", "no")
    asr_ready = bool(
        (env.get("VOLCENGINE_ASR_APP_ID") or "").strip()
        and (env.get("VOLCENGINE_ASR_ACCESS_TOKEN") or "").strip()
    )
    provider_default = (env.get("DECOMPOSE_PROVIDER") or "auto").strip().lower()
    llm_enabled = _env_flag(env.get("DOUBAO_VIDEO_ANALYSIS_ENABLED"), default=True)
    auto_enabled = _env_flag(env.get("VIDEO_ANALYSIS_AUTO"), default=True)
    return {
        "configured": bool(key),
        "provider_default": provider_default,
        "mode": mode,
        "turbo_model": turbo,
        "pro_model": pro,
        "base_url": base,
        "asr_enabled": asr_on,
        "asr_configured": asr_ready,
        "llm_enabled": llm_enabled,
        "auto_enabled": auto_enabled,
        "paused": not llm_enabled and not auto_enabled,
        "pause_message": (
            "视频结构拆解已暂停：已分析素材不会重复调豆包，新抓取素材也不会自动分析。"
            "恢复请在 overseas-loc-mvp/.env 将 DOUBAO_VIDEO_ANALYSIS_ENABLED、VIDEO_ANALYSIS_AUTO 设为 1。"
        ),
        "env_path": str(OVERSEAS_ENV),
        "setup": "在 overseas-loc-mvp/.env 填写 ARK_API_KEY，并开通豆包视频理解模型",
        "docs": "https://www.volcengine.com/docs/82379/1895586",
    }


def _env_flag(raw: str | None, *, default: bool) -> bool:
    if raw is None or not str(raw).strip():
        return default
    return str(raw).strip().lower() not in ("0", "false", "no", "off")


def video_analysis_policy() -> dict:
    """视频拆解策略（读 overseas-loc-mvp/.env）。"""
    cfg = doubao_config()
    return {
        "llm_enabled": bool(cfg.get("llm_enabled")),
        "auto_enabled": bool(cfg.get("auto_enabled")),
        "paused": bool(cfg.get("paused")),
        "message": str(cfg.get("pause_message") or ""),
    }


def resolve_model(mode: str | None = None) -> str:
    cfg = doubao_config()
    m = (mode or cfg["mode"] or "auto").strip().lower()
    if m == "pro":
        return cfg["pro_model"]
    if m == "turbo":
        return cfg["turbo_model"]
    return cfg["turbo_model"]


def ark_api_key() -> str:
    return doubao_config()["configured"] and _env().get("ARK_API_KEY", "") or ""
