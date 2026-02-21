#!/usr/bin/env python3
"""
Legacy compatibility shim for the old protocol pipeline script.

The original standalone pipeline implementation depended on archived modules
that are no longer part of the active DevGodzilla runtime.
"""

import argparse
import sys


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Deprecated compatibility shim. Use DevGodzilla CLI protocol commands instead.",
    )
    parser.parse_args()

    print("scripts/protocol_pipeline.py is deprecated and no longer wired to the active runtime.")
    print("Use the DevGodzilla CLI flow instead:")
    print("  1) python -m devgodzilla.cli.main protocol create <project_id> <protocol_name> --description \"...\"")
    print("  2) python -m devgodzilla.cli.main protocol generate <protocol_id>")
    print("  3) python -m devgodzilla.cli.main protocol plan <protocol_id>")
    print("  4) python -m devgodzilla.cli.main protocol start <protocol_id>")
    print("See docs/cli.md for complete examples.")
    return 2


if __name__ == "__main__":
    sys.exit(main())
