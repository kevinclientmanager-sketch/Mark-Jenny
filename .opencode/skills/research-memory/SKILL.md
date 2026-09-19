# Research with Hermes Persistent Memory

## Overview
Use Hermes Agent's persistent memory and research capabilities for tasks that require learning, remembering, and building on previous work.

## When to Use
- Research tasks that span multiple sessions
- Building knowledge bases about the project
- Complex investigations requiring memory of past findings
- Tasks that benefit from accumulated context

## Workflow

### 1. Store Project Context
```
Use hermes_memory MCP tool:
- action: "store"
- content: "Project uses FastAPI + SQLite backend, Next.js 16 frontend. Auth is OAuth2 form-based."
```

### 2. Search Previous Research
```
Use hermes_memory MCP tool:
- action: "search"
- content: "authentication implementation"
```

### 3. Execute Research Tasks
```
Use hermes_execute MCP tool:
- command: "Research best practices for FastAPI rate limiting and document findings"
- tools: ["web_search", "file_ops"]
```

### 4. Create Reusable Skills
```
Use hermes_skills MCP tool:
- action: "create"
- skill_name: "fastapi-patterns"
- skill_description: "Common FastAPI patterns and best practices for this project"
```

## Memory Best Practices

### Store After Learning
After solving a complex problem, store the solution:
```
hermes_memory store "Solved CORS issue by adding middleware in main.py with allow_origins=['http://localhost:3000']"
```

### Search Before Solving
Before tackling a similar problem, search memory:
```
hermes_memory search "CORS configuration"
```

### Build Knowledge Over Time
The more you use Hermes memory, the better it becomes at:
- Recalling project-specific patterns
- Suggesting solutions based on past work
- Avoiding repeated mistakes

## Mark Project Memory Seeds

Store these in Hermes memory to get started:
1. "Mark Jenny is a ChatGPT-like application with FastAPI backend and Next.js frontend"
2. "Backend runs on port 8000, frontend on port 3000"
3. "Auth is temporarily bypassed with AUTO_LOGIN_DEMO=true"
4. "SQLite database at backend/mark_jenny.db"
5. "Quick actions defined in backend/app/api/v1/endpoints/quick_actions.py"
