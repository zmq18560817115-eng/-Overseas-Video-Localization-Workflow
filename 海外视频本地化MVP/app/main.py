from __future__ import annotations

import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = ROOT / "scripts"
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))

from ensure_legacy_paths import ensure_legacy_junctions

ensure_legacy_junctions()

from fastapi import FastAPI, HTTPException, Query
from fastapi.concurrency import run_in_threadpool
from fastapi.responses import FileResponse, HTMLResponse, StreamingResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

from paths import OVERSEAS_RUNS_DIR, WEB_DIR

from .brand_policy import (
    detect_content_line,
    display_product_name,
    product_material_match,
    sanitize_analysis,
)
from .data import (
    filter_materials,
    filter_options,
    link_has_script,
    load_analysis_detail,
    load_materials,
    load_script_payload,
    material_detail,
    needs_doubao_analysis,
    shot_count_for,
)
from .analyze_jobs import analyze_status, clear_analyze_job, start_material_analyze
from .doubao_config import doubao_config, video_analysis_policy
from .doubao_video_analysis import test_connection as test_doubao_connection
from .jobs import job_status, start_job
from .library_api import list_feedback, list_finished, load_feedback, load_templates, save_feedback
from .feedback_loop import preview_constraints
from .feedback_tags import ISSUE_TAG_DEFS
from .llm_script import pick_template
from .olm_bridge import (
    build_delivery_zip,
    delivery_ready,
    ensure_delivery_project,
    finish_project,
    project_exists,
)
from .product_tags import normalize_selected_tags, product_delivery_tags
from .products import get_product, list_products, update_product
from .scene_script import scenario_conflict_note
from .script_gen import generate_script
from .thumbnails import ensure_thumbnail_cached
from .tiktok_collector_bridge import run_collector_import
from .tiktok_collector_bridge import query_collector_database
from .tiktok_collector_bridge import collector_database_enabled
from .tiktok_collector_bridge import sync_collector_database_to_workflow
from .seedance_bridge import (
    assemble_project,
    project_status,
    refresh_project_seedance_source,
    run_all,
    seedance_config,
    test_connection,
)

app = FastAPI(title="海外视频本地化工作台", version="1.0.0")
app.mount("/static", StaticFiles(directory=WEB_DIR), name="static")
UI_VERSION = 91


def _friendly_analyze_message(detail: dict[str, Any] | None, link_id: int | str) -> str:
    analysis = (detail or {}).get("analysis") if detail else None
    err = ""
    if isinstance(analysis, dict):
        err = str(analysis.get("error_message") or "")
    if "ReadTimeout" in err:
        return (
            f"豆包 API 响应超时（约 3 分钟）。可点击「重试拆解」，"
            f"或将源视频放入「源视频/{link_id}.mp4」后重新打开。"
        )
    if "doubao_fallback" in err:
        return "豆包拆解失败，已回退规则模板。可重试拆解，或补充源视频后再试。"
    return "豆包拆解未完成，请稍后重试。"


def _sanitize_analyze_message(message: str | None) -> str:
    text = str(message or "").strip()
    if not text:
        return ""
    if "video_analysis.csv" in text or "豆包失败，已回退规则" in text or "rule shots=" in text:
        return ""
    return text


class GenerateRequest(BaseModel):
    product_id: str = ""
    bridge: bool = Field(default=True, description="同步创建 overseas-loc-mvp 项目")
    target_country: str = "US"
    language: str = "en"
    style: str = "us_tiktok_spoken"
    audience_tags: list[str] = Field(default_factory=list)
    scenario_tags: list[str] = Field(default_factory=list)
    selling_tags: list[str] = Field(default_factory=list)
    pain_tags: list[str] = Field(default_factory=list)
    aspect_ratio: str = "9:16"
    edit_mode: str = "multi_shot"
    resolution: str = "720P"
    duration_sec: int = 5
    generate_count: int = 1
    creative_brief: str = ""
    prompt_enhanced: bool = False


