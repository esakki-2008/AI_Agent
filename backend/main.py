from __future__ import annotations

import os
import re
import shutil
import subprocess
import tempfile
import threading
import uuid
from pathlib import Path
from typing import Any

import imageio_ffmpeg
from fastapi import BackgroundTasks, FastAPI, File, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from pydantic import BaseModel, Field, HttpUrl

BASE_DIR = Path(__file__).resolve().parent.parent
UPLOAD_DIR = BASE_DIR / "uploads"
OUTPUT_DIR = BASE_DIR / "outputs"
UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

FFMPEG = imageio_ffmpeg.get_ffmpeg_exe()
FFMPEG_DIR = str(Path(FFMPEG).parent)
if FFMPEG_DIR not in os.environ.get("PATH", "").split(os.pathsep):
    os.environ["PATH"] = FFMPEG_DIR + os.pathsep + os.environ.get("PATH", "")

ALLOWED_EXTENSIONS = {".mp4", ".mov", ".mkv", ".avi", ".webm", ".m4v"}
MAX_UPLOAD_BYTES = 2 * 1024 * 1024 * 1024
MAX_CLIPS = 5
MIN_CLIP_SECONDS = 15
MAX_CLIP_SECONDS = 60

app = FastAPI(title="ClipForge AI", version="2.0.0", description="Local AI YouTube-to-Shorts generator. No API key required.")
origins = [x.strip() for x in os.getenv("CORS_ORIGINS", "http://localhost:5173,http://127.0.0.1:5173").split(",") if x.strip()]
app.add_middleware(CORSMiddleware, allow_origins=origins, allow_credentials=True, allow_methods=["*"], allow_headers=["*"])

JOBS: dict[str, dict[str, Any]] = {}
JOBS_LOCK = threading.Lock()

class ProcessOptions(BaseModel):
    num_clips: int = Field(default=3, ge=1, le=MAX_CLIPS)
    clip_duration: int = Field(default=30, ge=MIN_CLIP_SECONDS, le=MAX_CLIP_SECONDS)
    captions: bool = True

class YouTubeRequest(BaseModel):
    url: HttpUrl
    options: ProcessOptions = Field(default_factory=ProcessOptions)

def update_job(job_id: str, **values: Any) -> None:
    with JOBS_LOCK:
        if job_id in JOBS:
            JOBS[job_id].update(values)

def run_command(command: list[str], timeout: int | None = None) -> subprocess.CompletedProcess[str]:
    result = subprocess.run(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, timeout=timeout)
    if result.returncode != 0:
        raise RuntimeError(result.stderr[-8000:] or "Command failed")
    return result

def run_ffmpeg(args: list[str]) -> subprocess.CompletedProcess[str]:
    return run_command([FFMPEG, *args])

