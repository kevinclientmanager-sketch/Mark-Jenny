"""
Mark-Imti Multi-Model Router — Routes tasks to best model
Based on Manus AI's multi-model approach (Claude + Qwen)
Routes code tasks to Codex, research to GPT-5, creative to Gemini
"""

import json
from enum import Enum
from typing import Any, Optional, Callable, Awaitable
from dataclasses import dataclass


class TaskDomain(Enum):
    CODE = "code"
    RESEARCH = "research"
    CREATIVE = "creative"
    ANALYSIS = "analysis"
    CONVERSATION = "conversation"
    TRANSLATION = "translation"
    MATH = "math"
    SECURITY = "security"
    SCIENCE = "science"
    GENERAL = "general"


@dataclass
class ModelConfig:
    name: str
    provider: str
    model_id: str
    api_key: str
    base_url: str
    max_tokens: int
    cost_per_1k_input: float
    cost_per_1k_output: float
    strengths: list[str]
    weaknesses: list[str]
    latency_ms: int
    reliability: float


class ModelRouter:
    """
    Routes tasks to the best model based on:
    - Task domain (code, research, creative, etc.)
    - Complexity level
    - Cost optimization
    - Latency requirements
    - Model strengths/weaknesses
    """

    def __init__(self):
        self.models: dict[str, ModelConfig] = {}
        self.routing_history: list[dict] = []
        self.domain_preferences: dict[TaskDomain, list[str]] = {}
        self._setup_default_routing()

    def _setup_default_routing(self):
        self.domain_preferences = {
            TaskDomain.CODE: ["codex", "claude", "gpt-5"],
            TaskDomain.RESEARCH: ["gpt-5", "claude", "gemini"],
            TaskDomain.CREATIVE: ["gemini", "claude", "gpt-5"],
            TaskDomain.ANALYSIS: ["claude", "gpt-5", "gemini"],
            TaskDomain.CONVERSATION: ["claude", "gpt-5", "gemini"],
            TaskDomain.TRANSLATION: ["gemini", "claude", "gpt-5"],
            TaskDomain.MATH: ["gpt-5", "claude", "gemini"],
            TaskDomain.SECURITY: ["claude-mythos", "claude", "gpt-5"],
            TaskDomain.SCIENCE: ["claude-mythos", "gpt-5", "gemini"],
            TaskDomain.GENERAL: ["claude", "gpt-5", "gemini"],
        }

    def register_model(self, model_id: str, config: ModelConfig):
        self.models[model_id] = config

    def classify_domain(self, text: str) -> TaskDomain:
        text_lower = text.lower()

        code_signals = ["code", "function", "class", "api", "debug", "refactor",
                        "implement", "algorithm", "database", "sql", "git", "deploy"]
        if any(s in text_lower for s in code_signals):
            return TaskDomain.CODE

        research_signals = ["research", "analyze", "compare", "investigate",
                           "study", "review", "literature", "papers", "sources"]
        if any(s in text_lower for s in research_signals):
            return TaskDomain.RESEARCH

        creative_signals = ["write", "create", "design", "story", "poem",
                           "creative", "imagine", "brainstorm", "art"]
        if any(s in text_lower for s in creative_signals):
            return TaskDomain.CREATIVE

        analysis_signals = ["data", "statistics", "chart", "graph", "metrics",
                           "performance", "benchmark", "evaluate"]
        if any(s in text_lower for s in analysis_signals):
            return TaskDomain.ANALYSIS

        math_signals = ["calculate", "equation", "formula", "proof", "theorem",
                       "probability", "statistics", "algebra"]
        if any(s in text_lower for s in math_signals):
            return TaskDomain.MATH

        security_signals = ["security", "vulnerability", "exploit", "penetration",
                           "firewall", "encryption", "audit", "scan"]
        if any(s in text_lower for s in security_signals):
            return TaskDomain.SECURITY

        science_signals = ["molecule", "protein", "genome", "experiment",
                          "hypothesis", "laboratory", "clinical", "drug"]
        if any(s in text_lower for s in science_signals):
            return TaskDomain.SCIENCE

        translate_signals = ["translate", "translation", "language", "localize"]
        if any(s in text_lower for s in translate_signals):
            return TaskDomain.TRANSLATION

        return TaskDomain.GENERAL

    def route(self, text: str, preferences: dict = None) -> dict:
        domain = self.classify_domain(text)
        preferences = preferences or {}

        preferred_models = self.domain_preferences.get(domain, ["claude", "gpt-5"])

        best_model = None
        best_score = -1

        for model_id in preferred_models:
            if model_id not in self.models:
                continue

            model = self.models[model_id]
            score = self._score_model(model, domain, preferences)

            if score > best_score:
                best_score = score
                best_model = model

        if not best_model and self.models:
            best_model = next(iter(self.models.values()))
            best_score = 0.5

        result = {
            "domain": domain.value,
            "model": best_model.name if best_model else None,
            "model_id": best_model.model_id if best_model else None,
            "provider": best_model.provider if best_model else None,
            "score": best_score,
            "alternatives": [
                {"model": m.name, "model_id": m.model_id}
                for m in self.models.values()
                if m != best_model
            ][:3],
        }

        self.routing_history.append({
            "text_preview": text[:100],
            "domain": domain.value,
            "selected": result["model"],
            "score": best_score,
        })

        return result

    def _score_model(self, model: ModelConfig, domain: TaskDomain,
                     preferences: dict) -> float:
        score = 0.5

        if domain.value in model.strengths:
            score += 0.3

        if preferences.get("prioritize_speed"):
            score -= model.latency_ms / 10000
        elif preferences.get("prioritize_cost"):
            score -= model.cost_per_1k_output / 100
        elif preferences.get("prioritize_quality"):
            score += model.reliability / 100

        score += model.reliability / 200

        return min(1.0, max(0.0, score))

    def get_stats(self) -> dict:
        domain_counts = {}
        for entry in self.routing_history:
            d = entry["domain"]
            domain_counts[d] = domain_counts.get(d, 0) + 1

        return {
            "total_routed": len(self.routing_history),
            "domain_distribution": domain_counts,
            "registered_models": len(self.models),
        }
