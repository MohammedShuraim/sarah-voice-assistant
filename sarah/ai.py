"""Conversational replies from Groq's chat completions API."""

from __future__ import annotations

import requests

from . import config


class ChatError(RuntimeError):
    """Raised when the chat model could not be reached."""


def supports_reasoning(model: str) -> bool:
    """Whether a model accepts the GPT-OSS reasoning parameters.

    Only GPT-OSS accepts ``reasoning_effort`` with low/medium/high and
    ``include_reasoning``. Sending them to a model that does not understand them
    is rejected with a 400, so they are gated on the model ID rather than sent
    unconditionally.
    """
    return "gpt-oss" in model


def list_available_models() -> list[str]:
    """Return the model IDs Groq is currently serving, sorted.

    Useful for catching a deprecation before it surfaces as a failed request:
    Groq retires models on a rolling basis and a shut-down ID simply errors.
    """
    try:
        api_key = config.require_groq_key()
    except config.ConfigError as exc:
        raise ChatError(str(exc)) from exc

    try:
        response = requests.get(
            config.MODELS_URL,
            headers={"Authorization": f"Bearer {api_key}"},
            timeout=config.HTTP_TIMEOUT,
        )
    except requests.RequestException as exc:
        raise ChatError(f"Could not reach Groq: {exc}") from exc

    if response.status_code != 200:
        raise ChatError(f"Could not list models ({response.status_code}).")

    try:
        return sorted(entry["id"] for entry in response.json()["data"])
    except (KeyError, TypeError, ValueError) as exc:
        raise ChatError("Groq returned an unexpected model list.") from exc


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

    def ask(
        self,
        user_input: str,
        temperature: float = config.TEMPERATURE,
        max_completion_tokens: int = config.MAX_COMPLETION_TOKENS,
    ) -> str:
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

        payload: dict[str, object] = {
            "model": self.model,
            "messages": [{"role": "system", "content": self.system_prompt}, *self._messages],
            "temperature": temperature,
            "max_completion_tokens": max_completion_tokens,
        }
        if supports_reasoning(self.model):
            payload["reasoning_effort"] = config.REASONING_EFFORT
            # The reasoning trace is never spoken, so there is no reason to
            # transfer it. Note that suppressing it does not reclaim the tokens
            # it consumed from max_completion_tokens.
            payload["include_reasoning"] = False

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
            choice = response.json()["choices"][0]
            # content is null rather than absent when a reasoning model spends its
            # whole budget thinking, so coalesce before stripping.
            reply = (choice["message"].get("content") or "").strip()
        except (KeyError, IndexError, ValueError) as exc:
            self._messages.pop()
            raise ChatError("Groq returned an unexpected response shape.") from exc

        if not reply:
            self._messages.pop()
            detail = (
                " Reasoning tokens share the MAX_COMPLETION_TOKENS budget, so try"
                " raising it or lowering REASONING_EFFORT."
                if supports_reasoning(self.model)
                else ""
            )
            raise ChatError(f"{self.model} returned an empty reply.{detail}")

        self._messages.append({"role": "assistant", "content": reply})
        self._trim()
        return reply
