from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from pydantic import BaseModel
from typing import Optional, List, Dict, Any
from datetime import datetime

from app.db.base import get_db
from app.core.security import get_current_user
from app.models.user import User, UserRole
from app.models.agent import Model, ModelProvider, ModelCapability, ModelProviderConfig, Agent, AgentType
from app.services.model_router import ModelRouter, ensure_default_models, TASK_TYPE_CAPABILITY_MAP
from app.services.agent_controller import AgentController
from app.utils.audit import log_audit
import json

router = APIRouter()

# Ensure default models exist on first call
def ensure_models(db: Session):
    ensure_default_models(db)

# --- Models ---
class ModelCreate(BaseModel):
    name: str
    display_name: Optional[str] = None
    provider: ModelProvider
    model_id: str
    capabilities: List[ModelCapability] = []
    context_window: Optional[int] = None
    max_output_tokens: Optional[int] = None
    cost_per_1k_input: Optional[int] = None
    cost_per_1k_output: Optional[int] = None
    is_local: bool = False
    is_active: bool = True
    config: Optional[dict] = None

class ModelUpdate(BaseModel):
    display_name: Optional[str] = None
    capabilities: Optional[List[ModelCapability]] = None
    context_window: Optional[int] = None
    max_output_tokens: Optional[int] = None
    cost_per_1k_input: Optional[int] = None
    cost_per_1k_output: Optional[int] = None
    is_active: Optional[bool] = None
    config: Optional[dict] = None

class ModelResponse(BaseModel):
    id: int
    name: str
    display_name: Optional[str]
    provider: str
    model_id: str
    capabilities: Optional[List[str]]
    context_window: Optional[int]
    max_output_tokens: Optional[int]
    cost_per_1k_input: Optional[int]
    cost_per_1k_output: Optional[int]
    is_local: bool
    is_active: bool
    config: Optional[dict]
    created_at: datetime
    class Config:
        from_attributes = True

