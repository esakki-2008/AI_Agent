# ClipForge AI — Short Clip Generator

Turn long-form videos into vertical Shorts with local AI.

## Features

- Upload MP4, MOV, MKV, AVI, WebM, or M4V
- Automatic audio detection
- Whisper transcription when speech/audio is available
- Highlight scoring based on transcript signals
- Up to 5 clips per video
- 9:16 vertical 1080x1920 output
- MP4 export with AAC audio
- Browser preview and download
- No paid API key required

## Architecture

```text
React + Vite frontend
        ↓
FastAPI backend
        ↓
Whisper + FFmpeg
        ↓
AI highlight selection
        ↓
Vertical MP4 clips
```

## Windows setup

### Backend

```powershell
cd backend
python -m pip install -r requirements.txt
python -m uvicorn main:app --reload
```

Backend: http://127.0.0.1:8000
Swagger: http://127.0.0.1:8000/docs

### Frontend

```powershell
cd frontend
npm install
npm run dev
```

Frontend: http://localhost:5173

## FFmpeg

The backend uses `imageio-ffmpeg`, so a separate system FFmpeg installation is not required.

## Notes

The first Whisper run downloads the selected model. The current MVP uses the `base` model and CPU-safe transcription (`fp16=False`).

## Roadmap

- Word-level animated captions
- Face-aware smart cropping
- Hook/title generation
- Background music
- Multiple caption styles
- Job queue and progress tracking
- Creator accounts and billing
- Cloud deployment
