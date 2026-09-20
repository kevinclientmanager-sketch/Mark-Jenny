# MARK IMTI — Autonomous AI Operating Platform

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

## Capability Overview

Mark Imti is a cloud-first autonomous AI operating platform with a Windows desktop wrapper and web application. It combines chat, project workspaces, browser/computer automation, scheduled jobs, knowledge and persistent memory, skills, voice, vision, MCP connectors, code generation, and governed execution.

### Core capabilities

- **Chat and agents:** Imti conversational chat, Mark work mode, Browser mode, multi-agent delegation, specialist routing, tool calling, streaming task updates, voice input/output, and contextual follow-up.
- **Build and code:** project workspaces, files, code generation, self-build sessions, live build logs, sandbox files, QA analysis, test/build checks, integration, rollback, blueprints, snapshots, and GitHub/Vercel operations.
- **Automation:** browser sessions, navigation/search/click/type/form automation, computer actions, scheduled tasks, task timelines, approvals, dry runs, self-healing, and audit logging.
- **Intelligence:** cloud-first OpenAI-compatible runtime, optional Ollama/AirLLM local or hybrid runtime, memory, knowledge ingestion/search, knowledge graphs, skills and dependency validation, vision/OCR/YouTube analysis, and workflow orchestration.
- **Governance:** JWT authentication, RBAC, per-user self-build session ownership, encrypted credential vault, rate limits, approval center, audit trail, snapshots, rollback, and readiness diagnostics.

### Runtime readiness and premium agent operations

Authenticated clients can call `GET /api/v1/features/readiness` to inspect cloud/local model configuration, AirLLM/CrewAI availability, self-build features, governance controls, and actionable setup recommendations. This makes deployment behavior explicit instead of silently pretending an optional provider is installed.

Research-led additions now exposed through `/api/v1/features`:

- `GET /catalog` — capability discovery for durable runs, trace/evaluation, policy guardrails, memory/knowledge, and computer/MCP use.
- `POST /evaluate` — delivery preflight scoring relevance, completeness, safety, and actionability.
- `POST /policy/preflight` — consistent human-approval decisions for sensitive, expensive, or irreversible actions.

These additions follow current agent-platform patterns: durable state, observable runs, eval gates, least-privilege tool use, and explicit human approval for side effects. They are API-backed and audit logged, so chat, quick actions, self-build, and future agent surfaces can share the same controls.

### Build workspace and sandboxes

The `/build` workspace combines the build brief, target selection, live console, preview iframe, artifact inventory, integration, and rollback. It currently uses the web filesystem sandbox: an isolated per-session workspace with live logs and artifacts. Docker execution is intentionally reserved for a future optional backend runtime and is not presented as an available feature until its isolation, provisioning, and lifecycle controls are implemented.

## Super-Agent

Self-Improvement (FailureMemory→skill patch), Self-Upgrade (Never-No gap→research→synthesize→validate→install), Mythos 1M context, and Hybrid Ollama/Cloud - see `docs/CONSOLIDATED_SUPER_MARK_SPEC.md`.

## Research-informed roadmap

Current agent platform guidance emphasizes durable state, specialist handoffs, guardrails and human approval, resumable runs, tracing/evaluation, computer use, and memory consolidation. Mark Imti already includes the corresponding building blocks; the new readiness endpoint makes optional runtime capabilities observable so production deployments can safely enable only what is configured.
