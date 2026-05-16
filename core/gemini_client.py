"""Gemini API client — upload, structured generation with retry/429/jitter/token logging."""
from __future__ import annotations

import os
import random
import time

from google import genai
from google.genai import types
from pydantic import BaseModel, ValidationError

from core.gemini_cache import load_file_uri, save_file_uri
from models.gemini_responses import (
    ClipRecommendation, PunchyLine, SceneSummary,
)

MAX_RETRIES       = 3
MAX_OUTPUT_TOKENS = 8192

_client: genai.Client | None = None


def get_client() -> genai.Client:
    global _client
    if _client is None:
        key = os.getenv("GEMINI_API_KEY")
        if not key:
            raise EnvironmentError("GEMINI_API_KEY not set in .env")
        _client = genai.Client(api_key=key)
    return _client


# ─── Intermediate schemas ─────────────────────────────────────────────────────

class IntermediateCharacter(BaseModel):
    character_id: str        # "C1"–"C5"
    name: str                # spoken name or physical descriptor
    description: str         # one-line identifier
    total_screen_time_seconds: float
    top_clips: list[ClipRecommendation]   # 3 clips, no full appearances list

class CharacterDiscovery(BaseModel):
    characters: list[IntermediateCharacter]

class TemporalBreakdown(BaseModel):
    scene_summaries: list[SceneSummary]

class EditorialAnalysis(BaseModel):
    genre: str
    visual_summary: str
    punchy_dialogues: list[PunchyLine]


# ─── Core generate ────────────────────────────────────────────────────────────

def generate(file_uri: str, prompt: str, schema: type, call_name: str) -> object:
    """Structured Gemini generation with retry, 429 separation, jitter, token logging."""
    client = get_client()
    model  = os.getenv("GEMINI_MODEL", "gemini-2.5-flash")
    error_context = ""

    for attempt in range(MAX_RETRIES):
        try:
            response = client.models.generate_content(
                model=model,
                contents=[
                    types.Part.from_uri(file_uri=file_uri, mime_type="video/mp4"),
                    prompt + error_context,
                ],
                config=types.GenerateContentConfig(
                    response_mime_type="application/json",
                    temperature=0.2 + attempt * 0.1,
                    max_output_tokens=MAX_OUTPUT_TOKENS,
                    thinking_config=types.ThinkingConfig(thinking_budget=0),
                ),
            )

            if hasattr(response, "usage_metadata") and response.usage_metadata:
                m = response.usage_metadata
                inp = getattr(m, "prompt_token_count", 0) or 0
                out = getattr(m, "candidates_token_count", 0) or 0
                print(f"  [{call_name}] tokens: {inp} in / {out} out")

            result = schema.model_validate_json(response.text)
            if attempt > 0:
                print(f"  [{call_name}] succeeded on attempt {attempt + 1}")
            return result

        except ValidationError as e:
            print(f"  [{call_name}] attempt {attempt+1}/{MAX_RETRIES} "
                  f"validation error: {str(e)[:100]}")
            error_context = (
                f"\n\n[CORRECTION NEEDED] Previous response failed schema validation:\n"
                f"{str(e)[:400]}\nFix these issues and return corrected JSON."
            )

        except Exception as e:
            err = str(e)
            if "429" in err or "quota" in err.lower() or "rate" in err.lower():
                wait = 60 + random.uniform(0, 10)
                print(f"  [{call_name}] rate limit — waiting {wait:.0f}s...")
                time.sleep(wait)
                continue
            print(f"  [{call_name}] attempt {attempt+1}/{MAX_RETRIES} error: {err[:100]}")
            error_context = (
                f"\n\n[RETRY] Previous attempt failed: {err[:200]}\n"
                f"Return valid JSON matching the schema."
            )
            if attempt < MAX_RETRIES - 1:
                time.sleep(2 ** attempt + random.uniform(0, 1))

    raise RuntimeError(f"Gemini call '{call_name}' failed after {MAX_RETRIES} attempts.")


# ─── Upload + delete ──────────────────────────────────────────────────────────

def upload_video(video_path: str, cache_dir: str) -> tuple[str, str]:
    """Upload video to Gemini Files API (skips if cached URI still valid)."""
    cached = load_file_uri(cache_dir)
    if cached:
        return cached

    client = get_client()
    print("  Uploading to Gemini Files API...")
    video_file = client.files.upload(file=video_path)

    print("  Waiting for Google to finish processing video frames...")
    while video_file.state.name == "PROCESSING":
        time.sleep(10)
        video_file = client.files.get(name=video_file.name)

    if video_file.state.name == "FAILED":
        raise RuntimeError(f"Gemini video processing failed: {video_file.error.message}")

    print(f"  Video ready: {video_file.uri}")
    save_file_uri(cache_dir, video_file.uri, video_file.name)
    return video_file.uri, video_file.name


def delete_file(file_name: str) -> None:
    try:
        get_client().files.delete(name=file_name)
        print("  Gemini file cleaned up.")
    except Exception as e:
        print(f"  [warn] Could not delete Gemini file: {e}")
