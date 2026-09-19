from typing import List, Dict, Optional, Any
from sqlalchemy.orm import Session
from app.models.task import Task
from app.models.agent import Agent, Model
from app.services.model_router import ModelRouter
import uuid

class ExecutionLogger:
    def __init__(self):
        self.logs: List[Dict] = []
    def log(self, task_id: int, stage: str, data: Dict):
        self.logs.append({"task_id": task_id, "stage": stage, "data": data})
    def get_logs(self, task_id: int) -> List[Dict]:
        return [l for l in self.logs if l["task_id"]==task_id]

class ContextManager:
    def __init__(self, max_tokens: int = 100000):
        self.max_tokens = max_tokens
    def compress(self, messages: List[Dict]) -> List[Dict]:
        # Simple compression: keep system + last 10, summarize middle if too long
        if len(messages) <= 12:
            return messages
        # Keep first and last 10
        return [messages[0]] + [{"role":"system","content":f"[Compressed {len(messages)-11} messages]"}] + messages[-10:]

class MemoryManager:
    def __init__(self, db: Session, user_id: int):
        self.db = db
        self.user_id = user_id
    def recall(self, query: str, project_id: Optional[int]=None, limit: int = 5) -> List[Dict]:
        # Scored retrieval across Memory + Knowledge (Agent Brain).
        # Falls back to legacy keyword match if the brain is unavailable.
        try:
            from app.services.agent_brain import recall_scored
            scored = recall_scored(self.db, self.user_id, query, project_id, limit=limit)
            return [{"id": s["id"], "type": s["type"], "content": s["content"][:200],
                     "importance": s.get("importance", 50), "score": s.get("score", 0),
                     "kind": s.get("kind", "memory")} for s in scored]
        except Exception:
            from app.models.knowledge import Memory
            q = self.db.query(Memory).filter(Memory.owner_id==self.user_id, Memory.enabled==True)
            if project_id:
                q = q.filter((Memory.project_id==project_id) | (Memory.project_id.is_(None)))
            results = []
            for m in q.limit(20).all():
                if query.lower() in m.content.lower():
                    results.append({"id":m.id, "type":m.type.value, "content":m.content[:200], "importance":m.importance})
            return sorted(results, key=lambda x: x["importance"], reverse=True)[:limit]
    def store_task_memory(self, task: Task, decision: str):
        from app.models.knowledge import Memory, MemoryType
        m = Memory(type=MemoryType.TASK, content=decision, source=f"task:{task.id}", owner_id=task.owner_id, project_id=task.project_id, task_id=task.id, confidence=90, importance=70)
        self.db.add(m); self.db.commit()

class ApprovalManager:
    def __init__(self, db: Session):
        self.db = db
    def requires_approval(self, task: Task, action: str) -> bool:
        # Level 1 asks before all, Level 2 sensitive, Level 3 autonomous within permissions, Level 4 scheduled
        # For now: if autonomy_level 1 -> always, 2 -> if action in sensitive list, 3-> never, 4-> never for scheduled
        sensitive = ["send_email","publish_website","delete_files","execute_command","spend_money","post_publicly"]
        if task.autonomy_level == 1:
            return True
        if task.autonomy_level == 2 and action in sensitive:
            return True
        return False
    def request(self, task: Task, action_type: str, title: str, details: Dict) -> int:
        from app.models.approval import Approval, ApprovalType, ApprovalStatus
        # Map action
        try:
            at = ApprovalType(action_type)
        except:
            at = ApprovalType.CUSTOM
        appr = Approval(type=at, title=title, description=details.get("description",""), details=details, task_id=task.id, user_id=task.owner_id, requested_by="agent", status=ApprovalStatus.PENDING)
        self.db.add(appr); self.db.commit(); self.db.refresh(appr)
        return appr.id

class ToolExecutor:
    def __init__(self):
        self.available_tools = ["web_search","file_read","file_write","code_execute","browser_navigate","connector_execute"]
    def select_tools(self, task: Task, skill_tools: List[str]) -> List[str]:
        # Ground tool choice in the real inventory (engines, connectors),
        # seeded by any explicit plan requirements and skill tools.
        needed = list(task.plan.get("required_tools", [])) if task.plan else []
        needed += [t for t in (skill_tools or []) if t not in needed]
        if not needed:
            try:
                from app.services.agent_brain import classify_intent, _INTENT_SUBTASKS
                intent = classify_intent(task.original_request or "")
                for _t, _k, tools, _a in _INTENT_SUBTASKS.get(intent["intent"], []):
                    needed += [t for t in tools if t not in needed]
            except Exception:
                prompt = (task.original_request or "").lower()
                if "research" in prompt or "search" in prompt:
                    needed = ["web_search"]
                elif "code" in prompt or "build" in prompt:
                    needed = ["code_execute","file_write"]
                elif "browse" in prompt or "website" in prompt:
                    needed = ["browser_navigate"]
        # Map skill-tool names onto engine tools
        mapping = {"web_search": "web_search", "browser_navigate": "browser_navigate",
                   "search": "web_search", "code": "code_execute", "files": "file_read"}
        needed = [mapping.get(t, t) for t in needed]
        picked = [t for t in needed if t in self.available_tools]
        return picked or ["file_read"]

