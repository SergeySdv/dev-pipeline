#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

echo "scripts/test_workflow_simple.sh is deprecated. Running scripts/test_devgodzilla.sh instead."
"${SCRIPT_DIR}/test_devgodzilla.sh" "$@"
