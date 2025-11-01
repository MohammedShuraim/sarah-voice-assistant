"""Conversational replies from Groq's chat completions API."""

from __future__ import annotations

import requests

from . import config


class ChatError(RuntimeError):
    """Raised when the chat model could not be reached."""


def ask(user_input: str, temperature: float = 0.7, max_tokens: int = 300) -> str:
    """Send a single message and return the assistant's reply."""
    if not user_input.strip():
        raise ChatError("Cannot send an empty message.")

    payload = {
        "model": config.CHAT_MODEL,
        "messages": [
            {"role": "system", "content": config.SYSTEM_PROMPT},
            {"role": "user", "content": user_input},
        ],
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
    return response.json()["choices"][0]["message"]["content"].strip()
