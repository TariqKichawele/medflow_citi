#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
BACKEND="$ROOT/backend"

echo "==> Creating Python virtual environment"
python3 -m venv "$BACKEND/.venv"
# shellcheck disable=SC1091
source "$BACKEND/.venv/bin/activate"
python -m pip install --upgrade pip
python -m pip install -r "$BACKEND/requirements.txt"

if [[ ! -f "$BACKEND/.env" ]]; then
  cp "$BACKEND/.env.example" "$BACKEND/.env"
  SECRET="$(python -c 'import secrets; print(secrets.token_urlsafe(48))')"
  if [[ "$(uname)" == "Darwin" ]]; then
    sed -i '' "s|^JWT_SECRET=.*|JWT_SECRET=${SECRET}|" "$BACKEND/.env"
  else
    sed -i "s|^JWT_SECRET=.*|JWT_SECRET=${SECRET}|" "$BACKEND/.env"
  fi
  echo "==> Wrote $BACKEND/.env with a generated JWT_SECRET"
else
  echo "==> Keeping existing $BACKEND/.env"
fi

echo "==> Starting Postgres"
cd "$ROOT"
docker compose up -d
echo "==> Waiting for Postgres to become healthy"
for _ in $(seq 1 30); do
  if docker compose exec -T postgres pg_isready -U medflow -d medflow >/dev/null 2>&1; then
    break
  fi
  sleep 1
done
docker compose exec -T postgres pg_isready -U medflow -d medflow

echo "==> Running migrations"
cd "$BACKEND"
alembic upgrade head

if [[ -f "$ROOT/frontend/package.json" ]]; then
  echo "==> Installing frontend packages"
  (cd "$ROOT/frontend" && npm install)
fi

echo "==> Setup complete. Start the API with:"
echo "    source backend/.venv/bin/activate && cd backend && uvicorn app.main:app --reload"
