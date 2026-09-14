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

# imageio-ffmpeg ships a working FFmpeg binary whose filename is not
# "ffmpeg.exe".  Whisper's loader invokes "ffmpeg" by name, so expose a
# Whisper-compatible executable in a small local bin directory.
FFMPEG = imageio_ffmpeg.get_ffmpeg_exe()
FFMPEG_DIR = Path(FFMPEG).parent
LOCAL_BIN = BASE_DIR / ".bin"
LOCAL_BIN.mkdir(parents=True, exist_ok=True)
WHISPER_FFMPEG = LOCAL_BIN / "ffmpeg.exe"
if not WHISPER_FFMPEG.exists():
    try:
        WHISPER_FFMPEG.symlink_to(FFMPEG)
    except (OSError, NotImplementedError):
        try:
            shutil.copy2(FFMPEG, WHISPER_FFMPEG)
        except OSError:
            pass
if WHISPER_FFMPEG.exists():
    os.environ["PATH"] = str(LOCAL_BIN) + os.pathsep + os.environ.get("PATH", "")
os.environ["PATH"] = str(FFMPEG_DIR) + os.pathsep + os.environ.get("PATH", "")

ALLOWED_EXTENSIONS = {".mp4", ".mov", ".mkv", ".avi", ".webm", ".m4v"}
MAX_UPLOAD_BYTES = 2 * 1024 * 1024 * 1024
MAX_CLIPS = 10
MIN_CLIP_SECONDS = 15
MAX_CLIP_SECONDS = 60

app = FastAPI(title="ClipForge AI", version="5.0.1", description="Local AI video repurposing studio")
origins = [x.strip() for x in os.getenv("CORS_ORIGINS", "http://localhost:5173,http://127.0.0.1:5173").split(",") if x.strip()]
app.add_middleware(CORSMiddleware, allow_origins=origins, allow_credentials=True, allow_methods=["*"], allow_headers=["*"])
JOBS: dict[str, dict[str, Any]] = {}
JOBS_LOCK = threading.Lock()

class ProcessOptions(BaseModel):
    num_clips: int = Field(5, ge=1, le=MAX_CLIPS)
    clip_duration: int = Field(30, ge=MIN_CLIP_SECONDS, le=MAX_CLIP_SECONDS)
    captions: bool = True
    model: str = Field("base", pattern=r"^(tiny|base|small|medium)$")
    smart_crop: bool = True
    generate_metadata: bool = True
    language: str = Field("auto", pattern=r"^(auto|en|hi|ta|te|ml|kn)$")
    caption_style: str = Field("bold", pattern=r"^(classic|bold|minimal)$")
    crop_mode: str = Field("center", pattern=r"^(center|blur|fit)$")
    normalize_audio: bool = True
    quality: str = Field("high", pattern=r"^(standard|high|max)$")
    hook_overlay: bool = False
    remove_filler: bool = True

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
    return duration, bool(re.search(r"Stream #.*?: Audio:", result.stderr)), width, height

def transcribe(path: Path, model_name: str, language: str) -> dict[str, Any]:
    try:
        import whisper
        model = whisper.load_model(model_name)
        kwargs: dict[str, Any] = {"fp16": False, "verbose": False, "temperature": 0, "condition_on_previous_text": True}
        if language != "auto":
            kwargs["language"] = language
        result = model.transcribe(str(path), **kwargs)
        text = result.get("text", "").strip()
        if not text:
            raise RuntimeError("Whisper returned an empty transcript")
        return {"text": text, "segments": result.get("segments", []), "language": result.get("language", "unknown")}
    except Exception as exc:
        print(f"Whisper unavailable/failed: {exc}")
        return {"text": "", "segments": [], "language": "unknown", "error": str(exc)}

HOOK_WORDS = {"amazing","important","secret","mistake","problem","solution","best","worst","never","always","how","why","truth","tip","tips","learn","learned","money","success","failure","hack","easy","hard","avoid","key","reason","idea","powerful","actually","real","wrong","simple","nobody","everyone","first","only","instead","remember","warning","free","shocking","crazy","story","lesson","because","result","change"}
FILLER_WORDS = {"um","uh","erm","hmm","like","you know","basically","actually"}

