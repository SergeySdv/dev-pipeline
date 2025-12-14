#!/usr/bin/env python3
"""
Generate a pbkdf2_sha256 password hash for TASKSGODZILLA_ADMIN_PASSWORD_HASH.

Usage:
  python scripts/gen_admin_password_hash.py
  python scripts/gen_admin_password_hash.py --password "secret"
  python scripts/gen_admin_password_hash.py --iterations 210000
"""

import argparse
import getpass
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from tasksgodzilla.auth.passwords import hash_pbkdf2_sha256  # noqa: E402


def main() -> None:
    parser = argparse.ArgumentParser(description="Generate admin password hash for TasksGodzilla (pbkdf2_sha256).")
    parser.add_argument("--password", help="Password (if omitted, will prompt).", default=None)
    parser.add_argument("--iterations", type=int, default=210_000, help="PBKDF2 iterations (default: 210000).")
    args = parser.parse_args()

    pwd = args.password
    if pwd is None:
        pwd = getpass.getpass("Admin password: ")
        confirm = getpass.getpass("Confirm password: ")
        if pwd != confirm:
            raise SystemExit("Passwords do not match.")
    if not pwd:
        raise SystemExit("Password cannot be empty.")

    print(hash_pbkdf2_sha256(pwd, iterations=args.iterations))


if __name__ == "__main__":
    main()

