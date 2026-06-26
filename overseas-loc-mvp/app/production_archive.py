"""每次成片成功后，将视频与关键元数据归档到工作区 03_产出库（按时间版本，不覆盖历史）。"""
from __future__ import annotations

import csv
import hashlib
import json
import shutil
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

WORKFLOW_ROOT = Path(__file__).resolve().parents[2]
PRODUCTION_ARCHIVE_DIR = WORKFLOW_ROOT / "03_产出库"
ARCHIVE_INDEX_CSV = PRODUCTION_ARCHIVE_DIR / "产出索引.csv"

ARCHIVE_INDEX_FIELDS = [
    "archived_at",
    "slug",
    "version_dir",
    "final_video",
    "shots",
    "bytes",
    "note",
    "source_runs",
]


def _utc_stamp() -> str:
    return datetime.now(timezone.utc).strftime("%Y%m%d-%H%M%S")


def _read_json(path: Path) -> dict[str, Any]:
    if not path.is_file():
        return {}
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return {}


def _prompt_fingerprint(project: Path) -> str:
    pack = _read_json(project / "script-pack.json")
    story = _read_json(project / "storyboard.json")
    blob = json.dumps(
        {"pack": pack.get("storyboard"), "story": story.get("shots")},
        ensure_ascii=False,
        sort_keys=True,
    )
    return hashlib.sha256(blob.encode("utf-8")).hexdigest()[:8]


def archive_production(
    project: Path,
    slug: str,
    *,
    note: str = "",
    assemble_meta: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """复制当前 runs 项目中的成片/分镜到 03_产出库/{slug}/{timestamp}/。"""
    broll = project / "broll"
    final = broll / "final-video.mp4"
    if not final.is_file():
        return {"ok": False, "message": "无 final-video.mp4，跳过归档", "path": None}

    version = _utc_stamp()
    dest = PRODUCTION_ARCHIVE_DIR / slug / version
    shots_dir = dest / "shots"
    meta_dir = dest / "meta"
    shots_dir.mkdir(parents=True, exist_ok=True)
    meta_dir.mkdir(parents=True, exist_ok=True)

    shot_files: list[str] = []
    for mp4 in sorted(broll.glob("shot-*.mp4")):
        target = shots_dir / mp4.name
        shutil.copy2(mp4, target)
        shot_files.append(mp4.name)

    shutil.copy2(final, dest / "final-video.mp4")

    for rel in (
        "script-pack.json",
        "storyboard.json",
        "storyboard-cn.md",
        "localization-brief.yaml",
        "subtitles.srt",
    ):
        src = project / rel
        if src.is_file():
            shutil.copy2(src, meta_dir / rel)

    inputs = project / "inputs"
    if inputs.is_dir():
        for img in inputs.glob("seedance-source.*"):
            shutil.copy2(img, meta_dir / img.name)

    for meta_name in ("final-video-meta.json",):
        src = broll / meta_name
        if src.is_file():
            shutil.copy2(src, meta_dir / meta_name)

    manifest = {
        "slug": slug,
        "version": version,
        "archived_at": datetime.now(timezone.utc).isoformat(),
        "note": note,
        "prompt_fingerprint": _prompt_fingerprint(project),
        "shots": shot_files,
        "final_video": "final-video.mp4",
        "bytes": final.stat().st_size,
        "source_runs": str(project),
        "assemble": assemble_meta or {},
    }
    (dest / "manifest.json").write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )

    _append_index(manifest, dest)
    return {
        "ok": True,
        "message": f"已归档到 03_产出库/{slug}/{version}",
        "path": str(dest),
        "version": version,
        "manifest": manifest,
    }


def _append_index(manifest: dict[str, Any], dest: Path) -> None:
    PRODUCTION_ARCHIVE_DIR.mkdir(parents=True, exist_ok=True)
    row = {
        "archived_at": manifest.get("archived_at", ""),
        "slug": manifest.get("slug", ""),
        "version_dir": dest.relative_to(PRODUCTION_ARCHIVE_DIR).as_posix(),
        "final_video": str(dest / "final-video.mp4"),
        "shots": ",".join(manifest.get("shots") or []),
        "bytes": str(manifest.get("bytes") or 0),
        "note": manifest.get("note") or "",
        "source_runs": manifest.get("source_runs") or "",
    }
    write_header = not ARCHIVE_INDEX_CSV.is_file()
    with ARCHIVE_INDEX_CSV.open("a", encoding="utf-8-sig", newline="") as fh:
        writer = csv.DictWriter(fh, fieldnames=ARCHIVE_INDEX_FIELDS)
        if write_header:
            writer.writeheader()
        writer.writerow(row)


def list_versions(slug: str) -> list[Path]:
    base = PRODUCTION_ARCHIVE_DIR / slug
    if not base.is_dir():
        return []
    return sorted([p for p in base.iterdir() if p.is_dir()], reverse=True)
