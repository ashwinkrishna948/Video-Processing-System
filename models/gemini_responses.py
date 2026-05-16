"""Pydantic models for Gemini's structured video analysis response."""
from __future__ import annotations
from pydantic import BaseModel


class ClipRecommendation(BaseModel):
    start_sec: float
    end_sec: float
    title: str
    reasoning: str


class VideoCharacter(BaseModel):
    character_id: str
    name: str
    description: str
    total_screen_time_seconds: float
    top_clips: list[ClipRecommendation]


class PunchyLine(BaseModel):
    rank: int
    text: str
    speaker: str
    start_sec: float
    end_sec: float
    reasoning: str


class SceneSummary(BaseModel):
    start_sec: float
    end_sec: float
    characters_present: list[str]   # character_ids visible in this segment


class VideoAnalysis(BaseModel):
    characters: list[VideoCharacter]
    punchy_dialogues: list[PunchyLine]
    genre: str
    visual_summary: str
    scene_summaries: list[SceneSummary]
