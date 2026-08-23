"""Command-line voice loop: listen, act, speak, repeat."""

from __future__ import annotations

import sys
from pathlib import Path

from . import assistant as assistant_module
from . import audio, config, stt, tts

WAV_PATH = Path("input.wav")


def _print_banner(bot: assistant_module.Assistant) -> None:
    print("=" * 58)
    print("  Sarah Voice Assistant")
    print("=" * 58)
    if bot.require_wake_word:
        print(f'  Say "{bot.wake_word}" followed by your request.')
    else:
        print("  Wake word is off — just start talking.")
    print("  Recording stops automatically when you go quiet.")
    print("  Press Ctrl+C to exit.")
    print("=" * 58)


def _speak(text: str) -> None:
    try:
        tts.speak(text)
    except (tts.SpeechError, audio.AudioError) as exc:
        print(f"  (could not speak: {exc})")


def _listen_once(bot: assistant_module.Assistant, wav_path: Path) -> None:
    """Record one utterance and respond to it."""
    captured = audio.record_until_silence(
        wav_path, on_start=lambda: print("\n[listening]", flush=True)
    )
    if not captured:
        print("  Heard nothing. Still listening.")
        return

    print("  Transcribing...")
    try:
        transcript = stt.transcribe(wav_path)
    except stt.TranscriptionError as exc:
        print(f"  {exc}")
        return
    finally:
        audio.delete_quietly(wav_path)

    if not transcript:
        print("  Could not make that out.")
        return

    print(f"  You: {transcript}")
    reply = bot.handle(transcript)

    if reply.source == "ignored":
        print(f'  (no wake word — say "{bot.wake_word}" to activate)')
        return

    print(f"  Sarah: {reply.text}")
    if reply.should_speak:
        _speak(reply.text)


def main() -> int:
    try:
        config.require_groq_key()
    except config.ConfigError as exc:
        print(f"Configuration error: {exc}", file=sys.stderr)
        return 1

    bot = assistant_module.Assistant()
    _print_banner(bot)

    try:
        while True:
            _listen_once(bot, WAV_PATH)
    except KeyboardInterrupt:
        print("\n\nGoodbye.")
    except audio.AudioError as exc:
        print(f"\nAudio error: {exc}", file=sys.stderr)
        return 1

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
