# Deployment

## Local Dev (SQLite)
```bash
# Backend
cd mark-jenny/backend
$env:PYTHONPATH="."; uvicorn app.main:app --reload --port 8000
# Frontend
cd ../frontend
npm run dev
```

## Docker (Prod Web)
```bash
cp .env.example .env  # set SECRET_KEY, DATABASE_URL
docker-compose up --build
# Frontend http://localhost:3000 → Backend http://localhost:8000 (via NEXT_PUBLIC_API_URL)
# Health: GET http://localhost:8000/health and /api/v1/docs
```

For Postgres, set `DATABASE_URL=postgresql://...` and add `postgres:15` service.

## Env Handling
- Backend: `app/core/config.py:BaseSettings` reads `.env`, `get_settings()` is `lru_cache`. Never hardcode prod secrets.
- Frontend: `NEXT_PUBLIC_*` baked at build time - rebuild after changing.

## Windows Desktop
See `docs/WINDOWS_INSTALL.md` + `frontend/src-tauri/tauri.conf.json:bundle.windows`. Build: `npm run tauri build` → `src-tauri/target/release/bundle/msi` + `nsis`.

## Production Checklist
- [ ] Set `SECRET_KEY` via env, not default `secrets.token_urlsafe`
- [ ] Use Postgres for multi-user, run `alembic upgrade head` (when migrations added)
- [ ] Set `CORS_ORIGINS` to your domain
- [ ] Put `uploads/` on persistent volume
- [ ] Enable HTTPS, set `secure` cookie via `settings.DEBUG=False`
