#!/usr/bin/env bash
# Start Postgres, ensure venv + deps, run migrations. Does not start API/frontend.
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"

if [[ ! -f .env ]]; then
  cp .env.example .env
  echo "Created .env from .env.example — fill in Google/LLM keys when ready."
fi

if [[ ! -d .venv ]]; then
  python3 -m venv .venv
  echo "Created .venv"
fi
# shellcheck disable=SC1091
source .venv/bin/activate
# CPU torch first — default CUDA wheels are multi-GB and blow disk/CI
pip install -q torch --index-url https://download.pytorch.org/whl/cpu
pip install -q -r requirements.txt

docker compose up -d

echo "Waiting for Postgres on :5433..."
for i in $(seq 1 30); do
  if docker compose exec -T postgres pg_isready -U postgres >/dev/null 2>&1; then
    break
  fi
  sleep 1
done
docker compose exec -T postgres pg_isready -U postgres

alembic upgrade head

echo ""
echo "DB ready. Next:"
echo "  source .venv/bin/activate && uvicorn app.main:app --reload --host 0.0.0.0 --port 8000"
echo "  cd frontend && npm install && npm run dev"
