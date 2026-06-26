"""检查 runs 下成片与分镜 mp4 是否存在、大小、文件头是否有效。"""
from __future__ import annotations

import json
import sys
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
RUNS = ROOT / "runs"
OUTPUT = ROOT.parent / "03_产出库"


def check_mp4(path: Path) -> dict:
    info: dict = {"path": str(path), "exists": path.is_file(), "bytes": 0, "ok": False, "note": ""}
    if not path.is_file():
        info["note"] = "missing"
        return info
    size = path.stat().st_size
    info["bytes"] = size
    info["mb"] = round(size / 1024 / 1024, 2)
    info["mtime"] = datetime.fromtimestamp(path.stat().st_mtime).isoformat(timespec="seconds")
    if size < 100_000:
        info["note"] = "too small"
        return info
    with open(path, "rb") as fh:
        head = fh.read(12)
    if len(head) >= 8 and head[4:8] == b"ftyp":
        info["ok"] = True
        info["note"] = "valid mp4"
    else:
        info["note"] = "invalid mp4 header"
    return info


def probe_duration(path: Path) -> float | None:
    try:
        import imageio_ffmpeg
        import subprocess

        ff = imageio_ffmpeg.get_ffmpeg_exe()
        cmd = [
            ff,
            "-i",
            str(path),
            "-f",
            "null",
            "-",
        ]
        proc = subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8", errors="replace")
        text = proc.stderr or ""
        for line in text.splitlines():
            if "Duration:" in line:
                part = line.split("Duration:", 1)[1].split(",")[0].strip()
                h, m, s = part.split(":")
                return round(int(h) * 3600 + int(m) * 60 + float(s), 2)
    except Exception:
        return None
    return None


def main() -> int:
    slugs = sorted(p.name for p in RUNS.glob("ref-*/broll/final-video.mp4"))
    if len(sys.argv) > 1:
        slugs = [s if s.startswith("ref-") else f"ref-{int(s):03d}" for s in sys.argv[1:]]

    report: dict = {
        "checked_at": datetime.now().isoformat(timespec="seconds"),
        "projects": [],
        "output_copies": [],
    }

    for slug in slugs:
        broll = RUNS / slug / "broll"
        proj = {"slug": slug, "num": int(slug.split("-")[1]), "final": None, "shots": [], "issues": []}
        final_path = broll / "final-video.mp4"
        final = check_mp4(final_path)
        if final["ok"]:
            final["duration_s"] = probe_duration(final_path)
        proj["final"] = final
        if not final["ok"]:
            proj["issues"].append(f"final: {final['note']}")

        for n in range(1, 6):
            shot_path = broll / f"shot-{n}.mp4"
            shot = check_mp4(shot_path)
            meta_path = broll / f"shot-{n}-seedance-meta.json"
            if meta_path.is_file():
                try:
                    shot["meta_status"] = json.loads(meta_path.read_text(encoding="utf-8")).get("status")
                except Exception:
                    shot["meta_status"] = "parse_error"
            proj["shots"].append({"n": n, **shot})
            if not shot["ok"]:
                proj["issues"].append(f"shot-{n}: {shot['note']}")

        report["projects"].append(proj)

    if OUTPUT.is_dir():
        for path in sorted(OUTPUT.glob("*-final-video.mp4")):
            item = check_mp4(path)
            if item["ok"]:
                item["duration_s"] = probe_duration(path)
            report["output_copies"].append(item)

    ok_finals = sum(1 for p in report["projects"] if p["final"] and p["final"]["ok"])
    ok_shots = sum(1 for p in report["projects"] for s in p["shots"] if s["ok"])
    report["summary"] = {
        "final_videos_ok": f"{ok_finals}/{len(slugs)}",
        "shots_ok": f"{ok_shots}/{len(slugs) * 5}",
        "output_copies_ok": sum(1 for c in report["output_copies"] if c["ok"]),
        "projects_with_issues": [p["slug"] for p in report["projects"] if p["issues"]],
    }

    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 0 if not report["summary"]["projects_with_issues"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
