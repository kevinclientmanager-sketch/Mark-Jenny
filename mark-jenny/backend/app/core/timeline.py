"""
Mark-Imti Timeline — Session timeline and playback
Records all agent actions for replay, audit, and learning
"""

import json
import time
from enum import Enum
from typing import Any, Optional
from dataclasses import dataclass, field
from datetime import datetime


class TimelineEventType(Enum):
    USER_INPUT = "user_input"
    AGENT_THINK = "agent_think"
    AGENT_PLAN = "agent_plan"
    TOOL_CALL = "tool_call"
    TOOL_RESULT = "tool_result"
    AGENT_RESPONSE = "agent_response"
    ERROR = "error"
    CHECKPOINT = "checkpoint"
    STATE_CHANGE = "state_change"
    PROACTIVE = "proactive"
    SYSTEM = "system"


@dataclass
class TimelineEvent:
    id: str
    event_type: TimelineEventType
    data: dict
    timestamp: float
    parent_id: Optional[str] = None
    duration_ms: Optional[int] = None
    metadata: dict = field(default_factory=dict)


class Timeline:
    """
    Records and replays agent session timelines.
    Enables step-by-step playback of agent reasoning.
    """

    def __init__(self, session_id: str = None):
        self.session_id = session_id or f"session-{int(time.time())}"
        self.events: list[TimelineEvent] = []
        self._event_counter = 0
        self._bookmarks: dict[str, int] = {}

    def record(self, event_type: TimelineEventType, data: dict,
               parent_id: str = None, duration_ms: int = None,
               metadata: dict = None) -> TimelineEvent:
        self._event_counter += 1
        event = TimelineEvent(
            id=f"evt-{self._event_counter}",
            event_type=event_type,
            data=data,
            timestamp=time.time(),
            parent_id=parent_id,
            duration_ms=duration_ms,
            metadata=metadata or {},
        )
        self.events.append(event)
        return event

    def record_user_input(self, text: str) -> TimelineEvent:
        return self.record(TimelineEventType.USER_INPUT, {"text": text})

    def record_thinking(self, thought: str, tokens_used: int = 0) -> TimelineEvent:
        return self.record(TimelineEventType.AGENT_THINK, {
            "thought": thought,
            "tokens_used": tokens_used,
        })

    def record_plan(self, plan: dict) -> TimelineEvent:
        return self.record(TimelineEventType.AGENT_PLAN, {"plan": plan})

    def record_tool_call(self, tool: str, params: dict) -> TimelineEvent:
        return self.record(TimelineEventType.TOOL_CALL, {
            "tool": tool,
            "params": params,
        })

    def record_tool_result(self, tool: str, result: dict, parent_id: str = None,
                           duration_ms: int = None) -> TimelineEvent:
        return self.record(
            TimelineEventType.TOOL_RESULT,
            {"tool": tool, "result": result},
            parent_id=parent_id,
            duration_ms=duration_ms,
        )

    def record_response(self, text: str) -> TimelineEvent:
        return self.record(TimelineEventType.AGENT_RESPONSE, {"text": text})

    def record_error(self, error: str, context: dict = None) -> TimelineEvent:
        return self.record(TimelineEventType.ERROR, {
            "error": error,
            "context": context or {},
        })

    def record_checkpoint(self, state: dict) -> TimelineEvent:
        return self.record(TimelineEventType.CHECKPOINT, {"state": state})

    def record_state_change(self, old_state: str, new_state: str) -> TimelineEvent:
        return self.record(TimelineEventType.STATE_CHANGE, {
            "from": old_state,
            "to": new_state,
        })

    def bookmark(self, name: str):
        self._bookmarks[name] = len(self.events) - 1

    def get_bookmark(self, name: str) -> Optional[int]:
        return self._bookmarks.get(name)

    def get_events(self, event_type: TimelineEventType = None,
                   since: float = None) -> list[TimelineEvent]:
        events = self.events
        if event_type:
            events = [e for e in events if e.event_type == event_type]
        if since:
            events = [e for e in events if e.timestamp >= since]
        return events

    def get_duration(self) -> float:
        if len(self.events) < 2:
            return 0
        return self.events[-1].timestamp - self.events[0].timestamp

    def get_stats(self) -> dict:
        type_counts = {}
        total_duration = 0
        for event in self.events:
            t = event.event_type.value
            type_counts[t] = type_counts.get(t, 0) + 1
            if event.duration_ms:
                total_duration += event.duration_ms

        return {
            "session_id": self.session_id,
            "total_events": len(self.events),
            "event_types": type_counts,
            "total_duration_ms": total_duration,
            "wall_duration_s": self.get_duration(),
            "bookmarks": list(self._bookmarks.keys()),
        }

    def playback(self, from_index: int = 0, to_index: int = None,
                 event_type: TimelineEventType = None) -> list[dict]:
        events = self.events[from_index:to_index]
        if event_type:
            events = [e for e in events if e.event_type == event_type]

        return [
            {
                "index": i + from_index,
                "id": e.id,
                "type": e.event_type.value,
                "data": e.data,
                "timestamp": e.timestamp,
                "duration_ms": e.duration_ms,
            }
            for i, e in enumerate(events)
        ]

    def export(self) -> dict:
        return {
            "session_id": self.session_id,
            "events": [
                {
                    "id": e.id,
                    "type": e.event_type.value,
                    "data": e.data,
                    "timestamp": e.timestamp,
                    "parent_id": e.parent_id,
                    "duration_ms": e.duration_ms,
                    "metadata": e.metadata,
                }
                for e in self.events
            ],
            "bookmarks": self._bookmarks,
            "stats": self.get_stats(),
        }

    def summary(self) -> str:
        stats = self.get_stats()
        user_inputs = [e for e in self.events if e.event_type == TimelineEventType.USER_INPUT]
        responses = [e for e in self.events if e.event_type == TimelineEventType.AGENT_RESPONSE]
        tool_calls = [e for e in self.events if e.event_type == TimelineEventType.TOOL_CALL]

        lines = [
            f"Session: {self.session_id}",
            f"Events: {stats['total_events']}",
            f"User inputs: {len(user_inputs)}",
            f"Agent responses: {len(responses)}",
            f"Tool calls: {len(tool_calls)}",
            f"Duration: {stats['wall_duration_s']:.1f}s",
        ]
        return "\n".join(lines)
