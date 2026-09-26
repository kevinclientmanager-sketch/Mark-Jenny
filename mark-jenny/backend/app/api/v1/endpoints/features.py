import importlib.util
import re
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any

from app.db.base import get_db
from app.core.security import get_current_user
from app.models.user import User
from app.services.mcp_client import mcp_client
from app.services.credential_vault import credential_vault
from app.services.qa_engine import qa_engine
from app.services.github_service import github_service
from app.services.vision_engine import vision_engine
from app.utils.audit import log_audit

router = APIRouter()


# This is the authoritative capability map for the existing platform. Each entry
# points at the subsystem that owns the behavior so future upgrades extend rather
# than duplicate the current runtime.
CAPABILITY_AUDIT = [
    (1, "Autonomous workflow execution", "PARTIALLY IMPLEMENTED", "tasks, agent_controller, execution"),
    (2, "Always-on / persistent operation", "PARTIALLY IMPLEMENTED", "schedules, websocket"),
    (3, "Multi-agent orchestration", "IMPLEMENTED", "advanced_autonomy, agent_controller"),
    (4, "Tool and service integration", "IMPLEMENTED", "mcp, integrations, connectors"),
    (5, "Intelligent model and tool routing", "IMPLEMENTED", "model_router, agent_controller"),
    (6, "Failure recovery and task resumption", "IMPLEMENTED", "advanced_autonomy, task_runs"),
    (7, "Autonomous coding and debugging", "PARTIALLY IMPLEMENTED", "code_execution, qa_engine"),
    (8, "Terminal and system access", "PARTIALLY IMPLEMENTED", "computer, execution"),
    (9, "Model flexibility / BYOM", "IMPLEMENTED", "model_router, models"),
    (10, "Cross-platform synchronization", "PARTIALLY IMPLEMENTED", "projects, files, websocket"),
    (11, "Persistent working memory and task state", "IMPLEMENTED", "tasks, memories, checkpoints"),
    (12, "Skill learning and workflow recording", "PARTIALLY IMPLEMENTED", "skills, advanced_autonomy"),
    (13, "Self-correction and strategy refinement", "IMPLEMENTED", "self_check, error_recovery"),
    (14, "Goal-oriented planning and decomposition", "IMPLEMENTED", "agent_controller, agent_brain"),
    (15, "Performance benchmarking and optimization", "PARTIALLY IMPLEMENTED", "qa_engine, audit"),
    (16, "Continuous evaluation and regression testing", "PARTIALLY IMPLEMENTED", "qa_engine"),
    (17, "Graduated autonomy", "IMPLEMENTED", "approval_manager, task.autonomy_level"),
    (18, "Long-term episodic memory", "IMPLEMENTED", "knowledge.Memory"),
    (19, "Proactive context awareness", "PARTIALLY IMPLEMENTED", "memory, schedules"),
    (20, "Knowledge retrieval and grounded research", "IMPLEMENTED", "knowledge, agent_brain"),
    (21, "Multimodal environment interaction", "PARTIALLY IMPLEMENTED", "vision, computer, voice"),
    (22, "Human-in-the-loop intent calibration", "PARTIALLY IMPLEMENTED", "approvals, chat"),
    (23, "Cross-agent reasoning and verification", "IMPLEMENTED", "supervisor, self_check"),
    (24, "Self-healing infrastructure", "PARTIALLY IMPLEMENTED", "error_recovery, health"),
    (25, "Predictive maintenance", "PARTIALLY IMPLEMENTED", "readiness, audit"),
    (26, "Real-time observability and tracing", "IMPLEMENTED", "audit, websocket, task_runs"),
    (27, "Intelligent failure diagnosis", "IMPLEMENTED", "error_recovery"),
    (28, "Security sandboxing", "PARTIALLY IMPLEMENTED", "code_execution, execution"),
    (29, "Automated security auditing", "IMPLEMENTED", "cybersecurity_agent, qa_engine"),
    (30, "Identity and permission management", "IMPLEMENTED", "auth, users, approvals"),
    (31, "Dynamic guardrails", "IMPLEMENTED", "policy_preflight, approvals"),
    (32, "Pre-execution risk assessment", "IMPLEMENTED", "policy_preflight"),
    (33, "Human approval gates", "IMPLEMENTED", "approval model and endpoints"),
    (34, "Dynamic resource scaling and cost control", "PARTIALLY IMPLEMENTED", "model_router, cost estimation"),
    (35, "Collaborative resource negotiation", "PARTIALLY IMPLEMENTED", "agent_controller"),
    (36, "Budget-aware planning", "IMPLEMENTED", "model_router, estimate_cost"),
    (37, "Flexible deployment and ownership", "PARTIALLY IMPLEMENTED", "github, vercel deployment"),
    (38, "Local and cloud hybrid execution", "IMPLEMENTED", "model_router, execution"),
    (39, "Persistent cloud workspaces", "PARTIALLY IMPLEMENTED", "projects, project_workspace"),
    (40, "Environment portability", "PARTIALLY IMPLEMENTED", "projects, files, skills"),
    (41, "Proactive task discovery", "PARTIALLY IMPLEMENTED", "schedules, notifications"),
    (42, "Event-driven autonomous execution", "PARTIALLY IMPLEMENTED", "schedules, websocket"),
    (43, "Dependency and environment awareness", "PARTIALLY IMPLEMENTED", "projects, tasks, skills"),
    (44, "Adaptive strategy selection", "IMPLEMENTED", "model_router, error_recovery"),
    (45, "Autonomous research and synthesis", "IMPLEMENTED", "agent_brain, research tools"),
    (46, "Source verification and evidence tracking", "PARTIALLY IMPLEMENTED", "knowledge, audit"),
    (47, "Long-running project management", "IMPLEMENTED", "projects, tasks, schedules"),
    (48, "Autonomous delegation and escalation", "IMPLEMENTED", "delegation, approvals, supervisor"),
]


