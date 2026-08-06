#!/usr/bin/env bash
# Production-style start (no --reload). --reload on NTFS burns CPU.
set -euo pipefail
cd "$(dirname "$0")"
# shellcheck disable=SC1091
source .venv/bin/activate
# Optional: set STUDY_DB_PATH to move the central SQLite database.
exec uvicorn server:app --host 0.0.0.0 --port 8765
