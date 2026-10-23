from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    # Tokens are verified against the project's public JWKS (ES256), so no JWT secret and no
    # service-role key ever reach this process.
    supabase_url: str
    supabase_anon_key: str
    # Narrow DB role (migration 0006) for confidential matching on every check; empty disables it.
    checker_database_url: str = ""
    groq_api_key: str = ""
    gemini_api_key: str = ""
    ollama_base_url: str = "http://localhost:11434/v1"
    llm_chain: list[str] = ["groq", "gemini"]
    max_upload_mb: int = 10
    match_threshold: float = 0.72