def _derive_status(owner: str) -> str:
    """Compute a capability's status from whether its modules actually import.

    The audit table used to ship hand-written IMPLEMENTED / PARTIALLY
    IMPLEMENTED verdicts that were never checked against the code.
    """
    import importlib
    tokens = [t.strip() for t in re.split(r"[,\s]+", owner or "") if t.strip()]
    modules = []
    for t in tokens:
        if t in {"and", "the", "model", "and"}:
            continue
        for cand in (f"app.services.{t}", f"app.core.{t}", f"app.api.v1.endpoints.{t}", f"app.models.{t}"):
            modules.append(cand)
    found = 0
    for m in modules:
        try:
            if importlib.util.find_spec(m) is not None:
                found += 1
        except Exception:
            continue
    if not modules:
        return "UNKNOWN"
    if found == 0:
        return "NOT IMPLEMENTED"
    if found < len(modules):
        return "PARTIALLY IMPLEMENTED"
    return "IMPLEMENTED"


@router.get("/audit")
async def capability_audit(current_user: User = Depends(get_current_user)):
    """Capability map with status derived from the real codebase."""
    counts = {}
    capabilities = []
    for number, name, _declared, owner in CAPABILITY_AUDIT:
        status = _derive_status(owner)
        counts[status] = counts.get(status, 0) + 1
        capabilities.append({
            "number": number, "name": name, "status": status, "owner": owner,
            "declared_status": _declared,
            "status_source": "derived_from_modules",
        })
    return {
        "total": len(capabilities),
        "counts": counts,
        "capabilities": capabilities,
        "note": "status is computed by checking that each capability's modules import; "
                "declared_status shows the previous hand-written value for comparison",
    }



