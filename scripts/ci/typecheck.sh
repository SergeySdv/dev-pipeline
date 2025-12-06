#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
report_status() {
  if [ -x "${SCRIPT_DIR}/report.sh" ]; then
    "${SCRIPT_DIR}/report.sh" "$1" || true
  fi
}
trap 'report_status failure' ERR

echo "[ci] typecheck: no commands defined yet. Replace with your typechecker (tsc --noEmit / mypy . / pyright / go vet ./...)."

report_status success
