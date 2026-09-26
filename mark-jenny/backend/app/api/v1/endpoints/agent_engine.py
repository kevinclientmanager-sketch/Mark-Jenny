"""
Mark-Imti Agent Engine API — Multi-agent orchestration endpoints
"""

from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel
from typing import Optional
import uuid

from app.core.agent_engine import AgentEngine, ComplexityLevel
from app.core.sandbox import SandboxExecutor, BrowserAutomation
from app.core.proactive import ProactiveEngine, TriggerType
from app.core.model_router import ModelRouter, TaskDomain
from app.core.task_dag import TaskDAG

router = APIRouter(tags=["Agent Engine"])


class ProcessRequest(BaseModel):
    request: str
    context: dict = {}
    use_multi_agent: bool = True
    max_iterations: int = 5


class SandboxExecRequest(BaseModel):
    code: str
    language: str = "python"
    context: dict = {}


class RouteRequest(BaseModel):
    text: str
    preferences: dict = {}


class DecomposeRequest(BaseModel):
    request: str


class ProactiveEvalRequest(BaseModel):
    context: dict


_engine = None
_sandbox = None
_proactive = None
_router = None


def get_engine():
    global _engine
    if _engine is None:
        from app.core.model_caller import ModelCaller
        _engine = AgentEngine(ModelCaller())
    return _engine


def get_sandbox():
    global _sandbox
    if _sandbox is None:
        _sandbox = SandboxExecutor()
    return _sandbox


def get_proactive():
    global _proactive
    if _proactive is None:
        from app.core.model_caller import ModelCaller
        _proactive = ProactiveEngine(ModelCaller())
    return _proactive


def get_router():
    """Router with the real model catalogue registered.

    Previously the registry was never populated, so /route always answered
    `model: None` and /router/stats reported 0 registered models.
    """
    global _router
    if _router is None:
        _router = ModelRouter()
        try:
            from app.db.base import SessionLocal
            from app.models.agent import Model
            from app.services.model_router import ensure_default_models
            from app.core.model_router import ModelConfig
            db = SessionLocal()
            try:
                ensure_default_models(db)
                for m in db.query(Model).filter(Model.is_active.is_(True)).all():
                    provider = m.provider.value if hasattr(m.provider, "value") else str(m.provider)
                    cfg = ModelConfig(
                        name=m.name,
                        provider=provider,
                        model_id=m.model_id,
                        api_key="",
                        base_url="",
                        max_tokens=m.max_output_tokens or 4096,
                        cost_per_1k_input=float(m.cost_per_1k_input or 0),
                        cost_per_1k_output=float(m.cost_per_1k_output or 0),
                        strengths=list(m.capabilities or []),
                        weaknesses=[],
                        latency_ms=0,
                        reliability=1.0,
                    )
                    try:
                        _router.register_model(m.model_id, cfg)
                    except Exception:
                        continue
            finally:
                db.close()
        except Exception:
            # No DB available - the router still works, just with no catalogue.
            pass
    return _router


@router.post("/process")
async def process_request(req: ProcessRequest):
    """
    Process a request through the multi-agent engine.
    Uses Planner -> Executor -> Verifier pattern with iterative self-correction.
    """
    engine = get_engine()
    result = await engine.process(req.request, req.context)
    return {
        "status": "ok",
        "task_id": result["task_id"],
        "complexity": result["complexity"],
        "iterations": result["iterations"],
        "steps": result["steps"],
        "timeline": result["timeline"],
        "verification": result["verification"],
    }


@router.post("/sandbox/execute")
async def sandbox_execute(req: SandboxExecRequest):
    """Execute code in isolated sandbox environment."""
    sandbox = get_sandbox()

    if req.language == "python":
        result = await sandbox.execute_python(req.code, req.context)
    elif req.language == "shell":
        result = await sandbox.execute_shell(req.code)
    elif req.language == "node":
        result = await sandbox.execute_node(req.code)
    else:
        raise HTTPException(400, f"Unsupported language: {req.language}")

    return {
        "status": "ok",
        "execution_id": result.id,
        "exit_code": result.exit_code,
        "stdout": result.stdout,
        "stderr": result.stderr,
        "duration_ms": result.duration_ms,
        "execution_status": result.status.value,
    }


@router.post("/sandbox/browse")
async def sandbox_browse(url: str):
    """Browse a URL in sandbox and extract data."""
    sandbox = get_sandbox()
    browser = BrowserAutomation(sandbox)
    result = await browser.navigate(url)
    return {"status": "ok", "data": result}


@router.post("/route")
async def route_task(req: RouteRequest):
    """Route a task to the best model based on domain and complexity."""
    router = get_router()
    result = router.route(req.text, req.preferences)
    return {"status": "ok", "routing": result}


@router.post("/decompose")
async def decompose_task(req: DecomposeRequest):
    """Decompose a complex task into a DAG of subtasks."""
    from app.core.model_caller import ModelCaller
    dag = TaskDAG(ModelCaller())
    await dag.decompose(req.request)
    return {
        "status": "ok",
        "nodes": len(dag.nodes),
        "execution_order": dag.get_execution_order(),
        "graph": dag.visualize(),
    }


@router.post("/proactive/evaluate")
async def proactive_evaluate(req: ProactiveEvalRequest):
    """Evaluate context and return proactive suggestions."""
    proactive = get_proactive()
    responses = await proactive.evaluate(req.context)
    return {
        "status": "ok",
        "suggestions": [
            {
                "id": r.id,
                "trigger": r.trigger_type.value,
                "message": r.message,
                "actions": r.suggested_actions,
                "confidence": r.confidence,
            }
            for r in responses
        ],
    }


@router.get("/proactive/active")
async def proactive_active():
    """Get active proactive suggestions."""
    proactive = get_proactive()
    active = proactive.get_active()
    return {
        "status": "ok",
        "count": len(active),
        "suggestions": [
            {
                "id": r.id,
                "trigger": r.trigger_type.value,
                "message": r.message,
                "actions": r.suggested_actions,
            }
            for r in active
        ],
    }


@router.post("/proactive/dismiss/{response_id}")
async def proactive_dismiss(response_id: str):
    """Dismiss a proactive suggestion."""
    proactive = get_proactive()
    proactive.dismiss(response_id)
    return {"status": "ok"}


@router.get("/router/stats")
async def router_stats():
    """Get model routing statistics."""
    router = get_router()
    return {"status": "ok", "stats": router.get_stats()}


@router.get("/router/classify")
async def router_classify(text: str):
    """Classify text into a task domain."""
    router = get_router()
    domain = router.classify_domain(text)
    return {"status": "ok", "domain": domain.value}
