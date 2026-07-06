"""首页热点素材：按产品从 MySQL / TikTok 采集同步到工作台素材库。"""
from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from paths import MVP_ROOT

from .data import load_materials
from .products import get_product
from .tiktok_collector_bridge import (
    collector_database_enabled,
    run_collector_import,
    sync_collector_database_to_workflow,
)

STATE_PATH = MVP_ROOT / "data" / "hotspot_refresh.json"

PRODUCT_COLLECTOR_KEYWORDS: dict[str, list[str]] = {
    "吸奶器": ["breast pump", "wearable breast pump", "electric breast pump"],
    "便携恒温杯": ["portable bottle warmer", "baby bottle warmer", "travel milk warmer"],
}


def _utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def collector_keywords_for_product(product_id: str) -> list[str]:
    pid = (product_id or "").strip()
    if not pid:
        return []
    keys = PRODUCT_COLLECTOR_KEYWORDS.get(pid)
    if keys:
        return list(keys)
    product = get_product(pid)
    if product:
        name = (product.get("product_name") or "").strip()
        if name and name != pid:
            return [name, pid]
    return [pid]


def load_hotspot_state() -> dict[str, Any]:
    if not STATE_PATH.exists():
        return {}
    try:
        return json.loads(STATE_PATH.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return {}


def save_hotspot_state(state: dict[str, Any]) -> None:
    STATE_PATH.parent.mkdir(parents=True, exist_ok=True)
    STATE_PATH.write_text(json.dumps(state, ensure_ascii=False, indent=2), encoding="utf-8")


def hotspot_status_payload() -> dict[str, Any]:
    state = load_hotspot_state()
    items = load_materials()
    return {
        "last_refresh_at": state.get("last_refresh_at"),
        "last_product_id": state.get("last_product_id") or "",
        "last_mode": state.get("last_mode") or "",
        "last_imported_new": int(state.get("last_imported_new") or 0),
        "last_updated": int(state.get("last_updated") or 0),
        "mysql_enabled": collector_database_enabled(),
        "materials_total": len(items),
        "materials_analyzed": sum(1 for i in items if i.get("has_analysis")),
        "keyword_map": PRODUCT_COLLECTOR_KEYWORDS,
    }


def refresh_hotspot_videos(
    *,
    product_id: str = "",
    mode: str = "auto",
    limit: int = 80,
    limit_per_keyword: int = 30,
) -> dict[str, Any]:
    """
    mode:
      auto  — MySQL 热榜同步（若已配置），否则仅返回刷新提示
      sync  — 仅 MySQL 同步
      collect — Playwright 浏览器采集（需人工登录 TikTok）
    """
    product_id = (product_id or "").strip()
    mode = (mode or "auto").strip().lower()
    if mode not in ("auto", "sync", "collect"):
        mode = "auto"

    keywords = collector_keywords_for_product(product_id)
    mysql_enabled = collector_database_enabled()
    out: dict[str, Any] = {
        "ok": True,
        "product_id": product_id,
        "mode": mode,
        "keywords": keywords,
        "mysql_enabled": mysql_enabled,
        "imported_new_links": 0,
        "updated_existing_links": 0,
        "synced_count": 0,
        "total_collected": 0,
        "message": "",
    }

    if mode == "collect":
        if not keywords:
            return {**out, "ok": False, "message": "请先选择产品后再抓取热点"}
        result = run_collector_import(
            keywords,
            limit_per_keyword=max(1, min(200, int(limit_per_keyword or 30))),
            product_id=product_id,
        )
        imported = int(result.imported_new_links or 0)
        collected = int(result.total_collected or 0)
        if collected <= 0:
            msg = (
                "浏览器采集未抓到视频：请在弹出的 Chrome 中完成 TikTok 登录/验证码后重试；"
                "若未弹出窗口，请用「启动页面.cmd」启动工作台（勿用 Cursor 终端）"
            )
        elif imported <= 0:
            msg = (
                f"已抓取 {collected} 条但均未入库（可能已被清洗过滤）；"
                f"可检查 tiktok_collector/data/raw 导出或调低清洗阈值"
            )
        else:
            msg = (
                f"浏览器采集完成：抓取 {collected} 条，新增 {imported} 条、"
                f"更新 {result.updated_existing_links} 条对标"
            )
        out.update(
            {
                "total_collected": collected,
                "imported_new_links": imported,
                "updated_existing_links": result.updated_existing_links,
                "message": msg,
            }
        )
    elif mysql_enabled:
        sync_result = sync_collector_database_to_workflow(
            limit=max(1, min(200, int(limit or 80))),
            product_id=product_id,
            strict_product_filter=bool(product_id),
            order_by="hot",
        )
        out.update(
            {
                "synced_count": sync_result.synced_count,
                "imported_new_links": sync_result.imported_new_links,
                "updated_existing_links": sync_result.updated_existing_links,
                "queried_total": sync_result.queried_total,
                "message": (
                    f"MySQL 热点同步：新增 {sync_result.imported_new_links} 条、"
                    f"更新 {sync_result.updated_existing_links} 条"
                    if sync_result.synced_count
                    else "MySQL 暂无新热点，已刷新本地列表"
                ),
            }
        )
    elif mode == "sync":
        out["ok"] = False
        out["message"] = "未配置 TikTok MySQL（TIKTOK_COLLECTOR_MYSQL_URL），无法后台同步"
    else:
        out["message"] = (
            "未配置 MySQL，本地素材未增加；请点设置 → 素材维护 →「浏览器采集」"
            "并在弹出的 Chrome 完成 TikTok 登录"
        )

    items = load_materials()
    out["materials_total"] = len(items)
    out["materials_analyzed"] = sum(1 for i in items if i.get("has_analysis"))
    out["refreshed_at"] = _utc_now()

    save_hotspot_state(
        {
            "last_refresh_at": out["refreshed_at"],
            "last_product_id": product_id,
            "last_mode": mode,
            "last_imported_new": out.get("imported_new_links") or 0,
            "last_updated": out.get("updated_existing_links") or 0,
            "last_message": out.get("message") or "",
        }
    )
    return out
