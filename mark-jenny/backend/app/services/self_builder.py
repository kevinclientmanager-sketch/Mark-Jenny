"""
Self-Builder Service — Mark-Imti's ability to browse GitHub, discover skills, and install them.

This is the core self-improvement loop:
1. Search GitHub for skill repos (SKILL.md files)
2. Parse and validate the skill definitions
3. Install them into the local skills registry
4. Wire them to agents based on relevance

Inspired by how Everything Claude Code (292 skills) and Claudex (162 skills) were discovered and installed.
"""
import re
import json
import httpx
from typing import List, Dict, Optional, Tuple
from dataclasses import dataclass


@dataclass
class DiscoveredSkill:
    name: str
    display_name: str
    description: str
    source_repo: str
    source_url: str
    content: str  # raw SKILL.md content
    tools: List[str]
    category: str
    origin: str  # "ECC", "ClaudeX", "custom", etc.


# Well-known skill repositories to scan
# These are repos known to contain SKILL.md files or similar skill definitions
KNOWN_SKILL_REPOS = [
    {"owner": "eastlondoner", "repo": "claude-code", "path": "skills", "origin": "ECC"},
    {"owner": "eastlondoner", "repo": "claude-code", "path": ".claude/skills", "origin": "ECC"},
    {"owner": "anthropics", "repo": "claude-code", "path": "skills", "origin": "Anthropic"},
    {"owner": "anthropics", "repo": "claude-code", "path": ".claude/skills", "origin": "Anthropic"},
    {"owner": "eastlondoner", "repo": "claude-code-samples", "path": "skills", "origin": "Samples"},
    {"owner": "eastlondoner", "repo": "claude-code-examples", "path": "skills", "origin": "Examples"},
    {"owner": "eastlondoner", "repo": "claude-code-tools", "path": "skills", "origin": "Tools"},
]


async def search_github_code(query: str, per_page: int = 20) -> List[Dict]:
    """Search GitHub code for SKILL.md files matching a query.
    Note: Code search requires authentication. Falls back to repo search."""
    # Try code search first (requires auth, may fail)
    url = f"https://api.github.com/search/code?q={query}+filename:SKILL.md&per_page={per_page}"
    headers = {"Accept": "application/vnd.github.v3+json"}
    async with httpx.AsyncClient(timeout=15) as client:
        try:
            r = await client.get(url, headers=headers)
            if r.status_code == 200:
                return r.json().get("items", [])
        except Exception:
            pass
    
    # Fall back to searching for repos with skills in the name
    url2 = f"https://api.github.com/search/repositories?q={query}+skills+SKILL.md&per_page={per_page}&sort=stars"
    async with httpx.AsyncClient(timeout=15) as client:
        try:
            r = await client.get(url2, headers=headers)
            if r.status_code == 200:
                return r.json().get("items", [])
        except Exception:
            pass
    
    return []


async def search_github_repos(query: str, per_page: int = 10) -> List[Dict]:
    """Search GitHub for repositories containing skills."""
    url = f"https://api.github.com/search/repositories?q={query}+skills+in:name,description&per_page={per_page}&sort=stars"
    headers = {"Accept": "application/vnd.github.v3+json"}
    async with httpx.AsyncClient(timeout=15) as client:
        try:
            r = await client.get(url, headers=headers)
            r.raise_for_status()
            return r.json().get("items", [])
        except Exception:
            return []


async def fetch_github_tree(owner: str, repo: str, path: str = "") -> List[Dict]:
    """Fetch directory listing from a GitHub repo."""
    url = f"https://api.github.com/repos/{owner}/{repo}/contents/{path}"
    headers = {"Accept": "application/vnd.github.v3+json"}
    async with httpx.AsyncClient(timeout=15) as client:
        try:
            r = await client.get(url, headers=headers)
            r.raise_for_status()
            return r.json() if isinstance(r.json(), list) else []
        except Exception:
            return []


async def fetch_raw_file(url: str) -> Optional[str]:
    """Fetch a raw file from GitHub."""
    if "github.com" in url and "/blob/" in url:
        url = url.replace("github.com", "raw.githubusercontent.com").replace("/blob/", "/")
    async with httpx.AsyncClient(timeout=15) as client:
        try:
            r = await client.get(url)
            r.raise_for_status()
            return r.text
        except Exception:
            return None