class ProductUpdateRequest(BaseModel):
    product_name: str = ""
    target_audience: str = ""
    core_selling_points: str = ""
    pain_points: str = ""
    usage_scenarios: str = ""
    forbidden_terms: str = ""
    price_range: str = ""
    competitor_ref: str = ""


class FeedbackUpdateRequest(BaseModel):
    manual_edits: str = ""
    adopted: str = "待定"
    notes: str = ""
    issue_tags: list[str] = Field(default_factory=list)
    publish_views: str = ""
    publish_engagement: str = ""
    publish_notes: str = ""


class JobStartRequest(BaseModel):
    engine: str = "auto"
    provider: str = "auto"


class TikTokCollectorRequest(BaseModel):
    keywords: list[str] = Field(min_length=1)
    limit_per_keyword: int = Field(default=20, ge=1, le=100)


class TikTokCollectorDbSyncRequest(BaseModel):
    q: str = ""
    source_keyword: str = ""
    processing_status: str = ""
    limit: int = Field(default=20, ge=1, le=100)


@app.get("/")
async def index() -> HTMLResponse:
    raw = (WEB_DIR / "index.html").read_text(encoding="utf-8")
    return HTMLResponse(raw.replace("{{UI_VERSION}}", str(UI_VERSION)))


@app.get("/api/health")
async def health() -> dict:
    items = load_materials()
    return {
        "ok": True,
        "ui_version": UI_VERSION,
        "workbench": True,
        "materials": len(items),
        "analyzed": sum(1 for i in items if i.get("has_analysis")),
        "products": len(list_products()),
        "finished": len(list_finished()),
        "job": job_status(),
        "llm": {
            "available": bool(os.getenv("ANTHROPIC_API_KEY", "").strip()),
            "model": os.getenv("OVERSEAS_LOC_MODEL", "claude-sonnet-4-6"),
            "fallback": "rule_template（无 Key 时自动使用）",
            "role": "脚本生成",
        },
        "decompose": {
            "mode": "doubao" if doubao_config().get("configured") else "rule",
            "provider": doubao_config().get("provider_default", "auto"),
            "label": (
                "结构拆解（豆包视频理解 + 规则兜底）"
                if doubao_config().get("configured")
                else "结构拆解（基于标题/话题标签的规则模板）"
            ),
            "doubao": doubao_config(),
            "policy": video_analysis_policy(),
        },
        "delivery_engine": {
            "mode": "subprocess",
            "label": "overseas-loc-mvp（字幕/zip/SeedDance，由工作台子进程调用）",
        },
        "aigc_primary": "seedance-2.0",
        "seedance": seedance_config(),
        "tiktok_collector": {
            "available": True,
            "limit_per_keyword": 20,
            "output_dir": str((ROOT.parent / "tiktok_collector" / "data" / "raw").resolve()),
            "clean_output_dir": str((ROOT.parent / "tiktok_collector" / "data" / "raw" / "clean").resolve()),
            "mysql_enabled": collector_database_enabled(),
        },
    }


@app.get("/api/filters")
async def filters() -> dict:
    return filter_options()


@app.get("/api/materials")
async def materials(
    category: str = "",
    subcategory: str = "",
    q: str = "",
    analyzed_only: bool = False,
) -> dict:
    items = load_materials()
    filtered = filter_materials(
        items,
        category=category,
        subcategory=subcategory,
        keyword=q,
        analyzed_only=analyzed_only,
    )
    return {"total": len(filtered), "items": filtered}


