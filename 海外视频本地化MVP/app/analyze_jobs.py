"""单条素材豆包拆解后台任务（与 pipeline 批量任务独立）。"""

from __future__ import annotations

import os
import subprocess
import sys
import threading
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from .runtime_paths import resolve_venv_python

MVP_ROOT = Path(__file__).resolve().parents[1]
PIPELINE = MVP_ROOT / "scripts" / "pipeline.py"
PYTHON = resolve_venv_python(MVP_ROOT / ".venv", fallback=Path(sys.executable))

_lock = threading.Lock()
_states: dict[str, dict[str, Any]] = {}


def _utc() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def analyze_status(link_id: int | str) -> dict[str, Any] | None:
    with _lock:
        st = _states.get(str(link_id))
        return dict(st) if st else None


def clear_analyze_job(link_id: int | str) -> None:
    with _lock:
        _states.pop(str(link_id), None)


def _run_analyze(link_id: int) -> None:
    key = str(link_id)
    from app.doubao_config import video_analysis_policy

    policy = video_analysis_policy()
    if not policy.get("llm_enabled"):
        with _lock:
            _states[key] = {
                "status": "error",
                "link_id": link_id,
                "finished_at": _utc(),
                "exit_code": 1,
                "output": policy.get("message") or "视频豆包拆解已暂停",
            }
        return
    proc = subprocess.run(
        [
            str(PYTHON),
            str(PIPELINE),
            "decompose",
            "--provider",
            "doubao",
            "--link-id",
            str(link_id),
        ],
        cwd=str(MVP_ROOT),
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        env={**os.environ, "PYTHONIOENCODING": "utf-8", "PYTHONUTF8": "1"},
    )
    output = (proc.stdout or "") + (proc.stderr or "")
    if proc.returncode != 0:
        status = "error"
    elif "豆包失败" in output:
        status = "partial"
    else:
        status = "done"
    with _lock:
        _states[key] = {
            "status": status,
            "link_id": link_id,
            "finished_at": _utc(),
            "exit_code": proc.returncode,
            "output": output[-4000:],
        }


def start_material_analyze(link_id: int) -> dict[str, Any]:
    """启动单条豆包拆解；若已在跑则返回当前状态。"""
    key = str(link_id)
    with _lock:
        cur = _states.get(key)
        if cur and cur.get("status") == "running":
            return dict(cur)
        _states[key] = {
            "status": "running",
            "link_id": link_id,
            "started_at": _utc(),
            "finished_at": None,
            "exit_code": None,
            "output": "",
        }
    threading.Thread(target=_run_analyze, args=(link_id,), daemon=True).start()
    with _lock:
        return dict(_states[key])
