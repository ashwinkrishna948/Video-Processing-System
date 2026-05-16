"""Stage 1: SRT parsing and Gemini-based subtitle formatting."""
from __future__ import annotations

import os
import re

from google import genai
from google.genai import types

MAX_BLOCKS_PER_CALL = 30
WORDS_PER_SECOND    = 2.5
GAP_MS              = 200
MIN_DUR_S           = 1.5

_SRT_RE = re.compile(
    r"(\d+)\s*\n(\d{2}:\d{2}:\d{2}[,\.]\d{3})\s*-->\s*(\d{2}:\d{2}:\d{2}[,\.]\d{3})\s*\n"
    r"([\s\S]*?)(?=\n\s*\n\d+\s*\n|\n\s*\Z|\Z)",
    re.MULTILINE,
)

_SRT_SYSTEM = """\
Reformat this SRT into correctly split subtitles. English only — do NOT translate.
Rules: ≤42 chars/line, ≤2 lines/block, break at natural boundaries.
Never split: Pronoun+Verb, Determiner+Noun, Preposition+phrase, Conjunction+clause, complex verbs.
Punctuation at END of line only. Preserve timecodes exactly.
OUTPUT: valid SRT only, no preamble."""

_TXT_SYSTEM = f"""\
Convert this transcript into SRT subtitles. English only.
4-10 words per block, ≤42 chars/line, ≤2 lines/block.
Timecodes: start 00:00:00,000, duration=words/{WORDS_PER_SECOND}s min {MIN_DUR_S}s, {GAP_MS}ms gap.
Never split word pairs. Punctuation at end of line only.
OUTPUT: valid SRT only, no preamble."""


def parse_srt(text: str) -> list[dict]:
    blocks = []
    for m in _SRT_RE.finditer(text.strip() + "\n\n"):
        raw = m.group(4).strip()
        if raw:
            blocks.append({
                "index": int(m.group(1)),
                "start": m.group(2).replace(".", ","),
                "end":   m.group(3).replace(".", ","),
                "text":  raw,
            })
    return blocks


def merge_bilingual(formatted_srt: str, translations: list[str]) -> str:
    blocks = parse_srt(formatted_srt)
    translations = (translations + [""] * len(blocks))[: len(blocks)]
    lines = []
    for block, trans in zip(blocks, translations):
        lines += [str(block["index"]), f"{block['start']} --> {block['end']}", block["text"]]
        if trans:
            lines.append(trans)
        lines.append("")
    return "\n".join(lines).rstrip() + "\n"


def _renumber(srt: str, start: int = 1) -> str:
    counter = [start]
    def _sub(m):
        n = counter[0]; counter[0] += 1; return str(n)
    return re.sub(r"(?m)^\d+$", _sub, srt.strip())


def _gemini_call(system: str, user: str) -> str:
    key = os.getenv("GEMINI_API_KEY")
    if not key:
        raise EnvironmentError("GEMINI_API_KEY not set in .env")
    client = genai.Client(api_key=key)
    model  = os.getenv("GEMINI_MODEL", "gemini-2.5-flash")
    resp = client.models.generate_content(
        model=model,
        contents=user,
        config=types.GenerateContentConfig(
            system_instruction=system,
            temperature=0.2,
            max_output_tokens=8192,
        ),
    )
    return resp.text.strip()


def _blocks_to_user(blocks: list[dict]) -> str:
    return "\n".join(
        line for b in blocks
        for line in [str(b["index"]), f"{b['start']} --> {b['end']}", b["text"], ""]
    )


def format_subtitles(blocks: list[dict] | None, raw_text: str | None) -> str:
    """Format SRT blocks or raw text into clean English-only SRT."""
    if blocks is not None:
        if len(blocks) <= MAX_BLOCKS_PER_CALL:
            return _gemini_call(_SRT_SYSTEM, _blocks_to_user(blocks))
        parts, idx = [], 1
        for i in range(0, len(blocks), MAX_BLOCKS_PER_CALL):
            chunk = blocks[i: i + MAX_BLOCKS_PER_CALL]
            raw = _gemini_call(_SRT_SYSTEM, _blocks_to_user(chunk))
            renumbered = _renumber(raw, start=idx)
            parts.append(renumbered)
            idx += len(re.findall(r"(?m)^\d+$", renumbered))
        return "\n\n".join(parts)
    return _gemini_call(_TXT_SYSTEM, (raw_text or "").strip())
