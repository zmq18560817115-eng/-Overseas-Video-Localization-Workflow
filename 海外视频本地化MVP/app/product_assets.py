"""产品实拍/Listing 素材：垫图路径解析与交付项目注入。"""
from __future__ import annotations

import shutil
from pathlib import Path

from paths import PRODUCT_MATERIALS_DIR, WORKFLOW_ROOT

HERO_CANDIDATES = (
    "主图/倒出口参考.png",
    "主图/倒出口参考.jpg",
    "主图/白底主图.png",
    "主图/白底主图.jpg",
    "A+/KV.jpg",
    "副图/主图.jpg",
    "副图/白底八背景.jpg",
    "M端/KV.jpg",
    "M图/KV.jpg",
)


def _pick_clear_hero(root: Path) -> Path | None:
    """优先选高分辨率、产品主体清晰的垫图。"""
    preferred = root / "A+" / "KV.jpg"
    if preferred.is_file() and preferred.stat().st_size >= 400_000:
        return preferred
    for sub in sorted(root.iterdir()):
        if not sub.is_dir():
            continue
        for path in sorted(sub.glob("*.jpg"), key=lambda p: p.stat().st_size, reverse=True):
            if any(k in path.name for k in ("白底", "主图", "KV")) and path.stat().st_size >= 250_000:
                return path
    return _pick_kv_hero(root)

IMAGE_SUFFIXES = {".jpg", ".jpeg", ".png", ".webp"}


def product_listing_dir(product_id: str) -> Path:
    base = PRODUCT_MATERIALS_DIR / product_id
    for name in ("listing-0602-nw", "listing", "assets"):
        path = base / name
        if path.is_dir():
            return path
    return base / "listing-0602-nw"


def _pick_kv_hero(root: Path) -> Path | None:
    kv_files = sorted(root.rglob("KV.jpg"))
    for path in kv_files:
        if path.parent.name.upper().startswith("M"):
            return path
    return kv_files[0] if kv_files else None


def list_product_images(product_id: str) -> list[Path]:
    root = product_listing_dir(product_id)
    if not root.is_dir():
        return []
    return [
        p
        for p in sorted(root.rglob("*"))
        if p.is_file() and p.suffix.lower() in IMAGE_SUFFIXES and p.name != ".DS_Store"
    ]


def get_product_hero_image(product_id: str) -> Path | None:
    root = product_listing_dir(product_id)
    if not root.is_dir():
        return None
    for rel in HERO_CANDIDATES:
        path = root / rel
        if path.is_file():
            return path
    hero = _pick_clear_hero(root)
    if hero:
        return hero
    for folder in ("M端", "M图", "副图", "主图", "A+"):
        sub = root / folder
        if not sub.is_dir():
            continue
        for path in sorted(sub.glob("*.jpg")):
            if path.is_file():
                return path
    images = list_product_images(product_id)
    return images[0] if images else None


def stage_seedance_source_image(project: Path, product_id: str) -> Path | None:
    """将产品主图复制到交付项目 inputs/seedance-source.jpg，供 SeedDance 图生视频。"""
    hero = get_product_hero_image(product_id)
    if not hero:
        return None
    inputs = project / "inputs"
    inputs.mkdir(parents=True, exist_ok=True)
    target = inputs / f"seedance-source{hero.suffix.lower()}"
    if target.exists() and target.stat().st_size == hero.stat().st_size:
        return target
    shutil.copy2(hero, target)
    return target


def import_listing_folder(src: Path, product_id: str, *, dest_name: str = "listing-0602-nw") -> Path:
    """从外部目录导入 Listing 素材到产品资料库。"""
    dest = PRODUCT_MATERIALS_DIR / product_id / dest_name
    if dest.exists():
        shutil.rmtree(dest)
    shutil.copytree(src, dest)
    mirror = WORKFLOW_ROOT / "overseas-loc-mvp" / "knowledge" / "products" / "assets" / product_id / dest_name
    mirror.parent.mkdir(parents=True, exist_ok=True)
    if mirror.exists():
        shutil.rmtree(mirror)
    shutil.copytree(dest, mirror)
    return dest