def parse_skill_md(content: str, source_url: str, origin: str = "custom") -> Optional[DiscoveredSkill]:
    """Parse a SKILL.md file into a DiscoveredSkill."""
    # Extract frontmatter
    fm_match = re.match(r'^---\n(.*?)\n---', content, re.DOTALL)
    if not fm_match:
        return None

    fm_text = fm_match.group(1)
    fm = {}
    for line in fm_text.split('\n'):
        if ':' in line:
            key, val = line.split(':', 1)
            fm[key.strip()] = val.strip().strip('"').strip("'")

    name = fm.get('name', '')
    if not name:
        return None

    description = fm.get('description', '')
    # Extract tools from description or content
    tools = []
    tool_patterns = [
        r'tools?:\s*([^\n]+)',
        r'uses?:\s*([^\n]+)',
        r'capabilities?:\s*([^\n]+)',
    ]
    for pat in tool_patterns:
        m = re.search(pat, content, re.IGNORECASE)
        if m:
            tools.extend([t.strip() for t in re.split(r'[,\s]+', m.group(1)) if t.strip()])

    # Deduplicate and limit
    tools = list(dict.fromkeys(tools))[:10]

    # Determine category from tools/description
    category = "general"
    cat_keywords = {
        "code": ["code", "python", "javascript", "typescript", "react", "fastapi", "debug"],
        "research": ["research", "search", "analyze", "investigate"],
        "design": ["design", "ui", "css", "component", "layout"],
        "security": ["security", "audit", "vulnerability", "auth"],
        "devops": ["deploy", "ci/cd", "docker", "kubernetes", "pipeline"],
        "data": ["data", "database", "sql", "csv", "spreadsheet"],
    }
    desc_lower = (description + " " + content[:500]).lower()
    for cat, keywords in cat_keywords.items():
        if any(k in desc_lower for k in keywords):
            category = cat
            break

    return DiscoveredSkill(
        name=name,
        display_name=fm.get('display_name', name.replace('-', ' ').title()),
        description=description[:200],
        source_url=source_url,
        source_repo=source_url.split('github.com/')[-1] if 'github.com' in source_url else '',
        content=content,
        tools=tools,
        category=category,
        origin=origin,
    )


async def discover_skills_from_repo(owner: str, repo: str, path: str = "skills", origin: str = "custom") -> List[DiscoveredSkill]:
    """Scan a GitHub repo for SKILL.md files and parse them."""
    skills = []

    # Get directory listing
    items = await fetch_github_tree(owner, repo, path)

    for item in items:
        if item.get("type") == "file" and item.get("name", "").endswith(".md"):
            # It's a skill file
            raw_url = item.get("download_url") or item.get("url", "")
            if raw_url:
                content = await fetch_raw_file(raw_url)
                if content:
                    parsed = parse_skill_md(content, item.get("html_url", raw_url), origin)
                    if parsed:
                        skills.append(parsed)

        elif item.get("type") == "dir":
            # Recurse into subdirectory (one level deep)
            sub_items = await fetch_github_tree(owner, repo, f"{path}/{item['name']}")
            for sub_item in sub_items:
                if sub_item.get("type") == "file" and sub_item.get("name", "").endswith(".md"):
                    raw_url = sub_item.get("download_url") or sub_item.get("url", "")
                    if raw_url:
                        content = await fetch_raw_file(raw_url)
                        if content:
                            parsed = parse_skill_md(content, sub_item.get("html_url", raw_url), origin)
                            if parsed:
                                skills.append(parsed)

    return skills


async def discover_from_known_repos() -> List[DiscoveredSkill]:
    """Scan all known skill repositories."""
    all_skills = []
    for repo_info in KNOWN_SKILL_REPOS:
        skills = await discover_skills_from_repo(
            repo_info["owner"],
            repo_info["repo"],
            repo_info.get("path", "skills"),
            repo_info.get("origin", "custom"),
        )
        all_skills.extend(skills)
    return all_skills


async def discover_from_url(url: str) -> List[DiscoveredSkill]:
    """Discover skills from a GitHub URL (repo, folder, or raw file)."""
    # Parse the URL
    if "github.com" not in url:
        return []

    # Handle raw.githubusercontent.com URLs
    if "raw.githubusercontent.com" in url:
        content = await fetch_raw_file(url)
        if content:
            parsed = parse_skill_md(content, url, "custom")
            return [parsed] if parsed else []
        return []

    # Extract owner/repo/path from github.com URL
    parts = url.replace("https://github.com/", "").strip("/").split("/")
    if len(parts) < 2:
        return []

    owner, repo = parts[0], parts[1]
    path = "/".join(parts[2:]) if len(parts) > 2 else "skills"

    return await discover_skills_from_repo(owner, repo, path, "custom")


async def search_and_discover(query: str) -> Tuple[List[DiscoveredSkill], List[Dict]]:
    """Search GitHub for skills and discover repos."""
    # Search for repos with skills in the name/description
    repo_results = await search_github_repos(f"{query} claude skills")
    
    skills = []
    seen_repos = set()
    
    # Try to scan each repo found
    for repo_info in repo_results[:5]:  # Limit to top 5 repos
        full_name = repo_info.get("full_name", "")
        if full_name and full_name not in seen_repos:
            seen_repos.add(full_name)
            owner, repo = full_name.split("/") if "/" in full_name else ("", "")
            if owner and repo:
                # Try multiple common paths for skills
                for path in ["skills", ".claude/skills", "prompts", ".prompts"]:
                    found = await discover_skills_from_repo(owner, repo, path, "community")
                    skills.extend(found)

    return skills, repo_results


async def discover_from_raw_urls(urls: List[str]) -> List[DiscoveredSkill]:
    """Discover skills from a list of raw URLs."""
    skills = []
    for url in urls:
        content = await fetch_raw_file(url)
        if content:
            parsed = parse_skill_md(content, url, "custom")
            if parsed:
                skills.append(parsed)
    return skills


async def discover_from_local_files(file_paths: List[str]) -> List[DiscoveredSkill]:
    """Discover skills from local file paths (for batch import)."""
    skills = []
    for path in file_paths:
        try:
            with open(path, 'r', encoding='utf-8') as f:
                content = f.read()
            parsed = parse_skill_md(content, f"file://{path}", "local")
            if parsed:
                skills.append(parsed)
        except Exception:
            continue
    return skills