def score_text(text: str) -> float:
    lower = text.lower(); words = re.findall(r"[a-zA-Z0-9']+", lower)
    if not words: return 0.0
    unique = set(words); score = 38.0
    score += min(30, sum(4 for w in HOOK_WORDS if w in unique))
    score += 10 if "?" in text else 0; score += 6 if "!" in text else 0
    score += 6 if len(words) >= 18 else 0; score += 5 if len(words) >= 35 else 0
    score += 5 if any(w.isdigit() for w in words) else 0
    score += 5 if any(w in {"you","your","we","our","they","this"} for w in unique) else 0
    score -= min(15, sum(lower.count(w) for w in FILLER_WORDS) * 2)
    return round(max(1, min(100, score)), 1)

def build_candidates(transcription: dict[str, Any], duration: float, target: int, clip_duration: int, remove_filler: bool) -> list[dict[str, Any]]:
    segments = [s for s in transcription.get("segments", []) if str(s.get("text", "")).strip()]
    if not segments: return []
    window = min(float(clip_duration), duration); candidates = []
    for i, seg in enumerate(segments):
        anchor = float(seg.get("start", 0)); start = max(0.0, anchor - min(6.0, window * .2))
        if duration > window: start = min(start, duration - window)
        end = min(duration, start + window)
        nearby = [s for s in segments if float(s.get("end", 0)) >= start and float(s.get("start", 0)) <= end]
        text = " ".join(str(s.get("text", "")).strip() for s in nearby).strip() or str(seg.get("text", "")).strip()
        score = score_text(text)
        if remove_filler and len(re.findall(r"\b(?:um|uh|erm|hmm)\b", text.lower())) >= 3: score -= 8
        candidates.append({"start": start, "end": end, "text": text, "score": round(max(1, score), 1), "anchor": i})
    candidates.sort(key=lambda x: (x["score"], len(x["text"])), reverse=True)
    selected = []
    for c in candidates:
        if any(c["start"] < old["end"] and c["end"] > old["start"] for old in selected): continue
        selected.append(c)
        if len(selected) >= target: break
    selected.sort(key=lambda x: x["start"]); return selected

