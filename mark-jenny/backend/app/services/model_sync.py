"""Syncs discovered provider models into the `models` table."""
from typing import Any, Dict, List, Optional

from sqlalchemy.orm import Session

from app.models.agent import Model, ModelProvider
from app.models.user import User
from app.services.model_discovery import PROVIDER_SPECS, fetch_provider_models


def _upsert(db: Session, provider: ModelProvider, item: Dict[str, Any]) -> bool:
    mid = item["model_id"]
    existing = db.query(Model).filter(
        Model.provider == provider, Model.model_id == mid
    ).first()

    caps = item.get("capabilities") or ["CHAT"]
    cfg = {
        "api_base": item.get("api_base"),
        "free": bool(item.get("free")),
        "discovered": True,
    }
    display = mid
    if existing:
        existing.display_name = existing.display_name or display
        existing.capabilities = caps
        if item.get("context_window"):
            existing.context_window = item["context_window"]
        if item.get("cost_per_1k_input") is not None:
            existing.cost_per_1k_input = item["cost_per_1k_input"]
        existing.is_active = True
        merged = dict(existing.config or {})
        merged.update(cfg)
        existing.config = merged
        return False

    db.add(Model(
        name=mid,
        display_name=display,
        provider=provider,
        model_id=mid,
        capabilities=caps,
        context_window=item.get("context_window"),
        max_output_tokens=None,
        cost_per_1k_input=item.get("cost_per_1k_input"),
        cost_per_1k_output=None,
        is_local=(provider == ModelProvider.OLLAMA),
        is_active=True,
        config=cfg,
    ))
    return True


async def discover_for_user(
    db: Session,
    user: User,
    provider: Optional[str] = None,
) -> Dict[str, Any]:
    """Discover models for one provider, or for every provider with a key."""
    from app.models.agent import ModelProviderConfig
    from app.services.model_router import ModelRouter

    router = ModelRouter(db, user.id)
    configs = db.query(ModelProviderConfig).filter(
        ModelProviderConfig.user_id == user.id
    ).all()
    if provider:
        wanted = provider.upper()
        configs = [c for c in configs if c.provider.value == wanted]
        if not configs:
            return {"synced": 0, "providers": {}, "errors": {wanted: "No saved credential for this provider."}}

    report: Dict[str, Any] = {"synced": 0, "providers": {}, "errors": {}}
    for cfg in configs:
        pname = cfg.provider.value
        key = router._decrypt_key(cfg.api_key_encrypted)
        base = (cfg.config or {}).get("api_base") or cfg.base_url
        models, err = await fetch_provider_models(pname, key=key, base_url=base)

        if err:
            # Local Ollama is often simply not running - that is not an error
            # worth shouting about.
            report["errors"][pname] = err
            if pname == "OLLAMA":
                continue
            # Mark the credential as needing attention so Settings shows it.
            try:
                cfg.config = {**(cfg.config or {}), "last_discovery_error": err}
                db.commit()
            except Exception:
                db.rollback()
            continue

        added = 0
        for item in models:
            try:
                if _upsert(db, cfg.provider, item):
                    added += 1
            except Exception:
                db.rollback()
                continue
        db.commit()
        report["synced"] += len(models)
        report["providers"][pname] = {"found": len(models), "added": added}
        try:
            cfg.config = {**(cfg.config or {}), "last_discovery_error": None,
                          "api_base": (cfg.config or {}).get("api_base")}
            db.commit()
        except Exception:
            db.rollback()

    return report
