#!/usr/bin/env bash
set -euo pipefail

# One-command runner: sync deps, fetch data, build outputs, launch Streamlit UI

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT_DIR"

if ! command -v uv >/dev/null 2>&1; then
  echo "uv is required. Install via: pip install uv" >&2
  exit 1
fi

# Sync dependencies (no-dev to keep runtime lean)
uv sync

# Build analytics outputs
uv run python -m macro_platform.viz.report

# Launch Streamlit UI
exec uv run streamlit run src/macro_platform/ui/app.py

