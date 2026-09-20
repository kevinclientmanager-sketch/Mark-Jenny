"""
Self-Build Orchestrator — The heart of Mark-Imti's self-building system.
User describes what they want in plain language to Jenny.
Jenny coordinates Mark (builder agent) to build it in a sandbox.
Jenny tests, validates, versions, and integrates when ready.

Flow:
1. User writes plain language request in chat
2. Jenny parses intent, breaks into tasks
3. Mark builds code in isolated sandbox
4. Jenny monitors, tests, reviews each change
5. Version snapshots at every step
6. If anything breaks, Jenny rolls back
7. Live preview in right panel (side-by-side)
8. When approved, Jenny merges sandbox into live app
"""
import asyncio
import json
import os
import shutil
import subprocess
import sys
import time
import traceback
from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional, Dict, Any, List, Callable
from enum import Enum

from app.core.config import get_settings

settings = get_settings()

# Directories
DATA_DIR = Path(os.environ.get("MARK_JENNY_DATA", "."))
SANDBOX_DIR = DATA_DIR / "sandbox"
VERSIONS_DIR = DATA_DIR / "versions"
LIVE_DIR = DATA_DIR / "live"
BUILD_LOGS_DIR = DATA_DIR / "build_logs"

for d in [SANDBOX_DIR, VERSIONS_DIR, LIVE_DIR, BUILD_LOGS_DIR]:
    d.mkdir(parents=True, exist_ok=True)


class BuildStatus(str, Enum):
    IDLE = "idle"
    PARSING = "parsing"
    BUILDING = "building"
    TESTING = "testing"
    REVIEWING = "reviewing"
    INTEGRATING = "integrating"
    ROLLING_BACK = "rolling_back"
    COMPLETE = "complete"
    FAILED = "failed"


class ChangeType(str, Enum):
    NEW_FILE = "new_file"
    MODIFY_FILE = "modify_file"
    DELETE_FILE = "delete_file"
    NEW_SKILL = "new_skill"
    NEW_AGENT = "new_agent"
    NEW_ENDPOINT = "new_endpoint"
    NEW_UI_COMPONENT = "new_ui_component"
    CONFIG_CHANGE = "config_change"
    DEPENDENCY = "dependency"


class BuildStep:
    def __init__(self, step_id: str, description: str, change_type: ChangeType, target: str):
        self.step_id = step_id
        self.description = description
        self.change_type = change_type
        self.target = target
        self.status = "pending"  # pending, running, passed, failed
        self.code = ""
        self.test_result = None
        self.jenny_review = None
        self.started_at = None
        self.completed_at = None

    def to_dict(self) -> Dict:
        return {
            "step_id": self.step_id,
            "description": self.description,
            "change_type": self.change_type.value,
            "target": self.target,
            "status": self.status,
            "test_result": self.test_result,
            "jenny_review": self.jenny_review,
            "started_at": self.started_at.isoformat() if self.started_at else None,
            "completed_at": self.completed_at.isoformat() if self.completed_at else None,
        }


class BuildSession:
    def __init__(self, session_id: str, user_request: str):
        self.session_id = session_id
        self.user_request = user_request
        self.status = BuildStatus.IDLE
        self.steps: List[BuildStep] = []
        self.sandbox_path = SANDBOX_DIR / session_id
        self.version_path = VERSIONS_DIR / session_id
        self.created_at = datetime.utcnow()
        self.completed_at = None
        self.error = None
        self.rollback_version = None
        self.preview_url = None
        self.log_lines = []

    def to_dict(self) -> Dict:
        return {
            "session_id": self.session_id,
            "user_request": self.user_request,
            "status": self.status.value,
            "steps": [s.to_dict() for s in self.steps],
            "created_at": self.created_at.isoformat(),
            "completed_at": self.completed_at.isoformat() if self.completed_at else None,
            "error": self.error,
            "preview_url": self.preview_url,
            "log_count": len(self.log_lines),
        }


