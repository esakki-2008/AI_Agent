from __future__ import annotations

import json
import os
import re
import shutil
import subprocess
import tempfile
import threading
import uuid
import zipfile
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
for folder in (UPLOAD_DIR, OUTPUT_DIR):
    folder.mkdir(parents=True, exist_ok=True)

FFMPEG = imageio_ffmpeg.get_ffmpeg_exe()
FFMPEG_DIR = str(Path(FFMPEG).parent)
os.environ["PATH"] = FFMPEG_DIR + os.pathsep + os.environ.get("PATH", "")

ALLOWED_EXTENSIONS = {".mp4", ".mov", ".mkv", ".avi", ".webm", ".m4v"}
MAX_UPLOAD_BYTES = 2 * 1024 * 1024 * 1024
MAX_CLIPS = 10
MIN_CLIP_SECONDS = 15
MAX_CLIP_SECONDS = 60

app = FastAPI(title="ClipForge AI", version="4.0.0", description="Local AI YouTube-to-Shorts generator with smart highlight ranking, captions, thumbnails and exports.")
origins = [x.strip() for x in os.getenv("CORS_ORIGINS", "http://localhost:5173,http://127.0.0.1:5173").split(",") if x.strip()]
app.add_middleware(CORSMiddleware, allow_origins=origins, allow_credentials=True, allow_methods=["*"], allow_headers=["*"])

JOBS: dict[str, dict[str, Any]] = {}
JOBS_LOCK = threading.Lock()

class ProcessOptions(BaseModel):
    num_clips: int = Field(default=5, ge=1, le=MAX_CLIPS)
    clip_duration: int = Field(default=30, ge=MIN_CLIP_SECONDS, le=MAX_CLIP_SECONDS)
    captions: bool = True
    model: str = Field(default="base", pattern=r"^(tiny|base|small|medium)$")
    smart_crop: bool = True
    generate_metadata: bool = True
    language: str = Field(default="auto", pattern=r"^(auto|en|hi|ta|te|ml|kn)$")

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


def module_available(name: str) -> bool:
    try:
        __import__(name)
        return True
    except Exception:
        return False


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


def transcribe(path: Path, model_name: str, language: str) -> dict[str, Any]:
    try:
        import whisper
        model = whisper.load_model(model_name)
        kwargs: dict[str, Any] = {"fp16": False, "verbose": False, "temperature": 0, "condition_on_previous_text": True}
        if language != "auto":
            kwargs["language"] = language
        result = model.transcribe(str(path), **kwargs)
        return {"text": result.get("text", "").strip(), "segments": result.get("segments", []), "language": result.get("language", "unknown")}
    except Exception as exc:
        print(f"Whisper unavailable/failed: {exc}")
        return {"text": "", "segments": [], "language": "unknown", "error": str(exc)}

HOOK_WORDS = {"amazing", "important", "secret", "mistake", "problem", "solution", "best", "worst", "never", "always", "how", "why", "truth", "tip", "tips", "learn", "learned", "money", "success", "failure", "hack", "easy", "hard", "avoid", "key", "reason", "idea", "powerful", "actually", "real", "wrong", "simple", "nobody", "everyone", "first", "only", "instead", "remember", "warning", "free", "shocking", "crazy", "story", "lesson"}
FILLER_WORDS = {"um", "uh", "erm", "hmm", "like", "you know", "basically"}


def score_text(text: str) -> float:
    lower = text.lower()
    words = re.findall(r"[a-zA-Z0-9']+", lower)
    if not words:
        return 0.0
    unique = set(words)
    score = 40.0
    score += min(28, sum(4 for w in HOOK_WORDS if w in unique))
    score += 9 if "?" in text else 0
    score += 6 if "!" in text else 0
    score += 6 if len(words) >= 18 else 0
    score += 5 if len(words) >= 35 else 0
    score += 5 if any(w.isdigit() for w in words) else 0
    score += 4 if any(w in {"you", "your", "we", "our", "they", "this"} for w in unique) else 0
    score += 4 if any(w in {"but", "because", "therefore", "so", "however"} for w in unique) else 0
    score -= min(12, sum(lower.count(w) for w in FILLER_WORDS) * 2)
    return round(max(1, min(100, score)), 1)


