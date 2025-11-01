"""Conversational replies from Groq's chat completions API."""

from __future__ import annotations

import requests

from . import config


class ChatError(RuntimeError):
    """Raised when the chat model could not be reached."""


class Conversation:
    """A chat session that remembers the turns that came before."""

    def __init__(
        self,
        system_prompt: str = config.SYSTEM_PROMPT,
        model: str = config.CHAT_MODEL,
    ) -> None:
        self.system_prompt = system_prompt
        self.model = model
        self._messages: list[dict[str, str]] = []

    @property
    def messages(self) -> list[dict[str, str]]:
        """The recorded turns, excluding the system prompt."""
        return list(self._messages)

    def reset(self) -> None:
        self._messages.clear()

    def ask(self, user_input: str, temperature: float = 0.7, max_tokens: int = 300) -> str:
        """Send a message and return the assistant's reply."""
        if not user_input.strip():
            raise ChatError("Cannot send an empty message.")

        self._messages.append({"role": "user", "content": user_input})

        payload = {
            "model": self.model,
            "messages": [{"role": "system", "content": self.system_prompt}, *self._messages],
            "temperature": temperature,
            "max_tokens": max_tokens,
        }
        headers = {
            "Authorization": f"Bearer {config.require_groq_key()}",
            "Content-Type": "application/json",
        }

        response = requests.post(
            config.CHAT_URL, headers=headers, json=payload, timeout=config.HTTP_TIMEOUT
        )
        response.raise_for_status()
        reply = response.json()["choices"][0]["message"]["content"].strip()

        self._messages.append({"role": "assistant", "content": reply})
        return reply
