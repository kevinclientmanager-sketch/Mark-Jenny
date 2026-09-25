"""Debug GitHub API responses."""
import asyncio
import httpx
import json
import sys
sys.path.insert(0, r"C:\Users\LAP TECH\Music\Mark\MARK-IMTI\backend")

async def test():
    # Test 1: Check if we can access the repo
    print("=== Test 1: Access repo root ===")
    async with httpx.AsyncClient(timeout=15) as client:
        r = await client.get("https://api.github.com/repos/eastlondoner/claude-code/contents/")
        print(f"Status: {r.status_code}")
        if r.status_code == 200:
            items = r.json()
            print(f"Root items: {len(items)}")
            for item in items[:10]:
                print(f"  {item.get('name', '?')} - {item.get('type', '?')}")
        else:
            print(f"Response: {r.text[:200]}")

    # Test 2: Check skills directory
    print("\n=== Test 2: Check skills directory ===")
    async with httpx.AsyncClient(timeout=15) as client:
        r = await client.get("https://api.github.com/repos/eastlondoner/claude-code/contents/skills")
        print(f"Status: {r.status_code}")
        if r.status_code == 200:
            items = r.json()
            if isinstance(items, list):
                print(f"Skills items: {len(items)}")
                for item in items[:10]:
                    print(f"  {item.get('name', '?')} - {item.get('type', '?')}")
            else:
                print(f"Not a list: {json.dumps(items)[:200]}")
        else:
            print(f"Response: {r.text[:200]}")

    # Test 3: Check .claude/skills directory
    print("\n=== Test 3: Check .claude/skills directory ===")
    async with httpx.AsyncClient(timeout=15) as client:
        r = await client.get("https://api.github.com/repos/eastlondoner/claude-code/contents/.claude/skills")
        print(f"Status: {r.status_code}")
        if r.status_code == 200:
            items = r.json()
            if isinstance(items, list):
                print(f".claude/skills items: {len(items)}")
                for item in items[:10]:
                    print(f"  {item.get('name', '?')} - {item.get('type', '?')}")
            else:
                print(f"Not a list: {json.dumps(items)[:200]}")
        else:
            print(f"Response: {r.text[:200]}")

    # Test 4: Try a known SKILL.md file
    print("\n=== Test 4: Try fetching a SKILL.md file ===")
    async with httpx.AsyncClient(timeout=15) as client:
        # Try raw.githubusercontent.com
        r = await client.get("https://raw.githubusercontent.com/eastlondoner/claude-code/main/skills/README.md")
        print(f"Status: {r.status_code}")
        if r.status_code == 200:
            print(f"Content length: {len(r.text)}")
            print(f"First 200 chars: {r.text[:200]}")
        else:
            print(f"Response: {r.text[:200]}")

    # Test 5: Check another repo
    print("\n=== Test 5: Check anthropics/claude-code-samples ===")
    async with httpx.AsyncClient(timeout=15) as client:
        r = await client.get("https://api.github.com/repos/anthropics/claude-code-samples/contents/")
        print(f"Status: {r.status_code}")
        if r.status_code == 200:
            items = r.json()
            print(f"Root items: {len(items)}")
            for item in items[:10]:
                print(f"  {item.get('name', '?')} - {item.get('type', '?')}")
        else:
            print(f"Response: {r.text[:200]}")

if __name__ == "__main__":
    asyncio.run(test())
