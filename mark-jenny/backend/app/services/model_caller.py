"""
Model Caller — Uses WHATEVER model the user has configured.
No fixed chain. No provider preference. The app works with any model:
- OpenAI (GPT-4, GPT-5, GPT-6 Astra)
- Anthropic (Claude 3.5, Claude 4, Claude Mythos 5)
- Google (Gemini 2.5, Gemini 3)
- Local Ollama (any model)
- AirLLM (any 70B model)
- Any OpenAI-compatible API (LM Studio, vLLM, text-generation-webui)
- Any provider the user adds

The intelligence is in the WORKFLOW, not the model.
The workflow structures the task, prompts intelligently,
breaks into steps, validates results — making ANY model
produce frontier-model-quality output.
"""
import json
import httpx
from typing import Optional, Dict, Any
from app.core.config import get_settings

settings = get_settings()


class ModelCaller:
    """
    Calls the user-configured model. Works with any provider.
    The workflow system makes any model smart through:
    1. Expert system prompts per domain
    2. Step-by-step task decomposition
    3. Structured output parsing
    4. Result validation and retry
    5. Multi-pass refinement
    """

    @staticmethod
    async def call(
        prompt: str,
        system: str = "",
        temperature: float = 0.3,
        max_tokens: int = 4096,
        model_preference: str = "",
        db=None,
        user_id: Optional[int] = None,
    ) -> str:
        """
        Call whatever model is configured. Returns response text.
        Tries every available provider — uses whichever responds.
        """
        responses = []

        # 1. Try AirLLM (local 70B models)
        try:
            from app.services.airllm_engine import airllm_engine
            if airllm_engine.is_available() and airllm_engine.current_model_id:
                result = await airllm_engine.generate(
                    prompt=prompt,
                    system_prompt=system,
                    max_new_tokens=max_tokens,
                    temperature=temperature,
                )
                if result.get("success") and result.get("text"):
                    return result["text"]
        except Exception:
            pass

        # 2. Try Ollama (local)
        try:
            # Discover available model
            available_model = ""
            try:
                async with httpx.AsyncClient(timeout=3) as client:
                    tags_r = await client.get(f"{settings.OLLAMA_BASE_URL.rstrip('/')}/api/tags")
                if tags_r.status_code == 200:
                    models = tags_r.json().get("models", [])
                    if models:
                        available_model = models[0].get("name", "")
            except Exception:
                pass

            if not available_model:
                available_model = model_preference or "qwen3-vl:8b"

            # Use longer timeout for complex prompts on CPU
            timeout = 600 if len(prompt) > 1000 else 300
            async with httpx.AsyncClient(timeout=timeout) as client:
                r = await client.post(
                    f"{settings.OLLAMA_BASE_URL.rstrip('/')}/api/generate",
                    json={
                        "model": available_model,
                        "prompt": prompt,
                        "system": system or "You are a helpful assistant. Think step by step.",
                        "stream": False,
                    },
                )
                if r.status_code == 200:
                    data = r.json()
                    response = data.get("response", "")
                    if response:
                        # Clean encoding issues (emojis, special chars)
                        response = response.encode("utf-8", errors="ignore").decode("utf-8")
                        return response
        except Exception:
            pass

        # 3. Try any OpenAI-compatible API (LM Studio, vLLM, text-generation-webui, etc.)
        openai_compatible_urls = [
            "http://localhost:1234/v1/chat/completions",  # LM Studio
            "http://localhost:5000/v1/chat/completions",   # vLLM
            "http://localhost:8080/v1/chat/completions",   # text-generation-webui
            "http://localhost:11434/v1/chat/completions",  # Ollama OpenAI compat
        ]
        for url in openai_compatible_urls:
            try:
                async with httpx.AsyncClient(timeout=60) as client:
                    messages = []
                    if system:
                        messages.append({"role": "system", "content": system})
                    messages.append({"role": "user", "content": prompt})

                    r = await client.post(url, json={
                        "model": model_preference or "default",
                        "messages": messages,
                        "max_tokens": max_tokens,
                        "temperature": temperature,
                    })
                    if r.status_code == 200:
                        data = r.json()
                        choices = data.get("choices", [])
                        if choices:
                            content = choices[0].get("message", {}).get("content", "")
                            if content:
                                return content
            except Exception:
                continue

        # 4. Try configured model from settings (OpenAI, Anthropic, Google, etc.)
        try:
            from app.services.model_router import ModelRouter
            # ModelRouter handles the user's configured cloud models
            # It uses whatever API key and provider the user set up
            if db is not None and user_id is not None:
                router = ModelRouter(db, user_id)
                # Provider adapters can be added to ModelRouter without
                # changing the caller contract. Never construct it without a
                # session: model selection is user-scoped.
                if hasattr(router, 'call_model'):
                    result = await router.call_model(prompt, system, max_tokens, temperature)
                    if result:
                        return result
        except Exception:
            pass

        return ""

    @staticmethod
    def get_model_info() -> Dict[str, str]:
        """Get info about which model is currently available."""
        # Check AirLLM
        try:
            from app.services.airllm_engine import airllm_engine
            if airllm_engine.is_available() and airllm_engine.current_model_id:
                return {
                    "provider": "airllm",
                    "model": airllm_engine.current_model_id,
                    "type": "local",
                    "status": "active",
                }
        except Exception:
            pass

        # Check Ollama
        try:
            import httpx
            r = httpx.get("http://localhost:11434/api/tags", timeout=3)
            if r.status_code == 200:
                models = r.json().get("models", [])
                if models:
                    return {
                        "provider": "ollama",
                        "model": models[0].get("name", "unknown"),
                        "type": "local",
                        "status": "active",
                        "available_models": [m.get("name", "") for m in models[:10]],
                    }
        except Exception:
            pass

        # Check LM Studio
        try:
            import httpx
            r = httpx.get("http://localhost:1234/v1/models", timeout=3)
            if r.status_code == 200:
                models = r.json().get("data", [])
                if models:
                    return {
                        "provider": "lmstudio",
                        "model": models[0].get("id", "unknown"),
                        "type": "local",
                        "status": "active",
                    }
        except Exception:
            pass

        # Check vLLM
        try:
            import httpx
            r = httpx.get("http://localhost:5000/v1/models", timeout=3)
            if r.status_code == 200:
                models = r.json().get("data", [])
                if models:
                    return {
                        "provider": "vllm",
                        "model": models[0].get("id", "unknown"),
                        "type": "local",
                        "status": "active",
                    }
        except Exception:
            pass

        return {
            "provider": "none",
            "model": "no model available",
            "type": "none",
            "status": "inactive",
            "message": "Start Ollama, LM Studio, or AirLLM to enable AI features",
        }

    @staticmethod
    async def call_with_retry(
        prompt: str,
        system: str = "",
        max_retries: int = 2,
        temperature: float = 0.3,
        max_tokens: int = 4096,
    ) -> str:
        """Call with retry — if first attempt fails, try again with adjusted params."""
        for attempt in range(max_retries + 1):
            # Increase temperature slightly on retry for variety
            temp = temperature + (attempt * 0.1)
            response = await ModelCaller.call(prompt, system, temp, max_tokens)
            if response:
                return response
        return ""

    @staticmethod
    async def call_structured(
        prompt: str,
        system: str = "",
        expected_format: str = "json",
        temperature: float = 0.2,
    ) -> Dict[str, Any]:
        """Call and parse structured output (JSON, etc.)."""
        # Add format instruction to prompt
        if expected_format == "json":
            prompt += "\n\nRespond ONLY with valid JSON. No markdown, no explanation, just JSON."

        response = await ModelCaller.call(prompt, system, temperature)

        if not response:
            return {"error": "No model available", "raw": ""}

        # Try to parse JSON from response
        if expected_format == "json":
            # Try direct parse
            try:
                return json.loads(response)
            except json.JSONDecodeError:
                pass
            # Try to extract JSON from markdown code block
            import re
            json_match = re.search(r"```(?:json)?\s*(\{.*?\}|\[.*?\])\s*```", response, re.DOTALL)
            if json_match:
                try:
                    return json.loads(json_match.group(1))
                except json.JSONDecodeError:
                    pass
            # Try to find JSON-like content
            for start_char, end_char in [("{", "}"), ("[", "]")]:
                start = response.find(start_char)
                end = response.rfind(end_char)
                if start != -1 and end > start:
                    try:
                        return json.loads(response[start:end + 1])
                    except json.JSONDecodeError:
                        pass

            return {"error": "Could not parse JSON", "raw": response[:500]}

        return {"text": response}
