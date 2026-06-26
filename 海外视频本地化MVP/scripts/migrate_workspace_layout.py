"""一次性迁移：整理素材库目录 + 将已有成片迁入 03_产出库（保留 runs 原文件）。

用法:
  python scripts/migrate_workspace_layout.py
  python scripts/migrate_workspace_layout.py --dry-run
"""
from __future__ import annotations

import argparse
import shutil
import sys
from pathlib import Path

MVP_ROOT = Path(__file__).resolve().parents[1]
WORKFLOW_ROOT = MVP_ROOT.parent
ENGINE_ROOT = WORKFLOW_ROOT / "overseas-loc-mvp"
sys.path.insert(0, str(ENGINE_ROOT))

from app.production_archive import archive_production  # noqa: E402

MOVES = [
    (MVP_ROOT / "数据表", WORKFLOW_ROOT / "01_素材库" / "竞品对标" / "数据表"),
    (MVP_ROOT / "AI拆解结果", WORKFLOW_ROOT / "01_素材库" / "竞品对标" / "AI拆解结果"),
    (MVP_ROOT / "产品资料", WORKFLOW_ROOT / "01_素材库" / "产品资料"),
    (MVP_ROOT / "生成脚本", WORKFLOW_ROOT / "01_素材库" / "脚本快照"),
    (WORKFLOW_ROOT / "成稿库", WORKFLOW_ROOT / "04_成稿库"),
    (WORKFLOW_ROOT / "反馈库", WORKFLOW_ROOT / "05_反馈库"),
]


def move_tree(src: Path, dest: Path, *, dry_run: bool) -> None:
    if not src.exists():
        print(f"  skip (missing): {src}")
        return
    if dest.exists():
        print(f"  skip (exists): {dest}")
        return
    print(f"  move: {src.name} -> {dest.relative_to(WORKFLOW_ROOT)}")
    if not dry_run:
        dest.parent.mkdir(parents=True, exist_ok=True)
        shutil.move(str(src), str(dest))


def migrate_runs_to_archive(*, dry_run: bool) -> int:
    from app.production_archive import PRODUCTION_ARCHIVE_DIR, list_versions

    runs = WORKFLOW_ROOT / "overseas-loc-mvp" / "runs"
    count = 0
    for project in sorted(runs.glob("ref-*")):
        final = project / "broll" / "final-video.mp4"
        if not final.is_file():
            continue
        slug = project.name
        if list_versions(slug):
            print(f"  archive skip {slug}: 产出库已有版本")
            continue
        print(f"  archive: {slug} -> 03_产出库/{slug}/")
        if not dry_run:
            archive_production(project, slug, note="migrate_workspace_layout")
        count += 1
    return count


def write_readmes() -> None:
  readme_01 = WORKFLOW_ROOT / "01_素材库" / "README.md"
  readme_01.parent.mkdir(parents=True, exist_ok=True)
  readme_01.write_text(
    """# 01 素材库

| 子目录 | 内容 |
|--------|------|
| `竞品对标/数据表/` | TikTok 竞品 URL、元数据、8 字段结构拆解 CSV |
| `竞品对标/AI拆解结果/` | 每条对标 #{id} 的 analysis.json |
| `产品资料/` | 我方产品 Markdown + listing 图片（SeedDance 垫图） |
| `脚本快照/` | 每次「生成脚本」的快照 script-pack.json |

公司知识库引擎副本：`overseas-loc-mvp/knowledge/`（合规、流程、产品镜像）
""",
    encoding="utf-8",
  )
  (WORKFLOW_ROOT / "02_引擎工作区" / "README.md").write_text(
    """# 02 引擎工作区

| 路径 | 说明 |
|------|------|
| `overseas-loc-mvp/runs/ref-{id}/` | **当前工作副本**（最新脚本、字幕、分镜；成片会被下次强制重生成覆盖） |
| `overseas-loc-mvp/` | 交付引擎代码与 .env |

历史成片请查 **`03_产出库/`**（按时间版本保留，不覆盖）。
""",
    encoding="utf-8",
  )
  (WORKFLOW_ROOT / "03_产出库" / "README.md").write_text(
    """# 03 产出库（版本化视频归档）

每次拼接 `final-video.mp4` 成功后自动复制到此目录：

```
03_产出库/
  ref-025/
    20260626-111208/
      final-video.mp4
      shots/shot-1..5.mp4
      meta/script-pack.json, storyboard.json, ...
      manifest.json
  产出索引.csv
```

**runs/** 里保留最新工作副本；**03_产出库/** 保留每一次成功产出的历史版本。
""",
    encoding="utf-8",
  )


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()
    dry = args.dry_run

    print("=== 创建目录结构 ===")
    for _, dest in MOVES:
        if not dry:
            dest.parent.mkdir(parents=True, exist_ok=True)
    (WORKFLOW_ROOT / "03_产出库").mkdir(parents=True, exist_ok=True)
    (WORKFLOW_ROOT / "02_引擎工作区").mkdir(parents=True, exist_ok=True)

    print("=== 迁移素材/成稿/反馈 ===")
    for src, dest in MOVES:
        move_tree(src, dest, dry_run=dry)

    print("=== 归档已有成片到 03_产出库 ===")
    n = migrate_runs_to_archive(dry_run=dry)

    if not dry:
        write_readmes()
    print(f"完成。归档 {n} 个项目成片。")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
