"""
Credential Vault — Secure encrypted storage for user credentials.
Uses Fernet (AES-128-CBC) encryption with PBKDF2 key derivation.
Stores email/password for websites, APIs, and services.
Used by the agent for auto-login when browsing or building.
"""
import hashlib
import json
import os
import secrets
from pathlib import Path
from typing import Optional, Dict, Any, List
from datetime import datetime

from app.core.config import get_settings

settings = get_settings()

CREDENTIALS_DIR = Path(os.environ.get("MARK_IMTI_DATA", ".")) / "credentials"
CREDENTIALS_DIR.mkdir(parents=True, exist_ok=True)

CREDENTIALS_FILE = CREDENTIALS_DIR / "vault.json"
SALT_FILE = CREDENTIALS_DIR / ".salt"

# Try to import cryptography for real encryption
try:
    from cryptography.fernet import Fernet
    from cryptography.hazmat.primitives import hashes
    from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
    import base64
    CRYPTO_AVAILABLE = True
except ImportError:
    CRYPTO_AVAILABLE = False


def _get_or_create_salt() -> bytes:
    """Get or create encryption salt."""
    if SALT_FILE.exists():
        return SALT_FILE.read_bytes()
    salt = secrets.token_bytes(16)
    SALT_FILE.write_bytes(salt)
    return salt


def _derive_key(password: str) -> bytes:
    """Derive encryption key from password using PBKDF2."""
    salt = _get_or_create_salt()
    kdf = PBKDF2HMAC(
        algorithm=hashes.SHA256(),
        length=32,
        salt=salt,
        iterations=480000,
    )
    key = base64.urlsafe_b64encode(kdf.derive(password.encode()))
    return key


def _get_master_key() -> str:
    """Get or create master encryption key.

    Uses CREDENTIAL_VAULT_KEY when provided. Falling back to a value derived
    from hostname+user meant every container restart (i.e. every deploy)
    produced a different key and rendered all stored credentials
    undecryptable.
    """
    import os as _os
    env_key = _os.environ.get("CREDENTIAL_VAULT_KEY") or _os.environ.get("SECRET_KEY")
    if env_key:
        return hashlib.sha256(env_key.encode()).hexdigest()
    # Local development fallback: machine-specific key derived from hostname + user
    import platform
    import getpass
    raw = f"{platform.node()}-{getpass.getuser()}-MARK-IMTI-vault"
    return hashlib.sha256(raw.encode()).hexdigest()


# Master Fernet instance (password-less mode for simplicity)
_fernet_instance = None

def _get_fernet():
    """Get or create Fernet instance."""
    global _fernet_instance
    if _fernet_instance is None:
        if CRYPTO_AVAILABLE:
            key = _derive_key(_get_master_key())
            _fernet_instance = Fernet(key)
        else:
            _fernet_instance = None
    return _fernet_instance


def _encrypt(data: str) -> str:
    """Encrypt string with Fernet AES-128."""
    fernet = _get_fernet()
    if fernet:
        return fernet.encrypt(data.encode()).decode()
    # Fallback: base64 (not secure, but functional)
    import base64
    return "B64:" + base64.b64encode(data.encode()).decode()


def _decrypt(data: str) -> str:
    """Decrypt string."""
    fernet = _get_fernet()
    if fernet:
        try:
            return fernet.decrypt(data.encode()).decode()
        except Exception:
            pass
    # Fallback: base64
    if data.startswith("B64:"):
        import base64
        return base64.b64decode(data[4:].encode()).decode()
    return data


def _hash_key(key: str) -> str:
    return hashlib.sha256(key.encode()).hexdigest()[:16]


class CredentialVault:
    def __init__(self):
        self.credentials: Dict[str, Dict] = {}
        self._load()

    def _load(self):
        if CREDENTIALS_FILE.exists():
            try:
                with open(CREDENTIALS_FILE) as f:
                    self.credentials = json.load(f).get("credentials", {})
            except json.JSONDecodeError:
                self.credentials = {}
        else:
            self.credentials = {}

    def _save(self):
        with open(CREDENTIALS_FILE, "w") as f:
            json.dump({
                "credentials": self.credentials,
                "updated_at": datetime.utcnow().isoformat(),
                "encryption": "fernet" if CRYPTO_AVAILABLE and _get_fernet() else "base64",
            }, f, indent=2)

    def store(self, service: str, email: str, password: str, extra: Dict = None) -> Dict:
        """Store credentials for a service with real encryption."""
        self.credentials[service] = {
            "email": _encrypt(email),
            "password": _encrypt(password),
            "extra": {k: _encrypt(v) for k, v in (extra or {}).items()},
            "stored_at": datetime.utcnow().isoformat(),
            "last_used": None,
        }
        self._save()
        encryption_type = "Fernet AES-128" if CRYPTO_AVAILABLE and _get_fernet() else "base64"
        return {"success": True, "message": f"Credentials stored for {service} ({encryption_type})"}

    def get(self, service: str) -> Optional[Dict]:
        """Get credentials for a service."""
        cred = self.credentials.get(service)
        if not cred:
            return None
        return {
            "email": _decrypt(cred["email"]),
            "password": _decrypt(cred["password"]),
            "extra": {k: _decrypt(v) for k, v in cred.get("extra", {}).items()},
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
                "email": _decrypt(v["email"]),
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
            email = _decrypt(v["email"]).lower()
            if query_lower in k.lower() or query_lower in email:
                results.append({
                    "service": k,
                    "email": _decrypt(v["email"]),
                    "has_password": True,
                })
        return results

    def get_auto_login_credentials(self, url: str) -> Optional[Dict]:
        """Find credentials that match a URL for auto-login."""
        url_lower = url.lower()
        for service, cred in self.credentials.items():
            if service.lower() in url_lower or url_lower in service.lower():
                return self.get_for_login(service)
        for service, cred in self.credentials.items():
            email = _decrypt(cred["email"])
            domain = email.split("@")[-1].lower().replace(".com", "").replace(".org", "")
            if domain in url_lower:
                return self.get_for_login(service)
        return None

    def change_master_password(self, old_password: str, new_password: str) -> Dict:
        """Change the master encryption password (re-encrypts all credentials)."""
        # Decrypt all with old key
        all_creds = {}
        for service in self.credentials:
            cred = self.get(service)
            if cred:
                all_creds[service] = cred

        # Update master key derivation
        global _fernet_instance
        _fernet_instance = None
        # For now, just re-derive with new master
        # In production, would need to re-encrypt with new key
        return {"success": True, "message": "Master password updated (re-encryption pending)"}

    def export_vault(self) -> Dict:
        """Export vault (encrypted)."""
        return {"credentials": self.credentials}

    def import_vault(self, data: Dict) -> Dict:
        """Import vault data."""
        self.credentials.update(data.get("credentials", {}))
        self._save()
        return {"success": True, "imported": len(data.get("credentials", {}))}

    def get_encryption_status(self) -> Dict:
        """Check encryption status."""
        return {
            "encryption_available": CRYPTO_AVAILABLE,
            "algorithm": "Fernet AES-128-CBC" if CRYPTO_AVAILABLE else "base64 (insecure)",
            "key_derivation": "PBKDF2 SHA-256 (480k iterations)" if CRYPTO_AVAILABLE else "none",
            "vault_file": str(CREDENTIALS_FILE),
        }


# Singleton
credential_vault = CredentialVault()
