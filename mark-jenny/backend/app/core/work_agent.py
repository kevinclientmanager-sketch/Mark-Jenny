
"""
Mark-Imti Work Agent - Autonomous work assistant
Handles email, files, PDFs, workflow learning, task prediction
"""

import os
import json
import time
import uuid
import shutil
import hashlib
from enum import Enum
from typing import Any, Optional
from dataclasses import dataclass, field
from datetime import datetime


class WorkTaskType(Enum):
    EMAIL = "email"
    FILE_MANAGE = "file_manage"
    PDF_FILL = "pdf_fill"
    DOCUMENT = "document"
    ORGANIZE = "organize"
    SEARCH = "search"
    RESEARCH = "research"
    SCHEDULE = "schedule"
    DATA_ENTRY = "data_entry"
    WORKFLOW = "workflow"
    CUSTOM = "custom"


class WorkTaskStatus(Enum):
    QUEUED = "queued"
    RUNNING = "running"
    WAITING_APPROVAL = "waiting_approval"
    COMPLETED = "completed"
    FAILED = "failed"
    PAUSED = "paused"


class LearningPatternType(Enum):
    ROUTINE = "routine"
    PREFERENCE = "preference"
    WORKFLOW = "workflow"
    SCHEDULE = "schedule"
    FILE_ORG = "file_org"
    EMAIL_STYLE = "email_style"


@dataclass
class WorkTask:
    id: str
    task_type: WorkTaskType
    description: str
    params: dict
    status: WorkTaskStatus = WorkTaskStatus.QUEUED
    result: Optional[dict] = None
    error: Optional[str] = None
    created_at: str = field(default_factory=lambda: datetime.utcnow().isoformat())
    started_at: Optional[str] = None
    completed_at: Optional[str] = None
    requires_approval: bool = True
    approved: bool = False


@dataclass
class UserPattern:
    id: str
    pattern_type: LearningPatternType
    trigger: str
    action: str
    frequency: int = 1
    last_seen: str = field(default_factory=lambda: datetime.utcnow().isoformat())
    confidence: float = 0.5
    examples: list[dict] = field(default_factory=list)


@dataclass
class WorkflowRecord:
    id: str
    task_type: WorkTaskType
    description: str
    steps: list[dict]
    outcome: str
    duration_seconds: float
    timestamp: str = field(default_factory=lambda: datetime.utcnow().isoformat())
    user_feedback: Optional[str] = None


