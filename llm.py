"""
Thin, provider-agnostic-ish wrapper around the LLM call.
Everything that talks to Groq lives here — swap providers by editing
only this file.
"""

import os
import json
import time
from groq import Groq
import groq as groq_errors

_client = None

# Primary model, plus fallbacks to try if one is rate-limited, overloaded,
# or briefly unavailable. Order matters: best quality first, then faster/
# smaller models from different model families (so one family's outage or
# rate limit doesn't take down every fallback at once).
#
# Groq retires/renames models on its own schedule — check
# https://console.groq.com/docs/models before assuming these are current.
MODEL_CANDIDATES = ["openai/gpt-oss-120b", "openai/gpt-oss-20b", "qwen/qwen3.8-27b"]


MAX_RETRIES_PER_MODEL = 3
BASE_BACKOFF_SECONDS = 2

# Errors worth retrying / falling back to the next model on: rate limits,
# server-side errors, and connection hiccups. None of these mean the
# request itself was wrong.
RETRYABLE_ERRORS = (
    groq_errors.RateLimitError,       # 429 — quota/rate limit hit
    groq_errors.InternalServerError,  # 5xx — provider-side failure
    groq_errors.APIConnectionError,   # network-level failure
    groq_errors.APITimeoutError,      # request timed out
)


def _get_client() -> Groq:
    global _client
    if _client is None:
        api_key = os.environ.get("GROQ_API_KEY")
        if not api_key:
            raise RuntimeError(
                "GROQ_API_KEY is not set. Add it to your .env file."
            )
        _client = Groq(api_key=api_key, max_retries=0)  # we handle retries ourselves
    return _client


def _call_model(client: Groq, model: str, prompt: str):
    return client.chat.completions.create(
        model=model,
        messages=[{"role": "user", "content": prompt}],
        response_format={"type": "json_object"},
        temperature=0.4,
    )


def generate_json(prompt: str) -> dict:
    """Sends a prompt, expects a JSON object back, parses and returns it.

    Retries with exponential backoff on rate-limit/server errors, and falls
    through to backup models if a given model keeps failing. This matters
    in particular for 429s: a per-model daily/rate quota being exhausted
    should not kill the whole request if another model still has room.
    """
    client = _get_client()
    last_error: Exception | None = None
    response = None

    for model in MODEL_CANDIDATES:
        model_succeeded = False

        for attempt in range(1, MAX_RETRIES_PER_MODEL + 1):
            try:
                response = _call_model(client, model, prompt)
                model_succeeded = True
                break  # success — stop retrying this model
            except RETRYABLE_ERRORS as e:
                last_error = e
                if attempt < MAX_RETRIES_PER_MODEL:
                    time.sleep(BASE_BACKOFF_SECONDS * attempt)
                # else: fall through to the next model below
            except groq_errors.APIStatusError as e:
                # Non-retryable 4xx (bad key, bad request, etc.) — fail fast.
                raise RuntimeError(f"Groq API call failed: {e}") from e
            except Exception as e:
                raise RuntimeError(f"Groq API call failed: {e}") from e

        if model_succeeded:
            break  # stop trying other models

    if response is None:
        raise RuntimeError(
            "All Groq models are currently rate-limited or unavailable. "
            f"Last error: {last_error}. Please try again in a minute."
        )

    raw_text = (response.choices[0].message.content or "").strip()

    try:
        return json.loads(raw_text)
    except json.JSONDecodeError as e:
        raise RuntimeError(
            f"Model did not return valid JSON. Raw output: {raw_text[:500]}"
        ) from e
