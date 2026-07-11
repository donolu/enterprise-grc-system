#!/usr/bin/env bash
set -euo pipefail

MYPY_BIN=""
for candidate in ".venv/bin/mypy" "venv/bin/mypy"; do
  if [[ -x "$candidate" ]]; then
    MYPY_BIN="$PWD/$candidate"
    break
  fi
done

if [[ -z "$MYPY_BIN" ]]; then
  if command -v mypy >/dev/null 2>&1; then
    MYPY_BIN="$(command -v mypy)"
  else
    echo "mypy not found; skipping type check locally (CI will verify)"
    echo "To set up: pip install -r requirements.txt"
    exit 0
  fi
fi

export DJANGO_SETTINGS_MODULE=app.settings.test
export SECRET_KEY=ci-mypy-check
export DATABASE_URL=postgres://localhost/mypy_check
export CELERY_BROKER_URL=redis://localhost/0
export CELERY_RESULT_BACKEND=redis://localhost/1

"$MYPY_BIN" app/
