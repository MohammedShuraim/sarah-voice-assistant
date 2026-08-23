"""Tests for phrase normalisation and command routing.

Handlers that would launch an application or open a browser are patched, so the
suite is safe to run on a desktop.
"""

import pytest

from sarah import commands


@pytest.mark.parametrize(
    ("raw", "expected"),
    [
        ("Hey Sarah, what's the TIME?", "hey sarah whats the time"),
        ("  multiple   spaces  ", "multiple spaces"),
        ("Open Notepad!!!", "open notepad"),
        ("", ""),
    ],
)
def test_normalize(raw, expected):
    assert commands.normalize(raw) == expected


def test_time_command_is_handled():
    result = commands.route("what time is it")
    assert result.handled
    assert "It's" in result.reply


def test_date_command_is_handled():
    result = commands.route("tell me the date")
    assert result.handled
    assert result.reply.startswith("Today is")


def test_unknown_phrase_falls_through():
    assert not commands.route("what do you think about jazz music").handled


def test_empty_input_falls_through():
    assert not commands.route("   ").handled


def test_search_uses_url_encoding(monkeypatch):
    opened = []
    monkeypatch.setattr(commands.webbrowser, "open", opened.append)

    result = commands.route("search for cat videos & dogs")

    assert result.handled
    # Punctuation is stripped by normalisation and spaces become '+'.
    assert opened == ["https://www.google.com/search?q=cat+videos+dogs"]


def test_youtube_prefix(monkeypatch):
    opened = []
    monkeypatch.setattr(commands.webbrowser, "open", opened.append)

    assert commands.route("play bohemian rhapsody").handled
    assert "youtube.com/results" in opened[0]


def test_prefix_without_argument_is_not_handled(monkeypatch):
    monkeypatch.setattr(commands.webbrowser, "open", lambda _url: None)
    assert not commands.route("search for").handled


def test_folder_command_tolerates_surrounding_words(monkeypatch):
    opened = []
    monkeypatch.setattr(
        commands, "_open_path", lambda relative, friendly: opened.append(relative) or "ok"
    )

    assert commands.route("open my downloads please").handled
    assert opened == ["Downloads"]


def test_play_prefix_is_word_bounded(monkeypatch):
    """ "please" must not trigger the "play" prefix command."""
    monkeypatch.setattr(commands, "_open_path", lambda *_args: "ok")
    monkeypatch.setattr(commands.webbrowser, "open", lambda _url: pytest.fail("opened a browser"))

    assert commands.route("open my downloads please").handled


def test_missing_file_raises_command_error(monkeypatch):
    monkeypatch.setattr(commands, "find_file", lambda _name: None)
    with pytest.raises(commands.CommandError):
        commands.route("open file quarterly report")


def test_available_commands_lists_prefixes():
    phrases = commands.available_commands()
    assert "what time is it" in phrases
    assert any(phrase.endswith("...") for phrase in phrases)
