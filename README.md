# ClipForge AI

**Local AI YouTube-to-Shorts generator — no API key required.**

Paste a YouTube video URL, or upload a video, and ClipForge automatically downloads/analyzes it, transcribes speech with Whisper, ranks strong moments, renders vertical Shorts, burns captions, creates titles/hashtags, thumbnails, and lets you download all results as a ZIP.

## Feature set

### AI clipping
- YouTube URL input and local video upload.
- Local Whisper models: Tiny, Base, Small, Medium.
- Transcript-aware highlight ranking.
- Hook detection using questions, numbers, strong keywords, audience language, contrast words, and useful phrases.
- Overlap-aware selection so generated clips are diverse.
- Automatic fallback clip selection when speech transcription is unavailable.
- Generate **1–10 Shorts**.
- Select **15, 20, 30, 45, or 60 seconds**.

### Shorts production
- Vertical **9:16** output.
- **1080×1920** MP4.
- H.264 video + AAC audio.
- Fast-start MP4 for web/social playback.
- Optional burned-in captions from Whisper timestamps.
- Automatic thumbnail JPG for each Short.
- Creator metadata: suggested title, description, and hashtags.
- Full transcript available after processing.
- Individual MP4 and thumbnail downloads.
- One-click **Download all** ZIP export.

### App experience
- Live processing progress.
- Stages: Download → Whisper → Rank → Render → Export.
- Engine health indicator.
- Advanced settings panel.
- Responsive creator dashboard for desktop and mobile.
- No OpenAI API key.
- FFmpeg supplied through `imageio-ffmpeg`.
- YouTube extraction through `yt-dlp`.

## Requirements

- Windows, macOS, or Linux
- Python 3.10+
- Node.js 18+
- Internet access for YouTube downloads and the first Whisper model download
- No separate system FFmpeg installation is required.
- Deno is optional but recommended for more reliable current YouTube extraction.

## Windows CMD setup

### 1. Backend

```cmd
cd /d "D:\AI AGENT\backend"
python -m pip install -r requirements.txt
python -m uvicorn main:app --reload
```

Keep this CMD window running.

### 2. Test the backend

Open another CMD:

```cmd
curl http://127.0.0.1:8000/health
```

You should see JSON showing FFmpeg, Whisper and yt-dlp status.

### 3. Frontend

Open another CMD:

```cmd
cd /d "D:\AI AGENT\frontend"
npm install
npm run dev
```

Open the Vite address shown by CMD, normally:

```text
http://localhost:5173
```

## YouTube workflow

1. Paste a YouTube URL such as `https://youtu.be/...`.
2. Select the number of Shorts.
3. Select clip length.
4. Choose the Whisper model.
5. Enable/disable captions, smart vertical formatting, and metadata.
6. Click **Generate Best Shorts**.
7. Wait for download, transcription, ranking and rendering.
8. Preview every Short.
9. Download an individual MP4, its thumbnail, or all Shorts as a ZIP.

## API endpoints

| Endpoint | Purpose |
|---|---|
| `GET /` | Service information |
| `GET /health` | Runtime/dependency health |
| `POST /process-url` | Queue a YouTube URL |
| `POST /process` | Queue a local upload |
| `GET /jobs/{job_id}` | Poll job progress/result |
| `GET /download/{filename}` | Download generated media |
| `GET /download-all/{job_id}` | Download all Shorts as ZIP |

## Notes

The app is intentionally local-first. Whisper models are downloaded once and then reused from the local Whisper cache. Processing speed depends heavily on your CPU/GPU, video length, resolution, and Whisper model size.

YouTube extraction can change as YouTube changes its player. `yt-dlp` is used with FFmpeg and automatically uses Deno if it is available on PATH.

Only process videos you own or have permission to download, transform, and redistribute. You are responsible for complying with YouTube's terms and applicable copyright laws.
