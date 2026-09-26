# MARK-IMTI — Full Application Specification

**Version:** 2026-09-26  
**Source:** Consolidated from `CONSOLIDATED_SUPER_MARK_SPEC.md`, `FEATURE_MANIFEST.md`, `ARCHITECTURE.md`, `API.md`, `DATABASE_SCHEMA.md`, `ADVANCED_INTELLIGENCE_PLAN.md`, and backend service implementations.

---

## 1. SYSTEM OVERVIEW

### 1.1 What Is Mark-Imti
Mark-Imti is an **autonomous AI operating platform** that functions as a "virtual colleague with its own computer." It doesn't just answer questions — it plans, executes, and delivers complete work products (files, applications, research reports, presentations, spreadsheets, code, websites) from start to finish.

**Core Philosophy:** The intelligence lives in the **agents and workflows**, not the models. Models are interchangeable brains (local Ollama, OpenAI, Anthropic, Google, custom). Agents contain the decision logic, workflows, and domain expertise.

### 1.2 Dual-Agent Architecture
- **Mark** — Builder/Executor agent. Handles code generation, website/app building, spreadsheet creation, document generation, file operations, browser automation, computer control, code execution.
- **Imti** — Supervisor/Quality/Security agent. Handles cybersecurity analysis, quality assurance, reasoning, research orchestration, approval gates, self-check loops, failure pattern detection, safety enforcement.

---

## 2. TECHNICAL STACK

| Layer | Technology |
|-------|------------|
| **Frontend** | Next.js 16 App Router, React 19, TypeScript, Tailwind CSS, shadcn/ui (@base-ui), next-themes, lucide-react |
| **Backend** | FastAPI, SQLAlchemy 2, SQLite (dev) / PostgreSQL (prod), Alembic, python-jose (JWT), passlib[bcrypt], httpx, websockets, psutil |
| **Local AI** | Ollama (AirLLM/qwen3-vl:8b), OpenAI-compatible endpoints (LM Studio, vLLM) |
| **Cloud AI** | OpenAI, Anthropic, Google, Azure, custom providers |
| **Browser** | Playwright (Chromium), httpx fallback |
| **Computer Control** | Windows: tkinter (clipboard), psutil (processes), tasklist (windows) |
| **Code Execution** | Isolated sandbox subprocesses (Python, Node.js, PowerShell, Shell) |
| **File Formats** | openpyxl (XLSX), python-pptx (PPTX), PIL (images), SVG |
| **Build** | `next build --webpack` (Windows), `uvicorn app.main:app --port 8000` |
| **Desktop** | Tauri (Windows MSI/NSIS installer) |

---

## 3. MARK CORE — 21 ENGINES

```
Agent Controller | Planner | Supervisor | Model Router | Tool Router | Skill Engine
| Memory Engine | Knowledge Engine | Task Engine | Scheduler | Approval Engine
| Connector Engine | Browser Engine | Computer Engine | Code Execution Engine
| File Engine | Research Engine | Workflow Engine | Notification Engine
| Security Engine | Audit Engine
```

Each engine is implemented as a service in `backend/app/services/` with dedicated API endpoints.

---

## 4. DATABASE — 34 TABLES (SQLite/PostgreSQL)

### Core
- **users** — id, email, hashed_password, full_name, avatar_url, role (USER/CREATOR/ADMIN), is_active, is_verified
- **sessions** — user_id, refresh_token, expires_at, revoked_at
- **projects** — owner_id, name, description, icon, instructions, status (ACTIVE/ARCHIVED/DELETED)

### Tasks & Scheduling
- **tasks** — owner_id, project_id, parent_task_id, title, status, priority, autonomy_level, plan JSON, model_used, result JSON, checkpoints
- **task_runs** — task_id, run_number, status, plan, tool_calls, model_usage, files_created, duration
- **subtasks** — task_id, title, status, order, assigned_agent, required_skills/tools, result
- **schedules** — owner_id, project_id, agent_id, title, prompt, frequency, time, timezone, run_option, connectors, config, is_active
- **schedule_runs** — schedule_id, task_id, status, error, duration

