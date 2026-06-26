"""模拟使用者走查：素材库 → 脚本生成 → 交付 → SeedDance 空镜 → 成稿库 闭环验证。"""
from __future__ import annotations

import argparse
import json
import socket
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
WORKFLOW_ROOT = Path(__file__).resolve().parents[2]
RUNS_DIR = WORKFLOW_ROOT / "overseas-loc-mvp" / "runs"


def get(path: str) -> dict:
    with urllib.request.urlopen(f"{BASE}{path}", timeout=30) as r:
        return json.load(r)


def post(path: str, body: dict | None = None, *, timeout: int = 120) -> dict:
    data = json.dumps(body or {}).encode("utf-8")
    req = urllib.request.Request(
        f"{BASE}{path}",
        data=data,
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return json.load(r)


def step(name: str, ok: bool, detail: str = "") -> bool:
    mark = "PASS" if ok else "FAIL"
    line = f"[{mark}] {name}"
    print(line.encode("utf-8", errors="replace").decode("utf-8", errors="replace"))
    if detail:
        d = detail.encode("utf-8", errors="replace").decode("utf-8", errors="replace")
        print(f"       {d}")
    return ok


def main() -> int:
    parser = argparse.ArgumentParser(description="8788 工作台端到端走查")
    parser.add_argument(
        "--with-seedance",
        action="store_true",
        help="交付后调用 Ark/fal 生成 AI 空镜（每镜约 2–5 分钟）",
    )
    parser.add_argument("--link-id", type=int, default=0, help="指定素材 link_id，默认自动选择")
    args = parser.parse_args()

    fails = 0

    def record(name: str, ok: bool, detail: str = "") -> None:
        nonlocal fails
        if not step(name, ok, detail):
            fails += 1

    # 0 启动与环境
    try:
        h = get("/api/health")
        sd = h.get("seedance") or {}
        record(
            "0. 服务可用",
            h.get("ok"),
            f"UI v{h.get('ui_version')} · 素材 {h.get('materials')} · 已拆解 {h.get('analyzed')}",
        )
        record(
            "0b. SeedDance 配置",
            sd.get("configured"),
            f"{sd.get('provider', '?')} · {sd.get('text_model', sd.get('label', ''))[:48]}",
        )
        if h.get("analyzed", 0) < 1:
            record("0c. 数据就绪", False, "无已拆解素材，请先在「设置」运行结构拆解")
    except Exception as e:
        record("0. 服务可用", False, str(e))
        return 1

    # 1 素材库
    mats = get("/api/materials?analyzed_only=true")
    items = mats.get("items") or []
    record("1. 素材库（已拆解）", len(items) > 0, f"共 {len(items)} 条")
    if not items:
        return 1

    link_id = args.link_id
    if not link_id:
        link_id = next((i["link_id"] for i in items if not i.get("delivery_ready")), items[0]["link_id"])
        for i in items:
            if not i.get("delivery_ready") and i.get("content_line") == PRODUCT:
                link_id = i["link_id"]
                break

    detail = get(f"/api/materials/{link_id}")
    record("1b. 素材详情", bool(detail.get("analysis")), f"#{link_id} {str(detail.get('title', ''))[:40]}")

    # 2 脚本页预览
    pid = urllib.parse.quote(PRODUCT)
    prev = get(f"/api/materials/{link_id}/preview?product_id={pid}")
    tags = prev.get("delivery_tags") or {}
    record(
        "2. 脚本页标签池",
        len(tags.get("audience") or []) > 0
        and len(tags.get("selling") or []) > 0
        and len(tags.get("pains") or []) > 0,
        f"人群 {len(tags.get('audience') or [])} · 场景 {len(tags.get('scenarios') or [])} · "
        f"卖点 {len(tags.get('selling') or [])} · 痛点 {len(tags.get('pains') or [])}",
    )
    record("2b. 结构参考+产品", bool(prev.get("material") and prev.get("product")), prev.get("brand_product", PRODUCT))

    # 3 生成脚本
    body = {
        "product_id": PRODUCT,
        "bridge": True,
        "target_country": "US",
        "language": "en",
        "style": "us_tiktok_spoken",
        **TAGS,
    }
    try:
        gen = post(f"/api/materials/{link_id}/generate", body, timeout=180)
        pack = gen.get("script_pack") or {}
        meta = gen.get("meta") or {}
        vo = pack.get("voiceover_20s") or ""
        bad_travel = any(x in vo.lower() for x in ("traveling", "out with baby", "next trip"))
        bad_scene = TAGS["scenario_tags"][0] == "夜间卧室喂奶" and bad_travel
        record("3. 生成脚本", bool(pack.get("storyboard")), f"标题 {str(pack.get('title', ''))[:50]}")
        record(
            "3b. 脚本引擎",
            bool(meta.get("provider")),
            f"{meta.get('provider', '?')} / {meta.get('model', '?')}",
        )
        record("3c. 场景一致", not bad_scene, vo[:80] if bad_scene else "口播与卧室场景一致")
        broll_shots = [
            s for s in (pack.get("storyboard") or []) if s.get("footage_type") in ("AI_BROLL", "AI_VIDEO")
        ]
        record("3d. 含 AI 视频镜位", len(broll_shots) > 0, f"可生成 {len(broll_shots)} 镜")
    except urllib.error.HTTPError as e:
        record("3. 生成脚本", False, e.read().decode()[:200])
        return 1

    slug = gen.get("slug") or f"ref-{link_id:03d}"
    sd_cfg = h.get("seedance") or {}
    on_finish = sd_cfg.get("mode") == "script"
    finish_timeout = 900 if on_finish and sd_cfg.get("configured") else 120

    # 4 完成交付（SKIP_SEEDANCE=1 时约数十秒；否则可能含空镜生成）
    try:
        fin = post(f"/api/delivery/{slug}/finish", timeout=finish_timeout)
        record("4. 完成交付", fin.get("ok") is not False, (fin.get("message") or "ok")[:80])
    except TimeoutError:
        prev_chk = get(f"/api/materials/{link_id}/preview?product_id={pid}")
        ok = prev_chk.get("delivery_ready") is True
        record("4. 完成交付", ok, f"请求>{finish_timeout}s 但 delivery_ready={'是' if ok else '否'}")
    except urllib.error.HTTPError as e:
        record("4. 完成交付", False, e.read().decode()[:200])

    prev3 = get(f"/api/materials/{link_id}/preview?product_id={pid}")
    record("4b. delivery_ready", prev3.get("delivery_ready") is True, f"slug={slug}")

    # 5 成稿库
    finished = get("/api/library/finished")
    items_f = finished.get("items") or []
    record("5. 成稿库", any(x.get("slug") == slug for x in items_f), f"成稿共 {len(items_f)} 条")

    # 6 交付 zip（脚本包）
    zip_size = 0
    try:
        req = urllib.request.Request(f"{BASE}/api/delivery/{slug}/zip")
        with urllib.request.urlopen(req, timeout=60) as r:
            zip_size = len(r.read())
        record("6. 下载 zip（脚本包）", zip_size > 500, f"{zip_size} bytes")
    except Exception as e:
        record("6. 下载 zip", False, str(e))

    # 7–9 SeedDance 空镜（模型接入）
    sd_status = get(f"/api/delivery/{urllib.parse.quote(slug)}/seedance")
    record("7. AI 空镜镜位就绪", sd_status.get("available"), f"镜头 {len(sd_status.get('shots') or [])} 个")

    if args.with_seedance:
        if not (h.get("seedance") or {}).get("configured"):
            record("8. 生成 AI 空镜", False, "未配置 ARK_API_KEY / FAL_KEY")
        elif not sd_status.get("shots"):
            record("8. 生成 AI 空镜", False, "无 AI_BROLL 镜头")
        else:
            pending = sum(1 for s in sd_status.get("shots") or [] if not s.get("ready"))
            if pending == 0 and all(s.get("ready") for s in sd_status.get("shots") or []):
                record("8. 生成 AI 空镜", True, "交付阶段已生成，跳过重复调用")
            else:
                print(f"       正在生成 {pending} 个空镜（Ark 约 2–5 分钟/镜）…")
                try:
                    socket.setdefaulttimeout(600)
                    run = post(f"/api/delivery/{slug}/seedance/run", timeout=600)
                    results = run.get("results") or []
                    ok_n = sum(1 for r in results if r.get("status") in ("ok", "skipped"))
                    err_n = sum(1 for r in results if r.get("status") == "error")
                    record("8. 生成 AI 空镜", err_n == 0 and ok_n > 0, f"成功/跳过 {ok_n} · 失败 {err_n}")
                except Exception as e:
                    record("8. 生成 AI 空镜", False, str(e)[:200])
                finally:
                    socket.setdefaulttimeout(30)

        sd_after = get(f"/api/delivery/{urllib.parse.quote(slug)}/seedance")
        ready = [s for s in sd_after.get("shots") or [] if s.get("ready")]
        record("9. 空镜 mp4 就绪", len(ready) > 0, f"{len(ready)}/{len(sd_after.get('shots') or [])} 镜")
        for s in ready:
            mp4 = RUNS_DIR / slug / (s.get("file") or "")
            record(f"9b. 文件 {s.get('file')}", mp4.is_file(), str(mp4) if mp4.is_file() else "缺失")

        try:
            req = urllib.request.Request(f"{BASE}/api/delivery/{slug}/zip")
            with urllib.request.urlopen(req, timeout=60) as r:
                zip2 = len(r.read())
            record("10. zip 含空镜后体积", zip2 >= zip_size, f"{zip_size} → {zip2} bytes")
        except Exception as e:
            record("10. zip 含空镜", False, str(e))
    else:
        print("       （跳过空镜生成；加 --with-seedance 可测 Ark 完整视频产出）")

    print()
    if fails:
        print(f"走查未完全通过（{fails} 项需关注）")
        print()
        print("产出目录:")
        print(f"  脚本包: {RUNS_DIR / slug}")
        print(f"  空镜:   {RUNS_DIR / slug / 'broll'}")
        return 1

    print("走查通过：素材 → 脚本（标签）→ 交付 → " + ("SeedDance 空镜 → " if args.with_seedance else "") + "成稿库")
    print()
    print("产出目录:")
    print(f"  {RUNS_DIR / slug}")
    print(f"  预览空镜: {BASE}/api/delivery/{slug}/files/broll/shot-N.mp4")
    return 0


if __name__ == "__main__":
    sys.exit(main())
