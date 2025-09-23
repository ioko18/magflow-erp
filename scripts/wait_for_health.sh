#!/usr/bin/env bash
set -euo pipefail

HOST="${1:-http://localhost:8000}"
PATH_HEALTH="${2:-/health}"
TIMEOUT_SECONDS="${3:-60}"
SLEEP_SECONDS="${4:-2}"

end_time=$(( $(date +%s) + TIMEOUT_SECONDS ))
echo "Waiting for ${HOST}${PATH_HEALTH} for up to ${TIMEOUT_SECONDS}s ..."

while true; do
  if curl -fsS "${HOST}${PATH_HEALTH}" >/dev/null; then
    echo "Service healthy at ${HOST}${PATH_HEALTH}"
    exit 0
  fi
  if [ $(date +%s) -ge ${end_time} ]; then
    echo "ERROR: Timed out waiting for ${HOST}${PATH_HEALTH}" >&2
    exit 1
  fi
  sleep "${SLEEP_SECONDS}"
done
