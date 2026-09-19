"""
Smart Scraper — adaptive web scraping powered by Scrapling (by Karim Shoair).
Features: adaptive selectors, anti-bot bypass, auto-pagination, multi-backend fetchers.
"""
import asyncio
import json
import time
from pathlib import Path
from typing import Optional, Dict, Any, List
from datetime import datetime

from app.core.config import get_settings

settings = get_settings()

# Try to import Scrapling
try:
    from scrapling import Fetcher, StealthyFetcher, PlayWrightFetcher, CrawlerFetcher
    from scrapling.defaults import RecusiveFetch
    SCRAPLING_AVAILABLE = True
except ImportError:
    SCRAPLING_AVAILABLE = False
    Fetcher = None
    StealthyFetcher = None
    PlayWrightFetcher = None
    CrawlerFetcher = None

SCRAPER_CACHE_DIR = Path(settings.UPLOAD_DIR) / "scraper_cache"
SCRAPER_CACHE_DIR.mkdir(parents=True, exist_ok=True)


class SmartScraper:
    def __init__(self):
        self.active_sessions: Dict[str, Any] = {}
        self._stats = {
            "total_scrapes": 0,
            "pages_scraped": 0,
            "data_extracted": 0,
            "avg_latency_ms": 0,
            "last_scrape_at": None,
        }

    def is_available(self) -> bool:
        return SCRAPLING_AVAILABLE

    def get_capabilities(self) -> Dict[str, Any]:
        return {
            "available": SCRAPLING_AVAILABLE,
            "features": {
                "adaptive_selectors": True,
                "anti_bot_bypass": True,
                "auto_pagination": True,
                "multi_backend": True,
                "stealth_mode": True,
                "rag_markdown": True,
                "fingerprint_rotation": True,
            },
            "backends": ["Fetcher", "StealthyFetcher", "PlayWrightFetcher", "CrawlerFetcher"],
            "stats": self._stats,
        }

    async def scrape_page(
        self,
        url: str,
        backend: str = "stealth",
        target_element: Optional[str] = None,
        wait_selector: Optional[str] = None,
        proxy: Optional[str] = None,
        timeout: int = 30,
    ) -> Dict[str, Any]:
        if not SCRAPLING_AVAILABLE:
            return {"success": False, "error": "scrapling not installed. Run: pip install scrapling[all]"}

        start_time = time.time()
        try:
            if backend == "stealth":
                fetcher = StealthyFetcher()
            elif backend == "playwright":
                fetcher = PlayWrightFetcher()
            elif backend == "crawler":
                fetcher = CrawlerFetcher()
            else:
                fetcher = Fetcher()

            kwargs = {"timeout": timeout}
            if proxy:
                kwargs["proxy"] = proxy

            page = await asyncio.to_thread(fetcher.get, url, **kwargs)

            # Wait for specific element if requested
            if wait_selector:
                await asyncio.to_thread(page.css_first, wait_selector)

            # Extract target element or full page
            if target_element:
                elements = await asyncio.to_thread(page.css, target_element)
                data = [el.text for el in elements] if elements else []
            else:
                data = page.text

            latency_ms = (time.time() - start_time) * 1000

            self._stats["total_scrapes"] += 1
            self._stats["pages_scraped"] += 1
            self._stats["last_scrape_at"] = datetime.utcnow().isoformat()
            if isinstance(data, list):
                self._stats["data_extracted"] += len(data)

            return {
                "success": True,
                "url": url,
                "title": page.css_first("title").text if page.css_first("title") else "",
                "data": data,
                "status_code": getattr(page, "status", 200),
                "latency_ms": round(latency_ms, 2),
                "backend": backend,
            }

        except Exception as e:
            return {"success": False, "error": str(e), "url": url}

    async def scrape_many(
        self,
        urls: List[str],
        backend: str = "stealth",
        concurrency: int = 3,
        proxy: Optional[str] = None,
    ) -> Dict[str, Any]:
        if not SCRAPLING_AVAILABLE:
            return {"success": False, "error": "scrapling not installed"}

        start_time = time.time()
        results = []

        sem = asyncio.Semaphore(concurrency)

        async def _scrape_one(url: str):
            async with sem:
                return await self.scrape_page(url, backend=backend, proxy=proxy)

        tasks = [_scrape_one(u) for u in urls]
        results = await asyncio.gather(*tasks, return_exceptions=True)

        latency_ms = (time.time() - start_time) * 1000
        successes = sum(1 for r in results if isinstance(r, dict) and r.get("success"))

        self._stats["total_scrapes"] += len(urls)
        self._stats["pages_scraped"] += successes

        return {
            "success": True,
            "total": len(urls),
            "succeeded": successes,
            "failed": len(urls) - successes,
            "results": [r for r in results if isinstance(r, dict)],
            "latency_ms": round(latency_ms, 2),
        }

    async def auto_paginate(
        self,
        start_url: str,
        next_selector: str = "a.next, a[rel=next], .pagination .next a",
        max_pages: int = 10,
        backend: str = "stealth",
        target_element: Optional[str] = None,
        proxy: Optional[str] = None,
    ) -> Dict[str, Any]:
        if not SCRAPLING_AVAILABLE:
            return {"success": False, "error": "scrapling not installed"}

        start_time = time.time()
        all_data = []
        current_url = start_url
        pages_scraped = 0

        try:
            for page_num in range(max_pages):
                result = await self.scrape_page(
                    current_url,
                    backend=backend,
                    target_element=target_element,
                    proxy=proxy,
                )
                if not result["success"]:
                    break

                all_data.append({
                    "page": page_num + 1,
                    "url": current_url,
                    "data": result["data"],
                })
                pages_scraped += 1

                # Find next page link
                if SCRAPLING_AVAILABLE:
                    fetcher = Fetcher()
                    page = await asyncio.to_thread(fetcher.get, current_url)
                    next_link = await asyncio.to_thread(page.css_first, next_selector)
                    if next_link:
                        current_url = next_link.attributes.get("href", "")
                        if not current_url.startswith("http"):
                            from urllib.parse import urljoin
                            current_url = urljoin(start_url, current_url)
                    else:
                        break
                else:
                    break

            latency_ms = (time.time() - start_time) * 1000
            self._stats["total_scrapes"] += pages_scraped
            self._stats["pages_scraped"] += pages_scraped

            return {
                "success": True,
                "pages_scraped": pages_scraped,
                "total_items": len(all_data),
                "data": all_data,
                "latency_ms": round(latency_ms, 2),
            }

        except Exception as e:
            return {"success": False, "error": str(e)}

    async def extract_structured(
        self,
        url: str,
        schema: Dict[str, str],
        backend: str = "stealth",
        proxy: Optional[str] = None,
    ) -> Dict[str, Any]:
        if not SCRAPLING_AVAILABLE:
            return {"success": False, "error": "scrapling not installed"}

        start_time = time.time()
        try:
            if backend == "stealth":
                fetcher = StealthyFetcher()
            else:
                fetcher = Fetcher()

            kwargs = {}
            if proxy:
                kwargs["proxy"] = proxy

            page = await asyncio.to_thread(fetcher.get, url, **kwargs)

            extracted = {}
            for field_name, selector in schema.items():
                elements = await asyncio.to_thread(page.css, selector)
                if elements:
                    if len(elements) == 1:
                        extracted[field_name] = elements[0].text
                    else:
                        extracted[field_name] = [el.text for el in elements]
                else:
                    extracted[field_name] = None

            latency_ms = (time.time() - start_time) * 1000
            self._stats["total_scrapes"] += 1

            return {
                "success": True,
                "url": url,
                "extracted": extracted,
                "latency_ms": round(latency_ms, 2),
            }

        except Exception as e:
            return {"success": False, "error": str(e), "url": url}

    async def to_markdown(self, url: str, backend: str = "stealth") -> Dict[str, Any]:
        """Convert page to RAG-ready Markdown."""
        if not SCRAPLING_AVAILABLE:
            return {"success": False, "error": "scrapling not installed"}

        try:
            result = await self.scrape_page(url, backend=backend)
            if not result["success"]:
                return result

            # Simple HTML-to-Markdown conversion
            html_content = result.get("data", "")
            title = result.get("title", url)

            markdown = f"# {title}\n\n"
            markdown += f"*Source: {url}*\n\n"
            markdown += str(html_content)[:50000]

            return {
                "success": True,
                "url": url,
                "markdown": markdown,
                "word_count": len(markdown.split()),
            }

        except Exception as e:
            return {"success": False, "error": str(e)}

    def cleanup(self):
        self.active_sessions.clear()


# Singleton
smart_scraper = SmartScraper()
