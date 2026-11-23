import re

from sqlalchemy import create_engine, event, text
from sqlalchemy.engine import URL, Engine

from app.core.config import settings
from app.core.errors import AppError


class ConnectionManager:
    """Holds the single active MySQL engine. The password never leaves this object."""

    def __init__(self):
        self.engine: Engine | None = None
        self.info: dict = {}
        self._password = ""

    def connect(self, host: str, port: int, user: str, password: str, database: str | None = None):
        timeout = settings.query_timeout_seconds
        url = URL.create("mysql+pymysql", username=user, password=password,
                         host=host, port=port, database=database or None)
        engine = create_engine(
            url, pool_pre_ping=True, pool_recycle=1800,
            connect_args={"connect_timeout": 8, "read_timeout": timeout + 5, "write_timeout": timeout + 5},
        )

        @event.listens_for(engine, "connect")
        def _limits(dbapi_conn, _record):
            try:
                cur = dbapi_conn.cursor()
                cur.execute(f"SET SESSION max_execution_time={timeout * 1000}")
                cur.close()
            except Exception:
                pass

        try:
            with engine.connect() as conn:
                conn.execute(text("SELECT 1"))
        except Exception as exc:
            engine.dispose()
            raise AppError(400, f"Could not connect to MySQL: {str(getattr(exc, 'orig', exc))[:200]}")

        if self.engine is not None:
            self.engine.dispose()
        self.engine = engine
        self._password = password
        self.info = {"host": host, "port": port, "user": user, "database": database or None}

    def select_database(self, name: str):
        if not re.fullmatch(r"[\w$\-]+", name):
            raise AppError(400, "Invalid database name.")
        i = self.info
        self.connect(i["host"], i["port"], i["user"], self._password, name)

    def require(self) -> Engine:
        if self.engine is None:
            raise AppError(400, "Not connected to MySQL. Connect first.")
        return self.engine


manager = ConnectionManager()
