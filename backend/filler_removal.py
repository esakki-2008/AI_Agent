from __future__ import annotations

from pathlib import Path
import re
import subprocess
from typing import Any

FILLER_RE = re.compile(r"\b(?:um+|uh+|erm+|hmm+|mm+|you know|i mean|basically|actually)\b", re.I)


def filler_ranges(segments: list[dict[str, Any]], min_pause: float = 0.65) -> list[tuple[float, float]]:
    ranges: list[tuple[float, float]] = []
    for seg in segments:
        text = str(seg.get("text", ""))
        start, end = float(seg.get("start", 0)), float(seg.get("end", 0))
        if end <= start:
            continue
        if FILLER_RE.search(text.strip()) and (end - start) <= 3.0:
            ranges.append((start, end))
    for prev, cur in zip(segments, segments[1:]):
        gap = float(cur.get("start", 0)) - float(prev.get("end", 0))
        if gap >= min_pause:
            ranges.append((float(prev.get("end", 0)), float(cur.get("start", 0))))
    return merge_ranges(ranges)


def merge_ranges(ranges: list[tuple[float, float]]) -> list[tuple[float, float]]:
    if not ranges:
        return []
    ranges = sorted((max(0, s), max(0, e)) for s, e in ranges if e > s)
    merged = [ranges[0]]
    for s, e in ranges[1:]:
        ps, pe = merged[-1]
        if s <= pe + 0.08:
            merged[-1] = (ps, max(pe, e))
        else:
            merged.append((s, e))
    return merged


def build_keep_ranges(start: float, end: float, remove: list[tuple[float, float]], pad: float = 0.06) -> list[tuple[float, float]]:
    cuts = [(max(start, s - pad), min(end, e + pad)) for s, e in remove if e > start and s < end]
    cuts = merge_ranges(cuts)
    keep: list[tuple[float, float]] = []
    cursor = start
    for s, e in cuts:
        if s > cursor + 0.03:
            keep.append((cursor, s))
        cursor = max(cursor, e)
    if end > cursor + 0.03:
        keep.append((cursor, end))
    return keep


def render_without_fillers(ffmpeg: str, source: Path, output: Path, start: float, end: float, segments: list[dict[str, Any]]) -> bool:
    cuts = filler_ranges(segments)
    if not cuts:
        return False
    keep = build_keep_ranges(start, end, cuts)
    if len(keep) <= 1:
        return False

    inputs: list[str] = []
    filters: list[str] = []
    for idx, (s, e) in enumerate(keep):
        inputs += ["-ss", f"{s:.3f}", "-to", f"{e:.3f}", "-i", str(source)]
        filters.append(f"[{idx}:v:0][{idx}:a:0]setpts=PTS-STARTPTS,asetpts=PTS-STARTPTS[v{idx}][a{idx}]")
    concat_inputs = "".join(f"[v{i}][a{i}]" for i in range(len(keep)))
    filters.append(f"{concat_inputs}concat=n={len(keep)}:v=1:a=1[v][a]")
    cmd = [ffmpeg, "-hide_banner", "-loglevel", "error", *inputs, "-filter_complex", ";".join(filters), "-map", "[v]", "-map", "[a]", "-c:v", "libx264", "-preset", "veryfast", "-crf", "20", "-c:a", "aac", "-b:a", "160k", "-movflags", "+faststart", "-y", str(output)]
    try:
        result = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, timeout=600)
        return result.returncode == 0 and output.exists() and output.stat().st_size > 1024
    except Exception:
        return False