@app.get("/api/materials/{link_id}/analysis/detail")
async def material_analysis_detail(link_id: int) -> dict:
    """打开素材详情时自动触发豆包拆解（若尚未完成）。"""
    detail = load_analysis_detail(str(link_id))
    job = analyze_status(link_id)
    lid = str(link_id)

    if detail and shot_count_for(lid, detail) >= 1:
        clear_analyze_job(link_id)
        warning = ""
        analysis = detail.get("analysis") or {}
        if isinstance(analysis, dict) and analysis.get("analyze_provider") == "rule":
            if "doubao_fallback" in str(analysis.get("error_message") or ""):
                warning = "最近一次豆包拆解超时，当前展示已有分镜结果。"
        return {**detail, "status": "ready", "warning": warning}

    if needs_doubao_analysis(lid, detail):
        if job and job.get("status") == "running":
            base = detail or {"link_id": link_id, "shots": [], "summary": "", "full_transcript": ""}
            return {**base, "status": "running", "message": "豆包视频拆解中，请稍候…", "job": job}
        if not job or job.get("status") != "running":
            job = start_material_analyze(link_id)
        base = detail or {"link_id": link_id, "shots": [], "summary": "", "full_transcript": ""}
        return {
            **base,
            "status": "running",
            "message": "豆包视频拆解中，请稍候…",
            "job": job,
        }

    policy = video_analysis_policy()
    if not detail and not policy.get("auto_enabled"):
        raise HTTPException(
            status_code=404,
            detail=policy.get("message") or "素材尚未拆解，且当前已暂停自动分析",
        )
    if detail and not policy.get("llm_enabled") and shot_count_for(lid, detail) < 1:
        return {
            **detail,
            "status": "ready",
            "warning": policy.get("message") or "视频豆包拆解已暂停，仅展示已有元数据。",
            "retryable": False,
        }

    if detail and isinstance(detail.get("analysis"), dict):
        err = str((detail["analysis"] or {}).get("error_message") or "")
        if "doubao_fallback" in err:
            return {
                **detail,
                "status": "error",
                "message": _friendly_analyze_message(detail, link_id),
                "retryable": True,
                "job": job,
            }

    if job and job.get("status") == "error":
        msg = _sanitize_analyze_message(job.get("output")) or _friendly_analyze_message(detail, link_id)
        return {
            **(detail or {"link_id": link_id, "shots": [], "summary": "", "full_transcript": ""}),
            "status": "error",
            "message": msg,
            "retryable": True,
            "job": job,
        }

    if not detail:
        raise HTTPException(status_code=404, detail="素材不存在或未抓取元数据")
    return {**detail, "status": "ready"}


@app.post("/api/materials/{link_id}/analyze")
async def material_analyze(link_id: int) -> dict:
    """手动重试豆包拆解。"""
    policy = video_analysis_policy()
    if not policy.get("llm_enabled"):
        raise HTTPException(
            status_code=403,
            detail=policy.get("message") or "视频豆包拆解已暂停",
        )
    from .jobs import PIPELINE, PYTHON
    import subprocess

    clear_analyze_job(link_id)
    proc = subprocess.run(
        [
            str(PYTHON),
            str(PIPELINE),
            "decompose",
            "--provider",
            "doubao",
            "--link-id",
            str(link_id),
        ],
        cwd=str(ROOT),
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        timeout=600,
    )
    detail = load_analysis_detail(str(link_id))
    if proc.returncode != 0 or (detail and shot_count_for(str(link_id), detail) < 1):
        msg = _friendly_analyze_message(detail, link_id)
        if proc.returncode != 0 and proc.stderr:
            msg = (proc.stderr or proc.stdout or msg)[-300:]
        raise HTTPException(status_code=500, detail=msg)
    return {"ok": True, "status": "ready", "detail": detail}


@app.get("/api/materials/{link_id}/thumbnail")
async def material_thumbnail(link_id: int) -> FileResponse:
    path = ensure_thumbnail_cached(link_id)
    if not path or not path.is_file():
        raise HTTPException(status_code=404, detail="封面不可用，请在「设置」运行「同步 TikTok」或「缓存封面」")
    return FileResponse(path, media_type="image/jpeg", filename=f"{link_id}.jpg")


@app.get("/api/materials/{link_id}")
async def material(link_id: int) -> dict:
    detail = material_detail(link_id)
    if not detail:
        raise HTTPException(status_code=404, detail="素材不存在")
    return detail


