"""
QA Engine — AI-driven testing, code analysis, and quality assurance.
Uses LLM for deep code analysis, test generation, and failure diagnosis.
"""
import asyncio
import json
import os
import subprocess
import sys
import time
from pathlib import Path
from typing import Optional, Dict, Any, List
from datetime import datetime

from app.core.config import get_settings

settings = get_settings()


def _call_ai(prompt: str, system: str = "", timeout: int = 120) -> str:
    """Call AI model for QA analysis."""
    try:
        from app.services.model_caller import model_caller
        return model_caller.call(prompt, system_prompt=system, timeout=timeout)
    except Exception:
        pass
    try:
        import httpx
        settings = get_settings()
        base = getattr(settings, "OLLAMA_BASE_URL", "http://localhost:11434")
        try:
            tags = httpx.get(f"{base}/api/tags", timeout=5).json()
            models = tags.get("models", [])
            model_name = models[0]["name"] if models else "qwen3-vl:8b"
        except:
            model_name = "qwen3-vl:8b"
        resp = httpx.post(
            f"{base}/api/generate",
            json={"model": model_name, "prompt": prompt, "system": system, "stream": False},
            timeout=timeout,
        )
        return resp.json().get("response", "")
    except Exception:
        return ""


class QAEngine:
    def __init__(self):
        self.test_results: Dict[str, Dict] = {}
        self._stats = {
            "total_tests": 0,
            "passed": 0,
            "failed": 0,
            "last_test_at": None,
        }

    async def analyze_code(self, code: str, language: str = "python") -> Dict[str, Any]:
        """AI-driven deep code analysis for bugs, security, performance, and architecture."""
        system = (
            "You are a senior software engineer and security expert performing code review. "
            "Analyze the code for: bugs, security vulnerabilities, performance issues, "
            "code smells, architectural problems, and improvement opportunities. "
            "Be thorough and specific. Output JSON:\n"
            '{"score": int 0-100, "issues": [{"line": int, "type": str, "severity": "critical|high|medium|low", "message": str, "fix": str}], '
            '"suggestions": [{"type": str, "message": str, "impact": str}], '
            '"security": [{"vulnerability": str, "risk": str, "fix": str}], '
            '"performance": [{"issue": str, "optimization": str}], '
            '"architecture": {"coupling": str, "maintainability": str, "testability": str}}'
        )
        ai_analysis = _call_ai(
            f"Analyze this {language} code for quality, bugs, security, and performance:\n\n```{language}\n{code[:8000]}\n```\n\n"
            "Provide detailed analysis with line numbers, severity ratings, specific fixes, "
            "and architectural assessment. Be thorough — check for SQL injection, XSS, "
            "race conditions, memory leaks, error handling gaps, and design patterns.",
            system=system,
            timeout=180,
        )
        if ai_analysis:
            try:
                cleaned = ai_analysis.strip()
                if cleaned.startswith("```"):
                    cleaned = cleaned.split("\n", 1)[1]
                if cleaned.endswith("```"):
                    cleaned = cleaned[:-3]
                result = json.loads(cleaned.strip())
                result["language"] = language
                result["lines"] = len(code.split("\n"))
                result["ai_powered"] = True
                return result
            except:
                pass

        # Fallback: basic analysis
        lines = code.split("\n")
        issues = []
        if language == "python":
            issues = self._analyze_python(code, lines)
        elif language in ["javascript", "typescript", "tsx", "jsx"]:
            issues = self._analyze_js(code, lines)
        elif language == "html":
            issues = self._analyze_html(code, lines)
        return {
            "language": language,
            "lines": len(lines),
            "issues": issues,
            "suggestions": [],
            "score": max(0, 100 - len(issues) * 10),
            "ai_powered": False,
        }

    def _analyze_python(self, code: str, lines: List[str]) -> List[Dict]:
        issues = []
        for i, line in enumerate(lines, 1):
            stripped = line.strip()
            if not stripped or stripped.startswith("#"):
                continue
            if "except:" in stripped and "as" not in stripped:
                issues.append({"line": i, "type": "warning", "severity": "medium", "message": "Bare except clause", "fix": "Catch specific exceptions"})
            if len(line) > 120:
                issues.append({"line": i, "type": "style", "severity": "low", "message": f"Line too long ({len(line)} > 120)", "fix": "Break into multiple lines"})
            if "eval(" in stripped or "exec(" in stripped:
                issues.append({"line": i, "type": "security", "severity": "critical", "message": "Dynamic code execution", "fix": "Use ast.literal_eval or safe alternatives"})
            if "import *" in stripped:
                issues.append({"line": i, "type": "warning", "severity": "medium", "message": "Wildcard import", "fix": "Use explicit imports"})
        return issues

    def _analyze_js(self, code: str, lines: List[str]) -> List[Dict]:
        issues = []
        for i, line in enumerate(lines, 1):
            stripped = line.strip()
            if not stripped or stripped.startswith("//"):
                continue
            if "==" in stripped and "===" not in stripped:
                issues.append({"line": i, "type": "warning", "severity": "medium", "message": "Use strict equality (===)", "fix": "Replace == with ==="})
            if "var " in stripped:
                issues.append({"line": i, "type": "style", "severity": "low", "message": "Use const/let instead of var", "fix": "Replace var with const or let"})
            if "console.log" in stripped:
                issues.append({"line": i, "type": "debug", "severity": "low", "message": "console.log in production code", "fix": "Remove or use proper logging"})
        return issues

    def _analyze_html(self, code: str, lines: List[str]) -> List[Dict]:
        issues = []
        if "<html" not in code.lower():
            issues.append({"line": 1, "type": "structure", "severity": "high", "message": "Missing <html> tag", "fix": "Add <html> wrapper"})
        if "<meta charset" not in code.lower():
            issues.append({"line": 1, "type": "seo", "severity": "medium", "message": "Missing charset meta tag", "fix": 'Add <meta charset="utf-8">'})
        if "alt=" not in code.lower() and "<img" in code.lower():
            issues.append({"line": 1, "type": "a11y", "severity": "medium", "message": "Images missing alt attributes", "fix": "Add alt text to all images"})
        return issues

    async def analyze_with_ai(self, code: str, language: str = "python", focus: str = "general") -> Dict[str, Any]:
        """Targeted AI analysis with specific focus area."""
        focus_prompts = {
            "security": "Focus on security vulnerabilities: SQL injection, XSS, CSRF, authentication bypass, data exposure, insecure deserialization, SSRF, path traversal.",
            "performance": "Focus on performance: O(n²) loops, unnecessary allocations, N+1 queries, missing indexes, blocking I/O, memory leaks, cache misses.",
            "architecture": "Focus on architecture: SOLID principles, coupling, cohesion, dependency injection, design patterns, separation of concerns.",
            "testing": "Focus on testability: mock-friendly design, dependency injection, pure functions, test coverage gaps, edge cases.",
            "general": "Comprehensive analysis covering bugs, security, performance, and architecture.",
        }
        system = (
            "You are a principal software engineer conducting an expert code review. "
            f"{focus_prompts.get(focus, focus_prompts['general'])}\n"
            "Provide specific line numbers, severity, and actionable fixes. "
            "Output JSON: {\"score\": int, \"findings\": [{\"line\": int, \"severity\": str, \"category\": str, \"title\": str, \"description\": str, \"fix\": str}]}"
        )
        ai_result = _call_ai(
            f"Perform {focus} analysis on this {language} code:\n\n```{language}\n{code[:8000]}\n```",
            system=system,
            timeout=180,
        )
        if ai_result:
            try:
                cleaned = ai_result.strip()
                if cleaned.startswith("```"):
                    cleaned = cleaned.split("\n", 1)[1]
                if cleaned.endswith("```"):
                    cleaned = cleaned[:-3]
                result = json.loads(cleaned.strip())
                result["ai_powered"] = True
                result["focus"] = focus
                return result
            except:
                pass
        return await self.analyze_code(code, language)

    async def test_project(self, project_path: str) -> Dict[str, Any]:
        """Run tests and analyze failures with AI."""
        results = {
            "project": project_path,
            "tests_run": 0,
            "passed": 0,
            "failed": 0,
            "errors": [],
            "output": "",
        }
        path = Path(project_path)
        if not path.exists():
            return {"success": False, "error": "Project path not found"}

        test_files = list(path.rglob("test_*.py")) + list(path.rglob("*_test.py"))
        if not test_files:
            test_files = list(path.rglob("*.test.js")) + list(path.rglob("*.test.ts"))
        if not test_files:
            return {"success": True, "message": "No test files found", "tests_run": 0}

        try:
            if any(f.suffix == ".py" for f in test_files):
                proc = await asyncio.create_subprocess_exec(
                    sys.executable, "-m", "pytest", str(path), "-v", "--tb=short",
                    stdout=asyncio.subprocess.PIPE,
                    stderr=asyncio.subprocess.PIPE,
                )
                stdout, stderr = await asyncio.wait_for(proc.communicate(), timeout=60)
                results["output"] = stdout.decode()
                results["tests_run"] = results["output"].count("PASSED") + results["output"].count("FAILED")
                results["passed"] = results["output"].count("PASSED")
                results["failed"] = results["output"].count("FAILED")
            else:
                proc = await asyncio.create_subprocess_exec(
                    "npm", "test", "--prefix", str(path),
                    stdout=asyncio.subprocess.PIPE,
                    stderr=asyncio.subprocess.PIPE,
                )
                stdout, stderr = await asyncio.wait_for(proc.communicate(), timeout=60)
                results["output"] = stdout.decode() + stderr.decode()
        except asyncio.TimeoutError:
            results["errors"].append("Test execution timed out")
        except Exception as e:
            results["errors"].append(str(e))

        # AI analysis of test failures
        if results["failed"] > 0 and results["output"]:
            system = (
                "You are a test failure analyst. Analyze test failures and provide root causes and fixes. "
                "Output JSON: {\"failures\": [{\"test\": str, \"cause\": str, \"fix\": str, \"severity\": str}]}"
            )
            ai_diagnosis = _call_ai(
                f"Analyze these test failures and provide root causes and fixes:\n\n{results['output'][:5000]}",
                system=system,
                timeout=120,
            )
            if ai_diagnosis:
                try:
                    cleaned = ai_diagnosis.strip()
                    if cleaned.startswith("```"):
                        cleaned = cleaned.split("\n", 1)[1]
                    if cleaned.endswith("```"):
                        cleaned = cleaned[:-3]
                    results["ai_diagnosis"] = json.loads(cleaned.strip())
                except:
                    pass

        self._stats["total_tests"] += results["tests_run"]
        self._stats["passed"] += results["passed"]
        self._stats["failed"] += results["failed"]
        self._stats["last_test_at"] = datetime.utcnow().isoformat()
        return results

    async def generate_tests(self, code: str, language: str = "python") -> Dict[str, Any]:
        """AI generates comprehensive tests for given code."""
        system = (
            "You are a test engineer. Generate comprehensive unit tests for the given code. "
            "Include: happy path, edge cases, error cases, boundary conditions, "
            "concurrent scenarios, and integration tests where appropriate. "
            f"Use pytest for Python, Jest for JavaScript. "
            "Output ONLY the test code with no markdown fences."
        )
        ai_tests = _call_ai(
            f"Generate comprehensive tests for this {language} code:\n\n```{language}\n{code[:6000]}\n```\n\n"
            "Include:\n- Unit tests for all public functions/methods\n- Edge cases (empty, null, boundary values)\n"
            "- Error handling tests\n- At least 80% coverage of logic paths\n- Fixtures and helpers as needed",
            system=system,
            timeout=300,
        )
        if ai_tests and len(ai_tests) > 50:
            test_code = ai_tests.strip()
            if test_code.startswith("```"):
                test_code = test_code.split("\n", 1)[1]
            if test_code.endswith("```"):
                test_code = test_code[:-3]
            return {"language": language, "tests": test_code.strip(), "ai_powered": True}
        return {"language": language, "tests": "", "ai_powered": False, "message": "AI unavailable"}

    async def lint_code(self, code: str, language: str) -> Dict[str, Any]:
        """Run linter and analyze results with AI."""
        issues = []
        raw_output = ""
        if language == "python":
            try:
                proc = await asyncio.create_subprocess_exec(
                    sys.executable, "-m", "pylint", "--from stdin", "--output-format=json",
                    stdin=asyncio.subprocess.PIPE,
                    stdout=asyncio.subprocess.PIPE,
                    stderr=asyncio.subprocess.PIPE,
                )
                stdout, _ = await asyncio.wait_for(proc.communicate(input=code.encode()), timeout=30)
                raw_output = stdout.decode()
                issues = json.loads(raw_output) if raw_output.strip() else []
            except Exception:
                pass

        # AI interpretation of lint results
        if issues:
            system = (
                "You are a code quality expert. Analyze linting issues and prioritize fixes. "
                "Output JSON: {\"critical_fixes\": [str], \"improvements\": [str], \"refactoring\": [str]}"
            )
            ai_interp = _call_ai(
                f"Prioritize these linting issues and suggest fixes:\n{json.dumps(issues[:20], indent=2)}",
                system=system,
                timeout=60,
            )
            if ai_interp:
                try:
                    cleaned = ai_interp.strip()
                    if cleaned.startswith("```"):
                        cleaned = cleaned.split("\n", 1)[1]
                    if cleaned.endswith("```"):
                        cleaned = cleaned[:-3]
                    return {"language": language, "issues": issues, "count": len(issues), "ai_prioritization": json.loads(cleaned.strip())}
                except:
                    pass

        return {"language": language, "issues": issues, "count": len(issues)}

    async def check_build(self, project_path: str) -> Dict[str, Any]:
        """Check if a project builds successfully with AI analysis."""
        path = Path(project_path)
        checks = {
            "has_entry_point": False,
            "has_dependencies": False,
            "has_config": False,
            "build_ok": False,
            "issues": [],
        }

        entry_points = ["main.py", "app.py", "index.js", "index.ts", "main.js", "main.ts"]
        for ep in entry_points:
            if (path / ep).exists():
                checks["has_entry_point"] = True
                break

        dep_files = ["requirements.txt", "package.json", "Cargo.toml", "go.mod", "pyproject.toml"]
        for df in dep_files:
            if (path / df).exists():
                checks["has_dependencies"] = True
                break

        config_files = [".env", "config.py", "config.json", "tsconfig.json", ".eslintrc"]
        for cf in config_files:
            if (path / cf).exists():
                checks["has_config"] = True
                break

        if not checks["has_entry_point"]:
            checks["issues"].append("No entry point found")
        if not checks["has_dependencies"]:
            checks["issues"].append("No dependency file found")

        # AI architecture review
        source_files = list(path.rglob("*.py"))[:5] + list(path.rglob("*.ts"))[:5] + list(path.rglob("*.js"))[:5]
        if source_files:
            combined = ""
            for sf in source_files[:3]:
                try:
                    combined += f"\n--- {sf.name} ---\n{sf.read_text(encoding='utf-8')[:2000]}\n"
                except:
                    pass
            if combined:
                system = (
                    "You are a software architect. Review this project structure and source code. "
                    "Identify architectural issues, missing patterns, and improvements. "
                    "Output JSON: {\"architecture_score\": int, \"issues\": [str], \"improvements\": [str], \"missing\": [str]}"
                )
                ai_arch = _call_ai(
                    f"Review this project's architecture:\n{combined[:6000]}",
                    system=system,
                    timeout=120,
                )
                if ai_arch:
                    try:
                        cleaned = ai_arch.strip()
                        if cleaned.startswith("```"):
                            cleaned = cleaned.split("\n", 1)[1]
                        if cleaned.endswith("```"):
                            cleaned = cleaned[:-3]
                        checks["ai_architecture_review"] = json.loads(cleaned.strip())
                    except:
                        pass

        return checks

    def get_stats(self) -> Dict:
        return self._stats


qa_engine = QAEngine()
