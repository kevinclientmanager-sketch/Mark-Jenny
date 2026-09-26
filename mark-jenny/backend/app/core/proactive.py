"""
Mark-Imti Proactive Engine — Anticipates user needs
Based on Google Astra's proactive response pattern
Monitors triggers and initiates helpful actions
"""

import asyncio
import json
import time
from enum import Enum
from typing import Any, Optional, Callable, Awaitable
from dataclasses import dataclass, field
from datetime import datetime, timedelta


class TriggerType(Enum):
    FILE_CHANGED = "file_changed"
    CALENDAR_EVENT = "calendar_event"
    DEADLINE_APPROACHING = "deadline_approaching"
    PATTERN_DETECTED = "pattern_detected"
    IDLE_SUGGESTION = "idle_suggestion"
    CONTEXT_CHANGE = "context_change"
    TASK_COMPLETED = "task_completed"
    ERROR_OCCURRED = "error_occurred"


@dataclass
class ProactiveTrigger:
    id: str
    trigger_type: TriggerType
    condition: dict
    action: str
    priority: int = 5
    cooldown_seconds: int = 300
    last_fired: Optional[float] = None
    enabled: bool = True


@dataclass
class ProactiveResponse:
    id: str
    trigger_id: str
    trigger_type: TriggerType
    message: str
    suggested_actions: list[str]
    context: dict
    confidence: float
    created_at: str = field(default_factory=lambda: datetime.utcnow().isoformat())
    dismissed: bool = False
    ai_generated: bool = True


class ProactiveEngine:
    """
    Monitors context and fires proactive suggestions.
    Learns user patterns over time to improve suggestions.
    """

    def __init__(self, model_caller=None):
        self.model = model_caller
        self.triggers: dict[str, ProactiveTrigger] = {}
        self.responses: list[ProactiveResponse] = []
        self.patterns: dict[str, Any] = {}
        self._monitors: list[Callable] = []
        self._setup_default_triggers()

    def _setup_default_triggers(self):
        self.register_trigger(ProactiveTrigger(
            id="idle-suggest",
            trigger_type=TriggerType.IDLE_SUGGESTION,
            condition={"idle_minutes": 5},
            action="suggest_continuation",
            priority=3,
            cooldown_seconds=600,
        ))
        self.register_trigger(ProactiveTrigger(
            id="task-complete",
            trigger_type=TriggerType.TASK_COMPLETED,
            condition={"auto": True},
            action="suggest_next_step",
            priority=7,
            cooldown_seconds=60,
        ))
        self.register_trigger(ProactiveTrigger(
            id="error-occur",
            trigger_type=TriggerType.ERROR_OCCURRED,
            condition={"auto": True},
            action="suggest_fix",
            priority=9,
            cooldown_seconds=30,
        ))

    def register_trigger(self, trigger: ProactiveTrigger):
        self.triggers[trigger.id] = trigger

    def remove_trigger(self, trigger_id: str):
        self.triggers.pop(trigger_id, None)

    async def evaluate(self, context: dict) -> list[ProactiveResponse]:
        responses = []
        now = time.time()

        for trigger in self.triggers.values():
            if not trigger.enabled:
                continue

            if trigger.last_fired:
                elapsed = now - trigger.last_fired
                if elapsed < trigger.cooldown_seconds:
                    continue

            if await self._check_condition(trigger.condition, context):
                response = await self._generate_response(trigger, context)
                if response:
                    responses.append(response)
                    trigger.last_fired = now
                    self.responses.append(response)

        return responses

    async def _check_condition(self, condition: dict, context: dict) -> bool:
        if condition.get("auto"):
            return True

        if "idle_minutes" in condition:
            last_activity = context.get("last_activity_time", 0)
            idle = time.time() - last_activity
            return idle >= condition["idle_minutes"] * 60

        if "file_pattern" in condition:
            changed_files = context.get("changed_files", [])
            pattern = condition["file_pattern"]
            return any(pattern in f for f in changed_files)

        if "error_type" in condition:
            return context.get("last_error_type") == condition["error_type"]

        return False

    async def _generate_response(self, trigger: ProactiveTrigger,
                                  context: dict) -> Optional[ProactiveResponse]:
        if self.model:
            prompt = f"""Based on this context, suggest a helpful action:
Context: {json.dumps(context, default=str)[:2000]}
Trigger: {trigger.trigger_type.value}

Return JSON:
{{
    "message": "helpful suggestion",
    "suggested_actions": ["action1", "action2"],
    "confidence": 0.8
}}"""
            try:
                response_text = await self.model.complete(prompt, max_tokens=500)
                data = json.loads(response_text)
                return ProactiveResponse(
                    id=f"resp-{trigger.id}-{int(time.time())}",
                    trigger_id=trigger.id,
                    trigger_type=trigger.trigger_type,
                    message=data.get("message", "Here's something that might help."),
                    suggested_actions=data.get("suggested_actions", []),
                    context=context,
                    confidence=data.get("confidence", 0.5),
                )
            except Exception:
                pass

        # No model answered. Emit an explicit, non-fabricated notice instead of
        # a canned "Need help with anything?" dressed up as an AI suggestion.
        return ProactiveResponse(
            id=f"resp-{trigger.id}-{int(time.time())}",
            trigger_id=trigger.id,
            trigger_type=trigger.trigger_type,
            message=(
                "A proactive suggestion was requested but no AI model is connected, so there is "
                "nothing real to suggest. Connect a provider in Settings > AI Studio to enable this."
            ),
            suggested_actions=[],
            context=context,
            confidence=0.0,
            ai_generated=False,
        )

    def _get_default_message(self, trigger_type: TriggerType) -> str:
        """Deprecated: returns an explicit unavailable notice, never a fake AI line."""
        return (
            "No AI model is connected, so this suggestion could not be generated. "
            "Connect a provider in Settings > AI Studio."
        )

    def _get_default_actions(self, trigger_type: TriggerType) -> list[str]:
        actions = {
            TriggerType.IDLE_SUGGESTION: ["Continue previous task", "Start new task"],
            TriggerType.TASK_COMPLETED: ["Review results", "Start related task"],
            TriggerType.ERROR_OCCURRED: ["View error details", "Try automatic fix"],
            TriggerType.FILE_CHANGED: ["Show diff", "Review changes"],
        }
        return actions.get(trigger_type, ["Take action"])

    def learn_pattern(self, pattern_type: str, data: dict):
        if pattern_type not in self.patterns:
            self.patterns[pattern_type] = []
        self.patterns[pattern_type].append({
            "data": data,
            "timestamp": datetime.utcnow().isoformat(),
        })
        if len(self.patterns[pattern_type]) > 100:
            self.patterns[pattern_type] = self.patterns[pattern_type][-100:]

    def get_dismissed(self) -> list[ProactiveResponse]:
        return [r for r in self.responses if r.dismissed]

    def dismiss(self, response_id: str):
        for r in self.responses:
            if r.id == response_id:
                r.dismissed = True
                break

    def get_active(self) -> list[ProactiveResponse]:
        return [r for r in self.responses if not r.dismissed]
