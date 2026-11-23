"""Application-level SQL gatekeeper. The LLM can never bypass this."""
import re

import sqlparse
from sqlparse import tokens as T

READ = {"SELECT", "SHOW", "DESCRIBE", "DESC", "EXPLAIN", "WITH"}
DML = {"INSERT", "UPDATE", "DELETE", "REPLACE"}
DDL = {"CREATE", "ALTER", "DROP", "TRUNCATE", "RENAME"}
RANK = {"readonly": 0, "write": 1, "admin": 2}

BLOCKED = re.compile(
    r"\b(?:GRANT|REVOKE|LOAD_FILE|SHUTDOWN|FLUSH|KILL)\b|\bLOAD\s+DATA\b|\bINTO\s+(?:OUTFILE|DUMPFILE)\b"
    r"|\b(?:SLEEP|BENCHMARK)\s*\(|\bSET\s+GLOBAL\b|\b(?:CREATE|DROP|ALTER)\s+USER\b", re.I)
SYSTEM_REF = re.compile(r"`?\b(?:mysql|sys|information_schema|performance_schema)\b`?\s*\.", re.I)
STRINGS = re.compile(r"'(?:[^'\\]|\\.|'')*'|\"(?:[^\"\\]|\\.)*\"")
TARGET = re.compile(
    r"(?:\bTABLE|\bDATABASE|\bSCHEMA|\bVIEW|\bINTO|\bUPDATE|\bFROM|\bON)\s+(?:IF\s+(?:NOT\s+)?EXISTS\s+)?"
    r"(`[^`]+`(?:\.`[^`]+`)?|[\w$]+(?:\.[\w$]+)?)", re.I)
TAUTOLOGY = re.compile(r"\bWHERE\s+\(?\s*(?:1\s*=\s*1|TRUE|''\s*=\s*'')\s*\)?\s*$", re.I)


def _operation(first: str, clean: str) -> str:
    if first in ("SELECT", "WITH"):
        return "SELECT"
    if first == "TRUNCATE":
        return "TRUNCATE TABLE"
    if first in ("SHOW", "DESCRIBE", "DESC", "EXPLAIN"):
        m = re.match(r"\s*\w+\s+(\w+)", clean)
        return f"SHOW {m.group(1).upper()}" if first == "SHOW" and m else first
    if first in DDL:
        m = re.match(r"\s*\w+\s+(?:(?:TEMPORARY|UNIQUE|FULLTEXT|OR\s+REPLACE)\s+)*(\w+)", clean, re.I)
        return f"{first} {m.group(1).upper()}" if m else first
    return first


def validate(sql: str, role: str = "write") -> dict:
    out = {"valid": False, "errors": [], "warnings": [], "operation": None, "category": None,
           "destructive": False, "requires_confirmation": False, "target": None}
    sql = (sql or "").strip()
    if not sql:
        out["errors"].append("SQL is empty.")
        return out

    stmts = [s for s in sqlparse.parse(sql) if str(s).strip().strip(";").strip()]
    if len(stmts) != 1:
        out["errors"].append("Exactly one SQL statement is allowed per run.")
        return out
    if any(t.ttype in T.Comment for t in stmts[0].flatten()):
        out["errors"].append("SQL comments are not allowed.")
        return out

    clean = STRINGS.sub("''", sql).strip().rstrip(";").strip()
    m = re.match(r"\s*(\w+)", clean)
    first = m.group(1).upper() if m else ""
    if first in READ:
        out["category"] = "read"
    elif first in DML:
        out["category"] = "dml"
    elif first in DDL:
        out["category"] = "ddl"
    else:
        out["errors"].append(f"'{first or sql[:20]}' statements are not supported.")
        return out

    out["operation"] = _operation(first, clean)
    if BLOCKED.search(clean):
        out["errors"].append("This statement uses a blocked feature (file access, user management, sleep, etc.).")
    if first == "WITH" and re.search(r"\b(?:INSERT|UPDATE|DELETE)\b", clean, re.I):
        out["errors"].append("Only read-only WITH queries are supported.")
    if out["category"] == "read" and re.search(r"\bINTO\b", clean, re.I):
        out["errors"].append("SELECT ... INTO is not allowed.")

    if out["category"] != "read":
        t = TARGET.search(clean)
        out["target"] = t.group(1).replace("`", "") if t else None
        if SYSTEM_REF.search(clean) or (out["target"] and out["target"].split(".")[0].lower()
                                         in {"mysql", "sys", "information_schema", "performance_schema"}):
            out["errors"].append("Changing MySQL system schemas is not allowed.")
        out["destructive"] = first in ("DROP", "TRUNCATE") or bool(
            re.search(r"\bALTER\b.*\bDROP\s+(?:COLUMN|PRIMARY|FOREIGN|INDEX|KEY)\b", clean, re.I | re.S))
        out["requires_confirmation"] = True
        if first in ("UPDATE", "DELETE"):
            if not re.search(r"\bWHERE\b", clean, re.I):
                out["errors"].append(f"{first} without a WHERE clause is rejected. Say which rows to change.")
            elif TAUTOLOGY.search(clean):
                out["errors"].append("WHERE 1=1 style conditions match every row and are rejected.")
        if out["category"] == "ddl":
            out["warnings"].append("Schema changes are committed immediately by MySQL and cannot be rolled back.")
        if out["destructive"]:
            out["warnings"].append("Destructive operation: data or structure will be permanently removed.")

    need = 0 if out["category"] == "read" else (2 if out["destructive"] else 1)
    if RANK.get(role, 0) < need:
        names = {0: "readonly", 1: "write", 2: "admin"}
        out["errors"].append(f"Role '{role}' cannot run {out['operation']}. Required role: {names[need]}.")

    out["valid"] = not out["errors"]
    return out
