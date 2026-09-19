import sqlite3, json
from datetime import datetime, timedelta, timezone

db = sqlite3.connect(r"C:\Users\LAP TECH\Music\Mark\mark-jenny\backend\mark_jenny.db")
c = db.cursor()

row = c.execute("select id from users where email = ?", ("kevin.clientmanager@gmail.com",)).fetchone()
owner = row[0] if row else None
print("kevin id:", owner)
if owner is None:
    db.close()
    raise SystemExit("no kevin")

def ts(seconds):
    return (datetime.now(timezone.utc) + timedelta(seconds=seconds)).isoformat()

c.execute("delete from chats where title = ?", ("Demo - Show me",))
c.execute(
    "insert into chats (title, owner_id, task_id, created_at, updated_at) values (?, ?, ?, ?, ?)",
    ("Demo - Show me", owner, 42, ts(-120), ts(0)),
)
chat_id = c.lastrowid

msgs = [
    ("USER", "Build me a landing page for my coffee shop with a menu section.", None, None, ts(-119)),
    ("ASSISTANT", "Here's the coffee shop landing page plan:\n\n## Sections\n1. Hero with shop name and tagline\n2. Menu with prices\n3. About us\n4. Contact & hours\n\nI'll scaffold the Next.js app, style it with Tailwind, and run it for you. Open the Agent panel to watch the steps live.", None, json.dumps({"task_id": 42}), ts(-60)),
    ("TOOL", "Executed `npx create-next-app coffee-shop` — project scaffold created.\nCreated: hero.tsx, menu.tsx, about.tsx, contact.tsx\nPreview available at /coffee-shop", None, None, ts(-30)),
    ("ASSISTANT", "Done! Your **coffee shop landing page** is live:\n\n- [x] Hero + tagline\n- [x] Menu with prices\n- [x] About & contact\n- [x] Tailwind styling\n\nPinned it to **Projects** so it's easy to keep building.", None, json.dumps({"task_id": 42}), ts(0)),
]
for role, content, tool_calls, meta, created in msgs:
    c.execute(
        "insert into messages (chat_id, role, content, tool_calls, message_metadata, created_at) values (?, ?, ?, ?, ?, ?)",
        (chat_id, role, content, tool_calls, meta, created),
    )
db.commit()
print("seeded chat_id:", chat_id)
db.close()