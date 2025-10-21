"""Microphone capture."""

from __future__ import annotations

import os
import wave

import numpy as np
import sounddevice as sd

from . import config


class AudioError(RuntimeError):
    """Raised when the microphone is unavailable."""


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
