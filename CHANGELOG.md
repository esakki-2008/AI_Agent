# Changelog

## [1.0.0] — 2026-09-14

### Added

- Local AI YouTube-to-Shorts workflow.
- Local video upload workflow.
- Whisper-based transcription with Tiny, Base, Small and Medium models.
- Transcript-aware highlight ranking and overlap-aware clip selection.
- 15, 30, 45 and 60 second clip lengths.
- 9:16 1080×1920 MP4 rendering.
- Auto captions and dynamic word-level captions.
- Center, blur, fit and face-aware framing modes.
- Thumbnail generation.
- Titles, descriptions, hashtags and transcript export.
- Individual downloads and ZIP export.
- Local processing progress and engine health indicators.
- Windows setup and startup scripts.
- Commercial license and installation documentation.
- Frontend production build support and CI checks.

### Notes

- Processing remains local after a source video is downloaded.
- Whisper models may require a first-run download.
- YouTube extraction depends on current yt-dlp/YouTube compatibility and may require Deno for best reliability.
