# ClipForge AI

Local AI tool that turns a long video into short vertical clips.

## Features

- Paste a YouTube URL or upload a local video.
- Downloads YouTube media with `yt-dlp` and bundled `imageio-ffmpeg`.
- Local Whisper transcription; no OpenAI API key is required.
- Transcript-based highlight scoring for strong hooks, questions, tips, numbers, and key phrases.
- Generate 1–5 clips with selectable 15–60 second duration.
- 9:16, 1080×1920 MP4 output with H.264/AAC and fast-start metadata.
- Optional burned-in captions using Whisper timestamps.
- Background jobs with progress polling so long videos do not block the UI.
- Preview and download every generated Short.
- Health endpoint for FFmpeg, Whisper, yt-dlp, and Deno detection.
- CORS configurable through `CORS_ORIGINS`.

## Requirements

- Windows, macOS, or Linux
- Python 3.10+
- Node.js 18+
- Internet access for YouTube downloads and the first Whisper model download
- FFmpeg is supplied automatically through `imageio-ffmpeg`; a system FFmpeg install is not required.

## Run on Windows CMD

### Backend

```cmd
cd /d "D:\AI AGENT\backend"
python -m pip install -r requirements.txt
python -m uvicorn main:app --reload
```

Check:

```cmd
curl http://127.0.0.1:8000/health
```

### Frontend

Open a second CMD window:

```cmd
cd /d "D:\AI AGENT\frontend"
npm install
npm run dev
```

Then open the Vite address shown in CMD, normally `http://localhost:5173`.

## YouTube workflow

1. Paste a YouTube URL.
2. Choose number of Shorts, duration, and captions.
3. Click **Generate Best Shorts**.
4. ClipForge downloads the source, transcribes it locally, ranks candidate moments, and renders the Shorts.
5. Preview or download the generated MP4 files.

### Important YouTube note

Current YouTube extraction can sometimes require a JavaScript runtime. ClipForge automatically uses Deno when it is installed and falls back to yt-dlp's available extraction methods when it is not. Installing Deno is optional but can improve compatibility with current YouTube changes.

## API

- `GET /health` — dependency/runtime health.
- `POST /process-url` — queue a YouTube job.
- `POST /process` — queue an uploaded video job.
- `GET /jobs/{job_id}` — job progress/result.
- `GET /download/{filename}` — generated MP4 download.

## Project layout

```text
AI_Agent/
├── backend/
│   ├── main.py
│   └── requirements.txt
├── frontend/
│   ├── src/
│   │   ├── App.jsx
│   │   ├── main.jsx
│   │   └── style.css
│   ├── .env.example
│   ├── index.html
│   ├── package.json
│   └── vite.config.js
├── outputs/
├── uploads/
└── README.md
```

## Copyright / permissions

Only process videos you own or have permission to download, transform, and redistribute. You are responsible for complying with YouTube's terms and applicable copyright laws.
