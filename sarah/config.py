"""Runtime configuration, loaded from the environment."""

import os

from dotenv import load_dotenv

load_dotenv()


class ConfigError(RuntimeError):
    """Raised when required configuration is missing."""


GROQ_API_KEY = os.getenv("GROQ_API_KEY", "")
WEATHER_API_KEY = os.getenv("WEATHER_API_KEY", "")
NEWS_API_KEY = os.getenv("NEWS_API_KEY", "")

GROQ_BASE_URL = os.getenv("GROQ_BASE_URL", "https://api.groq.com/openai/v1")
TRANSCRIBE_URL = f"{GROQ_BASE_URL}/audio/transcriptions"
CHAT_URL = f"{GROQ_BASE_URL}/chat/completions"

MODELS_URL = f"{GROQ_BASE_URL}/models"

TRANSCRIBE_MODEL = os.getenv("TRANSCRIBE_MODEL", "whisper-large-v3-turbo")
CHAT_MODEL = os.getenv("CHAT_MODEL", "openai/gpt-oss-120b")

# GPT-OSS models reason before answering, and those reasoning tokens are charged
# against the completion budget. "low" keeps a spoken assistant responsive.
REASONING_EFFORT = os.getenv("REASONING_EFFORT", "low")
# Covers reasoning and the answer together, so it needs far more headroom than
# the length of the reply alone would suggest.
MAX_COMPLETION_TOKENS = int(os.getenv("MAX_COMPLETION_TOKENS", "1024"))
# Groq recommends 0.5-0.7 for these models; higher values get incoherent.
TEMPERATURE = float(os.getenv("TEMPERATURE", "0.6"))

WAKE_WORD = os.getenv("WAKE_WORD", "hey sarah").lower()
# Set REQUIRE_WAKE_WORD=false to have Sarah respond to every utterance.
REQUIRE_WAKE_WORD = os.getenv("REQUIRE_WAKE_WORD", "true").lower() not in {
    "false",
    "0",
    "no",
}

SAMPLE_RATE = int(os.getenv("SAMPLE_RATE", "16000"))
MAX_RECORD_SECONDS = float(os.getenv("MAX_RECORD_SECONDS", "15"))
SILENCE_SECONDS = float(os.getenv("SILENCE_SECONDS", "1.2"))
# RMS amplitude below which a frame counts as silence, as a fraction of full scale.
SILENCE_THRESHOLD = float(os.getenv("SILENCE_THRESHOLD", "0.015"))

TTS_LANGUAGE = os.getenv("TTS_LANGUAGE", "en")
HTTP_TIMEOUT = float(os.getenv("HTTP_TIMEOUT", "30"))

SYSTEM_PROMPT = os.getenv(
    "SYSTEM_PROMPT",
    "You are Sarah, a friendly voice assistant. Because your replies are spoken "
    "aloud, keep them short and conversational — two or three sentences at most. "
    "Never use markdown, bullet points, or emoji.",
)

# Conversation turns kept in memory. Older turns are dropped to bound token cost.
HISTORY_LIMIT = int(os.getenv("HISTORY_LIMIT", "20"))


def require_groq_key() -> str:
    """Return the Groq API key, or explain how to set it."""
    if not GROQ_API_KEY:
        raise ConfigError(
            "GROQ_API_KEY is not set. Copy .env.example to .env and add your key "
            "from https://console.groq.com/keys"
        )
    return GROQ_API_KEY
