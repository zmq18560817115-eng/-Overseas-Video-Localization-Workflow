"""多场景批量出片：skill 校验 → 按场景标签生成脚本 → SeedDance → 归档 03_产出库。

用法:
  python scripts/run_batch_scenario_video.py --check-skill
  python scripts/run_batch_scenario_video.py --link-id 23 --scenarios bedroom
  python scripts/run_batch_scenario_video.py --link-id 23
"""
from __future__ import annotations

import argparse
import json
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

MVP_ROOT = Path(__file__).resolve().parents[1]
WORKFLOW_ROOT = MVP_ROOT.parent
ARCHIVE_DIR = WORKFLOW_ROOT / "03_产出库"
OLM_ROOT = WORKFLOW_ROOT / "overseas-loc-mvp"

sys.path.insert(0, str(MVP_ROOT / "scripts"))
sys.path.insert(0, str(MVP_ROOT))

PRODUCT = "便携恒温杯"
BASE_TAGS = {
    "audience_tags": ["0-12月新手爸妈"],
    "selling_tags": ["便携可充电设计", "外出随时加热"],
    "pain_tags": ["传统暖奶器太大不便携"],
    "target_country": "US",
    "language": "en",
    "style": "us_tiktok_spoken",
}

SCENARIOS: dict[str, dict[str, Any]] = {
    "bedroom": {
        "label": "夜间卧室喂奶",
        "scenario_tags": ["夜间卧室喂奶"],
        "audience_tags": ["0-12月新手爸妈", "夜奶家庭"],
    },
    "car": {
        "label": "车内杯架加热",
        "scenario_tags": ["车内杯架加热"],
        "audience_tags": ["0-12月新手爸妈"],
    },
    "travel": {
        "label": "旅途出行",
        "scenario_tags": ["旅途出行", "机场"],
        "audience_tags": ["0-12月新手爸妈"],
    },
    "office": {
        "label": "办公室背奶",
        "scenario_tags": ["办公室背奶"],
        "audience_tags": ["背奶职场妈妈", "0-12月新手爸妈"],
    },
}

SKILL_CONTRACT_FIELDS = (
    "product_sources",
    "asset_manifest",
    "shot_asset_map",
    "scene_continuity",
    "character_continuity",
    "production_fidelity",
    "claim_guardrails",
    "delivery_risks",
)


def run_skill_validation() -> dict[str, Any]:
    proc = subprocess.run(
        [sys.executable, str(MVP_ROOT / "scripts" / "validate_output_standards_skill.py")],
        cwd=str(MVP_ROOT),
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
    )
    if proc.returncode != 0:
        raise RuntimeError(proc.stdout or proc.stderr or "skill validation failed")
    return json.loads(proc.stdout)


def verify_pack_contract(pack: dict[str, Any]) -> list[str]:
    missing = [f for f in SKILL_CONTRACT_FIELDS if f not in pack]
    risks = pack.get("delivery_risks") or {}
    if risks.get("status") == "BLOCKED":
        missing.append(f"delivery_risks:BLOCKED:{risks.get('blockers')}")
    return missing


def _olm_import():
    """Import OLM modules without MVP `app` package shadowing."""
    olm = str(OLM_ROOT)
    mvp = str(MVP_ROOT)
    if mvp in sys.path:
        sys.path.remove(mvp)
    if olm not in sys.path:
        sys.path.insert(0, olm)


def _restore_mvp_import():
    mvp = str(MVP_ROOT)
    if mvp not in sys.path:
        sys.path.insert(0, mvp)


def latest_archive_video(slug: str) -> Path | None:
    _olm_import()
    try:
        from app.production_archive import list_versions

        versions = list_versions(slug)
        if not versions:
            return None
        final = versions[0] / "final-video.mp4"
        return final if final.is_file() else None
    finally:
        _restore_mvp_import()


def patch_archive_manifest(slug: str, scenario_id: str, label: str, pack: dict[str, Any]) -> str:
    _olm_import()
    try:
        from app.production_archive import list_versions

        versions = list_versions(slug)
        if not versions:
            return ""
        dest = versions[0]
        manifest_path = dest / "manifest.json"
        manifest = json.loads(manifest_path.read_text(encoding="utf-8")) if manifest_path.is_file() else {}
        manifest["scenario_id"] = scenario_id
        manifest["scenario_label"] = label
        manifest["note"] = f"batch-scenario:{scenario_id}:{label}"
        manifest["output_standards_version"] = pack.get("output_standards_version", "")
        manifest["character_id"] = (pack.get("character_continuity") or {}).get("character_id", "")
        manifest_path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        return str(dest)
    finally:
        _restore_mvp_import()


def pick_link_id(explicit: int) -> int:
    if explicit:
        return explicit
    from app.data import load_materials

    for item in load_materials():
        if item.get("has_analysis") and item.get("content_line") == PRODUCT:
            return int(item["link_id"])
    for item in load_materials():
        if item.get("has_analysis"):
            return int(item["link_id"])
    raise RuntimeError("无已拆解素材，请先在设置运行结构拆解")


