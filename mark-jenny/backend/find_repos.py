"""Find actual skill repo structures."""
import asyncio
import httpx
import json

REPOS_TO_CHECK = [
    ("eastlondoner", "claude-code"),
    ("anthropics", "claude-code"),
    ("anthropics", "claude-code-samples"),
    ("eastlondoner", "claude-code-examples"),
    ("eastlondoner", "claude-code-tools"),
    ("eastlondoner", "claude-code-plugins"),
    ("eastlondoner", "claude-code-extensions"),
    ("eastlondoner", "claude-code-libraries"),
]

async def find_skill_dirs(owner, repo):
    """Recursively find SKILL.md files in a repo."""
    skills = []
    
    async def scan_path(path=""):
        async with httpx.AsyncClient(timeout=15) as client:
            url = f"https://api.github.com/repos/{owner}/{repo}/contents/{path}" if path else f"https://api.github.com/repos/{owner}/{repo}/contents/"
            r = await client.get(url, headers={"Accept": "application/vnd.github.v3+json"})
            if r.status_code != 200:
                return
            
            items = r.json()
            if not isinstance(items, list):
                return
            
            for item in items:
                name = item.get("name", "")
                item_type = item.get("type", "")
                item_path = item.get("path", "")
                
                if item_type == "file" and name.endswith(".md") and "skill" in name.lower():
                    skills.append(item_path)
                
                if item_type == "dir" and not name.startswith("."):
                    # Only scan one level deep to avoid too many requests
                    if path.count("/") < 2:
                        await scan_path(item_path)
    
    await scan_path()
    return skills

async def main():
    for owner, repo in REPOS_TO_CHECK:
        print(f"\n=== {owner}/{repo} ===")
        try:
            async with httpx.AsyncClient(timeout=15) as client:
                r = await client.get(f"https://api.github.com/repos/{owner}/{repo}", headers={"Accept": "application/vnd.github.v3+json"})
                if r.status_code != 200:
                    print(f"  Repo not found (status {r.status_code})")
                    continue
                
                info = r.json()
                print(f"  Stars: {info.get('stargazers_count', 0)}")
                print(f"  Description: {info.get('description', 'N/A')[:80]}")
                
                # Scan for skill files
                skills = await find_skill_dirs(owner, repo)
                if skills:
                    print(f"  Skill files found: {len(skills)}")
                    for s in skills[:5]:
                        print(f"    {s}")
                else:
                    print("  No skill files found")
        except Exception as e:
            print(f"  Error: {e}")

if __name__ == "__main__":
    asyncio.run(main())
