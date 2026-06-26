"""竞品视频封面：下载到本地并通过工作台 API 提供（TikTok CDN 外链会过期/403）。"""
from __future__ import annotations

import csv
from pathlib import Path
from typing import Any

import httpx

from paths import THUMBNAILS_DIR, VIDEOS_META_CSV

_FETCH_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
    ),
    "Referer": "https://www.tiktok.com/",
}


def thumbnail_cache_path(link_id: str | int) -> Path:
    THUMBNAILS_DIR.mkdir(parents=True, exist_ok=True)
    return THUMBNAILS_DIR / f"{int(link_id)}.jpg"


def thumbnail_api_url(link_id: str | int) -> str:
    return f"/api/materials/{int(link_id)}/thumbnail"


def _read_meta_row(link_id: str | int) -> dict[str, str]:
    if not VIDEOS_META_CSV.is_file():
        return {}
    with VIDEOS_META_CSV.open(encoding="utf-8-sig", newline="") as handle:
        for row in csv.DictReader(handle):
            if row.get("link_id") == str(link_id):
                return row
    return {}


def has_thumbnail_source(link_id: str | int) -> bool:
    if thumbnail_cache_path(link_id).is_file():
        return True
    meta = _read_meta_row(link_id)
    return bool(meta.get("thumbnail_url") or meta.get("url"))


def public_thumbnail_url(link_id: str | int) -> str:
    if has_thumbnail_source(link_id):
        return thumbnail_api_url(link_id)
    return ""


def _fetch_oembed_thumbnail(video_url: str) -> str | None:
    with httpx.Client(headers=_FETCH_HEADERS, follow_redirects=True, timeout=25) as client:
        resp = client.get("https://www.tiktok.com/oembed", params={"url": video_url})
        resp.raise_for_status()
        data = resp.json()
    thumb = str(data.get("thumbnail_url") or "").strip()
    return thumb or None


def _download_image(url: str, dest: Path) -> bool:
    with httpx.Client(headers=_FETCH_HEADERS, follow_redirects=True, timeout=30) as client:
        resp = client.get(url)
        if resp.status_code != 200:
            return False
        content = resp.content
        if len(content) < 500:
            return False
        dest.write_bytes(content)
        return True


def ensure_thumbnail_cached(link_id: str | int, *, force: bool = False) -> Path | None:
    """返回本地封面路径；必要时从 CSV 外链或 oEmbed 刷新下载。"""
    cache = thumbnail_cache_path(link_id)
    if not force and cache.is_file() and cache.stat().st_size > 500:
        return cache

    meta = _read_meta_row(link_id)
    remote = str(meta.get("thumbnail_url") or "").strip()
    video_url = str(meta.get("url") or "").strip()

    if remote and _download_image(remote, cache):
        return cache

    if video_url:
        try:
            fresh = _fetch_oembed_thumbnail(video_url)
        except httpx.HTTPError:
            fresh = None
        if fresh and _download_image(fresh, cache):
            return cache

    return cache if cache.is_file() and cache.stat().st_size > 500 else None


def cache_all_thumbnails(*, force: bool = False) -> dict[str, Any]:
    if not VIDEOS_META_CSV.is_file():
        return {"ok": False, "error": "videos_meta.csv missing", "cached": 0, "failed": 0}
    ids = []
    with VIDEOS_META_CSV.open(encoding="utf-8-sig", newline="") as handle:
        for row in csv.DictReader(handle):
            lid = row.get("link_id")
            if lid:
                ids.append(lid)
    cached = 0
    failed = 0
    for lid in ids:
        if ensure_thumbnail_cached(lid, force=force):
            cached += 1
        else:
            failed += 1
    return {"ok": failed == 0, "total": len(ids), "cached": cached, "failed": failed}
