#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
PYTHON_BIN="${PYTHON_BIN:-python}"

"$PYTHON_BIN" "$SCRIPT_DIR/review_artifact.py" --repo-root "$REPO_ROOT" "$@"
