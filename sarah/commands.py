"""Recognition and execution of spoken system commands.

Handlers return the sentence Sarah should say back, which keeps this module free
of printing or speaking so both the CLI and the HTTP API can reuse it.
"""

from __future__ import annotations

import platform
import subprocess
import time
import webbrowser
from collections.abc import Callable
from dataclasses import dataclass

IS_WINDOWS = platform.system() == "Windows"


@dataclass
class CommandResult:
    """Outcome of routing one utterance."""

    handled: bool
    reply: str = ""


class CommandError(RuntimeError):
    """Raised when a recognised command could not be carried out."""


def _launch(target: str, friendly: str) -> str:
    """Start a desktop application by executable name or shell target."""
    if not IS_WINDOWS:
        raise CommandError(f"Opening {friendly} is only supported on Windows.")
    try:
        # 'start' is a cmd builtin, so it needs a shell. Targets here are fixed
        # constants from the table below, never user speech.
        subprocess.Popen(f'start "" {target}', shell=True)
    except OSError as exc:
        raise CommandError(f"Could not open {friendly}: {exc}") from exc
    return f"Opening {friendly}."


def _open_url(url: str, friendly: str) -> str:
    webbrowser.open(url)
    return f"Opening {friendly}."


def _tell_time() -> str:
    return f"It's {time.strftime('%I:%M %p').lstrip('0')}."


def _tell_date() -> str:
    return f"Today is {time.strftime('%A, %B %d, %Y')}."


_PHRASE_COMMANDS: tuple[tuple[tuple[str, ...], Callable[[], str]], ...] = (
    (("what time is it", "tell time", "tell me the time", "current time"), _tell_time),
    (("what's the date", "what is the date", "tell me the date", "today's date"), _tell_date),
    (
        ("open browser", "open the browser"),
        lambda: _open_url("https://www.google.com", "your browser"),
    ),
    (("open notepad", "open note pad"), lambda: _launch("notepad", "Notepad")),
    (("open calculator", "open calc"), lambda: _launch("calc", "Calculator")),
)


def normalize(text: str) -> str:
    """Lowercase text and drop punctuation so phrases match reliably."""
    cleaned = "".join(c for c in text.lower() if c.isalnum() or c.isspace())
    return " ".join(cleaned.split())


def route(text: str) -> CommandResult:
    """Try to handle an utterance as a system command.

    Returns an unhandled result when nothing matches, which is the caller's cue
    to fall back to the conversational model.
    """
    spoken = normalize(text)
    if not spoken:
        return CommandResult(handled=False)

    for triggers, handler in _PHRASE_COMMANDS:
        for trigger in triggers:
            if trigger in spoken:
                return CommandResult(handled=True, reply=handler())

    return CommandResult(handled=False)


def available_commands() -> list[str]:
    """Representative phrases for each command, for help text and the web UI."""
    return [triggers[0] for triggers, _ in _PHRASE_COMMANDS]
