#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"

TARGETS=(
  "${ROOT_DIR}/devgodzilla"
  "${ROOT_DIR}/windmill/flows/devgodzilla"
  "${ROOT_DIR}/windmill/scripts/devgodzilla"
  "${ROOT_DIR}/docker-compose.yml"
  "${ROOT_DIR}/docker-compose.devgodzilla.yml"
  "${ROOT_DIR}/nginx.devgodzilla.conf"
)

PATTERNS=(
  'TASKSGODZILLA_'
  'tgz_emit_refs'
  'emit_tasksgodzilla_codex_refs'
  '_tasksgodzilla_api'
  'tasksgodzilla-api'
)

if ! command -v rg >/dev/null 2>&1; then
  echo "devgodzilla-standalone-guard: rg not found (install ripgrep)" >&2
  exit 1
fi

fail=0
for pat in "${PATTERNS[@]}"; do
  if rg -n --hidden --glob '!.git/**' "${pat}" "${TARGETS[@]}" >/dev/null; then
    echo "devgodzilla-standalone-guard: found forbidden reference matching: ${pat}" >&2
    rg -n --hidden --glob '!.git/**' "${pat}" "${TARGETS[@]}" >&2 || true
    fail=1
  fi
done

if [ "${fail}" -ne 0 ]; then
  echo "devgodzilla-standalone-guard: FAIL (DevGodzilla runtime must not depend on legacy TasksGodzilla)" >&2
  exit 1
fi

echo "devgodzilla-standalone-guard: OK"
