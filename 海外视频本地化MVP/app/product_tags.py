"""从产品资料解析可下发的目标人群 / 场景 / 卖点 / 痛点标签。"""

from __future__ import annotations

import re
from pathlib import Path
from typing import Any


def chinese_lines(text: str) -> str:
    """提取含中文的段落，用于界面与脚本策划展示。"""
    parts = re.split(r"[；;、\n，,]", text or "")
    zh = [p.strip() for p in parts if p.strip() and re.search(r"[\u4e00-\u9fff]", p)]
    return "；".join(zh) if zh else (text or "").strip()


def split_tags(text: str, *, max_items: int = 12) -> list[str]:
    if not text:
        return []
    parts = re.split(r"[；;、\n，,]", text)
    out: list[str] = []
    for part in parts:
        tag = part.strip()
        if not tag or len(tag) < 2:
            continue
        if not re.search(r"[\u4e00-\u9fff]", tag):
            continue
        if tag not in out:
            out.append(tag)
        if len(out) >= max_items:
            break
    return out


def _knowledge_md_path(product_id: str) -> Path | None:
    if not product_id:
        return None
    root = Path(__file__).resolve().parents[2] / "overseas-loc-mvp" / "knowledge" / "products"
    path = root / f"{product_id}.md"
    return path if path.is_file() else None


def _parse_knowledge_md(path: Path) -> dict[str, str]:
    sections: dict[str, str] = {}
    current = ""
    buf: list[str] = []
    for line in path.read_text(encoding="utf-8").splitlines():
        m = re.match(r"^#{1,3}\s+(.+)$", line.strip())
        if m:
            if current and buf:
                sections[current] = "\n".join(buf).strip()
            current = m.group(1).strip()
            buf = []
        else:
            buf.append(line)
    if current and buf:
        sections[current] = "\n".join(buf).strip()

    field_map = [
        ("适用人群", "target_audience"),
        ("核心卖点", "core_selling_points"),
        ("用户痛点", "pain_points"),
        ("使用场景", "usage_scenarios"),
        ("竞品", "competitor_ref"),
    ]
    out: dict[str, str] = {}
    for title, content in sections.items():
        for key, field in field_map:
            if key in title and content:
                chunk = re.sub(r"\s+", " ", content.replace("；", "；").strip())
                out[field] = chunk
    return out


def enrich_product_from_knowledge(product: dict[str, str] | None) -> dict[str, str]:
    """CSV 字段为空时，从公司 knowledge/products 素材库补全。"""
    if not product:
        return {}
    enriched = dict(product)
    path = Path(str(enriched.get("source_path") or ""))
    if not path.is_file():
        path = _knowledge_md_path(str(enriched.get("product_id") or ""))
    if not path or not path.is_file():
        return enriched
    try:
        row = _parse_knowledge_md(path)
        for key in (
            "target_audience",
            "core_selling_points",
            "pain_points",
            "usage_scenarios",
            "competitor_ref",
        ):
            if not str(enriched.get(key) or "").strip() and row.get(key):
                enriched[key] = row[key]
    except OSError:
        pass
    return enriched


PRODUCT_TAG_PRESETS: dict[str, dict[str, list[str]]] = {
    "便携恒温杯": {
        "audience": [
            "0-12月新手爸妈",
            "夜奶/外出行程家庭",
            "混合喂养与瓶喂妈妈",
            "经常带娃出门、坐飞机、车内喂奶人群",
        ],
        "scenarios": [
            "夜间卧室喂奶",
            "车内杯架加热",
            "机场/旅途出行",
            "公园遛娃",
            "办公室背奶妈妈",
            "餐厅/商场临时冲奶",
        ],
        "selling": [
            "便携可充电设计，外出随时加热",
            "多档温控，奶液加热更均匀",
            "USB-C 充电，妈咪包/杯架都能放",
            "保温锁温，减少反复加热",
            "清洗简单，配件少",
        ],
        "pains": [
            "外出没热水、找微波炉麻烦",
            "加热太慢宝宝哭闹",
            "温度忽高忽低",
            "传统暖奶器太大不便携",
            "夜喂等待久、手忙脚乱",
            "飞机上/车内难加热",
        ],
    },
    "吸奶器": {
        "audience": [
            "0-6月新手妈妈",
            "背奶职场妈妈",
            "夜间吸奶人群",
            "混合喂养家庭",
        ],
        "scenarios": [
            "夜间吸奶",
            "背奶通勤",
            "居家哺乳角",
            "办公室隐蔽吸奶",
            "乳头皲裂恢复期",
        ],
        "selling": [
            "活塞泵技术，吸放节奏更接近婴儿吮吸",
            "可调吸力档位",
            "多种护罩尺寸",
            "可充电电池",
            "易拆洗结构",
            "夜奶场景下电机相对安静",
            "便携设计适合背奶",
        ],
        "pains": [
            "吸不出来/吸不干净",
            "疼痛导致放弃母乳",
            "吸力不适",
            "护罩尺寸不合",
            "清洗繁琐",
            "夜间噪音打扰",
            "外出不便",
        ],
    },
}


