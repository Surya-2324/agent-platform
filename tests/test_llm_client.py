"""Unit tests for LLMClient using a fake model (no API calls, no waiting)."""

from types import SimpleNamespace
from typing import Any

import pytest
from litellm.exceptions import AuthenticationError, RateLimitError

from agent_platform.llm.client import AllModelsFailedError, LLMClient

PING = [{"role": "user", "content": "ping"}]


def fake_response(content: str) -> Any:
    """Build an object shaped like a LiteLLM response."""
    message = SimpleNamespace(content=content, tool_calls=None)
    usage = SimpleNamespace(prompt_tokens=10, completion_tokens=2)
    return SimpleNamespace(choices=[SimpleNamespace(message=message)], usage=usage)


def no_sleep(_: float) -> None:
    pass


def test_primary_model_success() -> None:
    calls: list[str] = []

    def completion(**kw: Any) -> Any:
        calls.append(kw["model"])
        return fake_response("pong")

    client = LLMClient(["m1", "m2"], "key", completion_fn=completion, sleep_fn=no_sleep)
    resp = client.chat(PING)

    assert resp.content == "pong"
    assert resp.model == "m1"
    assert resp.input_tokens == 10  # proves usage is read correctly
    assert calls == ["m1"]  # fallback never touched


def test_retries_then_falls_back_on_rate_limit() -> None:
    calls: list[str] = []

    def completion(**kw: Any) -> Any:
        calls.append(kw["model"])
        if kw["model"] == "m1":
            raise RateLimitError(message="429", llm_provider="groq", model="m1")
        return fake_response("from fallback")

    client = LLMClient(
        ["m1", "m2"], "key", max_retries=2, completion_fn=completion, sleep_fn=no_sleep
    )
    resp = client.chat(PING)

    assert resp.model == "m2"
    assert calls == ["m1", "m1", "m1", "m2"]  # 1 try + 2 retries, then fallback


def test_auth_error_fails_fast() -> None:
    calls: list[str] = []

    def completion(**kw: Any) -> Any:
        calls.append(kw["model"])
        raise AuthenticationError(message="bad key", llm_provider="groq", model="m1")

    client = LLMClient(["m1", "m2"], "key", completion_fn=completion, sleep_fn=no_sleep)
    with pytest.raises(AuthenticationError):
        client.chat(PING)

    assert calls == ["m1"]  # no retry, no fallback: a bad key is our bug


def test_all_models_fail() -> None:
    def completion(**kw: Any) -> Any:
        raise RateLimitError(message="429", llm_provider="groq", model=kw["model"])

    client = LLMClient(
        ["m1", "m2"], "key", max_retries=1, completion_fn=completion, sleep_fn=no_sleep
    )
    with pytest.raises(AllModelsFailedError):
        client.chat(PING)
