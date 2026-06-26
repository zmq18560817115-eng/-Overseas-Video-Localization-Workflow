"""演示：按选定标签生成脚本 → 5 镜分镜视频 → ffmpeg 拼接成片 final-video.mp4"""
from __future__ import annotations

import argparse
import json
import subprocess
import sys
import urllib.parse
import urllib.request
from pathlib import Path

BASE = "http://127.0.0.1:8788"
PRODUCT = "便携恒温杯"
DEFAULT_TAGS = {
    "audience_tags": ["0-12月新手爸妈"],
    "scenario_tags": ["夜间卧室喂奶"],
    "selling_tags": ["便携可充电设计", "外出随时加热"],
    "pain_tags": ["传统暖奶器太大不便携"],
}
ROOT = Path(__file__).resolve().parents[2]
RUNS = ROOT / "overseas-loc-mvp" / "runs"


def get(path: str) -> dict:
    with urllib.request.urlopen(f"{BASE}{path}", timeout=60) as r:
        return json.load(r)


def post(path: str, body: dict | None = None, *, timeout: int = 3600) -> dict:
    req = urllib.request.Request(
        f"{BASE}{path}",
        data=json.dumps(body or {}).encode("utf-8"),
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return json.load(r)


def main() -> int:
    parser = argparse.ArgumentParser(description="分镜拼接长视频演示")
    parser.add_argument("--link-id", type=int, default=0, help="指定素材 ID，默认自动选未交付")
    args = parser.parse_args()

    print("=" * 60)
    print("  长视频演示：5 镜分镜 → 拼接成片")
    print("=" * 60)
    print(f"  产品: {PRODUCT}")
    print(f"  场景: {', '.join(DEFAULT_TAGS['scenario_tags'])}")
    print("=" * 60)

    try:
        h = get("/api/health")
    except Exception as e:
        print(f"\n[失败] 8788 未启动: {e}\n请双击「启动工作台.cmd」")
        return 1

    if not (h.get("seedance") or {}).get("configured"):
        print("[失败] 未配置 ARK_API_KEY")
        return 1

    mats = get("/api/materials?analyzed_only=true").get("items") or []
    if not mats:
        print("[失败] 素材库为空，请先在设置运行结构拆解")
        return 1

    link_id = args.link_id
    if not link_id:
        for i in mats:
            if not i.get("delivery_ready") and i.get("content_line") == PRODUCT:
                link_id = i["link_id"]
                break
        if not link_id:
            link_id = next((i["link_id"] for i in mats if not i.get("delivery_ready")), mats[0]["link_id"])

    print(f"\n[1/5] 素材 #{link_id} · 生成脚本 …")
    body = {
        "product_id": PRODUCT,
        "bridge": True,
        "target_country": "US",
        "language": "en",
        "style": "us_tiktok_spoken",
        **DEFAULT_TAGS,
    }
    gen = post(f"/api/materials/{link_id}/generate", body, timeout=180)
    slug = gen.get("slug") or f"ref-{link_id:03d}"
    pack = gen.get("script_pack") or {}
    n_ai = len(pack.get("storyboard") or [])
    print(f"      {slug} · {str(pack.get('title', ''))[:50]} · {n_ai} 镜")

    print(f"\n[2/5] 完成交付（生成 5 镜 + 拼接，约 15–30 分钟）…")
    fin = post(f"/api/delivery/{slug}/finish", timeout=3600)
    print(f"      {fin.get('message', 'ok')}")

    sd = get(f"/api/delivery/{urllib.parse.quote(slug)}/seedance")
    ready_n = sum(1 for s in sd.get("shots") or [] if s.get("ready"))
    total_n = len(sd.get("shots") or [])
    print(f"\n[3/5] 分镜 mp4: {ready_n}/{total_n}")

    if ready_n < total_n:
        print("      补生成剩余分镜 …")
        post(f"/api/delivery/{slug}/seedance/run", timeout=3600)
        sd = get(f"/api/delivery/{urllib.parse.quote(slug)}/seedance")
        ready_n = sum(1 for s in sd.get("shots") or [] if s.get("ready"))
        print(f"      现有 {ready_n}/{total_n} 镜")

    fv = sd.get("final_video") or {}
    if not fv.get("ready"):
        print(f"\n[4/5] 拼接成片 …")
        asm = post(f"/api/delivery/{slug}/assemble", timeout=600)
        a = asm.get("assemble") or {}
        print(f"      {a.get('message', asm)}")
        sd = get(f"/api/delivery/{urllib.parse.quote(slug)}/seedance")
        fv = sd.get("final_video") or {}
    else:
        print(f"\n[4/5] 成片已在交付阶段生成")

    if not fv.get("ready"):
        print("[失败] 未生成 final-video.mp4（需至少 5 镜 mp4，见 .env AI_VIDEO_CONCAT_MIN_SHOTS）")
        return 1

    final_path = RUNS / slug / "broll" / "final-video.mp4"
    final_url = f"{BASE}/api/delivery/{slug}/files/broll/final-video.mp4"
    print(f"\n[5/5] 长视频就绪")
    print("-" * 60)
    print(f"  浏览器预览: {final_url}")
    print(f"  本地文件:   {final_path}")
    print(f"  大小:       {fv.get('bytes', 0) // 1024} KB · 含 {ready_n} 镜")
    print(f"  下载 zip:   {BASE}/api/delivery/{slug}/zip")
    print("-" * 60)

    if final_path.is_file():
        try:
            subprocess.Popen(["cmd", "/c", "start", "", str(final_path)], shell=False)
        except Exception:
            pass
    return 0


if __name__ == "__main__":
    sys.exit(main())
