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

PYTHON_BIN="${PYTHON_BIN:-python3}"
VENV_PATH="${VENV_PATH:-.venv}"
REQ_FILE="${REQ_FILE:-requirements.txt}"

if [ ! -x "${VENV_PATH}/bin/python" ]; then
  "${PYTHON_BIN}" -m venv "${VENV_PATH}"
fi

"${VENV_PATH}/bin/python" -m pip install --upgrade pip
"${VENV_PATH}/bin/pip" install -r "${REQ_FILE}" ruff

ci_info "bootstrap ready" "venv=${VENV_PATH} req=${REQ_FILE}"

report_status success
