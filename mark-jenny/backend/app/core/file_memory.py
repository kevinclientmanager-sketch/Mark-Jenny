
"""
Mark-Imti File-Based Memory - Persistent memory with file system storage
Supports semantic search, importance scoring, consolidation, and checkpoints
"""

import json
import os
import hashlib
import time
from enum import Enum
from typing import Any, Optional
from dataclasses import dataclass, field
from datetime import datetime


class MemoryType(Enum):
    EPISODIC = "episodic"
    SEMANTIC = "semantic"
    PROCEDURAL = "procedural"
    WORKING = "working"
    CHECKPOINT = "checkpoint"


class ImportanceLevel(Enum):
    LOW = 1
    MEDIUM = 5
    HIGH = 8
    CRITICAL = 10


@dataclass
class MemoryEntry:
    id: str
    memory_type: MemoryType
    content: str
    summary: str
    tags: list[str]
    importance: ImportanceLevel
    access_count: int = 0
    last_accessed: Optional[str] = None
    created_at: str = field(default_factory=lambda: datetime.utcnow().isoformat())
    expires_at: Optional[str] = None
    source: str = ""
    associations: list[str] = field(default_factory=list)
    metadata: dict = field(default_factory=dict)


@dataclass
class MemoryCheckpoint:
    id: str
    task_id: str
    state: dict
    memories_used: list[str]
    created_at: str = field(default_factory=lambda: datetime.utcnow().isoformat())


