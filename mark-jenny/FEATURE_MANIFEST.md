# Mark-Imti - Feature Manifest

This document tracks all features from the specification and their implementation status.

## Status Definitions
- [PLANNED] - Feature identified, not started
- [IMPLEMENTING] - Currently being implemented
- [IMPLEMENTED] - Code complete, needs testing
- [TESTED] - Feature verified working
- [BLOCKED_EXTERNAL_DEPENDENCY] - Requires external service/credential

---

## PHASE 0: Architecture and Repository Foundation

### Repository Structure
- [PLANNED] Monorepo with frontend/, backend/, docs/, scripts/
- [PLANNED] Shared TypeScript types package
- [PLANNED] Docker compose for local development
- [PLANNED] CI/CD pipeline configuration

### Feature Manifest
- [PLANNED] This document created and maintained

---

## PHASE 1: Authentication, User System, Database, Application Shell and Navigation

### Database Models
- [PLANNED] Users table
- [PLANNED] Roles table (USER, CREATOR, ADMIN)
- [PLANNED] Sessions table
- [PLANNED] Projects table
- [PLANNED] Tasks table
- [PLANNED] Subtasks table
- [PLANNED] TaskRuns table
- [PLANNED] Schedules table
- [PLANNED] Files table
- [PLANNED] Folders table
- [PLANNED] Skills table
- [PLANNED] SkillVersions table
- [PLANNED] Connectors table
- [PLANNED] ConnectorCredentials table
- [PLANNED] Knowledge table
- [PLANNED] Memories table
- [PLANNED] Chats table
- [PLANNED] Messages table
- [PLANNED] Agents table
- [PLANNED] Models table
- [PLANNED] ModelProviders table
- [PLANNED] Approvals table
- [PLANNED] Blueprints table
- [PLANNED] Notifications table
- [PLANNED] AuditLogs table
- [PLANNED] BrowserSessions table
- [PLANNED] GeneratedApps table
- [PLANNED] GeneratedWebsites table
- [PLANNED] Settings table

### Authentication System
- [PLANNED] User registration with email/password
- [PLANNED] Secure password hashing (bcrypt/argon2)
- [PLANNED] JWT token authentication
- [PLANNED] Refresh token rotation
- [PLANNED] Session management
- [PLANNED] Password reset flow
- [PLANNED] Email verification
- [PLANNED] Role-based access control (RBAC)
- [PLANNED] Secure credential storage (encrypted)

### Application Shell
- [PLANNED] Main layout with sidebar navigation
- [PLANNED] Top bar with user menu, notifications
- [PLANNED] Responsive design (desktop-first)
- [PLANNED] Dark/light theme support
- [PLANNED] PWA manifest and service worker

### Navigation
- [PLANNED] Dashboard (Scheduled / Library / Projects tabs)
- [PLANNED] Project Workspace (Instructions / Files & Source / Skills / Connectors)
- [PLANNED] Chat interface
- [PLANNED] Settings
- [PLANNED] Admin Control Center (protected)
- [PLANNED] Back button on all secondary screens
- [PLANNED] Unsaved changes confirmation

---

## PHASE 2: Dashboard

### Scheduled Tab
- [PLANNED] Runs sub-tab: execution history with task name, status, start time, duration, project, result, error
- [PLANNED] Scheduled sub-tab: upcoming tasks with title, next execution, frequency, status, project, agent/model, connected services
- [PLANNED] Actions: Edit, Pause, Resume, Duplicate, Delete
- [PLANNED] Empty state: "No scheduled tasks yet"
- [PLANNED] "+ New schedule" button

### Library Tab
- [PLANNED] Search files
- [PLANNED] Categories: Websites, Documents, Images, Videos, Audios, Spreadsheets, Others
- [PLANNED] File operations: Open, Preview, Download, Share, Rename, Move, Delete, Duplicate, Attach to project, Attach to task
- [PLANNED] Bulk selection
- [PLANNED] Sort: Name, Date, Size, Type
- [PLANNED] Filter by category

### Projects Tab
- [PLANNED] Grid/list toggle
- [PLANNED] Project cards with icon, name, description, task count, file count, skill count, last modified, running status
- [PLANNED] Actions: Open, Rename, Duplicate, Archive, Delete, Export, Share
- [PLANNED] Create new project

---

## PHASE 3: Project Workspace

### Instructions Tab
- [PLANNED] Project avatar
- [PLANNED] Project name and description
- [PLANNED] Instructions editor with markdown support
- [PLANNED] Autosave
- [PLANNED] Version history
- [PLANNED] Restore previous version
- [PLANNED] Delete Project with destructive confirmation

