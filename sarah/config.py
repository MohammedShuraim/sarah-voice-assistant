"""Runtime configuration, loaded from the environment."""

import os

from dotenv import load_dotenv

load_dotenv()


class ConfigError(RuntimeError):
    """Raised when required configuration is missing."""


GROQ_API_KEY = os.getenv("GROQ_API_KEY", "")

GROQ_BASE_URL = os.getenv("GROQ_BASE_URL", "https://api.groq.com/openai/v1")
TRANSCRIBE_URL = f"{GROQ_BASE_URL}/audio/transcriptions"
CHAT_URL = f"{GROQ_BASE_URL}/chat/completions"

TRANSCRIBE_MODEL = os.getenv("TRANSCRIBE_MODEL", "whisper-large-v3-turbo")
CHAT_MODEL = os.getenv("CHAT_MODEL", "llama-3.3-70b-versatile")

WAKE_WORD = os.getenv("WAKE_WORD", "hey sarah").lower()

SAMPLE_RATE = int(os.getenv("SAMPLE_RATE", "16000"))

TTS_LANGUAGE = os.getenv("TTS_LANGUAGE", "en")
HTTP_TIMEOUT = float(os.getenv("HTTP_TIMEOUT", "30"))


def require_groq_key() -> str:
    """Return the Groq API key, or explain how to set it."""
    if not GROQ_API_KEY:
        raise ConfigError(
            "GROQ_API_KEY is not set. Copy .env.example to .env and add your key "
            "from https://console.groq.com/keys"
        )
    return GROQ_API_KEY
