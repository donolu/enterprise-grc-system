#!/usr/bin/env bash
set -euo pipefail

REPOSITORY_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
FRONTEND_DIR="$REPOSITORY_ROOT/frontend"

if [[ ! -x "$FRONTEND_DIR/node_modules/.bin/eslint" ]]; then
  echo "Frontend dependencies are not installed. Run: (cd frontend && npm ci)" >&2
  exit 1
fi

cd "$FRONTEND_DIR"
npm run lint
npm run type-check
npm run test:unit
