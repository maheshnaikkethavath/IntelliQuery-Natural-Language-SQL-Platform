import asyncio
import time

from app.ai import llm
from app.core.config import settings
from app.database.connection import manager
from app.schemas.models import ExecuteRequest
from app.security.validator import validate
from app.services import history_service, schema_service
from app.sql_engine import executor


def _stage(stages, name, t0, detail="", status="done"):
    stages.append({"name": name, "status": status, "ms": round((time.perf_counter() - t0) * 1000), "detail": detail})


async def generate(request: str) -> dict:
    """Real pipeline; every stage below records its own measured time."""
    stages = []
    t = time.perf_counter()
    request = " ".join(request.split())
    _stage(stages, "Understanding request", t, f"{len(request)} characters received")

    t = time.perf_counter()
    engine = manager.require()
    schema, cached = await asyncio.to_thread(schema_service.get_schema, engine)
    _stage(stages, "Retrieving database schema", t,
           f"{len(schema['tables'])} tables ({'cached' if cached else 'fresh'})")

    t = time.perf_counter()
    data = await llm.generate_sql(request, schema_service.schema_text(schema, request))
    _stage(stages, "Calling LLM API", t, settings.gemini_model)

    t = time.perf_counter()
    sql = str(data.get("sql") or "").strip()
    _stage(stages, "Generating SQL", t, data.get("operation") or ("no SQL returned" if not sql else ""))

    t = time.perf_counter()
    validation = validate(sql, settings.app_role) if sql else None
    _stage(stages, "Validating SQL", t,
           "skipped" if not sql else ("passed" if validation["valid"] else "; ".join(validation["errors"])),
           "done" if not sql or validation["valid"] else "failed")
    return {"sql": sql, "explanation": data.get("explanation", ""), "operation": data.get("operation", ""),
            "stages": stages, "validation": validation}


async def run_query(req: ExecuteRequest) -> dict:
    engine = manager.require()
    db = manager.info.get("database")
    role = settings.app_role
    stages = []

    t = time.perf_counter()
    v = validate(req.sql, role)
    _stage(stages, "Validating SQL", t,
           "; ".join(v["errors"]) if not v["valid"] else f"{v['operation']} allowed for role '{role}'",
           "done" if v["valid"] else "failed")
    if not v["valid"]:
        err = "; ".join(v["errors"])
        history_service.add(req.request, req.sql, db, "rejected", error=err, role=role)
        return {"status": "rejected", "error": err, "validation": v, "stages": stages}

    if v["requires_confirmation"]:
        ok = req.confirmed and (not v["destructive"] or req.confirm_text.strip().upper() == "CONFIRM")
        stages.append({"name": "Waiting for confirmation", "status": "done" if ok else "waiting",
                       "ms": 0, "detail": "confirmed by user" if ok else "needs your confirmation"})
        if not ok:
            return {"status": "confirmation_required", "validation": v, "stages": stages}

    current, corrections, attempt = req.sql, [], 0
    while True:
        t = time.perf_counter()
        try:
            result = await asyncio.to_thread(executor.run, engine, current)
            _stage(stages, "Executing SQL", t, f"{result['duration_ms']} ms")
            break
        except Exception as exc:
            info = executor.explain_error(exc)
            _stage(stages, "Executing SQL", t, info["message"], "failed")
            if req.auto_correct and req.request and attempt < settings.max_corrections:
                attempt += 1
                t = time.perf_counter()
                schema, _ = await asyncio.to_thread(schema_service.get_schema, engine)
                try:
                    fix = await llm.fix_sql(req.request, current, info["detail"],
                                            schema_service.schema_text(schema, req.request))
                except Exception:
                    fix = {}
                fixed = str(fix.get("sql") or "").strip()
                fv = validate(fixed, role) if fixed else None
                _stage(stages, f"AI correction attempt {attempt}", t,
                       "validated" if fv and fv["valid"] else "no valid correction", "done" if fv and fv["valid"] else "failed")
                if fv and fv["valid"]:
                    if fv["category"] == "read" and v["category"] == "read":
                        corrections.append({"from": current, "to": fixed})
                        current = fixed
                        continue
                    history_service.add(req.request, current, db, "error", error=info["detail"], role=role)
                    return {"status": "error", "error": info["message"], "detail": info["detail"],
                            "suggested_sql": fixed, "suggested_validation": fv, "validation": v, "stages": stages}
            history_service.add(req.request, current, db, "error", error=info["detail"], role=role)
            return {"status": "error", "error": info["message"], "detail": info["detail"],
                    "validation": v, "stages": stages}

    if v["category"] == "ddl":
        schema_service.invalidate()
    history_service.add(req.request, current, db, "success", result["duration_ms"], result["affected_rows"], role=role)
    t = time.perf_counter()
    _stage(stages, "Displaying results", t,
           f"{result['row_count']} rows" if result["columns"] else f"{result['affected_rows']} rows affected")
    return {"status": "success", "sql": current, "validation": v, "stages": stages,
            "result": result, "corrections": corrections}
