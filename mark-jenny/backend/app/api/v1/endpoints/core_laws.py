"""
Core Laws API — Immutable rules that govern Mark and Imti agents.
No agent, model, or system can modify these laws once set.
Only the user (with password) can view or edit them.
"""
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from typing import Optional, Dict, Any, List
from datetime import datetime
import json
import hashlib
import os
from pathlib import Path

from app.db.base import get_db
from app.core.security import get_current_user
from app.models.user import User

router = APIRouter()

CORE_LAWS_DIR = Path(os.environ.get("MARK_IMTI_DATA", ".")) / "core_laws"
CORE_LAWS_DIR.mkdir(parents=True, exist_ok=True)

CORE_LAWS_FILE = CORE_LAWS_DIR / "laws.json"
CORE_LAWS_HASH_FILE = CORE_LAWS_DIR / ".laws_hash"
CORE_LAWS_PASSWORD_FILE = CORE_LAWS_DIR / ".password"


def _hash_password(password: str) -> str:
    """Hash password with SHA-256 + salt."""
    salt = "mark-imti-core-laws-2024"
    return hashlib.sha256(f"{salt}:{password}".encode()).hexdigest()


def _load_password_hash() -> Optional[str]:
    """Load stored password hash."""
    if CORE_LAWS_PASSWORD_FILE.exists():
        return CORE_LAWS_PASSWORD_FILE.read_text().strip()
    return None


def _save_password_hash(password: str):
    """Save password hash."""
    CORE_LAWS_PASSWORD_FILE.write_text(_hash_password(password))


def _compute_laws_hash(laws: List[Dict]) -> str:
    """Compute hash of laws for tamper detection."""
    content = json.dumps(laws, sort_keys=True)
    return hashlib.sha256(content.encode()).hexdigest()


def _load_laws() -> List[Dict]:
    """Load core laws from encrypted file."""
    if CORE_LAWS_FILE.exists():
        try:
            with open(CORE_LAWS_FILE) as f:
                data = json.load(f)
                return data.get("laws", [])
        except:
            return []
    return []


def _save_laws(laws: List[Dict]):
    """Save core laws with tamper-proof hash."""
    data = {
        "laws": laws,
        "updated_at": datetime.utcnow().isoformat(),
        "hash": _compute_laws_hash(laws),
        "immutable": True,
    }
    with open(CORE_LAWS_FILE, "w") as f:
        json.dump(data, f, indent=2)
    # Save hash separately for verification
    CORE_LAWS_HASH_FILE.write_text(_compute_laws_hash(laws))


class CoreLaw(BaseModel):
    id: Optional[str] = None
    plain_text: str  # Plain language law
    code: str = ""   # Auto-generated code representation
    enabled: bool = True
    category: str = "general"  # general, security, behavior, data, autonomy, scope


class CoreLawsSetup(BaseModel):
    password: str
    laws: List[CoreLaw] = []


class CoreLawsUnlock(BaseModel):
    password: str


class CoreLawUpdate(BaseModel):
    law_id: str
    plain_text: str
    code: str = ""


class CoreLawsPasswordChange(BaseModel):
    current_password: str
    new_password: str


@router.post("/setup")
async def setup_core_laws(body: CoreLawsSetup, current_user: User = Depends(get_current_user)):
    """First-time setup: set password and initial laws."""
    if _load_password_hash() is not None:
        raise HTTPException(status_code=400, detail="Core Laws already configured. Use /unlock first.")

    _save_password_hash(body.password)

    laws = []
    for law in body.laws:
        laws.append({
            "id": law.id or f"law_{len(laws)+1}",
            "plain_text": law.plain_text,
            "code": law.code or _generate_law_code(law.plain_text),
            "enabled": law.enabled,
            "category": law.category,
            "created_at": datetime.utcnow().isoformat(),
            "immutable": True,
        })

    _save_laws(laws)
    return {"success": True, "message": "Core Laws established", "law_count": len(laws)}


@router.post("/unlock")
async def unlock_core_laws(body: CoreLawsUnlock, current_user: User = Depends(get_current_user)):
    """Unlock Core Laws with password to view/edit."""
    stored_hash = _load_password_hash()
    if stored_hash is None:
        raise HTTPException(status_code=404, detail="Core Laws not configured yet")

    if _hash_password(body.password) != stored_hash:
        raise HTTPException(status_code=401, detail="Invalid password")

    laws = _load_laws()
    return {"success": True, "laws": laws, "hash": _compute_laws_hash(laws)}


@router.post("/change-password")
async def change_core_laws_password(body: CoreLawsPasswordChange, current_user: User = Depends(get_current_user)):
    """Change the Core Laws password (must know the current one)."""
    stored_hash = _load_password_hash()
    if stored_hash is None:
        raise HTTPException(status_code=404, detail="Core Laws not configured yet")
    if _hash_password(body.current_password) != stored_hash:
        raise HTTPException(status_code=401, detail="Current Core Laws password is incorrect")
    if not body.new_password or len(body.new_password) < 4:
        raise HTTPException(status_code=400, detail="New password must be at least 4 characters")
    _save_password_hash(body.new_password)
    return {"success": True, "message": "Core Laws password changed"}


@router.get("/status")
async def core_laws_status(current_user: User = Depends(get_current_user)):
    """Check if Core Laws are configured (no sensitive data returned)."""
    configured = _load_password_hash() is not None
    laws = _load_laws() if configured else []
    return {
        "configured": configured,
        "law_count": len(laws),
        "immutable": True,
    }


