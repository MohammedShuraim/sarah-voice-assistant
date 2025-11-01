"""Conversational replies from Groq's chat completions API."""

from __future__ import annotations

import requests

from . import config


class ChatError(RuntimeError):
    """Raised when the chat model could not be reached."""


class Conversation:
    """A chat session that remembers a bounded window of recent turns.

    History is trimmed to the most recent ``history_limit`` messages so a long
    session cannot grow the request past the model's context window.
    """

    def __init__(
        self,
        system_prompt: str = config.SYSTEM_PROMPT,
        model: str = config.CHAT_MODEL,
        history_limit: int = config.HISTORY_LIMIT,
    ) -> None:
        self.system_prompt = system_prompt
        self.model = model
        self.history_limit = history_limit
        self._messages: list[dict[str, str]] = []

    @property
    def messages(self) -> list[dict[str, str]]:
        """The recorded turns, excluding the system prompt."""
        return list(self._messages)

    def reset(self) -> None:
        self._messages.clear()

    def _trim(self) -> None:
        if len(self._messages) > self.history_limit:
            del self._messages[: len(self._messages) - self.history_limit]

    def ask(self, user_input: str, temperature: float = 0.7, max_tokens: int = 300) -> str:
        """Send a message and return the assistant's reply."""
        if not user_input.strip():
            raise ChatError("Cannot send an empty message.")

        # Checked before the turn is recorded so a missing key leaves history clean.
        try:
            api_key = config.require_groq_key()
        except config.ConfigError as exc:
            raise ChatError(str(exc)) from exc

        self._messages.append({"role": "user", "content": user_input})
        self._trim()

        payload = {
            "model": self.model,
            "messages": [{"role": "system", "content": self.system_prompt}, *self._messages],
            "temperature": temperature,
            "max_tokens": max_tokens,
        }
        headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
        }

        try:
            response = requests.post(
                config.CHAT_URL,
                headers=headers,
                json=payload,
                timeout=config.HTTP_TIMEOUT,
            )
        except requests.RequestException as exc:
            # Drop the unanswered turn so history stays a valid alternating log.
            self._messages.pop()
            raise ChatError(f"Could not reach Groq: {exc}") from exc

        if response.status_code != 200:
            self._messages.pop()
            if response.status_code == 401:
                raise ChatError("Groq rejected the API key (401). Check GROQ_API_KEY.")
            if response.status_code == 429:
                raise ChatError("Groq rate limit reached. Wait a moment and try again.")
            raise ChatError(f"Chat request failed ({response.status_code}): {response.text[:200]}")

        try:
            reply = response.json()["choices"][0]["message"]["content"].strip()
        except (KeyError, IndexError, ValueError) as exc:
            self._messages.pop()
            raise ChatError("Groq returned an unexpected response shape.") from exc

        self._messages.append({"role": "assistant", "content": reply})
        self._trim()
        return reply
