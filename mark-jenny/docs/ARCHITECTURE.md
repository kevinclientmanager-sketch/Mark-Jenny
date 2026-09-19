# Architecture

## Stack
- **Frontend:** Next.js 16 App Router (`src/app`), React 19, TypeScript, Tailwind, shadcn/ui (@base-ui), next-themes, lucide-react, WebSocket hook
- **Backend:** FastAPI, SQLAlchemy 2, SQLite (check_same_thread False), Alembic (available), python-jose, passlib[bcrypt], httpx, websockets, psutil (optional), python-multipart
- **Build:** `next build --webpack` (Windows WASM fallback), `uvicorn app.main:app --port 8000`

## MARK CORE 21 Engines
`Agent Controller | Planner | Supervisor | Model Router | Tool Router | Skill Engine | Memory Engine | Knowledge Engine | Task Engine | Scheduler | Approval Engine | Connector Engine | Browser Engine | Computer Engine | Code Execution Engine | File Engine | Research Engine | Workflow Engine | Notification Engine | Security Engine | Audit Engine`

## Data Flow
`USER REQUEST → Intent Analysis → Goal Decomposition → Plan → Skill Selection → Model Selection (ModelRouter cost/speed/capability + Ollama hybrid) → Tool Selection → Execution (sandbox) → Observation → Validation → Self-Correction → Memory Update → Project Storage`

## Persistence
`app/db/base.py:Base` → 34 tables (see DATABASE_SCHEMA.md) via `app/db/init_db.py:create_all` (SQLite file `mark_jenny.db` + `uploads/`). No silent overwrite, FK cascades, indexes.

## Auth
`app/core/security.py:OAuth2PasswordBearer` JWT access 30m + refresh 7d httpOnly cookie + `Session` table rotation, `get_current_user` dependency, RBAC `USER/CREATOR/ADMIN`.

## Real-time
`app/api/v1/endpoints/websocket.py:ConnectionManager` per-user + per-task subscriptions, `notify_task_update` on task mutation.

## Security
`app/core/rate_limit.py:RateLimiter` 100/min IP, 10/min auth (429), plus input/file validation, `FileType`, upload 100MB, permission checks, encrypted `api_key_encrypted` (base64 stub, Fernet in prod).
