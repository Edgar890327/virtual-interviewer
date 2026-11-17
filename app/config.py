from pathlib import Path
import os


BASE_DIR = Path(__file__).resolve().parent.parent
STATIC_DIR = BASE_DIR / "static"
SESSIONS_DIR = Path(os.getenv("SESSIONS_DIR", BASE_DIR / "data" / "sessions"))

# PostgreSQL (primary) - falls back to SQLite URL for local dev without Docker
DATABASE_URL = os.getenv(
    "DATABASE_URL",
    "postgresql://interview:interview_secret@localhost:5432/interviewdb"
)

OLLAMA_BASE_URL = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")
OLLAMA_MODEL = os.getenv("OLLAMA_MODEL", "llama3.1:8b")
WHISPER_MODEL_SIZE = os.getenv("WHISPER_MODEL_SIZE", "small")
WHISPER_DEVICE = os.getenv("WHISPER_DEVICE", "auto")
WHISPER_COMPUTE_TYPE = os.getenv("WHISPER_COMPUTE_TYPE", "int8")

JWT_SECRET_KEY = os.getenv("JWT_SECRET_KEY", "your-secret-key-change-in-production")
OLLAMA_API_KEY = os.getenv("OLLAMA_API_KEY", "your-ollama-api-key-change-in-production")
