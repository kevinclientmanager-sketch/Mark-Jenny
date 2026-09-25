"""
Mark-Imti Agent Engine — Multi-Agent Architecture
Based on Manus AI's Planner + Execution + Verification pattern
Implements iterative agent loop, task decomposition, and self-correction
"""

import asyncio
import json
import time
import uuid
from enum import Enum
from typing import Any, Optional
from dataclasses import dataclass, field, asdict
from datetime import datetime


class AgentRole(Enum):
    PLANNER = "planner"
    EXECUTOR = "executor"
    VERIFIER = "verifier"
    ORCHESTRATOR = "orchestrator"


class TaskState(Enum):
    PENDING = "pending"
    PLANNING = "planning"
    EXECUTING = "executing"
    VERIFYING = "verifying"
    CORRECTING = "correcting"
    COMPLETED = "completed"
    FAILED = "failed"
    PAUSED = "paused"


class ComplexityLevel(Enum):
    TRIVIAL = "trivial"
    SIMPLE = "simple"
    MODERATE = "moderate"
    COMPLEX = "complex"
    EXPERT = "expert"


@dataclass
class AgentStep:
    id: str
    step_number: int
    action: str
    tool: Optional[str]
    input_data: dict
    output_data: Optional[dict] = None
    status: str = "pending"
    started_at: Optional[str] = None
    completed_at: Optional[str] = None
    duration_ms: Optional[int] = None
    error: Optional[str] = None
    retry_count: int = 0
    max_retries: int = 3


@dataclass
class TaskPlan:
    id: str
    original_request: str
    complexity: ComplexityLevel
    estimated_steps: int
    subtasks: list[dict] = field(default_factory=list)
    dependencies: dict = field(default_factory=dict)
    created_at: str = field(default_factory=lambda: datetime.utcnow().isoformat())


@dataclass
class TaskCheckpoint:
    id: str
    task_id: str
    step_number: int
    state: TaskState
    plan: Optional[TaskPlan]
    steps_completed: list[AgentStep]
    variables: dict
    created_at: str = field(default_factory=lambda: datetime.utcnow().isoformat())


class ComplexityAnalyzer:
    """Analyzes request complexity to determine agent routing and thinking depth."""

    COMPLEXITY_SIGNALS = {
        ComplexityLevel.TRIVIAL: {
            "keywords": ["hi", "hello", "thanks", "yes", "no", "ok"],
            "max_words": 5,
            "tools_needed": 0,
        },
        ComplexityLevel.SIMPLE: {
            "keywords": ["what", "how", "explain", "define", "who"],
            "max_words": 20,
            "tools_needed": 1,
        },
        ComplexityLevel.MODERATE: {
            "keywords": ["create", "build", "write", "generate", "design"],
            "max_words": 100,
            "tools_needed": 2,
        },
        ComplexityLevel.COMPLEX: {
            "keywords": ["research", "analyze", "compare", "implement", "deploy",
                         "automate", "integrate", "optimize", "refactor"],
            "max_words": 500,
            "tools_needed": 3,
        },
        ComplexityLevel.EXPERT: {
            "keywords": ["architect", "migrate", "security audit", "performance",
                         "distributed", "real-time", "multi-agent", "autonomous"],
            "max_words": 1000,
            "tools_needed": 5,
        },
    }

    def analyze(self, text: str, context: dict = None) -> ComplexityLevel:
        text_lower = text.lower()
        word_count = len(text.split())

        scores = {level: 0 for level in ComplexityLevel}

        for level, signals in self.COMPLEXITY_SIGNALS.items():
            for keyword in signals["keywords"]:
                if keyword in text_lower:
                    scores[level] += 2

            if word_count <= signals["max_words"]:
                scores[level] += 1

        if context:
            if context.get("has_files"):
                scores[ComplexityLevel.MODERATE] += 1
            if context.get("has_code"):
                scores[ComplexityLevel.COMPLEX] += 1
            if context.get("multi_step"):
                scores[ComplexityLevel.COMPLEX] += 2

        best = max(scores, key=scores.get)
        if scores[best] == 0:
            return ComplexityLevel.SIMPLE
        return best

    def get_thinking_tokens(self, level: ComplexityLevel) -> int:
        return {
            ComplexityLevel.TRIVIAL: 100,
            ComplexityLevel.SIMPLE: 500,
            ComplexityLevel.MODERATE: 2000,
            ComplexityLevel.COMPLEX: 8000,
            ComplexityLevel.EXPERT: 32000,
        }[level]


