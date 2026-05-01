from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    PROJECT_NAME: str = "Cleo"
    VERSION: str = "0.1.0"
    DEBUG: bool = False

    # API
    API_HOST: str = "0.0.0.0"
    API_PORT: int = 8000

    # CORS
    CORS_ORIGINS: list[str] = ["*"]

    # Database (SQLite for local dev, override with PostgreSQL in production)
    DATABASE_URL: str = "sqlite+aiosqlite:///./agent_chat.db"

    # LLM Providers — set the key for whichever provider you want to use
    LLM_PROVIDER: str = "gemini"  # "gemini", "anthropic", or "openai"
    GEMINI_API_KEY: str = ""
    ANTHROPIC_API_KEY: str = ""
    OPENAI_API_KEY: str = ""

    # Search API (Tavily, SerpAPI, etc.)
    SEARCH_API_KEY: str = ""
    SEARCH_PROVIDER: str = "tavily"

    # ElevenLabs TTS
    ELEVENLABS_API_KEY: str = ""
    ELEVENLABS_VOICE_ID: str = "JBFqnCBsd6RMkjVDRZzb"  # "George" - natural male voice

    # Agent defaults
    DEFAULT_MODEL: str = "gemini-2.0-flash"
    MAX_AGENT_STEPS: int = 25
    AGENT_TIMEOUT_SECONDS: int = 120

    model_config = {"env_file": ".env", "env_file_encoding": "utf-8"}


settings = Settings()
