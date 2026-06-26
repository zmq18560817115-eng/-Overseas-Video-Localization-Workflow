#!/usr/bin/env python3
"""验证 SeedDance 配置 + 项目 AI 空镜数据是否就绪。"""
from __future__ import annotations

import asyncio
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from app.config import settings  # noqa: E402
from app.providers import test_seedance_connection  # noqa: E402
from app.storage import project_dir  # noqa: E402
from app.workflow import seedance_status  # noqa: E402


def main() -> int:
    slug = sys.argv[1] if len(sys.argv) > 1 else "ref-001"
    print("=== SeedDance 配置 ===")
    print(f"provider: {settings.seedance_provider_resolved or '(未配置)'}")
    print(f"configured: {settings.seedance_configured}")
    if settings.seedance_provider_resolved == "ark":
        print(f"ark_model: {settings.ark_text_model_resolved}")
    elif settings.seedance_provider_resolved == "fal":
        print(f"fal_model: {settings.seedance_text_model_resolved}")

    print("\n=== 连接测试（生成 4 秒探针视频，约 1–3 分钟）===")
    probe = asyncio.run(test_seedance_connection())
    print(json.dumps(probe, ensure_ascii=False, indent=2))
    if not probe.get("ok"):
        return 1

    print(f"\n=== 项目 {slug} AI 空镜状态 ===")
    project = project_dir(slug, create=False)
    if not project.exists():
        print(f"项目不存在: {project}")
        return 1
    status = seedance_status(project)
    print(json.dumps(status, ensure_ascii=False, indent=2))
    if not status.get("available"):
        print("提示：该项目无 AI_BROLL 镜头，请先在脚本生成页生成脚本并完成交付。")
        return 0
    pending = [s for s in status.get("shots", []) if not s.get("ready")]
    print(f"\n待生成镜头: {len(pending)} / {len(status.get('shots', []))}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
