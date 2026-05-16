# Video Character & Clip Generation

Analyses a YouTube video using Google Gemini 2.5 Flash to identify the top 5 characters by screen time, recommend the best clips per character, surface punchy dialogues, and produce a structured Excel report.

Also includes a bilingual subtitle generator that formats any SRT/TXT transcript and translates it to Indic languages via Sarvam AI.

---

## How It Works

**Video pipeline (3 steps):**
1. Downloads the YouTube video via yt-dlp
2. Uploads to Gemini Files API → 3 focused inference calls (character tracking, scene segmentation, editorial analysis)
3. Generates an Excel report

**Subtitle pipeline (2 steps):**
1. Formats the transcript into clean SRT (42-char lines, 2-line max, word-pair rules) via Gemini
2. Translates each block via Sarvam mayura:v1 (Indic) or Gemini (other languages)

---

## Setup

### 1. Python dependencies

```bash
pip install google-genai sarvamai yt-dlp opencv-python openpyxl python-dotenv pydantic
```

### 2. API keys

Create a `.env` file in the project root:

```env
# Required for video analysis and subtitle formatting
GEMINI_API_KEY=your_gemini_api_key

# Required for Indic subtitle translation (Telugu, Hindi, Tamil, etc.)
SARVAM_API_KEY=your_sarvam_api_key
```

| Key | Where to get it |
|---|---|
| `GEMINI_API_KEY` | [Google AI Studio](https://aistudio.google.com) → Get API Key (free tier) |
| `SARVAM_API_KEY` | [Sarvam AI Dashboard](https://dashboard.sarvam.ai) → API Keys (free tier) |

### 3. System dependencies

- **ffmpeg** — required by yt-dlp for video merging  
  `brew install ffmpeg` (macOS) / `apt install ffmpeg` (Linux)

---

## Running

### Task 1 — Video analysis → Excel report

```bash
python main.py --url "https://www.youtube.com/watch?v=VIDEO_ID"
```

### Task 2 — Subtitle formatting + translation

```bash
# From an SRT file
python main.py --subtitle input.srt --lang Telugu

# From a plain text transcript
python main.py --subtitle transcript.txt --lang Hindi

# Specify output path
python main.py --subtitle input.srt --lang Tamil --output output.srt

# Run subtitle module directly
python -m subtitle input.srt --lang Telugu
```

Supported Indic languages: `Telugu`, `Hindi`, `Tamil`, `Kannada`, `Malayalam`, `Marathi`, `Bengali`, `Gujarati`, `Punjabi`, `Odia`

---

## Output

### Video pipeline

```
output/
  <job_id>/
    <video_id>.mp4                          # downloaded video
    report_<video_title>_<timestamp>.xlsx   # Excel report
    gemini_cache/                           # cached API results (enables fast reruns)
      gemini_call1_characters.json
      gemini_call2_temporal.json
      gemini_call3_editorial.json
      gemini_file_uri.json
```

**Excel report structure:**
- **Summary sheet** — video metadata, character screen time table, top 5 punchy dialogues
- **One sheet per character** — appearance blocks derived from scene data, top 3 recommended clips with titles and reasoning

### Subtitle pipeline

```
input_telugu.srt    # bilingual SRT: English line(s) + translated line per block
```

---

## Optional overrides (.env)

```env
GEMINI_MODEL=gemini-2.5-flash        # default model
TOP_CHARACTERS=5                      # number of characters to identify
TOP_CLIPS_PER_CHARACTER=3             # clips per character
MIN_CLIP_DURATION=5.0                 # minimum clip length in seconds
TOP_PUNCHY_DIALOGUES=5                # number of punchy dialogues
OUTPUT_DIR=./output                   # where reports are saved
```