@router.get("/readiness")
async def capability_readiness(current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    """Runtime readiness computed from the actual system state.

    Previously this returned hardcoded `true` for multi_agent, self_build and
    governance, which reported capability that was never verified.
    """
    import importlib.util
    from app.core.config import get_settings
    from app.models.agent import ModelProviderConfig
    settings = get_settings()
    airllm_installed = importlib.util.find_spec("airllm") is not None
    crewai_installed = importlib.util.find_spec("crewai") is not None
    cloud_configured = bool(settings.CLOUD_MODEL_BASE_URL and settings.CLOUD_MODEL_API_KEY)

    # A model is only "ready" if this user actually has a usable provider key.
    user_keys = 0
    try:
        user_keys = db.query(ModelProviderConfig).filter(
            ModelProviderConfig.user_id == current_user.id,
            ModelProviderConfig.api_key_encrypted.isnot(None),
        ).count()
    except Exception:
        user_keys = 0

    def _has_module(path: str) -> bool:
        try:
            return importlib.util.find_spec(path) is not None
        except Exception:
            return False

    from app.core.rate_limit import limiter as _limiter
    try:
        from app.models.approval import Approval
        approvals_ok = db.query(Approval).limit(1).all() is not None
    except Exception:
        approvals_ok = False
    try:
        from app.models.audit import AuditLog
        audit_ok = db.query(AuditLog).limit(1).all() is not None
    except Exception:
        audit_ok = False

    sandbox_ok = _has_module("app.services.code_execution_engine")
    self_build_ok = _has_module("app.services.self_build_orchestrator")

    return {
        "runtime_mode": settings.MODEL_RUNTIME_MODE,
        "cloud_model": {"configured": cloud_configured, "model": settings.CLOUD_MODEL_NAME},
        "local_model": {"configured": bool(settings.OLLAMA_BASE_URL), "model": settings.OLLAMA_MODEL},
        "user_provider_keys": user_keys,
        "model_callable": bool(cloud_configured or user_keys),
        "multi_agent": {"available": _has_module("app.services.agent_brain"), "orchestrator": "agent_brain"},
        "airllm": {"installed": airllm_installed, "enabled": settings.MODEL_RUNTIME_MODE in {"local", "hybrid"}},
        "crewai": {"installed": crewai_installed, "available": crewai_installed},
        "self_build": {
            "available": self_build_ok,
            "self_evaluation": _has_module("app.services.qa_engine"),
            "rollback": self_build_ok,
        },
        "governance": {
            "approvals": approvals_ok,
            "audit_log": audit_ok,
            "rate_limits": hasattr(_limiter, "max_requests"),
            "sandbox": sandbox_ok,
        },
        "recommendations": [
            *([] if (cloud_configured or user_keys) else [
                "No AI provider is reachable. Add an API key in Settings > AI Studio - "
                "without one every agent step returns an explicit offline notice."
            ]),
            *([] if crewai_installed else ["CrewAI is not installed; native orchestration is used instead."]),
            *([] if sandbox_ok else ["Code execution sandbox module could not be imported."]),
        ],
    }


# === Premium agent operations ===

class EvaluationRequest(BaseModel):
    task: str
    response: str
    criteria: List[str] = Field(default_factory=lambda: ["relevance", "completeness", "safety", "actionability"])


class PolicyPreflightRequest(BaseModel):
    action: str
    target: Optional[str] = None
    requires_approval: bool = False
    estimated_cost_usd: float = 0.0


@router.post("/evaluate")
async def evaluate_agent_output(data: EvaluationRequest, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    """Deterministic preflight evaluation for agent responses before delivery."""
    text = data.response.strip()
    task_terms = {term.lower() for term in data.task.split() if len(term) > 3}
    response_terms = {term.lower() for term in text.split() if len(term) > 3}
    relevance = min(1.0, len(task_terms & response_terms) / max(1, min(len(task_terms), 8)))
    completeness = min(1.0, len(text) / max(240, len(data.task) * 3))
    safety = 0.0 if any(marker in text.lower() for marker in ["ignore all safety", "exfiltrate", "steal credentials"]) else 1.0
    actionability = 1.0 if any(marker in text.lower() for marker in ["next", "step", "created", "implemented", "run", "use"]) else 0.5
    scores = {"relevance": round(relevance, 2), "completeness": round(completeness, 2), "safety": safety, "actionability": actionability}
    selected = [name for name in data.criteria if name in scores]
    overall = round(sum(scores[name] for name in selected) / max(1, len(selected)), 2)
    passed = overall >= 0.7 and safety == 1.0
    await log_audit(db, user_id=current_user.id, action="AGENT_EVALUATE", resource_type="agent_run", resource_id="preflight", success=passed)
    return {"passed": passed, "overall_score": overall, "scores": scores, "criteria": selected, "recommendations": ([] if passed else ["Improve task alignment, completeness, or actionable next steps before delivery."])}


@router.post("/policy/preflight")
async def policy_preflight(data: PolicyPreflightRequest, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    """Return a consistent approval decision before an agent invokes a side-effecting tool."""
    sensitive = any(word in data.action.lower() for word in ["delete", "publish", "deploy", "send", "purchase", "credential", "push"])
    approval_required = data.requires_approval or sensitive or data.estimated_cost_usd > 5
    result = {
        "allowed": not approval_required,
        "approval_required": approval_required,
        "risk_level": "high" if sensitive or data.estimated_cost_usd > 5 else "low",
        "reason": "Human approval required for a sensitive or costly action." if approval_required else "Action is eligible for autonomous execution.",
    }
    await log_audit(db, user_id=current_user.id, action="POLICY_PREFLIGHT", resource_type="tool", resource_id=data.action[:120], success=True)
    return result


@router.get("/catalog")
async def premium_capability_catalog(current_user: User = Depends(get_current_user)):
    return {"capabilities": [
        {"id": "durable_runs", "name": "Durable agent runs", "status": "available", "details": "Task runs, subtasks, resumable progress, and websocket updates."},
        {"id": "trace_evaluation", "name": "Trace and evaluation preflight", "status": "available", "details": "Score relevance, completeness, safety, and actionability before delivery."},
        {"id": "policy_guardrails", "name": "Policy guardrails", "status": "available", "details": "Approval preflight for sensitive, costly, and irreversible actions."},
        {"id": "memory_knowledge", "name": "Persistent memory and knowledge", "status": "available", "details": "User-scoped memories, knowledge ingestion, and retrieval."},
        {"id": "computer_mcp", "name": "Computer use and MCP", "status": "available", "details": "Browser/computer automation and external tool servers with audit logging."},
    ]}


# === MCP ===

class MCPServerAdd(BaseModel):
    name: str
    command: str
    args: Optional[List[str]] = []
    env: Optional[Dict[str, str]] = {}
    type: str = "stdio"
    url: Optional[str] = ""
    enabled: bool = True
    auto_start: bool = False

class MCPToolCall(BaseModel):
    server_id: str
    tool_name: str
    arguments: Optional[Dict[str, Any]] = {}


@router.get("/mcp/servers")
async def mcp_list_servers(current_user: User = Depends(get_current_user)):
    return {"servers": mcp_client.list_servers(), "stats": mcp_client.get_stats()}

@router.post("/mcp/servers")
async def mcp_add_server(data: MCPServerAdd, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    result = mcp_client.add_server(data.name, data.model_dump())
    await log_audit(db, user_id=current_user.id, action="MCP_ADD", resource_type="server", resource_id=data.name, success=result["success"])
    return result

@router.delete("/mcp/servers/{server_id}")
async def mcp_remove_server(server_id: str, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    result = mcp_client.remove_server(server_id)
    await log_audit(db, user_id=current_user.id, action="MCP_REMOVE", resource_type="server", resource_id=server_id, success=result["success"])
    return result

@router.post("/mcp/servers/{server_id}/start")
async def mcp_start_server(server_id: str, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    result = await mcp_client.start_server(server_id)
    await log_audit(db, user_id=current_user.id, action="MCP_START", resource_type="server", resource_id=server_id, success=result["success"])
    return result

@router.post("/mcp/servers/{server_id}/stop")
async def mcp_stop_server(server_id: str, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    result = await mcp_client.stop_server(server_id)
    return result

@router.post("/mcp/call")
async def mcp_call_tool(data: MCPToolCall, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    result = await mcp_client.call_tool(data.server_id, data.tool_name, data.arguments)
    await log_audit(db, user_id=current_user.id, action="MCP_CALL", resource_type="tool", resource_id=f"{data.server_id}/{data.tool_name}", success=result["success"])
    return result


# --- Curated registry: connect known MCP servers in one click -----------

class RegistryConnect(BaseModel):
    env: Optional[Dict[str, str]] = {}
    auto_start: bool = True


@router.get("/mcp/registry")
async def mcp_registry(current_user: User = Depends(get_current_user)):
    """Known-good MCP servers with their launch config and required secrets."""
    from app.services.mcp_registry import MCP_REGISTRY
    import shutil
    connected = {s.get("id") for s in mcp_client.list_servers()}
    rows = []
    for r in MCP_REGISTRY:
        rows.append({
            **r,
            "connected": r["id"] in connected,
            "runtime_available": bool(shutil.which(r["command"])) if r.get("command") else False,
        })
    return {
        "servers": rows,
        "note": "runtime_available is false when the launch command is not installed on this host.",
    }


@router.post("/mcp/registry/{server_id}/connect")
async def mcp_connect_from_registry(
    server_id: str,
    data: RegistryConnect,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Add a registry server with its real launch config, then start it."""
    from app.services.mcp_registry import registry_entry
    import shutil

    entry = registry_entry(server_id)
    if not entry:
        raise HTTPException(status_code=404, detail=f"'{server_id}' is not in the MCP registry")

    missing = [k for k in entry.get("required_env", []) if not (data.env or {}).get(k)]
    if missing:
        raise HTTPException(
            status_code=400,
            detail=f"Missing required value(s): {', '.join(missing)}",
        )

    if not shutil.which(entry["command"]):
        raise HTTPException(
            status_code=400,
            detail=f"`{entry['command']}` is not installed on this host, so {entry['label']} "
                   f"cannot start here. {entry.get('note') or ''}".strip(),
        )

    result = mcp_client.add_server(entry["id"], {
        "name": entry["label"],
        "command": entry["command"],
        "args": entry["args"],
        "env": data.env or {},
        "type": "stdio",
        "enabled": True,
        "auto_start": data.auto_start,
    })
    await log_audit(db, user_id=current_user.id, action="MCP_ADD",
                    resource_type="server", resource_id=entry["id"], success=True)

    started = None
    if data.auto_start:
        # Re-run the handshake cleanly: a previously running process would
        # short-circuit start_server and skip the tools/list discovery.
        try:
            await mcp_client.stop_server(entry["id"])
        except Exception:
            pass
        started = await mcp_client.start_server(entry["id"])
        # Record any tools the server advertised so they are browsable.
        mcp_client.servers[entry["id"]]["tools"] = mcp_client.servers[entry["id"]].get("tools", [])
        mcp_client._save_config()

    return {
        "added": result,
        "start": started,
        "server": next((s for s in mcp_client.list_servers() if s.get("id") == entry["id"]), None),
    }


@router.get("/mcp/tools")
async def mcp_all_tools(current_user: User = Depends(get_current_user)):
    """Every callable tool: Mark-Imti's own skills/tools plus live MCP servers."""
    from app.services import builtin_tools
    tools = list(builtin_tools.list_tools())
    for s in mcp_client.list_servers():
        for t in s.get("tools", []) or []:
            tools.append({
                "name": t.get("name"),
                "description": t.get("description", ""),
                "server": s.get("id"),
                "inputSchema": t.get("inputSchema") or t.get("input_schema") or {},
            })
    return {"tools": tools, "count": len(tools),
            "sources": {"builtin": len(builtin_tools.list_tools()),
                        "mcp_servers": len(tools) - len(builtin_tools.list_tools())}}


class BuiltinToolCall(BaseModel):
    tool_name: str
    arguments: Optional[Dict[str, Any]] = {}


@router.post("/mcp/tools/call")
async def mcp_call_builtin(data: BuiltinToolCall, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    """Invoke one of Mark-Imti's own tools (skills, memory, knowledge, sandbox, files, model)."""
    from app.services import builtin_tools
    try:
        out = await builtin_tools.call_tool(data.tool_name, data.arguments or {}, db, current_user)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc))
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"{type(exc).__name__}: {exc}")
    await log_audit(db, user_id=current_user.id, action="TOOL_CALL",
                    resource_type="tool", resource_id=data.tool_name, success=True)
    return {"success": True, "tool": data.tool_name, "result": out}

@router.get("/mcp/tools")
async def mcp_list_tools(current_user: User = Depends(get_current_user)):
    return {"tools": mcp_client.get_all_tools()}


# === Credentials ===

class CredentialStore(BaseModel):
    service: str
    email: str
    password: str
    extra: Optional[Dict[str, str]] = {}

class CredentialGet(BaseModel):
    service: str


@router.get("/credentials")
async def cred_list(current_user: User = Depends(get_current_user)):
    return {"credentials": credential_vault.list_services()}

@router.post("/credentials")
async def cred_store(data: CredentialStore, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    result = credential_vault.store(data.service, data.email, data.password, data.extra)
    await log_audit(db, user_id=current_user.id, action="CRED_STORE", resource_type="credential", resource_id=data.service, success=result["success"])
    return result

@router.post("/credentials/get")
async def cred_get(data: CredentialGet, current_user: User = Depends(get_current_user)):
    cred = credential_vault.get(data.service)
    if not cred:
        raise HTTPException(status_code=404, detail="No credentials found")
    return cred

@router.delete("/credentials/{service}")
async def cred_delete(service: str, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    result = credential_vault.delete(service)
    await log_audit(db, user_id=current_user.id, action="CRED_DELETE", resource_type="credential", resource_id=service, success=result["success"])
    return result

@router.get("/credentials/search/{query}")
async def cred_search(query: str, current_user: User = Depends(get_current_user)):
    return {"results": credential_vault.search(query)}


# === QA ===

class CodeAnalyze(BaseModel):
    code: str
    language: str = "python"

class TestProject(BaseModel):
    project_path: str


@router.post("/qa/analyze")
async def qa_analyze_code(data: CodeAnalyze, current_user: User = Depends(get_current_user)):
    return await qa_engine.analyze_code(data.code, data.language)

@router.post("/qa/test")
async def qa_test_project(data: TestProject, current_user: User = Depends(get_current_user)):
    return await qa_engine.test_project(data.project_path)

@router.post("/qa/check-build")
async def qa_check_build(data: TestProject, current_user: User = Depends(get_current_user)):
    return await qa_engine.check_build(data.project_path)

@router.get("/qa/stats")
async def qa_stats(current_user: User = Depends(get_current_user)):
    return qa_engine.get_stats()


# === GitHub ===

class GitHubToken(BaseModel):
    token: str

class GitHubCreateRepo(BaseModel):
    name: str
    description: Optional[str] = ""
    private: bool = False

class GitHubPush(BaseModel):
    local_path: str
    repo_url: str
    branch: str = "main"
    message: str = "Update from Mark-Imti"

class VercelDeploy(BaseModel):
    project_path: str
    project_name: Optional[str] = ""


@router.get("/github/user")
async def github_user(current_user: User = Depends(get_current_user)):
    if not github_service.token:
        raise HTTPException(status_code=400, detail="GitHub token not configured")
    return await github_service.get_user()

@router.post("/github/token")
async def github_set_token(data: GitHubToken, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    github_service.set_token(data.token)
    await log_audit(db, user_id=current_user.id, action="GITHUB_TOKEN", resource_type="github", resource_id="token", success=True)
    return {"success": True, "message": "GitHub token configured"}

@router.get("/github/repos")
async def github_list_repos(current_user: User = Depends(get_current_user)):
    if not github_service.token:
        raise HTTPException(status_code=400, detail="GitHub token not configured")
    return await github_service.list_repos()

@router.post("/github/repos")
async def github_create_repo(data: GitHubCreateRepo, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    if not github_service.token:
        raise HTTPException(status_code=400, detail="GitHub token not configured")
    result = await github_service.create_repo(data.name, data.description, data.private)
    await log_audit(db, user_id=current_user.id, action="GITHUB_CREATE_REPO", resource_type="repo", resource_id=data.name, success=True)
    return result

@router.post("/github/push")
async def github_push(data: GitHubPush, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    result = await github_service.push_to_repo(data.local_path, data.repo_url, data.branch, data.message)
    await log_audit(db, user_id=current_user.id, action="GITHUB_PUSH", resource_type="repo", resource_id=data.repo_url, success=result["success"])
    return result

@router.post("/deploy/vercel")
async def deploy_vercel(data: VercelDeploy, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    result = await github_service.deploy_to_vercel(data.project_path, data.project_name)
    await log_audit(db, user_id=current_user.id, action="VERCEL_DEPLOY", resource_type="deployment", resource_id=data.project_path, success=result["success"])
    return result


# === Vision ===

class ImageAnalyze(BaseModel):
    image_path: str
    question: str = "What do you see?"

class YouTubeURL(BaseModel):
    url: str

class OCRRequest(BaseModel):
    image_path: str

class CompareImages(BaseModel):
    image1_path: str
    image2_path: str


@router.post("/vision/analyze-image")
async def vision_analyze_image(data: ImageAnalyze, current_user: User = Depends(get_current_user)):
    return await vision_engine.analyze_image(data.image_path, data.question)

@router.post("/vision/read-screenshot")
async def vision_read_screenshot(data: ImageAnalyze, current_user: User = Depends(get_current_user)):
    return await vision_engine.read_screenshot(data.image_path)

@router.post("/vision/youtube")
async def vision_youtube(data: YouTubeURL, current_user: User = Depends(get_current_user)):
    return await vision_engine.understand_youtube(data.url)

@router.post("/vision/youtube-playlist")
async def vision_youtube_playlist(data: YouTubeURL, current_user: User = Depends(get_current_user)):
    return await vision_engine.understand_youtube_playlist(data.url)

@router.post("/vision/ocr")
async def vision_ocr(data: OCRRequest, current_user: User = Depends(get_current_user)):
    return await vision_engine.ocr_image(data.image_path)

@router.post("/vision/compare")
async def vision_compare(data: CompareImages, current_user: User = Depends(get_current_user)):
    return await vision_engine.compare_images(data.image1_path, data.image2_path)

@router.get("/vision/stats")
async def vision_stats(current_user: User = Depends(get_current_user)):
    return vision_engine.get_stats()
