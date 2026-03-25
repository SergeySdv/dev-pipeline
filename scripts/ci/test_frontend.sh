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

if ! command -v pnpm >/dev/null 2>&1; then
  ci_error "frontend pnpm missing" "hint=install_pnpm"
  exit 1
fi

FRONTEND_DIR="${FRONTEND_DIR:-frontend}"
if [ ! -d "${FRONTEND_DIR}" ]; then
  ci_error "frontend directory missing" "path=${FRONTEND_DIR}"
  exit 1
fi

pushd "${FRONTEND_DIR}" >/dev/null
ci_info "running frontend vitest" "scope=frontend unit=vitest"
pnpm test:run
ci_info "running frontend playwright smoke" "scope=frontend e2e=playwright"
pnpm test:e2e:smoke
popd >/dev/null

ci_info "frontend test suite completed" "result=pass"
report_status success
