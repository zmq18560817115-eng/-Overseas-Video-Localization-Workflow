"""清理前的差异体检：只读、不写、不删。

在服务器上执行「清理工作区.cmd --dry-run」之前，先用这个脚本看清楚旧路径
（成稿库/反馈库/数据表/产品资料/生成脚本/AI拆解结果）和 canonical 路径
（04_成稿库/05_反馈库/01_素材库/...）之间到底差在哪，再决定要不要合并。

用法:
  python scripts/preflight_cleanup.py
"""
from __future__ import annotations

import hashlib
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

MVP_ROOT = Path(__file__).resolve().parent
WORKFLOW_ROOT = MVP_ROOT.parents[1]

if str(MVP_ROOT) not in sys.path:
    sys.path.insert(0, str(MVP_ROOT))

from ensure_legacy_paths import LINKS  # noqa: E402


def _sha1(path: Path) -> str:
    h = hashlib.sha1()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1 << 16), b""):
            h.update(chunk)
    return h.hexdigest()


def _walk_files(root: Path) -> dict[str, Path]:
    if not root.is_dir():
        return {}
    return {str(p.relative_to(root)).replace("\\", "/"): p for p in root.rglob("*") if p.is_file()}


def diff_pair(legacy: Path, canonical: Path) -> dict:
    if legacy.is_symlink():
        try:
            resolved = legacy.resolve()
            ok = resolved.exists() and resolved == canonical.resolve()
        except OSError:
            resolved, ok = None, False
        return {
            "legacy": str(legacy.relative_to(WORKFLOW_ROOT)),
            "canonical": str(canonical.relative_to(WORKFLOW_ROOT)),
            "type": "symlink",
            "status": "ok" if ok else "broken_or_wrong_target",
            "current_target": str(resolved) if resolved else None,
        }
    if not legacy.exists():
        return {
            "legacy": str(legacy.relative_to(WORKFLOW_ROOT)),
            "canonical": str(canonical.relative_to(WORKFLOW_ROOT)),
            "type": "missing",
            "status": "legacy_absent",
        }

    legacy_files = _walk_files(legacy)
    canonical_files = _walk_files(canonical)

    only_legacy: list[str] = []
    only_canonical: list[str] = []
    conflicts: list[str] = []
    identical = 0

    for rel, lp in legacy_files.items():
        cp = canonical_files.get(rel)
        if cp is None:
            only_legacy.append(rel)
        elif _sha1(lp) != _sha1(cp):
            conflicts.append(rel)
        else:
            identical += 1
    for rel in canonical_files:
        if rel not in legacy_files:
            only_canonical.append(rel)

    return {
        "legacy": str(legacy.relative_to(WORKFLOW_ROOT)),
        "canonical": str(canonical.relative_to(WORKFLOW_ROOT)),
        "type": "dir",
        "status": "conflict" if conflicts else "clean",
        "only_in_legacy": sorted(only_legacy),
        "only_in_canonical": sorted(only_canonical),
        "same_name_diff_content": sorted(conflicts),
        "identical_count": identical,
        "suggested_side": (
            "canonical（线上代码固定读取这条路径）；"
            "only_in_legacy 会在清理时自动合并进 canonical；"
            "same_name_diff_content 会把旧版本备份到 06_备份库/cleanup-legacy-conflicts/ 后以 canonical 为准，"
            "建议清理后打开备份人工核对一遍。"
        ),
    }


def main() -> int:
    results = [diff_pair(link, target) for link, target in LINKS]
    report = {"generated_at": datetime.now(timezone.utc).isoformat(), "pairs": results}

    out_dir = WORKFLOW_ROOT / "temp"
    out_dir.mkdir(parents=True, exist_ok=True)
    (out_dir / "cleanup_preflight_report.json").write_text(
        json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8"
    )

    lines = ["# 清理预检报告", "", f"生成时间: {report['generated_at']}", ""]
    for r in results:
        lines.append(f"## {r['legacy']} -> {r['canonical']}")
        lines.append(f"- 状态: {r['status']}")
        if r["type"] == "symlink":
            lines.append(f"- 当前指向: {r.get('current_target') or '（断链）'}")
        elif r["type"] == "missing":
            lines.append("- 旧目录不存在，无需处理")
        else:
            lines.append(f"- 仅旧目录存在（会自动合并）: {len(r['only_in_legacy'])} 个")
            for rel in r["only_in_legacy"][:20]:
                lines.append(f"  - {rel}")
            lines.append(f"- 仅新目录存在: {len(r['only_in_canonical'])} 个")
            lines.append(f"- 同名但内容不同（需人工确认）: {len(r['same_name_diff_content'])} 个")
            for rel in r["same_name_diff_content"][:20]:
                lines.append(f"  - {rel}")
            lines.append(f"- 内容一致: {r['identical_count']} 个")
        lines.append("")
    (out_dir / "cleanup_preflight_report.md").write_text("\n".join(lines), encoding="utf-8")

    print(f"报告已写入 {out_dir / 'cleanup_preflight_report.md'}")
    conflict_pairs = [r for r in results if r.get("status") in ("conflict", "broken_or_wrong_target")]
    if conflict_pairs:
        print(f"发现 {len(conflict_pairs)} 组需要留意的差异，详见报告；清理时会自动备份冲突文件，不会丢数据。")
        return 1
    print("未发现需要人工确认的冲突，可以安全执行 清理工作区.cmd。")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
