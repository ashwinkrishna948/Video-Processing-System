"""Download YouTube video with yt-dlp."""
from __future__ import annotations

import json
import subprocess
from pathlib import Path

import cv2


def download_video(url: str, output_dir: str) -> tuple[str, str, float, float]:
    """Download YouTube video. Returns (video_path, title, duration_seconds, fps)."""
    out_path = Path(output_dir)
    out_path.mkdir(parents=True, exist_ok=True)
    template = str(out_path / "%(id)s.%(ext)s")

    subprocess.run(
        [
            "yt-dlp",
            "-f", "bestvideo[ext=mp4]+bestaudio[ext=m4a]/best[ext=mp4]/best",
            "--merge-output-format", "mp4",
            "--write-info-json",
            "-o", template,
            url,
        ],
        capture_output=True, text=True, check=True,
    )

    video_file = next(out_path.glob("*.mp4"), None)
    if video_file is None:
        raise FileNotFoundError("yt-dlp did not produce an mp4 file.")

    cap = cv2.VideoCapture(str(video_file))
    fps = cap.get(cv2.CAP_PROP_FPS) or 30.0
    total_frames = cap.get(cv2.CAP_PROP_FRAME_COUNT)
    duration = total_frames / fps
    cap.release()

    title = video_file.stem
    info_files = list(out_path.glob("*.info.json"))
    if info_files:
        with open(info_files[0]) as f:
            title = json.load(f).get("title", title)

    return str(video_file), title, duration, fps