### Files & Knowledge
- **files/folders** — owner_id, project_id, task_id, name, path, mime_type, file_type (IMAGE/DOCUMENT/VIDEO/AUDIO/SPREADSHEET/CODE/ARCHIVE/WEBSITE/OTHER), hash
- **skills** — name, version, source (OFFICIAL/UPLOADED/GITHUB/CREATED_BY_MARK), manifest, instructions, tools, permissions, config_schema, dependencies
- **skill_versions** — skill_id, version, manifest, changelog
- **connectors** — name, type, config_schema, is_system
- **connector_credentials** — connector_id, user_id, project_id, auth_type, encrypted_credentials, status
- **knowledge** — name, use_when, content, enabled, project_id, confidence, importance, tags
- **memories** — type (9 types), content, source, confidence, importance, enabled, owner_id, project_id, task_id

### Chat & AI
- **chats** — owner_id, project_id, task_id, title, model_used
- **messages** — chat_id, role (USER/ASSISTANT/SYSTEM/TOOL), content, tool_calls, metadata
- **models** — name, provider, model_id, capabilities, context_window, cost_per_1k, is_local, is_active
- **model_provider_configs** — user_id, provider, api_key_encrypted, base_url, is_default
- **agents** — name, type (PRIMARY/RESEARCH/CODING/BROWSER/DOCUMENT/SPREADSHEET/DESIGN/DATA/SECURITY/QA/SUPERVISOR), model_id, available_tools/skills

### Governance & System
- **approvals** — type (SEND_EMAIL/PUBLISH/DELETE/EXECUTE/SPEND/POST), title, details, risk_level, task_id, user_id, status (PENDING/APPROVED/REJECTED)
- **notifications** — user_id, task_id, type, title, is_read
- **audit_logs** — user_id, action, resource_type/id, details, success, ip
- **generated_websites/apps** — owner_id, project_id, task_id, name, prompt, status, files, preview_url
- **browser_sessions** — owner_id, task_id, browser_type, cookies, is_persistent
- **settings** — user preferences, data controls, cloud browser, mail config

---

## 5. API ENDPOINTS (50+ Routes)

Base: `http://localhost:8000/api/v1` | Docs: `/api/v1/docs` (Swagger)

### Auth
- `POST /auth/register`, `POST /auth/login` (OAuth2 form), `POST /auth/refresh`, `GET /auth/me`, `POST /auth/logout`

### Core Resources
- `GET/POST /projects`, `GET/PATCH/DELETE /projects/{id}`, `POST /{id}/duplicate`
- `GET/POST /tasks`, `PATCH/DELETE /{id}`, `POST /{id}/execute|pause|resume|cancel|retry`, `GET /{id}/runs`
- `GET/POST /files`, `POST /files/upload`, `GET /{id}/download`, `DELETE`
- `GET/POST /schedules`, `PATCH /{id}`, `POST /{id}/pause|resume|duplicate`, `GET /upcoming/next`

### Intelligence & Agents
- `GET/POST /chats`, `GET /chats/{id}`, `POST /chats/{id}/messages` → triggers autonomous pipeline
- `GET/POST /quick-actions`, `POST /quick-actions/{id}/execute` (16 actions)
- `GET/POST /knowledge`, `PATCH/DELETE /{id}`, `POST /{id}/toggle`
- `GET/POST /memories`, `PATCH/DELETE`, `GET /memories/types/list` (9 types)
- `GET/POST /skills`, `GET /skills/official`, `POST /skills/official/{name}/install`, `POST /skills/upload|github|build`, `POST /{id}/enable|disable|rollback`
- `GET /connectors` (14 seeded), `POST /connectors/connect`, `POST /connectors/custom-api|mcp`

### Automation Engines
- `GET /browser/capability`, `POST /browser/sessions`, `POST /browser/navigate|search|click|type|read|extract`
- `GET /computer/info|files|processes|clipboard|windows`, `POST /computer/files/write|clipboard`
- `POST /execution/run` `{language: python|javascript|powershell, code, timeout}` → sandboxed
- `GET /ai/models|providers|agents`, `POST /ai/providers`, `POST /ai/route`, `POST /ai/plan`
- `POST /generate/{website|app|slides|image|research|spreadsheet|video|audio|document|code}` → Task + Files

