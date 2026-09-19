# Full-Stack Development with CrewAI

## Overview
Use CrewAI multi-agent orchestration for complex full-stack development tasks. This skill coordinates specialized agents for planning, coding, testing, and documentation.

## When to Use
- Building new features requiring multiple components
- Refactoring across frontend and backend
- Complex bug fixes requiring investigation + implementation
- Architecture decisions requiring analysis

## Workflow

### 1. Plan with Research Crew
```
Use the crewai_run MCP tool:
- Agent 1: "Architect" - Analyze requirements and design solution
- Agent 2: "Researcher" - Find best practices and patterns
```

### 2. Implement with Development Crew
```
Use crewai_create_crew with task_type "code_review" or custom:
- Agent 1: "Backend Developer" - Implement API/database changes
- Agent 2: "Frontend Developer" - Implement UI changes
- Agent 3: "Tester" - Write and run tests
```

### 3. Review with Quality Crew
```
Use crewai_create_crew with task_type "code_review":
- Agent 1: "Code Reviewer" - Review for quality and patterns
- Agent 2: "Security Analyst" - Check for vulnerabilities
```

## Example: Building a New API Endpoint

```javascript
// Step 1: Research
crewai_run({
  agents: [
    { role: "API Architect", goal: "Design RESTful endpoint", backstory: "Expert in API design patterns" },
    { role: "Database Specialist", goal: "Design data model", backstory: "SQL and ORM expert" }
  ],
  tasks: [
    { description: "Design POST /api/v1/resource endpoint", expected_output: "API spec", agent_role: "API Architect" },
    { description: "Design database schema", expected_output: "SQL migration", agent_role: "Database Specialist" }
  ]
})

// Step 2: Implement
// Use the output to guide your implementation

// Step 3: Review
crewai_create_crew({ task_type: "code_review", topic: "New API endpoint implementation" })
```

## Mark Project Context
- Backend: FastAPI + SQLite at `mark-jenny/backend`
- Frontend: Next.js 16 at `mark-jenny/frontend`
- Auth: OAuth2 form at `/api/v1/auth/login`
- Key routers: `backend/app/api/v1/endpoints/`
