# MARK JENNY — Autonomous AI Operating Platform

Production-ready autonomous AI agent platform: Windows desktop + Web, shared business logic, 23 routes, 34 tables.

## Quick Start

```bash
# Backend (FastAPI + SQLite)
cd mark-jenny/backend
python -m venv venv
venv\Scripts\activate
pip install -r requirements.txt
# pip install -r requirements-dev.txt  # for tests
$env:PYTHONPATH="."  # PowerShell
python app/db/init_db.py
uvicorn app.main:app --reload --port 8000  # docs at /api/v1/docs

# Frontend (Next.js 16)
cd ../frontend
npm install
npm run dev  # http://localhost:3000  (use --webpack on Windows)
npm run build -- --webpack  # production check
```

Create first user: `POST /api/v1/auth/register` then login.

## Architecture

- **Frontend:** Next.js 16 App Router + React 19 + TypeScript + Tailwind + shadcn/ui (@base-ui) + next-themes
- **Backend:** FastAPI + SQLAlchemy 2 + SQLite (Postgres ready) + JWT (bcrypt) + WebSocket
- **Routes:** 19 frontend (`/`, `/chat`, `/quick-actions`, `/scheduled`, `/knowledge`, `/memory`, `/browser`, `/computer`, `/execution`, `/ai`, `/generate`, `/settings`, `/admin`, `/skills`, `/connectors`, `/blueprints`, `/advanced`, `/advanced-features`... + `/projects/[id]`)
- **API:** 15 routers (`/api/v1/auth|users|projects|tasks|files|schedules|ws|chats|quick-actions|knowledge|memories|skills|browser|computer|execution|ai|generate|settings|admin|advanced`)

See `docs/ARCHITECTURE.md`, `docs/DATABASE_SCHEMA.md`, `docs/ENV_VARS.md`, `docs/DEPLOYMENT.md`.

## Windows Desktop

Built with Tauri/Electron wrapper over Next.js + FastAPI sidecar. See `docs/WINDOWS_INSTALL.md` and `frontend/tauri.conf.json`. Installs to Start Menu/Desktop, tray, persistent `%APPDATA%/MarkJenny`, auto-update, crash recovery.

## Tests

```bash
cd backend
pytest tests/test_api.py -v
cd ../frontend
npm run test  # vitest
```

## Security

RBAC `USER/CREATOR/ADMIN` server-side (`app/api/v1/endpoints/admin.py:require_admin`), encrypted provider keys, rate limit 100/min (10/min auth), never expose secrets in logs.

## Super-Agent

Self-Improvement (FailureMemory→skill patch), Self-Upgrade (Never-No gap→research→synthesize→validate→install), Mythos 1M context, Hybrid Ollama/Cloud - see `docs/CONSOLIDATED_SUPER_MARK_SPEC.md`.
