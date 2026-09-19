# MARK JENNY — Agent operating notes

FastAPI + SQLite backend (`mark-jenny/backend`), Next.js 16 App Router frontend (`mark-jenny/frontend`). All on Windows/PowerShell 5.1. Git repo root = project root (Windows paths contain spaces: `C:\Users\LAP TECH\...`).

## CRITICAL: How this agent sees screenshots (read first)
- **The agent model cannot ingest pasted images** ("model does not support image input"). Never claim you saw an image. If a user drops an image, say so plainly and use the pipeline below.
- Dropped images land in `C:\Users\LAP TECH\AppData\Local\Temp\opencode-vision\vision-*.png`.
- Local vision model: Ollama `qwen3-vl:8b` on `http://localhost:11434` (~7 min/image on CPU — it is the ONLY working vision model; `gemma4:26b` returns empty). Start Ollama with `ollama serve` if needed.
- Helper `C:\Users\LAP TECH\AppData\Local\Temp\opencode\vision.ps1` downscales to 640px, POSTs to Ollama, prints the answer AND appends to `vision-results.txt`. Invoke it synchronously from the temp dir:
  `& "C:\Users\LAP TECH\AppData\Local\Temp\opencode\vision.ps1" -ImagePath "C:\Users\LAP TECH\AppData\Local\Temp\opencode-vision\vision-XXX.png" -Question "..."`  (generous timeout, ≥900s).
- **Quoting gotcha:** never launch it via `Start-Process -ArgumentList '-File','C:\Users\LAP TECH\...'` — the space in `LAP TECH` splits the argument and PowerShell fails to find the file. Use a wrapper `.ps1` file containing the `& "..."` line, or run it synchronously.
- opencode vision auto-routing IS configured globally (`~/.config/opencode/opencode.jsonc` MCP `local_vision` server + plugin `opencode-vision` in `opencode-vision.json`, tool `local_vision_analyze_local_image`) but it only activates after a **full opencode restart**. Until the user restarts, MCP vision calls return `Connection closed` — use `vision.ps1` instead.

## Run / verify
- Start (hidden background): run `mark-jenny\START-APP.ps1` → backend `backend\venv\Scripts\python.exe main.py` on :8000 and `npm run dev -- --webpack` on :3000; logs in `mark-jenny\logs\`, PIDs in `logs\app.pids`. The tool shell often reports the launcher as "killed" — that's the detach; poll health instead. Stop with `mark-jenny\STOP-APP.bat`.
- Health check: `Invoke-WebRequest http://localhost:8000/health` and `http://localhost:3000/chat` → expect 200.
- Backend `main.py` runs uvicorn with `reload=True` → backend picks up Python edits automatically.
- Frontend verification after edits: `npx tsc --noEmit` (clean) then `Invoke-WebRequest http://localhost:3000/<route>` 200. Do full `npx next build --webpack` only when asked.
- npm on this machine prints `npm warn install-scripts` and blocks native postinstall builds (e.g. `sharp`). Do not add npm deps that need them.
- PowerShell 5.1: no `&&`; chain with `; ` or `if ($?) { }`.
- git: user declined repo setup for now — do not `git init`/push unless explicitly asked.

## Auth (temporarily bypassed)
- Login is disabled: `AUTO_LOGIN_DEMO` in `frontend/src/lib/auth/auth-context.tsx` (enabled: true) auto-logs-in as `kevin.clientmanager@gmail.com` / `Admin1234` and fetches a real JWT, so protected pages work with no login screen. Re-enable later by flipping `enabled` to false.
- Auth API is **OAuth2 form** (not JSON): `POST /api/v1/auth/login`, `Content-Type: application/x-www-form-urlencoded`, field `username`.

## UI conventions (user checks these carefully — keep ChatGPT fidelity)
- Wordmark is lowercase **"mark jenny"**. Never add "Free", "Free offer", or "CodeX".
- Top bar: centered Chat | Work | Browse toggle. Sidebar also has the Chat|Work|Browse toggle under "New chat" (both write `localStorage["mark.sidebarMode"]`; switching mode on the chat page opens a fresh new chat).
- Chat page must keep the composer pinned: root is `h-dvh overflow-hidden`, only the messages column scrolls (`MessageList` root: `h-full overflow-y-auto`). The composer vanishing while scrolling = someone reverted this.
- Current sidebar: primary = Images, Library, Scheduled, Plugins, Browse; More… = Dashboard, Projects, Quick Actions. Quick Actions page cards are defined server-side in `backend/app/api/v1/endpoints/quick_actions.py` (`ACTION_DEFS`) — Camera/Picture/File were purposefully removed there. The chat composer's ＋ menu (`frontend/src/components/chat/PlusMenu.tsx`) is separate: it keeps Camera/Picture/File + Scheduled tasks and is NOT driven by the backend.
- Settings (`frontend/src/app/settings/page.tsx`) owns: Computer, Security, Connectors, Knowledge, Memory, Agents, AI Studio, Admin (as tabs/link-outs).

## Architecture map
- Backend routers under `backend/app/api/v1/endpoints/`: auth, users, projects, tasks, files, schedules, chats, quick-actions, knowledge, memories, skills, browser, computer, execution, ai, generate, settings, admin, advanced, ws (WebSocket task updates). SQLite DB `backend/mark_jenny.db`. Quick seed helpers (`backend/seed_shot.py`) may create demo data (chat id 6 "Demo - Show me" is a seed).
- Frontend key files: `app/chat/page.tsx`, `components/layout/sidebar.tsx`, `components/chat/ChatTopBar.tsx`, `components/chat/ChatInput.tsx`, `components/chat/MessageList.tsx`, `app/settings/page.tsx`, `app/quick-actions/page.tsx`.
- **Next.js 16 has breaking changes** — `frontend/AGENTS.md` instructs reading the relevant guide in `node_modules/next/dist/docs/` before writing Next code; respect it and don't remove that block.