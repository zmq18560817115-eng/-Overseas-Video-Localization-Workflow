from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app.tiktok_collector_bridge import sync_collector_database_to_workflow


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Sync TikTok collector MySQL records into workflow CSVs.")
    parser.add_argument("--q", default="", help="Free-text search over caption/author/video_id/source keyword/hashtags")
    parser.add_argument("--source-keyword", default="", help="Filter by exact source_keyword")
    parser.add_argument("--processing-status", default="", help="Filter by processing_status")
    parser.add_argument("--limit", type=int, default=20, help="Max records to sync")
    return parser


def main() -> int:
    args = build_parser().parse_args()
    result = sync_collector_database_to_workflow(
        q=args.q,
        source_keyword=args.source_keyword,
        processing_status=args.processing_status,
        limit=args.limit,
    )
    print(
        json.dumps(
            {
                "db_enabled": result.db_enabled,
                "queried_total": result.queried_total,
                "synced_count": result.synced_count,
                "imported_new_links": result.imported_new_links,
                "updated_existing_links": result.updated_existing_links,
            },
            ensure_ascii=False,
            indent=2,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
