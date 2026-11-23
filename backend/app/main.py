from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.api.routes import router
from app.core.config import settings
from app.core.errors import AppError
from app.database.connection import manager
from app.services import history_service


@asynccontextmanager
async def lifespan(_app: FastAPI):
    history_service.init()
    if settings.mysql_host and settings.mysql_user:
        try:
            manager.connect(settings.mysql_host, settings.mysql_port, settings.mysql_user,
                            settings.mysql_password, settings.mysql_database or None)
            print(f"Connected to MySQL at {settings.mysql_host}")
        except AppError as exc:
            print(f"Auto-connect skipped: {exc.message}")
    yield


app = FastAPI(title="AskDB - Natural Language SQL", lifespan=lifespan)
app.add_middleware(CORSMiddleware, allow_origins=[o.strip() for o in settings.cors_origins.split(",")],
                   allow_methods=["*"], allow_headers=["*"])
app.include_router(router)


@app.exception_handler(AppError)
async def app_error_handler(_req: Request, exc: AppError):
    return JSONResponse(status_code=exc.status_code, content={"detail": exc.message})


@app.get("/health")
def health():
    return {"ok": True}
