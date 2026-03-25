#!/usr/bin/env python3
from __future__ import annotations

import argparse
import sys
from pathlib import Path


def _count_lines(path: Path) -> int:
    with path.open("r", encoding="utf-8", errors="ignore") as handle:
        return sum(1 for _ in handle)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Check Python module length.")
    parser.add_argument("paths", nargs="*", help="Python files to validate")
    parser.add_argument("--max-lines", type=int, default=1500, help="Maximum allowed line count")
    parser.add_argument(
        "--ignore",
        action="append",
        default=[],
        help="Repo-relative file path to ignore; may be passed multiple times",
    )
    args = parser.parse_args(argv)

    ignored = {Path(raw).as_posix() for raw in args.ignore}
    failures: list[tuple[Path, int]] = []
    for raw_path in args.paths:
        path = Path(raw_path)
        if not path.exists() or not path.is_file():
            continue
        if path.as_posix() in ignored:
            continue
        line_count = _count_lines(path)
        if line_count > args.max_lines:
            failures.append((path, line_count))

    if not failures:
        return 0

    print(f"Python modules exceeding {args.max_lines} lines:")
    for path, line_count in sorted(failures):
        print(f"  {path}: {line_count} lines")
    return 1


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
