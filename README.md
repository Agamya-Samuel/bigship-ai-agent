# Bigship AI Agent

FastAPI microservice that exposes a LangGraph + LangChain agent for the Bigship dashboard. The agent uses the `bigship-sdk` to call Bigship API methods step-by-step, with per-chat-session memory via `SqliteSaver` and encrypted credential storage via `EncryptedCredentialStore`.

## Architecture

```
Bigship Dashboard  →  HTTP  →  Agent Service (FastAPI + LangGraph)
                                           │
                                    SqliteSaver (per-thread memory)
                                    EncryptedCredentialStore (encrypted at-rest)
                                           │
                                    bigship-sdk (individual method calls)
                                           │
                                    Bigship Unified Outbound API
```

## Setup

```bash
# Install the Bigship SDK in editable mode
pip install -e /run/media/agamya/Storage/BigShip/bigship-sdk-python

# Install project dependencies
uv sync --group dev
```

## Environment

| Variable | Default | Description |
|---|---|---|
| `OPENROUTER_API_KEY` | (required) | OpenRouter API key |
| `LLM_MODEL` | (required) | Model to use via OpenRouter |
| `AGENT_PORT` | `8000` | Port for the FastAPI service |
| `CHECKPOINT_DB_PATH` | `./checkpoints.db` | SQLite checkpoint database path |
| `MAX_TOOL_CALLS` | `10` | Max recursive tool calls per turn |
| `AGENT_SERVICE_API_KEY` | (optional) | Service-level API key; when set, all endpoints require `X-Service-Api-Key` |
| `CREDENTIAL_ENCRYPTION_KEY` | (required) | Base64-encoded 32-byte Fernet key for encrypting stored merchant credentials |

## Run

```bash
OPENROUTER_API_KEY=... \
CREDENTIAL_ENCRYPTION_KEY=... \
uv run uvicorn src.agent.main:app --port 8000
```

## API

All endpoints require the header `X-Service-Api-Key` when `AGENT_SERVICE_API_KEY` is configured.

| Method | Path | Body | Description |
|---|---|---|---|
| POST | `/account/session` | `{thread_id, user_name, password, access_key}` | Create or update a merchant account and start a chat session |
| POST | `/session/end` | `{thread_id}` | End a merchant session and evict cached credentials |
| POST | `/chat` | `{thread_id, message}` | Send a chat message; returns the agent's response |
| GET | `/health` | — | Liveness check |

## Agent Tools

The agent exposes 15 tools derived from the Bigship SDK:

- `get_profile` — merchant profile and wallet balance
- `save_warehouse` — create a new warehouse
- `get_warehouse_list` — list warehouses with pagination
- `update_warehouse` — update an existing warehouse
- `get_package_types` — available package types
- `get_payment_modes` — available payment modes by segment
- `get_risk_types` — available risk types
- `calculate_rate` — calculate shipping rates
- `create_order` — create a shipment order
- `get_serviceable_couriers` — list couriers for an order
- `place_order` — confirm an order with a courier
- `cancel_order` — cancel an order
- `track_order` — track an order
- `get_order_detail` — get detailed order information
- `download_document` — download invoice, label, ewaybill, or manifest

## Development

```bash
# Run tests
uv run pytest tests/ -v

# Lint
uv run ruff check src/

# Typecheck
uv run mypy src/
```

## Security

- Merchant credentials are encrypted at rest using Fernet symmetric encryption.
- Passwords are hashed with bcrypt before storage.
- The service API key guard prevents unauthorized access to the agent endpoints.
- LLM exception details are not exposed to clients; internal errors are logged server-side only.
