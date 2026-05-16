"""Orchestrates the 3-call Gemini video analysis pipeline.

Call 1 → character tracking (must finish first — 2+3 need its character IDs)
Call 2 → transcript + scenes  } independent — run in parallel
Call 3 → editorial analysis   }
"""
from __future__ import annotations

import os
from concurrent.futures import ThreadPoolExecutor, as_completed

from core.gemini_cache import load_cache, save_cache
from core.gemini_client import (
    CharacterDiscovery, EditorialAnalysis, TemporalBreakdown,
    generate, upload_video, delete_file,
)
from core.gemini_prompts import CALL1_PROMPT, CALL2_PROMPT, CALL3_PROMPT
from models.gemini_responses import VideoAnalysis, VideoCharacter


def _cfg(key: str, default: str) -> str:
    return os.getenv(key, default)


def analyse_video(file_uri: str, title: str, cache_dir: str) -> VideoAnalysis:

    # ── Call 1: Character tracking ────────────────────────────────────────────
    c1 = load_cache(cache_dir, "call1_characters", CharacterDiscovery)
    if c1 is None:
        print("  [Call 1/3] Character tracking + clip selection...")
        c1 = generate(
            file_uri,
            CALL1_PROMPT.format(
                title=title,
                top_chars=_cfg("TOP_CHARACTERS", "5"),
                top_clips=_cfg("TOP_CLIPS_PER_CHARACTER", "3"),
                min_clip=_cfg("MIN_CLIP_DURATION", "5.0"),
            ),
            CharacterDiscovery, "call1_characters",
        )
        save_cache(cache_dir, "call1_characters", c1)

    print(f"  → {len(c1.characters)} characters: "
          + " | ".join(f"{c.character_id}={c.name} ({c.total_screen_time_seconds:.0f}s)"
                       for c in c1.characters))

    char_ids   = ", ".join(c.character_id for c in c1.characters)
    char_roster = "; ".join(f"{c.character_id}={c.name}" for c in c1.characters)

    # ── Calls 2 + 3: independent — run in parallel ────────────────────────────
    c2 = load_cache(cache_dir, "call2_temporal", TemporalBreakdown)
    c3 = load_cache(cache_dir, "call3_editorial", EditorialAnalysis)

    pending = {}
    if c2 is None:
        pending["call2"] = (
            CALL2_PROMPT.format(title=title, char_ids=char_ids, char_roster=char_roster),
            TemporalBreakdown, "call2_temporal",
        )
    if c3 is None:
        pending["call3"] = (
            CALL3_PROMPT.format(
                title=title,
                top_dialogues=_cfg("TOP_PUNCHY_DIALOGUES", "5"),
                char_roster=char_roster,
            ),
            EditorialAnalysis, "call3_editorial",
        )

    if pending:
        print(f"  [Calls {'+'.join(pending)} / 3] Running in parallel...")
        results: dict[str, object] = {}
        with ThreadPoolExecutor(max_workers=2) as pool:
            futures = {
                pool.submit(generate, file_uri, prompt, schema, call_name): tag
                for tag, (prompt, schema, call_name) in pending.items()
            }
            for fut in as_completed(futures):
                tag = futures[fut]
                _, _, call_name = pending[tag]
                result = fut.result()
                results[tag] = result
                save_cache(cache_dir, call_name, result)
        if "call2" in results:
            c2 = results["call2"]
        if "call3" in results:
            c3 = results["call3"]

    print(f"  → {len(c2.scene_summaries)} scene summaries")
    print(f"  → genre={c3.genre}, {len(c3.punchy_dialogues)} punchy dialogues")

    return VideoAnalysis(
        characters=[
            VideoCharacter(
                character_id=c.character_id, name=c.name, description=c.description,
                total_screen_time_seconds=c.total_screen_time_seconds,
                top_clips=c.top_clips,
            )
            for c in c1.characters
        ],
        punchy_dialogues=c3.punchy_dialogues,
        genre=c3.genre,
        visual_summary=c3.visual_summary,
        scene_summaries=c2.scene_summaries,
    )
