# Database Schema (34 tables, SQLite, SQLAlchemy 2)

All tables `app/models/*.py` with FK, indexes, timestamps, `ondelete` cascades. Created via `app/db/init_db.py`.

## Core
- **users** (`user.py`): id, email unique, hashed_password, full_name, avatar_url, role `USER/CREATOR/ADMIN`, is_active, is_verified, created_at, last_login_at
- **sessions**: user_id FK CASCADE, refresh_token unique, expires_at, revoked_at
- **projects**: owner_id FK, name, description, icon, instructions, status `ACTIVE/ARCHIVED/DELETED`, deleted_at
- **project_skills**: project_id, skill_id, enabled, config JSON

## Tasks
- **tasks**: owner_id, project_id, parent_task_id, title, status `PENDING/PLANNING/RUNNING/WAITING_APPROVAL/PAUSED/COMPLETED/FAILED/CANCELLED`, priority, autonomy_level, plan JSON, current_step, model_used, result JSON, error, checkpoints in plan
- **task_runs**: task_id, run_number, status, plan, tool_calls, model_usage, files_created, duration
- **subtasks**: task_id, title, status, order, assigned_agent, required_skills/tools, result

## Files
- **files**: owner_id, project_id, task_id, folder_id, name, original_name, path, storage_key, mime_type, file_type `IMAGE/DOCUMENT/VIDEO/AUDIO/SPREADSHEET/CODE/ARCHIVE/WEBSITE/OTHER`, size, hash, file_metadata, deleted_at
- **folders**: name, path, parent_id, project_id, owner_id

## Skills/Connectors/Knowledge
- **skills**: name, version, source `OFFICIAL/UPLOADED/GITHUB/CREATED_BY_MARK`, status, manifest, instructions, tools, permissions, config_schema, dependencies, owner_id
- **skill_versions**: skill_id, version, manifest, changelog
- **connectors**: name, type `GOOGLE_DRIVE/.../CUSTOM_API/MCP`, config_schema, is_system
- **connector_credentials**: connector_id, user_id, project_id, auth_type, encrypted_credentials (encrypted), status `NOT_CONNECTED/CONNECTED/EXPIRED`, last_sync_at
- **knowledge**: name, use_when, content, enabled, project_id, confidence, importance, tags JSON
- **memories**: type `WORKING/SHORT_TERM/EPISODIC/SEMANTIC/PROCEDURAL/PROJECT/USER_PREFERENCE/TASK/FAILURE`, content, source, confidence, importance, enabled, owner_id, project_id, task_id, memory_metadata JSON

## Chat/AI
- **chats**: owner_id, project_id, task_id, title, model_used
- **messages**: chat_id, role `USER/ASSISTANT/SYSTEM/TOOL`, content, tool_calls, message_metadata JSON
- **models**: name, provider `OPENAI/ANTHROPIC/GOOGLE/OLLAMA/AZURE/CUSTOM`, model_id, capabilities JSON, context_window, cost_per_1k, is_local, is_active
- **model_provider_configs**: user_id, provider, api_key_encrypted, base_url, is_default
- **agents**: name, type `PRIMARY/RESEARCH/CODING/BROWSER/DOCUMENT/SPREADSHEET/DESIGN/DATA/SECURITY/QA/SUPERVISOR`, model_id FK, available_tools/skills JSON

## Scheduling/Approvals
- **schedules**: owner_id, project_id, agent_id, title, prompt, frequency `DAILY/WEEKLY/MONTHLY/ONCE/CRON`, time_of_day, timezone, run_option `SAME/SEPARATE`, skip_confirmations, connectors JSON, config JSON (holds computer), is_active, next_run_at, run_count
- **schedule_runs**: schedule_id, task_id, status, error, duration
- **approvals**: type `SEND_EMAIL/PUBLISH_WEBSITE/DELETE_FILES/EXECUTE_COMMAND/SPEND_MONEY/POST_PUBLICLY/...`, title, details JSON, risk_level, task_id, user_id, requested_by, status `PENDING/APPROVED/REJECTED`, decided_by, expires_at

## System
- **notifications**: user_id, task_id, type `TASK_STARTED/.../SECURITY_EVENT`, title, is_read
- **audit_logs**: user_id, action `LOGIN/PROJECT_CREATE/TASK_START/...`, resource_type/id, details JSON, success, ip
- **generated_websites/apps**: owner_id, project_id, task_id, name, prompt, status, files JSON, preview/deploy_url
- **browser_sessions**: owner_id, task_id, browser_type, cookies JSON, is_persistent
