"""
AirLLM Engine — layer-by-layer 70B model inference on 4GB GPU.
Uses airllm library for memory-efficient large model inference without quantization.
Supports: Llama2/3, Mixtral, Falcon, Qwen2, Phi-3, Mistral, DeepSeek, Yi, Gemma, GPT-2/NeoX.
"""
import asyncio
import json
import os
import threading
import time
from pathlib import Path
from typing import Optional, Dict, Any, List
from datetime import datetime

from app.core.config import get_settings

settings = get_settings()

# Try to import airllm
try:
    from airllm import AutoModel, AutoTokenizer
    AIRLLM_AVAILABLE = True
except ImportError:
    AIRLLM_AVAILABLE = False
    AutoModel = None
    AutoTokenizer = None

AIRLLM_CACHE_DIR = Path(settings.UPLOAD_DIR) / "airllm_models"
AIRLLM_CACHE_DIR.mkdir(parents=True, exist_ok=True)

# Supported models with metadata
SUPPORTED_MODELS = [
    {
        "id": "meta-llama/Meta-Llama-3.1-8B-Instruct",
        "name": "Llama 3.1 8B Instruct",
        "family": "llama3",
        "size_gb": 16,
        "min_gpu_gb": 4,
        "desc": "Meta's latest 8B instruction-tuned model — fast, efficient",
        "recommended": True,
    },
    {
        "id": "meta-llama/Meta-Llama-3.1-70B-Instruct",
        "name": "Llama 3.1 70B Instruct",
        "family": "llama3",
        "size_gb": 140,
        "min_gpu_gb": 4,
        "desc": "Full 70B model — runs layer-by-layer on 4GB GPU via AirLLM",
        "recommended": True,
    },
    {
        "id": "mistralai/Mixtral-8x22B-Instruct-v0.1",
        "name": "Mixtral 8x22B Instruct",
        "family": "mixtral",
        "size_gb": 130,
        "min_gpu_gb": 4,
        "desc": "Mistral's MoE model — 141B parameters, 39B active",
    },
    {
        "id": "Qwen/Qwen2.5-72B-Instruct",
        "name": "Qwen 2.5 72B Instruct",
        "family": "qwen2",
        "size_gb": 144,
        "min_gpu_gb": 4,
        "desc": "Alibaba's top open model — 72B parameters",
    },
    {
        "id": "tiiuae/falcon-180B-Chat",
        "name": "Falcon 180B Chat",
        "family": "falcon",
        "size_gb": 360,
        "min_gpu_gb": 4,
        "desc": "Technology Innovation Institute's massive 180B chat model",
    },
    {
        "id": "microsoft/Phi-3-medium-4k-instruct",
        "name": "Phi-3 Medium 4K",
        "family": "phi3",
        "size_gb": 32,
        "min_gpu_gb": 4,
        "desc": "Microsoft's 14B parameter model — strong reasoning at small size",
    },
    {
        "id": "01-ai/Yi-1.5-34B-Chat",
        "name": "Yi 1.5 34B Chat",
        "family": "yi",
        "size_gb": 68,
        "min_gpu_gb": 4,
        "desc": "01.AI's 34B bilingual model — strong multilingual support",
    },
    {
        "id": "meta-llama/Llama-2-70b-chat-hf",
        "name": "Llama 2 70B Chat",
        "family": "llama2",
        "size_gb": 140,
        "min_gpu_gb": 4,
        "desc": "Meta's previous gen 70B — battle-tested and reliable",
    },
    {
        "id": "google/gemma-2-27b-it",
        "name": "Gemma 2 27B IT",
        "family": "gemma2",
        "size_gb": 54,
        "min_gpu_gb": 4,
        "desc": "Google's 27B instruction-tuned model",
    },
]


