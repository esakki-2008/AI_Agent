from __future__ import annotations

import re
from pathlib import Path
from typing import Any


def _ass_time(seconds: float) -> str:
    total_cs = max(0, int(round(seconds * 100)))
    h, rem = divmod(total_cs, 360000)
    m, rem = divmod(rem, 6000)
    s, cs = divmod(rem, 100)
    return f"{h}:{m:02d}:{s:02d}.{cs:02d}"


def _ass_escape(text: str) -> str:
    return str(text).replace("\\", "\\\\").replace("{", "\\{").replace("}", "\\}").replace("\n", " ").strip()


def _words_from_segments(segments: list[dict[str, Any]], start: float, end: float) -> list[tuple[float, float, str]]:
    words: list[tuple[float, float, str]] = []
    for seg in segments:
        for word in seg.get("words") or []:
            text = str(word.get("word", "")).strip()
            if not text:
                continue
            ws = float(word.get("start", seg.get("start", 0)))
            we = float(word.get("end", seg.get("end", ws + 0.2)))
            if we <= start or ws >= end:
                continue
            words.append((max(start, ws), min(end, we), text))
    return words


def make_dynamic_ass(
    transcription: dict[str, Any],
    start: float,
    end: float,
    path: Path,
    style: str = "bold",
) -> bool:
    words = _words_from_segments(transcription.get("segments", []), start, end)
    if not words:
        return False

    styles = {
        "bold": (24, 3, 4, 190, -1),
        "classic": (20, 2, 3, 180, -1),
        "minimal": (18, 1, 2, 160, -1),
    }
    font_size, outline, shadow, margin_v, _ = styles.get(style, styles["bold"])
    ass_style = (
        f"Style: Default,Arial,{font_size},&H00FFFFFF,&H000000FF,&H00000000,&H80000000,"
        f"-1,0,0,0,100,100,0,0,1,{outline},{shadow},2,10,10,{margin_v},1"
    )

    # Group roughly 1-5 words into readable caption events. Each event uses
    # ASS \k karaoke timing so the active word changes as it is spoken.
    events: list[tuple[float, float, list[tuple[float, float, str]]]] = []
    group: list[tuple[float, float, str]] = []
    for item in words:
        group.append(item)
        duration = item[1] - group[0][0]
        punctuation_break = bool(re.search(r"[.!?,;:]$", item[2]))
        if len(group) >= 5 or duration >= 2.6 or punctuation_break:
            events.append((group[0][0], group[-1][1], group))
            group = []
    if group:
        events.append((group[0][0], group[-1][1], group))

    lines = [
        "[Script Info]",
        "ScriptType: v4.00+",
        "PlayResX: 1080",
        "PlayResY: 1920",
        "ScaledBorderAndShadow: yes",
        "",
        "[V4+ Styles]",
        "Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding",
        ass_style,
        "",
        "[Events]",
        "Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text",
    ]

    for ev_start, ev_end, group in events:
        parts: list[str] = []
        for ws, we, text in group:
            centiseconds = max(1, int(round((we - ws) * 100)))
            parts.append("{" + f"\\k{centiseconds}" + "}" + _ass_escape(text))
        rel_start = ev_start - start
        rel_end = max(rel_start + 0.1, ev_end - start)
        lines.append(f"Dialogue: 0,{_ass_time(rel_start)},{_ass_time(rel_end)},Default,,0,0,0,,{' '.join(parts)}")

    path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return True
