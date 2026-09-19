"""
QA Engine — Self-testing and quality analysis.
Runs tests, analyzes code, checks build quality, and suggests improvements.
Works automatically when Mark builds anything.
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
        """Analyze code for quality, bugs, and improvements."""
        analysis = {
            "language": language,
            "lines": len(code.split("\n")),
            "issues": [],
            "suggestions": [],
            "score": 100,
        }

        lines = code.split("\n")

        # Basic analysis per language
        if language == "python":
            analysis["issues"] = self._analyze_python(code, lines)
        elif language in ["javascript", "typescript", "tsx", "jsx"]:
            analysis["issues"] = self._analyze_js(code, lines)
        elif language == "html":
            analysis["issues"] = self._analyze_html(code, lines)
        elif language == "css":
            analysis["issues"] = self._analyze_css(code, lines)

        # Score calculation
        analysis["score"] = max(0, 100 - len(analysis["issues"]) * 10)

        # General suggestions
        if len(lines) > 500:
            analysis["suggestions"].append("Consider splitting into smaller files")
        if "TODO" in code or "FIXME" in code:
            analysis["suggestions"].append("Has TODO/FIXME comments — resolve before shipping")
        if "console.log" in code or "print(" in code:
            analysis["suggestions"].append("Has debug statements — remove for production")

        return analysis

    def _analyze_python(self, code: str, lines: List[str]) -> List[Dict]:
        issues = []
        for i, line in enumerate(lines, 1):
            stripped = line.strip()
            if not stripped or stripped.startswith("#"):
                continue
            if "except:" in stripped and "as" not in stripped:
                issues.append({"line": i, "type": "warning", "message": "Bare except clause — catch specific exceptions"})
            if len(line) > 120:
                issues.append({"line": i, "type": "style", "message": f"Line too long ({len(line)} > 120)"})
            if "import *" in stripped:
                issues.append({"line": i, "type": "warning", "message": "Wildcard import — use explicit imports"})
            if "eval(" in stripped or "exec(" in stripped:
                issues.append({"line": i, "type": "security", "message": "Dynamic code execution — potential security risk"})
            if stripped.startswith("def ") and ":" in stripped:
                func_name = stripped.split("def ")[1].split("(")[0]
                if not func_name.startswith("_") and func_name[0].islower():
                    # Check docstring
                    if i < len(lines) and '"""' not in lines[i] and "'''" not in lines[i]:
                        issues.append({"line": i, "type": "docs", "message": f"Function '{func_name}' missing docstring"})
        return issues

    def _analyze_js(self, code: str, lines: List[str]) -> List[Dict]:
        issues = []
        for i, line in enumerate(lines, 1):
            stripped = line.strip()
            if not stripped or stripped.startswith("//"):
                continue
            if "==" in stripped and "===" not in stripped:
                issues.append({"line": i, "type": "warning", "message": "Use strict equality (===) instead of =="})
            if "var " in stripped:
                issues.append({"line": i, "type": "style", "message": "Use const/let instead of var"})
            if "console.log" in stripped:
                issues.append({"line": i, "type": "debug", "message": "console.log in production code"})
            if "any" in stripped and ": any" in stripped:
                issues.append({"line": i, "type": "typescript", "message": "Avoid 'any' type — use specific types"})
        return issues

    def _analyze_html(self, code: str, lines: List[str]) -> List[Dict]:
        issues = []
        if "<html" not in code.lower():
            issues.append({"line": 1, "type": "structure", "message": "Missing <html> tag"})
        if "<head" not in code.lower():
            issues.append({"line": 1, "type": "structure", "message": "Missing <head> section"})
        if "<meta charset" not in code.lower() and "charset=" not in code.lower():
            issues.append({"line": 1, "type": "seo", "message": "Missing charset meta tag"})
        if "<title" not in code.lower():
            issues.append({"line": 1, "type": "seo", "message": "Missing <title> tag"})
        if "alt=" not in code.lower() and "<img" in code.lower():
            issues.append({"line": 1, "type": "a11y", "message": "Images missing alt attributes"})
        return issues

    def _analyze_css(self, code: str, lines: List[str]) -> List[Dict]:
        issues = []
        for i, line in enumerate(lines, 1):
            if "!important" in line:
                issues.append({"line": i, "type": "style", "message": "Avoid !important — use specificity instead"})
        return issues

    async def test_project(self, project_path: str) -> Dict[str, Any]:
        """Run tests for a project."""
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

        # Check for test files
        test_files = list(path.rglob("test_*.py")) + list(path.rglob("*_test.py"))
        if not test_files:
            test_files = list(path.rglob("*.test.js")) + list(path.rglob("*.test.ts"))

        if not test_files:
            return {"success": True, "message": "No test files found", "tests_run": 0}

        # Try running pytest or npm test
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
                # Try npm test
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

        self._stats["total_tests"] += results["tests_run"]
        self._stats["passed"] += results["passed"]
        self._stats["failed"] += results["failed"]
        self._stats["last_test_at"] = datetime.utcnow().isoformat()

        return results

    async def lint_code(self, code: str, language: str) -> Dict[str, Any]:
        """Run linter on code."""
        issues = []

        if language == "python":
            try:
                proc = await asyncio.create_subprocess_exec(
                    sys.executable, "-m", "pylint", "--from stdin", "--output-format=json",
                    stdin=asyncio.subprocess.PIPE,
                    stdout=asyncio.subprocess.PIPE,
                    stderr=asyncio.subprocess.PIPE,
                )
                stdout, _ = await asyncio.wait_for(proc.communicate(input=code.encode()), timeout=30)
                issues = json.loads(stdout.decode()) if stdout.strip() else []
            except Exception:
                pass

        return {"language": language, "issues": issues, "count": len(issues)}

    async def check_build(self, project_path: str) -> Dict[str, Any]:
        """Check if a project builds successfully."""
        path = Path(project_path)
        checks = {
            "has_entry_point": False,
            "has_dependencies": False,
            "has_config": False,
            "build_ok": False,
            "issues": [],
        }

        # Check for common entry points
        entry_points = ["main.py", "app.py", "index.js", "index.ts", "main.js", "main.ts"]
        for ep in entry_points:
            if (path / ep).exists():
                checks["has_entry_point"] = True
                break

        # Check for dependency files
        dep_files = ["requirements.txt", "package.json", "Cargo.toml", "go.mod", "pyproject.toml"]
        for df in dep_files:
            if (path / df).exists():
                checks["has_dependencies"] = True
                break

        # Check for config files
        config_files = [".env", "config.py", "config.json", "tsconfig.json", ".eslintrc"]
        for cf in config_files:
            if (path / cf).exists():
                checks["has_config"] = True
                break

        if not checks["has_entry_point"]:
            checks["issues"].append("No entry point found (main.py, index.js, etc)")
        if not checks["has_dependencies"]:
            checks["issues"].append("No dependency file found (requirements.txt, package.json, etc)")

        return checks

    def get_stats(self) -> Dict:
        return self._stats


# Singleton
qa_engine = QAEngine()