def build_candidates(transcription: dict[str, Any], duration: float, target: int, clip_duration: int) -> list[dict[str, Any]]:
    segments = [s for s in transcription.get("segments", []) if str(s.get("text", "")).strip()]
    if not segments:
        return []
    window = min(float(clip_duration), duration)
    candidates = []
    for i, seg in enumerate(segments):
        anchor = float(seg.get("start", 0))
        start = max(0.0, anchor - min(6.0, window * 0.2))
        if duration > window:
            start = min(start, duration - window)
        end = min(duration, start + window)
        nearby = [s for s in segments if float(s.get("end", 0)) >= start and float(s.get("start", 0)) <= end]
        text = " ".join(str(s.get("text", "")).strip() for s in nearby).strip() or str(seg.get("text", "")).strip()
        candidates.append({"start": start, "end": end, "text": text, "score": score_text(text), "anchor": i})
    candidates.sort(key=lambda x: (x["score"], len(x["text"])), reverse=True)
    selected = []
    for candidate in candidates:
        if any(candidate["start"] < old["end"] and candidate["end"] > old["start"] for old in selected):
            continue
        selected.append(candidate)
        if len(selected) >= target:
            break
    selected.sort(key=lambda x: x["start"])
    return selected


def fallback_candidates(duration: float, target: int, clip_duration: int) -> list[dict[str, Any]]:
    if duration <= 0:
        return []
    length = min(float(clip_duration), duration)
    count = min(target, max(1, int((duration + length - 1) // length)))
    usable = max(0.0, duration - length)
    starts = [0.0] if count == 1 else [usable * i / (count - 1) for i in range(count)]
    return [{"start": round(s, 2), "end": round(min(duration, s + length), 2), "text": "", "score": 50.0, "anchor": i} for i, s in enumerate(starts)]


def make_srt(transcription: dict[str, Any], start: float, end: float, path: Path) -> None:
    def timestamp(seconds: float) -> str:
        total_ms = max(0, int(round(seconds * 1000)))
        h, rem = divmod(total_ms, 3600000); m, rem = divmod(rem, 60000); s, ms = divmod(rem, 1000)
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


def make_title(text: str, number: int) -> str:
    words = re.sub(r"\s+", " ", text).strip().split()
    if not words: return f"AI Short #{number}"
    title = " ".join(words[:10]).strip(".,!?;:")
    return (title + "…")[:72] if len(words) > 10 else title[:72]


def make_metadata(text: str, number: int) -> dict[str, Any]:
    words = re.findall(r"[a-zA-Z0-9']+", text.lower())
    stop = {"the", "and", "that", "this", "with", "from", "your", "have", "what", "when", "then", "they", "will", "about", "just", "into", "are", "you", "for"}
    freq: dict[str, int] = {}
    for word in words:
        if len(word) > 3 and word not in stop: freq[word] = freq.get(word, 0) + 1
    topics = [w for w, _ in sorted(freq.items(), key=lambda x: x[1], reverse=True)[:5]]
    hashtags = ["#Shorts", "#ClipForgeAI"] + [f"#{re.sub(r'[^a-zA-Z0-9]', '', x).title()}" for x in topics]
    return {"title": make_title(text, number), "description": text[:500], "hashtags": list(dict.fromkeys(hashtags))}


def create_thumbnail(input_file: Path, output_file: Path, start: float, smart_crop: bool) -> None:
    vf = "scale=1080:1920:force_original_aspect_ratio=increase,crop=1080:1920" if smart_crop else "scale=1080:1920:force_original_aspect_ratio=decrease,pad=1080:1920:(ow-iw)/2:(oh-ih)/2"
    run_ffmpeg(["-y", "-ss", f"{start:.3f}", "-i", str(input_file), "-frames:v", "1", "-vf", vf, str(output_file)])


def create_short(input_file: Path, output_file: Path, start: float, duration: float, transcription: dict[str, Any], captions: bool, smart_crop: bool) -> None:
    srt_path = None
    try:
        vf = "scale=1080:1920:force_original_aspect_ratio=increase,crop=1080:1920" if smart_crop else "scale=1080:1920:force_original_aspect_ratio=decrease,pad=1080:1920:(ow-iw)/2:(oh-ih)/2"
        filters = [vf]
        if captions and transcription.get("segments"):
            with tempfile.NamedTemporaryFile(suffix=".srt", delete=False) as tmp: srt_path = Path(tmp.name)
            make_srt(transcription, start, start + duration, srt_path)
            subtitle_path = str(srt_path).replace("\\", "/").replace(":", "\\:")
            filters.append("subtitles=" + subtitle_path + ":force_style='FontName=Arial,FontSize=22,PrimaryColour=&H00FFFFFF,OutlineColour=&H00000000,BorderStyle=1,Outline=3,Shadow=1,Alignment=2,MarginV=180,Bold=1'")
        run_ffmpeg(["-y", "-ss", f"{start:.3f}", "-i", str(input_file), "-t", f"{duration:.3f}", "-vf", ",".join(filters), "-c:v", "libx264", "-preset", os.getenv("FFMPEG_PRESET", "veryfast"), "-crf", os.getenv("FFMPEG_CRF", "23"), "-pix_fmt", "yuv420p", "-c:a", "aac", "-b:a", "128k", "-movflags", "+faststart", str(output_file)])
    finally:
        if srt_path: srt_path.unlink(missing_ok=True)


def validate_youtube_url(url: str) -> bool:
    return bool(re.match(r"^https?://(www\.)?(youtube\.com|youtu\.be)(/|$)", url.strip(), re.IGNORECASE))


def youtube_runtime_args() -> list[str]:
    try:
        return ["deno"] if subprocess.run(["deno", "--version"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL).returncode == 0 else []
    except FileNotFoundError:
        return []


def download_youtube(url: str, destination: Path, job_id: str) -> None:
    try:
        import yt_dlp
    except ImportError as exc:
        raise RuntimeError("yt-dlp is missing. Run: python -m pip install yt-dlp") from exc
    template = str(destination.with_suffix("")) + ".%(ext)s"
    runtime = youtube_runtime_args()
    selectors = [
        "bestvideo[height<=1080][ext=mp4]+bestaudio[ext=m4a]/bestvideo[height<=720][ext=mp4]+bestaudio[ext=m4a]",
        "bestvideo[height<=720]+bestaudio/best[height<=720]",
        "best[height<=1080]/best",
    ]
    last_error = "No compatible YouTube format was found."
    for selector in selectors:
        try:
            opts: dict[str, Any] = {"format": selector, "outtmpl": template, "merge_output_format": "mp4", "noplaylist": True, "ffmpeg_location": FFMPEG, "restrictfilenames": True, "quiet": False, "overwrites": True}
            if runtime: opts["js_runtimes"] = {runtime[0]: {}}
            with yt_dlp.YoutubeDL(opts) as ydl:
                info = ydl.extract_info(url, download=True)
                prepared = Path(ydl.prepare_filename(info))
            candidates = [destination, prepared, prepared.with_suffix(".mp4"), prepared.with_suffix(".mkv"), prepared.with_suffix(".webm"), prepared.with_suffix(".m4v")]
            candidates += list(destination.parent.glob(destination.stem + ".*"))
            candidates = [p for p in candidates if p.is_file() and p.suffix.lower() in ALLOWED_EXTENSIONS]
            if not candidates: raise RuntimeError("YouTube download completed but no video file was produced.")
            best = max(candidates, key=lambda p: p.stat().st_size)
            if best.resolve() != destination.resolve():
                if destination.exists(): destination.unlink()
                shutil.move(str(best), str(destination))
            return
        except Exception as exc:
            last_error = str(exc); update_job(job_id, message="Trying a compatible YouTube format…")
    raise RuntimeError(last_error + (" Install Deno for more reliable current YouTube extraction." if not runtime else ""))


def process_file(input_file: Path, job_id: str, options: ProcessOptions) -> dict[str, Any]:
    update_job(job_id, progress=35, message="Inspecting video…")
    duration, has_audio, width, height = probe_video(input_file)
    update_job(job_id, progress=48, message=f"Transcribing with local Whisper ({options.model})…")
    transcription = transcribe(input_file, options.model, options.language) if has_audio else {"text": "", "segments": [], "language": "unknown"}
    update_job(job_id, progress=62, message="Ranking hooks, context and retention signals…")
    highlights = build_candidates(transcription, duration, options.num_clips, options.clip_duration) or fallback_candidates(duration, options.num_clips, options.clip_duration)
    update_job(job_id, progress=70, message="Rendering 1080x1920 vertical Shorts…")
    clips = []
    for index, highlight in enumerate(highlights, 1):
        start = float(highlight["start"]); end = min(duration, start + options.clip_duration); actual_duration = max(1.0, end - start)
        output = OUTPUT_DIR / f"{job_id}_clip_{index}.mp4"
        create_short(input_file, output, start, actual_duration, transcription, options.captions, options.smart_crop)
        thumb = OUTPUT_DIR / f"{job_id}_clip_{index}.jpg"
        try: create_thumbnail(input_file, thumb, start, options.smart_crop)
        except Exception: thumb = None
        metadata = make_metadata(highlight["text"], index) if options.generate_metadata else {}
        clips.append({"clip_number": index, "title": metadata.get("title", f"AI Short #{index}"), "score": highlight["score"], "text": highlight["text"], "start": round(start, 2), "end": round(end, 2), "duration": round(actual_duration, 2), "download_url": f"/download/{output.name}", "thumbnail_url": f"/download/{thumb.name}" if thumb else None, "metadata": metadata})
        update_job(job_id, progress=70 + int(index / max(1, len(highlights)) * 28), message=f"Rendered Short {index} of {len(highlights)}…")
    manifest = {"source_duration": round(duration, 2), "source_resolution": f"{width}x{height}", "language": transcription.get("language", "unknown"), "transcript": transcription.get("text", ""), "clips": clips}
    (OUTPUT_DIR / f"{job_id}_manifest.json").write_text(json.dumps(manifest, indent=2, ensure_ascii=False), encoding="utf-8")
    result: dict[str, Any] = {"status": "completed", "job_id": job_id, "source_duration": round(duration, 2), "source_resolution": f"{width}x{height}", "has_audio": has_audio, "language": transcription.get("language", "unknown"), "transcript": transcription.get("text", ""), "number_of_clips": len(clips), "clips": clips, "settings": options.model_dump(), "download_all_url": f"/download-all/{job_id}"}
    if transcription.get("error"): result["warning"] = "Whisper could not transcribe this video, so fallback highlight selection was used."
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
def home() -> dict[str, str]: return {"status": "running", "service": "ClipForge AI", "version": "4.0.0"}

@app.get("/health")
def health() -> dict[str, Any]:
    return {"status": "healthy", "ffmpeg": Path(FFMPEG).exists(), "ffmpeg_path": FFMPEG, "whisper": module_available("whisper"), "yt_dlp": module_available("yt_dlp"), "deno": bool(youtube_runtime_args()), "max_clips": MAX_CLIPS, "max_upload_gb": MAX_UPLOAD_BYTES / (1024 ** 3)}

@app.get("/jobs")
def list_jobs() -> dict[str, Any]:
    with JOBS_LOCK: items = [{"job_id": k, **v} for k, v in JOBS.items()]
    return {"jobs": items[-20:]}

@app.post("/process")
async def process_upload(background_tasks: BackgroundTasks, file: UploadFile = File(...), num_clips: int = 5, clip_duration: int = 30, captions: bool = True, model: str = "base", smart_crop: bool = True, generate_metadata: bool = True, language: str = "auto") -> dict[str, Any]:
    options = ProcessOptions(num_clips=num_clips, clip_duration=clip_duration, captions=captions, model=model, smart_crop=smart_crop, generate_metadata=generate_metadata, language=language)
    extension = Path(file.filename or "").suffix.lower()
    if extension not in ALLOWED_EXTENSIONS: raise HTTPException(400, "Unsupported video format. Use MP4, MOV, MKV, AVI, WebM or M4V.")
    job_id = str(uuid.uuid4()); input_file = UPLOAD_DIR / f"{job_id}{extension}"; total = 0
    try:
        with input_file.open("wb") as buffer:
            while chunk := await file.read(1024 * 1024):
                total += len(chunk)
                if total > MAX_UPLOAD_BYTES:
                    input_file.unlink(missing_ok=True); raise HTTPException(413, "Video is larger than 2 GB")
                buffer.write(chunk)
    finally: await file.close()
    with JOBS_LOCK: JOBS[job_id] = {"status": "queued", "progress": 5, "message": "Queued for processing…"}
    background_tasks.add_task(run_job, job_id, input_file, options)
    return {"status": "queued", "job_id": job_id, "status_url": f"/jobs/{job_id}"}

@app.post("/process-url")
def process_youtube(request: YouTubeRequest, background_tasks: BackgroundTasks) -> dict[str, Any]:
    url = str(request.url)
    if not validate_youtube_url(url): raise HTTPException(400, "Only YouTube URLs are supported.")
    job_id = str(uuid.uuid4()); input_file = UPLOAD_DIR / f"{job_id}.mp4"
    with JOBS_LOCK: JOBS[job_id] = {"status": "queued", "progress": 5, "message": "Queued for YouTube download…"}
    def download_and_process() -> None:
        try:
            update_job(job_id, status="processing", progress=8, message="Downloading YouTube video…")
            download_youtube(url, input_file, job_id)
            update_job(job_id, progress=30, message="Download complete. Starting AI analysis…")
            run_job(job_id, input_file, request.options)
        except Exception as exc:
            print(f"YouTube job {job_id} failed: {exc}")
            update_job(job_id, status="failed", progress=0, message="YouTube processing failed", error=str(exc)); input_file.unlink(missing_ok=True)
    background_tasks.add_task(download_and_process)
    return {"status": "queued", "job_id": job_id, "status_url": f"/jobs/{job_id}"}

@app.get("/jobs/{job_id}")
def get_job(job_id: str) -> dict[str, Any]:
    with JOBS_LOCK: job = JOBS.get(job_id)
    if not job: raise HTTPException(404, "Job not found")
    return {"job_id": job_id, **job}

@app.get("/transcript/{job_id}")
def transcript(job_id: str) -> FileResponse:
    path = OUTPUT_DIR / f"{job_id}_manifest.json"
    if not path.is_file(): raise HTTPException(404, "Transcript not found")
    data = json.loads(path.read_text(encoding="utf-8")); text = data.get("transcript", "")
    txt = OUTPUT_DIR / f"{job_id}_transcript.txt"; txt.write_text(text, encoding="utf-8")
    return FileResponse(txt, media_type="text/plain", filename=txt.name)

@app.get("/download/{filename}")
def download_clip(filename: str) -> FileResponse:
    candidate = (OUTPUT_DIR / Path(filename).name).resolve()
    if OUTPUT_DIR.resolve() not in candidate.parents: raise HTTPException(403, "Invalid file path")
    if not candidate.is_file(): raise HTTPException(404, "File not found")
    suffix = candidate.suffix.lower(); media = "image/jpeg" if suffix == ".jpg" else "application/json" if suffix == ".json" else "video/mp4"
    return FileResponse(candidate, media_type=media, filename=candidate.name)

@app.get("/download-all/{job_id}")
def download_all(job_id: str) -> FileResponse:
    if not re.fullmatch(r"[0-9a-f-]{36}", job_id, re.I): raise HTTPException(400, "Invalid job id")
    files = list(OUTPUT_DIR.glob(f"{job_id}_clip_*.mp4"))
    if not files: raise HTTPException(404, "No generated clips found")
    archive = OUTPUT_DIR / f"{job_id}_ClipForge_Shorts.zip"
    with zipfile.ZipFile(archive, "w", zipfile.ZIP_DEFLATED) as zf:
        for file in sorted(files): zf.write(file, file.name)
        manifest = OUTPUT_DIR / f"{job_id}_manifest.json"
        if manifest.exists(): zf.write(manifest, manifest.name)
    return FileResponse(archive, media_type="application/zip", filename=archive.name)
