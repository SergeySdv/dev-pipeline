#!/usr/bin/env python3
"""
Compatibility wrapper for the legacy onboarding test script.
"""

import subprocess
import sys
from pathlib import Path


def main() -> int:
    script = Path(__file__).resolve().with_name("test_devgodzilla_onboard.py")
    print("scripts/test_onboarding.py is deprecated. Running scripts/test_devgodzilla_onboard.py instead.")
    return subprocess.run([sys.executable, str(script)], check=False).returncode


if __name__ == "__main__":
    raise SystemExit(main())
