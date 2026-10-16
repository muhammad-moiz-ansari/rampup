from functools import lru_cache
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=("../.env", ".env"), extra="ignore")
    app_env: str = "development"
    database_url: str = ""
    database_direct_url: str = ""
    jwt_secret: str = ""
    access_token_ttl_minutes: int = 120
    llm_api_key: str = ""
    llm_model: str = ""
    llm_provider: str = "auto"
    repository_provider: str = "github_rest"
    github_token: str = ""
    github_owner: str = "muhammad-moiz-ansari"
    github_repo: str = "rampup"
    github_ref: str = "main"
    port: int = 8000
    static_dir: str = "static"


@lru_cache
def get_settings() -> Settings:
    return Settings()
