"""对标素材库：同步热点、品类收窄、去重限额 — 供首页一键维护。"""
from __future__ import annotations

import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from paths import MVP_ROOT

from .data import load_materials
from .hotspot_refresh import refresh_hotspot_videos
from .material_scope import trim_material_library_to_product

SCRIPTS_DIR = MVP_ROOT / "scripts"
if str(SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_DIR))

from prune_materials import _env_bool, _env_int, prune_materials  # noqa: E402

STATE_PATH = MVP_ROOT / "data" / "material_maintenance.json"


def _utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def load_maintenance_state() -> dict[str, Any]:
    if not STATE_PATH.exists():
        return {}
    try:
        return json.loads(STATE_PATH.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return {}


def save_maintenance_state(state: dict[str, Any]) -> None:
    STATE_PATH.parent.mkdir(parents=True, exist_ok=True)
    STATE_PATH.write_text(json.dumps(state, ensure_ascii=False, indent=2), encoding="utf-8")


def maintenance_status_payload() -> dict[str, Any]:
    state = load_maintenance_state()
    items = load_materials()
    analyzed = sum(1 for i in items if i.get("has_analysis"))
    return {
        "last_run_at": state.get("last_run_at"),
        "last_product_id": state.get("last_product_id") or "",
        "last_message": state.get("last_message") or "",
        "last_trim_removed": int(state.get("last_trim_removed") or 0),
        "last_prune_removed": int(state.get("last_prune_removed") or 0),
        "materials_total": len(items),
        "materials_analyzed": analyzed,
        "max_total": _env_int("MATERIAL_MAX_TOTAL", 80),
    }


def run_material_maintenance(
    *,
    product_id: str = "",
    sync: bool = True,
    trim: bool = True,
    prune: bool = True,
    dry_run: bool = False,
) -> dict[str, Any]:
    product_id = (product_id or "").strip()
    report: dict[str, Any] = {
        "ok": True,
        "product_id": product_id,
        "dry_run": dry_run,
        "steps": [],
        "message": "",
    }

    if sync:
        sync_out = refresh_hotspot_videos(product_id=product_id, mode="auto")
        report["sync"] = sync_out
        report["steps"].append("sync")

    if trim and product_id:
        trim_out = trim_material_library_to_product(product_id, dry_run=dry_run)
        report["trim"] = trim_out
        report["steps"].append("trim")

    if prune:
        prune_out = prune_materials(
            max_total=_env_int("MATERIAL_MAX_TOTAL", 80),
            max_candidates=_env_int("DISCOVERY_CANDIDATE_MAX", 150),
            keep_analyzed=_env_bool("MATERIAL_KEEP_ANALYZED", True),
            dry_run=dry_run,
        )
        report["prune"] = prune_out
        report["steps"].append("prune")

    items = load_materials()
    report["materials_total"] = len(items)
    report["materials_analyzed"] = sum(1 for i in items if i.get("has_analysis"))
    report["refreshed_at"] = _utc_now()

    trim_n = int((report.get("trim") or {}).get("removed") or 0)
    prune_n = int((report.get("prune") or {}).get("materials_removed") or 0)
    sync_new = int((report.get("sync") or {}).get("imported_new_links") or 0)
    parts = []
    if sync_new:
        parts.append(f"新增 {sync_new} 条热点")
    if trim_n:
        parts.append(f"移除非品类 {trim_n} 条")
    if prune_n:
        parts.append(f"整理删除 {prune_n} 条")
    if not parts:
        parts.append("素材库已是最新，无需清理")
    report["message"] = " · ".join(parts)

    if not dry_run:
        save_maintenance_state(
            {
                "last_run_at": report["refreshed_at"],
                "last_product_id": product_id,
                "last_message": report["message"],
                "last_trim_removed": trim_n,
                "last_prune_removed": prune_n,
                "last_sync_new": sync_new,
            }
        )
    return report
