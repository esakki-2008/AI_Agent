# ClipForge AI v1.0.0 — Product Manifest

## Product

ClipForge AI is a local-first video repurposing application that turns long videos into short-form vertical clips using local speech transcription and video processing.

## Version

**1.0.0**

## Included application

- React/Vite creator dashboard
- FastAPI local backend
- Local Whisper transcription
- yt-dlp YouTube ingestion
- Local FFmpeg processing through imageio-ffmpeg
- Transcript-aware highlight selection
- 9:16 vertical rendering
- Caption generation
- Dynamic word-level captions when Whisper word timestamps are available
- Face-aware framing option using local OpenCV detection
- Thumbnails and creator metadata
- ZIP export
- Windows setup and launch scripts

## Customer requirements

- Windows 10/11, macOS, or Linux
- Python 3.10+
- Node.js 18+
- Internet access for initial dependency/model downloads and YouTube ingestion
- 8 GB RAM or more recommended for the Base Whisper model
- More capable hardware is recommended for larger Whisper models

## Windows entry points

- `setup_windows.bat` — install dependencies and prepare runtime folders
- `start_windows.bat` — start the local backend and frontend
- `docs/INSTALLATION.md` — customer installation and troubleshooting guide

## Package exclusions

Do not include these generated/runtime directories in a customer archive:

- `node_modules/`
- `frontend/dist/`
- `uploads/` generated media
- `outputs/` generated media
- local Python caches
- editor configuration
- personal environment files such as `.env`

## License

Purchased copies are governed by `COMMERCIAL_LICENSE.md` and the final license terms shown on the applicable sales page.

## Support scope

The product documentation covers installation, startup, common dependency problems, YouTube extraction issues, and processing performance basics. Updates or ongoing support are included only when explicitly stated on the sales page.