def probe_video(path: Path) -> tuple[float, bool, int, int]:
    result = subprocess.run([FFMPEG, "-hide_banner", "-i", str(path)], stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
    match = re.search(r"Duration:\s*(\d+):(\d+):([\d.]+)", result.stderr)
    if not match:
        raise RuntimeError("Could not read video duration")
    duration = int(match.group(1)) * 3600 + int(match.group(2)) * 60 + float(match.group(3))
    video = re.search(r"Stream #.*?: Video:.*?(\d{2,5})x(\d{2,5})", result.stderr)
    width, height = (int(video.group(1)), int(video.group(2))) if video else (1920, 1080)
    has_audio = bool(re.search(r"Stream #.*?: Audio:", result.stderr))
    return duration, has_audio, width, height

def transcribe(path: Path) -> dict[str, Any]:
    try:
        import whisper
        model = whisper.load_model(os.getenv("WHISPER_MODEL", "base"))
        result = model.transcribe(str(path), fp16=False, verbose=False, temperature=0, condition_on_previous_text=True)
        return {"text": result.get("text", "").strip(), "segments": result.get("segments", [])}
    except Exception as exc:
        print(f"Whisper unavailable/failed: {exc}")
        return {"text": "", "segments": [], "error": str(exc)}

HOOK_WORDS = {"amazing", "important", "secret", "mistake", "problem", "solution", "best", "worst", "never", "always", "how", "why", "truth", "tip", "tips", "learn", "learned", "money", "success", "failure", "hack", "easy", "hard", "avoid", "key", "reason", "idea", "powerful", "actually", "real", "wrong", "simple", "nobody", "everyone", "first", "only", "instead", "remember", "warning", "free"}
FILLER_WORDS = {"um", "uh", "erm", "hmm", "like", "you know"}

def score_text(text: str) -> float:
    lower = text.lower()
    words = re.findall(r"[a-zA-Z0-9']+", lower)
    if not words:
        return 0.0
    unique = set(words)
    score = 45.0
    score += min(25, sum(4 for w in HOOK_WORDS if w in unique))
    score += 8 if "?" in text else 0
    score += 5 if "!" in text else 0
    score += 5 if len(words) >= 18 else 0
    score += 4 if len(words) >= 35 else 0
    score += 4 if any(w.isdigit() for w in words) else 0
    score += 4 if any(w in {"you", "your", "we", "our"} for w in unique) else 0
    score += 3 if any(w in {"but", "because", "therefore", "so"} for w in unique) else 0
    score -= min(12, sum(lower.count(w) for w in FILLER_WORDS) * 2)
    return round(max(0, min(100, score)), 1)

def build_candidates(transcription: dict[str, Any], duration: float, target: int, clip_duration: int) -> list[dict[str, Any]]:
    segments = [s for s in transcription.get("segments", []) if str(s.get("text", "")).strip()]
    if not segments:
        return []
    candidates = []
    for i, seg in enumerate(segments):
        anchor_start = float(seg.get("start", 0))
        anchor_end = float(seg.get("end", anchor_start + 1))
        start = max(0.0, anchor_start - 6)
        if duration >= clip_duration:
            start = min(start, duration - clip_duration)
            end = start + clip_duration
        else:
            end = duration
            start = 0.0
        nearby = [s for s in segments if float(s.get("end", 0)) >= start and float(s.get("start", 0)) <= end]
        text = " ".join(str(s.get("text", "")).strip() for s in nearby).strip() or str(seg.get("text", "")).strip()
        candidates.append({"start": start, "end": end, "text": text, "score": score_text(text), "anchor": i})
    candidates.sort(key=lambda x: (x["score"], len(x["text"])), reverse=True)
    selected = []
    for c in candidates:
        if any(c["start"] < x["end"] and c["end"] > x["start"] for x in selected):
            continue
        selected.append(c)
        if len(selected) >= target:
            break
    selected.sort(key=lambda x: x["start"])
    return selected

def fallback_candidates(duration: float, target: int, clip_duration: int) -> list[dict[str, Any]]:
    if duration <= 0:
        return []
    length = min(duration, clip_duration)
    count = min(target, max(1, int((duration + length - 1) // length)))
    usable = max(0.0, duration - length)
    starts = [0.0] if count == 1 else [usable * i / (count - 1) for i in range(count)]
    return [{"start": round(s, 2), "end": round(min(duration, s + length), 2), "text": "", "score": 50.0, "anchor": i} for i, s in enumerate(starts)]

def make_srt(transcription: dict[str, Any], start: float, end: float, path: Path) -> None:
    def timestamp(seconds: float) -> str:
        total_ms = max(0, int(round(seconds * 1000)))
        h, rem = divmod(total_ms, 3600000)
        m, rem = divmod(rem, 60000)
        s, ms = divmod(rem, 1000)
        return f"{h:02d}:{m:02d}:{s:02d},{ms:03d}"
    rows, number = [], 1
    for segment in transcription.get("segments", []):
        s, e = float(segment.get("start", 0)), float(segment.get("end", 0))
        if e <= start or s >= end:
            continue
        text = str(segment.get("text", "")).strip()
        if not text:
            continue
        ls, le = max(0, s - start), min(end - start, e - start)
        rows.append(f"{number}\n{timestamp(ls)} --> {timestamp(max(ls + 0.2, le))}\n{text}\n")
        number += 1
    path.write_text("\n".join(rows), encoding="utf-8")

def create_short(input_file: Path, output_file: Path, start: float, duration: float, transcription: dict[str, Any], captions: bool) -> None:
    srt_path = None
    try:
        filters = ["scale=1080:1920:force_original_aspect_ratio=increase", "crop=1080:1920"]
        if captions and transcription.get("segments"):
            with tempfile.NamedTemporaryFile(suffix=".srt", delete=False) as tmp:
                srt_path = Path(tmp.name)
            make_srt(transcription, start, start + duration, srt_path)
            subtitle_path = str(srt_path).replace("\\", "/").replace(":", "\\:")
            filters.append("subtitles=" + subtitle_path + ":force_style='FontName=Arial,FontSize=22,PrimaryColour=&H00FFFFFF,OutlineColour=&H00000000,BorderStyle=1,Outline=3,Shadow=1,Alignment=2,MarginV=180,Bold=1'")
        run_ffmpeg(["-y", "-ss", f"{start:.3f}", "-i", str(input_file), "-t", f"{duration:.3f}", "-vf", ",".join(filters), "-c:v", "libx264", "-preset", os.getenv("FFMPEG_PRESET", "veryfast"), "-crf", os.getenv("FFMPEG_CRF", "23"), "-pix_fmt", "yuv420p", "-c:a", "aac", "-b:a", "128k", "-movflags", "+faststart", str(output_file)])
    finally:
        if srt_path:
            srt_path.unlink(missing_ok=True)

def validate_youtube_url(url: str) -> bool:
    return bool(re.match(r"^https?://(www\.)?(youtube\.com|youtu\.be)(/|$)", url.strip(), re.IGNORECASE))

def youtube_runtime_args() -> list[str]:
    try:
        result = subprocess.run(["deno", "--version"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        return ["deno"] if result.returncode == 0 else []
    except FileNotFoundError:
        return []

def download_youtube(url: str, destination: Path, job_id: str) -> None:
    try:
        import yt_dlp
    except ImportError as exc:
        raise RuntimeError("yt-dlp is missing. Run: python -m pip install -r requirements.txt") from exc
    template = str(destination.with_suffix("")) + ".%(ext)s"
    runtime = youtube_runtime_args()
    selectors = [
        "bestvideo[height<=1080][ext=mp4]+bestaudio[ext=m4a]/bestvideo[height<=720][ext=mp4]+bestaudio[ext=m4a]",
        "bestvideo[height<=1080]+bestaudio/best[height<=1080]",
        "best[height<=1080]/best",
    ]
    last_error = "No compatible YouTube format was found."
    for selector in selectors:
        try:
            opts: dict[str, Any] = {"format": selector, "outtmpl": template, "merge_output_format": "mp4", "noplaylist": True, "ffmpeg_location": FFMPEG, "restrictfilenames": True, "quiet": False, "no_warnings": False}
            if runtime:
                opts["js_runtimes"] = {runtime[0]: {}}
            with yt_dlp.YoutubeDL(opts) as ydl:
                info = ydl.extract_info(url, download=True)
                prepared = Path(ydl.prepare_filename(info))
            candidates = [destination, prepared, prepared.with_suffix(".mp4"), prepared.with_suffix(".mkv"), prepared.with_suffix(".webm"), prepared.with_suffix(".m4v")]
            candidates += list(destination.parent.glob(destination.stem + ".*"))
            candidates = [p for p in candidates if p.is_file() and p.suffix.lower() in ALLOWED_EXTENSIONS]
            if not candidates:
                raise RuntimeError("YouTube download completed but no video file was produced.")
            best = max(candidates, key=lambda p: p.stat().st_size)
            if best.resolve() != destination.resolve():
                if destination.exists(): destination.unlink()
                shutil.move(str(best), str(destination))
            return
        except Exception as exc:
            last_error = str(exc)
            update_job(job_id, message="Trying another YouTube format…")
    note = " Install Deno for more reliable current YouTube extraction." if not runtime else ""
    raise RuntimeError(last_error + note)

def process_file(input_file: Path, job_id: str, options: ProcessOptions) -> dict[str, Any]:
    update_job(job_id, progress=35, message="Inspecting video…")
    duration, has_audio, width, height = probe_video(input_file)
    update_job(job_id, progress=48, message="Transcribing with local Whisper…")
    transcription = transcribe(input_file) if has_audio else {"text": "", "segments": []}
    update_job(job_id, progress=62, message="Finding the strongest moments…")
    highlights = build_candidates(transcription, duration, options.num_clips, options.clip_duration) or fallback_candidates(duration, options.num_clips, options.clip_duration)
    update_job(job_id, progress=70, message="Rendering vertical Shorts…")
    clips = []
    for index, highlight in enumerate(highlights, 1):
        start = float(highlight["start"])
        end = min(duration, start + options.clip_duration)
        actual_duration = max(1.0, end - start)
        output = OUTPUT_DIR / f"{job_id}_clip_{index}.mp4"
        create_short(input_file, output, start, actual_duration, transcription, options.captions)
        clips.append({"clip_number": index, "title": f"AI Short #{index}", "score": highlight["score"], "text": highlight["text"], "start": round(start, 2), "duration": round(actual_duration, 2), "download_url": f"/download/{output.name}"})
        update_job(job_id, progress=70 + int(index / max(1, len(highlights)) * 28), message=f"Rendered Short {index} of {len(highlights)}…")
    result: dict[str, Any] = {"status": "completed", "job_id": job_id, "source_duration": round(duration, 2), "source_resolution": f"{width}x{height}", "has_audio": has_audio, "transcript": transcription.get("text", ""), "number_of_clips": len(clips), "clips": clips, "settings": options.model_dump()}
    if transcription.get("error"):
        result["warning"] = "Whisper could not transcribe this video. The app used fallback clip selection. Details: " + transcription["error"]
    return result

def run_job(job_id: str, input_file: Path, options: ProcessOptions) -> None:
    try:
        update_job(job_id, status="processing", progress=32, message="Starting AI analysis…")
        result = process_file(input_file, job_id, options)
        update_job(job_id, status="completed", progress=100, message="Process complete", result=result)
    except Exception as exc:
        print(f"Job {job_id} failed: {exc}")
        update_job(job_id, status="failed", progress=0, message="Processing failed", error=str(exc))
    finally:
        input_file.unlink(missing_ok=True)

@app.get("/")
def home() -> dict[str, str]:
    return {"status": "running", "service": "ClipForge AI", "version": "2.0.0"}

@app.get("/health")
def health() -> dict[str, Any]:
    return {"status": "healthy", "ffmpeg": Path(FFMPEG).exists(), "ffmpeg_path": FFMPEG, "whisper": module_available("whisper"), "yt_dlp": module_available("yt_dlp"), "deno": bool(youtube_runtime_args())}

def module_available(name: str) -> bool:
    try:
        __import__(name)
        return True
    except Exception:
        return False

@app.post("/process")
async def process_upload(background_tasks: BackgroundTasks, file: UploadFile = File(...), num_clips: int = 3, clip_duration: int = 30, captions: bool = True) -> dict[str, Any]:
    options = ProcessOptions(num_clips=num_clips, clip_duration=clip_duration, captions=captions)
    extension = Path(file.filename or "").suffix.lower()
    if extension not in ALLOWED_EXTENSIONS:
        raise HTTPException(400, "Unsupported video format")
    job_id = str(uuid.uuid4())
    input_file = UPLOAD_DIR / f"{job_id}{extension}"
    total = 0
    try:
        with input_file.open("wb") as buffer:
            while chunk := await file.read(1024 * 1024):
                total += len(chunk)
                if total > MAX_UPLOAD_BYTES:
                    input_file.unlink(missing_ok=True)
                    raise HTTPException(413, "Video is larger than 2 GB")
                buffer.write(chunk)
    finally:
        await file.close()
    with JOBS_LOCK:
        JOBS[job_id] = {"status": "queued", "progress": 5, "message": "Queued for processing…"}
    background_tasks.add_task(run_job, job_id, input_file, options)
    return {"status": "queued", "job_id": job_id, "status_url": f"/jobs/{job_id}"}

@app.post("/process-url")
def process_youtube(request: YouTubeRequest, background_tasks: BackgroundTasks) -> dict[str, Any]:
    url = str(request.url)
    if not validate_youtube_url(url):
        raise HTTPException(400, "Only YouTube URLs are supported.")
    job_id = str(uuid.uuid4())
    input_file = UPLOAD_DIR / f"{job_id}.mp4"
    with JOBS_LOCK:
        JOBS[job_id] = {"status": "queued", "progress": 5, "message": "Queued for YouTube download…"}
    def download_and_process() -> None:
        try:
            update_job(job_id, status="processing", progress=8, message="Downloading YouTube video…")
            download_youtube(url, input_file, job_id)
            update_job(job_id, progress=30, message="Download complete. Starting AI analysis…")
            run_job(job_id, input_file, request.options)
        except Exception as exc:
            print(f"YouTube job {job_id} failed: {exc}")
            update_job(job_id, status="failed", progress=0, message="YouTube processing failed", error=str(exc))
            input_file.unlink(missing_ok=True)
    background_tasks.add_task(download_and_process)
    return {"status": "queued", "job_id": job_id, "status_url": f"/jobs/{job_id}"}

@app.get("/jobs/{job_id}")
def get_job(job_id: str) -> dict[str, Any]:
    with JOBS_LOCK:
        job = JOBS.get(job_id)
    if not job:
        raise HTTPException(404, "Job not found")
    return {"job_id": job_id, **job}

@app.get("/download/{filename}")
def download_clip(filename: str) -> FileResponse:
    candidate = (OUTPUT_DIR / Path(filename).name).resolve()
    if OUTPUT_DIR.resolve() not in candidate.parents:
        raise HTTPException(403, "Invalid file path")
    if not candidate.is_file():
        raise HTTPException(404, "Clip not found")
    return FileResponse(candidate, media_type="video/mp4", filename=candidate.name)
'''}