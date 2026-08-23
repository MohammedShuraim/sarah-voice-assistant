"""The assistant itself: wake word, command routing, and conversational fallback."""

from __future__ import annotations

from dataclasses import dataclass, field

from . import ai, commands, config


@dataclass
class Reply:
    """What Sarah decided to do about one piece of input."""

    text: str
    source: str  # "command", "chat", "wake", "error", or "ignored"
    handled: bool = True
    transcript: str = ""

    @property
    def should_speak(self) -> bool:
        """Whether this reply is worth saying out loud.

        Errors are shown but not spoken: they are diagnostics aimed at whoever is
        running Sarah, not conversation.
        """
        return self.handled and bool(self.text) and self.source not in {"ignored", "error"}


@dataclass
class Assistant:
    """Turns text into an action or an answer.

    Speech recognition and playback deliberately live outside this class so the
    same logic serves the microphone loop and the typed web interface.
    """

    require_wake_word: bool = config.REQUIRE_WAKE_WORD
    wake_word: str = config.WAKE_WORD
    conversation: ai.Conversation = field(default_factory=ai.Conversation)

    def reset(self) -> None:
        self.conversation.reset()

    def _strip_wake_word(self, spoken: str) -> tuple[bool, str]:
        """Detect the wake word and return the remaining request."""
        normalized_wake = commands.normalize(self.wake_word)
        if normalized_wake not in spoken:
            return False, spoken
        return True, spoken.replace(normalized_wake, " ", 1).strip()

    def handle(self, text: str, *, wake_word_required: bool | None = None) -> Reply:
        """Respond to one utterance or typed message."""
        spoken = commands.normalize(text)
        if not spoken:
            return Reply(text="", source="ignored", handled=False, transcript=text)

        needs_wake = self.require_wake_word if wake_word_required is None else wake_word_required

        if needs_wake:
            awake, remainder = self._strip_wake_word(spoken)
            if not awake:
                return Reply(
                    text="",
                    source="ignored",
                    handled=False,
                    transcript=text,
                )
            if not remainder:
                return Reply(text="Yes, I'm listening.", source="wake", transcript=text)
            spoken = remainder

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
