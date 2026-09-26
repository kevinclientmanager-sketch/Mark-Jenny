"""Live model discovery.

Rather than shipping a hardcoded, inevitably-stale list of model IDs, this
module asks each provider what models the user's key can actually reach and
syncs the answer into the `models` table. That means newly released models
appear automatically, and every entry listed in the UI is one the user's own
key can really call.

Most providers expose an OpenAI-compatible `/v1/models` endpoint, so one code
path covers the long tail (Groq, Cerebras, Together, Fireworks, NVIDIA,
Hugging Face, OpenRouter, DeepSeek, Mistral, xAI, and any custom base URL).
"""
from typing import Any, Dict, List, Optional, Tuple

# provider -> spec
#   models_url : endpoint that lists models for the authenticated key
#   api_base   : OpenAI-compatible base to send chat/completions to
#   style      : "openai" | "x-api-key" | "googkey" | "ollama"
#   free       : provider has a usable free tier (no card required)
PROVIDER_SPECS: Dict[str, Dict[str, Any]] = {
    "OPENAI": {
        "models_url": "https://api.openai.com/v1/models",
        "api_base": "https://api.openai.com/v1",
        "style": "openai", "free": False,
        "label": "OpenAI", "signup": "https://platform.openai.com/api-keys",
        "note": "Paid after trial credit. No permanently free chat model.",
    },
    "ANTHROPIC": {
        "models_url": "https://api.anthropic.com/v1/models",
        "api_base": "https://api.anthropic.com/v1",
        "style": "x-api-key", "free": False,
        "label": "Anthropic", "signup": "https://console.anthropic.com/settings/keys",
        "note": "Paid. Requires prepaid credit.",
    },
    "GOOGLE": {
        "models_url": "https://generativelanguage.googleapis.com/v1beta/models",
        "api_base": "https://generativelanguage.googleapis.com/v1beta",
        "style": "googkey", "free": True,
        "label": "Google AI (Gemini)", "signup": "https://aistudio.google.com/apikey",
        "note": "FREE TIER - no card needed. Strong Gemini models incl. vision.",
    },
    "OPENROUTER": {
        "models_url": "https://openrouter.ai/api/v1/models",
        "api_base": "https://openrouter.ai/api/v1",
        "style": "openai", "free": True, "public_list": True,
        "label": "OpenRouter", "signup": "https://openrouter.ai/keys",
        "note": "FREE TIER - models ending in ':free' cost nothing.",
    },
    "GROQ": {
        "models_url": "https://api.groq.com/openai/v1/models",
        "api_base": "https://api.groq.com/openai/v1",
        "style": "openai", "free": True,
        "label": "Groq", "signup": "https://console.groq.com/keys",
        "note": "FREE TIER - very fast inference on open models.",
    },
    "CEREBRAS": {
        "models_url": "https://api.cerebras.ai/v1/models",
        "api_base": "https://api.cerebras.ai/v1",
        "style": "openai", "free": True,
        "label": "Cerebras", "signup": "https://cloud.cerebras.ai/",
        "note": "FREE TIER - fast open-weight models.",
    },
    "MISTRAL": {
        "models_url": "https://api.mistral.ai/v1/models",
        "api_base": "https://api.mistral.ai/v1",
        "style": "openai", "free": True,
        "label": "Mistral", "signup": "https://console.mistral.ai/api-keys",
        "note": "FREE TIER - experimental tier available.",
    },
    "DEEPSEEK": {
        "models_url": "https://api.deepseek.com/models",
        "api_base": "https://api.deepseek.com/v1",
        "style": "openai", "free": False,
        "label": "DeepSeek", "signup": "https://platform.deepseek.com/",
        "note": "Very cheap, strong coding models.",
    },
    "XAI": {
        "models_url": "https://api.x.ai/v1/models",
        "api_base": "https://api.x.ai/v1",
        "style": "openai", "free": False,
        "label": "xAI (Grok)", "signup": "https://console.x.ai/",
        "note": "Paid.",
    },
    "TOGETHER": {
        "models_url": "https://api.together.xyz/v1/models",
        "api_base": "https://api.together.xyz/v1",
        "style": "openai", "free": True,
        "label": "Together AI", "signup": "https://api.together.ai/settings/api-keys",
        "note": "FREE TIER credits on signup, open-weight catalogue.",
    },
    "FIREWORKS": {
        "models_url": "https://api.fireworks.ai/inference/v1/models",
        "api_base": "https://api.fireworks.ai/inference/v1",
        "style": "openai", "free": True,
        "label": "Fireworks AI", "signup": "https://fireworks.ai/api-keys",
        "note": "FREE TIER credits on signup.",
    },
    "NVIDIA": {
        "models_url": "https://integrate.api.nvidia.com/v1/models",
        "api_base": "https://integrate.api.nvidia.com/v1",
        "style": "openai", "free": True, "public_list": True,
        "label": "NVIDIA NIM", "signup": "https://build.nvidia.com/",
        "note": "FREE TIER - open models incl. Qwen, DeepSeek, Llama.",
    },
    "HUGGINGFACE": {
        "models_url": "https://router.huggingface.co/v1/models",
        "api_base": "https://router.huggingface.co/v1",
        "style": "openai", "free": True, "public_list": True,
        "label": "Hugging Face", "signup": "https://huggingface.co/settings/tokens",
        "note": "FREE TIER - thousands of community models via the OpenAI-compatible router.",
    },
    "CUSTOM": {
        "models_url": None, "api_base": None,
        "style": "openai", "free": False,
        "label": "Custom / self-hosted (LM Studio, vLLM, Ollama, any OpenAI-compatible)",
        "signup": "", "note": "Point at any OpenAI-compatible /v1 base URL.",
    },
}