### Files & Source Tab
- [PLANNED] Support: Images, Files, URLs, Web resources
- [PLANNED] Actions: Upload, Preview, Download, Rename, Delete, Move, Search, Attach, Detach
- [PLANNED] Add menu: Add images, Add files, Add resource links, Search the web

### Skills Tab
- [PLANNED] Display project skills with name, description, version, status, source, last updated
- [PLANNED] Actions: Enable, Disable, Configure, Update, Remove
- [PLANNED] Add Skill: Upload, Official, GitHub import, Build with Mark

### Connectors Tab
- [PLANNED] Connector framework with interface: authenticate, connect, disconnect, refresh, getStatus, execute, validatePermissions
- [PLANNED] Initial connectors: Google Drive, Google Calendar, Gmail, GitHub, Slack, Notion, Microsoft Outlook, Outlook Calendar, Outlook Mail, Shopify, Apify, Instagram, Meta Ads
- [PLANNED] OAuth and API-key support
- [PLANNED] Secure credential handling (no secrets in logs)

---

## PHASE 4: Chat and Autonomous Task Engine

### Chat Interface
- [PLANNED] Main input: "Assign a task or ask anything"
- [PLANNED] Support: Text, Images, Documents, Code, Tables, Links
- [PLANNED] Buttons: + (plus menu), Connectors, Microphone, Send

### Plus Menu Actions (ALL MUST WORK)
- [PLANNED] Camera
- [PLANNED] Picture
- [PLANNED] File
- [PLANNED] Connect My Computer
- [PLANNED] Add Skills
- [PLANNED] Build website
- [PLANNED] Develop apps
- [PLANNED] Create slides
- [PLANNED] Create image
- [PLANNED] Edit image
- [PLANNED] Wide Research
- [PLANNED] Scheduled tasks
- [PLANNED] Create spreadsheet
- [PLANNED] Create video
- [PLANNED] Generate audio
- [PLANNED] Playbook

### Voice Interface
- [PLANNED] Voice modes: Direct Task Execution, Meeting Minutes
- [PLANNED] Recording interface: Permission, Timer, Waveform, Stop, Transcription, Summary, Task creation

### Autonomous Agent Engine
- [PLANNED] Pipeline: Intent Analysis → Goal Decomposition → Plan Generation → Skill Selection → Model Selection → Tool Selection → Execution → Observation → Validation → Self-Correction → Memory Update → Result → Project Storage
- [PLANNED] Task state management with: Task ID, User, Project, Original request, Plan, Subtasks, Current state, Tool calls, Files, Errors, Approvals, Model usage, Execution timestamps, Final result

---

## PHASE 5: Quick Actions
- [PLANNED] All Plus Menu actions fully implemented as real workflows

---

## PHASE 6: Scheduled Tasks

### New Scheduled Task Form
- [PLANNED] Title
- [PLANNED] Repeat: Daily, Weekly, Monthly, No repeat
- [PLANNED] Time
- [PLANNED] Never Ends / End Date
- [PLANNED] Prompt
- [PLANNED] Skip Confirmations
- [PLANNED] Run Options: Same task, Separate task
- [PLANNED] Connectors
- [PLANNED] Agent
- [PLANNED] Project
- [PLANNED] Computer
- [PLANNED] Approval defaults to SAFE behavior

---

## PHASE 7: Memory and Knowledge

### Knowledge Base
- [PLANNED] Knowledge entries: Name, Use When, Content, Enabled
- [PLANNED] CRUD: Create, Edit, Delete, Enable, Disable, Search

### Memory Architecture (Multiple Layers)
- [PLANNED] Working Memory
- [PLANNED] Short-Term Memory
- [PLANNED] Episodic Memory
- [PLANNED] Semantic Memory
- [PLANNED] Procedural Memory
- [PLANNED] Project Memory
- [PLANNED] User Preference Memory
- [PLANNED] Task Memory
- [PLANNED] Failure Memory
- [PLANNED] Every entry: ID, Type, Content, Source, Created date, Updated date, Project association, Confidence, Importance, Enabled/disabled
- [PLANNED] User can inspect, edit, delete memories
- [PLANNED] No unnecessary sensitive data storage

---

## PHASE 8: Skills System and Skill Builder

### Skill Package Architecture
- [PLANNED] Manifest, metadata, instructions, tools, permissions, configuration, version, dependencies
- [PLANNED] Sources: Official, Uploaded, GitHub, Created by Mark