class AirLLMEngine:
    def __init__(self):
        self.loaded_models: Dict[str, Any] = {}
        self.loaded_tokenizers: Dict[str, Any] = {}
        self.current_model_id: Optional[str] = None
        self._lock = threading.Lock()
        self._loading = False
        self._last_error: Optional[str] = None
        self._stats = {
            "total_inferences": 0,
            "total_tokens_generated": 0,
            "avg_latency_ms": 0,
            "last_inference_at": None,
        }

    def is_available(self) -> bool:
        return AIRLLM_AVAILABLE

    def get_capabilities(self) -> Dict[str, Any]:
        return {
            "available": AIRLLM_AVAILABLE,
            "loaded_model": self.current_model_id,
            "loading": self._loading,
            "last_error": self._last_error,
            "stats": self._stats,
            "supported_models": len(SUPPORTED_MODELS),
            "cache_dir": str(AIRLLM_CACHE_DIR),
        }

    def list_models(self) -> List[Dict]:
        return SUPPORTED_MODELS

    def get_model(self, model_id: str) -> Optional[Dict]:
        for m in SUPPORTED_MODELS:
            if m["id"] == model_id:
                return m
        return None

    def load_model(self, model_id: str) -> Dict[str, Any]:
        if not AIRLLM_AVAILABLE:
            return {"success": False, "error": "airllm not installed. Run: pip install airllm"}

        model_info = self.get_model(model_id)
        if not model_info:
            return {"success": False, "error": f"Unknown model: {model_id}"}

        with self._lock:
            if self.current_model_id == model_id:
                return {"success": True, "message": f"Model {model_id} already loaded", "cached": True}

            self._loading = True
            self._last_error = None

        try:
            if model_id in self.loaded_models:
                self.current_model_id = model_id
                return {"success": True, "message": f"Model {model_id} loaded from cache", "cached": True}

            tokenizer = AutoTokenizer.from_pretrained(model_id, trust_remote_code=True)
            model = AutoModel.from_pretrained(
                model_id,
                multi_gpus=False,
                trust_remote_code=True,
                DiskOffloadPath=str(AIRLLM_CACHE_DIR / model_id.replace("/", "_")),
            )

            self.loaded_models[model_id] = model
            self.loaded_tokenizers[model_id] = tokenizer
            self.current_model_id = model_id

            return {"success": True, "message": f"Model {model_id} loaded successfully", "cached": False}

        except Exception as e:
            self._last_error = str(e)
            return {"success": False, "error": str(e)}
        finally:
            self._loading = False

    def unload_model(self, model_id: Optional[str] = None) -> Dict:
        target = model_id or self.current_model_id
        if not target:
            return {"success": False, "error": "No model loaded"}

        with self._lock:
            self.loaded_models.pop(target, None)
            self.loaded_tokenizers.pop(target, None)
            if self.current_model_id == target:
                self.current_model_id = None
        return {"success": True, "message": f"Model {target} unloaded"}

    async def generate(
        self,
        prompt: str,
        model_id: Optional[str] = None,
        max_new_tokens: int = 2048,
        temperature: float = 0.7,
        top_p: float = 0.9,
        top_k: int = 50,
        repetition_penalty: float = 1.1,
        system_prompt: Optional[str] = None,
        stop: Optional[List[str]] = None,
    ) -> Dict[str, Any]:
        target_model = model_id or self.current_model_id
        if not target_model:
            return {"success": False, "error": "No model loaded. Call load_model first."}

        if target_model not in self.loaded_models:
            load_result = self.load_model(target_model)
            if not load_result["success"]:
                return load_result

        try:
            tokenizer = self.loaded_tokenizers[target_model]
            model = self.loaded_models[target_model]

            # Build chat prompt
            messages = []
            if system_prompt:
                messages.append({"role": "system", "content": system_prompt})
            messages.append({"role": "user", "content": prompt})

            # Format based on model family
            model_info = self.get_model(target_model)
            family = model_info["family"] if model_info else "llama3"

            if family in ["llama3", "llama2"]:
                formatted = tokenizer.apply_chat_template(messages, tokenize=False, add_generation_prompt=True)
            elif family == "qwen2":
                formatted = tokenizer.apply_chat_template(messages, tokenize=False, add_generation_prompt=True)
            else:
                # Generic format
                formatted = "\n".join(f"{m['role'].upper()}: {m['content']}" for m in messages)
                formatted += "\nASSISTANT:"

            inputs = tokenizer(formatted, return_tensors="pt")

            start_time = time.time()
            output = await asyncio.to_thread(
                model.generate,
                **inputs,
                max_new_tokens=max_new_tokens,
                temperature=temperature,
                top_p=top_p,
                top_k=top_k,
                repetition_penalty=repetition_penalty,
            )
            latency_ms = (time.time() - start_time) * 1000

            generated = tokenizer.decode(output[0][inputs["input_ids"].shape[-1]:], skip_special_tokens=True)

            # Apply stop sequences
            if stop:
                for s in stop:
                    if s in generated:
                        generated = generated[:generated.index(s)]

            self._stats["total_inferences"] += 1
            self._stats["total_tokens_generated"] += len(generated.split())
            self._stats["avg_latency_ms"] = (
                (self._stats["avg_latency_ms"] * (self._stats["total_inferences"] - 1) + latency_ms)
                / self._stats["total_inferences"]
            )
            self._stats["last_inference_at"] = datetime.utcnow().isoformat()

            return {
                "success": True,
                "text": generated.strip(),
                "model": target_model,
                "tokens": len(generated.split()),
                "latency_ms": round(latency_ms, 2),
                "usage": {
                    "prompt_tokens": inputs["input_ids"].shape[-1],
                    "completion_tokens": len(generated.split()),
                },
            }

        except Exception as e:
            return {"success": False, "error": str(e)}

    def cleanup(self):
        self.loaded_models.clear()
        self.loaded_tokenizers.clear()
        self.current_model_id = None


# Singleton
airllm_engine = AirLLMEngine()
