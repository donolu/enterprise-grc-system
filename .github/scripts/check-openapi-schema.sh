#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
SCHEMA_FILE="$ROOT_DIR/app/schema.yml"
GENERATED_SCHEMA="$(mktemp)"
DIAGNOSTICS_LOG="$(mktemp)"

cleanup() {
  rm -f "$GENERATED_SCHEMA" "$DIAGNOSTICS_LOG"
}
trap cleanup EXIT

cd "$ROOT_DIR"
export PYTHONPATH="$ROOT_DIR/app${PYTHONPATH:+:$PYTHONPATH}"

if ! python manage.py spectacular --file "$GENERATED_SCHEMA" >"$DIAGNOSTICS_LOG" 2>&1; then
  cat "$DIAGNOSTICS_LOG"
  exit 1
fi

if ! python - "$SCHEMA_FILE" "$GENERATED_SCHEMA" <<'PY'; then
from pathlib import Path
import sys

import yaml

committed_path = Path(sys.argv[1])
generated_path = Path(sys.argv[2])

with committed_path.open() as committed_file:
    committed = yaml.safe_load(committed_file)
with generated_path.open() as generated_file:
    generated = yaml.safe_load(generated_file)

if committed != generated:
    sys.exit(1)
PY
  echo "::error::Committed OpenAPI schema is stale. Run 'python manage.py spectacular --file app/schema.yml' and commit the result."
  exit 1
fi

warnings="$(awk '/^Warnings:/{print $2}' "$DIAGNOSTICS_LOG" | tail -1)"
errors="$(awk '/^Errors:/{print $2}' "$DIAGNOSTICS_LOG" | tail -1)"
warnings="${warnings:-0}"
errors="${errors:-0}"

# Baseline current drf-spectacular diagnostics so new schema noise is caught.
# Future cleanup should lower these ceilings until both reach zero.
max_warnings="${OPENAPI_MAX_WARNINGS:-196}"
max_errors="${OPENAPI_MAX_ERRORS:-167}"

if (( warnings > max_warnings )); then
  cat "$DIAGNOSTICS_LOG"
  echo "::error::OpenAPI warnings increased from the baseline of $max_warnings to $warnings."
  exit 1
fi

if (( errors > max_errors )); then
  cat "$DIAGNOSTICS_LOG"
  echo "::error::OpenAPI errors increased from the baseline of $max_errors to $errors."
  exit 1
fi

echo "OpenAPI schema is current."
echo "drf-spectacular diagnostics: $warnings warnings, $errors errors. Baseline ceilings: $max_warnings warnings, $max_errors errors."
