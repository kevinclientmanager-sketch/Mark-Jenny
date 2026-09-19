from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from pydantic import BaseModel
from typing import Optional, List, Dict, Any

from app.db.base import get_db
from app.core.security import get_current_user
from app.models.user import User, UserRole
from app.services.airllm_engine import airllm_engine, SUPPORTED_MODELS
from app.services.smart_scraper import smart_scraper
from app.utils.audit import log_audit

router = APIRouter()


# === AirLLM Endpoints ===

class AirLLMLoadRequest(BaseModel):
    model_id: str

class AirLLMGenerateRequest(BaseModel):
    prompt: str
    model_id: Optional[str] = None
    max_new_tokens: int = 2048
    temperature: float = 0.7
    top_p: float = 0.9
    top_k: int = 50
    repetition_penalty: float = 1.1
    system_prompt: Optional[str] = None
    stop: Optional[List[str]] = None

class AirLLMUnloadRequest(BaseModel):
    model_id: Optional[str] = None


@router.get("/airllm/status")
async def airllm_status(current_user: User = Depends(get_current_user)):
    return airllm_engine.get_capabilities()

@router.get("/airllm/models")
async def airllm_list_models(current_user: User = Depends(get_current_user)):
    return {"models": airllm_engine.list_models(), "available": airllm_engine.is_available()}

@router.post("/airllm/load")
async def airllm_load(data: AirLLMLoadRequest, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    result = airllm_engine.load_model(data.model_id)
    await log_audit(db, user_id=current_user.id, action="AIRLLM_LOAD", resource_type="model", resource_id=data.model_id, success=result["success"])
    return result

@router.post("/airllm/unload")
async def airllm_unload(data: AirLLMUnloadRequest, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    result = airllm_engine.unload_model(data.model_id)
    await log_audit(db, user_id=current_user.id, action="AIRLLM_UNLOAD", resource_type="model", resource_id=data.model_id or "current", success=result["success"])
    return result

@router.post("/airllm/generate")
async def airllm_generate(data: AirLLMGenerateRequest, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    result = await airllm_engine.generate(
        prompt=data.prompt,
        model_id=data.model_id,
        max_new_tokens=data.max_new_tokens,
        temperature=data.temperature,
        top_p=data.top_p,
        top_k=data.top_k,
        repetition_penalty=data.repetition_penalty,
        system_prompt=data.system_prompt,
        stop=data.stop,
    )
    await log_audit(db, user_id=current_user.id, action="AIRLLM_GENERATE", resource_type="model", resource_id=data.model_id or airllm_engine.current_model_id or "none", success=result["success"])
    return result


# === Scrapling Endpoints ===

class ScrapPageRequest(BaseModel):
    url: str
    backend: str = "stealth"
    target_element: Optional[str] = None
    wait_selector: Optional[str] = None
    proxy: Optional[str] = None
    timeout: int = 30

class ScrapManyRequest(BaseModel):
    urls: List[str]
    backend: str = "stealth"
    concurrency: int = 3
    proxy: Optional[str] = None

class AutoPaginateRequest(BaseModel):
    start_url: str
    next_selector: str = "a.next, a[rel=next], .pagination .next a"
    max_pages: int = 10
    backend: str = "stealth"
    target_element: Optional[str] = None
    proxy: Optional[str] = None

class ExtractStructuredRequest(BaseModel):
    url: str
    extract_schema: Dict[str, str]
    backend: str = "stealth"
    proxy: Optional[str] = None

class ToMarkdownRequest(BaseModel):
    url: str
    backend: str = "stealth"


@router.get("/scrapling/status")
async def scrapling_status(current_user: User = Depends(get_current_user)):
    return smart_scraper.get_capabilities()

@router.post("/scrapling/scrape")
async def scrapling_scrape_page(data: ScrapPageRequest, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    result = await smart_scraper.scrape_page(
        url=data.url,
        backend=data.backend,
        target_element=data.target_element,
        wait_selector=data.wait_selector,
        proxy=data.proxy,
        timeout=data.timeout,
    )
    await log_audit(db, user_id=current_user.id, action="SCRAPLING_SCRAPE", resource_type="url", resource_id=data.url, success=result["success"])
    return result

@router.post("/scrapling/scrape-many")
async def scrapling_scrape_many(data: ScrapManyRequest, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    result = await smart_scraper.scrape_many(
        urls=data.urls,
        backend=data.backend,
        concurrency=data.concurrency,
        proxy=data.proxy,
    )
    await log_audit(db, user_id=current_user.id, action="SCRAPLING_SCRAPE_MANY", resource_type="urls", resource_id=f"{len(data.urls)} URLs", success=result["success"])
    return result

@router.post("/scrapling/auto-paginate")
async def scrapling_auto_paginate(data: AutoPaginateRequest, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    result = await smart_scraper.auto_paginate(
        start_url=data.start_url,
        next_selector=data.next_selector,
        max_pages=data.max_pages,
        backend=data.backend,
        target_element=data.target_element,
        proxy=data.proxy,
    )
    await log_audit(db, user_id=current_user.id, action="SCRAPLING_PAGINATE", resource_type="url", resource_id=data.start_url, success=result["success"])
    return result

@router.post("/scrapling/extract-structured")
async def scrapling_extract_structured(data: ExtractStructuredRequest, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    result = await smart_scraper.extract_structured(
        url=data.url,
        schema=data.extract_schema,
        backend=data.backend,
        proxy=data.proxy,
    )
    await log_audit(db, user_id=current_user.id, action="SCRAPLING_EXTRACT", resource_type="url", resource_id=data.url, success=result["success"])
    return result

@router.post("/scrapling/to-markdown")
async def scrapling_to_markdown(data: ToMarkdownRequest, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    result = await smart_scraper.to_markdown(url=data.url, backend=data.backend)
    await log_audit(db, user_id=current_user.id, action="SCRAPLING_MARKDOWN", resource_type="url", resource_id=data.url, success=result["success"])
    return result
