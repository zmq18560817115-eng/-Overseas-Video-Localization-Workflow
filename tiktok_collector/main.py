from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import uvicorn

if __package__ in (None, ""):
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
    from tiktok_collector.models import CollectRequest
    from tiktok_collector.service import TikTokCollectorService
else:
    from .models import CollectRequest
    from .service import TikTokCollectorService


def _resolve_mvp_app_dir(workflow_root: Path) -> Path:
    direct = workflow_root / "海外视频本地化MVP" / "app"
    if direct.exists():
        return direct
    for candidate in workflow_root.iterdir():
        app_dir = candidate / "app"
        if candidate.is_dir() and app_dir.exists() and (app_dir / "tiktok_collector_bridge.py").exists():
            return app_dir
    raise RuntimeError("未找到主项目 app 目录，无法导入素材库")


def _import_into_workflow(service: TikTokCollectorService, result) -> dict[str, object]:
    workflow_root = Path(__file__).resolve().parents[1]
    mvp_app_dir = _resolve_mvp_app_dir(workflow_root)
    if str(mvp_app_dir) not in sys.path:
        sys.path.insert(0, str(mvp_app_dir))
    from tiktok_collector_bridge import import_reviewed_records

    imported = import_reviewed_records(
        result.response.clean_records,
        total_collected=result.response.total_records,
        total_dropped=result.response.dropped_records,
        json_path=str(result.json_file) if result.json_file else None,
        csv_path=str(result.csv_file) if result.csv_file else None,
        clean_json_path=str(result.clean_json_file) if result.clean_json_file else None,
        clean_csv_path=str(result.clean_csv_file) if result.clean_csv_file else None,
        review_json_path=str(result.review_json_file) if result.review_json_file else None,
        output_dir=str(service.settings.output_dir),
    )
    return {
        "imported_new_links": imported.imported_new_links,
        "updated_existing_links": imported.updated_existing_links,
        "total_cleaned": imported.total_cleaned,
        "total_dropped": imported.total_dropped,
    }


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Minimal TikTok public metadata collector")
    subparsers = parser.add_subparsers(dest="command", required=True)

    collect = subparsers.add_parser("collect", help="Collect public TikTok metadata for keywords")
    collect.add_argument("--keywords", nargs="+", required=True, help="Keywords to search")
    collect.add_argument("--limit", type=int, default=20, help="Max results per keyword")
    collect.add_argument("--no-json", action="store_true", help="Skip JSON export")
    collect.add_argument("--no-csv", action="store_true", help="Skip CSV export")
    collect.add_argument("--import-workflow", action="store_true", help="Import clean results into workflow CSVs")

    serve = subparsers.add_parser("serve", help="Run collector API service")
    serve.add_argument("--host", default="127.0.0.1")
    serve.add_argument("--port", type=int, default=8890)

    return parser


def main() -> int:
    parser = _build_parser()
    args = parser.parse_args()

    if args.command == "serve":
        uvicorn.run("tiktok_collector.api:create_app", factory=True, host=args.host, port=args.port, reload=False)
        return 0

    service = TikTokCollectorService()
    request = CollectRequest(
        keywords=args.keywords,
        limit_per_keyword=args.limit,
        export_json=not args.no_json,
        export_csv=not args.no_csv,
    )
    run = service.collect(request)
    payload = run.response.model_dump(mode="json")
    if args.import_workflow:
        payload["workflow_import"] = _import_into_workflow(service, run)
    print(json.dumps(payload, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
