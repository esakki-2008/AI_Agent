from fastapi import FastAPI, UploadFile, File, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from pathlib import Path
import shutil
import subprocess
import tempfile
import uuid
import re

import imageio_ffmpeg

BASE_DIR = Path(__file__).resolve().parent.parent
UPLOAD_DIR = BASE_DIR / "uploads"
OUTPUT_DIR = BASE_DIR / "outputs"
UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

FFMPEG = imageio_ffmpeg.get_ffmpeg_exe()

app = FastAPI(title="AI Short Clip Generator", version="1.0.0")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

ALLOWED = {".mp4", ".mov", ".mkv", ".avi", ".webm", ".m4v"}
KEYWORDS = {
    "amazing", "important", "secret", "mistake", "problem", "solution",
    "best", "worst", "never", "always", "how", "why", "truth", "tip",
    "tips", "learn", "learned", "money", "success", "failure", "hack",
    "easy", "hard", "avoid", "remember", "key", "reason", "idea",
    "difference", "powerful", "simple", "actually", "real", "wrong"
}


def run_ffmpeg(args: list[str]) -> subprocess.CompletedProcess:
    return subprocess.run(
        [FFMPEG, *args],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        encoding="utf-8",
        errors="replace",
    )


def get_duration(path: Path) -> float:
    result = run_ffmpeg(["-i", str(path)])
    match = re.search(r"Duration:\s*(\d+):(\d+):([\d.]+)", result.stderr)
    if not match:
        return 0.0
    return int(match.group(1)) * 3600 + int(match.group(2)) * 60 + float(match.group(3))


def has_audio(path: Path) -> bool:
    result = run_ffmpeg(["-i", str(path)])
    return bool(re.search(r"Stream #.*Audio:", result.stderr, re.I))


def transcribe(path: Path) -> dict:
    try:
        import whisper
        model = whisper.load_model("base")
        return model.transcribe(str(path), fp16=False)
    except Exception as exc:
        print("Whisper unavailable/error:", exc)
        return {"text": "", "segments": []}


def detect_highlights(transcription: dict, video_duration: float) -> list[dict]:
    segments = transcription.get("segments", []) or []
    candidates = []

    for segment in segments:
        text = (segment.get("text") or "").strip()
        if not text:
            continue
        start = float(segment.get("start", 0))
        end = float(segment.get("end", start + 1))
        lower = text.lower()
        score = 50
        score += min(24, sum(4 for word in KEYWORDS if word in lower))
        if "?" in text:
            score += 10
        if "!" in text:
            score += 6
        if len(text) >= 50:
            score += 5
        if len(text) >= 100:
            score += 5
        if "you" in lower or "your" in lower:
            score += 4
        if re.search(r"\b\d+\b", text):
            score += 4
        candidates.append({"start": start, "end": end, "text": text, "score": min(score, 100)})

    if not candidates:
        d = min(video_duration, 30)
        return [{"start": 0, "duration": d, "end": d, "text": "", "score": 50}]

    candidates.sort(key=lambda x: x["score"], reverse=True)
    selected = []
    for c in candidates:
        start = max(0, c["start"] - 5)
        end = min(video_duration, c["end"] + 10)
        if end - start < 15:
            end = min(video_duration, start + 30)
        if end - start > 45:
            end = start + 45
        if end - start < 8:
            continue
        if any(start < x["end"] and end > x["start"] for x in selected):
            continue
        selected.append({"start": start, "duration": end - start, "end": end, "text": c["text"], "score": c["score"]})
        if len(selected) == 5:
            break

    selected.sort(key=lambda x: x["start"])
    return selected or [{"start": 0, "duration": min(video_duration, 30), "end": min(video_duration, 30), "text": "", "score": 50}]


def create_short(input_file: Path, output_file: Path, start: float, duration: float) -> None:
    result = run_ffmpeg([
        "-y", "-ss", str(start), "-i", str(input_file), "-t", str(duration),
        "-vf", "scale=1080:1920:force_original_aspect_ratio=increase,crop=1080:1920",
        "-c:v", "libx264", "-preset", "veryfast", "-crf", "23",
        "-c:a", "aac", "-b:a", "128k", "-movflags", "+faststart", str(output_file)
    ])
    if result.returncode != 0:
        raise RuntimeError(result.stderr[-2000:])


@app.get("/")
def home():
    return {"status": "running", "message": "AI Short Clip Generator", "version": "1.0.0"}


@app.get("/health")
def health():
    return {"status": "ok", "ffmpeg": bool(FFMPEG)}


@app.post("/process")
async def process_video(file: UploadFile = File(...)):
    if not file.filename:
        raise HTTPException(400, "No video file provided")
    ext = Path(file.filename).suffix.lower()
    if ext not in ALLOWED:
        raise HTTPException(400, f"Unsupported format: {ext}")

    job_id = str(uuid.uuid4())
    input_file = UPLOAD_DIR / f"{job_id}{ext}"
    with input_file.open("wb") as buffer:
        shutil.copyfileobj(file.file, buffer)

    try:
        duration = get_duration(input_file)
        if duration <= 0:
            raise RuntimeError("Could not read video duration")

        audio = has_audio(input_file)
        transcript = transcribe(input_file) if audio else {"text": "", "segments": []}
        highlights = detect_highlights(transcript, duration)
        clips = []

        for i, h in enumerate(highlights, 1):
            output_file = OUTPUT_DIR / f"{job_id}_clip_{i}.mp4"
            create_short(input_file, output_file, h["start"], h["duration"])
            clips.append({
                "clip_number": i,
                "title": f"AI Short #{i}",
                "score": h["score"],
                "text": h["text"],
                "start": round(h["start"], 2),
                "duration": round(h["duration"], 2),
                "file": f"/download/{output_file.name}",
            })

        return {
            "status": "completed",
            "job_id": job_id,
            "duration": round(duration, 2),
            "has_audio": audio,
            "transcript": transcript.get("text", "") or "",
            "number_of_clips": len(clips),
            "clips": clips,
        }
    except Exception as exc:
        print("PROCESSING ERROR:", repr(exc))
        raise HTTPException(500, f"Video processing failed: {exc}") from exc


@app.get("/download/{filename}")
def download_clip(filename: str):
    requested = (OUTPUT_DIR / filename).resolve()
    if OUTPUT_DIR.resolve() not in requested.parents:
        raise HTTPException(403, "Invalid file path")
    if not requested.exists():
        raise HTTPException(404, "Clip not found")
    return FileResponse(str(requested), media_type="video/mp4", filename=requested.name)
