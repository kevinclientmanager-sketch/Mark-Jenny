from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from pydantic import BaseModel
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
