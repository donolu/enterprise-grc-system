#!/usr/bin/env bash
set -euo pipefail

BRANCH=$(git symbolic-ref --short HEAD 2>/dev/null || true)

if [[ "$BRANCH" == "main" || -z "$BRANCH" ]]; then
  exit 0
fi

PATTERN='^(feature|fix|chore|docs)/[0-9]+-[a-z][a-z0-9-]*$'

if [[ ! "$BRANCH" =~ $PATTERN ]]; then
  echo ""
  echo "  Branch name '$BRANCH' does not match the required convention."
  echo ""
  echo "  Required format:  <type>/<issue-number>-<short-description>"
  echo ""
  echo "  Examples:"
  echo "    feature/42-add-search"
  echo "    fix/17-cart-reservation-race"
  echo "    chore/88-bump-ruff"
  echo "    docs/5-deployment-guide"
  echo ""
  echo "  Allowed types: feature, fix, chore, docs"
  echo "  The issue number must come from a GitHub Issue."
  echo ""
  exit 1
fi

exit 0
