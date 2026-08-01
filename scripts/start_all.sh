#!/usr/bin/env bash
# Single-command launch of the whole CCMS stack (no Docker).
# Postgres/Redis are managed separately as brew services; everything else
# runs under honcho, driven by the root Procfile.
set -euo pipefail
cd "$(dirname "$0")/.."

if ! brew services list | grep -q "postgresql@16.*started"; then
  echo "==> Starting Postgres"
  brew services start postgresql@16
fi
if ! brew services list | grep -q "^redis.*started"; then
  echo "==> Starting Redis"
  brew services start redis
fi

exec backend/.venv/bin/honcho start -f Procfile
