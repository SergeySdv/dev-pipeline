#!/usr/bin/env python3
"""Compatibility launcher for the TUI.

DevGodzilla no longer ships the old Python Textual TUI module.
This wrapper delegates to the Rust TUI launcher.
"""

import subprocess
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

if __name__ == "__main__":
    launcher = PROJECT_ROOT / "scripts" / "tui-rs"
    raise SystemExit(subprocess.call([str(launcher), *sys.argv[1:]]))
