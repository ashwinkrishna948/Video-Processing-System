"""Prompt strings for the 3 focused Gemini API calls.

Kept separate from client/orchestration so editorial content
can be iterated without touching transport or caching logic.
"""

CALL1_PROMPT = """Watch this entire video titled "{title}".

TASK: Identify the top {top_chars} characters by total screen time and select their best clips.

IDENTIFY EACH CHARACTER:
• Same face across all scenes = same person (ignore clothing changes).
• Name: use it if spoken in dialogue or shown on screen. Otherwise write a precise
  one-line descriptor — "Heavyset man, 50s, grey stubble, white kurta" not "Unknown".
• total_screen_time_seconds: your best estimate of total seconds on screen.

TOP CLIPS ({top_clips} per character, each ≥ {min_clip}s):
• Choose moments with strong dialogue, clear emotion, or comedy.
• Give each a catchy title (max 8 words) and one-sentence reasoning.
• Timestamps precise to 0.5 seconds.

Keep output minimal — no appearance lists, just screen time totals and clips.

OUTPUT FORMAT:
{{
  "characters": [
    {{
      "character_id": "C1",
      "name": "<spoken name or physical descriptor>",
      "description": "<one-line appearance summary>",
      "total_screen_time_seconds": 0.0,
      "top_clips": [
        {{"start_sec": 0.0, "end_sec": 0.0,
          "title": "<catchy clip title>",
          "reasoning": "<one sentence>"}}
      ]
    }}
  ]
}}"""


CALL2_PROMPT = """Watch this entire video titled "{title}".

TASK: Divide the full video into 45–60 second segments covering EVERY second with no gaps.
For each segment output ONLY: start_sec, end_sec, and which characters are visible.

Character IDs: {char_ids}
Reference: {char_roster}

OUTPUT FORMAT (nothing else):
{{
  "scene_summaries": [
    {{"start_sec": 0.0, "end_sec": 55.0, "characters_present": ["C1", "C2"]}},
    {{"start_sec": 55.0, "end_sec": 112.0, "characters_present": ["C3"]}}
  ]
}}"""


CALL3_PROMPT = """Watch this video titled "{title}".

TASK A — GENRE: Single label (Comedy, Drama, Action, Thriller, Romance, etc.)

TASK B — VISUAL SUMMARY: 2–3 sentences for a streaming catalogue.
Convey: setting, tone, key visual moments. Make it compelling.

TASK C — PUNCHY DIALOGUES: {top_dialogues} most memorable/impactful lines.
  Comedy → lines that land a laugh: timing, wordplay, absurdity, punchline
  Drama  → emotional weight: revelations, confrontations, declarations
  Action → iconic lines or tension amplifiers

For each line: exact spoken words, speaker, precise timestamps, one-sentence reasoning.

Character reference: {char_roster}

OUTPUT FORMAT:
{{
  "genre": "<single genre label>",
  "visual_summary": "<2-3 sentence catalogue description>",
  "punchy_dialogues": [
    {{"rank": 1, "text": "<exact spoken words>",
      "speaker": "<character name or descriptor>",
      "start_sec": 0.0, "end_sec": 0.0,
      "reasoning": "<one sentence>"}}
  ]
}}"""
