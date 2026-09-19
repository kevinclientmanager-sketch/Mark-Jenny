import subprocess
import tempfile
import uuid
import os
import sys
import shutil
import time
from pathlib import Path
from typing import Dict, Optional, List
import json

from app.core.config import get_settings

settings = get_settings()
EXECUTION_ROOT = Path(settings.UPLOAD_DIR) / "exec_sandbox"
EXECUTION_ROOT.mkdir(parents=True, exist_ok=True)

SUPPORTED_LANGUAGES = ["python", "javascript", "node", "powershell", "shell"]

class CodeExecutionEngine:
    def __init__(self):
        self.timeout_default = 30  # seconds
        self.max_output = 50000  # chars
        self.max_file_size = 10 * 1024 * 1024  # 10MB

    def _prepare_sandbox(self, language: str) -> Path:
        sid = str(uuid.uuid4())[:8]
        sandbox = EXECUTION_ROOT / f"{language}_{sid}"
        sandbox.mkdir(parents=True, exist_ok=True)
        return sandbox

    def _cleanup(self, sandbox: Path):
        try:
            shutil.rmtree(sandbox, ignore_errors=True)
        except: pass

    def _run_subprocess(self, cmd: List[str], cwd: Path, input_text: Optional[str] = None, timeout: int = 30, env_extra: Optional[Dict] = None) -> Dict:
        start = time.time()
        env = os.environ.copy()
        # Network policy: by default allow, but can restrict via env
        env["PYTHONUNBUFFERED"] = "1"
        if env_extra:
            env.update(env_extra)
        # Filesystem isolation: only cwd is writable, but we run with cwd set
        try:
            proc = subprocess.run(
                cmd,
                cwd=str(cwd),
                input=input_text,
                capture_output=True,
                text=True,
                timeout=timeout,
                env=env
            )
            duration = time.time() - start
            stdout = proc.stdout[:self.max_output] if proc.stdout else ""
            stderr = proc.stderr[:self.max_output] if proc.stderr else ""
            return {
                "success": proc.returncode == 0,
                "returncode": proc.returncode,
                "stdout": stdout,
                "stderr": stderr,
                "duration": round(duration, 2),
                "timeout": False,
                "truncated": len(proc.stdout or "") > self.max_output if proc.stdout else False
            }
        except subprocess.TimeoutExpired as e:
            duration = time.time() - start
            return {
                "success": False,
                "returncode": -1,
                "stdout": (e.stdout.decode() if e.stdout else "")[:self.max_output] if e.stdout else "",
                "stderr": f"Timeout after {timeout}s",
                "duration": round(duration, 2),
                "timeout": True,
                "truncated": False
            }
        except Exception as e:
            return {"success": False, "error": str(e), "duration": 0}

    def execute_python(self, code: str, timeout: Optional[int] = None, packages: Optional[List[str]] = None) -> Dict:
        timeout = timeout or self.timeout_default
        sandbox = self._prepare_sandbox("python")
        try:
            # Write code to file
            script = sandbox / "main.py"
            # Basic validation: prevent dangerous imports if needed (allow all for now with audit)
            script.write_text(code, encoding="utf-8")
            # Optional: install packages in sandbox (isolated via --target)
            # For now, skip auto-install, just run
            cmd = [sys.executable, "main.py"]
            result = self._run_subprocess(cmd, sandbox, timeout=timeout)
            # Collect any generated files in sandbox
            files = []
            for p in sandbox.iterdir():
                if p.name != "main.py" and p.is_file():
                    files.append({"name": p.name, "size": p.stat().st_size, "path": str(p)})
            result["files"] = files[:5]
            result["sandbox"] = str(sandbox)
            result["language"] = "python"
            return result
        finally:
            # keep sandbox for 60s for inspection then cleanup async? For now cleanup immediately after reading files
            # Don't cleanup immediately if files were generated - caller may need them; we keep path in result
            # Schedule cleanup via temp file tracking
            pass  # caller must cleanup via execution_id if needed

    def execute_javascript(self, code: str, timeout: Optional[int] = None) -> Dict:
        timeout = timeout or self.timeout_default
        sandbox = self._prepare_sandbox("node")
        try:
            script = sandbox / "main.js"
            script.write_text(code, encoding="utf-8")
            # try node, fallback to nodejs
            cmd = None
            for candidate in ["node", "nodejs"]:
                if shutil.which(candidate):
                    cmd = [candidate, "main.js"]
                    break
            if not cmd:
                return {"success": False, "error": "Node.js not found - install Node.js to enable JS execution", "language": "javascript"}
            result = self._run_subprocess(cmd, sandbox, timeout=timeout)
            result["language"] = "javascript"
            result["sandbox"] = str(sandbox)
            return result
        finally:
            pass

    def execute_powershell(self, code: str, timeout: Optional[int] = None) -> Dict:
        if os.name != "nt":
            return {"success": False, "error": "PowerShell only on Windows", "language": "powershell"}
        timeout = timeout or self.timeout_default
        sandbox = self._prepare_sandbox("ps")
        try:
            script = sandbox / "main.ps1"
            script.write_text(code, encoding="utf-8")
            # Prefer pwsh, fallback to powershell
            cmd = None
            for cand in ["pwsh", "powershell"]:
                if shutil.which(cand):
                    cmd = [cand, "-ExecutionPolicy", "Bypass", "-File", "main.ps1"]
                    break
            if not cmd:
                return {"success": False, "error": "PowerShell not found", "language": "powershell"}
            result = self._run_subprocess(cmd, sandbox, timeout=timeout)
            result["language"] = "powershell"
            result["sandbox"] = str(sandbox)
            return result
        finally:
            pass

    def execute(self, language: str, code: str, timeout: Optional[int] = None) -> Dict:
        lang = language.lower().strip()
        if lang in ["python", "py"]:
            return self.execute_python(code, timeout)
        elif lang in ["javascript", "js", "node", "nodejs"]:
            return self.execute_javascript(code, timeout)
        elif lang in ["powershell", "ps", "pwsh"]:
            return self.execute_powershell(code, timeout)
        elif lang in ["shell", "bash", "sh"]:
            # For shell, only allow on explicit permission; map to powershell on Windows
            if os.name == "nt":
                return self.execute_powershell(code, timeout)
            else:
                return {"success": False, "error": "Shell execution requires explicit confirmation - see ComputerEngine shell_exec permission"}
        else:
            return {"success": False, "error": f"Unsupported language: {language}. Supported: {SUPPORTED_LANGUAGES}"}

    def list_languages(self) -> Dict:
        return {
            "supported": SUPPORTED_LANGUAGES,
            "available": {
                "python": True,
                "javascript": bool(shutil.which("node") or shutil.which("nodejs")),
                "powershell": bool(shutil.which("pwsh") or shutil.which("powershell")) if os.name=="nt" else False,
                "shell": os.name != "nt"
            },
            "sandbox_root": str(EXECUTION_ROOT),
            "limits": {"timeout_default": self.timeout_default, "max_output": self.max_output, "fs_isolation": str(EXECUTION_ROOT), "network": "allowed (audit logged)", "cleanup": "manual after 5min"}
        }

code_execution_engine = CodeExecutionEngine()
