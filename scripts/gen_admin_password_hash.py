#!/usr/bin/env python3
"""
Generate a pbkdf2_sha256 password hash for `DEVGODZILLA_ADMIN_PASSWORD_HASH`.

Usage:
  python scripts/gen_admin_password_hash.py
  python scripts/gen_admin_password_hash.py --password "secret"
  python scripts/gen_admin_password_hash.py --iterations 210000
"""

import argparse
import base64
import getpass
import hashlib
import os


def hash_pbkdf2_sha256(password: str, *, iterations: int = 210_000, salt_bytes: int = 16) -> str:
    salt = os.urandom(salt_bytes)
    digest = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt, iterations)
    return "pbkdf2_sha256$%d$%s$%s" % (
        iterations,
        base64.urlsafe_b64encode(salt).decode("ascii").rstrip("="),
        base64.urlsafe_b64encode(digest).decode("ascii").rstrip("="),
    )


def main() -> None:
    parser = argparse.ArgumentParser(description="Generate admin password hash for DevGodzilla (pbkdf2_sha256).")
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
