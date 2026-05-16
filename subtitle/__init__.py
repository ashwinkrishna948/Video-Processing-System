"""Bilingual SRT subtitle generator.

    python subtitle.py input.srt --lang Telugu
    python subtitle.py input.txt --lang Hindi --output out.srt
"""
from __future__ import annotations

import os
import re
import sys
from pathlib import Path

from dotenv import load_dotenv
load_dotenv()

from subtitle.format import format_subtitles, merge_bilingual, parse_srt
from subtitle.translate import SARVAM_LANG_CODES, SarvamTranslator, translate_batch_gemini


def run(input_path: str, lang: str, output: str = "", workers: int = 8) -> str:
    """Format and translate a subtitle file. Returns output path."""
    inp = Path(input_path)
    if not inp.exists():
        sys.exit(f"File not found: {input_path}")

    if not os.getenv("GEMINI_API_KEY"):
        sys.exit("GEMINI_API_KEY not set in .env")

    sarvam_key  = os.getenv("SARVAM_API_KEY", "")
    out_path    = output or str(inp.parent / f"{inp.stem}_{lang.lower()}.srt")
    sarvam_code = SARVAM_LANG_CODES.get(lang.lower())
    use_sarvam  = bool(sarvam_code and sarvam_key)

    text   = inp.read_text(encoding="utf-8")
    blocks = parse_srt(text) if inp.suffix.lower() == ".srt" else None

    print(f"\n[subtitles] {inp.name} → {out_path} | lang={lang}")
    print("[Stage 1] Formatting with Gemini...")
    formatted  = format_subtitles(blocks, None if blocks else text)
    fmt_blocks = parse_srt(formatted)
    print(f"  {len(fmt_blocks)} subtitle blocks formatted.")

    texts = [b["text"] for b in fmt_blocks]
    if use_sarvam:
        print(f"[Stage 2] Sarvam mayura:v1 ({workers} threads, Gemini fallback)...")
        translations = SarvamTranslator(sarvam_key, sarvam_code).translate_batch(
            texts, max_workers=workers
        )
    else:
        print(f"[Stage 2] Gemini 2.5 Flash — {lang} ({workers} threads)...")
        translations = translate_batch_gemini(texts, lang, max_workers=workers)

    final = merge_bilingual(formatted, translations)
    Path(out_path).write_text(final, encoding="utf-8")
    count = len(re.findall(r"(?m)^\d+$", final))
    print(f"Done — {count} blocks → {out_path}")
    return out_path


if __name__ == "__main__":
    import argparse
    p = argparse.ArgumentParser()
    p.add_argument("input")
    p.add_argument("--lang",    default="Telugu")
    p.add_argument("--output",  default="")
    p.add_argument("--workers", type=int, default=8)
    args = p.parse_args()
    run(args.input, args.lang, args.output, args.workers)
