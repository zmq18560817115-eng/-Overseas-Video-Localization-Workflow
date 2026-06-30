"""Minimal TikTok public metadata collector."""

from .api import create_app
from .service import TikTokCollectorService

__all__ = ["TikTokCollectorService", "create_app"]
