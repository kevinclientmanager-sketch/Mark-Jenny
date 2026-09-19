"""Search GitHub for SKILL.md files."""
import asyncio
import httpx

async def search_skills():
    async with httpx.AsyncClient(timeout=15) as client:
        # Search for SKILL.md files
        r = await client.get(
            "https://api.github.com/search/code",
            params={"q": "filename:SKILL.md language:markdown", "per_page": 10},
            headers={"Accept": "application/vnd.github.v3+json"}
        )
        
        if r.status_code == 200:
            results = r.json()
            print(f"Total results: {results.get('total_count', 0)}")
            for item in results.get("items", [])[:10]:
                repo = item.get("repository", {}).get("full_name", "?")
                path = item.get("path", "?")
                print(f"  {repo}: {path}")
        else:
            print(f"Search failed: {r.status_code}")
            print(r.text[:200])

if __name__ == "__main__":
    asyncio.run(search_skills())
