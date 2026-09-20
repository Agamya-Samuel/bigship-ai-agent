from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="", case_sensitive=False)

    openrouter_api_key: str
    llm_model: str = "openai/gpt-4o"
    agent_port: int = 8000
    checkpoint_db_path: str = "./checkpoints.db"
    max_tool_calls: int = 10
    agent_service_api_key: str | None = None


settings = Settings()  # type: ignore[call-arg]
