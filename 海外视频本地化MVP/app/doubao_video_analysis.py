"""豆包视频理解：精细分镜拆解 + 兼容旧 8 字段。"""
from __future__ import annotations

import asyncio
import json
import re
from pathlib import Path
from typing import Any

import httpx

from paths import DECOMPOSE_DIR, MVP_ROOT

from .doubao_config import DEFAULT_PRO, DEFAULT_TURBO, doubao_config, resolve_model
from .volcengine_asr import transcribe_media

SYSTEM_PROMPT = (
    "你是短视频素材拆解分析师。只基于提供的视频/封面/元数据/ASR 分析，不得编造画面中不存在的信息。"
    "输出必须是合法 JSON，不要 markdown 代码块。"
)

USER_PROMPT_TEMPLATE = """请把这个短视频拆成逐镜脚本（参考小红书视频拆解器）。

要求：
1. 按镜头或语义段切分，通常 2-8 秒一段。
2. shots 数组每项包含：index, start, end, visual_description, dialogue, subtitle_or_title,
   scene_type, camera_action, structure_role, pain_point, selling_point, reuse_note, confidence
3. structure_role 仅从 hook,pain,demo,proof,comparison,cta,transition,other 选择
4. dialogue 优先使用 ASR 原文，不要润色成新文案
5. visual_description 只描述画面，不写营销推断
6. 顶层还需：summary, reusable_template, subtitle_layout, video_structure, full_transcript

元数据:
{metadata}

ASR 片段:
{asr_text}
"""


def _strip_json(text: str) -> dict[str, Any]:
    raw = (text or "").strip()
    if raw.startswith("```"):
        raw = re.sub(r"^```(?:json)?\s*", "", raw)
        raw = re.sub(r"\s*```$", "", raw)
    return json.loads(raw)


def _resolve_video_path(link_id: str, meta: dict[str, Any]) -> Path | None:
    vid = str(meta.get("video_id") or "")
    candidates = [
        DECOMPOSE_DIR / link_id / "source.mp4",
        MVP_ROOT / "源视频" / f"{link_id}.mp4",
        MVP_ROOT / "源视频" / f"{vid}.mp4",
        MVP_ROOT.parent / "01_source_video" / f"ref-{int(link_id):03d}.mp4",
    ]
    for p in candidates:
        if p.is_file() and p.stat().st_size > 1000:
            return p
    return None


def _metadata_block(meta: dict[str, Any]) -> str:
    return json.dumps(
        {
            "link_id": meta.get("link_id"),
            "url": meta.get("url"),
            "title": meta.get("title"),
            "description": meta.get("description"),
            "author": meta.get("author"),
            "duration_sec": meta.get("duration_sec"),
            "view_count": meta.get("view_count"),
            "like_count": meta.get("like_count"),
            "hashtags": meta.get("hashtags"),
            "thumbnail_url": meta.get("thumbnail_url"),
        },
        ensure_ascii=False,
        indent=2,
    )


def _asr_block(transcript: dict[str, Any]) -> str:
    if transcript.get("full_transcript"):
        return transcript["full_transcript"]
    segs = transcript.get("segments") or []
    if not segs:
        return "（无 ASR，请结合视频画面推断台词，confidence 应偏低）"
    return "\n".join(
        f"[{s.get('start', '')}-{s.get('end', '')}] {s.get('text', '')}" for s in segs
    )


def derive_legacy_fields(detail: dict[str, Any]) -> dict[str, str]:
    shots = detail.get("shots") or []
    summary = str(detail.get("summary") or "")
    hooks = [s for s in shots if s.get("structure_role") == "hook"]
    pains = [s for s in shots if s.get("structure_role") == "pain"]
    demos = [s for s in shots if s.get("structure_role") in ("demo", "proof")]
    ctas = [s for s in shots if s.get("structure_role") == "cta"]

    def _dlg(items: list[dict]) -> str:
        return "；".join(str(x.get("dialogue") or x.get("subtitle_or_title") or "")[:80] for x in items if x)[:200]

    hook_line = _dlg(hooks) or (shots[0].get("dialogue") if shots else summary[:60])
    return {
        "hook_3s": hook_line or summary[:80],
        "pain_points": _dlg(pains) or summary[:120],
        "selling_points": _dlg(demos) or summary[:120],
        "scenes": "；".join(
            dict.fromkeys(str(s.get("visual_description") or "")[:40] for s in shots if s.get("visual_description"))
        )[:200],
        "video_structure": str(detail.get("video_structure") or "钩子 → 痛点 → 演示 → 证明 → CTA"),
        "subtitle_layout": str(detail.get("subtitle_layout") or "底部居中主字幕，关键词贴纸强调"),
        "cta": _dlg(ctas) or "收藏 / 评论 / 关注",
        "reusable_template": str(detail.get("reusable_template") or summary[:160]),
    }


