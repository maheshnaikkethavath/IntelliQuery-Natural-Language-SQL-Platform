from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    gemini_api_key: str = ""
    gemini_model: str = "gemini-2.5-flash"
    mysql_host: str = ""
    mysql_port: int = 3306
    mysql_user: str = ""
    mysql_password: str = ""
    mysql_database: str = ""
    app_role: str = "write"  # readonly | write | admin
    max_rows: int = 1000
    query_timeout_seconds: int = 15
    max_corrections: int = 2
    cors_origins: str = "http://localhost:5173"


settings = Settings()
