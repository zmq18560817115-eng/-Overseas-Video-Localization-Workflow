from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

from dotenv import load_dotenv


BASE_DIR = Path(__file__).resolve().parent
ENV_FILE = BASE_DIR / ".env"


def _bool(name: str, default: bool) -> bool:
    raw = os.getenv(name, str(default)).strip().lower()
    return raw in {"1", "true", "yes", "on"}


def _int(name: str, default: int) -> int:
    try:
        return int(os.getenv(name, str(default)).strip())
    except ValueError:
        return default


@dataclass(slots=True)
class CollectorSettings:
    headless: bool
    max_results: int
    search_scrolls: int
    search_wait_ms: int
    video_wait_ms: int
    manual_verify_wait_ms: int
    error_retry_count: int
    locale: str
    output_dir: Path
    user_data_dir: Path
    mysql_url: str
    mysql_echo: bool


def load_settings() -> CollectorSettings:
    load_dotenv(ENV_FILE, override=False)
    output_dir = Path(os.getenv("TIKTOK_COLLECTOR_OUTPUT_DIR", "./data/raw")).expanduser()
    if not output_dir.is_absolute():
        output_dir = (BASE_DIR / output_dir).resolve()
    user_data_dir = Path(os.getenv("TIKTOK_COLLECTOR_USER_DATA_DIR", "./data/browser_profile")).expanduser()
    if not user_data_dir.is_absolute():
        user_data_dir = (BASE_DIR / user_data_dir).resolve()
    return CollectorSettings(
        headless=_bool("TIKTOK_COLLECTOR_HEADLESS", True),
        max_results=max(1, min(100, _int("TIKTOK_COLLECTOR_MAX_RESULTS", 20))),
        search_scrolls=max(1, _int("TIKTOK_COLLECTOR_SEARCH_SCROLLS", 5)),
        search_wait_ms=max(500, _int("TIKTOK_COLLECTOR_SEARCH_WAIT_MS", 1800)),
        video_wait_ms=max(500, _int("TIKTOK_COLLECTOR_VIDEO_WAIT_MS", 1500)),
        manual_verify_wait_ms=max(5000, _int("TIKTOK_COLLECTOR_MANUAL_VERIFY_WAIT_MS", 90000)),
        error_retry_count=max(0, min(5, _int("TIKTOK_COLLECTOR_ERROR_RETRY_COUNT", 2))),
        locale=os.getenv("TIKTOK_COLLECTOR_LOCALE", "en-US").strip() or "en-US",
        output_dir=output_dir,
        user_data_dir=user_data_dir,
        mysql_url=os.getenv("TIKTOK_COLLECTOR_MYSQL_URL", "").strip(),
        mysql_echo=_bool("TIKTOK_COLLECTOR_MYSQL_ECHO", False),
    )
