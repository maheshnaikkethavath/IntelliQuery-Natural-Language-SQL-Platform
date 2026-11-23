import asyncio
import re

from fastapi import APIRouter

from app.core.config import settings
from app.core.errors import AppError
from app.database.connection import manager
from app.schemas.models import (ConnectRequest, ExecuteRequest, GenerateRequest,
                                SelectDbRequest, SqlRequest)
from app.security.validator import validate
from app.services import history_service, query_service, schema_service
from app.sql_engine import executor

router = APIRouter(prefix="/api/v1")


# ---------- database ----------
@router.post("/database/connect")
def connect(body: ConnectRequest):
    manager.connect(body.host, body.port, body.user, body.password, body.database)
    schema_service.invalidate()
    return {"connected": True, "info": manager.info}


@router.get("/database/status")
def status():
    if manager.engine is None:
        return {"connected": False, "role": settings.app_role}
    engine = manager.engine
    try:
        dbs = schema_service.list_databases(engine)
        schema, _ = schema_service.get_schema(engine)
    except Exception as exc:
        return {"connected": False, "role": settings.app_role, "error": str(exc)[:200]}
    return {"connected": True, "info": manager.info, "role": settings.app_role,
            "database_count": len(dbs), "table_count": len(schema["tables"]),
            "total_rows": sum(t["rows"] or 0 for t in schema["tables"])}


@router.get("/database/list")
def databases():
    return {"databases": schema_service.list_databases(manager.require()), "current": manager.info.get("database")}


@router.post("/database/select")
def select_database(body: SelectDbRequest):
    manager.require()
    manager.select_database(body.database)
    schema_service.invalidate()
    return {"current": body.database}


@router.get("/database/schema")
def schema(refresh: bool = False):
    data, _ = schema_service.get_schema(manager.require(), refresh)
    return data


@router.get("/database/tables")
def tables():
    data, _ = schema_service.get_schema(manager.require())
    return {"tables": [{"name": t["name"], "is_view": t["is_view"], "rows": t["rows"],
                        "columns": len(t["columns"])} for t in data["tables"]]}


@router.get("/database/tables/{table_name}")
def table_detail(table_name: str):
    engine = manager.require()
    if not re.fullmatch(r"[\w$]+", table_name):
        raise AppError(400, "Invalid table name.")
    data, _ = schema_service.get_schema(engine)
    table = next((t for t in data["tables"] if t["name"] == table_name), None)
    if not table:
        raise AppError(404, f"Table '{table_name}' not found.")
    ddl = executor.run(engine, f"SHOW CREATE TABLE `{table_name}`")
    count = executor.run(engine, f"SELECT COUNT(*) FROM `{table_name}`") if not table["is_view"] else None
    return {**table, "exact_rows": count["rows"][0][0] if count else None,
            "create_statement": ddl["rows"][0][1] if ddl["rows"] else None}


# ---------- AI + query ----------
@router.post("/ai/generate-sql")
async def generate_sql(body: GenerateRequest):
    return await query_service.generate(body.request)


@router.post("/query/validate")
def validate_sql(body: SqlRequest):
    return validate(body.sql, settings.app_role)


@router.post("/query/preview")
def preview(body: SqlRequest):
    v = validate(body.sql, settings.app_role)
    if not v["valid"]:
        raise AppError(400, "; ".join(v["errors"]))
    if v["operation"] not in ("UPDATE", "DELETE"):
        return {"available": False, "message": "Preview is only available for UPDATE and DELETE."}
    try:
        data = executor.preview(manager.require(), body.sql)
    except Exception as exc:
        return {"available": False, "message": executor.explain_error(exc)["message"]}
    if not data:
        return {"available": False, "message": "Could not build a preview for this statement."}
    return {"available": True, **data}


@router.post("/query/execute")
async def execute(body: ExecuteRequest):
    return await query_service.run_query(body)


@router.get("/query/history")
def history(limit: int = 50):
    return {"items": history_service.list_history(min(max(limit, 1), 200))}


@router.get("/query/history/{query_id}")
def history_item(query_id: int):
    item = history_service.get(query_id)
    if not item:
        raise AppError(404, "Query not found.")
    return item


@router.get("/query/stats")
def stats():
    return history_service.stats()
