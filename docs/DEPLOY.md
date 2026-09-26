# Deploy (single VPS + docker-compose)

## Layout

```
bigship-ai-agent/
  agent/                 # FastAPI + LangGraph backend (mirrors frontend/)
  frontend/              # Vite + React SPA (Docker: node build → nginx serve)
  data/                  # SQLite volume (checkpoints.db, git-ignored, host-persisted)
  docs/                  # ENV.md, DEPLOY.md
  scripts/               # smoke.sh, backup.sh
  Dockerfile             # backend: uv + python:3.12-slim, uvicorn agent.service:app
  docker-compose.yml     # api + web, ./data:/data, healthchecks
```

`agent/` mirrors `frontend/` on purpose: symmetric top-level services, no
`src/` nesting, no `PYTHONPATH` hacks. Imports stay `from agent...`.

## 1. Configure

```bash
cp .env.example .env
# fill OPENROUTER_API_KEY, LLM_MODEL, JWT_SECRET, CREDENTIAL_ENCRYPTION_KEY
# set FRONTEND_ORIGIN=https://app.example.com (your domain)

# frontend build arg — same-origin default needs no change:
# VITE_API_URL= (empty → nginx proxies /auth /sessions /chat /api /health to api:8000)
# split domains: VITE_API_URL=https://api.example.com
```

See `docs/ENV.md` for the full variable table.

## 2. First data + build

```bash
mkdir -p data
docker compose build
docker compose up -d
docker compose ps
curl -fsS http://localhost:3000/ >/dev/null && echo web-ok
curl -fsS http://localhost:8000/health
```

`api` persists SQLite at `./data/checkpoints.db` (`CHECKPOINT_DB_PATH=/data/checkpoints.db`).
The backend also creates the parent dir on boot (`lifespan`), so a fresh
volume works without manual init.

## 3. Single-domain vs split-domain

- **Single domain (recommended):** point DNS at VPS, reverse-proxy `/:80 web`,
  `web` already proxies `/auth /sessions /chat /api /health` → `api:8000`.
  Set `VITE_API_URL=` (empty) at build, `FRONTEND_ORIGIN=https://app.example.com`.
- **Split domains:** `app.example.com → web:80`, `api.example.com → api:8000`.
  Build web with `VITE_API_URL=https://api.example.com`,
  set `FRONTEND_ORIGIN=https://app.example.com`.

## 4. Update

```bash
git pull
docker compose build
docker compose up -d
./scripts/smoke.sh
```

## 5. Backup

```bash
./scripts/backup.sh   # sqlite .backup → data/backups/checkpoints-<ts>.db
```

## 6. Local dev (no docker)

```bash
uv sync --group dev
cp .env.example .env  # CHECKPOINT_DB_PATH=./checkpoints.db for local
uv run uvicorn agent.service:app --port 8000
cd frontend && npm ci && npm run dev
```
