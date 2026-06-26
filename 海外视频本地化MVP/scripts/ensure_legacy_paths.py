"""为迁移后的素材库创建旧路径联接，避免未重启的工作台读不到数据。"""
from __future__ import annotations

import os
import sys
from pathlib import Path

MVP_ROOT = Path(__file__).resolve().parents[1]
WORKFLOW_ROOT = MVP_ROOT.parent

LINKS = [
    (MVP_ROOT / "数据表", WORKFLOW_ROOT / "01_素材库" / "竞品对标" / "数据表"),
    (MVP_ROOT / "AI拆解结果", WORKFLOW_ROOT / "01_素材库" / "竞品对标" / "AI拆解结果"),
    (MVP_ROOT / "产品资料", WORKFLOW_ROOT / "01_素材库" / "产品资料"),
    (MVP_ROOT / "生成脚本", WORKFLOW_ROOT / "01_素材库" / "脚本快照"),
    (WORKFLOW_ROOT / "成稿库", WORKFLOW_ROOT / "04_成稿库"),
    (WORKFLOW_ROOT / "反馈库", WORKFLOW_ROOT / "05_反馈库"),
]


def ensure_legacy_junctions() -> list[str]:
    created: list[str] = []
    for link, target in LINKS:
        if not target.is_dir():
            continue
        if link.exists():
            if link.is_symlink() or _is_junction(link):
                continue
            # 真实目录已存在且非联接：不覆盖
            continue
        link.parent.mkdir(parents=True, exist_ok=True)
        if os.name == "nt":
            import subprocess

            subprocess.run(
                ["cmd", "/c", "mklink", "/J", str(link), str(target)],
                check=True,
                capture_output=True,
            )
        else:
            link.symlink_to(target, target_is_directory=True)
        created.append(f"{link.name} -> {target}")
    return created


def _is_junction(path: Path) -> bool:
    try:
        return path.is_dir() and os.path.samefile(path, path.resolve())
    except OSError:
        return False


if __name__ == "__main__":
    made = ensure_legacy_junctions()
    for line in made:
        print("linked:", line)
    if not made:
        print("all legacy links ok")
