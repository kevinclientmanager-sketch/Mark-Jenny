"""
Mark-Imti Model Caller — Provider-agnostic model interface
Tries Ollama -> OpenAI-compatible -> cloud APIs -> fallback
"""

import json
import os
import asyncio
import urllib.request
import urllib.error


class ModelCaller:
    """
    Provider-agnostic model caller.
    Tries multiple providers in order of preference.
    """

    def __init__(self, config: dict = None):
        self.config = config or {}
        self.ollama_url = self.config.get("ollama_url", "http://localhost:11434")
        self.openai_url = self.config.get("openai_url", "https://api.openai.com/v1")
        self.openai_key = self.config.get("openai_key", os.environ.get("OPENAI_API_KEY", ""))
        self.default_model = self.config.get("default_model", "qwen3-vl:8b")
        self.timeout = self.config.get("timeout", 120)

    async def complete(self, prompt: str, max_tokens: int = 4000,
                       temperature: float = 0.7, system: str = None) -> str:
        messages = []
        if system:
            messages.append({"role": "system", "content": system})
        messages.append({"role": "user", "content": prompt})

        result = await self._try_ollama(messages, max_tokens)
        if result is not None:
            return result

        result = await self._try_openai_compatible(messages, max_tokens, temperature)
        if result is not None:
            return result

        return "I apologize, but I'm unable to process this request at the moment. All available models are currently offline."

    async def _try_ollama(self, messages: list, max_tokens: int) -> str:
        try:
            data = json.dumps({
                "model": self.default_model,
                "messages": messages,
                "stream": False,
                "options": {"num_predict": max_tokens},
            }).encode()

            req = urllib.request.Request(
                f"{self.ollama_url}/api/chat",
                data=data,
                headers={"Content-Type": "application/json"},
                method="POST",
            )

            loop = asyncio.get_event_loop()
            response = await loop.run_in_executor(
                None, lambda: urllib.request.urlopen(req, timeout=self.timeout)
            )
            body = json.loads(response.read().decode())
            return body.get("message", {}).get("content", "")
        except Exception:
            return None

    async def _try_openai_compatible(self, messages: list, max_tokens: int,
                                      temperature: float) -> str:
        if not self.openai_key:
            return None
        try:
            data = json.dumps({
                "model": self.config.get("openai_model", "gpt-4o"),
                "messages": messages,
                "max_tokens": max_tokens,
                "temperature": temperature,
            }).encode()

            req = urllib.request.Request(
                f"{self.openai_url}/chat/completions",
                data=data,
                headers={
                    "Content-Type": "application/json",
                    "Authorization": f"Bearer {self.openai_key}",
                },
                method="POST",
            )

            loop = asyncio.get_event_loop()
            response = await loop.run_in_executor(
                None, lambda: urllib.request.urlopen(req, timeout=self.timeout)
            )
            body = json.loads(response.read().decode())
            return body["choices"][0]["message"]["content"]
        except Exception:
            return None