# Local inference is discovered from the machine, not an account.
LOCAL_SPEC = {
    "models_url": "http://localhost:11434/api/tags",
    "api_base": "http://localhost:11434/v1",
    "style": "openai", "free": True,
    "label": "Ollama (local)", "signup": "", "note": "Runs on this machine - no key, no cost.",
}

_VISION_HINTS = ("vision", "vl", "-v-", "llava", "pixtral", "gemma-3", "qwen2.5-vl", "qwen3-vl", "clip")
_REASONING_HINTS = ("o1", "o3", "o4", "r1", "reason", "thinking", "thinking", "max", "pro")
_CODE_HINTS = ("codex", "coder", "codestral", "deepseek-coder", "qwen3-coder", "starcoder")
_IMAGE_HINTS = ("dall-e", "imagen", "flux", "sdxl", "stable-diffusion", "image", "seedream")
_AUDIO_HINTS = ("whisper", "tts", "speech", "audio", "nova-")


def _guess_capabilities(model_id: str) -> List[str]:
    mid = (model_id or "").lower()
    caps = ["CHAT"]
    if any(h in mid for h in _IMAGE_HINTS):
        return ["IMAGE_GENERATION"]
    if any(h in mid for h in _AUDIO_HINTS):
        caps.append("AUDIO")
    else:
        if any(h in mid for h in _REASONING_HINTS):
            caps.append("REASONING")
        if any(h in mid for h in _CODE_HINTS):
            caps.append("CODING")
        if any(h in mid for h in _VISION_HINTS):
            caps.append("VISION")
    return caps


def _is_free_model(model_id: str, provider: str) -> bool:
    """True only when this specific model costs $0 to call.

    A provider having *a* free tier (e.g. OpenRouter) does not make every model
    on it free - only ids explicitly marked free qualify.
    """
    mid = (model_id or "").lower()
    if ":free" in mid or mid.endswith("-free") or "/free" in mid:
        return True
    if provider == "OLLAMA":
        return True
    return False


def _headers(style: str, key: str) -> Dict[str, str]:
    if style == "x-api-key":
        return {"x-api-key": key, "anthropic-version": "2023-06-01"}
    if style == "googkey":
        return {"x-goog-api-key": key}
    return {"Authorization": f"Bearer {key}"}


def _parse_openai_list(payload: Any) -> List[Dict[str, Any]]:
    items = payload.get("data") if isinstance(payload, dict) else None
    if items is None and isinstance(payload, dict):
        items = payload.get("models") or payload.get("data")
    out: List[Dict[str, Any]] = []
    for it in items or []:
        if not isinstance(it, dict):
            continue
        mid = it.get("id") or it.get("name") or it.get("model")
        if not mid:
            continue
        out.append({"model_id": mid, "raw": it})
    return out


def _parse_google_list(payload: Any) -> List[Dict[str, Any]]:
    out = []
    for it in (payload or {}).get("models", []) or []:
        name = it.get("name", "")            # "models/gemini-3.5-flash"
        if not name:
            continue
        methods = it.get("supportedGenerationMethods") or []
        if methods and not any("generateContent" in m for m in methods):
            continue                          # skip embedding-only models
        ctx = it.get("inputTokenLimit")
        out.append({
            "model_id": name.split("/")[-1],
            "context_window": int(ctx) if ctx else None,
            "raw": it,
        })
    return out


