#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
source "${SCRIPT_DIR}/logging.sh"
report_status() {
  if [ -x "${SCRIPT_DIR}/report.sh" ]; then
    "${SCRIPT_DIR}/report.sh" "$1" || true
  fi
}
trap 'report_status failure' ERR

VENV_PATH="${VENV_PATH:-.venv}"
PYTEST_BIN="${PYTEST_BIN:-${VENV_PATH}/bin/pytest}"

if [ ! -x "${PYTEST_BIN}" ]; then
  ci_error "test pytest missing" "pytest_bin=${PYTEST_BIN} hint=run_bootstrap"
  exit 1
fi

if [ "${DEVGODZILLA_RUN_E2E:-}" != "1" ]; then
  ci_warn "e2e skipped" "reason=missing_env DEVGODZILLA_RUN_E2E=1"
  exit 0
fi

if ! command -v git >/dev/null 2>&1; then
  ci_error "e2e git missing"
  exit 1
fi

export PYTHONPATH="${PYTHONPATH:-.}"

"${PYTEST_BIN}" -q --disable-warnings --maxfail=1 tests/test_devgodzilla_cli_e2e_real_repo.py

ci_info "e2e completed" "result=pass"
report_status success

