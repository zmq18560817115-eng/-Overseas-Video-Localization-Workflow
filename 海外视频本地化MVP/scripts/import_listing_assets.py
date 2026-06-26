"""导入桌面 Listing 素材到产品资料库。"""
from __future__ import annotations

import sys
from pathlib import Path

MVP_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(MVP_ROOT / "scripts"))
sys.path.insert(0, str(MVP_ROOT))

from app.product_assets import get_product_hero_image, import_listing_folder, list_product_images  # noqa: E402


def _find_desktop_folder() -> Path:
    desktop = Path.home() / "Desktop"
    for path in desktop.iterdir():
        if path.is_dir() and path.name.startswith("0602") and "listing" in path.name.lower():
            return path
    raise FileNotFoundError("未在桌面找到「0602 nw恒温杯listing 输出」文件夹")


def main() -> int:
    src = _find_desktop_folder()
    product_id = "便携恒温杯"
    dest = import_listing_folder(src, product_id)
    hero = get_product_hero_image(product_id)
    images = list_product_images(product_id)
    print(f"OK 已导入 {len(images)} 张图片 → {dest}")
    print(f"垫图主图: {hero}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
