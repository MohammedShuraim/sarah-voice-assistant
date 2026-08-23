"""Tests for the Groq chat client.

Every test intercepts ``requests.post``, so nothing here touches the network or
needs an API key beyond the fake one installed by the ``api_key`` fixture.
"""

import pytest

from sarah import ai, config


class FakeResponse:
    def __init__(self, payload, status_code=200):
        self.status_code = status_code
        self._payload = payload
        self.text = str(payload)

    def json(self):
        if isinstance(self._payload, Exception):
            raise self._payload
        return self._payload


def reply_payload(content):
    return {"choices": [{"message": {"content": content}}]}


@pytest.fixture
def api_key(monkeypatch):
    monkeypatch.setattr(config, "GROQ_API_KEY", "gsk_test_key")


@pytest.fixture
def captured(monkeypatch, api_key):
    """Capture the request Conversation.ask sends, and control the response."""
    calls = []
    box = {"response": FakeResponse(reply_payload("Hello there."))}

    def fake_post(url, headers=None, json=None, timeout=None):
        calls.append({"url": url, "headers": headers, "json": json, "timeout": timeout})
        return box["response"]

    monkeypatch.setattr(ai.requests, "post", fake_post)
    return calls, box


@pytest.mark.parametrize(
    ("model", "expected"),
    [
        ("openai/gpt-oss-120b", True),
        ("openai/gpt-oss-20b", True),
        ("qwen/qwen3.6-27b", False),
        ("whisper-large-v3-turbo", False),
    ],
)
def test_supports_reasoning(model, expected):
    assert ai.supports_reasoning(model) is expected


def test_gpt_oss_request_sends_reasoning_parameters(captured):
    calls, _ = captured
    conversation = ai.Conversation(model="openai/gpt-oss-120b")

    assert conversation.ask("hello") == "Hello there."

    payload = calls[0]["json"]
    assert payload["model"] == "openai/gpt-oss-120b"
    assert payload["reasoning_effort"] == config.REASONING_EFFORT
    assert payload["include_reasoning"] is False


def test_non_reasoning_model_omits_reasoning_parameters(captured):
    """Sending these to a model that does not accept them returns a 400."""
    calls, _ = captured
    ai.Conversation(model="some/other-model").ask("hello")

    payload = calls[0]["json"]
    assert "reasoning_effort" not in payload
    assert "include_reasoning" not in payload


def test_request_uses_max_completion_tokens(captured):
    calls, _ = captured
    ai.Conversation(model="openai/gpt-oss-120b").ask("hello", max_completion_tokens=512)

    payload = calls[0]["json"]
    # Reasoning models budget reasoning and answer together under this key;
    # the older max_tokens field does not account for reasoning.
    assert payload["max_completion_tokens"] == 512
    assert "max_tokens" not in payload


def test_system_prompt_leads_the_messages(captured):
    calls, _ = captured
    conversation = ai.Conversation(system_prompt="Be brief.")
    conversation.ask("hello")

    messages = calls[0]["json"]["messages"]
    assert messages[0] == {"role": "system", "content": "Be brief."}
    assert messages[1] == {"role": "user", "content": "hello"}


def test_successful_reply_is_recorded(captured):
    _, box = captured
    box["response"] = FakeResponse(reply_payload("  Paris.  "))
    conversation = ai.Conversation()

    assert conversation.ask("capital of France") == "Paris."
    assert conversation.messages == [
        {"role": "user", "content": "capital of France"},
        {"role": "assistant", "content": "Paris."},
    ]


def test_empty_content_raises_with_budget_advice(captured):
    """A reasoning model that spends its whole budget thinking returns no content."""
    _, box = captured
    box["response"] = FakeResponse(reply_payload(None))
    conversation = ai.Conversation(model="openai/gpt-oss-120b")

    with pytest.raises(ai.ChatError, match="MAX_COMPLETION_TOKENS"):
        conversation.ask("explain everything")

    assert conversation.messages == []


def test_whitespace_only_content_is_treated_as_empty(captured):
    _, box = captured
    box["response"] = FakeResponse(reply_payload("   \n  "))

    with pytest.raises(ai.ChatError, match="empty reply"):
        ai.Conversation(model="openai/gpt-oss-120b").ask("hello")


def test_empty_reply_advice_is_omitted_for_non_reasoning_models(captured):
    _, box = captured
    box["response"] = FakeResponse(reply_payload(""))

    with pytest.raises(ai.ChatError) as error:
        ai.Conversation(model="some/other-model").ask("hello")

    assert "MAX_COMPLETION_TOKENS" not in str(error.value)


@pytest.mark.parametrize(
    ("status", "match"),
    [(401, "401"), (429, "rate limit"), (503, "503")],
)
def test_http_errors_become_chat_errors(captured, status, match):
    _, box = captured
    box["response"] = FakeResponse({"error": "nope"}, status_code=status)
    conversation = ai.Conversation()

    with pytest.raises(ai.ChatError, match=match):
        conversation.ask("hello")

    assert conversation.messages == []


def test_unexpected_response_shape_is_reported(captured):
    _, box = captured
    box["response"] = FakeResponse({"unexpected": True})
    conversation = ai.Conversation()

    with pytest.raises(ai.ChatError, match="unexpected response shape"):
        conversation.ask("hello")

    assert conversation.messages == []


def test_network_failure_does_not_record_the_turn(monkeypatch, api_key):
    def fail(*_args, **_kwargs):
        raise ai.requests.RequestException("connection reset")

    monkeypatch.setattr(ai.requests, "post", fail)
    conversation = ai.Conversation()

    with pytest.raises(ai.ChatError, match="Could not reach Groq"):
        conversation.ask("hello")

    assert conversation.messages == []


def test_list_available_models_returns_sorted_ids(monkeypatch, api_key):
    payload = {"data": [{"id": "openai/gpt-oss-120b"}, {"id": "whisper-large-v3-turbo"}]}
    monkeypatch.setattr(ai.requests, "get", lambda *_args, **_kwargs: FakeResponse(payload))

    assert ai.list_available_models() == ["openai/gpt-oss-120b", "whisper-large-v3-turbo"]


def test_list_available_models_requires_a_key(monkeypatch):
    monkeypatch.setattr(config, "GROQ_API_KEY", "")
    with pytest.raises(ai.ChatError, match="GROQ_API_KEY"):
        ai.list_available_models()
