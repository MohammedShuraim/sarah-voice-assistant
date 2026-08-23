"""Text-to-speech using Google Translate's voice endpoint via gTTS."""

from __future__ import annotations

import io
import os
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


def synthesize_to_bytes(text: str) -> io.BytesIO:
    """Render text to an in-memory MP3 stream, for serving over HTTP."""
    if not text.strip():
        raise SpeechError("Nothing to speak.")
    buffer = io.BytesIO()
    try:
        gTTS(text=text, lang=config.TTS_LANGUAGE).write_to_fp(buffer)
    except Exception as exc:
        raise SpeechError(f"Speech synthesis failed: {exc}") from exc
    buffer.seek(0)
    return buffer


def speak(text: str) -> None:
    """Say something out loud, cleaning up the temporary file afterwards.

    gTTS needs a network round trip, so this is not instant. Failures are raised
    rather than swallowed; callers decide whether a silent assistant is fatal.
    """
    # mkstemp rather than NamedTemporaryFile: gTTS and the mixer both reopen the
    # file by path, which Windows forbids while the original handle is still open.
    descriptor, name = tempfile.mkstemp(suffix=".mp3", prefix="sarah-")
    os.close(descriptor)
    temp_path = Path(name)
    try:
        synthesize(text, temp_path)
        audio.play_file(temp_path)
    finally:
        audio.delete_quietly(temp_path)
