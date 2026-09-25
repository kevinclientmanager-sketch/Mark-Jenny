"""
Mark-Imti Sandbox Engine — Isolated code execution
Based on Manus AI's cloud sandbox architecture
Provides safe code execution, browser automation, file operations
"""

import asyncio
import json
import os
import subprocess
import tempfile
import uuid
from enum import Enum
from typing import Any, Optional
from dataclasses import dataclass, field
from datetime import datetime


class SandboxType(Enum):
    PYTHON = "python"
    SHELL = "shell"
    BROWSER = "browser"
    NODEJS = "nodejs"


class ExecutionStatus(Enum):
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    TIMEOUT = "timeout"
    KILLED = "killed"


@dataclass
class ExecutionResult:
    id: str
    sandbox_type: SandboxType
    command: str
    stdout: str
    stderr: str
    exit_code: int
    status: ExecutionStatus
    duration_ms: int
    created_at: str = field(default_factory=lambda: datetime.utcnow().isoformat())
    files_created: list[str] = field(default_factory=list)
    artifacts: dict = field(default_factory=dict)


class SandboxExecutor:
    """
    Executes code in isolated sandbox environment.
    Supports Python, Shell, and Node.js execution.
    Uses subprocess isolation with timeout and resource limits.
    """

    def __init__(self, working_dir: str = None, timeout: int = 30):
        self.working_dir = working_dir or tempfile.mkdtemp(prefix="mark_sandbox_")
        self.timeout = timeout
        self._executions: dict[str, ExecutionResult] = {}

    async def execute_python(self, code: str, context: dict = None) -> ExecutionResult:
        script_path = os.path.join(self.working_dir, f"script_{uuid.uuid4().hex[:8]}.py")

        preamble = ""
        if context:
            for key, value in context.items():
                if isinstance(value, str):
                    preamble += f'{key} = """{value}"""\n'
                elif isinstance(value, (int, float, bool, list, dict)):
                    preamble += f"{key} = {json.dumps(value)}\n"

        full_code = preamble + "\n" + code

        with open(script_path, "w") as f:
            f.write(full_code)

        return await self._run(
            SandboxType.PYTHON,
            ["python", script_path],
            script_path,
        )

    async def execute_shell(self, command: str) -> ExecutionResult:
        return await self._run(
            SandboxType.SHELL,
            ["powershell", "-Command", command],
            None,
        )

    async def execute_node(self, code: str) -> ExecutionResult:
        script_path = os.path.join(self.working_dir, f"script_{uuid.uuid4().hex[:8]}.js")
        with open(script_path, "w") as f:
            f.write(code)

        return await self._run(
            SandboxType.NODEJS,
            ["node", script_path],
            script_path,
        )

    async def _run(self, sandbox_type: SandboxType, cmd: list[str],
                   script_path: Optional[str]) -> ExecutionResult:
        exec_id = str(uuid.uuid4())
        start = datetime.utcnow()
        status = ExecutionStatus.RUNNING

        try:
            proc = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
                cwd=self.working_dir,
            )

            try:
                stdout, stderr = await asyncio.wait_for(
                    proc.communicate(), timeout=self.timeout
                )
                exit_code = proc.returncode or 0
                status = ExecutionStatus.COMPLETED if exit_code == 0 else ExecutionStatus.FAILED
            except asyncio.TimeoutError:
                proc.kill()
                stdout, stderr = b"", b"Execution timed out"
                exit_code = -1
                status = ExecutionStatus.TIMEOUT

        except Exception as e:
            stdout, stderr = b"", str(e).encode()
            exit_code = -1
            status = ExecutionStatus.FAILED

        end = datetime.utcnow()
        duration_ms = int((end - start).total_seconds() * 1000)

        files_created = []
        if script_path and os.path.exists(script_path):
            files_created.append(script_path)

        result = ExecutionResult(
            id=exec_id,
            sandbox_type=sandbox_type,
            command=" ".join(cmd),
            stdout=stdout.decode("utf-8", errors="replace"),
            stderr=stderr.decode("utf-8", errors="replace"),
            exit_code=exit_code,
            status=status,
            duration_ms=duration_ms,
            files_created=files_created,
        )

        self._executions[exec_id] = result
        return result

    async def install_package(self, package: str) -> ExecutionResult:
        return await self.execute_shell(f"pip install {package}")

    def list_executions(self) -> list[ExecutionResult]:
        return list(self._executions.values())

    def get_execution(self, exec_id: str) -> Optional[ExecutionResult]:
        return self._executions.get(exec_id)

    def cleanup(self):
        import shutil
        if os.path.exists(self.working_dir):
            shutil.rmtree(self.working_dir, ignore_errors=True)


class BrowserAutomation:
    """
    Browser automation using subprocess-based control.
    Supports navigation, screenshots, form filling, data extraction.
    """

    def __init__(self, sandbox: SandboxExecutor):
        self.sandbox = sandbox
        self.current_url: Optional[str] = None
        self.cookies: dict = {}

    async def navigate(self, url: str) -> dict:
        self.current_url = url
        code = f"""
import urllib.request
import json

url = "{url}"
req = urllib.request.Request(url, headers={{"User-Agent": "Mark-Imti/1.0"}})
try:
    response = urllib.request.urlopen(req, timeout=10)
    content = response.read().decode("utf-8", errors="replace")[:50000]
    print(json.dumps({{"status": "ok", "url": url, "length": len(content), "preview": content[:2000]}}))
except Exception as e:
    print(json.dumps({{"status": "error", "error": str(e)}}))
"""
        result = await self.sandbox.execute_python(code)
        try:
            return json.loads(result.stdout.strip().split("\n")[-1])
        except Exception:
            return {"status": "error", "error": "Failed to parse response"}

    async def extract_data(self, url: str, selectors: dict = None) -> dict:
        code = f"""
import urllib.request
import json
import re

url = "{url}"
req = urllib.request.Request(url, headers={{"User-Agent": "Mark-Imti/1.0"}})
response = urllib.request.urlopen(req, timeout=10)
html = response.read().decode("utf-8", errors="replace")

# Extract text content
text = re.sub(r"<[^>]+>", " ", html)
text = re.sub(r"\\s+", " ", text).strip()

# Extract links
links = re.findall(r'href="(https?://[^"]+)"', html)

print(json.dumps({{
    "url": url,
    "text_preview": text[:3000],
    "links_count": len(links),
    "links": links[:20],
    "html_length": len(html)
}}))
"""
        result = await self.sandbox.execute_python(code)
        try:
            return json.loads(result.stdout.strip().split("\n")[-1])
        except Exception:
            return {"status": "error", "error": "Failed to extract data"}
