# ADR 0001: Use LiteLLM as the LLM gateway

**Status:** Accepted · **Date:** 2026-11-15

## Context
The project must run on free tiers, which have strict per-model rate limits.
We need to switch models (and possibly providers) without rewriting code,
and we need uniform token/latency data for observability.

## Decision
All LLM calls go through LiteLLM. Models are set in config
(PRIMARY_MODEL, FALLBACK_MODEL), with automatic fallback when the primary fails.

## Alternatives considered
- **Groq SDK directly** — simple, but locks us to one provider; switching = code rewrite.
- **LangChain chat models** — works, but a heavy dependency for just model calls.
- **Raw HTTP calls** — maximum control, but we'd rebuild retries, parsing and usage tracking ourselves.

## Consequences
+ Swap models/providers by editing `.env` only
+ One response format and usage data across all models
− One more dependency to keep updated
− Provider-specific features may be hidden behind the common interface
