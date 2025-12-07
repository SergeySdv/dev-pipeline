#!/usr/bin/env python3
"""
CLI to audit/backfill ProtocolSpec entries across existing runs.

Usage:
  python3 scripts/spec_audit.py [--project-id 1] [--protocol-id 2] [--backfill]
"""

import argparse
import json
from pathlib import Path

from tasksgodzilla.config import load_config
from tasksgodzilla.spec_tools import audit_specs
from tasksgodzilla.storage import create_database


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Audit/backfill ProtocolSpec for existing runs.")
    parser.add_argument("--project-id", type=int, help="Limit audit to a specific project ID.")
    parser.add_argument("--protocol-id", type=int, help="Limit audit to a specific protocol run ID.")
    parser.add_argument("--backfill", action="store_true", help="Backfill missing specs from protocol files or CodeMachine config.")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    cfg = load_config()
    db = create_database(cfg.db_path, db_url=cfg.db_url, pool_size=cfg.db_pool_size)
    db.init_schema()

    results = audit_specs(
        db,
        project_id=args.project_id,
        protocol_id=args.protocol_id,
        backfill_missing=args.backfill,
    )
    for res in results:
        print(json.dumps(res, sort_keys=True))
    summary = {
        "count": len(results),
        "backfilled": sum(1 for r in results if r.get("backfilled")),
        "with_errors": sum(1 for r in results if r.get("errors")),
    }
    print(json.dumps({"summary": summary}, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
