"""Curated MCP server registry.

Mark-Imti can talk to any MCP server over stdio, but hand-writing the JSON-RPC
launch config is error prone. This registry ships known-good launch recipes for
the servers people actually want, so they can be connected in one click.

`required_env` marks secrets the user must supply; `local_only` marks servers
that cannot run on a cloud host (they need Docker or a browser on the machine).
"""
from typing import Any, Dict, List

MCP_REGISTRY: List[Dict[str, Any]] = [
    {
        "id": "context7",
        "label": "Context7",
        "category": "Documentation",
        "description": "Pulls up-to-date, version-specific library documentation so agents code against the real API instead of guessing.",
        "command": "npx",
        "args": ["-y", "@upstash/context7-mcp"],
        "env": {},
        "required_env": [],
        "optional_env": ["CONTEXT7_API_KEY"],
        "docs_url": "https://github.com/upstash/context7",
        "local_only": False,
        "needs_node": True,
        "capabilities": ["CHAT", "CODING"],
    },
    {
        "id": "playwright",
        "label": "Playwright CLI / Browser MCP",
        "category": "Browser automation",
        "description": "Official Playwright MCP: lets the agent drive a real browser - navigate, click, type, screenshot, scrape.",
        "command": "npx",
        "args": ["-y", "@playwright/mcp@latest", "--headless", "--isolated"],
        "env": {},
        "required_env": [],
        "optional_env": [],
        "docs_url": "https://github.com/microsoft/playwright-mcp",
        "local_only": False,
        "needs_node": True,
        "capabilities": ["CHAT", "VISION"],
    },
    {
        "id": "playwright-cli",
        "label": "Playwright CLI (command line)",
        "category": "Browser automation",
        "description": "Drives the playwright CLI directly for scripted browser runs and recorded traces.",
        "command": "npx",
        "args": ["-y", "@playwright/cli@latest", "--help"],
        "env": {},
        "required_env": [],
        "optional_env": [],
        "docs_url": "https://playwright.dev/docs/cli",
        "local_only": False,
        "needs_node": True,
        "capabilities": ["CHAT"],
    },
    {
        "id": "supabase",
        "label": "Supabase (Postgres MCP)",
        "category": "Database",
        "description": "Official Supabase MCP: inspect schema, run SQL and query project data. Also the recommended way to give Mark-Imti a persistent database.",
        "command": "npx",
        "args": ["-y", "@supabase/mcp-server-postgres"],
        "env": {},
        "required_env": ["SUPABASE_DB_URL"],
        "optional_env": [],
        "docs_url": "https://github.com/supabase-community/supabase-mcp",
        "local_only": False,
        "needs_node": True,
        "capabilities": ["CHAT", "DATA"],
    },
    {
        "id": "supabase-management",
        "label": "Supabase Management API",
        "category": "Database",
        "description": "Project-level Supabase management: list projects, run SQL in the dashboard API, inspect logs.",
        "command": "npx",
        "args": ["-y", "@supabase/mcp-server-supabase"],
        "env": {},
        "required_env": ["SUPABASE_ACCESS_TOKEN", "SUPABASE_PROJECT_REF"],
        "optional_env": [],
        "docs_url": "https://github.com/supabase-community/supabase-mcp",
        "local_only": False,
        "needs_node": True,
        "capabilities": ["CHAT", "DATA"],
    },
    {
        "id": "strix",
        "label": "Strix Security",
        "category": "Security",
        "description": "Open-source autonomous AI penetration-testing agent. Scans a target and reports real findings.",
        "command": "uvx",
        "args": ["strix-agent", "--non-interactive"],
        "env": {},
        "required_env": ["STRIX_API_KEY"],
        "optional_env": ["STRIX_TARGET"],
        "docs_url": "https://github.com/usestrix/strix",
        "local_only": True,
        "needs_node": False,
        "capabilities": ["CHAT", "SECURITY"],
        "note": "Needs Docker and runs best from a local/desktop host.",
    },
    {
        "id": "filesystem",
        "label": "Filesystem",
        "category": "Files",
        "description": "Grants sandboxed read/write access to a chosen directory.",
        "command": "npx",
        # The filesystem server REQUIRES at least one directory argument;
        # without it the process exits immediately and no tools are advertised.
        "args": ["-y", "@modelcontextprotocol/server-filesystem", "/tmp/mark-imti-workspace"],
        "env": {},
        "required_env": [],
        "optional_env": [],
        "docs_url": "https://github.com/modelcontextprotocol/servers",
        "local_only": False,
        "needs_node": True,
        "capabilities": ["CHAT", "FILES"],
    },
    {
        "id": "memory",
        "label": "Memory",
        "category": "Knowledge",
        "description": "Reference MCP knowledge-graph server for durable notes Mark can read and write.",
        "command": "npx",
        "args": ["-y", "@modelcontextprotocol/server-memory"],
        "env": {},
        "required_env": [],
        "optional_env": [],
        "docs_url": "https://github.com/modelcontextprotocol/servers",
        "local_only": False,
        "needs_node": True,
        "capabilities": ["CHAT", "MEMORY"],
    },
]


def registry_entry(server_id: str) -> Dict[str, Any] | None:
    for r in MCP_REGISTRY:
        if r["id"] == server_id:
            return r
    return None