class TaskPlanner:
    def __init__(self, db: Session, user_id: int):
        self.db = db
        self.user_id = user_id
        self.memory = MemoryManager(db, user_id)

    def decompose(self, user_request: str, project_id: Optional[int]=None) -> Dict:
        # Intent-aware decomposition with acceptance criteria and skill routing.
        # Falls back to the legacy heuristic if the brain is unavailable.
        memories = self.memory.recall(user_request, project_id)
        try:
            from app.services import agent_brain
            from app.models.skill import Skill, SkillStatus
            intent = agent_brain.classify_intent(user_request)
            routing = agent_brain.route_skills(self.db, self.user_id, user_request, intent)
            skill_names = [s["name"] for s in routing["assigned"]]
            if not skill_names:
                installed = self.db.query(Skill).filter(
                    Skill.owner_id == self.user_id,
                    Skill.status.in_([SkillStatus.ENABLED, SkillStatus.INSTALLED])).limit(3).all()
                skill_names = [s.name for s in installed]
            plan = agent_brain.plan_heuristic(user_request, intent, routing["assigned"])
            subtasks = [{**st, "skills": skill_names[:2]} for st in plan["subtasks"]]
            return {
                "original": user_request,
                "subtasks": subtasks,
                "memories_used": memories,
                "estimated_steps": len(subtasks),
                "intent": intent,
                "skill_gaps": routing["gaps"],
                "context": plan.get("context", ""),
            }
        except Exception:
            lower = user_request.lower()
            subtasks = []
            if "research" in lower:
                subtasks.append({"title":"Research and gather sources", "skills":["research-agent"]})
            if "spreadsheet" in lower or "excel" in lower:
                subtasks.append({"title":"Create spreadsheet", "skills":["spreadsheet-agent"]})
            if "report" in lower or "compare" in lower:
                subtasks.append({"title":"Write recommendation report", "skills":["document-agent"]})
            if not subtasks:
                parts = [p.strip() for p in user_request.split(",") if p.strip()]
                for p in parts[:4]:
                    subtasks.append({"title": p[:60], "skills":[]})
            if not subtasks:
                subtasks = [{"title": user_request[:60], "skills":[]}]
            return {
                "original": user_request,
                "subtasks": subtasks,
                "memories_used": memories,
                "estimated_steps": len(subtasks)
            }

class AgentController:
    def __init__(self, db: Session, user_id: int):
        self.db = db
        self.user_id = user_id
        self.router = ModelRouter(db, user_id)
        self.planner = TaskPlanner(db, user_id)
        self.tool_exec = ToolExecutor()
        self.memory = MemoryManager(db, user_id)
        self.approval = ApprovalManager(db)
        self.context = ContextManager()
        self.logger = ExecutionLogger()

    async def plan_task(self, user_request: str, project_id: Optional[int]=None, task_type: str = "fast") -> Dict:
        # Full pipeline: Intent -> Decompose -> Skill/Model/Tool -> Plan
        decomposition = self.planner.decompose(user_request, project_id)
        # Model selection (hybrid)
        model = await self.router.select_model(task_type)
        fallback = await self.router.select_with_fallback_chain(task_type)
        # Tool selection
        # Create a mock task for tool selection
        mock_task = Task(original_request=user_request, plan={"required_tools": []})
        tools = self.tool_exec.select_tools(mock_task, [])
        # Check for missing capabilities (Self-Build hook)
        missing = []
        # If no model found for vision but task needs it, mark missing
        if task_type == "vision" and not any("VISION" in (m.capabilities or []) for m in ([model] if model else [])):
            missing.append("vision-model")
        plan = {
            "id": str(uuid.uuid4()),
            "user_request": user_request,
            "decomposition": decomposition,
            "selected_model": {"id": model.id, "name": model.name, "provider": model.provider.value} if model else None,
            "fallback_chain": [{"id":m.id, "name":m.name} for m in fallback[:2]],
            "tools": tools,
            "missing_capabilities": missing,
            "requires_approval": False,  # would check via approval manager
            "estimated_cost": (model.cost_per_1k_input or 0) if model else 0
        }
        return plan

    async def estimate_cost(self, user_request: str, task_type: str = "fast") -> Dict:
        model = await self.router.select_model(task_type, prefer_cheap=True)
        cheap_model = await self.router.select_model(task_type, prefer_cheap=True)
        return {
            "task_type": task_type,
            "selected": {"name": model.name, "cost_input": model.cost_per_1k_input, "cost_output": model.cost_per_1k_output} if model else None,
            "cheapest": {"name": cheap_model.name, "cost": (cheap_model.cost_per_1k_input or 0)} if cheap_model else None,
            "hybrid": f"Ollama available: {await self.router.registry.is_ollama_available()}"
        }