### Skill Lifecycle
- [PLANNED] Install, Validate, Enable, Disable, Configure, Update, Rollback, Remove

### Skill Builder
- [PLANNED] User describes skill in natural language
- [PLANNED] Mark generates skill package
- [PLANNED] Validate before installation

---

## PHASE 9: Connectors and Integrations

### Connector Framework
- [PLANNED] Extensible architecture for new connectors
- [PLANNED] Custom API connector builder
- [PLANNED] Custom MCP configuration (desktop)
- [PLANNED] Clear indication of MCP support per platform

---

## PHASE 10: Browser / Computer / Local Execution

### Browser Automation
- [PLANNED] Open browser, Navigate, Search, Click, Type, Scroll, Download, Upload, Read page, Extract structured info
- [PLANNED] Secure browser sessions
- [PLANNED] Persistent login state (explicit opt-in)

### Local Computer Control (Windows)
- [PLANNED] ComputerController, WindowManager, ProcessManager, FileSystemController, ClipboardController, BrowserController
- [PLANNED] Explicit permissions
- [PLANNED] Dangerous operations require confirmation

### Safe Code Execution
- [PLANNED] Isolated execution: Python, JavaScript/Node.js, Shell/PowerShell
- [PLANNED] Sandbox, Timeout, Resource limits, Filesystem isolation, Network policy, Process cleanup, Execution logs

---

## PHASE 11: AI Model Routing and Multi-Model Orchestration

### Model Router Architecture
- [PLANNED] AIProvider, ModelRegistry, ModelRouter, TaskPlanner, TaskExecutor, ToolExecutor, MemoryManager, ContextManager, AgentController, ApprovalManager, ExecutionLogger
- [PLANNED] Configurable model providers
- [PLANNED] Models for: Fast tasks, Deep reasoning, Coding, Research, Vision, Image generation, Audio, Video, Embeddings, Local inference
- [PLANNED] Router selects based on task type, cost, speed, capability, availability
- [PLANNED] Local + Cloud hybrid routing
- [PLANNED] Model fallback chain

---

## PHASE 12: Generative Workflows
- [PLANNED] Website creation
- [PLANNED] Application development
- [PLANNED] Slides
- [PLANNED] Images
- [PLANNED] Image editing
- [PLANNED] Research (Wide Research)
- [PLANNED] Spreadsheets
- [PLANNED] Video
- [PLANNED] Audio
- [PLANNED] Documents
- [PLANNED] Code

---

## PHASE 13: Settings, Data Controls, Mail Mark, Admin Control Center

### Settings Categories
- [PLANNED] Scheduled Tasks, Knowledge, Mail Mark, Data Controls, Cloud Browser, Skills, Connectors, Integrations, Account, Language, Appearance, Clear Cache

### Data Controls
- [PLANNED] Shared Tasks, Archived Tasks, Shared Files, Deployed Websites, Apps

### Cloud Browser
- [PLANNED] Persist login state, Cookies and website data

### Mail Mark
- [PLANNED] Settings, Inbox
- [PLANNED] Inbound task creation through email
- [PLANNED] Approved senders
- [PLANNED] Workflow email configuration
- [PLANNED] Authorization for privileged tasks

### Admin Control Center (Server-side Protected)
- [PLANNED] Creator management
- [PLANNED] Admin management
- [PLANNED] User lookup
- [PLANNED] Subscription management
- [PLANNED] Credits
- [PLANNED] Access control
- [PLANNED] Blacklist
- [PLANNED] Feature flags
- [PLANNED] Skill access
- [PLANNED] System configuration
- [PLANNED] Audit logs
- [PLANNED] Roles: USER, CREATOR, ADMIN

---

## PHASE 14: Advanced Autonomous Capabilities

### Self-Check Loop
- [PLANNED] Post-task evaluation: objective satisfaction, required files, valid calculations, readable outputs, tool failures, omitted requirements
- [PLANNED] Corrective work if not satisfied

### Task Checkpointing
- [PLANNED] Save checkpoints after meaningful operations

### Error Recovery
- [PLANNED] Analyze error, try alternative, retry where safe, ask user when necessary

### Multi-Agent Delegation
- [PLANNED] Specialized agents: Research, Coding, Browser, Document, Spreadsheet, Design, Data, Security, QA

### Agent Supervisor
- [PLANNED] Monitor delegated work, verify results

### Task Memory
- [PLANNED] Remember task-specific decisions

### User Preference Memory
- [PLANNED] Store explicitly approved preferences

### Project Memory
- [PLANNED] Store project-relevant knowledge

