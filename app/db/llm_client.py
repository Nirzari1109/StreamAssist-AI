"""
LLM client using an OpenAI-compatible API.

Supports:
- OpenAI-compatible providers such as OpenAI and Groq
- Langfuse tracing when LANGFUSE_ENABLED=true and Langfuse keys are present
- latency logging
- token usage logging
- retry with exponential backoff
- timeout protection
- JSON repair fallback
"""
import os
import json
import time
import asyncio
from typing import Optional

from app.observability.logger import get_logger

logger = get_logger(__name__)

LANGFUSE_ENABLED = os.getenv("LANGFUSE_ENABLED", "false").lower() == "true"
LANGFUSE_PUBLIC_KEY = os.getenv("LANGFUSE_PUBLIC_KEY", "")
LANGFUSE_SECRET_KEY = os.getenv("LANGFUSE_SECRET_KEY", "")

if LANGFUSE_ENABLED and LANGFUSE_PUBLIC_KEY and LANGFUSE_SECRET_KEY:
    from langfuse.openai import AsyncOpenAI
    LANGFUSE_ACTIVE = True
else:
    from openai import AsyncOpenAI
    LANGFUSE_ACTIVE = False


_client: Optional[AsyncOpenAI] = None

OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "")
OPENAI_BASE_URL = os.getenv("OPENAI_BASE_URL", "https://api.openai.com/v1")
MODEL = os.getenv("LLM_MODEL", "gpt-4o-mini")

LLM_TIMEOUT_SECONDS = float(os.getenv("LLM_TIMEOUT_SECONDS", "30"))
LLM_MAX_RETRIES = int(os.getenv("LLM_MAX_RETRIES", "2"))


def get_client() -> AsyncOpenAI:
    global _client

    if _client is None:
        if not OPENAI_API_KEY:
            raise RuntimeError("OPENAI_API_KEY is not set")

        _client = AsyncOpenAI(
            api_key=OPENAI_API_KEY,
            base_url=OPENAI_BASE_URL,
            timeout=LLM_TIMEOUT_SECONDS,
            max_retries=0,
        )

        logger.info(
            "llm_client_initialized",
            extra={
                "model": MODEL,
                "base_url": OPENAI_BASE_URL,
                "langfuse_active": LANGFUSE_ACTIVE,
            },
        )

    return _client


async def chat(
    system: str,
    user: str,
    temperature: float = 0.2,
    max_tokens: int = 800,
    json_mode: bool = False,
) -> str:
    client = get_client()

    kwargs = {
        "model": MODEL,
        "messages": [
            {"role": "system", "content": system},
            {"role": "user", "content": user},
        ],
        "temperature": temperature,
        "max_tokens": max_tokens,
    }

    if json_mode:
        kwargs["response_format"] = {"type": "json_object"}

    last_error: Exception | None = None

    for attempt in range(LLM_MAX_RETRIES + 1):
        start_time = time.perf_counter()

        try:
            response = await client.chat.completions.create(**kwargs)
            latency_ms = round((time.perf_counter() - start_time) * 1000, 2)

            usage = getattr(response, "usage", None)
            prompt_tokens = getattr(usage, "prompt_tokens", None) if usage else None
            completion_tokens = getattr(usage, "completion_tokens", None) if usage else None
            total_tokens = getattr(usage, "total_tokens", None) if usage else None

            logger.info(
                "llm_call",
                extra={
                    "model": MODEL,
                    "attempt": attempt + 1,
                    "max_attempts": LLM_MAX_RETRIES + 1,
                    "latency_ms": latency_ms,
                    "prompt_tokens": prompt_tokens,
                    "completion_tokens": completion_tokens,
                    "total_tokens": total_tokens,
                    "json_mode": json_mode,
                    "timeout_seconds": LLM_TIMEOUT_SECONDS,
                    "langfuse_active": LANGFUSE_ACTIVE,
                },
            )

            return response.choices[0].message.content or ""

        except Exception as exc:
            last_error = exc
            latency_ms = round((time.perf_counter() - start_time) * 1000, 2)

            logger.warning(
                "llm_call_failed",
                extra={
                    "model": MODEL,
                    "attempt": attempt + 1,
                    "max_attempts": LLM_MAX_RETRIES + 1,
                    "latency_ms": latency_ms,
                    "json_mode": json_mode,
                    "timeout_seconds": LLM_TIMEOUT_SECONDS,
                    "error": str(exc)[:300],
                    "langfuse_active": LANGFUSE_ACTIVE,
                },
            )

            if attempt >= LLM_MAX_RETRIES:
                logger.error(
                    "llm_call_exhausted_retries",
                    extra={
                        "model": MODEL,
                        "attempts": LLM_MAX_RETRIES + 1,
                        "error": str(exc)[:300],
                    },
                )
                raise

            backoff_seconds = 2 ** attempt
            await asyncio.sleep(backoff_seconds)

    raise last_error or RuntimeError("LLM call failed without captured exception")


async def chat_json(
    system: str,
    user: str,
    max_tokens: int = 600,
    temperature: float = 0.0,
) -> dict:
    """Chat and parse JSON response with repair fallback."""
    raw = await chat(
        system=system,
        user=user,
        json_mode=True,
        max_tokens=max_tokens,
        temperature=temperature,
    )

    try:
        return json.loads(raw)

    except json.JSONDecodeError:
        cleaned = raw.strip().lstrip("```json").lstrip("```").rstrip("```").strip()

        try:
            logger.info("llm_json_repair_success")
            return json.loads(cleaned)

        except json.JSONDecodeError:
            logger.warning("llm_json_repair_failed")
            return {"error": "parse_failure", "raw": raw[:200]}