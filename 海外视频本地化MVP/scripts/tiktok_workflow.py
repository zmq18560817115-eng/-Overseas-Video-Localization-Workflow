from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
WORKFLOW_ROOT = ROOT.parents[0]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
if str(WORKFLOW_ROOT) not in sys.path:
    sys.path.insert(0, str(WORKFLOW_ROOT))

from app.tiktok_collector_bridge import (
    collector_database_enabled,
    query_collector_database,
    run_collector_import,
    sync_collector_database_to_workflow,
)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Unified local TikTok collector workflow entrypoint for MVP / Cursor."
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    status = subparsers.add_parser("status", help="Show local workflow readiness")
    status.add_argument("--limit", type=int, default=3, help="Preview item count")

    collect_sync = subparsers.add_parser(
        "collect-sync",
        help="Collect TikTok data, write MySQL/exports, and sync clean results into workflow CSVs",
    )
    collect_sync.add_argument("--keywords", nargs="+", required=True, help="Keywords to search")
    collect_sync.add_argument("--limit", type=int, default=20, help="Max results per keyword")
    collect_sync.add_argument(
        "--manual-verify-wait-sec",
        type=int,
        default=180,
        help="Seconds to wait for TikTok manual verification in the opened browser",
    )
    collect_sync.add_argument(
        "--headless",
        choices=["true", "false"],
        default="false",
        help="Whether to run Playwright in headless mode for collection",
    )

    query_db = subparsers.add_parser("query-db", help="Query TikTok collector MySQL records")
    query_db.add_argument("--q", default="", help="Free-text search")
    query_db.add_argument("--source-keyword", default="", help="Exact source keyword")
    query_db.add_argument("--processing-status", default="", help="Processing status filter")
    query_db.add_argument("--limit", type=int, default=10, help="Max rows to return")

    sync_db = subparsers.add_parser(
        "sync-db",
        help="Sync existing TikTok collector MySQL records into workflow CSVs",
    )
    sync_db.add_argument("--q", default="", help="Free-text search")
    sync_db.add_argument("--source-keyword", default="", help="Exact source keyword")
    sync_db.add_argument("--processing-status", default="", help="Processing status filter")
    sync_db.add_argument("--limit", type=int, default=20, help="Max rows to sync")

    return parser


def emit(payload: dict) -> int:
    print(json.dumps(payload, ensure_ascii=True, indent=2))
    return 0


def main() -> int:
    args = build_parser().parse_args()

    if args.command == "status":
        db_enabled = collector_database_enabled()
        preview = query_collector_database(limit=args.limit) if db_enabled else None
        return emit(
            {
                "workflow_root": str(WORKFLOW_ROOT),
                "mvp_root": str(ROOT),
                "db_enabled": db_enabled,
                "preview_total": preview.total if preview else 0,
                "preview_items": preview.items if preview else [],
            }
        )

    if args.command == "collect-sync":
        os.environ["TIKTOK_COLLECTOR_HEADLESS"] = args.headless
        os.environ["TIKTOK_COLLECTOR_MANUAL_VERIFY_WAIT_MS"] = str(max(30, args.manual_verify_wait_sec) * 1000)
        try:
            result = run_collector_import(args.keywords, limit_per_keyword=args.limit)
        except RuntimeError as exc:
            message = str(exc)
            if "login/captcha" in message or "rate-limited" in message:
                return emit(
                    {
                        "ok": False,
                        "error_type": "manual_verification_required",
                        "message": message,
                        "next_action": (
                            "Complete TikTok login/captcha in the opened browser, "
                            "then rerun collect-sync with the same browser profile."
                        ),
                        "keywords": args.keywords,
                        "limit_per_keyword": args.limit,
                        "headless": args.headless,
                        "manual_verify_wait_sec": args.manual_verify_wait_sec,
                    }
                )
            raise
        return emit(
            {
                "ok": True,
                "keywords": args.keywords,
                "limit_per_keyword": args.limit,
                "total_collected": result.total_collected,
                "total_cleaned": result.total_cleaned,
                "total_dropped": result.total_dropped,
                "imported_new_links": result.imported_new_links,
                "updated_existing_links": result.updated_existing_links,
                "json_path": result.json_path,
                "csv_path": result.csv_path,
                "clean_json_path": result.clean_json_path,
                "clean_csv_path": result.clean_csv_path,
                "review_json_path": result.review_json_path,
                "output_dir": result.output_dir,
                "headless": args.headless,
                "manual_verify_wait_sec": args.manual_verify_wait_sec,
            }
        )

    if args.command == "query-db":
        result = query_collector_database(
            q=args.q,
            source_keyword=args.source_keyword,
            processing_status=args.processing_status,
            limit=args.limit,
        )
        return emit(
            {
                "db_enabled": result.db_enabled,
                "total": result.total,
                "items": result.items,
            }
        )

    if args.command == "sync-db":
        result = sync_collector_database_to_workflow(
            q=args.q,
            source_keyword=args.source_keyword,
            processing_status=args.processing_status,
            limit=args.limit,
        )
        return emit(
            {
                "db_enabled": result.db_enabled,
                "queried_total": result.queried_total,
                "synced_count": result.synced_count,
                "imported_new_links": result.imported_new_links,
                "updated_existing_links": result.updated_existing_links,
            }
        )

    raise RuntimeError(f"Unsupported command: {args.command}")


if __name__ == "__main__":
    raise SystemExit(main())