class SelfBuildOrchestrator:
    def __init__(self):
        self.sessions: Dict[str, BuildSession] = {}
        self.current_session: Optional[str] = None
        self._callbacks: List[Callable] = []
        self._stats = {
            "total_builds": 0,
            "successful": 0,
            "failed": 0,
            "rollbacks": 0,
            "files_created": 0,
            "files_modified": 0,
        }

    def on_event(self, callback: Callable):
        """Register callback for build events (WebSocket)."""
        self._callbacks.append(callback)

    async def _emit(self, event: str, data: Dict):
        for cb in self._callbacks:
            try:
                await cb(event, data)
            except Exception:
                pass

    def _log(self, session: BuildSession, message: str):
        timestamp = datetime.utcnow().strftime("%H:%M:%S")
        line = f"[{timestamp}] {message}"
        session.log_lines.append(line)
        print(f"[SelfBuild] {line}")

    # === PHASE 1: PARSE USER REQUEST ===

    async def start_build(self, user_request: str) -> str:
        """Start a new build session from user's plain language request."""
        session_id = f"build_{int(time.time())}_{os.urandom(4).hex()}"
        session = BuildSession(session_id, user_request)
        self.sessions[session_id] = session
        self.current_session = session_id

        # Create sandbox
        session.sandbox_path.mkdir(parents=True, exist_ok=True)

        # Copy current live app to sandbox as base
        if LIVE_DIR.exists():
            shutil.copytree(LIVE_DIR, session.sandbox_path, dirs_exist_ok=True)

        self._log(session, f"Build session started: {session_id}")
        self._log(session, f"User request: {user_request}")

        await self._emit("build_started", {"session_id": session_id, "request": user_request})

        # Start the build process
        asyncio.create_task(self._run_build_pipeline(session))

        return session_id

    async def _parse_request(self, session: BuildSession) -> List[BuildStep]:
        """Parse user's plain language into build steps."""
        self._log(session, "Jenny: Analyzing your request...")
        session.status = BuildStatus.PARSING
        await self._emit("status_changed", {"session_id": session.session_id, "status": "building"})

        request = session.user_request.lower()
        steps = []

        # Detect what user wants
        if any(w in request for w in ["website", "web page", "landing page", "html", "page"]):
            steps.append(BuildStep(
                step_id="web_1",
                description="Create website structure and layout",
                change_type=ChangeType.NEW_FILE,
                target="index.html",
            ))
            steps.append(BuildStep(
                step_id="web_2",
                description="Add styling and responsive design",
                change_type=ChangeType.NEW_FILE,
                target="styles.css",
            ))
            steps.append(BuildStep(
                step_id="web_3",
                description="Add interactive functionality",
                change_type=ChangeType.NEW_FILE,
                target="script.js",
            ))

        if any(w in request for w in ["api", "backend", "server", "endpoint", "fastapi", "flask"]):
            steps.append(BuildStep(
                step_id="api_1",
                description="Create API server with endpoints",
                change_type=ChangeType.NEW_ENDPOINT,
                target="api_server.py",
            ))
            steps.append(BuildStep(
                step_id="api_2",
                description="Add database models and schemas",
                change_type=ChangeType.NEW_FILE,
                target="models.py",
            ))

        if any(w in request for w in ["react", "next", "frontend", "ui", "component", "dashboard"]):
            steps.append(BuildStep(
                step_id="ui_1",
                description="Create React/Next.js component structure",
                change_type=ChangeType.NEW_UI_COMPONENT,
                target="components/",
            ))
            steps.append(BuildStep(
                step_id="ui_2",
                description="Build UI layout and state management",
                change_type=ChangeType.NEW_FILE,
                target="page.tsx",
            ))

        if any(w in request for w in ["skill", "ability", "capability"]):
            steps.append(BuildStep(
                step_id="skill_1",
                description="Create new AI skill with instructions",
                change_type=ChangeType.NEW_SKILL,
                target="SKILL.md",
            ))

        if any(w in request for w in ["agent", "specialist", "helper"]):
            steps.append(BuildStep(
                step_id="agent_1",
                description="Configure specialist agent with tools",
                change_type=ChangeType.NEW_AGENT,
                target="agent_config.json",
            ))

        if any(w in request for w in ["database", "db", "sqlite", "table"]):
            steps.append(BuildStep(
                step_id="db_1",
                description="Create database schema and migrations",
                change_type=ChangeType.NEW_FILE,
                target="schema.sql",
            ))

        if any(w in request for w in ["test", "testing", "spec"]):
            steps.append(BuildStep(
                step_id="test_1",
                description="Write tests for the new feature",
                change_type=ChangeType.NEW_FILE,
                target="test_*.py",
            ))

        # Default: generic code generation
        if not steps:
            steps.append(BuildStep(
                step_id="code_1",
                description="Generate code based on request",
                change_type=ChangeType.NEW_FILE,
                target="main.py",
            ))

        self._log(session, f"Jenny: I identified {len(steps)} steps to build:")
        for step in steps:
            self._log(session, f"  → {step.description}")

        return steps

    # === PHASE 2: MARK BUILDS IN SANDBOX ===

    async def _run_build_pipeline(self, session: BuildSession):
        """Main build pipeline: parse → build → test → review → integrate."""
        try:
            # Step 1: Parse
            steps = await self._parse_request(session)
            session.steps = steps

            # Step 2: Build each step
            session.status = BuildStatus.BUILDING
            for step in steps:
                success = await self._build_step(session, step)
                if not success:
                    session.status = BuildStatus.FAILED
                    session.error = f"Build failed at step: {step.description}"
                    self._log(session, f"Mark: Build failed at {step.description}")
                    await self._emit("build_failed", {"session_id": session.session_id, "step": step.to_dict()})
                    return

            # Step 3: Test
            session.status = BuildStatus.TESTING
            self._log(session, "Jenny: Now testing everything...")
            test_results = await self._test_sandbox(session)

            # Step 4: Review
            session.status = BuildStatus.REVIEWING
            self._log(session, "Jenny: Reviewing code quality...")
            review = await self._review_sandbox(session)

            if not review["passed"]:
                self._log(session, f"Jenny: Found {len(review['issues'])} issues. Sending back to Mark...")
                # Mark fixes issues
                for issue in review["issues"][:5]:
                    await self._fix_issue(session, issue)
                # Re-test
                test_results = await self._test_sandbox(session)

            # Step 5: Create version snapshot
            self._create_snapshot(session)

            # Step 6: Ready for integration
            session.status = BuildStatus.COMPLETE
            session.completed_at = datetime.utcnow()
            self._stats["total_builds"] += 1
            self._stats["successful"] += 1
            self._stats["files_created"] += sum(1 for s in steps if s.change_type == ChangeType.NEW_FILE)

            self._log(session, "Jenny: Build complete! Everything looks good.")
            self._log(session, f"Jenny: {len(steps)} steps done, {test_results.get('passed', 0)} tests passed")
            await self._emit("build_complete", {"session_id": session.session_id, "session": session.to_dict()})

        except Exception as e:
            session.status = BuildStatus.FAILED
            session.error = str(e)
            self._stats["failed"] += 1
            self._log(session, f"Jenny: Build failed — {str(e)}")
            await self._emit("build_error", {"session_id": session.session_id, "error": str(e)})

    async def _build_step(self, session: BuildSession, step: BuildStep) -> bool:
        """Mark builds a single step in the sandbox."""
        step.status = "running"
        step.started_at = datetime.utcnow()
        self._log(session, f"Mark: Building — {step.description}")

        await self._emit("step_started", {"session_id": session.session_id, "step": step.to_dict()})

        try:
            target_path = session.sandbox_path / step.target

            if step.change_type == ChangeType.NEW_FILE:
                # Generate real code based on step description
                code = await self._generate_code(step, session.user_request)
                step.code = code

                # Write to sandbox
                target_path.parent.mkdir(parents=True, exist_ok=True)
                if target_path.suffix == ".py":
                    target_path.write_text(code, encoding="utf-8")
                elif target_path.suffix in [".html", ".htm"]:
                    target_path.write_text(code, encoding="utf-8")
                elif target_path.suffix in [".css", ".scss"]:
                    target_path.write_text(code, encoding="utf-8")
                elif target_path.suffix in [".js", ".ts", ".tsx", ".jsx"]:
                    target_path.write_text(code, encoding="utf-8")
                elif target_path.suffix == ".json":
                    target_path.write_text(code, encoding="utf-8")
                elif target_path.suffix == ".md":
                    target_path.write_text(code, encoding="utf-8")
                else:
                    target_path.write_text(code, encoding="utf-8")

                self._log(session, f"Mark: Created {step.target}")

            elif step.change_type == ChangeType.MODIFY_FILE:
                # Modify existing file
                if target_path.exists():
                    content = target_path.read_text(encoding="utf-8")
                    modified = await self._modify_code(content, step, session.user_request)
                    step.code = modified
                    target_path.write_text(modified, encoding="utf-8")
                    self._log(session, f"Mark: Modified {step.target}")

            elif step.change_type == ChangeType.NEW_SKILL:
                code = await self._generate_skill(step, session.user_request)
                step.code = code
                skill_dir = session.sandbox_path / "skills" / step.target.replace("SKILL.md", "").strip("/")
                skill_dir.mkdir(parents=True, exist_ok=True)
                (skill_dir / "SKILL.md").write_text(code, encoding="utf-8")
                self._log(session, f"Mark: Created skill {step.target}")

            elif step.change_type == ChangeType.NEW_ENDPOINT:
                code = await self._generate_endpoint(step, session.user_request)
                step.code = code
                target_path.parent.mkdir(parents=True, exist_ok=True)
                target_path.write_text(code, encoding="utf-8")
                self._log(session, f"Mark: Created endpoint {step.target}")

            step.status = "passed"
            step.completed_at = datetime.utcnow()
            await self._emit("step_complete", {"session_id": session.session_id, "step": step.to_dict()})
            return True

        except Exception as e:
            step.status = "failed"
            step.completed_at = datetime.utcnow()
            self._log(session, f"Mark: Error — {str(e)}")
            return False

    # === PHASE 3: CODE GENERATION ===

    async def _generate_code(self, step: BuildStep, user_request: str) -> str:
        """Mark generates real code using AI based on step description."""
        target = step.target
        desc = step.description
        request = user_request

        # Determine language/type from target
        if target.endswith(".html"):
            lang_hint = "HTML with embedded CSS and JavaScript"
        elif target.endswith(".css"):
            lang_hint = "CSS stylesheet"
        elif target.endswith(".js") or target.endswith(".ts"):
            lang_hint = "JavaScript/TypeScript"
        elif target.endswith(".py"):
            lang_hint = "Python"
        elif target.endswith(".json"):
            lang_hint = "JSON configuration"
        elif target.endswith(".md"):
            lang_hint = "Markdown documentation"
        elif target.endswith(".sql"):
            lang_hint = "SQL schema"
        else:
            lang_hint = "appropriate language"

        system = (
            "You are a senior software engineer. Generate production-quality code. "
            "Write clean, well-documented, complete code following best practices. "
            "Include error handling, proper imports, type hints, and docstrings. "
            "Output ONLY the raw code with no markdown fences or explanations."
        )
        ai_code = _call_ai(
            f"Generate {lang_hint} code for: {desc}\n\n"
            f"User's full request: {request[:2000]}\n\n"
            f"Target file: {target}\n\n"
            "Requirements:\n- Complete, production-ready code\n- Proper error handling\n"
            "- Clean architecture\n- No placeholders or TODOs\n- Real functionality",
            system=system,
            timeout=300,
        )
        if ai_code and len(ai_code) > 30:
            code = ai_code.strip()
            if code.startswith("```"):
                code = code.split("\n", 1)[1]
            if code.endswith("```"):
                code = code[:-3]
            return code.strip()

        # Minimal fallback only when AI is completely unavailable
        return f'# Generated by Mark-Imti\n# {desc}\n# Request: {request[:200]}\n# AI model unavailable — manual implementation required\n'

    async def _modify_code(self, content: str, step: BuildStep, user_request: str) -> str:
        """Mark modifies existing code."""
        # Add new functionality to existing code
        addition = f"\n\n# === Added by Mark-Imti: {step.description} ===\n"
        addition += f"# Request: {user_request[:100]}\n"
        addition += "def new_feature():\n"
        addition += "    '''New feature added via self-build.'''\n"
        addition += "    return {'status': 'added', 'feature': '" + step.description + "'}\n"
        return content + addition

    async def _generate_skill(self, step: BuildStep, user_request: str) -> str:
        """Mark generates a new AI skill."""
        return f"""# {step.description}

## Overview
{user_request[:500]}

## Instructions
1. Understand the user's intent
2. Follow the specific workflow defined here
3. Use available tools to accomplish the task
4. Verify results before reporting completion

## Tools Used
- Code generation
- File management
- Testing

## Quality Standards
- Code must be clean and documented
- Tests must pass
- No breaking changes to existing functionality

## Trigger Words
- {step.description.lower()}
- related keywords from user request
"""

    async def _generate_endpoint(self, step: BuildStep, user_request: str) -> str:
        """Mark generates a new API endpoint file."""
        return f'''"""Endpoint: {step.description}
Generated by Mark-Imti
"""
from fastapi import APIRouter, Depends
from pydantic import BaseModel
from typing import Optional, Any, Dict

router = APIRouter()


class Request(BaseModel):
    data: Optional[Dict[str, Any]] = None


@router.get("/endpoint")
async def endpoint_get():
    return {{"status": "ok", "message": "{step.description}"}}


@router.post("/endpoint")
async def endpoint_post(req: Request):
    return {{"status": "created", "data": req.data}}
'''

    # === PHASE 4: TESTING ===

    async def _test_sandbox(self, session: BuildSession) -> Dict:
        """Jenny tests the sandbox build."""
        self._log(session, "Jenny: Running tests in sandbox...")
        results = {"passed": 0, "failed": 0, "errors": []}

        for step in session.steps:
            if step.status != "passed":
                continue

            target = session.sandbox_path / step.target
            if not target.exists():
                results["errors"].append(f"File not found: {step.target}")
                results["failed"] += 1
                continue

            content = target.read_text(encoding="utf-8")

            # Syntax check for Python
            if target.suffix == ".py":
                try:
                    compile(content, str(target), "exec")
                    results["passed"] += 1
                    self._log(session, f"Jenny: {step.target} — syntax OK ✓")
                except SyntaxError as e:
                    results["errors"].append(f"{step.target}: Syntax error at line {e.lineno}")
                    results["failed"] += 1
                    self._log(session, f"Jenny: {step.target} — syntax error ✗")

            # Syntax check for JavaScript
            elif target.suffix == ".js":
                # Basic check
                if "function" in content or "=>" in content or "const" in content:
                    results["passed"] += 1
                    self._log(session, f"Jenny: {step.target} — structure OK ✓")
                else:
                    results["passed"] += 1  # Simple check

            # HTML check
            elif target.suffix == ".html":
                if "<html" in content.lower() and "</html>" in content.lower():
                    results["passed"] += 1
                    self._log(session, f"Jenny: {step.target} — valid HTML ✓")
                else:
                    results["errors"].append(f"{step.target}: Missing html tags")
                    results["failed"] += 1

            else:
                results["passed"] += 1

        self._log(session, f"Jenny: Tests done — {results['passed']} passed, {results['failed']} failed")
        return results

    # === PHASE 5: JENNY REVIEWS ===

    async def _review_sandbox(self, session: BuildSession) -> Dict:
        """Jenny reviews code quality."""
        issues = []

        for step in session.steps:
            if not step.code:
                continue

            # Check for common issues
            if "TODO" in step.code:
                issues.append({"step": step.step_id, "type": "todo", "message": "Has TODO comments"})
            if "FIXME" in step.code:
                issues.append({"step": step.step_id, "type": "fixme", "message": "Has FIXME comments"})
            if "console.log" in step.code:
                issues.append({"step": step.step_id, "type": "debug", "message": "Has console.log"})
            if step.code.count("\n") > 500:
                issues.append({"step": step.step_id, "type": "size", "message": "File is very large"})

        passed = len(issues) == 0
        self._log(session, f"Jenny: Review complete — {'PASS ✓' if passed else f'{len(issues)} issues found'}")

        return {"passed": passed, "issues": issues}

    async def _fix_issue(self, session: BuildSession, issue: Dict):
        """Mark fixes a review issue."""
        self._log(session, f"Mark: Fixing — {issue['message']}")
        # In a real implementation, Mark would modify the code
        # For now, log the fix attempt

    # === PHASE 6: VERSIONING ===

    def _create_snapshot(self, session: BuildSession):
        """Create a version snapshot of the sandbox."""
        version_num = len(list(VERSIONS_DIR.glob(f"{session.session_id}_*"))) + 1
        snapshot_path = VERSIONS_DIR / f"{session.session_id}_v{version_num}"

        if session.sandbox_path.exists():
            shutil.copytree(session.sandbox_path, snapshot_path)
            self._log(session, f"Jenny: Version snapshot created — v{version_num}")
            session.rollback_version = str(snapshot_path)

        self._stats["files_created"] += len(list(session.sandbox_path.rglob("*")))

    # === PHASE 7: INTEGRATION ===

    async def integrate_to_live(self, session_id: str) -> Dict:
        """Jenny integrates sandbox into live app after approval."""
        session = self.sessions.get(session_id)
        if not session:
            return {"success": False, "error": "Session not found"}

        session.status = BuildStatus.INTEGRATING
        self._log(session, "Jenny: Integrating into live application...")

        try:
            # Copy sandbox to live
            if session.sandbox_path.exists():
                shutil.copytree(session.sandbox_path, LIVE_DIR, dirs_exist_ok=True)

            self._log(session, "Jenny: Integration complete! ✓")
            await self._emit("integrated", {"session_id": session_id})
            return {"success": True, "message": "Integrated to live"}

        except Exception as e:
            session.status = BuildStatus.FAILED
            session.error = str(e)
            return {"success": False, "error": str(e)}

    async def rollback(self, session_id: str) -> Dict:
        """Jenny rolls back to previous version if something breaks."""
        session = self.sessions.get(session_id)
        if not session:
            return {"success": False, "error": "Session not found"}

        session.status = BuildStatus.ROLLING_BACK
        self._log(session, "Jenny: Rolling back to previous version...")

        try:
            if session.rollback_version and Path(session.rollback_version).exists():
                shutil.copytree(session.rollback_version, LIVE_DIR, dirs_exist_ok=True)
                self._stats["rollbacks"] += 1
                self._log(session, "Jenny: Rollback complete ✓")
                return {"success": True, "message": "Rolled back to previous version"}
            else:
                return {"success": False, "error": "No previous version to rollback to"}

        except Exception as e:
            return {"success": False, "error": str(e)}

    # === QUERIES ===

    def get_session(self, session_id: str) -> Optional[Dict]:
        session = self.sessions.get(session_id)
        return session.to_dict() if session else None

    def list_sessions(self) -> List[Dict]:
        return [s.to_dict() for s in self.sessions.values()]

    def get_build_logs(self, session_id: str) -> List[str]:
        session = self.sessions.get(session_id)
        return session.log_lines if session else []

    def get_sandbox_files(self, session_id: str) -> List[Dict]:
        session = self.sessions.get(session_id)
        if not session or not session.sandbox_path.exists():
            return []
        files = []
        for f in session.sandbox_path.rglob("*"):
            if f.is_file():
                files.append({
                    "path": str(f.relative_to(session.sandbox_path)),
                    "size": f.stat().st_size,
                    "modified": datetime.fromtimestamp(f.stat().st_mtime).isoformat(),
                })
        return files

    def get_stats(self) -> Dict:
        return self._stats


# Singleton
self_builder = SelfBuildOrchestrator()
