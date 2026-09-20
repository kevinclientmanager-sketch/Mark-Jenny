"""
Mark Imti Self-Builder — Extension Manager
Downloads, installs, and manages extensions, skills, models, and features.
The app can enhance itself without user intervention.
"""
import asyncio
import json
import os
import shutil
import zipfile
import tempfile
from pathlib import Path
from typing import Optional, Dict, Any, List
from datetime import datetime

from app.core.config import get_settings

settings = get_settings()

# Extension directories
EXTENSIONS_DIR = Path(os.environ.get("MARK_JENNY_DATA", ".")) / "extensions"
EXTENSIONS_DIR.mkdir(parents=True, exist_ok=True)

MODELS_DIR = Path(os.environ.get("MARK_JENNY_DATA", ".")) / "models"
MODELS_DIR.mkdir(parents=True, exist_ok=True)

# Extension registry
REGISTRY_URL = "https://raw.githubusercontent.com/markjenny/extensions/main/registry.json"

# Built-in extension types
EXTENSION_TYPES = {
    "skill": "AI Skills — specialized instructions for tasks",
    "plugin": "Plugins — add new capabilities to Mark Imti",
    "model": "Models — download and run AI models locally",
    "connector": "Connectors — integrate with external services",
    "theme": "Themes — customize Mark Imti's appearance",
    "agent": "Agents — specialist AI agents for specific domains",
}


class ExtensionManager:
    def __init__(self):
        self.installed: Dict[str, Dict] = {}
        self._load_manifest()

    def _manifest_path(self) -> Path:
        return EXTENSIONS_DIR / "manifest.json"

    def _load_manifest(self):
        path = self._manifest_path()
        if path.exists():
            with open(path) as f:
                self.installed = json.load(f).get("extensions", {})
        else:
            self.installed = {}

    def _save_manifest(self):
        with open(self._manifest_path(), "w") as f:
            json.dump({"extensions": self.installed, "updated_at": datetime.utcnow().isoformat()}, f, indent=2)

    def list_installed(self) -> List[Dict]:
        return [{"id": k, **v} for k, v in self.installed.items()]

    def get_extension(self, ext_id: str) -> Optional[Dict]:
        return self.installed.get(ext_id)

    async def install_from_url(self, url: str, ext_type: str = "skill") -> Dict[str, Any]:
        """Download and install extension from URL."""
        try:
            import httpx
            async with httpx.AsyncClient(timeout=60) as client:
                resp = await client.get(url)
                resp.raise_for_status()

            # Determine name from URL
            name = url.split("/")[-1].replace(".zip", "").replace(".py", "").replace(".md", "")
            ext_dir = EXTENSIONS_DIR / name
            ext_dir.mkdir(parents=True, exist_ok=True)

            # If it's a zip, extract it
            if url.endswith(".zip"):
                with tempfile.NamedTemporaryFile(suffix=".zip", delete=False) as tmp:
                    tmp.write(resp.content)
                    tmp_path = tmp.name
                with zipfile.ZipFile(tmp_path) as zf:
                    zf.extractall(ext_dir)
                os.unlink(tmp_path)
            else:
                # Save as single file
                ext_dir.mkdir(parents=True, exist_ok=True)
                (ext_dir / "index.py").write_text(resp.text)

            self.installed[name] = {
                "type": ext_type,
                "source": url,
                "installed_at": datetime.utcnow().isoformat(),
                "version": "1.0.0",
            }
            self._save_manifest()

            return {"success": True, "name": name, "type": ext_type}

        except Exception as e:
            return {"success": False, "error": str(e)}

    async def install_from_github(self, repo: str, path: str = "") -> Dict[str, Any]:
        """Install extension from a GitHub repo."""
        url = f"https://raw.githubusercontent.com/{repo}/main/{path}"
        return await self.install_from_url(url)

    async def install_skill(self, skill_data: Dict[str, str]) -> Dict[str, Any]:
        """Install a skill from content data."""
        name = skill_data.get("name", "unnamed_skill")
        ext_dir = EXTENSIONS_DIR / "skills" / name
        ext_dir.mkdir(parents=True, exist_ok=True)

        # Write SKILL.md
        if "content" in skill_data:
            (ext_dir / "SKILL.md").write_text(skill_data["content"])

        # Write any additional files
        for filename, content in skill_data.get("files", {}).items():
            (ext_dir / filename).write_text(content)

        self.installed[f"skill:{name}"] = {
            "type": "skill",
            "name": name,
            "installed_at": datetime.utcnow().isoformat(),
            "version": skill_data.get("version", "1.0.0"),
        }
        self._save_manifest()

        return {"success": True, "name": name, "path": str(ext_dir)}

    async def install_model(self, model_id: str, model_name: str = "") -> Dict[str, Any]:
        """Download and install an AI model."""
        from app.services.airllm_engine import airllm_engine

        if not airllm_engine.is_available():
            return {"success": False, "error": "AirLLM not installed. Run: pip install airllm"}

        result = airllm_engine.load_model(model_id)
        if result["success"]:
            self.installed[f"model:{model_id}"] = {
                "type": "model",
                "name": model_name or model_id,
                "installed_at": datetime.utcnow().isoformat(),
                "model_id": model_id,
            }
            self._save_manifest()

        return result

    async def uninstall(self, ext_id: str) -> Dict[str, Any]:
        """Uninstall an extension."""
        if ext_id not in self.installed:
            return {"success": False, "error": f"Extension {ext_id} not found"}

        ext = self.installed[ext_id]
        ext_type = ext.get("type", "")

        # Remove files
        if ext_type == "skill":
            name = ext.get("name", "")
            skill_dir = EXTENSIONS_DIR / "skills" / name
            if skill_dir.exists():
                shutil.rmtree(skill_dir)
        else:
            ext_dir = EXTENSIONS_DIR / ext_id.replace(":", "_")
            if ext_dir.exists():
                shutil.rmtree(ext_dir)

        del self.installed[ext_id]
        self._save_manifest()

        return {"success": True, "message": f"Extension {ext_id} uninstalled"}

    async def auto_discover(self) -> List[Dict]:
        """Auto-discover and suggest extensions from GitHub."""
        try:
            import httpx
            async with httpx.AsyncClient(timeout=30) as client:
                resp = await client.get(REGISTRY_URL)
                if resp.status_code == 200:
                    registry = resp.json()
                    suggestions = []
                    for ext in registry.get("extensions", []):
                        if ext["id"] not in self.installed:
                            suggestions.append(ext)
                    return suggestions
        except Exception:
            pass
        return []

    async def check_updates(self) -> List[Dict]:
        """Check for updates to installed extensions."""
        updates = []
        for ext_id, ext in self.installed.items():
            # In a real implementation, check version against remote
            pass
        return updates

    def get_stats(self) -> Dict[str, Any]:
        types = {}
        for ext in self.installed.values():
            t = ext.get("type", "unknown")
            types[t] = types.get(t, 0) + 1
        return {
            "total": len(self.installed),
            "by_type": types,
            "extensions_dir": str(EXTENSIONS_DIR),
        }


# Singleton
extension_manager = ExtensionManager()