@app.get("/api/materials/{link_id}/preview")
async def material_preview(link_id: int, product_id: str = "") -> dict:
    detail = material_detail(link_id)
    if not detail:
        raise HTTPException(status_code=404, detail="素材不存在")
    if not detail.get("analysis"):
        raise HTTPException(status_code=409, detail="该素材尚未结构拆解，请先在「设置」运行「结构拆解」")

    products = list_products()
    product = None
    if product_id:
        product = get_product(product_id)
    if not product and products:
        product = get_product("便携恒温杯") or products[0]

    pid = (product or {}).get("product_id", "")
    raw_analysis = detail.get("analysis") or {}
    analysis = sanitize_analysis(raw_analysis, pid) if pid else raw_analysis
    templates = load_templates()
    matched = pick_template(raw_analysis, templates)
    template_hint = analysis.get("reusable_template", "")
    content_line = detect_content_line(detail)
    matched_product = product_material_match(pid, detail) if pid else True
    slug = detail.get("bridged_slug") or f"ref-{link_id:03d}"
    has_script = detail.get("has_script") or link_has_script(link_id)
    delivered = delivery_ready(slug)
    tag_pool = product_delivery_tags(product)
    saved = load_script_payload(link_id)
    selected = normalize_selected_tags(
        tag_pool,
        audience=saved.get("audience_tags") or None,
        scenarios=saved.get("scenario_tags") or None,
        selling=saved.get("selling_tags") or None,
        pains=saved.get("pain_tags") or None,
    )
    scenario_tags = selected.get("scenarios") or []
    return {
        "material": {**detail, "analysis": analysis, "content_line": content_line},
        "product": product,
        "template": matched,
        "template_hint": template_hint,
        "slug": slug,
        "project_ready": project_exists(slug),
        "has_script": has_script,
        "delivery_ready": delivered,
        "workflow": {
            "ref_ready": bool(raw_analysis),
            "product_ready": bool(pid),
            "script_ready": has_script,
            "delivery_ready": delivered,
        },
        "content_line": content_line,
        "product_match": matched_product,
        "brand_product": display_product_name(pid) if pid else "",
        "delivery_tags": tag_pool,
        "library_tags": tag_pool,
        "selected_tags": selected,
        "scenario_conflict_note": scenario_conflict_note(scenario_tags),
        "can_finish": has_script,
        "script_pack": detail.get("script_pack"),
        "script_meta": detail.get("script_meta"),
        "workflow_note": (
            "仅借鉴本条竞品的钩子/节奏/分镜结构；成片口播与画面统一露出我方品牌，不出现竞品名。"
        ),
        "seedance": project_status(slug) if project_exists(slug) else None,
    }


@app.post("/api/materials/{link_id}/generate")
async def generate(link_id: int, body: GenerateRequest) -> dict:
    try:
        result = generate_script(
            link_id,
            product_id=body.product_id,
            bridge=body.bridge,
            market={
                "target_country": body.target_country,
                "language": body.language,
                "style": body.style,
                "audience_tags": body.audience_tags,
                "scenario_tags": body.scenario_tags,
                "selling_tags": body.selling_tags,
                "pain_tags": body.pain_tags,
                "aspect_ratio": body.aspect_ratio,
                "edit_mode": body.edit_mode,
                "resolution": body.resolution,
                "duration_sec": body.duration_sec,
                "generate_count": body.generate_count,
                "creative_brief": body.creative_brief,
                "prompt_enhanced": body.prompt_enhanced,
            },
        )
        slug = f"ref-{link_id:03d}"
        result["slug"] = slug
        return result
    except ValueError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"生成失败: {exc}") from exc


@app.get("/api/products")
async def products() -> dict:
    rows = list_products()
    return {"total": len(rows), "items": rows}


