#!/usr/bin/env python3
"""
Legacy compatibility shim for the old QA orchestrator script.
"""

import argparse
import sys


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Deprecated compatibility shim. Use DevGodzilla QA commands instead.",
    )
    parser.parse_args()

    print("scripts/quality_orchestrator.py is deprecated and no longer wired to the active runtime.")
    print("Use one of:")
    print("  - python -m devgodzilla.cli.main step qa <step_id>")
    print("  - python -m devgodzilla.cli.main qa evaluate <workspace> <step_name>")
    print("See docs/cli.md for examples.")
    return 2


if __name__ == "__main__":
    sys.exit(main())
