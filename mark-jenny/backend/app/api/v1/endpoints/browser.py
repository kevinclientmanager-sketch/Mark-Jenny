from fastapi import APIRouter, Depends, HTTPException, Query, Response
from sqlalchemy.orm import Session
from pydantic import BaseModel
from typing import Optional, List, Dict
from datetime import datetime

from app.db.base import get_db
from app.core.security import get_current_user
from app.models.user import User
from app.services.browser_engine import browser_engine, get_browser_capability

router = APIRouter()

class NavigateRequest(BaseModel):
    url: str
    session_id: Optional[str] = None
    persistent: bool = False

class SearchRequest(BaseModel):
    query: str
    engine: str = "duckduckgo"
    session_id: Optional[str] = None

class SessionRequest(BaseModel):
    persistent: bool = False

class ClickRequest(BaseModel):
    selector: str
    session_id: str

class TypeRequest(BaseModel):
    selector: str
    text: str
    session_id: str

class ExtractRequest(BaseModel):
    selector: str
    attribute: Optional[str] = None
    session_id: str

@router.get("/capability")
async def get_capability(current_user: User = Depends(get_current_user)):
    cap = get_browser_capability()
    return {
        "capability": cap,
        "playwright_installed": cap["status"] == "supported",
        "setup": "pip install playwright && playwright install" if cap["status"] != "supported" else "ready",
        "persistent_login": "only when explicitly enabled via persistent=true",
        "sessions_active": len(browser_engine.sessions)
    }

@router.post("/sessions", status_code=201)
async def create_session(data: SessionRequest, current_user: User = Depends(get_current_user)):
    sess = await browser_engine.create_session(current_user.id, persistent=data.persistent)
    return {
        "session_id": sess.session_id,
        "persistent": sess.persistent,
        "created_at": sess.created_at.isoformat(),
        "capability": get_browser_capability(),
        "message": "Browser session created" if sess.page else "Fallback mode - playwright not available, will use httpx"
    }

@router.get("/sessions")
async def list_sessions(current_user: User = Depends(get_current_user)):
    # only return sessions owned by user
    user_sessions = [s for s in browser_engine.sessions.values() if s.owner_id == current_user.id]
    return [
        {"session_id": s.session_id, "persistent": s.persistent, "current_url": s.current_url, "last_used": s.last_used.isoformat(), "has_page": s.page is not None}
        for s in user_sessions
    ]

@router.delete("/sessions/{session_id}")
async def close_session(session_id: str, current_user: User = Depends(get_current_user)):
    sess = browser_engine.get_session(session_id)
    if not sess or sess.owner_id != current_user.id:
        raise HTTPException(status_code=404, detail="Session not found")
    await browser_engine.close_session(session_id)
    return {"message": "Session closed"}

@router.post("/navigate")
async def navigate(data: NavigateRequest, current_user: User = Depends(get_current_user)):
    # if no session, create one
    sess = None
    if data.session_id:
        sess = browser_engine.get_session(data.session_id)
        if not sess or sess.owner_id != current_user.id:
            raise HTTPException(status_code=404, detail="Session not found")
    else:
        sess = await browser_engine.create_session(current_user.id, persistent=data.persistent)
    result = await sess.navigate(data.url)
    return {"session_id": sess.session_id, **result}

@router.post("/search")
async def search(data: SearchRequest, current_user: User = Depends(get_current_user)):
    sess = None
    if data.session_id:
        sess = browser_engine.get_session(data.session_id)
        if not sess or sess.owner_id != current_user.id:
            raise HTTPException(status_code=404, detail="Session not found")
    else:
        sess = await browser_engine.create_session(current_user.id)
    result = await sess.search(data.query, data.engine)
    return {"session_id": sess.session_id, **result}

@router.post("/click")
async def click(data: ClickRequest, current_user: User = Depends(get_current_user)):
    sess = browser_engine.get_session(data.session_id)
    if not sess or sess.owner_id != current_user.id:
        raise HTTPException(status_code=404, detail="Session not found")
    result = await sess.click(data.selector)
    return {"session_id": data.session_id, **result}

@router.post("/type")
async def type_text(data: TypeRequest, current_user: User = Depends(get_current_user)):
    sess = browser_engine.get_session(data.session_id)
    if not sess or sess.owner_id != current_user.id:
        raise HTTPException(status_code=404, detail="Session not found")
    result = await sess.type_text(data.selector, data.text)
    return {"session_id": data.session_id, **result}

@router.post("/scroll")
async def scroll(session_id: str, y: int = 500, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    sess = browser_engine.get_session(session_id)
    if not sess or sess.owner_id != current_user.id:
        raise HTTPException(status_code=404, detail="Session not found")
    result = await sess.scroll(y)
    return {"session_id": session_id, **result}

@router.post("/read")
async def read_page(session_id: str, current_user: User = Depends(get_current_user)):
    sess = browser_engine.get_session(session_id)
    if not sess or sess.owner_id != current_user.id:
        raise HTTPException(status_code=404, detail="Session not found")
    result = await sess.read_page()
    return {"session_id": session_id, **result}

@router.post("/extract")
async def extract(data: ExtractRequest, current_user: User = Depends(get_current_user)):
    sess = browser_engine.get_session(data.session_id)
    if not sess or sess.owner_id != current_user.id:
        raise HTTPException(status_code=404, detail="Session not found")
    result = await sess.extract(data.selector, data.attribute)
    return {"session_id": data.session_id, **result}

@router.get("/sessions/{session_id}/screenshot")
async def screenshot(session_id: str, current_user: User = Depends(get_current_user)):
    from fastapi.responses import Response
    sess = browser_engine.get_session(session_id)
    if not sess or sess.owner_id != current_user.id:
        raise HTTPException(status_code=404, detail="Session not found")
    data = await sess.screenshot()
    if not data:
        raise HTTPException(status_code=400, detail="Screenshot not available - requires Playwright")
    return Response(content=data, media_type="image/png")

@router.get("/fetch")
async def fetch_page(url: str, current_user: User = Depends(get_current_user)):
    """Fetch a page server-side so the browser view can offer a real download.

    A cross-origin iframe cannot be downloaded from the client, so the bytes
    are retrieved here and streamed back.
    """
    if not url.startswith(("http://", "https://")):
        raise HTTPException(status_code=400, detail="Only http/https URLs can be fetched")
    import httpx
    try:
        async with httpx.AsyncClient(timeout=30, follow_redirects=True) as client:
            r = await client.get(url, headers={"User-Agent": "Mark-Imti/1.0"})
    except Exception as exc:
        raise HTTPException(status_code=502, detail=f"Could not reach the site: {exc}")
    if r.status_code >= 400:
        raise HTTPException(status_code=r.status_code, detail=f"Site returned HTTP {r.status_code}")
    return Response(
        content=r.content,
        media_type=r.headers.get("content-type", "text/html"),
    )
