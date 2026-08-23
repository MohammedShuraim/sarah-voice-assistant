"""The assistant itself: command routing with a conversational fallback."""

from __future__ import annotations

from dataclasses import dataclass, field

from . import ai, commands


@dataclass
class Reply:
    """What Sarah decided to do about one piece of input."""

    text: str
    source: str  # "command", "chat", "error", or "ignored"
    handled: bool = True
    transcript: str = ""

    @property
    def should_speak(self) -> bool:
        """Whether this reply is worth saying out loud."""
        return self.handled and bool(self.text)


@dataclass
class Assistant:
    """Turns text into an action or an answer.

    Speech recognition and playback deliberately live outside this class so the
    same logic serves the microphone loop and the typed web interface.
    """

    conversation: ai.Conversation = field(default_factory=ai.Conversation)

    def reset(self) -> None:
        self.conversation.reset()

    def handle(self, text: str) -> Reply:
        """Respond to one utterance or typed message."""
        spoken = commands.normalize(text)
        if not spoken:
            return Reply(text="", source="ignored", handled=False, transcript=text)

        try:
            result = commands.route(spoken)
        except commands.CommandError as exc:
            return Reply(text=str(exc), source="error", transcript=text)

        if result.handled:
            return Reply(text=result.reply, source="command", transcript=text)

        try:
            answer = self.conversation.ask(spoken)
        except ai.ChatError as exc:
            return Reply(text=str(exc), source="error", transcript=text)

        return Reply(text=answer, source="chat", transcript=text)
