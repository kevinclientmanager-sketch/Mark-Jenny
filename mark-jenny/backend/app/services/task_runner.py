"""Task execution engine.

Previously `POST /tasks/{id}/execute` only flipped the status to PLANNING and
returned "queued" - nothing ever consumed the queue, so tasks sat forever.

This runner actually executes a task:
  1. plan it (AgentBrain.think + plan_heuristic)
  2. persist the plan as a TaskRun and Subtask rows
  3. execute every step through a real model call
  4. record tool calls, produced files, model usage and timing
  5. finish as COMPLETED / FAILED with a real, honest result
"""
import time
import traceback
from typing import Any, Dict, List, Optional

from sqlalchemy.orm import Session

from app.models.task import Task, TaskRun, TaskStatus, Subtask
from app.models.user import User

_OFFLINE_MARKERS = (
    "not connected to an ai model",
    "could not answer",
    "no ai model connected",
    "reply pipeline failed",
)


def _looks_ai_powered(text: str) -> bool:
    low = (text or "").lower()
    if not text or not text.strip():
        return False
    return not any(m in low for m in _OFFLINE_MARKERS)


async def run_task(
    db: Session,
    task: Task,
    user: User,
    *,
    prompt: Optional[str] = None,
    think: bool = False,
    model: Optional[str] = None,
) -> Dict[str, Any]:
    """Execute a task end to end and return a truthful result summary."""
    from app.services.agent_brain import AgentBrain, plan_heuristic, think as brain_think

    started = time.time()
    request = (prompt or task.original_request or task.description or task.title or "").strip()
    if not request:
        task.status = TaskStatus.FAILED
        task.result = {"summary": "Task has no request text to execute.", "steps": []}
        db.commit()
        return {"task_id": task.id, "status": "FAILED",
                "result": task.result, "steps": 0, "total_steps": 0,
                "tool_calls": [], "files_created": [], "errors": ["empty request"],
                "duration_seconds": round(time.time() - started, 2)}

    # --- 1. Plan -----------------------------------------------------------
    task.status = TaskStatus.PLANNING
    db.commit()

    brain = AgentBrain(db)
    intent: Dict[str, Any] = {"intent": "analyze", "confidence": 0.3, "complexity": "simple"}
    skills: Dict[str, Any] = {"matched": [], "gaps": [], "assigned": []}
    try:
        traced = await brain_think(db, user, request, task.project_id)
        intent = traced.get("intent") or intent
        skills = traced.get("skills") or skills
    except Exception:
        pass

    try:
        plan = plan_heuristic(request, intent, skills.get("assigned", []))
    except Exception:
        plan = {"strategy": "sequential",
                "subtasks": [{"title": request[:120], "tools": [], "skills": []}]}

    raw_steps = plan.get("subtasks") or []
    steps = [{"title": (s.get("title") or request[:120])[:300],
              "tools": s.get("tools", []), "skills": s.get("skills", [])}
             for s in raw_steps] or [{"title": request[:120], "tools": [], "skills": []}]

    plan_payload = {
        "goal": request,
        "strategy": plan.get("strategy", "sequential"),
        "intent": intent.get("intent"),
        "subtasks": [{**s, "description": s["title"], "status": "PENDING"} for s in steps],
        "missing_capabilities": skills.get("gaps", []),
    }
    task.plan = plan_payload
    task.total_steps = len(steps)
    task.current_step = 0

    run_number = (db.query(TaskRun).filter(TaskRun.task_id == task.id).count() or 0) + 1
    run = TaskRun(task_id=task.id, run_number=run_number, status=TaskStatus.RUNNING,
                  plan=plan_payload)
    db.add(run)

    for i, s in enumerate(steps):
        db.add(Subtask(task_id=task.id, title=s["title"], status=TaskStatus.PENDING,
                       order=i + 1, required_tools=s["tools"], required_skills=s["skills"]))
    task.status = TaskStatus.RUNNING
    db.commit()
    db.refresh(run)
    await _notify(db, task, "running")

    # --- 2. Execute every step --------------------------------------------
    tool_calls: List[Dict[str, Any]] = []
    model_usage: List[Dict[str, Any]] = []
    step_results: List[Dict[str, Any]] = []
    sub_rows = db.query(Subtask).filter(Subtask.task_id == task.id).order_by(Subtask.order).all()

    for idx, step in enumerate(steps):
        task.current_step = idx + 1
        if sub_rows:
            sub_rows[idx].status = TaskStatus.RUNNING
            db.commit()
        step_prompt = (
            f"Overall goal: {request}\n"
            f"This is step {idx + 1} of {len(steps)} ({plan_payload['strategy']} strategy).\n"
            f"Step: {step['title']}\n\n"
            "Carry out this step and report the concrete outcome."
        )
        try:
            text = (await brain.chat(
                user_message=step_prompt,
                user_id=user.id,
                project_id=task.project_id,
                think=think,
                model=model,
            ) or "").strip()
            powered = _looks_ai_powered(text)
            step_results.append({"step": idx + 1, "title": step["title"],
                                 "output": text, "ai_powered": powered})
            tool_calls.append({"step": idx + 1, "title": step["title"],
                               "ai_powered": powered, "output_preview": text[:400]})
            model_usage.append({"step": idx + 1, "model": model or "auto", "ai_powered": powered})
            if sub_rows:
                sub_rows[idx].status = TaskStatus.COMPLETED
        except Exception as exc:
            detail = f"{type(exc).__name__}: {exc}"
            step_results.append({"step": idx + 1, "title": step["title"],
                                 "output": "", "ai_powered": False, "error": detail})
            tool_calls.append({"step": idx + 1, "title": step["title"], "error": detail,
                               "traceback": traceback.format_exc()[:1200]})
            if sub_rows:
                sub_rows[idx].status = TaskStatus.FAILED
        db.commit()

    # --- 3. Collect what was actually produced ----------------------------
    files_created: List[Dict[str, Any]] = []
    try:
        from app.models.file import File
        rows = db.query(File).filter(File.task_id == task.id).all()
        files_created = [{"id": f.id, "name": f.original_name, "type": f.file_type} for f in rows]
    except Exception:
        pass

    errors = [c["error"] for c in tool_calls if c.get("error")]
    ai_steps = sum(1 for s in step_results if s.get("ai_powered"))
    status = TaskStatus.FAILED if errors else TaskStatus.COMPLETED
    duration = round(time.time() - started, 2)

    summary_lines = [f"Goal: {request}",
                     f"Strategy: {plan_payload['strategy']}",
                     f"Steps executed: {task.current_step}/{len(steps)} (AI-generated: {ai_steps})",
                     f"Duration: {duration}s", ""]
    for s in step_results:
        summary_lines.append(f"--- Step {s['step']}: {s['title']}")
        if s.get("error"):
            summary_lines.append(f"FAILED - {s['error']}")
        else:
            summary_lines.append(s.get("output") or "(no output)")
    if files_created:
        summary_lines.append("")
        summary_lines.append("Files created: " + ", ".join(f["name"] for f in files_created))
    if not ai_steps and not errors:
        summary_lines.append("")
        summary_lines.append(
            "NOTE: no AI provider answered any step, so the run completed mechanically "
            "without generated content. Connect a provider in Settings > AI Studio for real results.")

    task.result = {"summary": "\n".join(summary_lines), "steps": step_results,
                   "ai_steps": ai_steps, "files_created": files_created}
    task.status = status
    db.commit()

    run.status = status
    run.steps_completed = task.current_step or 0
    run.tool_calls = tool_calls
    run.files_created = files_created
    run.model_usage = model_usage
    run.errors = errors
    try:
        from datetime import datetime, timezone
        run.finished_at = datetime.now(timezone.utc)
    except Exception:
        pass
    db.commit()

    await _notify(db, task, "completed" if status == TaskStatus.COMPLETED else "failed")

    return {
        "task_id": task.id,
        "status": status.value,
        "result": task.result,
        "steps": task.current_step or 0,
        "total_steps": len(steps),
        "tool_calls": tool_calls,
        "files_created": files_created,
        "errors": errors,
        "ai_steps": ai_steps,
        "duration_seconds": duration,
    }


async def _notify(db: Session, task: Task, event: str) -> None:
    try:
        from app.services.notification import notify_task_update
        await notify_task_update(db, task, event)
    except Exception:
        pass