def fallback_candidates(duration: float, target: int, clip_duration: int) -> list[dict[str, Any]]:
    if duration <= 0: return []
    length = min(float(clip_duration), duration); count = min(target, max(1, int((duration + length - 1) // length)))
    usable = max(0.0, duration - length); starts = [0.0] if count == 1 else [usable * i / (count - 1) for i in range(count)]
    return [{"start": round(s, 2), "end": round(min(duration, s + length), 2), "text": "", "score": 50.0, "anchor": i} for i, s in enumerate(starts)]

def make_srt(transcription: dict[str, Any], start: float, end: float, path: Path) -> None:
    def ts(seconds: float) -> str:
        total = max(0, int(round(seconds * 1000))); h, rem = divmod(total, 3600000); m, rem = divmod(rem, 60000); s, ms = divmod(rem, 1000)
        return f"{h:02d}:{m:02d}:{s:02d},{ms:03d}"
    rows = []; n = 1
    for seg in transcription.get("segments", []):
        s, e = float(seg.get("start", 0)), float(seg.get("end", 0))
        if e <= start or s >= end: continue
        text = str(seg.get("text", "")).strip()
        if not text: continue
        ls, le = max(0, s - start), min(end - start, e - start)
        rows.append(f"{n}\n{ts(ls)} --> {ts(max(ls + .2, le))}\n{text}\n"); n += 1
    path.write_text("\n".join(rows), encoding="utf-8")

def make_title(text: str, number: int) -> str:
    words = re.sub(r"\s+", " ", text).strip().split()
    if not words: return f"AI Short #{number}"
    title = " ".join(words[:10]).strip(".,!?;:"); return ((title + "…") if len(words) > 10 else title)[:72]

def make_metadata(text: str, number: int) -> dict[str, Any]:
    words = re.findall(r"[a-zA-Z0-9']+", text.lower()); stop = {"the","and","that","this","with","from","your","have","what","when","then","they","will","about","just","into","are","you","for"}
    freq: dict[str, int] = {}
    for w in words:
        if len(w) > 3 and w not in stop: freq[w] = freq.get(w, 0) + 1
    topics = [w for w, _ in sorted(freq.items(), key=lambda x: x[1], reverse=True)[:7]]
    tags = ["#Shorts", "#ClipForgeAI"] + ["#" + re.sub(r"[^a-zA-Z0-9]", "", x).title() for x in topics]
    return {"title": make_title(text, number), "description": text[:500], "hashtags": list(dict.fromkeys(tags)), "keywords": topics}

def video_filter(smart_crop: bool, crop_mode: str) -> str:
    if not smart_crop or crop_mode == "fit": return "scale=1080:1920:force_original_aspect_ratio=decrease,pad=1080:1920:(ow-iw)/2:(oh-ih)/2"
    if crop_mode == "blur": return "split=2[bg][fg];[bg]scale=1080:1920:force_original_aspect_ratio=increase,crop=1080:1920,boxblur=18:2[blur];[fg]scale=1080:1920:force_original_aspect_ratio=decrease[main];[blur][main]overlay=(W-w)/2:(H-h)/2"
    return "scale=1080:1920:force_original_aspect_ratio=increase,crop=1080:1920"

def caption_style(name: str) -> str:
    styles = {"classic": "FontName=Arial,FontSize=20,PrimaryColour=&H00FFFFFF,OutlineColour=&H00000000,BorderStyle=1,Outline=3,Shadow=1,Alignment=2,MarginV=180", "bold": "FontName=Arial,FontSize=24,PrimaryColour=&H00FFFFFF,OutlineColour=&H00000000,BorderStyle=1,Outline=4,Shadow=1,Alignment=2,MarginV=190,Bold=1", "minimal": "FontName=Arial,FontSize=18,PrimaryColour=&H00FFFFFF,OutlineColour=&H00000000,BorderStyle=1,Outline=2,Alignment=2,MarginV=160"}
    return styles[name]

def create_thumbnail(input_file: Path, output_file: Path, start: float, smart_crop: bool, crop_mode: str) -> None:
    run_ffmpeg(["-y", "-ss", f"{start:.3f}", "-i", str(input_file), "-frames:v", "1", "-vf", video_filter(smart_crop, crop_mode), str(output_file)])

def create_short(input_file: Path, output_file: Path, start: float, duration: float, transcription: dict[str, Any], options: ProcessOptions) -> None:
    srt_path = None
    try:
        filters = [video_filter(options.smart_crop, options.crop_mode)]
        if options.captions and transcription.get("segments"):
            with tempfile.NamedTemporaryFile(suffix=".srt", delete=False) as tmp: srt_path = Path(tmp.name)
            make_srt(transcription, start, start + duration, srt_path)
            sub = str(srt_path).replace("\\", "/").replace(":", "\\:")
            filters.append("subtitles=" + sub + ":force_style='" + caption_style(options.caption_style) + "'")
        crf = {"standard": "26", "high": "23", "max": "20"}[options.quality]
        args = ["-y", "-ss", f"{start:.3f}", "-i", str(input_file), "-t", f"{duration:.3f}", "-vf", ",".join(filters), "-c:v", "libx264", "-preset", os.getenv("FFMPEG_PRESET", "veryfast"), "-crf", crf, "-pix_fmt", "yuv420p", "-c:a", "aac", "-b:a", "160k"]
        if options.normalize_audio: args += ["-af", "loudnorm=I=-14:TP=-1.5:LRA=11"]
        args += ["-movflags", "+faststart", str(output_file)]; run_ffmpeg(args)
    finally:
        if srt_path: srt_path.unlink(missing_ok=True)

def validate_youtube_url(url: str) -> bool: return bool(re.match(r"^https?://(www\\.)?(youtube\\.com|youtu\\.be)(/|$)", url.strip(), re.I))

def youtube_runtime_args() -> list[str]:
    try: return ["deno"] if subprocess.run(["deno", "--version"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL).returncode == 0 else []
    except FileNotFoundError: return []

def download_youtube(url: str, destination: Path, job_id: str) -> None:
    try: import yt_dlp
    except ImportError as exc: raise RuntimeError("yt-dlp is missing. Run: python -m pip install yt-dlp") from exc
    template = str(destination.with_suffix("")) + ".%(ext)s"; runtime = youtube_runtime_args()
    selectors = ["bestvideo[height<=1080][ext=mp4]+bestaudio[ext=m4a]/bestvideo[height<=720][ext=mp4]+bestaudio[ext=m4a]", "bestvideo[height<=720]+bestaudio/best[height<=720]", "best[height<=1080]/best"]
    last_error = "No compatible YouTube format was found."
    for selector in selectors:
        try:
            opts = {"format": selector, "outtmpl": template, "merge_output_format": "mp4", "noplaylist": True, "ffmpeg_location": FFMPEG, "restrictfilenames": True, "quiet": False, "overwrites": True}
            if runtime: opts["js_runtimes"] = {runtime[0]: {}}
            with yt_dlp.YoutubeDL(opts) as ydl:
                info = ydl.extract_info(url, download=True); prepared = Path(ydl.prepare_filename(info))
            candidates = [destination, prepared, prepared.with_suffix(".mp4"), prepared.with_suffix(".mkv"), prepared.with_suffix(".webm"), prepared.with_suffix(".m4v")] + list(destination.parent.glob(destination.stem + ".*"))
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

# Remaining API/job functions are intentionally kept below the existing implementation.

def process_file(input_file: Path, job_id: str, options: ProcessOptions) -> dict[str, Any]:
    update_job(job_id, progress=35, message="Inspecting video and audio…"); duration, has_audio, width, height = probe_video(input_file)
    update_job(job_id, progress=48, message=f"Transcribing with local Whisper ({options.model})…")
    transcription = transcribe(input_file, options.model, options.language) if has_audio else {"text": "", "segments": [], "language": "unknown", "error": "No audio stream found"}
    update_job(job_id, progress=62, message="Finding hooks, context and diverse moments…")
    highlights = build_candidates(transcription, duration, options.num_clips, options.clip_duration, options.remove_filler) or fallback_candidates(duration, options.num_clips, options.clip_duration)
    update_job(job_id, progress=70, message="Rendering creator-ready 9:16 Shorts…"); clips = []
    for index, h in enumerate(highlights, 1):
        start = float(h["start"]); end = min(duration, start + options.clip_duration); actual = max(1.0, end - start); output = OUTPUT_DIR / f"{job_id}_clip_{index}.mp4"
        create_short(input_file, output, start, actual, transcription, options); thumb = OUTPUT_DIR / f"{job_id}_clip_{index}.jpg"
        try: create_thumbnail(input_file, thumb, start, options.smart_crop, options.crop_mode)
        except Exception: thumb = None
        metadata = make_metadata(h["text"], index) if options.generate_metadata else {}
        clips.append({"clip_number": index, "title": metadata.get("title", f"AI Short #{index}"), "score": h["score"], "text": h["text"], "start": round(start, 2), "end": round(end, 2), "duration": round(actual, 2), "download_url": f"/download/{output.name}", "thumbnail_url": f"/download/{thumb.name}" if thumb else None, "metadata": metadata, "format": "9:16", "resolution": "1080x1920"})
        update_job(job_id, progress=min(95, 70 + int(index / max(1, len(highlights)) * 25)), message=f"Rendered clip {index}/{len(highlights)}")
    manifest = {"job_id": job_id, "source": input_file.name, "source_duration": duration, "source_resolution": f"{width}x{height}", "output_format": "9:16", "output_resolution": "1080x1920", "whisper": transcription.get("language", "unknown"), "transcription_error": transcription.get("error"), "settings": options.model_dump(), "clips": clips}
    manifest_path = OUTPUT_DIR / f"{job_id}_manifest.json"; manifest_path.write_text(json.dumps(manifest, indent=2, ensure_ascii=False), encoding="utf-8")
    zip_path = OUTPUT_DIR / f"{job_id}_shorts.zip"
    with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as z:
        for c in clips:
            video = OUTPUT_DIR / Path(c["download_url"]).name; z.write(video, video.name)
            if c["thumbnail_url"]: z.write(OUTPUT_DIR / Path(c["thumbnail_url"]).name, Path(c["thumbnail_url"]).name)
        z.write(manifest_path, manifest_path.name)
    return {"job_id": job_id, "status": "completed", "duration": duration, "transcript": transcription.get("text", ""), "transcript_language": transcription.get("language", "unknown"), "transcription_error": transcription.get("error"), "clips": clips, "download_all_url": f"/download-all/{job_id}", "manifest_url": f"/download/{manifest_path.name}"}

def run_job(job_id: str, input_file: Path, options: ProcessOptions) -> None:
    try:
        result = process_file(input_file, job_id, options); update_job(job_id, status="completed", progress=100, message="Done", result=result)
    except Exception as exc:
        print(f"Job {job_id} failed: {exc}"); update_job(job_id, status="failed", progress=100, message=str(exc), error=str(exc))
    finally:
        input_file.unlink(missing_ok=True)

@app.get("/")
def root(): return {"name": "ClipForge AI", "version": "5.0.1", "format": "9:16", "resolution": "1080x1920", "whisper_ffmpeg": WHISPER_FFMPEG.exists()}

@app.get("/health")
def health(): return {"status": "ok", "version": "5.0.1", "ffmpeg": Path(FFMPEG).name, "whisper_ffmpeg": WHISPER_FFMPEG.exists(), "whisper": module_available("whisper"), "features": ["local-whisper", "hook-ranking", "filler-reduction", "captions", "9:16", "1080x1920", "blur-background", "audio-normalization", "quality-presets", "metadata", "thumbnails", "zip-export"]}

@app.post("/process")
async def process(background_tasks: BackgroundTasks, file: UploadFile = File(...), options: str = "{}"):
    suffix = Path(file.filename or "video.mp4").suffix.lower()
    if suffix not in ALLOWED_EXTENSIONS: raise HTTPException(400, "Unsupported video format")
    try: opts = ProcessOptions.model_validate_json(options)
    except Exception as exc: raise HTTPException(400, f"Invalid options: {exc}")
    job_id = str(uuid.uuid4()); destination = UPLOAD_DIR / f"{job_id}{suffix}"
    with destination.open("wb") as out:
        size = 0
        while chunk := await file.read(1024 * 1024):
            size += len(chunk)
            if size > MAX_UPLOAD_BYTES: destination.unlink(missing_ok=True); raise HTTPException(413, "Video exceeds 2 GB limit")
            out.write(chunk)
    with JOBS_LOCK: JOBS[job_id] = {"job_id": job_id, "status": "queued", "progress": 5, "message": "Video uploaded…"}
    background_tasks.add_task(run_job, job_id, destination, opts)
    return {"job_id": job_id}

@app.post("/process-url")
async def process_url(request: YouTubeRequest, background_tasks: BackgroundTasks):
    url = str(request.url)
    if not validate_youtube_url(url): raise HTTPException(400, "Only YouTube URLs are supported")
    job_id = str(uuid.uuid4()); destination = UPLOAD_DIR / f"{job_id}.mp4"
    with JOBS_LOCK: JOBS[job_id] = {"job_id": job_id, "status": "downloading", "progress": 8, "message": "Downloading YouTube video…"}
    def download_and_run():
        try:
            download_youtube(url, destination, job_id); update_job(job_id, status="processing", progress=30, message="Download complete")
            run_job(job_id, destination, request.options)
        except Exception as exc:
            print(f"YouTube job {job_id} failed: {exc}"); update_job(job_id, status="failed", progress=100, message=str(exc), error=str(exc)); destination.unlink(missing_ok=True)
    background_tasks.add_task(download_and_run)
    return {"job_id": job_id}

@app.get("/jobs/{job_id}")
def job_status(job_id: str):
    with JOBS_LOCK: job = JOBS.get(job_id)
    if not job: raise HTTPException(404, "Job not found")
    return job

@app.get("/download/{filename}")
def download(filename: str):
    safe = Path(filename).name; path = OUTPUT_DIR / safe
    if not path.is_file(): raise HTTPException(404, "File not found")
    return FileResponse(path)

@app.get("/download-all/{job_id}")
def download_all(job_id: str):
    path = OUTPUT_DIR / f"{job_id}_shorts.zip"
    if not path.is_file(): raise HTTPException(404, "ZIP not found")
    return FileResponse(path, filename=path.name, media_type="application/zip")

@app.get("/transcript/{job_id}")
def transcript(job_id: str):
    with JOBS_LOCK: job = JOBS.get(job_id)
    if not job: raise HTTPException(404, "Job not found")
    result = job.get("result", {})
    return {"job_id": job_id, "language": result.get("transcript_language", "unknown"), "text": result.get("transcript", ""), "error": result.get("transcription_error")}
