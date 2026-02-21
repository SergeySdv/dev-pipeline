#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "${SCRIPT_DIR}/../.." && pwd)"

VENV_PATH="${VENV_PATH:-${REPO_ROOT}/.venv}"
PYTEST_BIN="${PYTEST_BIN:-${VENV_PATH}/bin/pytest}"

if [[ ! -x "${PYTEST_BIN}" ]]; then
  echo "error: pytest not found at ${PYTEST_BIN}. Run scripts/ci/bootstrap.sh first." >&2
  exit 1
fi

export DEVGODZILLA_RUN_E2E_HARNESS="${DEVGODZILLA_RUN_E2E_HARNESS:-1}"
export HARNESS_GITHUB_OWNER="${HARNESS_GITHUB_OWNER:-ilyafedotov-ops}"
export HARNESS_GITHUB_REPOS="${HARNESS_GITHUB_REPOS:-test-glm5-demo,SimpleAdminReporter,demo-spring}"
export HARNESS_CONTINUE_ON_ERROR="${HARNESS_CONTINUE_ON_ERROR:-1}"
export HARNESS_ONBOARD_MODE="${HARNESS_ONBOARD_MODE:-windmill}"
export HARNESS_STEP_ENGINE="${HARNESS_STEP_ENGINE:-opencode}"
if [[ -z "${DEVGODZILLA_DB_URL:-}" && -z "${DEVGODZILLA_DB_PATH:-}" ]]; then
  export DEVGODZILLA_DB_URL="postgresql://devgodzilla:changeme@localhost:5432/devgodzilla_db"
fi

cd "${REPO_ROOT}"
"${PYTEST_BIN}" -q -m integration tests/e2e/test_workflow_harness_live.py
