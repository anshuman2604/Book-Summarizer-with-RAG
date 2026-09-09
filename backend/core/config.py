import os
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """
    Application Settings & Environment Configuration.
    Automatically reads variables from the environment or a .env file.
    """

    # Server Configuration
    PROJECT_NAME: str = "Book Summarizer & Query AI"
    API_V1_STR: str = "/api/v1"
    PORT: int = 8000

    # Database Configuration (PostgreSQL with pgvector)
    DATABASE_URL: str = "postgresql://postgres:postgres@localhost:5432/book_summarizer"

    # JWT Authentication & Security
    SECRET_KEY: str = "default-insecure-secret-key-change-in-production"
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 1440  # 24 hours

    # Google Gemini AI (LLM / Summarizer)
    GOOGLE_API_KEY: str = ""
    GEMINI_API_KEY: str = ""
    LLM_MODEL: str = "gemini-3.6-flash"

    @property
    def effective_gemini_key(self) -> str:
        return self.GEMINI_API_KEY or self.GOOGLE_API_KEY or os.environ.get("GEMINI_API_KEY", "") or os.environ.get("GOOGLE_API_KEY", "")

    # Cohere Embeddings (100 RPM Free Tier)
    COHERE_API_KEY: str = ""
    COHERE_EMBED_MODEL: str = "embed-english-v3.0"

    # Observability & Tracing (LangSmith)
    LANGCHAIN_TRACING_V2: str = "false"
    LANGCHAIN_API_KEY: str = ""
    LANGCHAIN_PROJECT: str = "book-summarizer-agent"

    # Pydantic configuration to load .env file
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",  # Ignore any extra environment variables
    )


# Instantiate a singleton settings object for the entire app
settings = Settings()

# Automatically propagate LangSmith environment variables to process env
if settings.LANGCHAIN_TRACING_V2.lower() == "true" and settings.LANGCHAIN_API_KEY:
    os.environ["LANGCHAIN_TRACING_V2"] = "true"
    os.environ["LANGCHAIN_API_KEY"] = settings.LANGCHAIN_API_KEY
    os.environ["LANGCHAIN_PROJECT"] = settings.LANGCHAIN_PROJECT or "book-summarizer-agent"
    os.environ["LANGSMITH_API_KEY"] = settings.LANGCHAIN_API_KEY
    os.environ["LANGSMITH_PROJECT"] = settings.LANGCHAIN_PROJECT or "book-summarizer-agent"
