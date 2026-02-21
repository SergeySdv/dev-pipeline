#!/usr/bin/env python3
"""
Legacy compatibility shim for the old spec audit script.
"""

import argparse
import sys


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Deprecated compatibility shim. Spec audit moved to API/TUI flows.",
    )
    parser.parse_args()

    print("scripts/spec_audit.py is deprecated and no longer wired to the active runtime.")
    print("Use current UI/API flows for specification integrity checks.")
    print("See docs/DevGodzilla/API-ARCHITECTURE.md and docs/cli.md.")
    return 2


if __name__ == "__main__":
    sys.exit(main())
