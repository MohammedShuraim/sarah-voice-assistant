"""Tests for wake-word handling and the fallback to conversation."""

import pytest

from sarah import ai, config, stt
from sarah import assistant as assistant_module


class StubConversation(ai.Conversation):
    """A conversation that answers locally instead of calling Groq."""

    def __init__(self, answer="Stub answer.", fail=False):
        super().__init__()
        self.answer = answer
        self.fail = fail
        self.asked = []

    def ask(self, user_input, temperature=None, max_completion_tokens=None):
        self.asked.append(user_input)
        if self.fail:
            raise ai.ChatError("Groq is unreachable.")
        return self.answer


@pytest.fixture
def bot():
    return assistant_module.Assistant(
        require_wake_word=True, wake_word="hey sarah", conversation=StubConversation()
    )


def test_input_without_wake_word_is_ignored(bot):
    reply = bot.handle("what time is it")
    assert not reply.handled
    assert reply.source == "ignored"
    assert not reply.should_speak


def test_bare_wake_word_acknowledges(bot):
    reply = bot.handle("hey Sarah")
    assert reply.source == "wake"
    assert reply.text == "Yes, I'm listening."
    assert reply.should_speak


def test_wake_word_then_command(bot):
    reply = bot.handle("hey Sarah, what time is it?")
    assert reply.source == "command"
    assert "It's" in reply.text


def test_wake_word_then_conversation(bot):
    reply = bot.handle("hey Sarah, who wrote Hamlet?")
    assert reply.source == "chat"
    assert reply.text == "Stub answer."
    assert bot.conversation.asked == ["who wrote hamlet"]


def test_wake_word_can_be_disabled_per_call(bot):
    reply = bot.handle("what time is it", wake_word_required=False)
    assert reply.source == "command"


def test_blank_input_is_ignored(bot):
    reply = bot.handle("   ")
    assert not reply.handled
    assert reply.source == "ignored"


def test_chat_failure_is_reported_not_raised():
    bot = assistant_module.Assistant(
        require_wake_word=False, conversation=StubConversation(fail=True)
    )
    reply = bot.handle("tell me a story")
    assert reply.source == "error"
    assert "unreachable" in reply.text
    # Diagnostics are printed, never spoken.
    assert not reply.should_speak


def test_history_is_bounded():
    conversation = ai.Conversation(history_limit=4)
    for index in range(10):
        conversation._messages.append({"role": "user", "content": str(index)})
        conversation._trim()
    assert len(conversation.messages) == 4
    assert conversation.messages[0]["content"] == "6"


def test_missing_api_key_surfaces_as_chat_error(monkeypatch):
    """A missing key must not escape as ConfigError, which callers do not catch."""
    monkeypatch.setattr(config, "GROQ_API_KEY", "")
    conversation = ai.Conversation()

    with pytest.raises(ai.ChatError, match="GROQ_API_KEY"):
        conversation.ask("hello")

    # The unanswered turn is not recorded.
    assert conversation.messages == []


def test_missing_api_key_is_reported_by_assistant(monkeypatch):
    monkeypatch.setattr(config, "GROQ_API_KEY", "")
    bot = assistant_module.Assistant(require_wake_word=False, conversation=ai.Conversation())

    reply = bot.handle("who wrote hamlet")

    assert reply.source == "error"
    assert "GROQ_API_KEY" in reply.text


def test_missing_api_key_surfaces_as_transcription_error(monkeypatch):
    monkeypatch.setattr(config, "GROQ_API_KEY", "")
    with pytest.raises(stt.TranscriptionError, match="GROQ_API_KEY"):
        stt.transcribe_bytes(b"not empty", "recording.webm")


def test_reset_clears_history():
    conversation = ai.Conversation()
    conversation._messages.append({"role": "user", "content": "hello"})
    bot = assistant_module.Assistant(conversation=conversation)

    bot.reset()

    assert conversation.messages == []
