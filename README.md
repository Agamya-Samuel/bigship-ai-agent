# Bigship AI Agent

FastAPI microservice that exposes a LangGraph + LangChain agent for the Bigship dashboard. The agent uses the `bigship-sdk` to call Bigship API methods step-by-step, with per-chat-session memory via `SqliteSaver`.

## Setup

```bash
pip install -e /run/media/agamya/Storage/BigShip/bigship-sdk-python
uv sync --group dev
```

## Run

```bash
OPENROUTER_API_KEY=... uv run uvicorn src.agent.main:app --port 8000
```

## Environment

| Variable | Default | Description |
|---|---|---|
| `OPENROUTER_API_KEY` | (required) | OpenRouter API key |
| `CREDENTIAL_ENCRYPTION_KEY` | (required) | Fernet key for encrypting stored merchant credentials |
| `LLM_MODEL` | `openai/gpt-4o` | Model to use |
| `AGENT_PORT` | `8000` | Port for the FastAPI service |
| `CHECKPOINT_DB_PATH` | `./checkpoints.db` | SQLite checkpoint database path |
| `MAX_TOOL_CALLS` | `10` | Max recursive tool calls per turn |

## API

| Method | Path | Body | Description |
|---|---|---|---|
| POST | `/session/create` | `{thread_id, user_name, password, access_key}` | Create a merchant session |
| POST | `/session/end` | `{thread_id}` | End a merchant session |
| POST | `/chat` | `{thread_id, message}` | Send a chat message |
| GET | `/health` | — | Liveness check |
