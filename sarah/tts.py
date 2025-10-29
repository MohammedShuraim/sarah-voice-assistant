"""Text-to-speech using Google Translate's voice endpoint via gTTS."""

from __future__ import annotations

import tempfile
from pathlib import Path

from gtts import gTTS

from . import audio, config


class SpeechError(RuntimeError):
    """Raised when speech could not be synthesised or played."""


def synthesize(text: str, path: str | Path) -> Path:
    """Render text to an MP3 file and return its path."""
    if not text.strip():
        raise SpeechError("Nothing to speak.")
    try:
        gTTS(text=text, lang=config.TTS_LANGUAGE).save(str(path))
    except Exception as exc:  # gTTS surfaces network and language errors alike
        raise SpeechError(f"Speech synthesis failed: {exc}") from exc
    return Path(path)


def speak(text: str) -> None:
    """Say something out loud, cleaning up the temporary file afterwards."""
    with tempfile.NamedTemporaryFile(suffix=".mp3") as handle:
        temp_path = Path(handle.name)
        synthesize(text, temp_path)
        audio.play_file(temp_path)
