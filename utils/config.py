"""
Application configuration — centralizes all environment variables and settings.

All settings are loaded from .env once at application startup.
No other module should call load_dotenv() or os.getenv() directly.
"""

import os
from pathlib import Path

from dotenv import load_dotenv

# Load .env file once at the single entry point for all configuration
load_dotenv()

_root = Path(__file__).parent.parent

# LLM Configuration
LLM_PROVIDER: str = os.getenv("LLM_PROVIDER", "gemini").lower().strip()
GEMINI_API_KEY: str = os.getenv("GEMINI_API_KEY", "")
GEMINI_MODEL: str = os.getenv("GEMINI_MODEL", "gemini-flash-lite-latest")

GROQ_API_KEY: str = os.getenv("GROQ_API_KEY", "").strip().strip("\"'")
GROQ_MODEL: str = os.getenv("GROQ_MODEL", "qwen/qwen3.6-27b")


# Database & File Paths
DB_PATH: Path = Path(os.getenv("DB_PATH", str(_root / "portfolio_database.db")))
DB_READ_ONLY: bool = os.getenv("DB_READ_ONLY", "true").lower() in {"true", "1", "yes"}
SCHEMA_PATH: Path = _root / "database_schema.sql"
DATA_DIR: Path = _root / "data"
LOG_DIR: Path = Path(os.getenv("LOG_DIR", str(_root / "logs")))


# Logging Configuration
LOG_LEVEL_NAME: str = os.getenv("LOG_LEVEL", "INFO").upper()

# LangSmith Observability & Tracing Configuration
LANGSMITH_TRACING: bool = os.getenv("LANGSMITH_TRACING", "false").lower() == "true"
LANGSMITH_PROJECT: str = os.getenv("LANGSMITH_PROJECT", "Portfolio-Analytics-Agent")
LANGSMITH_ENDPOINT: str = os.getenv("LANGSMITH_ENDPOINT", "https://api.smith.langchain.com")
LANGSMITH_API_KEY: str = os.getenv("LANGSMITH_API_KEY", "")
