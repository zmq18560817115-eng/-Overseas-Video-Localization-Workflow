from __future__ import annotations

import sys
from pathlib import Path

if __package__ in (None, ""):
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
    from tiktok_collector.config import load_settings
    from tiktok_collector.db import DatabaseManager
else:
    from .config import load_settings
    from .db import DatabaseManager


def main() -> int:
    settings = load_settings()
    db = DatabaseManager(settings)
    db.init_db()
    print("Initialized MySQL table: tiktok_videos")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
