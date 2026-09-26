"""Real mailbox reading for Mail Mark.

Uses the stored connector credential to read an IMAP mailbox. No fabricated
messages: if the credential cannot be used, the caller gets an explicit error.
"""
import base64
import email
import imaplib
from typing import Any, Dict, List, Optional


def _decrypt(blob: Optional[str]) -> str:
    if not blob:
        return ""
    try:
        from app.services.credential_vault import credential_vault
        return credential_vault.decrypt(blob)
    except Exception:
        try:
            return base64.b64decode(blob).decode()
        except Exception:
            return ""


def _credential_dict(cred) -> Dict[str, Any]:
    raw = getattr(cred, "credentials", None) or {}
    if isinstance(raw, str):
        import json
        try:
            raw = json.loads(raw)
        except Exception:
            raw = {}
    return {k: _decrypt(v) if k in {"password", "access_token", "refresh_token", "client_secret"} else v
            for k, v in (raw or {}).items()}


async def fetch_inbox(cred, limit: int = 20) -> List[Dict[str, Any]]:
    """Fetch the most recent messages from a connected IMAP mailbox."""
    conf = _credential_dict(cred)
    host = conf.get("imap_host") or "imap.gmail.com"
    port = int(conf.get("imap_port") or 993)
    user = conf.get("email") or conf.get("username") or ""
    password = conf.get("password") or conf.get("access_token") or ""
    if not user or not password:
        raise RuntimeError("Connected mailbox is missing its username or password")

    loop = imaplib.IMAP4_SSL(host, port)
    try:
        loop.login(user, password)
        loop.select("INBOX", readonly=True)
        typ, data = loop.search(None, "ALL")
        if typ != "OK":
            raise RuntimeError("Mailbox search failed")
        ids = data[0].split()[-limit:][::-1]
        out: List[Dict[str, Any]] = []
        for mid in ids:
            typ, msg_data = loop.fetch(mid, "(RFC822)")
            if typ != "OK" or not msg_data or not msg_data[0]:
                continue
            msg = email.message_from_bytes(msg_data[0][1])
            body = ""
            if msg.is_multipart():
                for part in msg.walk():
                    if part.get_content_type() == "text/plain":
                        payload = part.get_payload(decode=True) or b""
                        body = payload.decode("utf-8", "ignore")
                        break
            else:
                payload = msg.get_payload(decode=True) or b""
                body = payload.decode("utf-8", "ignore")
            out.append({
                "id": int(mid),
                "from": msg.get("From", ""),
                "subject": msg.get("Subject", ""),
                "date": msg.get("Date", ""),
                "snippet": body[:280],
                "body": body[:8000],
            })
        loop.close()
        return out
    finally:
        try:
            loop.close()
        except Exception:
            pass
