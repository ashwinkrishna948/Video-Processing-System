"""Stage 2: Sarvam mayura:v1 translation with Gemini fallback."""
from __future__ import annotations

import os
import time
from concurrent.futures import ThreadPoolExecutor, as_completed

from sarvamai import SarvamAI

SARVAM_LANG_CODES: dict[str, str] = {
    "hindi": "hi-IN", "bengali": "bn-IN", "gujarati": "gu-IN",
    "kannada": "kn-IN", "malayalam": "ml-IN", "marathi": "mr-IN",
    "odia": "od-IN", "punjabi": "pa-IN", "tamil": "ta-IN", "telugu": "te-IN",
}
SARVAM_MODEL   = "mayura:v1"
DEFAULT_WORKERS = 8


def _gemini_translate(text: str, lang: str) -> str:
    """Translate one block via Gemini — used as fallback."""
    key = os.getenv("GEMINI_API_KEY", "")
    if not key or not text.strip():
        return ""
    try:
        from google import genai
        resp = genai.Client(api_key=key).models.generate_content(
            model="gemini-2.5-flash",
            contents=(f"Translate into {lang} for subtitles. "
                      f"Output ONLY the translation.\n\n{text}"),
        )
        return resp.text.strip()
    except Exception:
        return ""


class SarvamTranslator:
    """Translates via Sarvam mayura:v1, falls back to Gemini on failure."""

    def __init__(self, api_key: str, lang_code: str) -> None:
        self._client    = SarvamAI(api_subscription_key=api_key)
        self._lang_code = lang_code
        self._lang_name = next(
            (k for k, v in SARVAM_LANG_CODES.items() if v == lang_code), lang_code
        )

    def translate_one(self, text: str) -> str:
        if not text.strip():
            return ""
        for attempt in range(3):
            try:
                resp = self._client.text.translate(
                    input=text, source_language_code="en-IN",
                    target_language_code=self._lang_code, model=SARVAM_MODEL,
                )
                return (resp.translated_text or "").strip()
            except Exception:
                if attempt == 2:
                    return _gemini_translate(text, self._lang_name)
                time.sleep(2 ** attempt)
        return ""

    def translate_batch(self, texts: list[str],
                        max_workers: int = DEFAULT_WORKERS) -> list[str]:
        results: dict[int, str] = {}
        with ThreadPoolExecutor(max_workers=max_workers) as pool:
            futures = {pool.submit(self.translate_one, t): i for i, t in enumerate(texts)}
            done, total = 0, len(futures)
            for fut in as_completed(futures):
                idx = futures[fut]
                results[idx] = fut.result() if not fut.exception() else ""
                done += 1
                if done % 20 == 0 or done == total:
                    print(f"  Translated {done}/{total} blocks…")
        return [results[i] for i in range(len(texts))]


def translate_batch_gemini(texts: list[str], lang: str,
                           max_workers: int = DEFAULT_WORKERS) -> list[str]:
    """Translate via Gemini — used for non-Indic languages."""
    results: dict[int, str] = {}
    with ThreadPoolExecutor(max_workers=max_workers) as pool:
        futures = {pool.submit(_gemini_translate, t, lang): i for i, t in enumerate(texts)}
        done, total = 0, len(futures)
        for fut in as_completed(futures):
            idx = futures[fut]
            results[idx] = fut.result() if not fut.exception() else ""
            done += 1
            if done % 20 == 0 or done == total:
                print(f"  Translated {done}/{total} blocks…")
    return [results[i] for i in range(len(texts))]
