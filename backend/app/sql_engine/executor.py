import datetime
import decimal
import re
import time

from app.core.config import settings

FRIENDLY = {
    1146: "That table does not exist. Check the table name in the explorer.",
    1054: "A column in the query does not exist in that table.",
    1062: "Duplicate value: a row with the same primary/unique key already exists.",
    1451: "This row is still referenced by other tables (foreign key), so it cannot be deleted or changed.",
    1452: "The referenced parent row does not exist (foreign key), so this row cannot be added or changed.",
    1064: "The SQL has a syntax error.",
    1366: "A value does not match the column's data type.",
    1406: "A value is too long for its column.",
    1048: "A required column cannot be empty (NULL).",
    1364: "A required column has no value and no default.",
    1045: "Access denied: wrong MySQL username or password.",
    1044: "Your MySQL user has no permission on this database.",
    1142: "Your MySQL user has no permission for this operation.",
    1050: "A table with that name already exists.",
    1007: "A database with that name already exists.",
    1060: "A column with that name already exists.",
    1061: "An index with that name already exists.",
    1091: "You tried to drop something that does not exist.",
    3024: "The query ran too long and was stopped (timeout).",
    1317: "The query was interrupted.",
    2003: "Cannot reach the MySQL server.",
    2006: "The MySQL connection was lost.",
    2013: "The query timed out or the connection was lost.",
}


def explain_error(exc: Exception) -> dict:
    args = getattr(exc, "args", ())
    code = args[0] if args and isinstance(args[0], int) else None
    raw = str(args[1]) if len(args) > 1 else str(exc)
    return {"code": code, "message": FRIENDLY.get(code, "MySQL rejected this statement."), "detail": raw[:300]}


def _ser(v):
    if v is None or isinstance(v, (str, int, float, bool)):
        return v
    if isinstance(v, decimal.Decimal):
        return float(v)
    if isinstance(v, datetime.datetime):
        return v.isoformat(sep=" ")
    if isinstance(v, (datetime.date, datetime.time)):
        return v.isoformat()
    if isinstance(v, (bytes, bytearray)):
        try:
            return bytes(v).decode("utf-8")
        except UnicodeDecodeError:
            return "0x" + bytes(v)[:16].hex()
    return str(v)


def run(engine, sql: str, max_rows: int | None = None) -> dict:
    """Execute one statement in its own transaction (commit on success, rollback on error).
    A raw DBAPI cursor is used so '%' in LIKE patterns is never treated as a placeholder."""
    max_rows = max_rows or settings.max_rows
    start = time.perf_counter()
    raw = engine.raw_connection()
    out = {"columns": [], "rows": [], "row_count": 0, "truncated": False, "affected_rows": 0}
    try:
        cur = raw.cursor()
        cur.execute(sql)
        if cur.description:
            rows = cur.fetchmany(max_rows + 1)
            out["truncated"] = len(rows) > max_rows
            rows = rows[:max_rows]
            out["columns"] = [d[0] for d in cur.description]
            out["rows"] = [[_ser(v) for v in r] for r in rows]
            out["row_count"] = len(rows)
        else:
            out["affected_rows"] = cur.rowcount
        raw.commit()
        cur.close()
    except Exception:
        try:
            raw.rollback()
        except Exception:
            pass
        raise
    finally:
        raw.close()
    out["duration_ms"] = round((time.perf_counter() - start) * 1000)
    return out


def preview(engine, sql: str) -> dict | None:
    """Show which rows an UPDATE/DELETE would touch, without changing anything."""
    s = sql.strip().rstrip(";").strip()
    m = (re.match(r"(?is)^DELETE\s+FROM\s+(\S+)\s+WHERE\s+(.+)$", s)
         or re.match(r"(?is)^UPDATE\s+(\S+)\s+SET\s+.+?\s+WHERE\s+(.+)$", s))
    if not m:
        return None
    table = m.group(1)
    where = re.sub(r"(?is)\s+(ORDER\s+BY\s+.+|LIMIT\s+\d+)\s*$", "", m.group(2))
    count = run(engine, f"SELECT COUNT(*) FROM {table} WHERE {where}")
    sample = run(engine, f"SELECT * FROM {table} WHERE {where} LIMIT 20")
    return {"affected_estimate": count["rows"][0][0], "columns": sample["columns"], "rows": sample["rows"]}