### Governance
- `GET/PATCH /settings`, `GET /settings/data-controls/overview`, `GET/PATCH /settings/cloud-browser|mail`, `POST /settings/clear-cache`
- `GET /admin/users` (Admin), `PATCH /admin/users/{id}/role`, `POST /admin/users/{id}/blacklist`, `GET/PATCH /admin/feature-flags`, `GET /admin/audit-logs`
- `GET/POST /advanced/self-check|checkpoint|recover|delegate|verify`, `GET /advanced/memory/failures`, `POST /advanced/blueprints|heal|simulate|dry-run|approvals|timeline|snapshots|knowledge-graph`

### Real-time
- `WS /ws/tasks?token=...` → `{"type":"task_update","task":{...}}` on task mutation

---

## 6. AGENT CAPABILITIES — COMPLETE LIST

### 6.1 Mark (Builder/Executor) Capabilities

| Capability | Description | Implementation |
|------------|-------------|----------------|
| **Website Generation** | Complete HTML/CSS/JS websites from prompts | `GenerativeEngine.generate_website()` |
| **App Development** | React/Next.js/TypeScript components, Python backends | `GenerativeEngine.generate_app()` |
| **Slide Creation** | PPTX presentations with speaker notes, visuals | `GenerativeEngine.generate_slides()` |
| **Image Generation** | SVG illustrations, PIL fallback | `GenerativeEngine.generate_image/edit_image()` |
| **Spreadsheet Creation** | XLSX with formulas, formatting, sample data | `GenerativeEngine.generate_spreadsheet()` |
| **Document Writing** | Markdown documents with structure, tables, code blocks | `GenerativeEngine.generate_document()` |
| **Code Generation** | Production-quality code in Python/JS/TS/Go with error handling | `GenerativeEngine.generate_code()` |
| **Research Reports** | Comprehensive reports: exec summary, findings, analysis, recommendations | `GenerativeEngine.generate_research()` |
| **Video Scripts** | Professional scripts with scenes, dialogue, timing | `GenerativeEngine.generate_video()` |
| **Audio Scripts** | Podcast/audio scripts with narration, SFX, music cues | `GenerativeEngine.generate_audio()` |
| **Browser Automation** | Navigate, search, click, type, scroll, read, extract, screenshot | `BrowserEngine` (Playwright + httpx fallback) |
| **Local Computer Control** | File read/write, process list/kill, clipboard, window list | `ComputerEngine` (Windows: tkinter, psutil) |
| **Code Execution** | Sandboxed Python/Node/PowerShell/Shell with timeout, FS isolation | `CodeExecutionEngine` |
| **File Management** | Upload, download, organize, search, preview, version | `Files` endpoints + `Folder` tree |
| **Project Workspace** | Instructions (markdown, versioned), Files & Source, Skills, Connectors | Phase 3 endpoints |
| **Scheduled Tasks** | Cron/daily/weekly/monthly with connectors, computer, approval defaults | `Schedules` + `ScheduleRuns` |
| **Quick Actions** | 16 one-click workflows from plus menu | `QuickActions` endpoints |
| **Voice Interface** | Direct task execution, meeting minutes (waveform, transcription) | `Voice` endpoints |
| **Skill Builder** | Natural language → skill package (manifest, tools, permissions) | `Skills` endpoints |
| **Self-Build Orchestration** | Plain language → sandbox build → test → review → integrate | `SelfBuildOrchestrator` |
| **Model Routing** | Hybrid local/cloud, 5 task types, fallback chain, cost-aware | `ModelRouter` + `ModelCaller` |

### 6.2 Imti (Supervisor/Quality/Security) Capabilities