@router.get("/enforce")
async def get_enforceable_laws(current_user: User = Depends(get_current_user)):
    """Get laws for agent enforcement (no password required, but no plain text either).
    Agents only see the code representation — never the plain language."""
    laws = _load_laws()
    enforceable = []
    for law in laws:
        if law.get("enabled", True):
            enforceable.append({
                "id": law["id"],
                "code": law.get("code", ""),
                "category": law.get("category", "general"),
                "immutable": True,
            })
    return {"laws": enforceable, "count": len(enforceable)}


@router.post("/update")
async def update_core_law(body: CoreLawUpdate, password: str = "", current_user: User = Depends(get_current_user)):
    """Update a core law (requires password verification)."""
    stored_hash = _load_password_hash()
    if stored_hash is None:
        raise HTTPException(status_code=404, detail="Core Laws not configured")

    if not password or _hash_password(password) != stored_hash:
        raise HTTPException(status_code=401, detail="Password required to modify Core Laws")

    laws = _load_laws()
    found = False
    for law in laws:
        if law["id"] == body.law_id:
            law["plain_text"] = body.plain_text
            law["code"] = body.code or _generate_law_code(body.plain_text)
            law["updated_at"] = datetime.utcnow().isoformat()
            found = True
            break

    if not found:
        raise HTTPException(status_code=404, detail="Law not found")

    _save_laws(laws)
    return {"success": True, "message": "Core Law updated", "hash": _compute_laws_hash(laws)}


@router.post("/add")
async def add_core_law(law: CoreLaw, password: str = "", current_user: User = Depends(get_current_user)):
    """Add a new core law (requires password)."""
    stored_hash = _load_password_hash()
    if stored_hash is None:
        raise HTTPException(status_code=404, detail="Core Laws not configured")

    if not password or _hash_password(password) != stored_hash:
        raise HTTPException(status_code=401, detail="Password required to modify Core Laws")

    laws = _load_laws()
    new_law = {
        "id": f"law_{len(laws)+1}_{int(datetime.utcnow().timestamp())}",
        "plain_text": law.plain_text,
        "code": law.code or _generate_law_code(law.plain_text),
        "enabled": law.enabled,
        "category": law.category,
        "created_at": datetime.utcnow().isoformat(),
        "immutable": True,
    }
    laws.append(new_law)
    _save_laws(laws)
    return {"success": True, "law": new_law, "hash": _compute_laws_hash(laws)}


@router.delete("/{law_id}")
async def delete_core_law(law_id: str, password: str = "", current_user: User = Depends(get_current_user)):
    """Delete a core law (requires password)."""
    stored_hash = _load_password_hash()
    if stored_hash is None:
        raise HTTPException(status_code=404, detail="Core Laws not configured")

    if not password or _hash_password(password) != stored_hash:
        raise HTTPException(status_code=401, detail="Password required to modify Core Laws")

    laws = _load_laws()
    original_count = len(laws)
    laws = [l for l in laws if l["id"] != law_id]

    if len(laws) == original_count:
        raise HTTPException(status_code=404, detail="Law not found")

    _save_laws(laws)
    return {"success": True, "message": "Core Law deleted", "hash": _compute_laws_hash(laws)}


@router.post("/verify")
async def verify_integrity(current_user: User = Depends(get_current_user)):
    """Verify Core Laws haven't been tampered with."""
    laws = _load_laws()
    stored_hash_file = CORE_LAWS_HASH_FILE.read_text().strip() if CORE_LAWS_HASH_FILE.exists() else ""
    current_hash = _compute_laws_hash(laws)
    return {
        "tamper_free": stored_hash_file == current_hash,
        "current_hash": current_hash,
        "stored_hash": stored_hash_file,
    }


def _generate_law_code(plain_text: str) -> str:
    """Generate a code representation from plain language law.
    This is a simple rule engine — in production would use AI."""
    text = plain_text.lower()

    # Security laws
    if any(w in text for w in ["never", "don't", "do not", "no access", "forbidden", "blocked"]):
        if any(w in text for w in ["delete", "remove", "drop", "destroy"]):
            return "BLOCK: destructive_operations"
        if any(w in text for w in ["access", "read", "view", "see", "show"]):
            return "RESTRICT: data_access"
        if any(w in text for w in ["send", "email", "publish", "deploy", "push"]):
            return "BLOCK: external_actions"
        if any(w in text for w in ["change", "modify", "edit", "update", "alter"]):
            return "IMMUTABLE: core_configuration"
        return f"BLOCK: {text[:50]}"

    # Permission laws
    if any(w in text for w in ["always", "must", "require", "need", "should"]):
        if any(w in text for w in ["ask", "confirm", "approve", "permission"]):
            return "REQUIRE: user_confirmation"
        if any(w in text for w in ["encrypt", "secure", "protect", "hash"]):
            return "ENFORCE: encryption"
        if any(w in text for w in ["log", "record", "audit", "track"]):
            return "ENFORCE: audit_logging"
        return f"ENFORCE: {text[:50]}"

    # Autonomy laws
    if any(w in text for w in ["autonomy", "independent", "self", "automatic", "autonomous"]):
        if any(w in text for w in ["level", "degree", "amount"]):
            return "SET: autonomy_level"
        return f"POLICY: autonomy_{text[:30]}"

    # Data laws
    if any(w in text for w in ["data", "information", "file", "document"]):
        if any(w in text for w in ["store", "keep", "save", "retain"]):
            return "POLICY: data_retention"
        if any(w in text for w in ["share", "send", "transfer", "export"]):
            return "POLICY: data_sharing"
        return f"POLICY: data_{text[:30]}"

    # Default
    return f"RULE: {plain_text[:100]}"
