"""
GitHub Service — Repository management, push, PRs, and Vercel deployment.
Handles git operations, GitHub API calls, and deployment.
"""
import asyncio
import json
import os
import subprocess
import sys
from pathlib import Path
from typing import Optional, Dict, Any, List
from datetime import datetime

import httpx
from app.core.config import get_settings

settings = get_settings()

GITHUB_API = "https://api.github.com"


class GitHubService:
    def __init__(self):
        self.token: Optional[str] = None
        self._load_token()

    def _load_token(self):
        token_file = Path(os.environ.get("MARK_JENNY_DATA", ".")) / "credentials" / "github_token.json"
        if token_file.exists():
            with open(token_file) as f:
                self.token = json.load(f).get("token")

    def set_token(self, token: str):
        self.token = token
        token_file = Path(os.environ.get("MARK_JENNY_DATA", ".")) / "credentials" / "github_token.json"
        token_file.parent.mkdir(parents=True, exist_ok=True)
        with open(token_file, "w") as f:
            json.dump({"token": token}, f)

    def _headers(self) -> Dict:
        h = {"Accept": "application/vnd.github+json"}
        if self.token:
            h["Authorization"] = f"Bearer {self.token}"
        return h

    async def get_user(self) -> Dict:
        async with httpx.AsyncClient() as client:
            r = await client.get(f"{GITHUB_API}/user", headers=self._headers())
            return r.json()

    async def list_repos(self, per_page: int = 30) -> List[Dict]:
        async with httpx.AsyncClient() as client:
            r = await client.get(f"{GITHUB_API}/user/repos", headers=self._headers(), params={"per_page": per_page, "sort": "updated"})
            return r.json()

    async def create_repo(self, name: str, description: str = "", private: bool = False) -> Dict:
        async with httpx.AsyncClient() as client:
            r = await client.post(
                f"{GITHUB_API}/user/repos",
                headers=self._headers(),
                json={"name": name, "description": description, "private": private, "auto_init": True},
            )
            return r.json()

    async def get_repo(self, owner: str, repo: str) -> Dict:
        async with httpx.AsyncClient() as client:
            r = await client.get(f"{GITHUB_API}/repos/{owner}/{repo}", headers=self._headers())
            return r.json()

    async def list_issues(self, owner: str, repo: str, state: str = "open") -> List[Dict]:
        async with httpx.AsyncClient() as client:
            r = await client.get(f"{GITHUB_API}/repos/{owner}/{repo}/issues", headers=self._headers(), params={"state": state})
            return r.json()

    async def create_issue(self, owner: str, repo: str, title: str, body: str = "") -> Dict:
        async with httpx.AsyncClient() as client:
            r = await client.post(
                f"{GITHUB_API}/repos/{owner}/{repo}/issues",
                headers=self._headers(),
                json={"title": title, "body": body},
            )
            return r.json()

    async def create_pull_request(self, owner: str, repo: str, title: str, head: str, base: str = "main", body: str = "") -> Dict:
        async with httpx.AsyncClient() as client:
            r = await client.post(
                f"{GITHUB_API}/repos/{owner}/{repo}/pulls",
                headers=self._headers(),
                json={"title": title, "head": head, "base": base, "body": body},
            )
            return r.json()

    async def list_pulls(self, owner: str, repo: str, state: str = "open") -> List[Dict]:
        async with httpx.AsyncClient() as client:
            r = await client.get(f"{GITHUB_API}/repos/{owner}/{repo}/pulls", headers=self._headers(), params={"state": state})
            return r.json()

    async def get_file_contents(self, owner: str, repo: str, path: str, branch: str = "main") -> Optional[str]:
        async with httpx.AsyncClient() as client:
            r = await client.get(
                f"{GITHUB_API}/repos/{owner}/{repo}/contents/{path}",
                headers=self._headers(),
                params={"ref": branch},
            )
            if r.status_code == 200:
                import base64
                return base64.b64decode(r.json().get("content", "")).decode()
        return None

    async def push_to_repo(self, local_path: str, repo_url: str, branch: str = "main", message: str = "Update from Mark-Imti") -> Dict:
        """Git add, commit, and push a local directory to a GitHub repo."""
        path = Path(local_path)
        if not path.exists():
            return {"success": False, "error": "Path not found"}

        try:
            # Init git if needed
            if not (path / ".git").exists():
                proc = await asyncio.create_subprocess_exec(
                    "git", "init", cwd=str(path),
                    stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE,
                )
                await proc.wait()

            # Add remote
            proc = await asyncio.create_subprocess_exec(
                "git", "remote", "add", "origin", repo_url, cwd=str(path),
                stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE,
            )
            await proc.wait()

            # Configure user
            await asyncio.create_subprocess_exec(
                "git", "config", "user.email", "mark@markjenny.com", cwd=str(path),
                stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE,
            )
            await asyncio.create_subprocess_exec(
                "git", "config", "user.name", "Mark-Imti", cwd=str(path),
                stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE,
            )

            # Add all files
            proc = await asyncio.create_subprocess_exec(
                "git", "add", ".", cwd=str(path),
                stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE,
            )
            await proc.wait()

            # Commit
            proc = await asyncio.create_subprocess_exec(
                "git", "commit", "-m", message, cwd=str(path),
                stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE,
            )
            stdout, stderr = await proc.communicate()

            # Push
            proc = await asyncio.create_subprocess_exec(
                "git", "push", "-u", "origin", branch, cwd=str(path),
                stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE,
            )
            stdout, stderr = await proc.communicate()

            if proc.returncode == 0:
                return {"success": True, "message": f"Pushed to {repo_url}"}
            else:
                return {"success": False, "error": stderr.decode()}

        except Exception as e:
            return {"success": False, "error": str(e)}

    async def deploy_to_vercel(self, project_path: str, project_name: str = "") -> Dict:
        """Deploy a project to Vercel."""
        path = Path(project_path)
        if not path.exists():
            return {"success": False, "error": "Path not found"}

        # Check for vercel CLI
        try:
            proc = await asyncio.create_subprocess_exec(
                "vercel", "--version",
                stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE,
            )
            stdout, _ = await proc.communicate()
            if proc.returncode != 0:
                return {"success": False, "error": "Vercel CLI not installed. Run: npm i -g vercel"}
        except FileNotFoundError:
            return {"success": False, "error": "Vercel CLI not found. Run: npm i -g vercel"}

        # Deploy
        try:
            args = ["vercel", "--yes", "--prod"]
            if project_name:
                args.extend(["--name", project_name])

            proc = await asyncio.create_subprocess_exec(
                *args,
                cwd=str(path),
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
            stdout, stderr = await asyncio.wait_for(proc.communicate(), timeout=120)

            output = stdout.decode()
            url = ""
            for line in output.split("\n"):
                if "https://" in line:
                    url = line.strip()
                    break

            if url:
                return {"success": True, "url": url, "output": output}
            else:
                return {"success": False, "error": stderr.decode() or "Deploy failed", "output": output}

        except asyncio.TimeoutError:
            return {"success": False, "error": "Deploy timed out"}
        except Exception as e:
            return {"success": False, "error": str(e)}

    def get_stats(self) -> Dict:
        return {
            "authenticated": bool(self.token),
        }


# Singleton
github_service = GitHubService()