| Capability | Description | Implementation |
|------------|-------------|----------------|
| **Cybersecurity Scanning** | Mythos-level: traces data flows, CWE classification, exploit scenarios, patches | `CybersecurityAgent.scan_code()`, `scan_codebase()`, `deep_web_audit()` |
| **Security Posture** | Passive web header/cookie/SSL analysis | `CybersecurityAgent.security_posture()` |
| **Exploit Analysis** | Deep exploitability: reachability, payload, chain potential, PoC | `CybersecurityAgent.analyze_exploit()` |
| **Continuous Security Loop** | 5-stage: Threat Model → Discovery → Verification → Triage → Patching | `CybersecurityAgent.security_loop()` |
| **Site Safety Assessment** | Phishing, malware, crypto-miners, trackers, redirect analysis | `CybersecurityAgent.site_safety()` |
| **Self-Check Loop** | Post-task AI evaluation: objective, quality, completeness, correctness | `SelfCheckLoop.evaluate()` |
| **Error Recovery** | AI root cause analysis, retry strategy, exponential backoff | `ErrorRecovery.analyze()` |
| **Checkpointing** | Save/restore task state at any step | `CheckpointManager` |
| **Memory Layer (9 types)** | Working, Short-term, Episodic, Semantic, Procedural, Project, User Preference, Task, Failure | `MemoryLayerManager` |
| **Multi-Agent Delegation** | 9 specialized agents (research, coding, browser, document, spreadsheet, design, data, security, QA) | `MultiAgentDelegation` |
| **Supervisor Verification** | AI quality review of delegated results | `Supervisor.verify()` |
| **Task Blueprints** | Save successful workflows as reusable templates | `AdvancedWorkflows` endpoints |
| **Self-Healing Workflows** | Diagnose → alternative → retry → continue → pause for user | `AdvancedWorkflows` + `ErrorRecovery` |
| **Approval Center** | Central dashboard for pending: email, publish, delete, execute, spend, post | `Approvals` endpoints |
| **Agent Activity Timeline** | Concise events: Planning, Researching, Reading, Calling, Creating, Validating | `AdvancedWorkflows` endpoints |
| **Project Snapshots** | Create, restore, compare versions | `AdvancedWorkflows` endpoints |
| **Skill Dependency Engine** | Skills declare deps, validate before execution | `AdvancedWorkflows` endpoints |
| **Knowledge Graph** | Connect Projects, People, Companies, Files, Tasks, Skills, Sources | `AdvancedWorkflows` endpoints |
| **Workflow Simulator / Dry Run** | Preview Plan → Dry Run (tools, files, connectors, risks) → Execute | `AdvancedWorkflows` endpoints |

---

## 7. ADVANCED INTELLIGENCE WORKFLOWS (Inspired by GPT-6 Astra & Claude Mythos 5)

### 7.1 Cybersecurity Workflow (Astra + Mythos)
- Code vulnerability scanning (OWASP Top 10, CWE)
- Multi-step analysis with synthesis
- Severity classification (Critical/High/Medium/Low)
- Fix generation with diffs
- Penetration testing guides
- Web app audit (headers, cookies, CSP)
- Tool integration: bandit, semgrep, npm audit

### 7.2 Biology Research Workflow (Mythos)
- Literature review (PubMed + arXiv)
- Sequence analysis (protein/DNA)
- Hypothesis generation
- Experiment design with controls
- Structure prediction features
- Pathway analysis
- Drug target identification
- Tool integration: BLAST, Clustal

### 7.3 Deep Reasoning Engine (Astra)
- Task decomposition
- Evidence gathering
- Chain-of-thought reasoning
- Confidence scoring
- Counter-argument analysis
- 5 reasoning levels: Fast/Balanced/Deep/Exhaustive/Maximum

### 7.4 Autonomous Research Agent (Mythos)
- Multi-session research (hours/days)
- Real-time web search
- Paper discovery & summarization
- Data collection from multiple sources
- Report generation with citations
- Progress tracking & resume
- Source verification

### 7.5 Coding Intelligence (Astra)
- Code analysis & pattern recognition
- Bug detection with root cause
- Refactoring suggestions
- Architecture review
- Test generation
- Documentation from code
- CI/CD integration

### 7.6 Context Memory System (Astra)
- Session notes during tasks
- Cross-session memory
- Knowledge base building
- Learning from corrections
- User preference memory

---

## 8. AUTONOMY LEVELS

| Level | Behavior |
|-------|----------|
| **L1** | Ask before ALL actions |
| **L2** | Ask for sensitive actions (email, publish, delete, execute, spend, post) |
| **L3** | Autonomous within approved permissions |
| **L4** | Scheduled autonomous operation (no confirmation) |

---

## 9. PLUS MENU — 16 ACTIONS (All Real Workflows)

