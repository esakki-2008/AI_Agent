from __future__ import annotations

from pathlib import Path
import statistics


def detect_speaker_center(video_path: Path, ffmpeg: str, sample_count: int = 12) -> float | None:
    """Estimate a stable face center as a normalized x position (0..1).

    Uses OpenCV's bundled Haar cascade locally. Returns None when OpenCV or
    face detection is unavailable, allowing the renderer to fall back safely.
    """
    try:
        import cv2
    except Exception:
        return None

    cascade_path = cv2.data.haarcascades + "haarcascade_frontalface_default.xml"
    detector = cv2.CascadeClassifier(cascade_path)
    if detector.empty():
        return None

    probe = __import__("subprocess").run(
        [ffmpeg, "-hide_banner", "-i", str(video_path)],
        stdout=__import__("subprocess").PIPE,
        stderr=__import__("subprocess").PIPE,
        text=True,
    )
    import re
    match = re.search(r"Duration:\s*(\d+):(\d+):([\d.]+)", probe.stderr)
    if not match:
        return None
    duration = int(match.group(1)) * 3600 + int(match.group(2)) * 60 + float(match.group(3))
    if duration <= 0:
        return None

    centers: list[float] = []
    for i in range(sample_count):
        timestamp = duration * (i + 0.5) / sample_count
        raw = __import__("subprocess").run(
            [ffmpeg, "-hide_banner", "-loglevel", "error", "-ss", f"{timestamp:.3f}", "-i", str(video_path), "-frames:v", "1", "-f", "image2", "pipe:1"],
            stdout=__import__("subprocess").PIPE,
            stderr=__import__("subprocess").PIPE,
        ).stdout
        if not raw:
            continue
        import numpy as np
        frame = cv2.imdecode(np.frombuffer(raw, dtype=np.uint8), cv2.IMREAD_COLOR)
        if frame is None:
            continue
        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        faces = detector.detectMultiScale(gray, scaleFactor=1.1, minNeighbors=5, minSize=(50, 50))
        if len(faces):
            # Prefer the largest detected face, normally the speaking subject.
            x, y, w, h = max(faces, key=lambda f: f[2] * f[3])
            centers.append((x + w / 2) / max(1, frame.shape[1]))

    return max(0.05, min(0.95, statistics.median(centers))) if centers else None
