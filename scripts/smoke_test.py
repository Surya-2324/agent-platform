import sys
import time

import psycopg
from litellm import completion

from agent_platform.config import get_settings


def check_db() -> bool:
    settings = get_settings()
    try:
        with psycopg.connect(settings.database_url, connect_timeout=5) as conn:
            row = conn.execute("SELECT count(*) FROM orders").fetchone()
        print(f"[OK]   Postgres: {row[0] if row else '?'} orders")
        return True
    except Exception as exc:
        print(f"[FAIL] Postgres: {type(exc).__name__}: {exc}")
        return False


def check_llm(model: str) -> bool:
    settings = get_settings()
    t0 = time.perf_counter()
    try:
        resp = completion(
            model=model,
            api_key=settings.groq_api_key.get_secret_value(),
            messages=[{"role": "user", "content": "Reply with exactly one word: pong"}],
            max_tokens=200,
        )
    except Exception as exc:
        print(f"[FAIL] {model}: {type(exc).__name__}: {exc}")
        return False

    ms = (time.perf_counter() - t0) * 1000
    usage = resp.usage
    text = (resp.choices[0].message.content or "").strip()
    print(
        f"[OK] {model}:'{text}' | {ms:.0f} ms | "
        f"in={usage.prompt_tokens} out = {usage.completion_tokens} tokens"
    )
    return True


if __name__ == "__main__":
    s = get_settings()
    results = [check_db(), check_llm(s.primary_model), check_llm(s.fallback_model)]
    print("\nALL CHECKS PASSED" if all(results) else "\nSOME CHECKS FAILED")
    sys.exit(0 if all(results) else 1)