def product_tag_presets(product_id: str) -> dict[str, list[str]]:
    return {
        key: list(vals)
        for key, vals in PRODUCT_TAG_PRESETS.get(str(product_id or "").strip(), {}).items()
    }


def _merge_unique_tags(*groups: list[str]) -> list[str]:
    out: list[str] = []
    for group in groups:
        for raw in group:
            tag = str(raw or "").strip()
            if tag and tag not in out:
                out.append(tag)
    return out


def product_delivery_tags(product: dict[str, str] | None) -> dict[str, list[str]]:
    product = enrich_product_from_knowledge(product)
    if not product:
        return {"audience": [], "scenarios": [], "selling": [], "pains": []}
    pid = str(product.get("product_id") or "").strip()
    presets = product_tag_presets(pid)
    parsed = {
        "audience": split_tags(product.get("target_audience", "")),
        "scenarios": split_tags(product.get("usage_scenarios", "")),
        "selling": split_tags(product.get("core_selling_points", ""), max_items=12),
        "pains": split_tags(product.get("pain_points", ""), max_items=10),
    }
    return {
        "audience": _merge_unique_tags(presets.get("audience", []), parsed["audience"]),
        "scenarios": _merge_unique_tags(presets.get("scenarios", []), parsed["scenarios"]),
        "selling": _merge_unique_tags(presets.get("selling", []), parsed["selling"]),
        "pains": _merge_unique_tags(presets.get("pains", []), parsed["pains"]),
    }


def validate_delivery_selection(market: dict[str, Any]) -> dict[str, list[str]]:
    """生成脚本必须基于用户在脚本页勾选的标签，禁止空选或静默回填默认。"""
    labels = {
        "audience_tags": "目标人群",
        "scenario_tags": "投放场景",
        "selling_tags": "核心卖点",
        "pain_tags": "用户痛点",
    }
    out: dict[str, list[str]] = {}
    for key, label in labels.items():
        tags = [str(t).strip() for t in (market.get(key) or []) if str(t).strip()]
        if not tags:
            raise ValueError(f"请先在脚本页为「{label}」选择至少一个标签")
        out[key] = tags
    return out


def normalize_selected_tags(
    tags: dict[str, list[str]],
    *,
    audience: list[str] | None = None,
    scenarios: list[str] | None = None,
    selling: list[str] | None = None,
    pains: list[str] | None = None,
) -> dict[str, list[str]]:
    pool_a = tags.get("audience") or []
    pool_s = tags.get("scenarios") or []
    pool_sel = tags.get("selling") or []
    pool_p = tags.get("pains") or []
    picked_a = [t for t in (audience or []) if t in pool_a]
    picked_s = [t for t in (scenarios or []) if t in pool_s]
    picked_sel = [t for t in (selling or []) if t in pool_sel]
    picked_p = [t for t in (pains or []) if t in pool_p]
    if not picked_a and pool_a:
        picked_a = [pool_a[0]]
    if not picked_s and pool_s:
        picked_s = [pool_s[0]]
    if not picked_sel and pool_sel:
        picked_sel = [pool_sel[0]]
    if not picked_p and pool_p:
        picked_p = [pool_p[0]]
    return {
        "audience": picked_a,
        "scenarios": picked_s,
        "selling": picked_sel,
        "pains": picked_p,
    }