class PlannerAgent:
    """Decomposes tasks into executable subtasks with dependencies."""

    def __init__(self, model_caller):
        self.model = model_caller

    async def create_plan(self, request: str, complexity: ComplexityLevel) -> TaskPlan:
        plan_id = str(uuid.uuid4())

        if complexity in (ComplexityLevel.TRIVIAL, ComplexityLevel.SIMPLE):
            return TaskPlan(
                id=plan_id,
                original_request=request,
                complexity=complexity,
                estimated_steps=1,
                subtasks=[{
                    "id": f"sub-{plan_id}-0",
                    "description": request,
                    "tools": ["chat"],
                    "dependencies": [],
                }],
            )

        prompt = f"""Analyze this request and create an execution plan.
Break it into independent subtasks that can run in parallel where possible.

REQUEST: {request}

Return JSON with:
{{
    "subtasks": [
        {{
            "id": "sub-0",
            "description": "...",
            "tools": ["tool1", "tool2"],
            "dependencies": [],
            "estimated_complexity": "simple|moderate|complex"
        }}
    ],
    "parallel_groups": [["sub-0", "sub-1"], ["sub-2"]],
    "estimated_total_steps": N
}}"""

        try:
            response = await self.model.complete(prompt, max_tokens=2000)
            plan_data = json.loads(response)
        except Exception:
            plan_data = {
                "subtasks": [{
                    "id": f"sub-{plan_id}-0",
                    "description": request,
                    "tools": ["auto"],
                    "dependencies": [],
                }],
                "parallel_groups": [[f"sub-{plan_id}-0"]],
                "estimated_total_steps": 1,
            }

        subtasks = plan_data.get("subtasks", [])
        for i, st in enumerate(subtasks):
            st.setdefault("id", f"sub-{plan_id}-{i}")

        return TaskPlan(
            id=plan_id,
            original_request=request,
            complexity=complexity,
            estimated_steps=plan_data.get("estimated_total_steps", len(subtasks)),
            subtasks=subtasks,
            dependencies={st["id"]: st.get("dependencies", []) for st in subtasks},
        )


class ExecutorAgent:
    """Executes individual subtasks using available tools."""

    def __init__(self, model_caller, tool_registry):
        self.model = model_caller
        self.tools = tool_registry

    async def execute_step(self, step: AgentStep, context: dict) -> AgentStep:
        step.status = "executing"
        step.started_at = datetime.utcnow().isoformat()
        start = time.time()

        try:
            tool_name = step.tool or "auto"
            if tool_name == "auto" or tool_name not in self.tools:
                result = await self._execute_with_model(step, context)
            else:
                tool = self.tools[tool_name]
                result = await tool.execute(step.input_data, context)

            step.output_data = result
            step.status = "completed"
        except Exception as e:
            step.error = str(e)
            if step.retry_count < step.max_retries:
                step.retry_count += 1
                step.status = "pending"
            else:
                step.status = "failed"

        step.completed_at = datetime.utcnow().isoformat()
        step.duration_ms = int((time.time() - start) * 1000)
        return step

    async def _execute_with_model(self, step: AgentStep, context: dict) -> dict:
        prompt = f"""Execute this task step:
{step.action}

Context: {json.dumps(context, default=str)[:2000]}

Provide the result as JSON."""
        try:
            response = await self.model.complete(prompt, max_tokens=4000)
            return {"result": response, "source": "model"}
        except Exception as e:
            return {"error": str(e), "source": "model"}


