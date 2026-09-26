"""Skill playbook authoring.

The official registry shipped identical boilerplate instructions for every
skill ("You are an expert X. Execute the 'x' skill: plan the workflow..."),
which told the agent nothing about *how* to do the work.

This module asks the configured model to author a real, tool-specific
playbook for a skill at install time. The result records where it came from
so the UI never presents a template as if it were a designed skill:

  playbook_source = "model"     - authored by the connected provider
  playbook_source = "template"  - no model was reachable; generic body kept
"""
from typing import Any, Dict, Optional

TEMPLATE_MARKER = "You are an expert"

PLAYBOOK_PROMPT = """You are the skill architect for MARK-IMTI, an autonomous AI agent platform.

Write a complete operating playbook for this skill.

SKILL: {name} - {description}
DECLARED TOOLS: {tools}
DECLARED PERMISSIONS: {permissions}
USER REQUEST THAT TRIGGERED THIS SKILL:
{trigger}

The playbook must be concrete and follow this exact structure:

## Goal
One sentence: the outcome this skill must produce.

## When To Use
2-4 bullet conditions.

## Inputs
List the inputs required, and what to do if one is missing.

## Procedure
Numbered steps. Each step must name the concrete tool or capability to use
and the decision made at that step. Reference only the declared tools where
relevant, and say explicitly when a step needs a capability that is missing.

## Quality Bar
The specific checks that must pass before the result is delivered.

## Failure Handling
What to do when a step fails, a source is unavailable, or the result is
incomplete. Be specific about what to report to the user.

## Output Format
The exact shape of the deliverable (report sections, file layout, table
columns, etc).

Write the playbook only - no preamble, no markdown fence around the whole thing.
"""


def is_template(instructions: Optional[str]) -> bool:
    return not instructions or TEMPLATE_MARKER in instructions


def author_playbook(
    name: str,
    description: str,
    tools: list,
    permissions: list,
    trigger: str = "",
    db=None,
    user_id: Optional[int] = None,
    timeout: int = 90,
) -> Dict[str, Any]:
    """Return {"instructions": str, "source": "model"|"template", "error": str|None}."""
    prompt = PLAYBOOK_PROMPT.format(
        name=name,
        description=description,
        tools=", ".join(tools) or "none declared",
        permissions=", ".join(permissions) or "none declared",
        trigger=(trigger or "not supplied - write the general workflow")[:1500],
    )
    text = ""
    error = None
    try:
        from app.services.model_caller import ModelCaller
        text = await_run(ModelCaller.call(
            prompt,
            "You write precise, executable agent playbooks. You never pad with filler.",
            max_tokens=2000,
            temperature=0.3,
            db=db,
            user_id=user_id,
        ))
    except Exception as exc:
        error = f"{type(exc).__name__}: {exc}"

    body = (text or "").strip()
    if not body or "not connected to an AI model" in body.lower() or len(body) < 200:
        return {
            "instructions": (
                f"You are an expert {name}. Execute the '{name}' skill: plan the workflow, "
                f"use the required tools ({', '.join(tools)}) as needed, follow industry best "
                "practices, verify outputs against the original goal, and deliver a polished result."
            ),
            "source": "template",
            "error": error or "No model answered, so a generic template was kept.",
        }
    return {"instructions": body, "source": "model", "error": None}


def await_run(coro):
    """Run a coroutine from sync code (skill install is a sync route)."""
    import asyncio
    try:
        loop = asyncio.get_running_loop()
    except RuntimeError:
        return asyncio.run(coro)
    # Already inside a loop: run in a private one to avoid re-entrancy.
    new_loop = asyncio.new_event_loop()
    try:
        return new_loop.run_until_complete(coro)
    finally:
        new_loop.close()
