from typing import Optional, List, Dict, Any
from sqlalchemy.orm import Session
import httpx
from app.models.agent import Model, ModelProvider, ModelCapability, ModelProviderConfig, Agent
from app.core.config import get_settings

settings = get_settings()

# Maps task types to required capabilities
TASK_TYPE_CAPABILITY_MAP = {
    "fast": [ModelCapability.CHAT],
    "deep_reasoning": [ModelCapability.REASONING],
    "coding": [ModelCapability.CODING],
    "research": [ModelCapability.CHAT, ModelCapability.REASONING],
    "vision": [ModelCapability.VISION],
    "image_generation": [ModelCapability.IMAGE_GENERATION],
    "audio": [ModelCapability.AUDIO],
    "video": [ModelCapability.VIDEO],
    "embeddings": [ModelCapability.EMBEDDINGS],
    "local": [],  # any local model
}

class ModelRegistry:
    def __init__(self, db: Session):
        self.db = db

    def list_models(self, is_active: Optional[bool] = True, is_local: Optional[bool] = None) -> List[Model]:
        q = self.db.query(Model)
        if is_active is not None:
            q = q.filter(Model.is_active == is_active)
        if is_local is not None:
            q = q.filter(Model.is_local == is_local)
        return q.all()

    def get_model(self, model_id: int) -> Optional[Model]:
        return self.db.query(Model).filter(Model.id == model_id).first()

    def get_by_provider(self, provider: ModelProvider) -> List[Model]:
        return self.db.query(Model).filter(Model.provider == provider, Model.is_active == True).all()

    def get_provider_config(self, user_id: int, provider: ModelProvider) -> Optional[ModelProviderConfig]:
        return self.db.query(ModelProviderConfig).filter(
            ModelProviderConfig.user_id == user_id,
            ModelProviderConfig.provider == provider
        ).first()

    def has_provider_config(self, user_id: int, provider: ModelProvider) -> bool:
        return self.get_provider_config(user_id, provider) is not None

    async def is_ollama_available(self) -> bool:
        try:
            async with httpx.AsyncClient(timeout=2) as client:
                r = await client.get(f"{settings.OLLAMA_BASE_URL}/api/tags")
                return r.status_code == 200
        except:
            return False

