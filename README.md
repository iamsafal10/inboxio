# Inboxio

Personal Gmail intelligence agent: sync career emails, RAG chat via LangGraph, profile memory, and gated cold-email drafts.

## Stack

| Piece | Port | How it runs |
|-------|------|-------------|
| Postgres | **5433** (host) → 5432 in container | `docker compose up -d` |
| FastAPI backend | **8000** | `uvicorn app.main:app --reload --port 8000` |
| Next.js frontend | **3000** | `cd frontend && npm run dev` |
| Chroma vectors | `./chroma_data` | created on first embed |

Frontend proxies `/auth`, `/gmail`, `/api`, `/cold_email`, `/baseline` to `http://127.0.0.1:8000`.

## Quick start

```bash
# 1. Env
cp .env.example .env
# Edit .env: set APP_SECRET_KEY, Google OAuth, and at least one LLM key

# 2. Postgres + migrate (also creates .venv; installs CPU torch then deps)
./scripts/dev.sh

# 3. Backend (separate terminal)
source .venv/bin/activate
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000

# 4. Frontend (separate terminal)
cd frontend && npm install && npm run dev
```

Open [http://localhost:3000](http://localhost:3000). API health: [http://localhost:8000/](http://localhost:8000/).

Legacy HTML UIs (same backend): `/chat-ui`, `/profile/ui`, `/cold_email/ui`.

## After signup

1. Connect Gmail (`/gmail/oauth/connect`)
2. `POST /gmail/sync` → `/gmail/chunk` → `/gmail/embed`
3. Chat or cold-email from the UI

## Env

See [`.env.example`](.env.example). Required for full features:

- `DATABASE_URL` — defaults to localhost **5433** (avoids clashing with other local Postgres on 5432)
- `GOOGLE_CLIENT_ID` / `GOOGLE_CLIENT_SECRET` / `GOOGLE_REDIRECT_URI=http://localhost:8000/gmail/oauth/callback`
- `LLM_PROVIDER` + matching key (`gemini` / `groq` / `openrouter_ox_alpha`)

## Layout

- `app/` — FastAPI, agent, Gmail services
- `frontend/` — Next.js UI
- `alembic/` — migrations
- `tests/` — pytest suite
- `eval/` — locked eval questions
- `scratch/` — one-off debug scripts (not product code)
- `flow.md` / `decisions.md` — architecture notes

## Deploy

Backend + managed Postgres: [`render.yaml`](render.yaml). Chroma on Render free tier is ephemeral.
