"""Append-only audit trail (output/audit_trail.json) with redaction of keys and personal data."""
import fcntl
import json
import os
import re
import threading
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from .models import AgentEvent

_EMAIL = re.compile(r"[\w.+-]+@[\w-]+(\.[\w-]+)+")
_ORG_WORDS = {
    "yale", "club", "properties", "co", "inc", "llc", "society", "association",
    "team", "office", "department", "group", "center", "gifts", "print",
}
_lock = threading.Lock()


class AuditError(RuntimeError):
    pass


def name_variants(requester: str) -> set[str]:
    """Strings to scrub from the audit trail: a person's name and first name (not organizations)."""
    requester = (requester or "").strip()
    if len(requester) < 3:
        return set()
    words = requester.split()
    if any(w.lower().strip(".,") in _ORG_WORDS for w in words):
        return set()  # a business or club name is not personal data
    out = {requester}
    if len(words) == 2:
        out.add(words[0])
    return out


def now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="milliseconds")


class AuditTrail:
    def __init__(self, path: Path, secrets: list[str] | None = None):
        self.path = Path(path)
        self.secrets = [s for s in (secrets or []) if s]

    def scrub(self, value: Any, redactions: set[str] | None = None, limit: int = 240) -> str:
        """Short, safe text for an audit field: no keys, emails or known personal names."""
        text = value if isinstance(value, str) else json.dumps(value, default=str, ensure_ascii=False)
        for secret in self.secrets:
            text = text.replace(secret, "[key]")
        text = _EMAIL.sub("[email]", text)
        for name in sorted(redactions or (), key=len, reverse=True):
            text = re.sub(re.escape(name), "[requester]", text, flags=re.IGNORECASE)
        text = " ".join(text.split())
        return text if len(text) <= limit else text[: limit - 1] + "…"

    def append(self, event: AgentEvent) -> None:
        """Add one entry. Never wipes the file: unreadable existing content raises instead."""
        entry = event.model_dump()
        with _lock:
            self.path.parent.mkdir(parents=True, exist_ok=True)
            fd = os.open(self.path, os.O_RDWR | os.O_CREAT, 0o644)
            with os.fdopen(fd, "r+", encoding="utf-8") as f:
                fcntl.flock(f, fcntl.LOCK_EX)
                raw = f.read()
                try:
                    entries = json.loads(raw) if raw.strip() else []
                except json.JSONDecodeError as exc:
                    raise AuditError(f"{self.path} is not valid JSON; refusing to overwrite it.") from exc
                if not isinstance(entries, list):
                    raise AuditError(f"{self.path} is not a JSON list; refusing to overwrite it.")
                entries.append(entry)
                payload = json.dumps(entries, indent=2, ensure_ascii=False) + "\n"
                f.seek(0)
                f.truncate()
                f.write(payload)
                f.flush()
                os.fsync(f.fileno())

    def read_run(self, run_id: str) -> list[dict]:
        """All entries recorded for one run_id, in order. Reads under a shared lock."""
        with _lock:
            if not self.path.exists():
                return []
            with open(self.path, "r", encoding="utf-8") as f:
                fcntl.flock(f, fcntl.LOCK_SH)
                raw = f.read()
        if not raw.strip():
            return []
        try:
            entries = json.loads(raw)
        except json.JSONDecodeError as exc:
            raise AuditError(f"{self.path} is not valid JSON.") from exc
        return [e for e in entries if e.get("run_id") == run_id]