@app.get("/api/products/{product_id}")
async def product_one(product_id: str) -> dict:
    row = get_product(product_id)
    if not row:
        raise HTTPException(status_code=404, detail="产品不存在")
    return row


@app.put("/api/products/{product_id}")
async def product_save(product_id: str, body: ProductUpdateRequest) -> dict:
    try:
        return update_product(product_id, body.model_dump())
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@app.get("/api/templates")
async def templates() -> dict:
    items = load_templates()
    return {"total": len(items), "items": items}


@app.get("/api/library/finished")
async def library_finished_list() -> dict:
    return {"items": list_finished()}


@app.get("/api/library/finished/{slug}")
async def library_finished_one(slug: str) -> dict:
    for item in list_finished():
        if item.get("slug") == slug:
            return item
    raise HTTPException(status_code=404, detail="成稿记录不存在")


@app.get("/api/library/feedback")
async def library_feedback_list() -> dict:
    return {"items": list_feedback()}


@app.get("/api/library/feedback-tags")
async def library_feedback_tags() -> dict:
    return {
        "items": [
            {"id": tag_id, "label": meta["label"], "hint_zh": meta["hint_zh"]}
            for tag_id, meta in ISSUE_TAG_DEFS.items()
        ],
    }


@app.get("/api/library/feedback-constraints")
async def library_feedback_constraints(
    product_id: str = Query(..., min_length=1),
    scenario_tags: str = Query("", description="逗号分隔场景标签"),
) -> dict:
    tags = [t.strip() for t in scenario_tags.split(",") if t.strip()]
    return preview_constraints(product_id, tags)


@app.get("/api/library/feedback/{slug}")
async def library_feedback_one(slug: str) -> dict:
    record = load_feedback(slug)
    if not record:
        raise HTTPException(status_code=404, detail="反馈记录不存在")
    return record


@app.post("/api/library/feedback/{slug}")
async def library_feedback_save(slug: str, body: FeedbackUpdateRequest) -> dict:
    try:
        record = save_feedback(
            slug,
            {
                "manual_edits": body.manual_edits,
                "adopted": body.adopted,
                "notes": body.notes,
                "issue_tags": body.issue_tags,
                "publish": {
                    "views": body.publish_views,
                    "engagement": body.publish_engagement,
                    "notes": body.publish_notes,
                },
            },
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return {"ok": True, "feedback": record}


@app.get("/api/jobs/status")
async def jobs_status() -> dict:
    return job_status()


@app.post("/api/jobs/{job_name}")
async def jobs_start(job_name: str, body: JobStartRequest | None = None) -> dict:
    try:
        return start_job(
            job_name,
            engine=(body.engine if body else "auto"),
            provider=(body.provider if body else "auto"),
        )
    except RuntimeError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@app.post("/api/tiktok-collector/collect")
async def tiktok_collector_collect(body: TikTokCollectorRequest) -> dict:
    keywords = [item.strip() for item in body.keywords if item.strip()]
    if not keywords:
        raise HTTPException(status_code=400, detail="请至少输入一个关键词")
    try:
        result = await run_in_threadpool(
            run_collector_import,
            keywords,
            limit_per_keyword=body.limit_per_keyword,
        )
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"TikTok 采集失败: {exc}") from exc
    items = load_materials()
    return {
        "ok": True,
        "keywords": keywords,
        "limit_per_keyword": body.limit_per_keyword,
        "total_collected": result.total_collected,
        "total_cleaned": result.total_cleaned,
        "total_dropped": result.total_dropped,
        "imported_new_links": result.imported_new_links,
        "updated_existing_links": result.updated_existing_links,
        "json_path": result.json_path,
        "csv_path": result.csv_path,
        "clean_json_path": result.clean_json_path,
        "clean_csv_path": result.clean_csv_path,
        "review_json_path": result.review_json_path,
        "output_dir": result.output_dir,
        "materials_total": len(items),
        "materials_analyzed": sum(1 for item in items if item.get("has_analysis")),
    }