### Skill Memory
- [PLANNED] Remember successful workflows

### Failure Memory
- [PLANNED] Remember failure patterns to avoid repetition

---

## PHASE 15: Security, Permissions, Logging, Recovery, Reliability

### Security
- [PLANNED] Authentication, Authorization, RBAC
- [PLANNED] Secure sessions, Encrypted secrets
- [PLANNED] Audit logs
- [PLANNED] Rate limiting
- [PLANNED] Input validation, File validation, Upload limits
- [PLANNED] CSRF protection, XSS protection, SQL injection protection
- [PLANNED] Secure OAuth handling
- [PLANNED] Permission checks, Task authorization
- [PLANNED] Never expose: API keys, OAuth secrets, Database credentials, Admin credentials, Internal tokens

### Autonomy Levels
- [PLANNED] LEVEL 1: Ask before actions
- [PLANNED] LEVEL 2: Ask for sensitive actions
- [PLANNED] LEVEL 3: Autonomous within approved permissions
- [PLANNED] LEVEL 4: Scheduled autonomous operation

### Personal Operating Memory
- [PLANNED] Learn explicitly approved preferences

### Task Blueprints
- [PLANNED] Save successful workflows as reusable blueprints

### Self-Healing Workflows
- [PLANNED] Diagnose, try alternative, retry, continue, pause for user intervention

### Multi-Agent Workspace Visualization
- [PLANNED] Supervisor, Research, Coding, Browser, Document, QA agents with status

### Task Graph
- [PLANNED] Dependency graph visualization

### Context Compression
- [PLANNED] Summarize completed context, keep important state, discard unnecessary

### Workflow Simulator / Dry Run
- [PLANNED] Preview Plan, Dry Run (show tools, files, connectors, actions, risks), Execute

### Approval Center
- [PLANNED] Central dashboard for pending actions: Send email, Publish website, Delete files, Execute sensitive command, Spend money, Post publicly

### Agent Activity Timeline
- [PLANNED] Concise events: Planning, Researching, Reading file, Calling connector, Creating spreadsheet, Validating result, Completed

### Project Snapshots
- [PLANNED] Create, Restore, Compare versions

### Skill Dependency Engine
- [PLANNED] Skills declare dependencies, validate before execution

### Knowledge Graph
- [PLANNED] Connect: Projects, People, Companies, Files, Tasks, Skills, Knowledge, Sources

---

## PHASE 16: QA, Testing, Production Packaging

### Windows Packaging
- [PLANNED] Actual Windows installer with executable, installer, uninstaller, desktop shortcut, start menu entry, app data directory, logging, crash recovery

### Web Deployment
- [PLANNED] Production deployable web app, environment variable documentation, no hardcoded secrets

### Testing
- [PLANNED] Unit tests: Auth, AuthZ, Navigation, Projects, Files, Skills, Connectors, Scheduling, Tasks, Approvals, Memory, Knowledge, Admin, Offline, Sync, Error recovery
- [PLANNED] End-to-end tests
- [PLANNED] Performance: Lazy loading, Pagination, Caching, Background processing, Debounced search, Optimistic UI, Virtualized lists, Indexed queries

### Documentation
- [PLANNED] README, Architecture docs, Database schema, Env vars, Deployment, Windows install, Connector setup, Skill dev, API docs, Troubleshooting

---

## Offline-First Architecture
- [PLANNED] Local projects, files, task history, memory, settings, skills, local model execution, local code execution, local scheduling, local task queue
- [PLANNED] Sync on reconnect with conflict resolution, no silent overwrites

---

## Long-Running Task Engine
- [PLANNED] Persistent task queue, Background workers, Checkpoints, Retry policies, Exponential backoff, Failure recovery, Pause, Resume, Cancel, Retry failed step, Continue from checkpoint, Timeout handling, Dependency management, Subtask graph
- [PLANNED] Recover tasks on app restart

---

## Research Engine
- [PLANNED] Query planning, Parallel searches, Source collection, Source extraction, Evidence comparison, Deduplication, Citation tracking, Synthesis, Report generation
- [PLANNED] Store source URLs and evidence metadata
- [PLANNED] No fabricated sources

---

## Notification System
- [PLANNED] Task starts, requires approval, completes, fails, scheduled runs, long-running pauses, connector expires, security events

---

## Audit System
- [PLANNED] User actions, Task executions, Agent decisions metadata, Tool calls, Errors, Approvals, Connector actions, Admin actions
- [PLANNED] No hidden chain-of-thought, store concise execution summaries