# API Documentation

Base: `http://localhost:8000/api/v1` - Docs at `/api/v1/docs` (Swagger) and `/api/v1/redoc`.

## Auth
- `POST /auth/register` `{email,password,full_name}` → 201
- `POST /auth/login` (OAuth2 form `username=email&password`) → `{access_token, refresh_token}` + httpOnly cookie
- `POST /auth/refresh` (cookie) → new tokens
- `GET /auth/me` (Bearer) → User
- `POST /auth/logout`

## Core
- `GET/POST /projects` / `GET/PATCH/DELETE /projects/{id}` / `POST /{id}/duplicate` + `GET /projects/{id}/skills`
- `GET/POST /tasks` / `PATCH/DELETE /{id}` + `POST /{id}/execute|pause|resume|cancel|retry` + `GET /{id}/runs`
- `GET /files?project_id=&file_type=` / `POST /files/upload` (multipart) / `GET /{id}/download` / `DELETE`
- `GET/POST /schedules` / `PATCH /{id}` + `POST /{id}/pause|resume|duplicate` + `GET /upcoming/next`

## Intelligence
- `GET/POST /chats` / `GET /chats/{id}` / `POST /chats/{id}/messages` (triggers autonomous pipeline → Task)
- `GET/POST /quick-actions` / `POST /quick-actions/{id}/execute` (16 actions)
- `GET/POST /knowledge` / `PATCH/DELETE /{id}` / `POST /{id}/toggle`
- `GET/POST /memories` / `PATCH/DELETE` + `GET /memories/types/list` (9 types)
- `GET/POST /skills` / `GET /skills/official` / `POST /skills/official/{name}/install` / `POST /skills/upload|github|build` / `POST /{id}/enable|disable|rollback`
- `GET /connectors` (14 seeded) / `POST /connectors/connect` / `POST /connectors/custom-api|mcp`

## Automation
- `GET /browser/capability` / `POST /browser/sessions` / `POST /browser/navigate|search|click|type|read|extract`
- `GET /computer/info|files|processes|clipboard|windows` / `POST /computer/files/write|clipboard`
- `POST /execution/run` `{language: python|javascript|powershell, code, timeout}` → sandboxed `exec_sandbox`
- `GET /ai/models|providers|agents` / `POST /ai/providers` / `POST /ai/route` `{task_type, prompt}` / `POST /ai/plan`
- `POST /generate/{website|app|slides|image|research|spreadsheet|video|audio|document|code}` → Task + Files

## Governance
- `GET/PATCH /settings` / `GET /settings/data-controls/overview` / `GET/PATCH /settings/cloud-browser|mail` / `POST /settings/clear-cache`
- `GET /admin/users` (Admin only 403 else) / `PATCH /admin/users/{id}/role` / `POST /admin/users/{id}/blacklist` / `GET/PATCH /admin/feature-flags` / `GET /admin/audit-logs`
- `GET/POST /advanced/self-check|checkpoint|recover|delegate|verify` / `GET /advanced/memory/failures` / `POST /advanced/blueprints|heal|simulate|dry-run|approvals|timeline|snapshots|knowledge-graph`

## Real-time
- `WS /ws/tasks?token=...` → `{"type":"task_update","task":{...}}` on task mutation.

## Rate Limit
- 100/min IP, 10/min auth → 429. See `GET /advanced/security/rate-limit`.