@app.get("/api/tiktok-collector/db/videos")
async def tiktok_collector_db_videos(
    q: str = "",
    source_keyword: str = "",
    processing_status: str = "",
    limit: int = Query(20, ge=1, le=100),
) -> dict:
    try:
        result = await run_in_threadpool(
            query_collector_database,
            q=q,
            source_keyword=source_keyword,
            processing_status=processing_status,
            limit=limit,
        )
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"TikTok MySQL 查询失败: {exc}") from exc
    return {
        "ok": True,
        "db_enabled": result.db_enabled,
        "total": result.total,
        "items": result.items,
        "filters": {
            "q": q,
            "source_keyword": source_keyword,
            "processing_status": processing_status,
            "limit": limit,
        },
    }


@app.post("/api/tiktok-collector/db/sync")
async def tiktok_collector_db_sync(body: TikTokCollectorDbSyncRequest) -> dict:
    try:
        result = await run_in_threadpool(
            sync_collector_database_to_workflow,
            q=body.q,
            source_keyword=body.source_keyword,
            processing_status=body.processing_status,
            limit=body.limit,
        )
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"TikTok MySQL 同步失败: {exc}") from exc
    return {
        "ok": True,
        "db_enabled": result.db_enabled,
        "queried_total": result.queried_total,
        "synced_count": result.synced_count,
        "imported_new_links": result.imported_new_links,
        "updated_existing_links": result.updated_existing_links,
    }


@app.post("/api/delivery/{slug}/finish")
async def delivery_finish(slug: str) -> dict:
    try:
        link_id = int(slug.replace("ref-", ""))
        ensure_delivery_project(link_id)
        return finish_project(slug)
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except RuntimeError as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc


@app.get("/api/doubao/test")
async def doubao_test() -> dict:
    return await test_doubao_connection()


@app.get("/api/seedance/test")
async def seedance_test() -> dict:
    try:
        return test_connection()
    except RuntimeError as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc


@app.get("/api/delivery/{slug}/seedance")
async def delivery_seedance(slug: str) -> dict:
    if not project_exists(slug):
        raise HTTPException(status_code=404, detail="项目不存在，请先生成脚本")
    try:
        return project_status(slug)
    except RuntimeError as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc


@app.post("/api/delivery/{slug}/seedance/run")
async def delivery_seedance_run(slug: str, force: bool = Query(False)) -> dict:
    if not project_exists(slug):
        raise HTTPException(status_code=404, detail="项目不存在，请先生成脚本")
    try:
        status = project_status(slug)
        if not status.get("shots"):
            raise HTTPException(status_code=409, detail="本项目无可生成的 AI 分镜")
        if force:
            refresh_project_seedance_source(slug)
        return run_all(slug, force=force)
    except HTTPException:
        raise
    except RuntimeError as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc


@app.post("/api/delivery/{slug}/assemble")
async def delivery_assemble(slug: str) -> dict:
    if not project_exists(slug):
        raise HTTPException(status_code=404, detail="项目不存在，请先生成脚本")
    try:
        return assemble_project(slug)
    except RuntimeError as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc


@app.get("/api/delivery/{slug}/files/{file_path:path}")
async def delivery_file(slug: str, file_path: str) -> FileResponse:
    if not file_path.startswith("broll/"):
        raise HTTPException(status_code=404, detail="文件不存在")
    path = OVERSEAS_RUNS_DIR / slug / file_path
    if not path.is_file():
        raise HTTPException(status_code=404, detail="文件不存在")
    return FileResponse(path, filename=path.name)


@app.get("/api/delivery/{slug}/zip")
async def delivery_zip(slug: str) -> StreamingResponse:
    try:
        data, filename = build_delivery_zip(slug)
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    return StreamingResponse(
        iter([data]),
        media_type="application/zip",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


def main() -> None:
    import uvicorn

    uvicorn.run("app.main:app", host="127.0.0.1", port=8788, reload=False)


if __name__ == "__main__":
    main()
