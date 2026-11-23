from pydantic import BaseModel, Field


class ConnectRequest(BaseModel):
    host: str = Field(min_length=1, max_length=255)
    port: int = Field(default=3306, ge=1, le=65535)
    user: str = Field(min_length=1, max_length=100)
    password: str = Field(default="", max_length=200)
    database: str | None = Field(default=None, max_length=100)


class SelectDbRequest(BaseModel):
    database: str = Field(min_length=1, max_length=100)


class GenerateRequest(BaseModel):
    request: str = Field(min_length=2, max_length=2000)


class SqlRequest(BaseModel):
    sql: str = Field(min_length=1, max_length=20000)


class ExecuteRequest(BaseModel):
    sql: str = Field(min_length=1, max_length=20000)
    confirmed: bool = False
    confirm_text: str = ""
    request: str | None = Field(default=None, max_length=2000)
    auto_correct: bool = True
