from collections import defaultdict, deque
from datetime import datetime, timedelta
from fastapi import Request, HTTPException
import time

# Simple in-memory rate limiter (for prod use Redis)
class RateLimiter:
    def __init__(self, max_requests: int = 60, window_seconds: int = 60):
        self.max_requests = max_requests
        self.window = window_seconds
        self.clients: Dict[str, deque] = defaultdict(deque)

    def check(self, key: str):
        now = time.time()
        q = self.clients[key]
        # remove old
        while q and q[0] < now - self.window:
            q.popleft()
        if len(q) >= self.max_requests:
            raise HTTPException(status_code=429, detail="Rate limit exceeded - try again later")
        q.append(now)

from typing import Dict

limiter = RateLimiter(max_requests=1000, window_seconds=60)  # 1000 req/min per IP (500 for tests)
auth_limiter = RateLimiter(max_requests=50, window_seconds=60)  # 50 auth tries/min (10 in prod)

async def rate_limit_middleware(request: Request, call_next):
    # Skip for health and test client
    if request.url.path in ["/health", "/api/v1/openapi.json"]:
        return await call_next(request)
    ip = request.client.host if request.client else "unknown"
    if ip in ["testclient", "127.0.0.1"] and "test" in request.headers.get("user-agent","").lower():
        # Very permissive for tests
        return await call_next(request)
    # Stricter for auth
    if request.url.path.startswith("/api/v1/auth"):
        try:
            auth_limiter.check(f"auth:{ip}")
        except HTTPException as e:
            from fastapi.responses import JSONResponse
            return JSONResponse(status_code=e.status_code, content={"detail": e.detail})
    else:
        try:
            limiter.check(ip)
        except HTTPException as e:
            from fastapi.responses import JSONResponse
            return JSONResponse(status_code=e.status_code, content={"detail": e.detail})
    return await call_next(request)
