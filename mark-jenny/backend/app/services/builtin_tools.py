"""Mark-Imti's own capabilities, exposed as callable MCP-style tools.

This makes the app's Skills engine reachable through the same
`/mcp/tools` + `/mcp/call` surface used for external MCP servers, so agents
(and integrations) can discover and invoke real skills uniformly instead of
every feature having its own bespoke endpoint.

These are implemented in-process - no subprocess, no network hop.
"""
from typing import Any, Dict, List


def list_tools() -> List[Dict[str, Any]]:
    return [
        {
            "name": "skills_list",
            "description": "List every skill installed for this user, with status, version and source.",
            "server": "mark-imti",
            "inputSchema": {"type": "object", "properties": {
                "status": {"type": "string", "description": "Optional filter: INSTALLED, DISABLED, UPDATING"},
            }},
        },
        {
            "name": "skills_search",
            "description": "Find skills that match a capability description, e.g. 'write a spreadsheet'.",
            "server": "mark-imti",
            "inputSchema": {"type": "object", "properties": {
                "query": {"type": "string", "description": "What you want the skill to do."},
            }, "required": ["query"]},
        },
        {
            "name": "memory_recall",
            "description": "Scored recall across the 9 memory layers for this user.",
            "server": "mark-imti",
            "inputSchema": {"type": "object", "properties": {
                "query": {"type": "string"},
                "limit": {"type": "integer", "default": 5},
            }, "required": ["query"]},
        },
        {
            "name": "knowledge_search",
            "description": "Search the user's knowledge base entries.",
            "server": "mark-imti",
            "inputSchema": {"type": "object", "properties": {
                "query": {"type": "string"},
            }, "required": ["query"]},
        },
        {
            "name": "code_execute",
            "description": "Run code in the sandboxed executor (python, javascript, powershell) and return stdout/stderr.",
            "server": "mark-imti",
            "inputSchema": {"type": "object", "properties": {
                "language": {"type": "string", "enum": ["python", "javascript", "powershell"]},
                "code": {"type": "string"},
                "timeout": {"type": "integer", "default": 30},
            }, "required": ["language", "code"]},
        },
        {
            "name": "files_list",
            "description": "List files the user owns, optionally filtered by project.",
            "server": "mark-imti",
            "inputSchema": {"type": "object", "properties": {
                "project_id": {"type": "integer"},
                "limit": {"type": "integer", "default": 25},
            }},
        },
        {
            "name": "model_call",
            "description": "Call the user's configured AI provider directly and return the raw completion.",
            "server": "mark-imti",
            "inputSchema": {"type": "object", "properties": {
                "prompt": {"type": "string"},
                "system": {"type": "string"},
                "max_tokens": {"type": "integer", "default": 1024},
            }, "required": ["prompt"]},
        },
    ]


async def call_tool(tool_name: str, arguments: Dict[str, Any], db, user) -> Dict[str, Any]:
    from app.models.skill import Skill, SkillStatus
    from app.models.knowledge import Knowledge, Memory
    from app.models.file import File

    args = arguments or {}

    if tool_name == "skills_list":
        q = db.query(Skill)
        if args.get("status"):
            try:
                q = q.filter(Skill.status == SkillStatus(args["status"].upper()))
            except Exception:
                pass
        rows = q.limit(200).all()
        return {"skills": [
            {"id": s.id, "name": s.name, "description": s.description,
             "version": s.version, "source": s.source.value if hasattr(s.source, "value") else s.source,
             "status": s.status.value if hasattr(s.status, "value") else s.status}
            for s in rows], "count": len(rows)}

    if tool_name == "skills_search":
        query = (args.get("query") or "").lower()
        rows = db.query(Skill).all()
        scored = []
        for s in rows:
            hay = f"{s.name} {s.description or ''} {s.instructions or ''}".lower()
            score = sum(hay.count(t) for t in query.split() if len(t) > 2)
            if score:
                scored.append((score, s))
        scored.sort(key=lambda x: x[0], reverse=True)
        return {"matches": [
            {"id": s.id, "name": s.name, "description": s.description, "score": sc}
            for sc, s in scored[:10]]}

    if tool_name == "memory_recall":
        query = args.get("query") or ""
        limit = int(args.get("limit") or 5)
        try:
            from app.services.agent_brain import recall_scored
            hits = await recall_scored(db, user.id, query)
            return {"memories": [
                {"type": h.get("type"), "content": (h.get("content") or "")[:400], "score": round(h.get("score", 0), 3)}
                for h in hits[:limit]]}
        except Exception as exc:
            rows = db.query(Memory).filter(Memory.owner_id == user.id).limit(limit).all()
            return {"memories": [{"type": m.type.value if hasattr(m.type, "value") else m.type,
                                  "content": m.content[:400], "score": None} for m in rows],
                    "note": f"scored recall unavailable ({exc}); returned recent memories"}

    if tool_name == "knowledge_search":
        query = (args.get("query") or "").lower()
        rows = db.query(Knowledge).filter(Knowledge.owner_id == user.id).all() if hasattr(Knowledge, "owner_id") \
            else db.query(Knowledge).all()
        hits = [k for k in rows if query in f"{k.name} {k.content}".lower()]
        return {"knowledge": [{"id": k.id, "name": k.name, "use_when": getattr(k, "use_when", None),
                               "content": (k.content or "")[:600]} for k in hits[:10]], "count": len(hits)}

    if tool_name == "code_execute":
        from app.services.code_execution_engine import code_execution_engine
        lang = (args.get("language") or "python").lower()
        result = code_execution_engine.execute(args.get("code") or "", lang,
                                               timeout=int(args.get("timeout") or 30))
        return result if isinstance(result, dict) else {"result": str(result)}

    if tool_name == "files_list":
        q = db.query(File).filter(File.owner_id == user.id)
        if args.get("project_id"):
            q = q.filter(File.project_id == args["project_id"])
        rows = q.limit(int(args.get("limit") or 25)).all()
        return {"files": [{"id": f.id, "name": f.original_name, "type": f.file_type,
                           "size": getattr(f, "size_bytes", None)} for f in rows]}

    if tool_name == "model_call":
        from app.services.model_caller import ModelCaller
        text = await ModelCaller.call(
            args.get("prompt") or "",
            args.get("system") or "",
            max_tokens=int(args.get("max_tokens") or 1024),
            db=db, user_id=user.id,
        )
        return {"text": text, "ai_powered": bool(text) and "not connected to an AI model" not in text.lower()}

    raise ValueError(f"Unknown tool '{tool_name}'")
