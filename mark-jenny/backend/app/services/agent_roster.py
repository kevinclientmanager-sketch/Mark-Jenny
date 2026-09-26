"""The built-in agent roster.

Two lead agents own the product's two jobs:

* **Imti** - the agent role. It reasons about goals, plans, researches, writes,
  analyses, and reviews everything Mark produces.
* **Mark** - the coding and building role. It plans, executes and researches the
  work that produces code, features and apps.

Each lead has its own sub-agents. The specific job of a sub-agent is stored in
``config["role"]`` because ``Agent.type`` is a broad capability bucket shared
across the product (PRIMARY / RESEARCH / CODING / DOCUMENT / DATA / QA), and
widening that enum would force a schema change on every existing database.

Seeding is idempotent: rows are matched on (name, parent) so a redeploy or a
second call never duplicates the roster.
"""

from typing import Any, Dict, List

from sqlalchemy.orm import Session

# (name, type, role, description, tools)
IMTI_SUBAGENTS: List[tuple] = [
    (
        "Planner", "SUPERVISOR", "planner",
        "Breaks a goal into ordered steps with an acceptance test for each one.",
        ["task_plan", "task_run"],
    ),
    (
        "Executor", "PRIMARY", "executor",
        "Carries out the plan step by step and reports what actually happened.",
        ["task_run", "files_write", "code_execute"],
    ),
    (
        "Researcher", "RESEARCH", "researcher",
        "Gathers facts from the web, the codebase and memory before answering.",
        ["browser", "knowledge_search", "web_fetch"],
    ),
    (
        "Writer", "DOCUMENT", "writer",
        "Turns findings into clear written output: docs, specs, summaries.",
        ["files_write"],
    ),
    (
        "Analyst", "DATA", "analyst",
        "Weighs evidence, compares options and produces a recommendation.",
        ["code_execute", "knowledge_search"],
    ),
    (
        "Reviewer", "QA", "reviewer",
        "Reviews everything Mark builds or codes and sends issues back.",
        ["code_execute", "files_list"],
    ),
]

MARK_SUBAGENTS: List[tuple] = [
    (
        "Planner", "CODING", "planner",
        "Turns a build request into concrete code changes and files to touch.",
        ["task_plan", "files_list"],
    ),
    (
        "Executor", "CODING", "executor",
        "Writes the code, runs it, and fixes what breaks.",
        ["code_execute", "files_write", "task_run"],
    ),
    (
        "Researcher", "RESEARCH", "researcher",
        "Looks up the APIs, libraries and patterns needed for the build.",
        ["browser", "web_fetch", "code_execute"],
    ),
]

LEADS: List[dict] = [
    {
        "name": "Imti",
        "type": "PRIMARY",
        "role": "agent",
        "description": (
            "The agent. Reasons about your goals, plans the work, researches, writes "
            "and analyses - and reviews everything Mark builds."
        ),
        "tools": ["task_plan", "task_run", "knowledge_search", "memory_recall"],
    },
    {
        "name": "Mark",
        "type": "CODING",
        "role": "coding",
        "description": (
            "The coding and building agent. Writes code, features and apps end to end."
        ),
        "tools": ["code_execute", "files_write", "task_run", "self_build"],
    },
]

CHILDREN: Dict[str, List[tuple]] = {
    "Imti": IMTI_SUBAGENTS,
    "Mark": MARK_SUBAGENTS,
}


def roster() -> List[Dict[str, Any]]:
    """The full roster as plain dicts, leads first then their sub-agents."""
    out: List[Dict[str, Any]] = []
    for lead in LEADS:
        out.append({
            "name": lead["name"],
            "type": lead["type"],
            "role": lead["role"],
            "parent": None,
            "description": lead["description"],
            "tools": list(lead["tools"]),
        })
        for name, type_, role, desc, tools in CHILDREN[lead["name"]]:
            out.append({
                "name": name,
                "type": type_,
                "role": role,
                "parent": lead["name"],
                "description": desc,
                "tools": list(tools),
            })
    return out


def ensure_roster(db: Session) -> int:
    """Insert any missing roster agents. Returns the number of rows created.

    Matching is done in Python rather than with JSON SQL operators: the config
    column is a JSON blob whose "parent" is absent for the two leads, and the
    portable way to tell those apart is to compare the loaded values.
    """
    from app.models.agent import Agent, AgentType

    existing = set()
    for row in db.query(Agent).all():
        cfg = row.config if isinstance(row.config, dict) else {}
        existing.add((row.name, cfg.get("parent")))

    created = 0
    for spec in roster():
        if (spec["name"], spec["parent"]) in existing:
            continue
        db.add(Agent(
            name=spec["name"],
            type=AgentType(spec["type"]),
            description=spec["description"],
            system_prompt=(
                f"You are {spec['name']}"
                + (f", working under {spec['parent']}" if spec["parent"] else "")
                + f". Your role is {spec['role']}. {spec['description']}"
            ),
            available_tools=spec["tools"],
            config={"role": spec["role"], "parent": spec["parent"], "roster": True},
            is_active=True,
        ))
        created += 1
    if created:
        db.commit()
    return created