def run_scenario(link_id: int, scenario_id: str, cfg: dict[str, Any]) -> dict[str, Any]:
    from app.script_gen import generate_script
    from app.seedance_bridge import refresh_project_seedance_source, run_all

    slug = f"ref-{link_id:03d}"
    market = {
        **BASE_TAGS,
        "audience_tags": cfg.get("audience_tags") or BASE_TAGS["audience_tags"],
        "scenario_tags": cfg["scenario_tags"],
    }
    print(f"\n{'=' * 60}")
    print(f"  场景: {cfg['label']} ({scenario_id}) · 素材 #{link_id}")
    print(f"{'=' * 60}")

    print("[1/4] 生成脚本（含 skill 七段契约）…")
    gen = generate_script(link_id, product_id=PRODUCT, bridge=True, market=market)
    pack = gen.get("script_pack") or {}
    gaps = verify_pack_contract(pack)
    if gaps:
        raise RuntimeError(f"script-pack 缺少 skill 字段: {gaps}")

    print(f"      slug={slug} · 场景={pack.get('scene_continuity', {}).get('main_scene_zh', '')}")
    char = (pack.get("character_continuity") or {}).get("label", "—")
    print(f"      人物锚定: {char}")

    print("[2/4] 刷新产品/人物垫图 …")
    refresh_project_seedance_source(slug)

    print("[3/4] SeedDance 分镜 + 拼接（force，约 15–40 分钟）…")
    sd = run_all(slug, force=True)
    results = sd.get("results") or []
    ok_shots = [r for r in results if r.get("status") == "ok"]
    assemble = sd.get("assemble") or {}
    if not ok_shots:
        if not results:
            raise RuntimeError("SeedDance 无分镜任务（检查 storyboard.json / script-pack 是否已同步）")
        errors = [r for r in results if r.get("status") == "error"]
        detail = "; ".join(
            f"镜{r.get('number')}: {r.get('message') or 'unknown'}" for r in errors[:3]
        )
        msg = assemble.get("message") or detail or "SeedDance 失败"
        raise RuntimeError(str(msg))
    if not assemble.get("ok"):
        raise RuntimeError(str(assemble.get("message") or "拼接成片失败"))

    print("[4/4] 归档 03_产出库 …")
    archive_path = patch_archive_manifest(slug, scenario_id, cfg["label"], pack)
    video = latest_archive_video(slug)
    if not video:
        raise RuntimeError("归档后未找到 final-video.mp4")

    return {
        "scenario": scenario_id,
        "label": cfg["label"],
        "ok": True,
        "slug": slug,
        "archive": str(video),
        "archive_dir": archive_path,
        "bytes": video.stat().st_size,
        "delivery_risks": pack.get("delivery_risks"),
        "seedance": {
            "ready": sd.get("seedance", {}).get("shots"),
            "assemble": assemble,
        },
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="多场景批量出片测试")
    parser.add_argument("--check-skill", action="store_true", help="仅校验 skill 与素材")
    parser.add_argument("--link-id", type=int, default=0, help="对标素材 ID，默认自动选择")
    parser.add_argument(
        "--scenarios",
        default="",
        help="逗号分隔场景 id：bedroom,car,travel,office；默认全部",
    )
    args = parser.parse_args()

    print("overseas-video-output-standards 预检 …")
    skill = run_skill_validation()
    print(f"  skill: {skill['passed']}/{skill['total']} · usable={skill['usable_for_workflow']}")
    if not skill["usable_for_workflow"]:
        return 1
    if args.check_skill:
        return 0

    keys = [k.strip() for k in args.scenarios.split(",") if k.strip()] if args.scenarios else list(SCENARIOS)
    unknown = [k for k in keys if k not in SCENARIOS]
    if unknown:
        print(f"未知场景: {unknown}，可选: {list(SCENARIOS)}")
        return 1

    link_id = pick_link_id(args.link_id)
    stamp = datetime.now(timezone.utc).strftime("%Y%m%d-%H%M%S")
    report: list[dict[str, Any]] = []

    for key in keys:
        entry: dict[str, Any] = {"scenario": key, "label": SCENARIOS[key]["label"]}
        try:
            entry.update(run_scenario(link_id, key, SCENARIOS[key]))
        except Exception as exc:
            entry["ok"] = False
            entry["error"] = str(exc)
            print(f"  [失败] {exc}")
        report.append(entry)

    report_path = ARCHIVE_DIR / f"batch-scenario-{stamp}.json"
    ARCHIVE_DIR.mkdir(parents=True, exist_ok=True)
    report_path.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    ok_n = sum(1 for r in report if r.get("ok"))
    print(f"\n完成 {ok_n}/{len(report)} · 报告: {report_path}")
    for row in report:
        if row.get("ok"):
            print(f"  OK {row['label']}: {row['archive']}")
        else:
            print(f"  FAIL {row['label']}: {row.get('error')}")
    return 0 if ok_n == len(report) else 1


if __name__ == "__main__":
    raise SystemExit(main())
