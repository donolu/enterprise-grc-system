#!/usr/bin/env bash
set -euo pipefail

wait_for() {
  local name="$1"
  local command="$2"
  local delay="${3:-2}"
  local attempts="${4:-30}"

  for attempt in $(seq 1 "$attempts"); do
    if eval "$command" >/dev/null 2>&1; then
      echo "$name is ready."
      return 0
    fi
    echo "Waiting for $name... ($attempt/$attempts)"
    sleep "$delay"
  done

  echo "::error::$name did not become ready in time."
  return 1
}

wait_for "PostgreSQL" "pg_isready -h localhost -p 5432 -U grc"
wait_for "Redis" "redis-cli -h localhost -p 6379 ping"
wait_for "Azurite" "(echo > /dev/tcp/127.0.0.1/10000)" 3 20
