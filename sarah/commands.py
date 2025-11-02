"""Recognition and execution of spoken system commands.

Handlers return the sentence Sarah should say back, which keeps this module free
of printing or speaking so both the CLI and the HTTP API can reuse it.
"""

from __future__ import annotations

import os
import platform
import shutil
import subprocess
import time
import webbrowser
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path

IS_WINDOWS = platform.system() == "Windows"
HOME = Path.home()


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


def _open_path(relative: str, friendly: str) -> str:
    """Open one of the user's standard folders in the file manager."""
    target = HOME / relative
    if not target.exists():
        raise CommandError(f"I could not find your {friendly} folder.")
    if IS_WINDOWS:
        os.startfile(target)  # noqa: S606 - path is derived from the home directory
    else:
        opener = "open" if platform.system() == "Darwin" else "xdg-open"
        if shutil.which(opener) is None:
            raise CommandError(f"No file manager available to open {friendly}.")
        subprocess.Popen([opener, str(target)])
    return f"Opening your {friendly} folder."


def _open_url(url: str, friendly: str) -> str:
    webbrowser.open(url)
    return f"Opening {friendly}."


def _tell_time() -> str:
    return f"It's {time.strftime('%I:%M %p').lstrip('0')}."


def _tell_date() -> str:
    return f"Today is {time.strftime('%A, %B %d, %Y')}."


# Exact phrases, longest first at match time so "open my downloads" wins over
# a hypothetical shorter overlap.
_PHRASE_COMMANDS: tuple[tuple[tuple[str, ...], Callable[[], str]], ...] = (
    (("what time is it", "tell time", "tell me the time", "current time"), _tell_time),
    (("what's the date", "what is the date", "tell me the date", "today's date"), _tell_date),
    (
        ("open browser", "open the browser"),
        lambda: _open_url("https://www.google.com", "your browser"),
    ),
    (("open brave", "start brave"), lambda: _launch("brave", "Brave")),
    (("open chrome", "start chrome", "open google chrome"), lambda: _launch("chrome", "Chrome")),
    (("open edge", "start edge", "open microsoft edge"), lambda: _launch("msedge", "Edge")),
    (("open firefox", "start firefox"), lambda: _launch("firefox", "Firefox")),
    (("open notepad", "open note pad"), lambda: _launch("notepad", "Notepad")),
    (("open calculator", "open calc"), lambda: _launch("calc", "Calculator")),
    (("open excel", "start excel"), lambda: _launch("excel", "Excel")),
    (("open word", "start word", "open microsoft word"), lambda: _launch("winword", "Word")),
    (("open powerpoint", "start powerpoint"), lambda: _launch("powerpnt", "PowerPoint")),
    (("open spotify", "start spotify"), lambda: _launch("spotify", "Spotify")),
    (
        ("open whatsapp", "start whatsapp"),
        lambda: _launch("shell:AppsFolder\\5319275A.WhatsAppDesktop_cv1g1gvanyjgm!App", "WhatsApp"),
    ),
    (
        ("open terminal", "open cmd", "open command prompt", "start terminal"),
        lambda: _launch("cmd", "the terminal"),
    ),
    (
        ("open explorer", "open file explorer", "open my computer"),
        lambda: _launch("explorer", "File Explorer"),
    ),
    (("open task manager",), lambda: _launch("taskmgr", "Task Manager")),
    (("open settings",), lambda: _launch("ms-settings:", "Settings")),
    (
        ("open email", "open gmail", "check my email", "check my mail"),
        lambda: _open_url("https://mail.google.com", "Gmail"),
    ),
    (("open outlook", "check outlook"), lambda: _launch("outlook", "Outlook")),
    (
        ("open calendar", "open my calendar"),
        lambda: _open_url("https://calendar.google.com", "your calendar"),
    ),
    (("open github",), lambda: _open_url("https://github.com", "GitHub")),
    (("open downloads", "open my downloads"), lambda: _open_path("Downloads", "Downloads")),
    (("open documents", "open my documents"), lambda: _open_path("Documents", "Documents")),
    (("open desktop", "open my desktop"), lambda: _open_path("Desktop", "Desktop")),
    (
        ("open pictures", "open my pictures", "open photos"),
        lambda: _open_path("Pictures", "Pictures"),
    ),
    (("open music", "open my music"), lambda: _open_path("Music", "Music")),
    (("open videos", "open my videos"), lambda: _open_path("Videos", "Videos")),
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

    matches = [
        (trigger, handler)
        for triggers, handler in _PHRASE_COMMANDS
        for trigger in triggers
        if trigger in spoken
    ]
    if matches:
        # Prefer the most specific phrase when several match the same utterance.
        _, handler = max(matches, key=lambda pair: len(pair[0]))
        return CommandResult(handled=True, reply=handler())

    return CommandResult(handled=False)


def available_commands() -> list[str]:
    """Representative phrases for each command, for help text and the web UI."""
    return [triggers[0] for triggers, _ in _PHRASE_COMMANDS]
