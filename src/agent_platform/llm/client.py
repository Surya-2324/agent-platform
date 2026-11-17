"""LLM client: one interface over LiteLLM with retries, timeouts and model fallback."""

from __future__ import annotations

import logging
import random
import time
from collections.abc import Callable, Sequence
from dataclasses import dataclass
from typing import Any

import litellm
from litellm.exceptions import (
    APIConnectionError,
    InternalServerError,
    NotFoundError,
    RateLimitError,
    ServiceUnavailableError,
    Timeout,
)

from agent_platform.config import get_settings

logger = logging.getLogger(__name__)
litellm.suppress_debug_info = True  # hide LiteLLM's "Give Feedback" banners

# Temporary problems: worth retrying the same model.
RETRYABLE_ERRORS: tuple[type[Exception], ...] = (
    RateLimitError,
    Timeout,
    APIConnectionError,
    InternalServerError,
    ServiceUnavailableError,
)
# Model-specific problems: skip straight to the next model.
NEXT_MODEL_ERRORS: tuple[type[Exception], ...] = (NotFoundError,)
# Everything else (bad key, bad request) is raised immediately — it's our bug.

# Type alias: "any function we can call to get a model reply" (real or fake).
CompletionFn = Callable[..., Any]


@dataclass(frozen=True)
class ToolCall:
    """One tool the model wants to run."""

    id: str
    name: str
    arguments: str  # raw JSON text from the model; the agent loop parses + validates it


@dataclass(frozen=True)
class LLMResponse:
    """A provider-independent view of one model reply."""

    content: str | None
    tool_calls: list[ToolCall]
    model: str
    latency_ms: float
    input_tokens: int
    output_tokens: int

    def as_message(self) -> dict[str, Any]:
        """Convert back to the chat-message format, to append to the conversation."""
        msg: dict[str, Any] = {"role": "assistant", "content": self.content}
        if self.tool_calls:
            msg["tool_calls"] = [
                {
                    "id": tc.id,
                    "type": "function",
                    "function": {"name": tc.name, "arguments": tc.arguments},
                }
                for tc in self.tool_calls
            ]
        return msg


class AllModelsFailedError(RuntimeError):
    """Every model in the chain failed."""


class LLMClient:
    def __init__(
        self,
        models: Sequence[str],
        api_key: str,
        *,
        max_retries: int = 2,
        timeout_s: float = 60.0,
        base_delay_s: float = 1.0,
        completion_fn: CompletionFn = litellm.completion,
        sleep_fn: Callable[[float], None] = time.sleep,
    ) -> None:
        if not models:
            raise ValueError("At least one model is required")
        self._models = list(models)
        self._api_key = api_key
        self._max_retries = max_retries
        self._timeout_s = timeout_s
        self._base_delay_s = base_delay_s
        self._completion = completion_fn
        self._sleep = sleep_fn

    def chat(
        self,
        messages: list[dict[str, Any]],
        tools: list[dict[str, Any]] | None = None,
        *,
        max_tokens: int = 2048,
    ) -> LLMResponse:
        """Try each model in order; retry temporary errors with backoff."""
        errors: list[str] = []
        for model in self._models:
            for attempt in range(self._max_retries + 1):
                try:
                    return self._call(model, messages, tools, max_tokens)
                except RETRYABLE_ERRORS as exc:
                    errors.append(f"{model} try {attempt + 1}: {type(exc).__name__}")
                    if attempt < self._max_retries:
                        delay = self._base_delay_s * 2**attempt + random.uniform(0, 0.5)
                        logger.warning(
                            "%s on %s, retrying in %.1fs", type(exc).__name__, model, delay
                        )
                        self._sleep(delay)
                except NEXT_MODEL_ERRORS as exc:
                    errors.append(f"{model}: {type(exc).__name__}")
                    break
            logger.warning("Model %s failed, trying next model", model)
        raise AllModelsFailedError("All models failed: " + "; ".join(errors))

    def _call(
        self,
        model: str,
        messages: list[dict[str, Any]],
        tools: list[dict[str, Any]] | None,
        max_tokens: int,
    ) -> LLMResponse:
        kwargs: dict[str, Any] = {
            "model": model,
            "messages": messages,
            "api_key": self._api_key,
            "timeout": self._timeout_s,
            "max_tokens": max_tokens,
        }
        if tools:
            kwargs["tools"] = tools

        t0 = time.perf_counter()
        resp = self._completion(**kwargs)
        latency_ms = (time.perf_counter() - t0) * 1000

        msg = resp.choices[0].message
        tool_calls = [
            ToolCall(id=tc.id, name=tc.function.name, arguments=tc.function.arguments or "{}")
            for tc in (msg.tool_calls or [])
        ]
        usage = getattr(resp, "usage", None)
        return LLMResponse(
            content=msg.content,
            tool_calls=tool_calls,
            model=model,
            latency_ms=latency_ms,
            input_tokens=int(getattr(usage, "prompt_tokens", 0) or 0),
            output_tokens=int(getattr(usage, "completion_tokens", 0) or 0),
        )


def build_client() -> LLMClient:
    """Create the client from settings: primary model first, then fallback."""
    s = get_settings()
    return LLMClient(
        [s.primary_model, s.fallback_model],
        api_key=s.groq_api_key.get_secret_value(),
    )
