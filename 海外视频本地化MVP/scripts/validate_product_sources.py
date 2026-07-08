"""校验产品资料是否存在高风险话术混入可出稿字段、以及白底主图/倒出口参考是否齐全。

用法:
  python scripts/validate_product_sources.py

退出码：发现任何 FAIL 时返回 1，仅 WARN 时返回 0。
"""
from __future__ import annotations

import csv
import sys
from pathlib import Path

MVP_ROOT = Path(__file__).resolve().parent
WORKFLOW_ROOT = MVP_ROOT.parents[1]

if str(MVP_ROOT) not in sys.path:
    sys.path.insert(0, str(MVP_ROOT))

from sync_products import RISK_MARKERS  # noqa: E402

PRODUCT_MATERIALS_CSV = WORKFLOW_ROOT / "01_素材库" / "竞品对标" / "数据表" / "product_materials.csv"
PRODUCT_DIR = WORKFLOW_ROOT / "01_素材库" / "产品资料"

SAFE_FIELDS = ("core_selling_points", "price_range")
REQUIRED_MD_SECTIONS = ("适用人群", "核心卖点", "用户痛点", "使用场景", "禁用词/风险表述", "价格区间")


def _hits(text: str) -> list[str]:
    low = (text or "").lower()
    return [m for m in RISK_MARKERS if m.lower() in low]


def check_csv() -> list[str]:
    problems: list[str] = []
    if not PRODUCT_MATERIALS_CSV.exists():
        problems.append(f"FAIL 缺少 {PRODUCT_MATERIALS_CSV.relative_to(WORKFLOW_ROOT)}，先运行 sync_products.py")
        return problems
    with PRODUCT_MATERIALS_CSV.open(encoding="utf-8-sig", newline="") as f:
        rows = list(csv.DictReader(f))
    if not rows:
        problems.append("FAIL product_materials.csv 为空")
        return problems
    for row in rows:
        pid = row.get("product_id", "?")
        for field in SAFE_FIELDS:
            hits = _hits(row.get(field, ""))
            if hits:
                problems.append(
                    f"FAIL {pid}.{field} 命中风险词 {hits}，应在 internal_notes/forbidden_terms 中，不应出现在可出稿字段"
                )
        if not (row.get("internal_notes") or "").strip():
            problems.append(f"WARN {pid} internal_notes 为空（正常，也可能是尚未跑过风险过滤）")
    return problems


def check_md_layering() -> list[str]:
    problems: list[str] = []
    if not PRODUCT_DIR.is_dir():
        problems.append(f"FAIL 缺少目录 {PRODUCT_DIR.relative_to(WORKFLOW_ROOT)}")
        return problems
    for md in sorted(PRODUCT_DIR.glob("*.md")):
        text = md.read_text(encoding="utf-8")
        missing = [s for s in REQUIRED_MD_SECTIONS if f"## {s}" not in text]
        if missing:
            problems.append(f"WARN {md.name} 缺少分层小节: {missing}")
        for section in ("核心卖点", "价格区间"):
            marker = f"## {section}"
            if marker not in text:
                continue
            start = text.index(marker) + len(marker)
            end = text.find("\n## ", start)
            body = text[start:end if end != -1 else None]
            hits = _hits(body)
            if hits:
                problems.append(f"FAIL {md.name} 的「{section}」小节混入风险话术: {hits}")
    return problems


def check_listing_assets() -> list[str]:
    problems: list[str] = []
    if not PRODUCT_DIR.is_dir():
        return problems
    for product_dir in sorted(p for p in PRODUCT_DIR.iterdir() if p.is_dir()):
        for listing_dir in sorted(p for p in product_dir.iterdir() if p.is_dir()):
            main_dir = listing_dir / "主图"
            white_bg = list(main_dir.glob("白底主图.*")) if main_dir.is_dir() else []
            pour_ref = list(main_dir.glob("倒出口参考.*")) if main_dir.is_dir() else []
            if not white_bg:
                problems.append(f"FAIL {listing_dir.relative_to(WORKFLOW_ROOT)} 缺少 主图/白底主图.*（SeedDance 垫图唯一锚点）")
            if not pour_ref:
                problems.append(f"WARN {listing_dir.relative_to(WORKFLOW_ROOT)} 缺少 主图/倒出口参考.*")
    return problems


def main() -> int:
    all_problems: list[str] = []
    all_problems += check_csv()
    all_problems += check_md_layering()
    all_problems += check_listing_assets()

    if not all_problems:
        print("PASS 产品资料校验通过：无风险话术混入可出稿字段，白底主图齐全。")
        return 0

    fails = [p for p in all_problems if p.startswith("FAIL")]
    warns = [p for p in all_problems if p.startswith("WARN")]
    for p in fails + warns:
        print(p)
    print(f"\n共 {len(fails)} 个 FAIL，{len(warns)} 个 WARN。")
    return 1 if fails else 0


if __name__ == "__main__":
    raise SystemExit(main())
