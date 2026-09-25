# Environment Variables

All secrets via `/.env` (never hardcode). See `.env.example`.

| Variable | Default | Description |
|---|---|---|
| `DATABASE_URL` | `sqlite:///./mark_imti.db` | SQLite file or `postgresql://user:pass@host:5432/db` for prod |
| `SECRET_KEY` | `secrets.token_urlsafe(32)` | JWT signing - **must** set in prod via env |
| `ACCESS_TOKEN_EXPIRE_MINUTES` | `30` | Access token TTL |
| `REFRESH_TOKEN_EXPIRE_DAYS` | `7` | Refresh cookie TTL |
| `CORS_ORIGINS` | `["http://localhost:3000"]` | JSON array for FastAPI CORS |
| `UPLOAD_DIR` | `./uploads` | File storage root (also exec_sandbox, browser_sessions, snapshots) |
| `MAX_FILE_SIZE` | `104857600` | 100MB upload limit |
| `OLLAMA_BASE_URL` | `http://localhost:11434` | Local inference |
| `NEXT_PUBLIC_API_URL` | `http://localhost:8000/api/v1` | Frontend → Backend |
| `NEXT_PUBLIC_WS_URL` | `ws://localhost:8000/api/v1/ws` | WebSocket |
| `REDIS_URL` | *(none)* | Optional for multi-process/cloud task queue |

Generate `SECRET_KEY`: `python -c "import secrets; print(secrets.token_urlsafe(32))"`