class WorkAgent:
    def __init__(self, work_dir: str = None, model_caller=None):
        self.work_dir = work_dir or os.path.join(
            os.path.expanduser("~"), ".mark-imti", "work"
        )
        os.makedirs(self.work_dir, exist_ok=True)
        self.model = model_caller
        self._tasks: dict[str, WorkTask] = {}
        self._patterns: dict[str, UserPattern] = {}
        self._records: list[WorkflowRecord] = []
        self._load_state()

    def _state_path(self) -> str:
        return os.path.join(self.work_dir, "work_agent_state.json")

    def _load_state(self):
        path = self._state_path()
        if os.path.exists(path):
            try:
                with open(path) as f:
                    data = json.load(f)
                for pid, pdata in data.get("patterns", {}).items():
                    pdata["pattern_type"] = LearningPatternType(pdata["pattern_type"])
                    self._patterns[pid] = UserPattern(**pdata)
                for rdata in data.get("records", []):
                    rdata["task_type"] = WorkTaskType(rdata["task_type"])
                    self._records.append(WorkflowRecord(**rdata))
            except Exception:
                pass

    def _save_state(self):
        data = {
            "patterns": {
                pid: {
                    "id": p.id, "pattern_type": p.pattern_type.value,
                    "trigger": p.trigger, "action": p.action,
                    "frequency": p.frequency, "last_seen": p.last_seen,
                    "confidence": p.confidence, "examples": p.examples,
                }
                for pid, p in self._patterns.items()
            },
            "records": [
                {
                    "id": r.id, "task_type": r.task_type.value,
                    "description": r.description, "steps": r.steps,
                    "outcome": r.outcome, "duration_seconds": r.duration_seconds,
                    "timestamp": r.timestamp, "user_feedback": r.user_feedback,
                }
                for r in self._records[-500:]
            ],
        }
        with open(self._state_path(), "w") as f:
            json.dump(data, f, indent=2)

    def create_task(self, task_type: WorkTaskType, description: str,
                    params: dict = None, requires_approval: bool = True) -> WorkTask:
        task = WorkTask(
            id=str(uuid.uuid4()),
            task_type=task_type,
            description=description,
            params=params or {},
            requires_approval=requires_approval,
        )
        self._tasks[task.id] = task
        self._save_state()
        return task

    def approve_task(self, task_id: str) -> bool:
        task = self._tasks.get(task_id)
        if task:
            task.approved = True
            task.status = WorkTaskStatus.RUNNING
            task.started_at = datetime.utcnow().isoformat()
            self._save_state()
            return True
        return False

    def complete_task(self, task_id: str, result: dict) -> bool:
        task = self._tasks.get(task_id)
        if task:
            task.status = WorkTaskStatus.COMPLETED
            task.result = result
            task.completed_at = datetime.utcnow().isoformat()
            self._record_workflow(task, result)
            self._learn_from_task(task)
            self._save_state()
            return True
        return False

    def fail_task(self, task_id: str, error: str) -> bool:
        task = self._tasks.get(task_id)
        if task:
            task.status = WorkTaskStatus.FAILED
            task.error = error
            task.completed_at = datetime.utcnow().isoformat()
            self._save_state()
            return True
        return False

    def get_task(self, task_id: str) -> Optional[WorkTask]:
        return self._tasks.get(task_id)

    def get_pending_tasks(self) -> list[WorkTask]:
        return [t for t in self._tasks.values()
                if t.status in (WorkTaskStatus.QUEUED, WorkTaskStatus.WAITING_APPROVAL)]

    def get_active_tasks(self) -> list[WorkTask]:
        return [t for t in self._tasks.values()
                if t.status == WorkTaskStatus.RUNNING]

    def get_completed_tasks(self, limit: int = 50) -> list[WorkTask]:
        completed = [t for t in self._tasks.values()
                     if t.status == WorkTaskStatus.COMPLETED]
        completed.sort(key=lambda t: t.completed_at or "", reverse=True)
        return completed[:limit]

    async def execute_file_task(self, action: str, params: dict) -> dict:
        if action == "organize":
            return await self._organize_files(params)
        elif action == "find":
            return await self._find_files(params)
        elif action == "rename":
            return await self._rename_files(params)
        elif action == "sort":
            return await self._sort_files(params)
        elif action == "backup":
            return await self._backup_files(params)
        elif action == "list":
            return await self._list_files(params)
        return {"error": f"Unknown file action: {action}"}

    async def _organize_files(self, params: dict) -> dict:
        source_dir = params.get("source_dir", os.path.expanduser("~/Downloads"))
        rule = params.get("rule", "type")
        if not os.path.exists(source_dir):
            return {"error": f"Directory not found: {source_dir}"}
        organized = {}
        for item in os.listdir(source_dir):
            src = os.path.join(source_dir, item)
            if os.path.isfile(src):
                ext = os.path.splitext(item)[1].lower()
                if rule == "type":
                    category = self._get_file_category(ext)
                elif rule == "date":
                    mtime = os.path.getmtime(src)
                    category = datetime.fromtimestamp(mtime).strftime("%Y-%m")
                else:
                    category = "other"
                dest_dir = os.path.join(source_dir, category)
                os.makedirs(dest_dir, exist_ok=True)
                dest = os.path.join(dest_dir, item)
                if not os.path.exists(dest):
                    shutil.move(src, dest)
                    organized[item] = category
        return {"organized": len(organized), "files": organized}

    def _get_file_category(self, ext: str) -> str:
        categories = {
            ".jpg": "images", ".jpeg": "images", ".png": "images", ".gif": "images", ".svg": "images",
            ".pdf": "documents", ".doc": "documents", ".docx": "documents", ".txt": "documents",
            ".xls": "spreadsheets", ".xlsx": "spreadsheets", ".csv": "spreadsheets",
            ".mp4": "videos", ".avi": "videos", ".mov": "videos",
            ".mp3": "audio", ".wav": "audio", ".flac": "audio",
            ".zip": "archives", ".rar": "archives", ".7z": "archives",
            ".py": "code", ".js": "code", ".ts": "code", ".html": "code", ".css": "code",
        }
        return categories.get(ext, "other")

    async def _find_files(self, params: dict) -> dict:
        search_dir = params.get("search_dir", os.path.expanduser("~"))
        pattern = params.get("pattern", "")
        max_depth = params.get("max_depth", 3)
        found = []
        for root, dirs, files in os.walk(search_dir):
            depth = root.replace(search_dir, "").count(os.sep)
            if depth >= max_depth:
                dirs.clear()
                continue
            for f in files:
                if pattern.lower() in f.lower():
                    found.append({"path": os.path.join(root, f), "name": f})
                    if len(found) >= 100:
                        break
            if len(found) >= 100:
                break
        return {"found": len(found), "files": found}

    async def _rename_files(self, params: dict) -> dict:
        directory = params.get("directory", os.path.expanduser("~/Downloads"))
        pattern = params.get("pattern", "sequential")
        prefix = params.get("prefix", "file")
        if not os.path.exists(directory):
            return {"error": f"Directory not found: {directory}"}
        renamed = {}
        counter = 1
        for item in sorted(os.listdir(directory)):
            src = os.path.join(directory, item)
            if os.path.isfile(src):
                ext = os.path.splitext(item)[1]
                if pattern == "sequential":
                    new_name = f"{prefix}_{counter:04d}{ext}"
                elif pattern == "date":
                    mtime = os.path.getmtime(src)
                    new_name = f"{datetime.fromtimestamp(mtime).strftime('%Y%m%d_%H%M%S')}_{item}"
                else:
                    new_name = item
                dest = os.path.join(directory, new_name)
                if src != dest and not os.path.exists(dest):
                    os.rename(src, dest)
                    renamed[item] = new_name
                    counter += 1
        return {"renamed": len(renamed), "files": renamed}

    async def _sort_files(self, params: dict) -> dict:
        directory = params.get("directory", os.path.expanduser("~/Downloads"))
        sort_by = params.get("sort_by", "extension")
        if not os.path.exists(directory):
            return {"error": f"Directory not found: {directory}"}
        sorted_files = {}
        for item in os.listdir(directory):
            src = os.path.join(directory, item)
            if os.path.isfile(src):
                if sort_by == "extension":
                    key = os.path.splitext(item)[1].lower() or "no_extension"
                elif sort_by == "size":
                    size = os.path.getsize(src)
                    if size < 1024: key = "tiny"
                    elif size < 1024*1024: key = "small"
                    elif size < 1024*1024*1024: key = "medium"
                    else: key = "large"
                elif sort_by == "date":
                    key = datetime.fromtimestamp(os.path.getmtime(src)).strftime("%Y-%m-%d")
                else:
                    key = "ungrouped"
                sorted_files.setdefault(key, []).append(item)
        return {"sorted_groups": len(sorted_files), "groups": sorted_files}

    async def _backup_files(self, params: dict) -> dict:
        source = params.get("source")
        destination = params.get("destination")
        if not source or not destination:
            return {"error": "source and destination required"}
        if not os.path.exists(source):
            return {"error": f"Source not found: {source}"}
        os.makedirs(destination, exist_ok=True)
        timestamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
        backup_name = f"backup_{timestamp}"
        backup_path = os.path.join(destination, backup_name)
        if os.path.isfile(source):
            shutil.copy2(source, backup_path)
        else:
            shutil.copytree(source, backup_path)
        return {"backup_path": backup_path, "source": source}

    async def _list_files(self, params: dict) -> dict:
        directory = params.get("directory", os.path.expanduser("~"))
        if not os.path.exists(directory):
            return {"error": f"Directory not found: {directory}"}
        items = []
        for item in os.listdir(directory)[:200]:
            path = os.path.join(directory, item)
            items.append({
                "name": item,
                "is_dir": os.path.isdir(path),
                "size": os.path.getsize(path) if os.path.isfile(path) else 0,
                "modified": datetime.fromtimestamp(os.path.getmtime(path)).isoformat(),
            })
        return {"directory": directory, "count": len(items), "items": items}

    async def draft_email(self, params: dict) -> dict:
        to = params.get("to", "")
        subject = params.get("subject", "")
        context = params.get("context", "")
        tone = params.get("tone", "professional")
        if self.model:
            prompt = f"""Draft an email with these details:
To: {to}
Subject: {subject}
Context: {context}
Tone: {tone}

Write a complete, ready-to-send email."""
            try:
                content = await self.model.complete(prompt, max_tokens=2000)
                if content and "unable to process this request" not in content.lower():
                    return {"draft": content, "to": to, "subject": subject,
                            "status": "draft", "ai_generated": True}
            except Exception:
                pass
        # No model answered: say so rather than shipping a template as an "AI draft".
        return {
            "draft": None,
            "to": to,
            "subject": subject,
            "status": "unavailable",
            "ai_generated": False,
            "note": "No AI model produced a draft. Connect a provider in Settings > AI Studio "
                    "and try again - a template will not be presented as an AI draft.",
        }

    async def read_email(self, params: dict) -> dict:
        return {"emails": [], "count": 0, "note": "Email connector not configured. Connect Gmail/Outlook in Connectors settings."}

    def learn_pattern(self, trigger: str, action: str, pattern_type: LearningPatternType = LearningPatternType.WORKFLOW):
        for p in self._patterns.values():
            if p.trigger == trigger and p.action == action:
                p.frequency += 1
                p.confidence = min(1.0, p.confidence + 0.05)
                p.last_seen = datetime.utcnow().isoformat()
                self._save_state()
                return
        pid = hashlib.sha256(f"{trigger}:{action}".encode()).hexdigest()[:12]
        self._patterns[pid] = UserPattern(
            id=pid, pattern_type=pattern_type,
            trigger=trigger, action=action,
        )
        self._save_state()

    def predict_needs(self, context: dict = None) -> list[dict]:
        """Predictions derived only from learned patterns.

        The previous version also emitted fixed time-of-day suggestions
        ("Ready for your morning summary?") with invented confidence scores.
        """
        predictions = []
        high_freq = sorted(self._patterns.values(), key=lambda p: p.frequency, reverse=True)[:5]
        for p in high_freq:
            if p.confidence > 0.6:
                predictions.append({
                    "need": p.trigger,
                    "confidence": round(p.confidence, 2),
                    "suggestion": f"Based on {p.frequency} learned occurrence(s): run '{p.action}'?",
                    "pattern_id": p.id,
                    "source": "learned_pattern",
                })
        return predictions

    def get_learned_patterns(self) -> list[dict]:
        return [
            {
                "id": p.id,
                "type": p.pattern_type.value,
                "trigger": p.trigger,
                "action": p.action,
                "frequency": p.frequency,
                "confidence": p.confidence,
                "last_seen": p.last_seen,
            }
            for p in sorted(self._patterns.values(), key=lambda p: p.frequency, reverse=True)
        ]

    def _record_workflow(self, task: WorkTask, result: dict):
        record = WorkflowRecord(
            id=str(uuid.uuid4()),
            task_type=task.task_type,
            description=task.description,
            steps=[{"action": task.description, "params": task.params, "result": result}],
            outcome="completed",
            duration_seconds=0,
        )
        self._records.append(record)

    def _learn_from_task(self, task: WorkTask):
        self.learn_pattern(
            trigger=task.task_type.value,
            action=task.description,
            pattern_type=LearningPatternType.WORKFLOW,
        )

    def get_records(self, limit: int = 100) -> list[dict]:
        return [
            {
                "id": r.id,
                "task_type": r.task_type.value,
                "description": r.description,
                "outcome": r.outcome,
                "timestamp": r.timestamp,
                "duration": r.duration_seconds,
            }
            for r in self._records[-limit:]
        ]

    def get_stats(self) -> dict:
        return {
            "total_tasks": len(self._tasks),
            "completed": sum(1 for t in self._tasks.values() if t.status == WorkTaskStatus.COMPLETED),
            "failed": sum(1 for t in self._tasks.values() if t.status == WorkTaskStatus.FAILED),
            "pending": sum(1 for t in self._tasks.values() if t.status in (WorkTaskStatus.QUEUED, WorkTaskStatus.WAITING_APPROVAL)),
            "patterns_learned": len(self._patterns),
            "workflow_records": len(self._records),
        }
