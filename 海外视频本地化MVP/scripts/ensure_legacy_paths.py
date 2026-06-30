"""为迁移后的素材库创建旧路径联接，避免未重启的工作台读不到数据。"""
from __future__ import annotations

import os
import shutil
import subprocess
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


def _is_junction(path: Path) -> bool:
    if os.name != "nt" or not path.exists():
        return path.is_symlink()
    try:
        import stat

        return stat.S_ISDIR(path.lstat().st_mode) and path.lstat().st_file_attributes & 0x400  # FILE_ATTRIBUTE_REPARSE_POINT
    except (OSError, AttributeError):
        try:
            return path.is_symlink()
        except OSError:
            return False


def _merge_into(src: Path, dest: Path) -> int:
    """将 src 中目标缺失的文件复制到 dest，返回复制数量。"""
    if not src.is_dir() or not dest.is_dir():
        return 0
    copied = 0
    for item in src.rglob("*"):
        if not item.is_file():
            continue
        rel = item.relative_to(src)
        target = dest / rel
        if target.exists():
            continue
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(item, target)
        copied += 1
    return copied


def _mklink_junction(link: Path, target: Path) -> None:
    link.parent.mkdir(parents=True, exist_ok=True)
    if os.name == "nt":
        subprocess.run(
            ["cmd", "/c", "mklink", "/J", str(link), str(target)],
            check=True,
            capture_output=True,
        )
    else:
        link.symlink_to(target, target_is_directory=True)


def replace_legacy_dirs_with_junctions(*, dry_run: bool = False) -> list[str]:
    """若旧路径为实体目录且 canonical 已存在：合并差异后删除旧目录并建 junction。"""
    lines: list[str] = []
    for link, target in LINKS:
        if not target.is_dir():
            target.mkdir(parents=True, exist_ok=True)
        if not link.exists():
            if dry_run:
                lines.append(f"[dry-run] junction {link.name} -> {target}")
            else:
                _mklink_junction(link, target)
                lines.append(f"linked: {link.name} -> {target}")
            continue
        if _is_junction(link) or link.is_symlink():
            lines.append(f"ok junction: {link.name}")
            continue
        if not link.is_dir():
            continue
        merged = _merge_into(link, target)
        if dry_run:
            lines.append(f"[dry-run] merge {merged} files, junction {link.name}")
            continue
        shutil.rmtree(link)
        _mklink_junction(link, target)
        lines.append(f"replaced dir with junction ({merged} merged): {link.name}")
    return lines


def ensure_legacy_junctions() -> list[str]:
    created: list[str] = []
    for link, target in LINKS:
        if not target.is_dir():
            continue
        if link.exists():
            if _is_junction(link) or link.is_symlink():
                continue
            continue
        link.parent.mkdir(parents=True, exist_ok=True)
        if os.name == "nt":
            subprocess.run(
                ["cmd", "/c", "mklink", "/J", str(link), str(target)],
                check=True,
                capture_output=True,
            )
        else:
            link.symlink_to(target, target_is_directory=True)
        created.append(f"{link.name} -> {target}")
    return created


if __name__ == "__main__":
    for line in replace_legacy_dirs_with_junctions():
        print(line)
