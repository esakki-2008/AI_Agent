# ClipForge AI

**Local AI YouTube-to-Shorts generator — no API key required.**

Paste a YouTube video URL or upload a video. ClipForge downloads/analyzes it, transcribes speech with local Whisper, ranks promising moments, renders vertical Shorts, burns captions, creates thumbnails and publishing metadata, and exports the results.

## Feature set

### AI clipping
- YouTube URL input and local video upload.
- Local Whisper models: Tiny, Base, Small, Medium.
- Auto language detection plus English, Hindi, Tamil, Telugu, Malayalam and Kannada.
- Transcript-aware highlight ranking.
- Hook scoring using questions, numbers, strong keywords, audience language and contrast/context words.
- Overlap-aware selection for more diverse clips.
- Fallback clip selection when transcription is unavailable.
- Generate **1–10 Shorts**.
- Select **15, 30, 45 or 60 seconds**.

### Shorts production
- Vertical **9:16** output.
- **1080×1920** MP4.
- H.264 video + AAC audio.
- Fast-start MP4 for web/social playback.
- Optional burned-in captions from Whisper timestamps.
- Smart crop or letterboxed vertical formatting.
- Automatic thumbnail JPG for every Short.
- Suggested title, description and hashtags.
- Full transcript export.
- Individual MP4, thumbnail and transcript downloads.
- One-click **Download all** ZIP export.
- In-browser video preview with native controls.

### Creator dashboard
- Live processing progress and stage messages.
- Engine health indicator for FFmpeg, Whisper, yt-dlp and Deno.
- Advanced generation settings.
- Recent local job history.
- Responsive desktop/mobile UI.
- Local-first architecture; no OpenAI API key.

## Requirements

- Windows, macOS, or Linux
- Python 3.10+
- Node.js 18+
- Internet access for YouTube downloads and the first Whisper model download
- No separate system FFmpeg installation is required; `imageio-ffmpeg` supplies the binary.
- Deno is optional but recommended for current YouTube extraction.

## Windows CMD setup

### Backend

```cmd
cd /d "D:\AI AGENT\backend"
python -m pip install -r requirements.txt
python -m uvicorn main:app --reload
```

Keep this CMD window running.

### Backend health check

Open another CMD:

```cmd
curl http://127.0.0.1:8000/health
```

The response reports whether FFmpeg, Whisper and yt-dlp are available.

### Frontend

Open another CMD:

```cmd
cd /d "D:\AI AGENT\frontend"
npm install
npm run dev
```

Open the Vite address shown by CMD, normally `http://localhost:5173`.

## YouTube workflow

1. Paste a public YouTube URL.
2. Choose 1–10 clips.
3. Choose 15, 30, 45 or 60 seconds.
4. Choose the local Whisper model and transcript language.
5. Toggle captions, smart crop and metadata generation.
6. Click **Generate best clips**.
7. ClipForge downloads the source, transcribes it locally and ranks candidate moments.
8. Each selected moment is rendered as a 1080×1920 MP4.
9. Preview clips in the dashboard.
10. Download MP4s, thumbnails, the transcript, or everything as a ZIP.

## API endpoints

| Endpoint | Purpose |
|---|---|
| `GET /` | Service information |
| `GET /health` | Runtime/dependency health |
| `GET /jobs` | Recent in-memory jobs |
| `POST /process-url` | Queue a YouTube URL |
| `POST /process` | Queue a local upload |
| `GET /jobs/{job_id}` | Poll job progress/result |
| `GET /transcript/{job_id}` | Download transcript text |
| `GET /download/{filename}` | Download generated media |
| `GET /download-all/{job_id}` | Download all Shorts as ZIP |

## Architecture

```text
YouTube URL / Upload
        ↓
      yt-dlp
        ↓
   Local video file
        ↓
 Local Whisper ASR
        ↓
 Transcript + timestamps
        ↓
 Hook / context ranking
        ↓
 FFmpeg 9:16 rendering
        ↓
 Captions + thumbnail + metadata
        ↓
 Preview / MP4 / ZIP export
```

## Notes

Whisper models are downloaded once and then reused from the local Whisper cache. Processing time depends on video length, CPU/GPU, resolution and model size.

YouTube extraction can change as YouTube changes its player. ClipForge uses `yt-dlp`, FFmpeg and Deno when Deno is available on PATH.

Only process videos you own or have permission to download, transform and redistribute. You are responsible for complying with YouTube's terms and applicable copyright laws.
