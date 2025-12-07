#!/usr/bin/env bash
# Lightweight structured-ish logging for CI shell helpers so messages are consistent.

ci_log() {
  local level="$1"; shift
  local message="$1"; shift
  local ts
  ts="$(date -Iseconds 2>/dev/null || date +"%Y-%m-%dT%H:%M:%S")"
  local context=""
  if [ "$#" -gt 0 ]; then
    context="$*"
  fi
  local payload
  if [ -n "$context" ]; then
    payload=$(printf '{"ts":"%s","level":"%s","component":"ci","message":"%s","context":"%s"}\n' "$ts" "$level" "$message" "$context")
  else
    payload=$(printf '{"ts":"%s","level":"%s","component":"ci","message":"%s"}\n' "$ts" "$level" "$message")
  fi
  if [ "$level" = "warn" ] || [ "$level" = "error" ]; then
    printf "%s" "$payload" >&2
  else
    printf "%s" "$payload"
  fi
}

ci_info() { ci_log "info" "$@"; }
ci_warn() { ci_log "warn" "$@"; }
ci_error() { ci_log "error" "$@"; }
