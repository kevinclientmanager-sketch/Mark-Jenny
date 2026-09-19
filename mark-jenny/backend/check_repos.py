"""Check specific repos for skills."""
import asyncio
import httpx

async def check_repo(owner, repo):
    async with httpx.AsyncClient(timeout=10) as client:
        r = await client.get(f"https://api.github.com/repos/{owner}/{repo}", headers={"Accept": "application/vnd.github.v3+json"})
        if r.status_code != 200:
            return None
        info = r.json()
        return {
            "owner": owner,
            "repo": repo,
            "stars": info.get("stargazers_count", 0),
            "description": info.get("description", ""),
        }

async def main():
    repos = [
        ("eastlondoner", "claude-code"),
        ("eastlondoner", "claude-code-examples"),
        ("eastlondoner", "claude-code-tools"),
        ("anthropics", "claude-code"),
    ]
    
    for owner, repo in repos:
        info = await check_repo(owner, repo)
        if info:
            print(f"{owner}/{repo}: {info['stars']} stars - {info['description'][:60]}")
        else:
            print(f"{owner}/{repo}: NOT FOUND")

if __name__ == "__main__":
    asyncio.run(main())
