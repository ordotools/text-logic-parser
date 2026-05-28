from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    """
    Application configuration settings using pydantic-settings.
    
    Environment variables are automatically mapped to these fields.
    For example:
    - GEMINI_API_KEY -> gemini_api_key
    - GEMINI_MODEL   -> gemini_model
    """
    gemini_api_key: str | None = None
    gemini_model: str = "gemini-3.1-flash-lite"
    
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore"
    )

# Global settings instance
settings = Settings()