class FileMemory:
    def __init__(self, memory_dir: str = None):
        self.memory_dir = memory_dir or os.path.join(
            os.path.expanduser("~"), ".mark-imti", "memory"
        )
        os.makedirs(self.memory_dir, exist_ok=True)
        self._index_path = os.path.join(self.memory_dir, "index.json")
        self._memories: dict[str, MemoryEntry] = {}
        self._checkpoints: dict[str, MemoryCheckpoint] = {}
        self._load_index()

    def _load_index(self):
        if os.path.exists(self._index_path):
            try:
                with open(self._index_path) as f:
                    data = json.load(f)
                for mid, mdata in data.get("memories", {}).items():
                    mdata["importance"] = ImportanceLevel(mdata["importance"])
                    mdata["memory_type"] = MemoryType(mdata["memory_type"])
                    self._memories[mid] = MemoryEntry(**mdata)
                for cid, cdata in data.get("checkpoints", {}).items():
                    self._checkpoints[cid] = MemoryCheckpoint(**cdata)
            except Exception:
                pass

    def _save_index(self):
        data = {"memories": {}, "checkpoints": {}}
        for mid, mem in self._memories.items():
            data["memories"][mid] = {
                "id": mem.id, "memory_type": mem.memory_type.value,
                "content": mem.content, "summary": mem.summary,
                "tags": mem.tags, "importance": mem.importance.value,
                "access_count": mem.access_count, "last_accessed": mem.last_accessed,
                "created_at": mem.created_at, "expires_at": mem.expires_at,
                "source": mem.source, "associations": mem.associations,
                "metadata": mem.metadata,
            }
        for cid, cp in self._checkpoints.items():
            data["checkpoints"][cid] = {
                "id": cp.id, "task_id": cp.task_id,
                "state": cp.state, "memories_used": cp.memories_used,
                "created_at": cp.created_at,
            }
        with open(self._index_path, "w") as f:
            json.dump(data, f, indent=2)

    def store(self, content: str, memory_type: MemoryType = MemoryType.EPISODIC,
              tags: list[str] = None, importance: ImportanceLevel = ImportanceLevel.MEDIUM,
              summary: str = "", source: str = "", metadata: dict = None) -> MemoryEntry:
        mid = hashlib.sha256(content.encode()).hexdigest()[:16]
        if mid in self._memories:
            self._memories[mid].access_count += 1
            self._memories[mid].last_accessed = datetime.utcnow().isoformat()
            self._save_index()
            return self._memories[mid]
        entry = MemoryEntry(
            id=mid, memory_type=memory_type, content=content,
            summary=summary or content[:200], tags=tags or [],
            importance=importance, source=source, metadata=metadata or {},
        )
        self._memories[mid] = entry
        file_path = os.path.join(self.memory_dir, f"{mid}.md")
        with open(file_path, "w") as f:
            f.write(f"# {entry.summary}\n\n")
            f.write(f"Type: {entry.memory_type.value}\n")
            f.write(f"Importance: {entry.importance.value}/10\n")
            f.write(f"Tags: {', '.join(entry.tags)}\n\n")
            f.write(content)
        self._save_index()
        return entry

    def recall(self, query: str = None, memory_type: MemoryType = None,
               tags: list[str] = None, min_importance: int = 0,
               limit: int = 10) -> list[MemoryEntry]:
        results = list(self._memories.values())
        if memory_type:
            results = [m for m in results if m.memory_type == memory_type]
        if tags:
            results = [m for m in results if any(t in m.tags for t in tags)]
        if min_importance:
            results = [m for m in results if m.importance.value >= min_importance]
        if query:
            ql = query.lower()
            scored = []
            for m in results:
                score = 0
                if ql in m.content.lower(): score += 3
                if ql in m.summary.lower(): score += 2
                if any(ql in t.lower() for t in m.tags): score += 1
                score += m.importance.value / 10
                score += min(m.access_count / 10, 0.5)
                if score > 0: scored.append((score, m))
            scored.sort(key=lambda x: x[0], reverse=True)
            results = [m for _, m in scored[:limit]]
        else:
            results.sort(key=lambda m: (m.importance.value, m.access_count), reverse=True)
            results = results[:limit]
        for m in results:
            m.access_count += 1
            m.last_accessed = datetime.utcnow().isoformat()
        self._save_index()
        return results

    def forget(self, memory_id: str) -> bool:
        if memory_id in self._memories:
            del self._memories[memory_id]
            file_path = os.path.join(self.memory_dir, f"{memory_id}.md")
            if os.path.exists(file_path): os.remove(file_path)
            self._save_index()
            return True
        return False

    def checkpoint(self, task_id: str, state: dict, memories_used: list[str] = None) -> MemoryCheckpoint:
        cp_id = f"cp-{int(time.time())}-{task_id[:8]}"
        cp = MemoryCheckpoint(id=cp_id, task_id=task_id, state=state, memories_used=memories_used or [])
        self._checkpoints[cp_id] = cp
        self.store(
            content=json.dumps({"checkpoint": cp_id, "state": state}, indent=2),
            memory_type=MemoryType.CHECKPOINT, tags=["checkpoint", task_id],
            importance=ImportanceLevel.HIGH, summary=f"Checkpoint for task {task_id}",
        )
        self._save_index()
        return cp

    def restore_checkpoint(self, checkpoint_id: str) -> Optional[dict]:
        cp = self._checkpoints.get(checkpoint_id)
        return cp.state if cp else None

    def consolidate(self) -> int:
        low = [m for m in self._memories.values() if m.importance.value <= 3 and m.access_count <= 2]
        if len(low) < 3: return 0
        groups = {}
        for m in low:
            key = tuple(sorted(m.tags)[:3]) if m.tags else ("untagged",)
            groups.setdefault(key, []).append(m)
        consolidated = 0
        for tag_group, memories in groups.items():
            if len(memories) < 2: continue
            combined = "\n".join(m.content[:200] for m in memories)
            tags = list(set(t for m in memories for t in m.tags))[:5]
            self.store(combined, MemoryType.SEMANTIC, tags, ImportanceLevel.MEDIUM, summary=f"Consolidated: {tag_group}")
            for m in memories: self.forget(m.id)
            consolidated += len(memories)
        return consolidated

    def get_stats(self) -> dict:
        type_counts = {}
        for m in self._memories.values():
            t = m.memory_type.value
            type_counts[t] = type_counts.get(t, 0) + 1
        return {
            "total_memories": len(self._memories),
            "total_checkpoints": len(self._checkpoints),
            "type_distribution": type_counts,
            "total_access": sum(m.access_count for m in self._memories.values()),
        }
