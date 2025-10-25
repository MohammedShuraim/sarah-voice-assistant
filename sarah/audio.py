"""Microphone capture and audio playback.

Recording stops on its own once you go quiet, so there is no fixed time limit to
talk within. Playback goes through pygame's mixer, which decodes MP3 natively --
pydub and playsound both break on Python 3.13 because the stdlib ``audioop``
module they rely on was removed in that release.
"""

from __future__ import annotations

import contextlib
import os
import queue
import wave
from pathlib import Path

import numpy as np
import sounddevice as sd

from . import config


class AudioError(RuntimeError):
    """Raised when the microphone or speakers are unavailable."""


def _rms(frame: np.ndarray) -> float:
    """Root-mean-square amplitude of an int16 frame, scaled to 0.0-1.0."""
    if frame.size == 0:
        return 0.0
    # float64 avoids overflow when squaring int16 values.
    return float(np.sqrt(np.mean(frame.astype(np.float64) ** 2)) / 32768.0)


def record_until_silence(
    path: str | os.PathLike[str],
    sample_rate: int = config.SAMPLE_RATE,
    max_seconds: float = config.MAX_RECORD_SECONDS,
    silence_seconds: float = config.SILENCE_SECONDS,
    threshold: float = config.SILENCE_THRESHOLD,
    on_start=None,
) -> bool:
    """Record from the default microphone until the speaker stops talking.

    Returns True if speech was captured, False if the recording was silence
    throughout. Trailing silence is kept, since Whisper handles it fine and
    trimming risks clipping soft word endings.
    """
    block_frames = max(1, int(sample_rate * 0.05))
    silence_blocks_needed = max(1, int(silence_seconds / 0.05))
    max_blocks = max(1, int(max_seconds / 0.05))

    blocks: list[np.ndarray] = []
    frames: queue.Queue[np.ndarray] = queue.Queue()

    def callback(indata, _frames, _time, status):
        if status:
            # Overflows are common on loaded machines and are safe to ignore.
            pass
        frames.put(indata.copy())

    try:
        stream = sd.InputStream(
            samplerate=sample_rate,
            channels=1,
            dtype="int16",
            blocksize=block_frames,
            callback=callback,
        )
    except Exception as exc:  # sounddevice raises a variety of backend errors
        raise AudioError(f"Could not open the microphone: {exc}") from exc

    speech_started = False
    trailing_silence = 0

    with stream:
        if on_start is not None:
            on_start()
        for _ in range(max_blocks):
            try:
                block = frames.get(timeout=1.0)
            except queue.Empty:
                break

            blocks.append(block)
            level = _rms(block)

            if level >= threshold:
                speech_started = True
                trailing_silence = 0
            elif speech_started:
                trailing_silence += 1
                if trailing_silence >= silence_blocks_needed:
                    break

    if not speech_started:
        return False

    audio = np.concatenate(blocks) if blocks else np.zeros((0, 1), dtype=np.int16)
    _write_wav(path, audio, sample_rate)
    return True


def _write_wav(path: str | os.PathLike[str], audio: np.ndarray, sample_rate: int) -> None:
    with wave.open(str(path), "wb") as handle:
        handle.setnchannels(1)
        handle.setsampwidth(2)  # int16
        handle.setframerate(sample_rate)
        handle.writeframes(audio.tobytes())


_mixer_ready = False


def _ensure_mixer() -> None:
    global _mixer_ready
    if _mixer_ready:
        return
    # Keep pygame from printing its banner to stdout on import.
    os.environ.setdefault("PYGAME_HIDE_SUPPORT_PROMPT", "1")
    try:
        import pygame
    except ImportError as exc:
        raise AudioError(
            "pygame is required for audio playback. Install it with 'pip install pygame'."
        ) from exc

    try:
        pygame.mixer.init()
    except Exception as exc:
        raise AudioError(f"No audio output device available: {exc}") from exc
    _mixer_ready = True


def play_file(path: str | os.PathLike[str]) -> None:
    """Play an audio file, blocking until it finishes."""
    _ensure_mixer()
    import pygame

    sound = pygame.mixer.Sound(str(path))
    channel = sound.play()
    if channel is None:
        return
    while channel.get_busy():
        pygame.time.wait(50)


def delete_quietly(path: str | os.PathLike[str]) -> None:
    """Remove a temporary audio file, ignoring the case where it is missing."""
    with contextlib.suppress(OSError):
        Path(path).unlink()