class ModelRouter:
    def __init__(self, db: Session, user_id: int):
        self.db = db
        self.user_id = user_id
        self.registry = ModelRegistry(db)

    def _score_model(self, model: Model, task_type: str, prefer_local: bool = False, prefer_cheap: bool = False) -> float:
        # Lower score is better
        score = 0.0
        caps = model.capabilities or []
        required = TASK_TYPE_CAPABILITY_MAP.get(task_type, [])
        # Capability match
        for req in required:
            if req.value not in caps and req not in caps:
                score += 100  # missing required capability
        # Cost factor
        cost = (model.cost_per_1k_input or 0) + (model.cost_per_1k_output or 0)
        if prefer_cheap:
            score += cost * 0.01
        else:
            score += cost * 0.001
        # Speed: local is faster for offline, but cloud is faster for large context
        if prefer_local and not model.is_local:
            score += 10
        if not prefer_local and model.is_local:
            # Check if Ollama actually has the model - for now assume ok
            score += 5
        # Context window bonus for research
        if task_type == "research" and model.context_window:
            score -= min(model.context_window / 100000, 5)
        return score

    async def select_model(
        self,
        task_type: str = "fast",
        prefer_local: Optional[bool] = None,
        prefer_cheap: bool = False,
        require_capabilities: Optional[List[str]] = None,
        fallback: bool = True
    ) -> Optional[Model]:
        """
        Selects best model for task_type. Implements hybrid local/cloud and fallback.
        task_type: fast|deep_reasoning|coding|research|vision|image_generation|audio|video|embeddings|local
        """
        # Determine prefer_local if not set: if Ollama available and task_type is local/fast, prefer local
        if prefer_local is None:
            if task_type == "local":
                prefer_local = True
            elif task_type in ["fast", "embeddings"]:
                # Check Ollama availability
                ollama_ok = await self.registry.is_ollama_available()
                prefer_local = ollama_ok
            else:
                prefer_local = False

        # Offline check: if no provider configs for cloud, force local
        has_cloud = any(
            self.registry.has_provider_config(self.user_id, p)
            for p in [ModelProvider.OPENAI, ModelProvider.ANTHROPIC, ModelProvider.GOOGLE, ModelProvider.AZURE]
        )
        if not has_cloud and not prefer_local:
            # No cloud config, try local
            local_models = self.registry.list_models(is_local=True)
            if local_models:
                prefer_local = True

        candidates = self.registry.list_models()
        # Filter by required capabilities if specified
        if require_capabilities:
            filtered = []
            for m in candidates:
                caps = [c.value if hasattr(c, 'value') else str(c) for c in (m.capabilities or [])]
                if all(req in caps or req.upper() in [x.upper() for x in caps] for req in require_capabilities):
                    filtered.append(m)
            if filtered:
                candidates = filtered

        # Filter by is_local if prefer_local and local models exist
        if prefer_local:
            local_cands = [m for m in candidates if m.is_local]
            if local_cands:
                candidates = local_cands
            elif fallback:
                # No local models, fallback to cloud
                pass
            else:
                return None

        # Filter to only models where provider is configured or is_local
        available = []
        for m in candidates:
            if m.is_local:
                # Check if Ollama has it (for now assume yes if available)
                if prefer_local and not await self.registry.is_ollama_available():
                    continue
                available.append(m)
            else:
                if self.registry.has_provider_config(self.user_id, m.provider):
                    available.append(m)
                elif fallback and m.provider == ModelProvider.OLLAMA:
                    # Ollama without config still ok if local
                    available.append(m)

        if not available and fallback:
            # Fallback: any active model
            available = candidates

        if not available:
            return None

        # Score and pick best
        scored = [(self._score_model(m, task_type, prefer_local, prefer_cheap), m) for m in available]
        scored.sort(key=lambda x: x[0])
        best = scored[0][1]

        # Check if best is actually available (for local, verify Ollama)
        if best.is_local and not await self.registry.is_ollama_available():
            if fallback and len(scored) > 1:
                # Try next best that is cloud
                for _, m in scored[1:]:
                    if not m.is_local and self.registry.has_provider_config(self.user_id, m.provider):
                        return m
            return None

        return best

    async def select_with_fallback_chain(self, task_type: str, fallback_chain: Optional[List[str]] = None) -> List[Model]:
        """
        Returns ordered fallback chain for a task_type. Used when primary fails.
        """
        primary = await self.select_model(task_type, fallback=False)
        chain = []
        if primary:
            chain.append(primary)
        # Add fallbacks for common types
        fallbacks = fallback_chain or ["fast", "deep_reasoning", "local"]
        for fb_type in fallbacks:
            if fb_type == task_type:
                continue
            m = await self.select_model(fb_type, fallback=False)
            if m and m not in chain:
                chain.append(m)
        # Finally any active
        if not chain:
            chain = self.registry.list_models()[:3]
        return chain

    PROVIDER_DEFAULT_URLS = {
        ModelProvider.OPENAI: "https://api.openai.com/v1",
        ModelProvider.ANTHROPIC: "https://api.anthropic.com",
        ModelProvider.GOOGLE: "https://generativelanguage.googleapis.com",
        ModelProvider.DEEPSEEK: "https://api.deepseek.com/v1",
        ModelProvider.MISTRAL: "https://api.mistral.ai/v1",
        ModelProvider.XAI: "https://api.x.ai/v1",
        ModelProvider.OPENROUTER: "https://openrouter.ai/api/v1",
        ModelProvider.OLLAMA: "http://localhost:11434",
    }

    PROVIDER_DEFAULT_MODELS = {
        ModelProvider.OPENAI: "gpt-4o-mini",
        ModelProvider.ANTHROPIC: "claude-3-5-sonnet-20241022",
        ModelProvider.GOOGLE: "gemini-2.0-flash",
        ModelProvider.DEEPSEEK: "deepseek-chat",
        ModelProvider.MISTRAL: "mistral-small-latest",
        ModelProvider.XAI: "grok-3-mini",
        ModelProvider.OPENROUTER: "openai/gpt-4o-mini",
        ModelProvider.OLLAMA: "llama3.1:8b",
        # Free-tier providers
        ModelProvider.GROQ: "llama-3.3-70b-versatile",
        ModelProvider.CEREBRAS: "llama-3.3-70b",
        ModelProvider.TOGETHER: "meta-llama/Llama-3.3-70B-Instruct-Turbo",
        ModelProvider.FIREWORKS: "accounts/fireworks/models/llama-v3p3-70b-instruct",
        ModelProvider.NVIDIA: "meta/llama-3.3-70b-instruct",
        ModelProvider.HUGGINGFACE: "meta-llama/Llama-3.3-70B-Instruct",
    }

    @staticmethod
    def _decrypt_key(enc: Optional[str]) -> str:
        """Decrypt a provider key. Handles fernet:, b64: and legacy bare base64."""
        if not enc:
            return ""
        try:
            if enc.startswith("fernet:"):
                from app.services.credential_vault import _decrypt
                return _decrypt(enc[len("fernet:"):])
            if enc.startswith("b64:"):
                import base64
                return base64.b64decode(enc[4:].encode()).decode()
            # Legacy values written before encryption was introduced.
            import base64
            try:
                return base64.b64decode(enc.encode()).decode()
            except Exception:
                return enc
        except Exception:
            return ""

    async def call_model(
        self,
        prompt: str,
        system: str = "",
        max_tokens: int = 1024,
        temperature: float = 0.3,
    ) -> str:
        """Call the user's configured cloud provider (saved in Settings). Default config first."""
        import httpx

        configs = self.db.query(ModelProviderConfig).filter(
            ModelProviderConfig.user_id == self.user_id
        ).all()
        # Default config first, then by provider priority
        order = {ModelProvider.OPENAI: 1, ModelProvider.ANTHROPIC: 2, ModelProvider.GOOGLE: 3,
                 ModelProvider.DEEPSEEK: 4, ModelProvider.MISTRAL: 5, ModelProvider.XAI: 6,
                 ModelProvider.OPENROUTER: 7, ModelProvider.CUSTOM: 8, ModelProvider.AZURE: 9,
                 ModelProvider.OLLAMA: 10}
        configs.sort(key=lambda c: (0 if c.is_default else 1, order.get(c.provider, 9)))

        for cfg in configs:
            key = self._decrypt_key(cfg.api_key_encrypted)
            if not key:
                continue
            try:
                conf = cfg.config or {}
                if cfg.provider == ModelProvider.ANTHROPIC:
                    model = conf.get("model") or self.PROVIDER_DEFAULT_MODELS[ModelProvider.ANTHROPIC]
                    async with httpx.AsyncClient(timeout=90) as client:
                        r = await client.post(
                            "https://api.anthropic.com/v1/messages",
                            headers={"x-api-key": key, "anthropic-version": "2023-06-01", "Content-Type": "application/json"},
                            json={"model": model, "max_tokens": max_tokens,
                                  "system": system or "You are a helpful assistant.",
                                  "messages": [{"role": "user", "content": prompt[:6000]}]},
                        )
                    if r.status_code == 200:
                        blocks = r.json().get("content", [])
                        text = "".join(b.get("text", "") for b in blocks if isinstance(b, dict))
                        if text.strip():
                            return text.strip()
                    continue
                if cfg.provider == ModelProvider.GOOGLE:
                    model = conf.get("model") or self.PROVIDER_DEFAULT_MODELS[ModelProvider.GOOGLE]
                    async with httpx.AsyncClient(timeout=90) as client:
                        r = await client.post(
                            f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent",
                            headers={"x-goog-api-key": key, "Content-Type": "application/json"},
                            json={"system_instruction": {"parts": [{"text": system or "You are a helpful assistant."}]},
                                  "contents": [{"parts": [{"text": prompt[:6000]}]}],
                                  "generationConfig": {"temperature": temperature, "maxOutputTokens": max_tokens}},
                        )
                    if r.status_code == 200:
                        cands = r.json().get("candidates", [])
                        parts = (cands[0].get("content", {}).get("parts", []) if cands else [])
                        text = "".join(p.get("text", "") for p in parts if isinstance(p, dict))
                        if text.strip():
                            return text.strip()
                    continue
                # Everything else via the OpenAI-compatible API. The base URL
                # comes from the discovered model row when available, so any
                # model the provider lists can be called - not just the handful
                # of hardcoded defaults.
                conf = conf or {}
                chosen = conf.get("model")
                api_base = ""
                if chosen:
                    try:
                        mrow = self.db.query(Model).filter(
                            Model.provider == cfg.provider, Model.model_id == chosen
                        ).first()
                        if mrow and isinstance(mrow.config, dict):
                            api_base = mrow.config.get("api_base") or ""
                    except Exception:
                        api_base = ""
                base = (api_base or conf.get("api_base") or cfg.base_url
                        or self.PROVIDER_DEFAULT_URLS.get(cfg.provider) or "").rstrip("/")
                if not base:
                    from app.services.model_discovery import PROVIDER_SPECS
                    base = (PROVIDER_SPECS.get(cfg.provider.value, {}).get("api_base") or "").rstrip("/")
                if not base:
                    continue
                endpoint = base if base.endswith("/chat/completions") else f"{base}/chat/completions"
                model = chosen or self.PROVIDER_DEFAULT_MODELS.get(cfg.provider) or "default"
                msgs = []
                if system:
                    msgs.append({"role": "system", "content": system})
                msgs.append({"role": "user", "content": prompt[:6000]})
                headers = {"Content-Type": "application/json", "Authorization": f"Bearer {key}"}
                body = {"model": model, "messages": msgs, "temperature": temperature, "max_tokens": max_tokens}
                if cfg.provider == ModelProvider.OPENROUTER:
                    # OpenRouter accepts optional routing hints and attribution.
                    headers["HTTP-Referer"] = "https://mark-imti.local"
                    headers["X-Title"] = "Mark-Imti"
                async with httpx.AsyncClient(timeout=180) as client:
                    r = await client.post(endpoint, headers=headers, json=body)
                if r.status_code == 200:
                    choices = r.json().get("choices", [])
                    content = choices[0].get("message", {}).get("content", "") if choices else ""
                    if isinstance(content, list):
                        content = "".join(p.get("text", "") for p in content if isinstance(p, dict))
                    if content and str(content).strip():
                        return str(content).strip()
            except Exception:
                continue
        return ""

    def get_model_for_agent(self, agent: Agent) -> Optional[Model]:
        if agent.model_id:
            m = self.registry.get_model(agent.model_id)
            if m and m.is_active:
                # Check provider config
                if m.is_local or self.registry.has_provider_config(self.user_id, m.provider):
                    return m
        # Fallback to router by agent type
        type_map = {
            "RESEARCH": "research",
            "CODING": "coding",
            "BROWSER": "vision",
            "DOCUMENT": "fast",
            "SPREADSHEET": "fast",
            "DESIGN": "image_generation",
            "DATA": "deep_reasoning",
            "QA": "fast",
        }
        task_type = type_map.get(agent.type.value if hasattr(agent.type, 'value') else str(agent.type), "fast")
        # This would be async in real, but we need sync fallback
        # For sync context, just pick first active of that capability
        cands = self.registry.list_models()
        for m in cands:
            caps = m.capabilities or []
            if task_type == "coding" and "CODING" in [c.value if hasattr(c,'value') else str(c) for c in caps]:
                return m
        return cands[0] if cands else None

# Helper to seed default models if empty
def DEFAULT_MODELS():  # noqa: N802 - kept for backwards compatibility
    from app.services.model_catalog_seed import default_models
    return default_models()


def ensure_default_models(db: Session):
    """Seed the multi-provider starter catalogue when the table is empty.

    Previously this inserted 5 models; the picker then had nothing to show for
    OpenAI/Anthropic/xAI/DeepSeek/Mistral or the free providers.
    """
    if db.query(Model).count() == 0:
        for m in DEFAULT_MODELS():
            db.add(m)
        db.commit()
