"""Command-line voice loop: listen, act, speak, repeat."""

from __future__ import annotations

import argparse
import sys
import tempfile
from pathlib import Path

from . import assistant as assistant_module
from . import audio, commands, config, stt, tts


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


def _text_mode(bot: assistant_module.Assistant) -> int:
    """Typed conversation, useful when no microphone is available."""
    print("Typed mode. Enter a blank line or Ctrl+C to quit.\n")
    while True:
        try:
            line = input("You: ").strip()
        except (EOFError, KeyboardInterrupt):
            print()
            return 0
        if not line:
            return 0
        reply = bot.handle(line, wake_word_required=False)
        print(f"Sarah: {reply.text}\n")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="sarah", description="Sarah, a voice assistant powered by Groq."
    )
    parser.add_argument(
        "--no-wake-word",
        action="store_true",
        help="respond to every utterance instead of waiting for the wake word",
    )
    parser.add_argument(
        "--text",
        action="store_true",
        help="type instead of speaking (no microphone needed)",
    )
    parser.add_argument(
        "--list-commands",
        action="store_true",
        help="show the built-in system commands and exit",
    )
    args = parser.parse_args(argv)

    if args.list_commands:
        print("Built-in commands:\n")
        for phrase in commands.available_commands():
            print(f"  - {phrase}")
        return 0

    try:
        config.require_groq_key()
    except config.ConfigError as exc:
        print(f"Configuration error: {exc}", file=sys.stderr)
        return 1

    bot = assistant_module.Assistant(
        require_wake_word=False if args.no_wake_word else config.REQUIRE_WAKE_WORD
    )

    if args.text:
        return _text_mode(bot)

    _print_banner(bot)

    with tempfile.TemporaryDirectory(prefix="sarah-") as workdir:
        wav_path = Path(workdir) / "input.wav"
        try:
            while True:
                _listen_once(bot, wav_path)
        except KeyboardInterrupt:
            print("\n\nGoodbye.")
        except audio.AudioError as exc:
            print(f"\nAudio error: {exc}", file=sys.stderr)
            print("Try 'python -m sarah --text' to chat without a microphone.")
            return 1

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
