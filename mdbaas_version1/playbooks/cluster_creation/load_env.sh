#!/usr/bin/env bash

# Backwards-compatible shim that delegates to the repo-root loader.

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT_DIR="$(cd "$SCRIPT_DIR/../.." && pwd)"

if [[ ! -f "$ROOT_DIR/load_env.sh" ]]; then
  echo "[cluster_creation/load_env] ERROR: Missing root load_env.sh" >&2
  exit 1
fi

source "$ROOT_DIR/load_env.sh" "$@"
