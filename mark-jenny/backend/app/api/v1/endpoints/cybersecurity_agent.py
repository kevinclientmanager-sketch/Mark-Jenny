"""
Cybersecurity Agent API — Mythos-level security analysis.
Routes: /api/v1/cybersecurity-agent/
"""
from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel, Field
from typing import Optional, List
from app.services.cybersecurity_agent import cybersecurity_agent
from app.core.security import get_current_user
from app.models.user import User

router = APIRouter(tags=["Cybersecurity Agent"], dependencies=[Depends(get_current_user)])


class CodeScanRequest(BaseModel):
    code: str
    filename: str = "unknown"
    language: str = "auto"


class CodebaseScanRequest(BaseModel):
    directory: str


class WebAuditRequest(BaseModel):
    url: str


class ExploitAnalysisRequest(BaseModel):
    code: str
    vulnerability: str
    filename: str = ""


class SecurityLoopRequest(BaseModel):
    code: str
    filename: str = ""


class SiteSafetyRequest(BaseModel):
    url: str


class ScanRequest(BaseModel):
    """Generic scan used by the Security page's 'Run Scan' button.

    Dispatches to the right agent based on what was supplied, so the page has
    one entry point instead of guessing which route exists.
    """
    target: str = ""
    url: str = ""
    code: str = ""
    filename: str = ""
    mode: str = "auto"   # auto | code | codebase | site | posture


@router.post("/scan")
async def scan(req: ScanRequest, current_user: User = Depends(get_current_user)):
    """Single dispatching security scan endpoint (the Security page used to 404 here)."""
    mode = (req.mode or "auto").lower()
    code = req.code or ""
    url = req.url or req.target or ""
    target = req.target or url

    if mode == "auto":
        if code:
            mode = "code"
        elif url.startswith("http://") or url.startswith("https://"):
            mode = "posture"
        else:
            mode = "codebase"

    try:
        if mode == "code":
            if not code:
                raise HTTPException(status_code=400, detail="Provide `code` to scan, or a `target` path to scan a codebase.")
            return await cybersecurity_agent.scan_code(code, req.filename or "snippet", "auto")
        if mode == "codebase":
            if not target:
                raise HTTPException(status_code=400, detail="Provide a directory or file path in `target`.")
            return await cybersecurity_agent.scan_codebase(target)
        if mode == "site":
            if not url:
                raise HTTPException(status_code=400, detail="Provide a `url` to assess.")
            return await cybersecurity_agent.site_safety(url)
        # posture
        if not url:
            raise HTTPException(status_code=400, detail="Provide a `url` to audit.")
        return await cybersecurity_agent.security_posture(url)
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# 1. Scan code for vulnerabilities
@router.post("/scan-code")
async def scan_code(req: CodeScanRequest, current_user: User = Depends(get_current_user)):

    try:
        return await cybersecurity_agent.scan_code(req.code, req.filename, req.language)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/security-posture")
async def security_posture(req: WebAuditRequest, current_user: User = Depends(get_current_user)):
    try:
        return await cybersecurity_agent.security_posture(req.url)
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


# 2. Scan entire codebase
@router.post("/scan-codebase")
async def scan_codebase(req: CodebaseScanRequest):
    try:
        return await cybersecurity_agent.scan_codebase(req.directory)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# 3. Deep web application audit
@router.post("/deep-web-audit")
async def deep_web_audit(req: WebAuditRequest):
    try:
        return await cybersecurity_agent.deep_web_audit(req.url)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# 4. Exploit analysis for a specific vulnerability
@router.post("/analyze-exploit")
async def analyze_exploit(req: ExploitAnalysisRequest):
    try:
        return await cybersecurity_agent.analyze_exploit(req.code, req.vulnerability, req.filename)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# 5. Continuous security loop
@router.post("/security-loop")
async def security_loop(req: SecurityLoopRequest):
    try:
        return await cybersecurity_agent.security_loop(req.code, req.filename)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# 6. Site safety check
@router.post("/site-safety")
async def site_safety(req: SiteSafetyRequest):
    try:
        return await cybersecurity_agent.site_safety(req.url)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# 7. Security status
@router.get("/status")
async def status():
    from app.services.model_caller import ModelCaller
    return {
        "status": "active",
        "name": "Cybersecurity Agent",
        "description": "Mythos-level security analysis — reads code, finds vulnerabilities, traces exploits",
        "endpoints": [
            "POST /scan-code — Scan code with data flow tracing",
            "POST /scan-codebase — Audit entire codebase",
            "POST /deep-web-audit — Deep web application security audit",
            "POST /analyze-exploit — Exploit analysis for specific vulnerability",
            "POST /security-loop — Continuous threat modeling → discovery → verification → triage → patching",
            "POST /site-safety — Check if a site is safe for users",
        ],
        "capabilities": [
            "Autonomous vulnerability discovery",
            "Data flow tracing and reachability analysis",
            "CWE classification with confidence ratings",
            "Exploit scenario development",
            "Root cause analysis",
            "Patch generation with code diffs",
            "Continuous security loop",
            "Attack surface mapping",
            "Passive security posture checks",
            "Security-header and cookie control analysis",
            "Hard-coded secret detection before AI analysis",
            "SSRF-safe public-target validation",
            "Defensive-only analysis with no exploit payload execution",
        ],
        "model": ModelCaller.get_model_info(),
    }
