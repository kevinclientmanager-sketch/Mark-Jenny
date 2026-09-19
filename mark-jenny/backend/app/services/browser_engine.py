import asyncio
import json
import os
from pathlib import Path
from typing import Optional, Dict, Any, List
from datetime import datetime
import uuid

try:
    from playwright.async_api import async_playwright, Browser, Page, BrowserContext
    PLAYWRIGHT_AVAILABLE = True
except ImportError:
    PLAYWRIGHT_AVAILABLE = False
    async_playwright = None

import httpx
from app.core.config import get_settings

settings = get_settings()
BROWSER_DATA_DIR = Path(settings.UPLOAD_DIR) / "browser_sessions"
BROWSER_DATA_DIR.mkdir(parents=True, exist_ok=True)

class BrowserCapability(str):
    SUPPORTED = "supported"
    FALLBACK = "fallback"
    UNSUPPORTED = "unsupported"

def get_browser_capability() -> Dict[str, str]:
    if PLAYWRIGHT_AVAILABLE:
        return {"status": BrowserCapability.SUPPORTED, "detail": "Playwright available - full automation"}
    else:
        return {"status": BrowserCapability.FALLBACK, "detail": "Playwright not installed - fallback to httpx (install: pip install playwright && playwright install)"}

class BrowserSession:
    def __init__(self, session_id: str, owner_id: int, persistent: bool = False):
        self.session_id = session_id
        self.owner_id = owner_id
        self.persistent = persistent
        self.created_at = datetime.utcnow()
        self.last_used = datetime.utcnow()
        self.page: Optional[Any] = None
        self.context: Optional[Any] = None
        self.browser: Optional[Any] = None
        self.playwright = None
        self.current_url: Optional[str] = None
        self.cookies: List[Dict] = []
        self.storage_path = BROWSER_DATA_DIR / f"{session_id}.json"

    async def init(self):
        if not PLAYWRIGHT_AVAILABLE:
            return False
        try:
            self.playwright = await async_playwright().start()
            self.browser = await self.playwright.chromium.launch(headless=True)
            self.context = await self.browser.new_context(
                viewport={"width": 1280, "height": 800},
                user_agent="MARK-JENNY/1.0",
                storage_state=str(self.storage_path) if self.persistent and self.storage_path.exists() else None
            )
            self.page = await self.context.new_page()
            return True
        except Exception as e:
            print(f"Browser init failed: {e}")
            return False

    async def navigate(self, url: str) -> Dict:
        self.last_used = datetime.utcnow()
        self.current_url = url
        if PLAYWRIGHT_AVAILABLE and self.page:
            try:
                await self.page.goto(url, wait_until="domcontentloaded", timeout=15000)
                title = await self.page.title()
                return {"success": True, "url": url, "title": title, "mode": "playwright"}
            except Exception as e:
                return {"success": False, "error": str(e), "mode": "playwright"}
        else:
            # Fallback: fetch via httpx
            try:
                async with httpx.AsyncClient(timeout=10, follow_redirects=True) as client:
                    r = await client.get(url, headers={"User-Agent": "MARK-JENNY/1.0"})
                    text = r.text[:5000]
                    return {"success": True, "url": url, "status": r.status_code, "snippet": text[:500], "mode": "fallback"}
            except Exception as e:
                return {"success": False, "error": str(e), "mode": "fallback"}

    async def search(self, query: str, engine: str = "duckduckgo") -> Dict:
        url = f"https://duckduckgo.com/html/?q={query}" if engine=="duckduckgo" else f"https://www.google.com/search?q={query}"
        return await self.navigate(url)

    async def click(self, selector: str) -> Dict:
        if PLAYWRIGHT_AVAILABLE and self.page:
            try:
                await self.page.click(selector, timeout=5000)
                return {"success": True, "selector": selector}
            except Exception as e:
                return {"success": False, "error": str(e)}
        return {"success": False, "error": "Click requires Playwright - install playwright"}

    async def type_text(self, selector: str, text: str) -> Dict:
        if PLAYWRIGHT_AVAILABLE and self.page:
            try:
                await self.page.fill(selector, text, timeout=5000)
                return {"success": True, "selector": selector}
            except Exception as e:
                return {"success": False, "error": str(e)}
        return {"success": False, "error": "Type requires Playwright"}

    async def scroll(self, y: int = 500) -> Dict:
        if PLAYWRIGHT_AVAILABLE and self.page:
            try:
                await self.page.mouse.wheel(0, y)
                return {"success": True, "y": y}
            except Exception as e:
                return {"success": False, "error": str(e)}
        return {"success": False, "error": "Scroll requires Playwright"}

    async def read_page(self) -> Dict:
        if PLAYWRIGHT_AVAILABLE and self.page:
            try:
                content = await self.page.content()
                text = await self.page.inner_text("body")
                return {"success": True, "html": content[:10000], "text": text[:5000], "url": self.page.url}
            except Exception as e:
                return {"success": False, "error": str(e)}
        elif self.current_url:
            return await self.navigate(self.current_url)
        return {"success": False, "error": "No page loaded"}

    async def extract(self, selector: str, attribute: Optional[str] = None) -> Dict:
        if PLAYWRIGHT_AVAILABLE and self.page:
            try:
                if attribute:
                    vals = await self.page.eval_on_selector_all(selector, f"els => els.map(e => e.getAttribute('{attribute}'))")
                else:
                    vals = await self.page.eval_on_selector_all(selector, "els => els.map(e => e.innerText)")
                return {"success": True, "data": vals[:50], "count": len(vals)}
            except Exception as e:
                return {"success": False, "error": str(e)}
        return {"success": False, "error": "Extract requires Playwright"}

    async def screenshot(self) -> Optional[bytes]:
        if PLAYWRIGHT_AVAILABLE and self.page:
            try:
                return await self.page.screenshot(full_page=False)
            except:
                return None
        return None

    async def save_storage(self):
        if self.persistent and self.context:
            try:
                await self.context.storage_state(path=str(self.storage_path))
            except: pass

    async def close(self):
        try:
            if self.persistent:
                await self.save_storage()
            if self.context:
                await self.context.close()
            if self.browser:
                await self.browser.close()
            if self.playwright:
                await self.playwright.stop()
        except: pass

class BrowserEngine:
    def __init__(self):
        self.sessions: Dict[str, BrowserSession] = {}

    def capability(self) -> Dict:
        return get_browser_capability()

    async def create_session(self, owner_id: int, persistent: bool = False) -> BrowserSession:
        sid = str(uuid.uuid4())
        sess = BrowserSession(sid, owner_id, persistent)
        ok = await sess.init()
        self.sessions[sid] = sess
        return sess

    def get_session(self, session_id: str) -> Optional[BrowserSession]:
        return self.sessions.get(session_id)

    async def close_session(self, session_id: str):
        sess = self.sessions.pop(session_id, None)
        if sess:
            await sess.close()

browser_engine = BrowserEngine()
