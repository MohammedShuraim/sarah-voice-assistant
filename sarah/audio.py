"""Microphone capture and audio playback."""

from __future__ import annotations

import contextlib
import os
import wave
from pathlib import Path

import numpy as np
import sounddevice as sd
from playsound import playsound

from . import config


class AudioError(RuntimeError):
    """Raised when the microphone or speakers are unavailable."""


def record(
    path: str | os.PathLike[str],
    seconds: float = 5.0,
    sample_rate: int = config.SAMPLE_RATE,
) -> None:
    """Record a fixed number of seconds from the default microphone."""
    try:
        audio = sd.rec(
            int(seconds * sample_rate), samplerate=sample_rate, channels=1, dtype="int16"
        )
        sd.wait()
    except Exception as exc:  # sounddevice raises a variety of backend errors
        raise AudioError(f"Could not open the microphone: {exc}") from exc

    _write_wav(path, audio, sample_rate)


def _write_wav(path: str | os.PathLike[str], audio: np.ndarray, sample_rate: int) -> None:
    with wave.open(str(path), "wb") as handle:
        handle.setnchannels(1)
        handle.setsampwidth(2)  # int16
        handle.setframerate(sample_rate)
        handle.writeframes(audio.tobytes())


def play_file(path: str | os.PathLike[str]) -> None:
    """Play an audio file, blocking until it finishes."""
    try:
        playsound(str(path))
    except Exception as exc:
        raise AudioError(f"Could not play audio: {exc}") from exc


def delete_quietly(path: str | os.PathLike[str]) -> None:
    """Remove a temporary audio file, ignoring the case where it is missing."""
    with contextlib.suppress(OSError):
        Path(path).unlink()
