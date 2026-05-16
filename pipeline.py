"""Video analysis pipeline — three sequential steps."""
from __future__ import annotations

import os
import uuid
from pathlib import Path

from dotenv import load_dotenv
load_dotenv()

from core.gemini_client import delete_file, upload_video
from core.gemini_processor import analyse_video
from core.report_generator import generate_report
from core.video_processor import download_video


def run(url: str) -> str:
    """Run the full pipeline. Returns path to XLS report."""
    output_dir = str(Path(os.getenv("OUTPUT_DIR", "./output")) / str(uuid.uuid4())[:8])
    cache_dir  = str(Path(output_dir) / "gemini_cache")

    print(f"\n[1/3] Downloading video...")
    video_path, title, duration, _ = download_video(url, output_dir)
    video_id = Path(video_path).stem
    print(f"[1/3] Done — '{title}' ({duration:.1f}s)")

    print(f"\n[2/3] Gemini analysis (model: {os.getenv('GEMINI_MODEL', 'gemini-2.5-flash')})...")
    file_uri, file_name = upload_video(video_path, cache_dir)
    analysis = analyse_video(file_uri, title, cache_dir)
    delete_file(file_name)
    print(f"[2/3] Done — {len(analysis.characters)} characters, genre={analysis.genre}")

    print(f"\n[3/3] Generating XLS report...")
    report_path = generate_report(analysis, output_dir, url, video_id, title, duration)
    print(f"[3/3] Done — {report_path}")

    return report_path
