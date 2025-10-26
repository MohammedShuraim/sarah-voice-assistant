"""Speech-to-text through Groq's hosted Whisper models."""

from __future__ import annotations

import os
from pathlib import Path

import requests

from . import config


def transcribe(path: str | os.PathLike[str]) -> str:
    """Transcribe an audio file and return the recognised text."""
    audio_path = Path(path)
    headers = {"Authorization": f"Bearer {config.require_groq_key()}"}

    with audio_path.open("rb") as handle:
        response = requests.post(
            config.TRANSCRIBE_URL,
            headers=headers,
            files={"file": (audio_path.name, handle, "audio/wav")},
            data={"model": config.TRANSCRIBE_MODEL, "response_format": "json"},
            timeout=config.HTTP_TIMEOUT,
        )

    if response.status_code != 200:
        print(f"Transcription failed: {response.status_code} {response.text[:200]}")
        return ""

    return response.json().get("text", "").strip()
