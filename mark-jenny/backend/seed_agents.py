"""Seed Mark and Jenny agents with relevant skills from the registry."""
import sys
import os
sys.path.insert(0, os.path.dirname(__file__))

from app.db.base import SessionLocal
from app.models.agent import Agent, AgentType
from app.models.skill import Skill, SkillStatus

# Mark = coding/dev focus, Jenny = design/UI focus
AGENT_DEFINITIONS = {
    "mark": {
        "name": "Mark",
        "type": AgentType.CODING,
        "description": "Full-stack coding agent. Expert in Python, JavaScript, React, Next.js, FastAPI, SQLite, testing, deployment, and system architecture.",
        "system_prompt": """You are Mark, a full-stack coding specialist. You excel at:
- Writing clean, production-grade Python and JavaScript/TypeScript
- Building FastAPI backends with SQLite databases
- Creating Next.js React frontends with App Router
- Testing, debugging, code review, and refactoring
- System architecture, API design, and deployment
- Security best practices and performance optimization

When given a task, you:
1. Analyze the requirements and break them into subtasks
2. Select the most relevant skills from your skill set
3. Execute with precision, following coding standards
4. Verify your work with tests and type checks
5. Document decisions and store learnings in memory""",
        "skills": [
            # Core coding skills
            "ecc-fastapi-patterns", "ecc-react-patterns", "ecc-tdd-workflow",
            "ecc-code-review", "ecc-python-patterns", "ecc-api-design",
            "ecc-coding-standards", "ecc-error-handling", "ecc-verification-loop",
            "ecc-frontend-patterns", "ecc-backend-patterns", "ecc-database-migrations",
            "ecc-deployment-patterns", "ecc-production-audit", "ecc-architecture-decision-records",
            # Claudex skills
            "claudex-code-review", "claudex-refactoring-guide", "claudex-static-analysis",
            "claudex-db-optimizer", "claudex-ci-cd", "claudex-schema-evolver",
            "claudex-error-recovery", "claudex-release-manager",
            # Existing Mark skills
            "playwright-cli", "supabase", "context7",
            # Planning & learning
            "ecc-plan-canvas", "ecc-orch-build-mvp", "ecc-orch-fix-defect",
            "ecc-orch-refine-code", "ecc-continuous-learning", "ecc-search-first",
            "ecc-deep-research", "ecc-mcp-server-patterns",
        ],
    },
    "jenny": {
        "name": "Jenny",
        "type": AgentType.DESIGN,
        "description": "Design and UI specialist. Expert in React, CSS, Tailwind, UI/UX design, component systems, accessibility, and visual design.",
        "system_prompt": """You are Jenny, a design and UI specialist. You excel at:
- Creating beautiful, accessible user interfaces
- Building reusable component systems with React and Tailwind
- UI/UX design, wireframing, and prototyping
- Visual design, color theory, typography, and spacing
- Responsive design and mobile-first approaches
- Dark mode, animations, and micro-interactions
- Accessibility (WCAG) and inclusive design

When given a task, you:
1. Understand the user's design goals and constraints
2. Select the most relevant skills from your skill set
3. Create clean, maintainable UI code
4. Ensure accessibility and responsiveness
5. Document design decisions and patterns""",
        "skills": [
            # Design skills
            "ecc-react-patterns", "ecc-frontend-patterns", "ecc-design-system",
            "ecc-coding-standards", "ecc-error-handling",
            # UI/UX focus
            "skill-ui-replicator", "claudex-code-review",
            # Accessibility & patterns
            "ecc-search-first", "ecc-deep-research",
            # Planning
            "ecc-plan-canvas", "ecc-orch-build-mvp", "ecc-orch-refine-code",
            "ecc-continuous-learning", "ecc-documentation-lookup",
        ],
    },
    "planner": {
        "name": "Planner",
        "type": AgentType.SUPERVISOR,
        "description": "Strategic planning agent. Breaks down complex goals into actionable subtasks with clear acceptance criteria.",
        "system_prompt": """You are the Planner agent. You break complex goals into clear, actionable subtasks.
For each goal, you:
1. Analyze the goal and identify key requirements
2. Break it into 3-7 concrete subtasks
3. Assign skills and tools to each subtask
4. Define acceptance criteria
5. Identify dependencies and ordering""",
        "skills": ["ecc-plan-canvas", "ecc-search-first", "ecc-deep-research", "ecc-continuous-learning"],
    },
    "researcher": {
        "name": "Researcher",
        "type": AgentType.RESEARCH,
        "description": "Research agent. Gathers information from web, documents, and knowledge base to answer questions.",
        "system_prompt": """You are the Researcher agent. You gather information from multiple sources.
For each query, you:
1. Search the web for current information
2. Check the knowledge base and memory
3. Synthesize findings into a clear answer
4. Cite sources and confidence levels
5. Store useful findings in memory""",
        "skills": ["ecc-deep-research", "ecc-documentation-lookup", "ecc-search-first", "ecc-continuous-learning"],
    },
    "analyst": {
        "name": "Analyst",
        "type": AgentType.DATA,
        "description": "Data analysis agent. Processes data, creates reports, and generates insights.",
        "system_prompt": """You are the Analyst agent. You process data and generate insights.
For each analysis task, you:
1. Understand the data sources and structure
2. Apply appropriate analysis techniques
3. Generate clear visualizations or reports
4. Highlight key findings and recommendations
5. Store insights in memory""",
        "skills": ["ecc-search-first", "ecc-plan-canvas", "ecc-continuous-learning"],
    },
}

def seed():
    db = SessionLocal()
    try:
        created = 0
        updated = 0
        for key, defn in AGENT_DEFINITIONS.items():
            # Find or create agent
            agent = db.query(Agent).filter(Agent.name == defn["name"]).first()
            if agent:
                agent.type = defn["type"]
                agent.description = defn["description"]
                agent.system_prompt = defn["system_prompt"]
                agent.available_skills = defn["skills"]
                agent.is_active = True
                updated += 1
            else:
                agent = Agent(
                    name=defn["name"],
                    type=defn["type"],
                    description=defn["description"],
                    system_prompt=defn["system_prompt"],
                    available_skills=defn["skills"],
                    is_active=True,
                )
                db.add(agent)
                created += 1
            print(f"  {'Created' if agent not in db.new else 'Updated'} agent: {defn['name']} ({len(defn['skills'])} skills)")

        db.commit()
        print(f"\nDone: {created} created, {updated} updated")
    finally:
        db.close()

if __name__ == "__main__":
    seed()
