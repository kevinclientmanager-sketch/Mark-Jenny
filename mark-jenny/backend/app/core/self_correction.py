"""
Mark-Imti Self-Correction — Automatic error detection and correction
Based on Manus AI's self-reflection loop
Detects errors, analyzes root causes, and applies fixes
"""

import json
import time
from enum import Enum
from typing import Any, Optional
from dataclasses import dataclass, field
from datetime import datetime


class ErrorType(Enum):
    SYNTAX = "syntax"
    LOGIC = "logic"
    RUNTIME = "runtime"
    TIMEOUT = "timeout"
    FORMAT = "format"
    INCOMPLETE = "incomplete"
    INCORRECT = "incorrect"
    SECURITY = "security"
    PERFORMANCE = "performance"
    UNKNOWN = "unknown"


class CorrectionStrategy(Enum):
    RETRY = "retry"
    REFINE_PROMPT = "refine_prompt"
    USE_DIFFERENT_TOOL = "use_different_tool"
    DECOMPOSE_FURTHER = "decompose_further"
    REQUEST_CLARIFICATION = "request_clarification"
    FALLBACK_MODEL = "fallback_model"
    APPLY_FIX = "apply_fix"


@dataclass
class ErrorAnalysis:
    error_type: ErrorType
    root_cause: str
    confidence: float
    suggested_strategies: list[CorrectionStrategy]
    context: dict = field(default_factory=dict)


@dataclass
class CorrectionAttempt:
    id: str
    original_output: str
    error_analysis: ErrorAnalysis
    strategy: CorrectionStrategy
    corrected_output: Optional[str] = None
    success: bool = False
    timestamp: str = field(default_factory=lambda: datetime.utcnow().isoformat())


