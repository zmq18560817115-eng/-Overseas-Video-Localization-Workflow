"""为迁移后的素材库创建旧路径联接，避免未重启的工作台读不到数据。

安全原则：旧目录(legacy) 与 新目录(canonical) 出现同名文件但内容不同(冲突)时，
绝不静默丢弃任何一方——冲突文件的旧版本会被备份到 06_备份库/cleanup-legacy-conflicts/，
canonical 一侧保留为最终生效版本（因为线上代码固定读取 canonical 路径），
仅旧目录独有的文件会正常合并进 canonical。
"""
from __future__ import annotations

import hashlib
import os
import shutil
import subprocess
from datetime import datetime, timezone
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


def _link_target(link: Path) -> Path | None:
    """已存在的联接（symlink/junction）当前实际指向哪里；非联接或已损坏返回 None。"""
    try:
        if not link.is_symlink() and not _is_junction(link):
            return None
        resolved = link.resolve()
        return resolved if resolved.exists() else None
    except OSError:
        return None


def _sha1(path: Path) -> str:
    h = hashlib.sha1()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1 << 16), b""):
            h.update(chunk)
    return h.hexdigest()


def _backup_dir() -> Path:
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    d = WORKFLOW_ROOT / "06_备份库" / "cleanup-legacy-conflicts" / stamp
    d.mkdir(parents=True, exist_ok=True)
    return d


def _merge_into(src: Path, dest: Path, *, backup_root: Path | None) -> tuple[int, list[str]]:
    """将 src 中缺失/冲突的文件安全合并进 dest。

    - dest 中不存在的文件：直接复制过去（旧目录独有数据不丢）。
    - dest 中已存在但内容不同（冲突）：dest 版本保留生效，src 版本备份到 06_备份库，绝不静默丢弃。
    - 内容相同：跳过。
    返回 (合并的文件数, 冲突文件相对路径列表)。
    """
    if not src.is_dir() or not dest.is_dir():
        return 0, []
    copied = 0
    conflicts: list[str] = []
    for item in src.rglob("*"):
        if not item.is_file():
            continue
        rel = item.relative_to(src)
        target = dest / rel
        if not target.exists():
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(item, target)
            copied += 1
            continue
        try:
            same = target.is_file() and _sha1(item) == _sha1(target)
        except OSError:
            same = False
        if same:
            continue
        conflicts.append(str(rel))
        if backup_root is not None:
            backup_path = backup_root / src.name / rel
            backup_path.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(item, backup_path)
    return copied, conflicts


def _mklink_junction(link: Path, target: Path) -> None:
    link.parent.mkdir(parents=True, exist_ok=True)
    if os.name == "nt":
        # NTFS junction 内部固定使用绝对路径，这是唯一合理选择。
        subprocess.run(
            ["cmd", "/c", "mklink", "/J", str(link), str(target)],
            check=True,
            capture_output=True,
        )
    else:
        # 用相对路径建 symlink，避免把「本机绝对路径」写死进联接
        # （否则换一台机器/换克隆目录，联接就会指向一个根本不存在的路径——
        # 正是这份脚本最初要修的那类 bug）。
        rel_target = os.path.relpath(target, start=link.parent)
        link.symlink_to(rel_target, target_is_directory=True)


def replace_legacy_dirs_with_junctions(*, dry_run: bool = False) -> list[str]:
    """若旧路径为实体目录且 canonical 已存在：安全合并差异后删除旧目录并建 junction。

    若旧路径已是联接但指向错误/已损坏目标（例如写死了他人机器的绝对路径），会修正为正确的 canonical 目标。
    """
    lines: list[str] = []
    for link, target in LINKS:
        if not target.is_dir():
            target.mkdir(parents=True, exist_ok=True)

        if not link.exists() and not link.is_symlink():
            if dry_run:
                lines.append(f"[dry-run] junction {link.name} -> {target}")
            else:
                _mklink_junction(link, target)
                lines.append(f"linked: {link.name} -> {target}")
            continue

        if link.is_symlink() or _is_junction(link):
            current = _link_target(link)
            if current is not None and current == target.resolve():
                lines.append(f"ok junction: {link.name}")
                continue
            # 断链或指向错误目标（如写死了他人机器的路径）——修正它
            if dry_run:
                lines.append(f"[dry-run] repair broken/mismatched link {link.name} -> {target}")
                continue
            link.unlink()
            _mklink_junction(link, target)
            lines.append(f"repaired link: {link.name} -> {target}")
            continue

        if not link.is_dir():
            continue

        if dry_run:
            copied, conflicts = _merge_into(link, target, backup_root=None)
            if conflicts:
                lines.append(
                    f"[dry-run] merge {copied} file(s), {len(conflicts)} conflict(s) would be backed up "
                    f"to 06_备份库/cleanup-legacy-conflicts/, junction {link.name}"
                )
            else:
                lines.append(f"[dry-run] merge {copied} file(s), junction {link.name}")
            continue

        backup_root = _backup_dir()
        copied, conflicts = _merge_into(link, target, backup_root=backup_root)
        shutil.rmtree(link)
        _mklink_junction(link, target)
        if conflicts:
            lines.append(
                f"replaced dir with junction ({copied} merged, {len(conflicts)} conflict(s) backed up to "
                f"{backup_root.relative_to(WORKFLOW_ROOT)}): {link.name}"
            )
        else:
            lines.append(f"replaced dir with junction ({copied} merged): {link.name}")
    return lines


def ensure_legacy_junctions() -> list[str]:
    created: list[str] = []
    for link, target in LINKS:
        if not target.is_dir():
            continue
        if link.exists() or link.is_symlink():
            continue
        _mklink_junction(link, target)
        created.append(f"{link.name} -> {target}")
    return created


if __name__ == "__main__":
    for line in replace_legacy_dirs_with_junctions():
        print(line)
