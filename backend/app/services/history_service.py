import logging
import sqlite3
import threading
from datetime import datetime, timezone
from pathlib import Path

DATA = Path(__file__).resolve().parents[2] / "data"
DB = DATA / "history.db"
_lock = threading.Lock()

DATA.mkdir(exist_ok=True)
audit = logging.getLogger("audit")
if not audit.handlers:
    h = logging.FileHandler(DATA / "audit.log", encoding="utf-8")
    h.setFormatter(logging.Formatter("%(asctime)s %(message)s"))
    audit.addHandler(h)
    audit.setLevel(logging.INFO)


def _conn():
    c = sqlite3.connect(DB)
    c.row_factory = sqlite3.Row
    return c


def init():
    with _lock, _conn() as c:
        c.execute("""CREATE TABLE IF NOT EXISTS queries (
            id INTEGER PRIMARY KEY AUTOINCREMENT, request TEXT, sql TEXT, database TEXT,
            status TEXT, executed_at TEXT, duration_ms INTEGER, affected_rows INTEGER, error TEXT)""")


def add(request, sql, database, status, duration_ms=None, affected_rows=None, error=None, role=""):
    with _lock, _conn() as c:
        c.execute("INSERT INTO queries (request, sql, database, status, executed_at, duration_ms, affected_rows, error) "
                  "VALUES (?,?,?,?,?,?,?,?)",
                  (request, sql, database, status, datetime.now(timezone.utc).isoformat(timespec="seconds"),
                   duration_ms, affected_rows, error))
    one_line = " ".join((sql or "").split())[:300]
    audit.info("role=%s db=%s status=%s sql=%s error=%s", role, database, status, one_line, (error or "")[:150])


def list_history(limit=50):
    with _lock, _conn() as c:
        return [dict(r) for r in c.execute("SELECT * FROM queries ORDER BY id DESC LIMIT ?", (limit,))]


def get(query_id: int):
    with _lock, _conn() as c:
        r = c.execute("SELECT * FROM queries WHERE id=?", (query_id,)).fetchone()
    return dict(r) if r else None


def stats():
    with _lock, _conn() as c:
        rows = c.execute("SELECT status, COUNT(*) n FROM queries GROUP BY status").fetchall()
    by = {r["status"]: r["n"] for r in rows}
    return {"total": sum(by.values()), "success": by.get("success", 0),
            "failed": by.get("error", 0), "rejected": by.get("rejected", 0)}
