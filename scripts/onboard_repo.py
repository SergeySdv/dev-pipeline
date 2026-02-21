#!/usr/bin/env python3
"""
Legacy compatibility shim for the old onboarding script.
"""

import argparse
import sys


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Deprecated compatibility shim. Use DevGodzilla project/onboard commands instead.",
    )
    parser.parse_args()

    print("scripts/onboard_repo.py is deprecated and no longer wired to the active runtime.")
    print("Use DevGodzilla CLI instead:")
    print("  - python -m devgodzilla.cli.main project create <name> --repo <git_url> --branch <base>")
    print("  - python -m devgodzilla.cli.main project onboard <project_id>")
    print("  - python -m devgodzilla.cli.main project discover <project_id> --agent --pipeline")
    print("See docs/cli.md for examples.")
    return 2


if __name__ == "__main__":
    sys.exit(main())