def write_analysis_artifacts(link_id: str, row: dict[str, Any], detail: dict[str, Any], transcript: dict[str, Any]) -> Path:
    out = DECOMPOSE_DIR / link_id
    out.mkdir(parents=True, exist_ok=True)
    (out / "analysis.json").write_text(json.dumps(row, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    (out / "shots.json").write_text(
        json.dumps(
            {
                "link_id": link_id,
                "source_url": row.get("url", ""),
                "model": row.get("analyze_model", ""),
                "shots": detail.get("shots") or [],
            },
            ensure_ascii=False,
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )
    (out / "transcript.json").write_text(json.dumps(transcript, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    (out / "analysis.md").write_text(make_analysis_md(row, detail, transcript), encoding="utf-8")
    return out


def make_analysis_md(row: dict[str, Any], detail: dict[str, Any], transcript: dict[str, Any]) -> str:
    lines = [
        f"# 视频拆解 · #{row.get('link_id')}",
        "",
        f"- 来源: {row.get('url', '')}",
        f"- 模型: {row.get('analyze_model', '')} ({row.get('analyze_mode', '')})",
        "",
        "## 摘要",
        str(detail.get("summary") or "—"),
        "",
        "## 完整文案（逐字稿）",
        str(detail.get("full_transcript") or transcript.get("full_transcript") or "—"),
        "",
        "## 分镜表",
        "",
        "| # | 时间 | 画面描述 | 台词 | 字幕/标题 | 结构 |",
        "|---|------|----------|------|-----------|------|",
    ]
    for s in detail.get("shots") or []:
        lines.append(
            f"| {s.get('index', '')} | {s.get('start', '')}-{s.get('end', '')} | "
            f"{str(s.get('visual_description', ''))[:36]} | {str(s.get('dialogue', ''))[:24]} | "
            f"{str(s.get('subtitle_or_title', ''))[:20]} | {s.get('structure_role', '')} |"
        )
    lines.append("")
    return "\n".join(lines)


async def _ark_headers() -> dict[str, str]:
    from .doubao_config import _env

    api_key = (_env().get("ARK_API_KEY") or "").strip()
    if not api_key:
        raise RuntimeError("未配置 ARK_API_KEY")
    return {"Authorization": f"Bearer {api_key}"}


async def _upload_video(client: httpx.AsyncClient, path: Path, base: str) -> str:
    headers = await _ark_headers()
    with path.open("rb") as handle:
        files = {
            "purpose": (None, "user_data"),
            "file": (path.name, handle, "video/mp4"),
            "preprocess_configs[video][fps]": (None, "1"),
        }
        resp = await client.post(f"{base}/files", headers=headers, files=files, timeout=300)
    resp.raise_for_status()
    data = resp.json()
    return str(data.get("id") or data.get("file_id") or "")


def _extract_text(data: dict[str, Any]) -> str:
    if "output" in data:
        for item in data.get("output") or []:
            for c in item.get("content") or []:
                if c.get("type") in ("output_text", "text") and c.get("text"):
                    return str(c["text"])
    choices = data.get("choices") or []
    if choices:
        msg = choices[0].get("message") or {}
        return str(msg.get("content") or "")
    return ""


async def _call_responses(client: httpx.AsyncClient, *, base: str, model: str, file_id: str, prompt: str) -> str:
    headers = {**(await _ark_headers()), "Content-Type": "application/json"}
    payload = {
        "model": model,
        "input": [
            {
                "role": "user",
                "content": [
                    {"type": "input_video", "file_id": file_id},
                    {"type": "input_text", "text": prompt},
                ],
            }
        ],
    }
    resp = await client.post(f"{base}/responses", headers=headers, json=payload, timeout=300)
    if resp.status_code >= 400:
        raise RuntimeError(f"Responses API {resp.status_code}: {resp.text[:400]}")
    return _extract_text(resp.json())


async def _call_chat_text(client: httpx.AsyncClient, *, base: str, model: str, prompt: str) -> str:
    headers = {**(await _ark_headers()), "Content-Type": "application/json"}
    payload = {
        "model": model,
        "messages": [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": prompt},
        ],
    }
    resp = await client.post(f"{base}/chat/completions", headers=headers, json=payload, timeout=180)
    if resp.status_code >= 400:
        raise RuntimeError(f"Chat API {resp.status_code}: {resp.text[:400]}")
    return _extract_text(resp.json())
async def _call_chat_image(client: httpx.AsyncClient, *, base: str, model: str, image_url: str, prompt: str) -> str:
    headers = {**(await _ark_headers()), "Content-Type": "application/json"}
    payload = {
        "model": model,
        "messages": [
            {
                "role": "system",
                "content": SYSTEM_PROMPT,
            },
            {
                "role": "user",
                "content": [
                    {"type": "image_url", "image_url": {"url": image_url}},
                    {"type": "text", "text": prompt},
                ],
            },
        ],
    }
    resp = await client.post(f"{base}/chat/completions", headers=headers, json=payload, timeout=180)
    if resp.status_code >= 400:
        raise RuntimeError(f"Chat image API {resp.status_code}: {resp.text[:300]}")
    return _extract_text(resp.json())


async def _analyze_async(meta: dict[str, Any], *, model_mode: str = "auto") -> tuple[dict[str, Any], dict[str, Any], str]:
    cfg = doubao_config()
    if not cfg["configured"]:
        raise RuntimeError("未配置 ARK_API_KEY")

    base = cfg["base_url"]
    model = resolve_model(model_mode if model_mode in ("turbo", "pro") else cfg["mode"])
    if model_mode == "pro":
        model = cfg["pro_model"]

    link_id = str(meta.get("link_id") or "")
    video_path = _resolve_video_path(link_id, meta)
    transcript = transcribe_media(video_path)
    prompt = USER_PROMPT_TEMPLATE.format(metadata=_metadata_block(meta), asr_text=_asr_block(transcript))

    analyze_mode = "thumbnail_meta"
    raw_text = ""

    async with httpx.AsyncClient() as client:
        if video_path:
            try:
                file_id = await _upload_video(client, video_path, base)
                if file_id:
                    raw_text = await _call_responses(client, base=base, model=model, file_id=file_id, prompt=prompt)
                    analyze_mode = "video_file"
            except Exception:
                raw_text = ""

        if not raw_text:
            thumb = str(meta.get("thumbnail_url") or "").strip()
            if thumb:
                try:
                    raw_text = await _call_chat_image(client, base=base, model=model, image_url=thumb, prompt=prompt)
                    analyze_mode = "thumbnail_meta"
                except Exception:
                    raw_text = ""

        if not raw_text:
            text_prompt = prompt + "\n\n（无可用视频/封面，仅根据元数据与标题推断分镜，confidence 请 ≤0.6）"
            raw_text = await _call_chat_text(client, base=base, model=model, prompt=text_prompt)
            analyze_mode = "metadata_text"

    detail = _strip_json(raw_text)
    if "shots" not in detail:
        raise RuntimeError("豆包返回 JSON 缺少 shots 字段")
    if not detail.get("full_transcript") and transcript.get("full_transcript"):
        detail["full_transcript"] = transcript["full_transcript"]
    return detail, transcript, analyze_mode


def analyze_material(meta: dict[str, Any], *, model_mode: str = "auto") -> dict[str, Any]:
    """同步入口：返回完整 analysis 行（含旧 8 字段 + 精细扩展）。"""
    from .doubao_config import video_analysis_policy

    policy = video_analysis_policy()
    if not policy.get("llm_enabled"):
        raise RuntimeError(policy.get("message") or "视频豆包拆解已暂停（DOUBAO_VIDEO_ANALYSIS_ENABLED=0）")
    detail, transcript, analyze_mode = asyncio.run(_analyze_async(meta, model_mode=model_mode))
    legacy = derive_legacy_fields(detail)
    model = resolve_model(model_mode if model_mode in ("turbo", "pro") else doubao_config()["mode"])
    if model_mode == "pro":
        model = doubao_config()["pro_model"]

    from datetime import datetime, timezone

    row: dict[str, Any] = {
        "link_id": str(meta.get("link_id")),
        "url": meta.get("url", ""),
        "video_id": meta.get("video_id", ""),
        "author": meta.get("author", ""),
        **legacy,
        "analyzed_at": datetime.now(timezone.utc).replace(microsecond=0).isoformat(),
        "analyze_status": "ok",
        "analyze_provider": "doubao_video",
        "analyze_model": model,
        "analyze_mode": analyze_mode,
        "detail_level": "shot_timeline",
        "summary": detail.get("summary", ""),
        "full_transcript": detail.get("full_transcript") or transcript.get("full_transcript", ""),
        "shot_count": len(detail.get("shots") or []),
        "error_message": "",
    }
    write_analysis_artifacts(str(meta.get("link_id")), row, detail, transcript)
    return row


async def test_connection() -> dict[str, Any]:
    cfg = doubao_config()
    if not cfg["configured"]:
        return {"ok": False, "message": "未配置 ARK_API_KEY"}
    try:
        headers = await _ark_headers()
        async with httpx.AsyncClient(timeout=30) as client:
            resp = await client.post(
                f"{cfg['base_url']}/chat/completions",
                headers={**headers, "Content-Type": "application/json"},
                json={
                    "model": cfg["turbo_model"],
                    "messages": [{"role": "user", "content": "回复 OK"}],
                    "max_tokens": 8,
                },
            )
        if resp.status_code in (401, 403):
            return {"ok": False, "message": "ARK_API_KEY 无效或无权限"}
        if resp.status_code >= 400:
            return {"ok": False, "message": f"Ark {resp.status_code}: {resp.text[:200]}"}
        return {
            "ok": True,
            "message": f"豆包视频理解已连通 · 默认模型 {cfg['turbo_model']}",
            "turbo_model": cfg["turbo_model"],
            "pro_model": cfg["pro_model"],
        }
    except Exception as exc:
        return {"ok": False, "message": str(exc)[:300]}
