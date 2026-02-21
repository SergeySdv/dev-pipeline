#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

echo "scripts/test_e2e_real.sh is deprecated. Running scripts/test_devgodzilla_e2e.py instead."
python3 "${SCRIPT_DIR}/test_devgodzilla_e2e.py" "$@"