@router.get("/models", response_model=List[ModelResponse])
async def list_models(
    provider: Optional[ModelProvider] = None,
    is_local: Optional[bool] = None,
    capability: Optional[ModelCapability] = None,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    ensure_models(db)
    q = db.query(Model)
    if provider:
        q = q.filter(Model.provider == provider)
    if is_local is not None:
        q = q.filter(Model.is_local == is_local)
    models = q.all()
    if capability:
        filtered = []
        for m in models:
            caps = [c.value if hasattr(c,'value') else str(c) for c in (m.capabilities or [])]
            if capability.value in caps:
                filtered.append(m)
        models = filtered
    return [ModelResponse.model_validate(m) for m in models]

@router.post("/models", response_model=ModelResponse, status_code=201)
async def create_model(data: ModelCreate, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    if current_user.role not in [UserRole.ADMIN, UserRole.CREATOR]:
        raise HTTPException(status_code=403, detail="Only admin/creator can create models")
    m = Model(**data.model_dump())
    db.add(m); db.commit(); db.refresh(m)
    await log_audit(db, user_id=current_user.id, action="SETTINGS_CHANGE", resource_type="model", resource_id=str(m.id), success=True)
    return ModelResponse.model_validate(m)

@router.get("/models/{model_id}", response_model=ModelResponse)
async def get_model(model_id: int, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    m = db.query(Model).filter(Model.id == model_id).first()
    if not m: raise HTTPException(status_code=404, detail="Model not found")
    return ModelResponse.model_validate(m)

@router.patch("/models/{model_id}", response_model=ModelResponse)
async def update_model(model_id: int, data: ModelUpdate, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    if current_user.role not in [UserRole.ADMIN, UserRole.CREATOR]:
        raise HTTPException(status_code=403, detail="Only admin/creator")
    m = db.query(Model).filter(Model.id == model_id).first()
    if not m: raise HTTPException(status_code=404, detail="Model not found")
    for k,v in data.model_dump(exclude_unset=True).items():
        setattr(m, k, v)
    db.commit(); db.refresh(m)
    return ModelResponse.model_validate(m)

@router.delete("/models/{model_id}")
async def delete_model(model_id: int, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    if current_user.role != UserRole.ADMIN:
        raise HTTPException(status_code=403, detail="Admin only")
    m = db.query(Model).filter(Model.id == model_id).first()
    if not m: raise HTTPException(status_code=404, detail="Model not found")
    db.delete(m); db.commit()
    return {"message":"Model deleted"}

# --- Provider Configs ---
class ProviderConfigCreate(BaseModel):
    provider: ModelProvider
    api_key: Optional[str] = None
    base_url: Optional[str] = None
    config: Optional[dict] = None
    is_default: bool = False

class ProviderConfigResponse(BaseModel):
    id: int
    provider: str
    base_url: Optional[str]
    has_key: bool
    is_default: bool
    created_at: datetime
    class Config:
        from_attributes = True

def _encrypt_key(key: str) -> str:
    """Encrypt a provider API key with the real Fernet vault.

    Previously this was plain base64, which is reversible by anyone with the
    database. Legacy base64 values are still readable (see ModelRouter._decrypt_key)
    and are re-encrypted the next time the key is saved.
    """
    if not key:
        return ""
    try:
        from app.services.credential_vault import _encrypt
        blob = _encrypt(key)
        return f"fernet:{blob}"
    except Exception:
        import base64
        return "b64:" + base64.b64encode(key.encode()).decode()

def _has_key(enc: Optional[str]) -> bool:
    return bool(enc)

@router.get("/providers", response_model=List[ProviderConfigResponse])
async def list_providers(current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    configs = db.query(ModelProviderConfig).filter(ModelProviderConfig.user_id == current_user.id).all()
    return [ProviderConfigResponse(id=c.id, provider=c.provider.value, base_url=c.base_url, has_key=_has_key(c.api_key_encrypted), is_default=c.is_default, created_at=c.created_at) for c in configs]


@router.get("/status")
async def models_status(current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    """Which models are connected/configured for this user (powers Settings status dots)."""
    import httpx
    from app.core.config import get_settings
    settings = get_settings()
    configs = {c.provider: c for c in db.query(ModelProviderConfig).filter(ModelProviderConfig.user_id == current_user.id).all()}

    ollama_models: list = []
    ollama_ok = False
    try:
        async with httpx.AsyncClient(timeout=4) as client:
            r = await client.get(f"{settings.OLLAMA_BASE_URL.rstrip('/')}/api/tags")
            if r.status_code == 200:
                ollama_ok = True
                ollama_models = [m.get("name", "") for m in r.json().get("models", [])]
    except Exception:
        pass

    providers = []
    for p in ModelProvider:
        cfg = configs.get(p)
        has_key = bool(cfg and cfg.api_key_encrypted)
        reachable = "unknown"
        if p == ModelProvider.OLLAMA:
            reachable = "online" if ollama_ok else "offline"
        elif has_key:
            reachable = "configured"
        providers.append({
            "provider": p.value,
            "configured": has_key or (p == ModelProvider.OLLAMA and ollama_ok),
            "has_key": has_key,
            "is_default": bool(cfg and cfg.is_default),
            "reachable": reachable,
            "base_url": cfg.base_url if cfg else None,
        })
    return {
        "providers": providers,
        "ollama_models": ollama_models,
        "runtime_mode": (settings.MODEL_RUNTIME_MODE or "cloud"),
        "chat_ready": any(x["configured"] for x in providers),
    }

@router.post("/providers", response_model=ProviderConfigResponse)
async def upsert_provider(data: ProviderConfigCreate, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    existing = db.query(ModelProviderConfig).filter(ModelProviderConfig.user_id==current_user.id, ModelProviderConfig.provider==data.provider).first()
    enc = _encrypt_key(data.api_key) if data.api_key else None
    if existing:
        if enc: existing.api_key_encrypted = enc
        if data.base_url is not None: existing.base_url = data.base_url
        if data.config is not None: existing.config = data.config
        existing.is_default = data.is_default
        db.commit(); db.refresh(existing)
        cfg = existing
    else:
        cfg = ModelProviderConfig(user_id=current_user.id, provider=data.provider, api_key_encrypted=enc, base_url=data.base_url, config=data.config, is_default=data.is_default)
        db.add(cfg); db.commit(); db.refresh(cfg)
    await log_audit(db, user_id=current_user.id, action="SETTINGS_CHANGE", resource_type="provider", resource_id=str(cfg.id), success=True)
    return ProviderConfigResponse(id=cfg.id, provider=cfg.provider.value, base_url=cfg.base_url, has_key=_has_key(cfg.api_key_encrypted), is_default=cfg.is_default, created_at=cfg.created_at)

@router.delete("/providers/{provider}")
async def delete_provider(provider: ModelProvider, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    cfg = db.query(ModelProviderConfig).filter(ModelProviderConfig.user_id==current_user.id, ModelProviderConfig.provider==provider).first()
    if not cfg: raise HTTPException(status_code=404, detail="Provider config not found")
    db.delete(cfg); db.commit()
    return {"message":"Provider config deleted"}


class ProviderTestRequest(BaseModel):
    provider: ModelProvider
    api_key: Optional[str] = None
    base_url: Optional[str] = None
    model: Optional[str] = None


@router.post("/providers/test")
async def test_provider(data: ProviderTestRequest, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    """Actually call the provider with a trivial prompt and report the real outcome.

    This is what makes 'Connect' meaningful: a stored key that the provider
    rejects is reported as a failure instead of silently looking configured.
    """
    import httpx

    cfg = db.query(ModelProviderConfig).filter(
        ModelProviderConfig.user_id == current_user.id,
        ModelProviderConfig.provider == data.provider,
    ).first()

    router_svc = ModelRouter(db, current_user.id)
    key = data.api_key
    if not key and cfg:
        key = router_svc._decrypt_key(cfg.api_key_encrypted)
    if not key and data.provider != ModelProvider.OLLAMA:
        raise HTTPException(status_code=400, detail="No API key supplied or saved for this provider.")

    model = data.model or (cfg.config or {}).get("model") or router_svc.PROVIDER_DEFAULT_MODELS.get(data.provider, "")
    base = (data.base_url or (cfg.base_url if cfg else None) or "").rstrip("/")
    prompt = "Reply with the single word: OK"
    try:
        if data.provider == ModelProvider.ANTHROPIC:
            async with httpx.AsyncClient(timeout=45) as client:
                r = await client.post(
                    "https://api.anthropic.com/v1/messages",
                    headers={"x-api-key": key, "anthropic-version": "2023-06-01", "Content-Type": "application/json"},
                    json={"model": model or "claude-3-5-sonnet-20241022", "max_tokens": 16,
                          "messages": [{"role": "user", "content": prompt}]},
                )
        elif data.provider == ModelProvider.GOOGLE:
            async with httpx.AsyncClient(timeout=45) as client:
                r = await client.post(
                    f"https://generativelanguage.googleapis.com/v1beta/models/{model or 'gemini-2.0-flash'}:generateContent",
                    headers={"x-goog-api-key": key, "Content-Type": "application/json"},
                    json={"contents": [{"parts": [{"text": prompt}]}], "generationConfig": {"maxOutputTokens": 16}},
                )
        else:
            url = f"{base or 'https://api.openai.com/v1'}/chat/completions"
            default_model = {
                ModelProvider.OPENAI: "gpt-4o-mini",
                ModelProvider.DEEPSEEK: "deepseek-chat",
                ModelProvider.MISTRAL: "mistral-small-latest",
                ModelProvider.XAI: "grok-2-latest",
                ModelProvider.OPENROUTER: "openai/gpt-4o-mini",
            }.get(data.provider, "gpt-4o-mini")
            async with httpx.AsyncClient(timeout=45) as client:
                r = await client.post(
                    url,
                    headers={"Content-Type": "application/json", "Authorization": f"Bearer {key}"},
                    json={"model": model or default_model,
                          "messages": [{"role": "user", "content": prompt}],
                          "max_tokens": 16},
                )
    except Exception as exc:
        return {"ok": False, "provider": data.provider.value, "detail": f"Could not reach provider: {exc}"}

    if r.status_code == 200:
        return {"ok": True, "provider": data.provider.value, "model": model, "detail": "Connection succeeded."}

    detail = ""
    try:
        body = r.json()
        detail = (body.get("error") or {}).get("message") or body.get("detail") or json.dumps(body)[:300]
    except Exception:
        detail = (r.text or "")[:300]

    friendly = {
        400: "Bad request - the API key or model name was rejected.",
        401: "Invalid API key. Check the key in Settings.",
        402: "Payment required - the account has no credit.",
        403: "Access denied - this key cannot use that model.",
        404: "Model or endpoint not found. Check the model name.",
        429: "Rate limited or out of quota. Check the account billing/limits.",
    }.get(r.status_code, f"Provider returned HTTP {r.status_code}.")

    return {"ok": False, "provider": data.provider.value, "status_code": r.status_code,
            "detail": f"{friendly} {detail}".strip()}

# --- Agents ---
class AgentCreate(BaseModel):
    name: str
    type: AgentType
    description: Optional[str] = None
    system_prompt: Optional[str] = None
    model_id: Optional[int] = None
    available_tools: Optional[List[str]] = None
    available_skills: Optional[List[str]] = None
    config: Optional[dict] = None

class AgentResponse(BaseModel):
    id: int
    name: str
    type: str
    description: Optional[str]
    system_prompt: Optional[str]
    model_id: Optional[int]
    model_name: Optional[str]
    available_tools: Optional[List[str]]
    available_skills: Optional[List[str]]
    config: Optional[dict]
    is_active: bool
    created_at: datetime
    class Config:
        from_attributes = True

@router.get("/agents", response_model=List[AgentResponse])
async def list_agents(current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    agents = db.query(Agent).filter(Agent.is_active==True).all()
    res = []
    for a in agents:
        model_name = None
        if a.model_id:
            m = db.query(Model).filter(Model.id==a.model_id).first()
            if m: model_name = m.name
        res.append(AgentResponse(id=a.id, name=a.name, type=a.type.value, description=a.description, system_prompt=a.system_prompt, model_id=a.model_id, model_name=model_name, available_tools=a.available_tools, available_skills=a.available_skills, config=a.config, is_active=a.is_active, created_at=a.created_at))
    return res

@router.post("/agents", response_model=AgentResponse, status_code=201)
async def create_agent(data: AgentCreate, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    if current_user.role not in [UserRole.ADMIN, UserRole.CREATOR]:
        raise HTTPException(status_code=403, detail="Only admin/creator")
    ag = Agent(**data.model_dump())
    db.add(ag); db.commit(); db.refresh(ag)
    return AgentResponse(id=ag.id, name=ag.name, type=ag.type.value, description=ag.description, system_prompt=ag.system_prompt, model_id=ag.model_id, model_name=None, available_tools=ag.available_tools, available_skills=ag.available_skills, config=ag.config, is_active=ag.is_active, created_at=ag.created_at)

@router.get("/agents/{agent_id}", response_model=AgentResponse)
async def get_agent(agent_id: int, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    ag = db.query(Agent).filter(Agent.id==agent_id).first()
    if not ag: raise HTTPException(status_code=404, detail="Agent not found")
    model_name = None
    if ag.model_id:
        m = db.query(Model).filter(Model.id==ag.model_id).first()
        if m: model_name=m.name
    return AgentResponse(id=ag.id, name=ag.name, type=ag.type.value, description=ag.description, system_prompt=ag.system_prompt, model_id=ag.model_id, model_name=model_name, available_tools=ag.available_tools, available_skills=ag.available_skills, config=ag.config, is_active=ag.is_active, created_at=ag.created_at)

# --- Router ---
class RouteRequest(BaseModel):
    task_type: str = "fast"
    prompt: Optional[str] = None
    prefer_local: Optional[bool] = None
    prefer_cheap: bool = False
    require_capabilities: Optional[List[str]] = None

@router.post("/route")
async def route_model(data: RouteRequest, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    ensure_models(db)
    router = ModelRouter(db, current_user.id)
    model = await router.select_model(task_type=data.task_type, prefer_local=data.prefer_local, prefer_cheap=data.prefer_cheap, require_capabilities=data.require_capabilities)
    if not model:
        raise HTTPException(status_code=404, detail="No suitable model found - configure a provider or enable Ollama")
    return {
        "selected": {"id": model.id, "name": model.name, "provider": model.provider.value, "model_id": model.model_id, "is_local": model.is_local, "cost_input": model.cost_per_1k_input, "cost_output": model.cost_per_1k_output},
        "task_type": data.task_type,
        "hybrid": f"Ollama available: {await router.registry.is_ollama_available()}",
        "fallback_chain": [{"id": m.id, "name": m.name} for m in await router.select_with_fallback_chain(data.task_type) if m.id != model.id][:2]
    }

class PlanRequest(BaseModel):
    user_request: str
    project_id: Optional[int] = None
    task_type: str = "fast"

@router.post("/plan")
async def plan_task(data: PlanRequest, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    ensure_models(db)
    ctrl = AgentController(db, current_user.id)
    plan = await ctrl.plan_task(data.user_request, data.project_id, data.task_type)
    cost = await ctrl.estimate_cost(data.user_request, data.task_type)
    return {"plan": plan, "cost": cost}

@router.get("/capabilities/list")
async def list_capabilities(current_user: User = Depends(get_current_user)):
    return {
        "task_types": list(TASK_TYPE_CAPABILITY_MAP.keys()),
        "capabilities": [c.value for c in ModelCapability],
        "providers": [p.value for p in ModelProvider],
        "agent_types": [a.value for a in AgentType]
    }