1. **Camera** — Capture photo via webcam
2. **Picture** — Upload image file
3. **File** — Upload any document
4. **Connect My Computer** — Pair local Windows device (explicit consent, tray)
5. **Add Skills** — Install/enable skills
6. **Build Website** → `generate_website`
7. **Develop Apps** → `generate_app`
8. **Create Slides** → `generate_slides`
9. **Create Image** → `generate_image`
10. **Edit Image** → `edit_image`
11. **Wide Research** → `generate_research` (query planning → parallel search → citation → synthesis)
12. **Scheduled Tasks** → Create schedule
13. **Create Spreadsheet** → `generate_spreadsheet`
14. **Create Video** → `generate_video`
15. **Generate Audio** → `generate_audio`
16. **Playbook** → Blueprint/workflow templates

---

## 10. CONNECTORS (14 Built-in + Custom)

| Connector | Type | Auth |
|-----------|------|------|
| Google Drive | System | OAuth |
| Google Calendar | System | OAuth |
| Gmail | System | OAuth |
| GitHub | System | OAuth/PAT |
| Slack | System | OAuth |
| Notion | System | OAuth |
| Microsoft Outlook | System | OAuth |
| Outlook Calendar | System | OAuth |
| Outlook Mail | System | OAuth |
| Shopify | System | API Key |
| Apify | System | API Key |
| Instagram | System | OAuth |
| Meta Ads | System | OAuth |
| Custom API | User-defined | API Key/Bearer |
| Custom MCP | User-defined | Config |

---

## 11. MEMORY ARCHITECTURE (9 Layers)

| Memory Type | Purpose | Weight | Confidence | Importance |
|-------------|---------|--------|------------|------------|
| **WORKING** | Current conversation context | 0.8 | - | - |
| **SHORT_TERM** | Recent interactions (hours) | 0.9 | - | - |
| **EPISODIC** | Specific events/episodes | 1.1 | - | - |
| **SEMANTIC** | Facts, concepts, knowledge | 1.0 | - | - |
| **PROCEDURAL** | Skills, workflows, how-to | 1.3 | - | - |
| **PROJECT** | Project-specific knowledge | 1.2 | - | - |
| **USER_PREFERENCE** | Explicit user preferences | 1.5 | 100% | 90% |
| **TASK** | Task-specific decisions | 1.1 | 85% | 60% |
| **FAILURE** | Error patterns to avoid | 1.4 | 95% | 85% |

**Retrieval:** Scored (token overlap + type weight + importance + confidence + recency boost), not keyword match.

---

## 12. MODEL ROUTING & MULTI-MODEL ORCHESTRATION

| Task Type | Purpose | Examples |
|-----------|---------|----------|
| `fast` | Quick responses | Chat, simple Q&A |
| `deep_reasoning` | Complex analysis | Research, planning, math |
| `coding` | Software engineering | Code gen, debugging, review |
| `research` | Information gathering | Web search, synthesis |
| `vision` | Image/video analysis | Screenshots, diagrams |
| `image_generation` | Visual creation | Images, slides, diagrams |
| `audio` | Speech/audio | TTS, transcription |
| `video` | Video generation | Scripts, editing |
| `embeddings` | Semantic search | Memory recall, RAG |
| `local` | Offline inference | Ollama, AirLLM |

**Routing Logic:** Task type → capability match → cost/speed/availability → fallback chain (local → cheap cloud → premium cloud)

---

## 13. SECURITY & GOVERNANCE

### Core Laws System
- User-defined immutable rules loaded from `core_laws/laws.json`
- Enforced at runtime BEFORE any model/tool call (not just prompt guidance)
- Categories: `BLOCK: DESTRUCTIVE_OPERATIONS`, `BLOCK: EXTERNAL_ACTIONS`, `REQUIRE: USER_CONFIRMATION`

### Security Features
- JWT access (30min) + refresh (7d) httpOnly cookie with rotation
- RBAC: USER / CREATOR / ADMIN
- Encrypted credential storage (base64 stub → Fernet in prod)
- Rate limiting: 100/min IP, 10/min auth (429)
- Input/file validation, 100MB upload limit
- CSRF, XSS, SQL injection protection
- Secure OAuth handling
- Audit logs: all user actions, task executions, agent decisions, tool calls, approvals, admin actions

