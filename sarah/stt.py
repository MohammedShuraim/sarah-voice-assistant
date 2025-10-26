"""Speech-to-text through Groq's hosted Whisper models."""

from __future__ import annotations

import os
from pathlib import Path

import requests

from . import config


class TranscriptionError(RuntimeError):
    """Raised when audio could not be transcribed."""


def transcribe(path: str | os.PathLike[str]) -> str:
    """Transcribe an audio file and return the recognised text.

    Returns an empty string when the model hears nothing intelligible.
    """
    audio_path = Path(path)
    if not audio_path.exists():
        raise TranscriptionError(f"Audio file not found: {audio_path}")
    return transcribe_bytes(audio_path.read_bytes(), audio_path.name)


def transcribe_bytes(payload: bytes, filename: str = "audio.wav") -> str:
    """Transcribe raw audio bytes.

    The filename matters: Groq infers the container format from its extension,
    so browser recordings must keep their ``.webm`` name rather than being
    relabelled as WAV.
    """
    if not payload:
        raise TranscriptionError("No audio data to transcribe.")

    try:
        api_key = config.require_groq_key()
    except config.ConfigError as exc:
        raise TranscriptionError(str(exc)) from exc

    headers = {"Authorization": f"Bearer {api_key}"}

    try:
        response = requests.post(
            config.TRANSCRIBE_URL,
            headers=headers,
            files={"file": (filename, payload)},
            data={"model": config.TRANSCRIBE_MODEL, "response_format": "json"},
            timeout=config.HTTP_TIMEOUT,
        )
    except requests.RequestException as exc:
        raise TranscriptionError(f"Could not reach Groq: {exc}") from exc

    if response.status_code == 401:
        raise TranscriptionError("Groq rejected the API key (401). Check GROQ_API_KEY.")
    if response.status_code == 429:
        raise TranscriptionError("Groq rate limit reached. Wait a moment and try again.")
    if response.status_code != 200:
        raise TranscriptionError(
            f"Transcription failed ({response.status_code}): {response.text[:200]}"
        )

    return response.json().get("text", "").strip()
