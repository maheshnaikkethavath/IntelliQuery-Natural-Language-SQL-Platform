import re
import threading

from sqlalchemy import inspect, text

from app.database.connection import manager

SYSTEM_DBS = {"information_schema", "mysql", "performance_schema", "sys"}
_cache: dict = {"key": None, "schema": None}
_lock = threading.Lock()


def list_databases(engine) -> list[str]:
    with engine.connect() as conn:
        rows = conn.execute(text("SHOW DATABASES")).fetchall()
    return [r[0] for r in rows if r[0].lower() not in SYSTEM_DBS]


def invalidate():
    with _lock:
        _cache.update(key=None, schema=None)


def _type(col_type, engine) -> str:
    try:
        return col_type.compile(dialect=engine.dialect)
    except Exception:
        return str(col_type)


def discover(engine) -> dict:
    with engine.connect() as conn:
        db = conn.execute(text("SELECT DATABASE()")).scalar()
        if not db:
            return {"database": None, "tables": [], "relationships": []}
        meta = conn.execute(text(
            "SELECT TABLE_NAME, TABLE_TYPE, TABLE_ROWS FROM information_schema.tables "
            "WHERE TABLE_SCHEMA = DATABASE() ORDER BY TABLE_NAME")).fetchall()

    insp = inspect(engine)
    tables, rels = [], []
    for name, ttype, nrows in meta:
        try:
            is_view = ttype == "VIEW"
            pk = set(insp.get_pk_constraint(name).get("constrained_columns") or [])
            fks = [] if is_view else insp.get_foreign_keys(name)
            cols_raw = insp.get_columns(name)
        except Exception:
            continue
        fkmap = {}
        for fk in fks:
            for col, rcol in zip(fk["constrained_columns"], fk["referred_columns"]):
                fkmap[col] = f"{fk['referred_table']}.{rcol}"
                rels.append({"from": f"{name}.{col}", "to": f"{fk['referred_table']}.{rcol}"})
        cols = [{"name": c["name"], "type": _type(c["type"], engine),
                 "nullable": bool(c.get("nullable", True)),
                 "pk": c["name"] in pk, "fk": fkmap.get(c["name"])} for c in cols_raw]
        tables.append({"name": name, "is_view": is_view,
                       "rows": int(nrows) if nrows is not None and not is_view else None,
                       "columns": cols})
    return {"database": db, "tables": tables, "relationships": rels}


def get_schema(engine, refresh: bool = False):
    key = (manager.info.get("host"), manager.info.get("database"))
    with _lock:
        if not refresh and _cache["key"] == key and _cache["schema"]:
            return _cache["schema"], True
    schema = discover(engine)
    with _lock:
        _cache.update(key=key, schema=schema)
    return schema, False


def schema_text(schema: dict, request: str = "", limit: int = 40) -> str:
    """Compact schema description for the LLM (no data, no credentials)."""
    tables = schema["tables"]
    if len(tables) > limit:
        words = set(re.findall(r"\w+", request.lower()))

        def score(t):
            names = [t["name"].lower()] + [c["name"].lower() for c in t["columns"]]
            return sum(1 for w in words for n in names if w == n or w.rstrip("s") == n.rstrip("s"))
        tables = sorted(tables, key=score, reverse=True)[:limit]
    lines = [f"Current database: {schema['database']}"]
    for t in tables:
        cols = ", ".join(
            f"{c['name']} {c['type']}" + (" PK" if c["pk"] else "") + (f" FK->{c['fk']}" if c["fk"] else "")
            for c in t["columns"])
        kind = "View" if t["is_view"] else "Table"
        approx = f" (~{t['rows']} rows)" if t["rows"] is not None else ""
        lines.append(f"{kind} {t['name']}{approx}: {cols}")
    if len(schema["tables"]) > len(tables):
        lines.append("Other tables: " + ", ".join(t["name"] for t in schema["tables"] if t not in tables))
    return "\n".join(lines)
