#!/usr/bin/env python3
"""
Run DevGodzilla multi-stage discovery on an existing repository.

This replaces the archived legacy implementation and uses the active
`DiscoveryAgentService` from `devgodzilla.services.discovery_agent`.
"""

import argparse
import os
import sys
from pathlib import Path
from typing import Optional

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from devgodzilla.config import load_config  # noqa: E402
from devgodzilla.logging import (  # noqa: E402
    EXIT_RUNTIME_ERROR,
    get_logger,
    init_cli_logging,
    json_logging_from_env,
)
from devgodzilla.services.base import ServiceContext  # noqa: E402
from devgodzilla.services.discovery_agent import DiscoveryAgentService  # noqa: E402

log = get_logger(__name__)


def parse_args(argv: Optional[list[str]] = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run multi-stage discovery and generate artifacts.")
    parser.add_argument("--repo-root", default=".", help="Repository root to analyze.")
    parser.add_argument("--engine", default=None, help="Engine ID for discovery (default: config/env/opencode).")
    parser.add_argument("--model", default=None, help="Model to use (default: engine default).")
    parser.add_argument(
        "--artifacts",
        default="inventory,architecture,api_reference,ci_notes",
        help="Comma-separated stages: inventory,architecture,api_reference,ci_notes",
    )
    parser.add_argument("--timeout-seconds", type=int, default=900, help="Engine timeout per stage.")
    parser.add_argument("--strict", dest="strict", action="store_true", help="Fail on missing outputs.")
    parser.add_argument("--no-strict", dest="strict", action="store_false", help="Allow missing outputs.")
    parser.set_defaults(strict=True)
    parser.add_argument("--pipeline", action="store_true", default=True, help="Use multi-stage discovery (default).")
    parser.add_argument("--single", dest="pipeline", action="store_false", help="Use single-stage discovery prompt.")
    return parser.parse_args(argv)


def main() -> int:
    config = load_config()
    init_cli_logging(config.log_level, json_output=json_logging_from_env())
    args = parse_args()

    repo_root = Path(args.repo_root).resolve()
    if not repo_root.exists():
        log.error("repo_root_missing", extra={"repo_root": str(repo_root)})
        return EXIT_RUNTIME_ERROR

    engine_id = (
        args.engine
        or os.environ.get("PROTOCOL_DISCOVERY_ENGINE")
        or getattr(config, "default_engine_id", None)
        or "opencode"
    )
    model = args.model or os.environ.get("PROTOCOL_DISCOVERY_MODEL")

    artifacts = [a.strip() for a in args.artifacts.split(",") if a.strip()]
    if args.pipeline:
        stages = artifacts
    else:
        stages = ["repo_discovery"]

    service = DiscoveryAgentService(ServiceContext(config=config))
    result = service.run_discovery(
        repo_root=repo_root,
        engine_id=engine_id,
        model=model,
        pipeline=args.pipeline,
        stages=stages,
        timeout_seconds=args.timeout_seconds,
        strict_outputs=args.strict,
    )

    if result.success:
        log.info(
            "discovery_pipeline_complete",
            extra={
                "repo_root": str(result.repo_root),
                "engine_id": result.engine_id,
                "model": result.model,
                "log_path": str(result.log_path),
            },
        )
        if result.warning:
            log.warning("discovery_pipeline_warning", extra={"warning": result.warning})
        return 0

    log.error(
        "discovery_pipeline_failed",
        extra={
            "repo_root": str(result.repo_root),
            "engine_id": result.engine_id,
            "model": result.model,
            "error": result.error,
            "missing_outputs": [str(p) for p in result.missing_outputs],
        },
    )
    return EXIT_RUNTIME_ERROR


if __name__ == "__main__":
    raise SystemExit(main())
