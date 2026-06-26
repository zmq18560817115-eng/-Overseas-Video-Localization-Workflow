"""清除旧分镜并强制使用最新产品垫图，供用法修正后重跑测试。"""
from __future__ import annotations

import sys
from pathlib import Path

MVP_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(MVP_ROOT / "scripts"))
sys.path.insert(0, str(MVP_ROOT))

from app.product_assets import get_product_hero_image, stage_seedance_source_image  # noqa: E402

RUNS = MVP_ROOT.parent / "overseas-loc-mvp" / "runs"
SLUG = "ref-001"


def main() -> int:
    project = RUNS / SLUG
    broll = project / "broll"
    if broll.is_dir():
        for p in broll.glob("*.mp4"):
            p.unlink()
            print(f"removed {p.name}")
    staged_old = project / "inputs" / "seedance-source.jpg"
    if staged_old.exists():
        staged_old.unlink()
    hero = get_product_hero_image("便携恒温杯")
    staged = stage_seedance_source_image(project, "便携恒温杯")
    print(f"hero: {hero}")
    print(f"staged: {staged} ({staged.stat().st_size if staged else 0} bytes)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
