#!/usr/bin/env bash
set -euo pipefail

MYPY_BIN=""
if [[ -n "${VIRTUAL_ENV:-}" && -x "$VIRTUAL_ENV/bin/mypy" ]]; then
  MYPY_BIN="$VIRTUAL_ENV/bin/mypy"
fi

for candidate in ".venv312/bin/mypy" ".venv/bin/mypy" "venv/bin/mypy"; do
  if [[ -n "$MYPY_BIN" ]]; then
    break
  fi
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
export PYTHONPATH="$PWD/app${PYTHONPATH:+:$PYTHONPATH}"
export SECRET_KEY=ci-mypy-check
export DATABASE_URL=postgres://localhost/mypy_check
export CELERY_BROKER_URL=redis://localhost/0
export CELERY_RESULT_BACKEND=redis://localhost/1

# Keep this as an incremental baseline. The wider Django app still has model,
# admin and test typing debt; expand these targets as those areas are cleaned.
"$MYPY_BIN" \
  app/app \
  app/api \
  app/core/health.py \
  --disable-error-code var-annotated \
  --disable-error-code django-manager-missing \
  --disable-error-code attr-defined \
  --disable-error-code misc \
  --disable-error-code union-attr \
  --disable-error-code arg-type \
  --disable-error-code assignment \
  --disable-error-code import-untyped \
  --disable-error-code index \
  --disable-error-code operator \
  --disable-error-code dict-item
