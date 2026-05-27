import os
import threading
import httpx

_SUPABASE_URL = os.environ.get("SUPABASE_URL", "")
_SUPABASE_KEY = os.environ.get("SUPABASE_SERVICE_KEY", "")


def _insert(session_id: str, role: str, content: str):
    if not _SUPABASE_URL or not _SUPABASE_KEY:
        return
    try:
        httpx.post(
            f"{_SUPABASE_URL}/rest/v1/chat_logs",
            headers={
                "apikey": _SUPABASE_KEY,
                "Authorization": f"Bearer {_SUPABASE_KEY}",
                "Content-Type": "application/json",
                "Prefer": "return=minimal",
            },
            json={"session_id": session_id or "unknown", "role": role, "content": content},
            timeout=5.0,
        )
    except Exception:
        pass  # never let logging break the chat


def log(session_id: str, role: str, content: str):
    threading.Thread(target=_insert, args=(session_id, role, content), daemon=True).start()
