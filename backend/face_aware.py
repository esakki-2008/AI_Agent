from __future__ import annotations

from pathlib import Path
import subprocess
import tempfile
from typing import Optional


def detect_crop_x(ffmpeg: str, video: Path, start: float, duration: float, out_width: int = 1080, out_height: int = 1920) -> Optional[int]:
    """Estimate a horizontal crop position from sampled video frames.

    Uses OpenCV's bundled Haar cascade locally. Returns the left x-coordinate
    in the source frame, or None when no face can be detected.
    """
    try:
        import cv2
    except Exception:
        return None

    cap = cv2.VideoCapture(str(video))
    if not cap.isOpened():
        return None
    fps = cap.get(cv2.CAP_PROP_FPS) or 25.0
    width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH) or 0)
    height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT) or 0)
    if width <= 0 or height <= 0:
        cap.release()
        return None

    # For 9:16, calculate the source-space crop width.
    crop_w = min(width, max(1, int(height * out_width / out_height)))
    if crop_w >= width:
        cap.release()
        return 0

    cascade_path = Path(cv2.data.haarcascades) / "haarcascade_frontalface_default.xml"
    detector = cv2.CascadeClassifier(str(cascade_path))
    centers: list[float] = []
    samples = 9
    for i in range(samples):
        t = start + (duration * i / max(1, samples - 1))
        cap.set(cv2.CAP_PROP_POS_MSEC, max(0.0, t) * 1000.0)
        ok, frame = cap.read()
        if not ok:
            continue
        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        gray = cv2.resize(gray, None, fx=0.5, fy=0.5)
        faces = detector.detectMultiScale(gray, scaleFactor=1.1, minNeighbors=5, minSize=(30, 30))
        if len(faces):
            # Prefer the largest detected face in each sample.
            x, y, w, h = max(faces, key=lambda f: f[2] * f[3])
            centers.append((x + w / 2.0) * 2.0)
    cap.release()
    if not centers:
        return None

    centers.sort()
    center = centers[len(centers) // 2]
    x = int(round(center - crop_w / 2.0))
    return max(0, min(width - crop_w, x))


def face_aware_filter(ffmpeg: str, video: Path, start: float, duration: float) -> str:
    """Return an FFmpeg filter for a face-centered 9:16 crop, with fallback."""
    x = detect_crop_x(ffmpeg, video, start, duration)
    if x is None:
        return "scale=1080:1920:force_original_aspect_ratio=increase,crop=1080:1920"
    return f"scale=-2:1920,crop=1080:1920:{x}:0"
