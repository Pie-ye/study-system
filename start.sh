#!/usr/bin/env bash
# Local/dev start (no --reload). Production prefers Docker — see deploy/DOCKER.md.
set -euo pipefail
cd "$(dirname "$0")"
# shellcheck disable=SC1091
source .venv/bin/activate
# Optional: set STUDY_DB_PATH / VAULT_ROOT / CLIPROXY_BASE for path abstraction.
exec uvicorn server:app --host 0.0.0.0 --port 8765