class SelfCorrectionLoop:
    """
    Detects errors in agent output and automatically corrects them.
    Uses root cause analysis and multiple correction strategies.
    """

    def __init__(self, model_caller=None, max_corrections: int = 3):
        self.model = model_caller
        self.max_corrections = max_corrections
        self.correction_history: list[CorrectionAttempt] = []
        self.error_patterns: dict[ErrorType, int] = {}

    async def analyze_error(self, output: str, expected: str = None,
                            context: dict = None) -> ErrorAnalysis:
        if self.model:
            prompt = f"""Analyze this output for errors:
OUTPUT: {output[:3000]}
EXPECTED: {expected[:1000] if expected else "N/A"}
CONTEXT: {json.dumps(context or {}, default=str)[:1000]}

Return JSON:
{{
    "error_type": "syntax|logic|runtime|timeout|format|incomplete|incorrect|security|performance|unknown",
    "root_cause": "detailed explanation",
    "confidence": 0.0-1.0,
    "suggested_strategies": ["retry", "refine_prompt", "use_different_tool", "decompose_further", "apply_fix"]
}}"""
            try:
                response = await self.model.complete(prompt, max_tokens=1000)
                data = json.loads(response)
                return ErrorAnalysis(
                    error_type=ErrorType(data.get("error_type", "unknown")),
                    root_cause=data.get("root_cause", "Unknown error"),
                    confidence=data.get("confidence", 0.5),
                    suggested_strategies=[
                        CorrectionStrategy(s) for s in data.get("suggested_strategies", ["retry"])
                    ],
                    context=context or {},
                )
            except Exception:
                pass

        return self._heuristic_analysis(output, expected)

    def _heuristic_analysis(self, output: str, expected: str = None) -> ErrorAnalysis:
        error_type = ErrorType.UNKNOWN
        root_cause = "Unable to determine"
        strategies = [CorrectionStrategy.RETRY]

        if "error" in output.lower() or "traceback" in output.lower():
            error_type = ErrorType.RUNTIME
            root_cause = "Runtime error detected in output"
            strategies = [CorrectionStrategy.APPLY_FIX, CorrectionStrategy.RETRY]
        elif "timeout" in output.lower():
            error_type = ErrorType.TIMEOUT
            root_cause = "Operation timed out"
            strategies = [CorrectionStrategy.RETRY, CorrectionStrategy.DECOMPOSE_FURTHER]
        elif len(output) < 10:
            error_type = ErrorType.INCOMPLETE
            root_cause = "Output is too short"
            strategies = [CorrectionStrategy.REFINE_PROMPT, CorrectionStrategy.RETRY]
        elif expected and self._similarity(output, expected) < 0.3:
            error_type = ErrorType.INCORRECT
            root_cause = "Output does not match expected result"
            strategies = [CorrectionStrategy.REFINE_PROMPT, CorrectionStrategy.USE_DIFFERENT_TOOL]

        return ErrorAnalysis(
            error_type=error_type,
            root_cause=root_cause,
            confidence=0.4,
            suggested_strategies=strategies,
        )

    def _similarity(self, a: str, b: str) -> float:
        words_a = set(a.lower().split())
        words_b = set(b.lower().split())
        if not words_a or not words_b:
            return 0
        intersection = words_a & words_b
        union = words_a | words_b
        return len(intersection) / len(union)

    async def correct(self, output: str, error_analysis: ErrorAnalysis,
                      original_input: str = None, context: dict = None) -> CorrectionAttempt:
        attempt = CorrectionAttempt(
            id=f"corr-{int(time.time())}",
            original_output=output,
            error_analysis=error_analysis,
            strategy=error_analysis.suggested_strategies[0] if error_analysis.suggested_strategies
                     else CorrectionStrategy.RETRY,
        )

        for strategy in error_analysis.suggested_strategies[:self.max_corrections]:
            attempt.strategy = strategy

            if strategy == CorrectionStrategy.RETRY:
                corrected = await self._retry(original_input, context)
            elif strategy == CorrectionStrategy.REFINE_PROMPT:
                corrected = await self._refine_prompt(original_input, error_analysis, context)
            elif strategy == CorrectionStrategy.APPLY_FIX:
                corrected = await self._apply_fix(output, error_analysis)
            elif strategy == CorrectionStrategy.DECOMPOSE_FURTHER:
                corrected = await self._decompose_further(original_input, context)
            elif strategy == CorrectionStrategy.USE_DIFFERENT_TOOL:
                corrected = await self._try_different_tool(original_input, context)
            else:
                continue

            if corrected:
                attempt.corrected_output = corrected
                attempt.success = True
                break

        self.correction_history.append(attempt)
        self.error_patterns[error_analysis.error_type] = \
            self.error_patterns.get(error_analysis.error_type, 0) + 1

        return attempt

    async def _retry(self, input_text: str, context: dict) -> Optional[str]:
        if not self.model:
            return None
        try:
            return await self.model.complete(input_text or "", max_tokens=4000)
        except Exception:
            return None

    async def _refine_prompt(self, input_text: str, analysis: ErrorAnalysis,
                              context: dict) -> Optional[str]:
        if not self.model:
            return None
        refined = f"""Previous attempt failed: {analysis.root_cause}
Original request: {input_text}
Please try again, being more careful about: {analysis.root_cause}"""
        try:
            return await self.model.complete(refined, max_tokens=4000)
        except Exception:
            return None

    async def _apply_fix(self, output: str, analysis: ErrorAnalysis) -> Optional[str]:
        if not self.model:
            return None
        prompt = f"Fix the following output based on this error: {analysis.root_cause}\n\nOUTPUT:\n{output[:3000]}"
        try:
            return await self.model.complete(prompt, max_tokens=4000)
        except Exception:
            return None

    async def _decompose_further(self, input_text: str, context: dict) -> Optional[str]:
        if not self.model:
            return None
        prompt = f"This task failed. Break it into smaller steps:\n{input_text}"
        try:
            return await self.model.complete(prompt, max_tokens=2000)
        except Exception:
            return None

    async def _try_different_tool(self, input_text: str, context: dict) -> Optional[str]:
        return await self._retry(input_text, context)

    def get_stats(self) -> dict:
        return {
            "total_corrections": len(self.correction_history),
            "success_rate": sum(1 for c in self.correction_history if c.success) /
                           max(1, len(self.correction_history)),
            "error_patterns": dict(self.error_patterns),
            "strategy_usage": {},
        }
