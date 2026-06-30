from __future__ import annotations

from fastapi import FastAPI

from .models import CollectRequest, CollectResponse
from .service import TikTokCollectorService


def create_app() -> FastAPI:
    app = FastAPI(title="tiktok_collector", version="0.1.0")
    service = TikTokCollectorService()

    @app.get("/health")
    def health() -> dict[str, object]:
        return {
            "ok": True,
            "output_dir": str(service.settings.output_dir),
            "headless": service.settings.headless,
            "max_results": service.settings.max_results,
            "mysql_enabled": service.db.enabled,
        }

    @app.post("/collect", response_model=CollectResponse)
    def collect(request: CollectRequest) -> CollectResponse:
        return service.collect(request).response

    return app