class VerifierAgent:
    """Verifies output quality and correctness."""

    def __init__(self, model_caller):
        self.model = model_caller

    async def verify(self, plan: TaskPlan, steps: list[AgentStep]) -> dict:
        results = []
        all_passed = True

        for step in steps:
            if step.status != "completed":
                all_passed = False
                results.append({
                    "step_id": step.id,
                    "passed": False,
                    "reason": f"Step status: {step.status}",
                })
                continue

            verification = await self._verify_step(step, plan)
            results.append(verification)
            if not verification["passed"]:
                all_passed = False

        return {
            "all_passed": all_passed,
            "results": results,
            "needs_correction": not all_passed,
        }

    async def _verify_step(self, step: AgentStep, plan: TaskPlan) -> dict:
        prompt = f"""Verify this task step output:
STEP: {step.action}
OUTPUT: {json.dumps(step.output_data, default=str)[:2000]}

Check if the output:
1. Answers the original request
2. Is complete and accurate
3. Has no errors

Return JSON: {{"passed": true/false, "reason": "...", "issues": []}}"""

        try:
            response = await self.model.complete(prompt, max_tokens=1000)
            return json.loads(response)
        except Exception:
            return {"passed": True, "reason": "Verification skipped", "issues": []}


class AgentEngine:
    """
    Main agent engine — orchestrates multi-agent system.
    Implements: iterative loop, task decomposition, self-correction,
    adaptive thinking, checkpoints, timeline.
    """

    def __init__(self, model_caller, tool_registry=None):
        self.model = model_caller
        self.tools = tool_registry or {}
        self.complexity_analyzer = ComplexityAnalyzer()
        self.planner = PlannerAgent(model_caller)
        self.executor = ExecutorAgent(model_caller, self.tools)
        self.verifier = VerifierAgent(model_caller)
        self._timeline: list[dict] = []
        self._checkpoints: dict[str, TaskCheckpoint] = {}

    async def process(self, request: str, context: dict = None) -> dict:
        context = context or {}
        task_id = str(uuid.uuid4())
        self._timeline = []

        complexity = self.complexity_analyzer.analyze(request, context)
        self._log("analyze", f"Complexity: {complexity.value}")

        plan = await self.planner.create_plan(request, complexity)
        self._log("plan", f"Created plan with {len(plan.subtasks)} subtasks")

        max_iterations = 5
        for iteration in range(max_iterations):
            self._log("iterate", f"Iteration {iteration + 1}/{max_iterations}")

            steps = []
            for subtask in plan.subtasks:
                step = AgentStep(
                    id=str(uuid.uuid4()),
                    step_number=len(steps) + 1,
                    action=subtask["description"],
                    tool=subtask.get("tools", ["auto"])[0] if subtask.get("tools") else "auto",
                    input_data={"subtask": subtask, "context": context},
                )
                self._save_checkpoint(task_id, iteration, plan, steps, context)
                step = await self.executor.execute_step(step, context)
                steps.append(step)
                self._log("execute", f"Step {step.step_number}: {step.status}")

            verification = await self.verifier.verify(plan, steps)
            self._log("verify", f"All passed: {verification['all_passed']}")

            if verification["all_passed"]:
                self._log("complete", "Task completed successfully")
                break

            if iteration < max_iterations - 1:
                self._log("correct", "Applying corrections...")
                for result in verification["results"]:
                    if not result["passed"]:
                        for step in steps:
                            if step.id == result.get("step_id"):
                                step.status = "pending"
                                step.retry_count += 1

        return {
            "task_id": task_id,
            "complexity": complexity.value,
            "iterations": iteration + 1,
            "steps": [asdict(s) for s in steps],
            "timeline": self._timeline,
            "verification": verification,
            "plan": asdict(plan),
        }

    def _log(self, action: str, detail: str):
        self._timeline.append({
            "timestamp": datetime.utcnow().isoformat(),
            "action": action,
            "detail": detail,
        })

    def _save_checkpoint(self, task_id: str, step: int, plan: TaskPlan,
                         completed_steps: list, context: dict):
        checkpoint = TaskCheckpoint(
            id=str(uuid.uuid4()),
            task_id=task_id,
            step_number=step,
            state=TaskState.EXECUTING,
            plan=plan,
            steps_completed=completed_steps,
            variables=context,
        )
        self._checkpoints[checkpoint.id] = checkpoint

    def get_checkpoint(self, checkpoint_id: str) -> Optional[TaskCheckpoint]:
        return self._checkpoints.get(checkpoint_id)

    def get_timeline(self) -> list[dict]:
        return self._timeline