### Autonomy Safeguards
- Dangerous operations (process kill, shell exec, file write) require confirmation
- Approval Center for: Send Email, Publish Website, Delete Files, Execute Command, Spend Money, Post Publicly
- Sandbox isolation for code execution (FS isolation, timeout, network policy)
- Browser sessions: persistent login opt-in only, explicit consent per session

---

## 14. OFFLINE-FIRST ARCHITECTURE

- Local: projects, files, task history, memory, settings, skills
- Local model execution (Ollama)
- Local code execution (sandbox)
- Local scheduling & task queue
- **Sync on reconnect:** Conflict resolution, NO silent overwrites

---

## 15. LONG-RUNNING TASK ENGINE

- Persistent task queue with background workers
- Checkpoints after meaningful operations
- Retry policies with exponential backoff
- Failure recovery, pause/resume/cancel
- Timeout handling, dependency management
- Subtask graph execution
- **Recover tasks on app restart**

---

## 16. RESEARCH ENGINE

- Query planning → parallel searches → source collection → extraction → evidence comparison → deduplication → citation tracking → synthesis → report generation
- Stores source URLs and evidence metadata
- **No fabricated sources**

---

## 17. NOTIFICATION SYSTEM

Events: Task starts, requires approval, completes, fails, scheduled runs, long-running pauses, connector expires, security events

---

## 18. DEPLOYMENT

### Local Dev
```bash
cd backend; $env:PYTHONPATH="."; uvicorn app.main:app --reload --port 8000
cd frontend; npm run dev
```

### Docker (Production Web)
```bash
cp .env.example .env  # Set SECRET_KEY, DATABASE_URL
docker-compose up --build
# Frontend http://localhost:3000 → Backend http://localhost:8000
```

### Windows Desktop
- Tauri build: `npm run tauri build` → MSI + NSIS installer
- Signed installer with tray, crash recovery, auto-update

### Environment Variables
| Variable | Default | Required |
|----------|---------|----------|
| `DATABASE_URL` | `sqlite:///./mark_imti.db` | No |
| `SECRET_KEY` | auto-generated | **YES (prod)** |
| `CORS_ORIGINS` | `["http://localhost:3000"]` | No |
| `UPLOAD_DIR` | `./uploads` | No |
| `OLLAMA_BASE_URL` | `http://localhost:11434` | No |
| `NEXT_PUBLIC_API_URL` | `http://localhost:8000/api/v1` | No |
| `NEXT_PUBLIC_WS_URL` | `ws://localhost:8000/api/v1/ws` | No |

---

## 19. CURRENT IMPLEMENTATION STATUS

Per `FEATURE_MANIFEST.md` tracking:
- **Phases 0-3:** Database (34 tables), Auth (JWT+RBAC), Shell, Navigation, Dashboard (Scheduled/Library/Projects), Project Workspace (Instructions/Files/Skills/Connectors) — **PLANNED/IMPLEMENTING**
- **Phase 4:** Chat interface, Plus Menu (16 actions), Voice, Autonomous Agent Pipeline — **PLANNED**
- **Phases 5-16:** Quick Actions, Scheduled Tasks, Memory/Knowledge, Skills Builder, Browser/Computer/Code Execution, Model Routing, Generative Workflows (10 types), Settings/Admin, Advanced Autonomy (Self-Check, Delegation, Memory, Blueprints, Approvals, Timeline, Snapshots), Security, QA, Windows Packaging — **PLANNED**

---

## 20. KEY DIFFERENTIATORS

1. **Agent-Native Intelligence** — Workflows contain the expertise; models are pluggable
2. **Self-Build Loop** — Jenny orchestrates Mark to build features in sandbox with version snapshots
3. **Mythos-Class Security** — Cybersecurity agent that traces data flows like a researcher
4. **9-Layer Memory** — Scored retrieval with type weights, not keyword matching
5. **Hybrid Local/Cloud** — Ollama + cloud providers with cost-aware routing
6. **Offline-First** — Full functionality without internet, sync on reconnect
7. **Windows Desktop Native** — Real computer control, not browser-limited
8. **Skill Ecosystem** — Official + GitHub + User-created + Mark-created skills
9. **Approval Gates** — Granular control over destructive/external actions
10. **Complete Audit Trail** — Every decision, tool call, and result logged

---

*Generated from deep codebase analysis — single source of truth for Mark-Imti platform.*