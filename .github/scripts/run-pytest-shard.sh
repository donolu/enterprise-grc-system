#!/usr/bin/env bash
set -euo pipefail

if [[ $# -lt 3 ]]; then
  echo "Usage: $0 <zero-based-shard-index> <total-shards> <pytest collection args...>" >&2
  exit 2
fi

shard_index="$1"
total_shards="$2"
shift 2

if (( shard_index < 0 || shard_index >= total_shards )); then
  echo "Shard index $shard_index must be between 0 and $((total_shards - 1))." >&2
  exit 2
fi

collection_file="$(mktemp)"
selected_file="$(mktemp)"
trap 'rm -f "$collection_file" "$selected_file"' EXIT

echo "::group::Collect backend tests"
python -m pytest --collect-only -q "$@" >"$collection_file"
python - "$collection_file" "$selected_file" "$shard_index" "$total_shards" <<'PY'
from pathlib import Path
import sys

collection_path = Path(sys.argv[1])
selected_path = Path(sys.argv[2])
shard_index = int(sys.argv[3])
total_shards = int(sys.argv[4])

nodeids = [
    line.strip()
    for line in collection_path.read_text().splitlines()
    if "::" in line and not line.startswith(("=", "<"))
]
selected = [
    nodeid
    for index, nodeid in enumerate(nodeids)
    if index % total_shards == shard_index
]

selected_path.write_text("\n".join(selected) + ("\n" if selected else ""))
print(f"Collected {len(nodeids)} tests; selected {len(selected)} for shard {shard_index + 1}/{total_shards}.")
PY
echo "::endgroup::"

mapfile -t selected_nodeids <"$selected_file"

if (( ${#selected_nodeids[@]} == 0 )); then
  echo "::error::No tests selected for shard $((shard_index + 1))/$total_shards."
  exit 1
fi

echo "::group::Selected backend tests for shard $((shard_index + 1))/$total_shards"
printf '%s\n' "${selected_nodeids[@]}"
echo "::endgroup::"

python -m pytest \
  "${selected_nodeids[@]}" \
  --cov=. \
  --cov-report=xml \
  --cov-report=term-missing \
  --cov-fail-under=0 \
  --durations=25 \
  --verbose \
  --nomigrations