async def fetch_provider_models(
    provider: str,
    key: str = "",
    base_url: Optional[str] = None,
) -> Tuple[List[Dict[str, Any]], Optional[str]]:
    """Return (models, error). Never raises; errors are reported to the caller."""
    import httpx

    provider = (provider or "").upper()
    if provider == "OLLAMA":
        spec = LOCAL_SPEC
    else:
        spec = PROVIDER_SPECS.get(provider)
    if not spec:
        return [], f"No discovery support for provider '{provider}'."

    style = spec["style"]
    models_url = spec["models_url"]
    if base_url:
        root = base_url.rstrip("/")
        models_url = f"{root}/models"
        if not root.endswith("/v1") and not root.endswith("/openai/v1"):
            models_url = f"{root}/v1/models"
        spec = {**spec, "api_base": root if root.endswith("/v1") else f"{root}/v1"}

    if provider == "OLLAMA":
        try:
            async with httpx.AsyncClient(timeout=10) as client:
                r = await client.get(models_url)
            if r.status_code != 200:
                return [], f"Ollama returned HTTP {r.status_code}"
            data = r.json().get("models", [])
            return ([{"model_id": m.get("name"), "context_window": None, "raw": m}
                     for m in data if m.get("name")], None)
        except Exception as exc:
            return [], f"Cannot reach local Ollama: {exc}"

    if not key and not spec.get("public_list"):
        return [], "No API key saved for this provider."
    if not models_url:
        return [], "This provider needs a base URL before models can be listed."

    url = models_url
    if style == "googkey":
        url = f"{models_url}?key={key}"

    try:
        async with httpx.AsyncClient(timeout=30) as client:
            r = await client.get(url, headers=_headers(style, key) if key else {})
    except Exception as exc:
        return [], f"Could not reach {provider}: {exc}"

    if r.status_code in (401, 403):
        return [], f"{provider} rejected the key (HTTP {r.status_code})."
    if r.status_code >= 400:
        return [], f"{provider} returned HTTP {r.status_code} for the model list."

    try:
        payload = r.json()
    except Exception:
        return [], f"{provider} returned a non-JSON model list."

    parsed = _parse_google_list(payload) if style == "googkey" else _parse_openai_list(payload)
    if not parsed:
        return [], f"{provider} returned no usable chat models."

    api_base = spec.get("api_base")
    out = []
    for item in parsed:
        mid = item["model_id"]
        raw = item.get("raw") or {}
        ctx = item.get("context_window")
        if not ctx:
            for k in ("context_length", "context_window", "max_context_length", "max_model_len"):
                if raw.get(k):
                    try:
                        ctx = int(raw[k])
                    except Exception:
                        ctx = None
                    break
        pricing_in = None
        pr = raw.get("pricing") or {}
        if isinstance(pr, dict) and pr.get("prompt") not in (None, ""):
            try:
                # OpenRouter quotes price per token; convert to cents per 1k.
                pricing_in = int(float(pr["prompt"]) * 1000 * 100)
            except Exception:
                pricing_in = None
        out.append({
            "model_id": mid,
            "context_window": ctx,
            "cost_per_1k_input": pricing_in,
            "capabilities": _guess_capabilities(mid),
            "free": _is_free_model(mid, provider),
            "api_base": api_base,
        })
    return out, None


def provider_catalog() -> List[Dict[str, Any]]:
    """Catalogue of providers offered in the UI.

    CUSTOM is intentionally excluded: a self-hosted base URL is an advanced
    power-user escape hatch, not something to present in a picker.
    """
    rows = []
    for key, spec in PROVIDER_SPECS.items():
        if key == "CUSTOM":
            continue
        rows.append({
            "provider": key,
            "label": spec["label"],
            "free_tier": bool(spec.get("free")),
            "api_base": spec.get("api_base"),
            "signup_url": spec.get("signup", ""),
            "note": spec.get("note", ""),
            "discovery": bool(spec.get("models_url")),
        })
    rows.append({
        "provider": "OLLAMA",
        "label": LOCAL_SPEC["label"],
        "free_tier": True,
        "api_base": LOCAL_SPEC["api_base"],
        "signup_url": "",
        "note": LOCAL_SPEC["note"],
        "discovery": True,
    })
    return rows
