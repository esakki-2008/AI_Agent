# ClipForge AI

ClipForge AI is a local-first video repurposing MVP: upload a long-form video, transcribe speech with Whisper, score candidate moments, crop them to 9:16, burn captions, and download MP4 Shorts.

## Stack
- React + Vite
- FastAPI
- OpenAI Whisper (local)
- imageio-ffmpeg (bundled FFmpeg binary)

No Ollama and no paid API key are required.

## Windows quick start

### Backend
```powershell
cd "D:\AI AGENT\backend"
python -m pip install -r requirements.txt
python -m uvicorn main:app --reload
```
Open http://127.0.0.1:8000/health

### Frontend
Open a second terminal:
```powershell
cd "D:\AI AGENT\frontend"
npm install
npm run dev
```
Open http://localhost:5173

## Production notes
This repository is a production-oriented MVP, not a hosted multi-tenant SaaS yet. Before public deployment, add authentication, persistent job storage, a background queue, object storage, rate limiting, usage quotas, billing, monitoring, HTTPS, and a dedicated FFmpeg/Whisper worker pool.

## Supported uploads
MP4, MOV, MKV, AVI, WebM and M4V. Maximum upload size is 2 GB.

## Output
Clips are 1080x1920 (9:16), H.264 video, AAC audio, optimized for browser playback with `faststart`.
