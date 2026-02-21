#!/usr/bin/env python3
"""
Legacy compatibility shim for the old project setup script.
"""

import argparse
import sys


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Deprecated compatibility shim. Use DevGodzilla project commands instead.",
    )
    parser.parse_args()

    print("scripts/project_setup.py is deprecated and no longer wired to the active runtime.")
    print("Use DevGodzilla CLI commands instead:")
    print("  - python -m devgodzilla.cli.main project create <name> --repo <git_url> --branch <base>")
    print("  - python -m devgodzilla.cli.main project discover <project_id> --agent --pipeline")
    print("See docs/cli.md for details.")
    return 2


if __name__ == "__main__":
    sys.exit(main())
