# Environment variables

Backend reads `.env` via `agent/config.py` (pydantic-settings). Frontend bakes
`VITE_API_URL` at build time — rebuild the `web` image after changing it.

## Backend (`.env`)

| Variable | Required | Default | Notes |
|---|---|---|---|
| `OPENROUTER_API_KEY` | yes | — | OpenRouter API key |
| `LLM_MODEL` | yes | — | e.g. `openrouter/free` |
| `JWT_SECRET` | yes | — | HS256 signing secret, long random string |
| `CREDENTIAL_ENCRYPTION_KEY` | yes | — | Base64 32-byte Fernet key (`python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"`) |
| `FRONTEND_ORIGIN` | deploy | `http://localhost:5173` | Comma-separated CORS origins. Prod: `https://app.example.com` (single-domain) or `https://app.example.com,https://admin.example.com` |
| `CHECKPOINT_DB_PATH` | no | `/data/checkpoints.db` | Compose mounts `./data:/data`. Local default override: `./checkpoints.db` via `.env` |
| `AGENT_PORT` | no | `8000` | Also used as compose host port `${AGENT_PORT:-8000}` |
| `MAX_TOOL_CALLS` | no | `10` | Recursion budget = `MAX_TOOL_CALLS*3+3` supersteps |
| `JWT_EXPIRY_MINUTES` | no | `1440` | Login token TTL |

## Frontend (`frontend/.env` / build arg)

| Variable | Default | Notes |
|---|---|---|
| `VITE_API_URL` | `""` (same-origin) | Local: `http://localhost:8000`. Prod same-origin (nginx proxy): empty. Split domains: `https://api.example.com` |
| `WEB_PORT` (compose only) | `3000` | Host port for `web` service |
| `VITE_API_URL` (compose only) | `""` | Passed as docker build arg to `web` |

## Generating secrets

```bash
python -c "import secrets; print(secrets.token_urlsafe(48))"  # JWT_SECRET
python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"  # CREDENTIAL_ENCRYPTION_KEY
```
