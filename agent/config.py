from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_prefix="",
        case_sensitive=False,
        env_file=".env",
        env_file_encoding="utf-8",
    )

    openrouter_api_key: str
    llm_model: str
    agent_port: int = 8000
    checkpoint_db_path: str = "/data/checkpoints.db"
    max_tool_calls: int = 10

    jwt_secret: str
    jwt_expiry_minutes: int = 1440
    credential_encryption_key: str
    frontend_origin: str = "http://localhost:5173"

    @property
    def frontend_origins(self) -> list[str]:
        """Comma-separated CORS origins, e.g. `https://app.example.com,https://admin.example.com`."""
        return [o.strip().rstrip("/") for o in self.frontend_origin.split(",") if o.strip()]


settings = Settings()  # type: ignore[call-arg]
