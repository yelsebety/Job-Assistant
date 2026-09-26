"""
Thin, provider-agnostic-ish wrapper around the LLM call.
Everything that talks to Gemini lives here — swap providers by
editing only this file.
"""

import os
import json
import time
from google import genai
from google.genai import types
from google.genai import errors as genai_errors

_client = None

# Primary model, plus fallbacks to try if it's overloaded (503) or briefly
# unavailable. Order matters: fastest/cheapest first.
#
# Google retires Gemini models on a rolling schedule (check
# https://ai.google.dev/gemini-api/docs/deprecations before assuming these
# are still current) — gemini-2.5-flash was deliberately left out of this
# list since it's slated for shutdown October 2026.
MODEL_CANDIDATES = ["gemini-3.6-flash", "gemini-3.5-flash", "gemini-3.1-flash-lite"]

MAX_RETRIES_PER_MODEL = 3
BASE_BACKOFF_SECONDS = 2


def _get_client() -> genai.Client:
    global _client
    if _client is None:
        api_key = os.environ.get("GEMINI_API_KEY")
        if not api_key:
            raise RuntimeError(
                "GEMINI_API_KEY is not set. Add it to your .env file."
            )
        _client = genai.Client(api_key=api_key)
    return _client


def _call_model(client: genai.Client, model: str, prompt: str):
    return client.models.generate_content(
        model=model,
        contents=prompt,
        config=types.GenerateContentConfig(
            response_mime_type="application/json",
            temperature=0.4,
        ),
    )


def generate_json(prompt: str) -> dict:
    """Sends a prompt, expects a JSON object back, parses and returns it.

    Retries with exponential backoff on 503 (overloaded) errors, and falls
    through to backup models if a given model keeps failing.
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
            except genai_errors.ServerError as e:
                # 503 UNAVAILABLE / high demand — worth retrying, and worth
                # trying the next model if this one is consistently down.
                last_error = e
                if attempt < MAX_RETRIES_PER_MODEL:
                    time.sleep(BASE_BACKOFF_SECONDS * attempt)
                # else: fall through to the next model below
            except genai_errors.ClientError as e:
                # 4xx errors (bad key, invalid model name, bad request) won't
                # be fixed by retrying or switching models — fail fast.
                raise RuntimeError(f"Gemini API call failed: {e}") from e
            except Exception as e:
                raise RuntimeError(f"Gemini API call failed: {e}") from e

        if model_succeeded:
            break  # stop trying other models

    if response is None:
        raise RuntimeError(
            "All Gemini models are currently overloaded or unavailable. "
            f"Last error: {last_error}. Please try again in a minute."
        )

    raw_text = (response.text or "").strip()

    try:
        return json.loads(raw_text)
    except json.JSONDecodeError as e:
        raise RuntimeError(
            f"Model did not return valid JSON. Raw output: {raw_text[:500]}"
        ) from e

