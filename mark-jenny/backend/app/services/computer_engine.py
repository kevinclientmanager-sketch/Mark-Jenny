import os
import platform
import subprocess
import json
from pathlib import Path
from typing import List, Dict, Optional, Any
from datetime import datetime
try:
    import psutil
    PSUTIL_AVAILABLE = True
except ImportError:
    PSUTIL_AVAILABLE = False
    psutil = None

from app.core.config import get_settings

settings = get_settings()

IS_WINDOWS = platform.system() == "Windows"

class PermissionError(Exception):
    pass

class ComputerEngine:
    def __init__(self):
        self.allowed_roots = [Path(settings.UPLOAD_DIR).resolve(), Path.cwd().resolve()]
        self.permissions = {
            "file_read": True,
            "file_write": True,
            "process_list": True,
            "process_kill": False,  # dangerous - requires confirmation
            "clipboard_read": True,
            "clipboard_write": True,
            "shell_exec": False,  # dangerous
        }

    def check_permission(self, action: str, require_confirm: bool = False) -> Dict:
        allowed = self.permissions.get(action, False)
        if not allowed:
            return {"allowed": False, "requires_confirmation": True, "reason": f"{action} requires explicit enable in settings. Dangerous operations need confirmation."}
        if require_confirm and action in ["process_kill", "shell_exec", "file_write"]:
            return {"allowed": True, "requires_confirmation": True, "reason": "Dangerous - confirmation needed unless Level 4 autonomous"}
        return {"allowed": True, "requires_confirmation": False}

    # FileSystemController
    def list_files(self, path: str = ".", owner_id: Optional[int] = None) -> Dict:
        perm = self.check_permission("file_read")
        if not perm["allowed"]:
            return {"success": False, "error": perm["reason"]}
        try:
            p = Path(path).resolve()
            # restrict to allowed roots for safety
            if not any(str(p).startswith(str(r)) for r in self.allowed_roots):
                # allow listing uploads and cwd subdirs only
                if p != Path.cwd().resolve() and p.parent != Path.cwd().resolve():
                    return {"success": False, "error": f"Access denied outside allowed roots: {self.allowed_roots}"}
            if not p.exists():
                return {"success": False, "error": "Path not found"}
            items = []
            for child in sorted(p.iterdir())[:100]:
                items.append({
                    "name": child.name,
                    "path": str(child),
                    "is_dir": child.is_dir(),
                    "size": child.stat().st_size if child.is_file() else 0,
                    "modified": datetime.fromtimestamp(child.stat().st_mtime).isoformat()
                })
            return {"success": True, "path": str(p), "items": items, "count": len(items)}
        except Exception as e:
            return {"success": False, "error": str(e)}

    def read_file(self, path: str, max_bytes: int = 50000) -> Dict:
        perm = self.check_permission("file_read")
        if not perm["allowed"]:
            return {"success": False, "error": perm["reason"]}
        try:
            p = Path(path).resolve()
            if not any(str(p).startswith(str(r)) for r in self.allowed_roots):
                return {"success": False, "error": "Access denied"}
            if not p.is_file():
                return {"success": False, "error": "Not a file"}
            data = p.read_bytes()[:max_bytes]
            try:
                text = data.decode('utf-8')
                return {"success": True, "path": str(p), "content": text[:10000], "truncated": len(data) == max_bytes}
            except:
                return {"success": True, "path": str(p), "content_b64": data.hex()[:2000], "is_binary": True}
        except Exception as e:
            return {"success": False, "error": str(e)}

    def write_file(self, path: str, content: str, require_confirm: bool = True) -> Dict:
        perm = self.check_permission("file_write", require_confirm)
        if perm["requires_confirmation"]:
            return {"success": False, "requires_confirmation": True, "error": perm["reason"]}
        try:
            p = Path(path).resolve()
            if not any(str(p).startswith(str(r)) for r in self.allowed_roots):
                return {"success": False, "error": "Write denied outside allowed roots"}
            p.parent.mkdir(parents=True, exist_ok=True)
            p.write_text(content, encoding='utf-8')
            return {"success": True, "path": str(p), "bytes": len(content)}
        except Exception as e:
            return {"success": False, "error": str(e)}

    # ProcessManager
    def list_processes(self, limit: int = 50) -> Dict:
        if not PSUTIL_AVAILABLE:
            return {"success": False, "error": "psutil not installed - run: pip install psutil (fallback: tasklist)"}
        perm = self.check_permission("process_list")
        if not perm["allowed"]:
            return {"success": False, "error": perm["reason"]}
        try:
            procs = []
            for proc in psutil.process_iter(['pid','name','cpu_percent','memory_percent'])[:limit]:
                try:
                    procs.append(proc.info)
                except: pass
            return {"success": True, "processes": procs, "count": len(procs), "platform": platform.system()}
        except Exception as e:
            return {"success": False, "error": str(e)}

    def kill_process(self, pid: int, require_confirm: bool = True) -> Dict:
        perm = self.check_permission("process_kill", require_confirm)
        if perm["requires_confirmation"]:
            return {"success": False, "requires_confirmation": True, "error": perm["reason"]}
        try:
            psutil.Process(pid).terminate()
            return {"success": True, "pid": pid}
        except Exception as e:
            return {"success": False, "error": str(e)}

    # ClipboardController
    def clipboard_read(self) -> Dict:
        if not IS_WINDOWS:
            return {"success": False, "error": "Clipboard only on Windows (requires pywin32 or tkinter)"}
        perm = self.check_permission("clipboard_read")
        if not perm["allowed"]:
            return {"success": False, "error": perm["reason"]}
        try:
            import tkinter
            r = tkinter.Tk()
            r.withdraw()
            data = r.clipboard_get()
            r.destroy()
            return {"success": True, "content": data[:5000]}
        except Exception as e:
            return {"success": False, "error": f"Clipboard read failed: {e}"}

    def clipboard_write(self, text: str) -> Dict:
        if not IS_WINDOWS:
            return {"success": False, "error": "Clipboard only on Windows"}
        perm = self.check_permission("clipboard_write")
        if not perm["allowed"]:
            return {"success": False, "error": perm["reason"]}
        try:
            import tkinter
            r = tkinter.Tk()
            r.withdraw()
            r.clipboard_clear()
            r.clipboard_append(text)
            r.update()
            r.destroy()
            return {"success": True}
        except Exception as e:
            return {"success": False, "error": str(e)}

    # WindowManager (stub - requires pywin32)
    def list_windows(self) -> Dict:
        if not IS_WINDOWS:
            return {"success": False, "error": "WindowManager only on Windows"}
        try:
            # Fallback: list via tasklist
            result = subprocess.run(["tasklist", "/FO", "CSV", "/NH"], capture_output=True, text=True, timeout=5)
            return {"success": True, "windows": result.stdout[:3000].splitlines()[:20], "note": "Full WindowManager requires pywin32 - install for HWND control"}
        except Exception as e:
            return {"success": False, "error": str(e)}

    def get_system_info(self) -> Dict:
        return {
            "success": True,
            "platform": platform.system(),
            "release": platform.release(),
            "is_windows": IS_WINDOWS,
            "permissions": self.permissions,
            "allowed_roots": [str(p) for p in self.allowed_roots],
            "note": "Dangerous ops (kill/shell/file_write) require confirmation unless Autonomy L4"
        }

computer_engine = ComputerEngine()
