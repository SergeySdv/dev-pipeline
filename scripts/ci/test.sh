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

export PYTHONPATH="${PYTHONPATH:-.}"
export DEKSDENFLOW_DB_PATH="${DEKSDENFLOW_DB_PATH:-/tmp/deksdenflow-test.sqlite}"
export DEKSDENFLOW_REDIS_URL="${DEKSDENFLOW_REDIS_URL:-fakeredis://}"

"${PYTEST_BIN}" -q --disable-warnings --maxfail=1

ci_info "tests completed" "result=pass"
report_status success
