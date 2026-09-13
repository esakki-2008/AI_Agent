from pathlib import Path
import re
import shutil
import subprocess
import tempfile
import uuid

from fastapi import FastAPI, File, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
import imageio_ffmpeg

BASE_DIR = Path(__file__).resolve().parent.parent
UPLOAD_DIR = BASE_DIR / "uploads"
OUTPUT_DIR = BASE_DIR / "outputs"
UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

FFMPEG = imageio_ffmpeg.get_ffmpeg_exe()
ALLOWED_EXTENSIONS = {".mp4", ".mov", ".mkv", ".avi", ".webm", ".m4v"}
MAX_UPLOAD_BYTES = 2 * 1024 * 1024 * 1024

app = FastAPI(title="ClipForge AI", version="1.0.0", description="Local AI long-form video to Shorts generator")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


def run_ffmpeg(args: list[str]) -> subprocess.CompletedProcess:
    result = subprocess.run([FFMPEG, *args], stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
    if result.returncode != 0:
        raise RuntimeError(result.stderr[-5000:] or "FFmpeg failed")
    return result


def probe_video(path: Path) -> tuple[float, bool]:
    result = subprocess.run([FFMPEG, "-i", str(path)], stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
    match = re.search(r"Duration:\s*(\d+):(\d+):([\d.]+)", result.stderr)
    if not match:
        raise RuntimeError("Could not read video duration")
    duration = int(match.group(1)) * 3600 + int(match.group(2)) * 60 + float(match.group(3))
    return duration, bool(re.search(r"Stream .*?: Audio:", result.stderr))


def transcribe(path: Path) -> dict:
    try:
        import whisper
        model = whisper.load_model("base")
        return model.transcribe(str(path), fp16=False, verbose=False)
    except Exception as exc:
        print(f"Whisper unavailable/failed: {exc}")
        return {"text": "", "segments": []}


def score_segment(text: str) -> int:
    words = {"amazing", "important", "secret", "mistake", "problem", "solution", "best", "worst", "never", "always", "how", "why", "truth", "tip", "tips", "learn", "learned", "money", "success", "failure", "hack", "easy", "hard", "avoid", "key", "reason", "idea", "powerful", "actually", "real", "wrong"}
    lower = text.lower()
    score = 50 + sum(4 for w in words if re.search(rf"\b{re.escape(w)}\b", lower))
    if "?" in text: score += 10
    if "!" in text: score += 6
    if len(text) >= 50: score += 5
    if len(text) >= 100: score += 5
    if re.search(r"\b\d+\b", text): score += 4
    if "you" in lower or "your" in lower: score += 4
    return min(score, 100)


def detect_highlights(transcription: dict, video_duration: float) -> list[dict]:
    segments = transcription.get("segments", [])
    candidates = []
    for seg in segments:
        text = str(seg.get("text", "")).strip()
        if not text:
            continue
        start = float(seg.get("start", 0))
        end = float(seg.get("end", start + 1))
        candidates.append({"start": start, "end": end, "text": text, "score": score_segment(text)})

    if not candidates:
        return [{"start": 0, "duration": min(video_duration, 30), "end": min(video_duration, 30), "text": "", "score": 50}]

    candidates.sort(key=lambda x: x["score"], reverse=True)
    selected = []
    for c in candidates:
        start = max(0.0, c["start"] - 5)
        end = min(video_duration, c["end"] + 10)
        if end - start < 15:
            end = min(video_duration, start + 30)
        end = min(end, start + 45)
        if end - start < 8:
            continue
        if any(start < x["end"] and end > x["start"] for x in selected):
            continue
        selected.append({"start": start, "duration": end - start, "end": end, "text": c["text"], "score": c["score"]})
        if len(selected) == 5:
            break
    selected.sort(key=lambda x: x["start"])
    return selected or [{"start": 0, "duration": min(video_duration, 30), "end": min(video_duration, 30), "text": "", "score": 50}]


def make_ass(text: str, path: Path) -> None:
    safe = text.replace("{", "(").replace("}", ")").replace("\\", "\\\\")
    lines = [line.strip() for line in re.split(r"(?<=[.!?])\s+", safe) if line.strip()]
    if not lines:
        path.write_text("", encoding="utf-8")
        return
    events = []
    chunk = ""
    for line in lines:
        if len(chunk) + len(line) > 70 and chunk:
            events.append(chunk)
            chunk = line
        else:
            chunk = f"{chunk} {line}".strip()
    if chunk: events.append(chunk)
    ass = """[Script Info]\nScriptType: v4.00+\nPlayResX: 1080\nPlayResY: 1920\n\n[V4+ Styles]\nFormat: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding\nStyle: Default,Arial,72,&H00FFFFFF,&H00FFFFFF,&H00000000,&H99000000,1,0,0,0,100,100,0,0,1,5,2,2,60,60,250,1\n\n[Events]\nFormat: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text\n"""
    # Display the whole transcript excerpt as a centered caption for the clip.
    ass += "Dialogue: 0,0:00:00.00,9:59:59.00,Default,,0,0,0,," + "\\N".join(events[:4]) + "\n"
    path.write_text(ass, encoding="utf-8")


def create_short(input_file: Path, output_file: Path, start: float, duration: float, caption: str) -> None:
    with tempfile.NamedTemporaryFile(suffix=".ass", delete=False) as tmp:
        ass_path = Path(tmp.name)
    try:
        make_ass(caption, ass_path)
        vf = "scale=1080:1920:force_original_aspect_ratio=increase,crop=1080:1920"
        if caption:
            # FFmpeg's subtitles filter accepts the generated ASS file path.
            vf += f",subtitles='{str(ass_path).replace(chr(92), '/')}'"
        run_ffmpeg([
            "-y", "-ss", str(start), "-i", str(input_file), "-t", str(duration),
            "-vf", vf, "-c:v", "libx264", "-preset", "veryfast", "-crf", "23",
            "-c:a", "aac", "-b:a", "128k", "-movflags", "+faststart", str(output_file)
        ])
    finally:
        ass_path.unlink(missing_ok=True)


@app.get("/")
def home():
    return {"status": "running", "service": "ClipForge AI", "version": "1.0.0"}


@app.get("/health")
def health():
    return {"status": "healthy", "ffmpeg": Path(FFMPEG).exists()}


@app.post("/process")
async def process_video(file: UploadFile = File(...)):
    job_id = str(uuid.uuid4())
    extension = Path(file.filename or "").suffix.lower()
    if extension not in ALLOWED_EXTENSIONS:
        raise HTTPException(400, "Unsupported video format")

    input_file = UPLOAD_DIR / f"{job_id}{extension}"
    total = 0
    try:
        with input_file.open("wb") as buffer:
            while chunk := await file.read(1024 * 1024):
                total += len(chunk)
                if total > MAX_UPLOAD_BYTES:
                    raise HTTPException(413, "Video is larger than 2 GB")
                buffer.write(chunk)

        duration, audio = probe_video(input_file)
        transcription = transcribe(input_file) if audio else {"text": "", "segments": []}
        highlights = detect_highlights(transcription, duration)
        clips = []
        for i, h in enumerate(highlights, 1):
            output = OUTPUT_DIR / f"{job_id}_clip_{i}.mp4"
            create_short(input_file, output, h["start"], h["duration"], h["text"])
            clips.append({
                "clip_number": i, "title": f"AI Short #{i}", "score": h["score"],
                "text": h["text"], "start": round(h["start"], 2),
                "duration": round(h["duration"], 2),
                "download_url": f"/download/{output.name}"
            })
        return {"status": "completed", "job_id": job_id, "has_audio": audio, "transcript": transcription.get("text", ""), "number_of_clips": len(clips), "clips": clips}
    except HTTPException:
        raise
    except Exception as exc:
        print(f"Processing error: {exc}")
        if input_file.exists(): input_file.unlink(missing_ok=True)
        raise HTTPException(500, f"Video processing failed: {exc}")


@app.get("/download/{filename}")
def download_clip(filename: str):
    candidate = (OUTPUT_DIR / filename).resolve()
    if OUTPUT_DIR.resolve() not in candidate.parents:
        raise HTTPException(403, "Invalid file path")
    if not candidate.is_file():
        raise HTTPException(404, "Clip not found")
    return FileResponse(candidate, media_type="video/mp4", filename=candidate.name)
