#!/usr/bin/env bash
# One-time local environment setup for CCMS. Safe to re-run.
set -euo pipefail
cd "$(dirname "$0")/.."

echo "==> Installing system dependencies via Homebrew"
brew list postgresql@16 &>/dev/null || brew install postgresql@16
brew list redis &>/dev/null || brew install redis
brew list ffmpeg &>/dev/null || brew install ffmpeg
brew list mediamtx &>/dev/null || brew install mediamtx
brew list mailpit &>/dev/null || brew install mailpit

echo "==> Starting Postgres and Redis as background services"
brew services start postgresql@16
brew services start redis

echo "==> Waiting for Postgres to accept connections"
PG_BIN="$(brew --prefix postgresql@16)/bin"
for i in $(seq 1 30); do
  if "$PG_BIN/pg_isready" -q; then break; fi
  sleep 1
done

echo "==> Creating ccms database (if not present)"
"$PG_BIN/createdb" ccms 2>/dev/null || echo "   (already exists)"

echo "==> Creating backend virtualenv"
if [ ! -d backend/.venv ]; then
  /opt/homebrew/bin/python3.12 -m venv backend/.venv
fi
backend/.venv/bin/pip install --upgrade pip -q
backend/.venv/bin/pip install -e "backend[dev]" -q

echo "==> Copying .env.example to .env (if not present)"
[ -f .env ] || cp .env.example .env

echo "==> Running database migrations"
(cd backend && ../backend/.venv/bin/alembic upgrade head)

echo "==> Seeding admin user"
backend/.venv/bin/python scripts/seed_admin_user.py

echo "==> Installing simulator package"
backend/.venv/bin/pip install -e simulator -q

echo "==> Installing frontend dependencies"
(cd frontend && npm install --silent)

echo ""
echo "Bootstrap complete. Run ./scripts/start_all.sh to launch CCMS."
