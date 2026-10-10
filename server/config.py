import os
from dotenv import load_dotenv

load_dotenv()

BASE_DIR = os.path.abspath(os.path.dirname(__file__))

class Config:
    SECRET_KEY = os.getenv("AUTH_SECRET", "learnai-dev-secret-change-me-for-production-use-32bytes")
    JWT_ALGORITHM = "HS256"
    JWT_EXPIRATION_HOURS = 24 * 7  # 7 days

    # Database configuration
    # Supports PostgreSQL; falls back gracefully to SQLite if not provided
    DATABASE_URL = os.getenv("DATABASE_URL")
    if not DATABASE_URL:
        DATABASE_URL = f"sqlite:///{os.path.join(BASE_DIR, 'learnai.db')}"
    elif DATABASE_URL.startswith("postgres://"):
        DATABASE_URL = DATABASE_URL.replace("postgres://", "postgresql://", 1)

    SQLALCHEMY_DATABASE_URI = DATABASE_URL
    SQLALCHEMY_TRACK_MODIFICATIONS = False

    # AI & Services
    OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "")
    GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "")
    GEMINI_MODEL = os.getenv("GEMINI_MODEL", "gemini-2.0-flash")

    AZURE_OPENAI_ENDPOINT = os.getenv("AZURE_OPENAI_ENDPOINT", "")
    AZURE_OPENAI_API_KEY = os.getenv("AZURE_OPENAI_API_KEY", "")
    AZURE_OPENAI_DEPLOYMENT = os.getenv("AZURE_OPENAI_DEPLOYMENT", "LearnAI")
    AZURE_OPENAI_API_VERSION = os.getenv("AZURE_OPENAI_API_VERSION", "")

    AZURE_SPEECH_TO_TEXT_ENDPOINT = os.getenv("AZURE_SPEECH_TO_TEXT_ENDPOINT", "")
    AZURE_SPEECH_TO_TEXT_API_KEY = os.getenv("AZURE_SPEECH_TO_TEXT_API_KEY", "")

    AZURE_TEXT_TO_SPEECH_ENDPOINT = os.getenv("AZURE_TEXT_TO_SPEECH_ENDPOINT", "")
    AZURE_TEXT_TO_SPEECH_API_KEY = os.getenv("AZURE_TEXT_TO_SPEECH_API_KEY", "")

    ELEVENLABS_API_KEY = os.getenv("ELEVENLABS_API_KEY", "")
    ELEVENLABS_BASE_URL = os.getenv("ELEVENLABS_BASE_URL", "https://api.elevenlabs.io")
    ELEVENLABS_TTS_MODEL = os.getenv("ELEVENLABS_TTS_MODEL", "eleven_turbo_v2_5")

    D_ID_API_KEY = os.getenv("D_ID_API_KEY", "")
    CLOUDINARY_URL = os.getenv("CLOUDINARY_URL", "")

    # Mail configuration
    MAIL_FROM_ADDRESS = os.getenv("MAIL_FROM_ADDRESS", "hello@learnai.local")
    MAIL_FROM_NAME = os.getenv("MAIL_FROM_NAME", "LearnAI")
    MAIL_HOST = os.getenv("MAIL_HOST", "")
    MAIL_PORT = int(os.getenv("MAIL_PORT", "587"))
    MAIL_USERNAME = os.getenv("MAIL_USERNAME", "")
    MAIL_PASSWORD = os.getenv("MAIL_PASSWORD", "")
    APP_DEBUG = os.getenv("APP_DEBUG", "true").lower() in ("true", "1")
