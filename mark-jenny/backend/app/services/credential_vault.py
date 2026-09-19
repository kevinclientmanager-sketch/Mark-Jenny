"""
Credential Vault — Secure storage for user credentials.
Stores email/password for websites, APIs, and services.
Used by the agent for auto-login when browsing or building.
"""
import base64
import hashlib
import json
import os
from pathlib import Path
from typing import Optional, Dict, Any, List
from datetime import datetime

from app.core.config import get_settings

settings = get_settings()

CREDENTIALS_DIR = Path(os.environ.get("MARK_JENNY_DATA", ".")) / "credentials"
CREDENTIALS_DIR.mkdir(parents=True, exist_ok=True)

CREDENTIALS_FILE = CREDENTIALS_DIR / "vault.json"


def _obfuscate(data: str) -> str:
    """Simple obfuscation (not real encryption — use Fernet in production)."""
    return base64.b64encode(data.encode()).decode()

def _deobfuscate(data: str) -> str:
    return base64.b64decode(data.encode()).decode()

def _hash_key(key: str) -> str:
    return hashlib.sha256(key.encode()).hexdigest()[:16]


class CredentialVault:
    def __init__(self):
        self.credentials: Dict[str, Dict] = {}
        self._load()

    def _load(self):
        if CREDENTIALS_FILE.exists():
            with open(CREDENTIALS_FILE) as f:
                self.credentials = json.load(f).get("credentials", {})
        else:
            self.credentials = {}

    def _save(self):
        with open(CREDENTIALS_FILE, "w") as f:
            json.dump({"credentials": self.credentials, "updated_at": datetime.utcnow().isoformat()}, f, indent=2)

    def store(self, service: str, email: str, password: str, extra: Dict = None) -> Dict:
        """Store credentials for a service (email, password, etc)."""
        self.credentials[service] = {
            "email": _obfuscate(email),
            "password": _obfuscate(password),
            "extra": {k: _obfuscate(v) for k, v in (extra or {}).items()},
            "stored_at": datetime.utcnow().isoformat(),
            "last_used": None,
        }
        self._save()
        return {"success": True, "message": f"Credentials stored for {service}"}

    def get(self, service: str) -> Optional[Dict]:
        """Get credentials for a service."""
        cred = self.credentials.get(service)
        if not cred:
            return None
        return {
            "email": _deobfuscate(cred["email"]),
            "password": _deobfuscate(cred["password"]),
            "extra": {k: _deobfuscate(v) for k, v in cred.get("extra", {}).items()},
            "stored_at": cred["stored_at"],
        }

    def get_for_login(self, service: str) -> Optional[Dict]:
        """Get credentials and mark as used."""
        cred = self.get(service)
        if cred:
            self.credentials[service]["last_used"] = datetime.utcnow().isoformat()
            self._save()
        return cred

    def list_services(self) -> List[Dict]:
        """List all stored services (without exposing passwords)."""
        return [
            {
                "service": k,
                "email": _deobfuscate(v["email"]),
                "has_password": bool(v.get("password")),
                "stored_at": v["stored_at"],
                "last_used": v.get("last_used"),
            }
            for k, v in self.credentials.items()
        ]

    def delete(self, service: str) -> Dict:
        if service not in self.credentials:
            return {"success": False, "error": f"No credentials for {service}"}
        del self.credentials[service]
        self._save()
        return {"success": True, "message": f"Credentials for {service} deleted"}

    def search(self, query: str) -> List[Dict]:
        """Search services by name or email."""
        results = []
        query_lower = query.lower()
        for k, v in self.credentials.items():
            email = _deobfuscate(v["email"]).lower()
            if query_lower in k.lower() or query_lower in email:
                results.append({
                    "service": k,
                    "email": _deobfuscate(v["email"]),
                    "has_password": True,
                })
        return results

    def get_auto_login_credentials(self, url: str) -> Optional[Dict]:
        """Find credentials that match a URL for auto-login."""
        url_lower = url.lower()
        for service, cred in self.credentials.items():
            if service.lower() in url_lower or url_lower in service.lower():
                return self.get_for_login(service)
        # Check email domains
        for service, cred in self.credentials.items():
            email = _deobfuscate(cred["email"])
            domain = email.split("@")[-1].lower().replace(".com", "").replace(".org", "")
            if domain in url_lower:
                return self.get_for_login(service)
        return None

    def export_vault(self) -> Dict:
        """Export vault (encrypted)."""
        return {"credentials": self.credentials}

    def import_vault(self, data: Dict) -> Dict:
        """Import vault data."""
        self.credentials.update(data.get("credentials", {}))
        self._save()
        return {"success": True, "imported": len(data.get("credentials", {}))}


# Singleton
credential_vault = CredentialVault()
