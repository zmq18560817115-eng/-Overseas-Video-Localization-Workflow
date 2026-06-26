"""一键演示：素材 → 脚本(5镜) → 交付 → Ark 分镜短视频，并打印预览路径。"""
from __future__ import annotations

import json
import subprocess
import sys
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path

BASE = "http://127.0.0.1:8788"
PRODUCT = "便携恒温杯"
TAGS = {
    "audience_tags": ["0-12月新手爸妈"],
    "scenario_tags": ["夜间卧室喂奶"],
    "selling_tags": ["便携可充电设计", "外出随时加热"],
    "pain_tags": ["传统暖奶器太大不便携"],
}
ROOT = Path(__file__).resolve().parents[2]
RUNS = ROOT / "overseas-loc-mvp" / "runs"


def get(path: str) -> dict:
    with urllib.request.urlopen(f"{BASE}{path}", timeout=30) as r:
        return json.load(r)


def post(path: str, body: dict | None = None, *, timeout: int = 900) -> dict:
    req = urllib.request.Request(
        f"{BASE}{path}",
        data=json.dumps(body or {}).encode("utf-8"),
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return json.load(r)


def main() -> int:
    print("=" * 60)
    print("  流程演示：脚本分镜 → Ark 短视频")
    print("=" * 60)

    try:
        h = get("/api/health")
    except Exception as e:
        print(f"\n[失败] 8788 未启动: {e}")
        print("请先双击「启动工作台.cmd」")
        return 1

    sd = h.get("seedance") or {}
    print(f"\n服务 OK · UI v{h.get('ui_version')} · 素材 {h.get('materials')} · 模式 {sd.get('mode')}")
    if not sd.get("configured"):
        print("[失败] 未配置 ARK_API_KEY")
        return 1

    mats = get("/api/materials?analyzed_only=true").get("items") or []
    if not mats:
        print("[失败] 无已拆解素材，请在设置页运行「结构拆解」")
        return 1

    link_id = None
    for i in mats:
        if not i.get("delivery_ready") and i.get("content_line") == PRODUCT:
            link_id = i["link_id"]
            break
    if not link_id:
        link_id = next((i["link_id"] for i in mats if not i.get("delivery_ready")), mats[0]["link_id"])

    print(f"\n[1/4] 选用素材 #{link_id} …")
    pid = urllib.parse.quote(PRODUCT)
    body = {
        "product_id": PRODUCT,
        "bridge": True,
        "target_country": "US",
        "language": "en",
        "style": "us_tiktok_spoken",
        **TAGS,
    }
    gen = post(f"/api/materials/{link_id}/generate", body, timeout=180)
    pack = gen.get("script_pack") or {}
    slug = gen.get("slug") or f"ref-{link_id:03d}"
    ai_shots = [s for s in pack.get("storyboard") or [] if s.get("footage_type") == "AI_VIDEO"]
    print(f"      脚本 {slug} · 标题 {str(pack.get('title', ''))[:48]}")
    print(f"      AI 分镜 {len(ai_shots)} 镜 · 引擎 {gen.get('meta', {}).get('provider', '?')}")

    print(f"\n[2/4] 完成交付（含 Ark 分镜视频，约 3–6 分钟）…")
    fin = post(f"/api/delivery/{slug}/finish", timeout=900)
    print(f"      {fin.get('message', 'ok')}")

    print(f"\n[3/4] 检查 mp4 …")
    sd_after = get(f"/api/delivery/{urllib.parse.quote(slug)}/seedance")
    ready = [s for s in sd_after.get("shots") or [] if s.get("ready")]
    if not ready:
        print("      交付未产出 mp4，尝试手动生成 …")
        run = post(f"/api/delivery/{slug}/seedance/run", timeout=900)
        ready = [s for s in (run.get("seedance") or {}).get("shots") or [] if s.get("ready")]

    if not ready:
        print("[失败] 未生成任何分镜视频，请检查 Ark 余额/密钥")
        return 1

    print(f"\n[4/4] 演示产出（共 {len(ready)} 镜）")
    print("-" * 60)
    for s in ready:
        mp4 = RUNS / slug / (s.get("file") or "").replace("/", "\\")
        url = f"{BASE}/api/delivery/{slug}/files/{s.get('file')}"
        print(f"  镜 {s.get('number')} · {s.get('role', s.get('timing', ''))}")
        print(f"    浏览器: {url}")
        print(f"    本地:   {mp4}")
        if mp4.is_file():
            try:
                subprocess.Popen(["cmd", "/c", "start", "", str(mp4)], shell=False)
            except Exception:
                pass
    print("-" * 60)
    print(f"\n成稿 zip: {BASE}/api/delivery/{slug}/zip")
    print(f"工作台:   {BASE}  → 成稿库 → {slug}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
