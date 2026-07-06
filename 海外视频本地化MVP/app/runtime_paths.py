"""Runtime path helpers shared by Windows and macOS/Linux deployments."""
from __future__ import annotations

import os
import sys
from pathlib import Path


def venv_python_candidates(venv_dir: Path) -> list[Path]:
    """Return plausible Python executables for a virtualenv on this platform."""
    candidates = [
        venv_dir / "Scripts" / "python.exe",
        venv_dir / "bin" / "python",
        venv_dir / "bin" / "python3",
    ]
    if os.name != "nt":
        candidates = [
            venv_dir / "bin" / "python",
            venv_dir / "bin" / "python3",
            venv_dir / "Scripts" / "python.exe",
        ]
    return candidates


def resolve_venv_python(venv_dir: Path, *, fallback: Path | None = None) -> Path:
    """Find an existing virtualenv Python, falling back to the current interpreter."""
    for path in venv_python_candidates(venv_dir):
        if path.is_file():
            return path
    if fallback:
        return fallback
    return Path(sys.executable)
