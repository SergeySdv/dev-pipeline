#!/usr/bin/env bash
set -euo pipefail

# Usage: scripts/ci/report.sh [status]
# status defaults to "success" and is sent to the orchestrator webhook for the configured provider.

STATUS="${1:-success}"
PROVIDER="$(echo "${DEKSDENFLOW_CI_PROVIDER:-github}" | tr '[:upper:]' '[:lower:]')"
API_BASE="${DEKSDENFLOW_API_BASE:-}"
PROTOCOL_RUN_ID="${DEKSDENFLOW_PROTOCOL_RUN_ID:-}"

if [ -z "$API_BASE" ]; then
  echo "[deksdenflow] DEKSDENFLOW_API_BASE not set; skipping orchestrator webhook report." >&2
  exit 0
fi

if ! command -v curl >/dev/null 2>&1; then
  echo "[deksdenflow] curl not available; skipping orchestrator webhook report." >&2
  exit 0
fi

BRANCH="${DEKSDENFLOW_BRANCH:-${CI_COMMIT_REF_NAME:-${GITHUB_HEAD_REF:-${GITHUB_REF_NAME:-}}}}"
if [ -z "$BRANCH" ] && command -v git >/dev/null 2>&1; then
  BRANCH="$(git rev-parse --abbrev-ref HEAD 2>/dev/null || echo "")"
fi
BRANCH="${BRANCH:-unknown}"

TARGET_URL="${DEKSDENFLOW_TARGET_URL:-${CI_JOB_URL:-${GITHUB_SERVER_URL:-}}}"

AUTH_HEADER=()
if [ -n "${DEKSDENFLOW_API_TOKEN:-}" ]; then
  AUTH_HEADER+=("-H" "Authorization: Bearer ${DEKSDENFLOW_API_TOKEN}")
fi

send_github() {
  local url payload sig
  url="${API_BASE%/}/webhooks/github"
  if [ -n "$PROTOCOL_RUN_ID" ]; then
    url="${url}?protocol_run_id=${PROTOCOL_RUN_ID}"
  fi
  payload=$(cat <<EOF
{"state":"${STATUS}","branches":[{"name":"${BRANCH}"}],"target_url":"${TARGET_URL:-}","ref":"${BRANCH}"}
EOF
)
  SIG_HEADER=()
  if [ -n "${DEKSDENFLOW_WEBHOOK_TOKEN:-}" ]; then
    if command -v openssl >/dev/null 2>&1; then
      sig="$(printf '%s' "$payload" | openssl dgst -sha256 -hmac "$DEKSDENFLOW_WEBHOOK_TOKEN" | awk '{print $NF}')"
      SIG_HEADER=("-H" "X-Hub-Signature-256: sha256=${sig}")
    else
      echo "[deksdenflow] openssl missing; sending GitHub-style webhook without signature." >&2
    fi
  fi
  curl -sS -X POST "$url" \
    -H "Content-Type: application/json" \
    -H "X-GitHub-Event: status" \
    "${AUTH_HEADER[@]}" \
    "${SIG_HEADER[@]}" \
    -d "$payload" >/dev/null 2>&1 || \
    echo "[deksdenflow] Failed to notify orchestrator (GitHub hook)." >&2
}

send_gitlab() {
  local url payload
  url="${API_BASE%/}/webhooks/gitlab"
  if [ -n "$PROTOCOL_RUN_ID" ]; then
    url="${url}?protocol_run_id=${PROTOCOL_RUN_ID}"
  fi
  payload=$(cat <<EOF
{"object_kind":"pipeline","object_attributes":{"status":"${STATUS}","ref":"${BRANCH}"}}
EOF
)
  TOKEN_HEADER=()
  if [ -n "${DEKSDENFLOW_WEBHOOK_TOKEN:-}" ]; then
    TOKEN_HEADER=("-H" "X-Gitlab-Token: ${DEKSDENFLOW_WEBHOOK_TOKEN}")
  fi
  curl -sS -X POST "$url" \
    -H "Content-Type: application/json" \
    -H "X-Gitlab-Event: Pipeline Hook" \
    "${TOKEN_HEADER[@]}" \
    "${AUTH_HEADER[@]}" \
    -d "$payload" >/dev/null 2>&1 || \
    echo "[deksdenflow] Failed to notify orchestrator (GitLab hook)." >&2
}

case "$PROVIDER" in
  github) send_github ;;
  gitlab) send_gitlab ;;
  *)
    echo "[deksdenflow] Unknown DEKSDENFLOW_CI_PROVIDER=${PROVIDER}; supported: github, gitlab." >&2
    ;;
esac
