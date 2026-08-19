"""SRT / ASS 字幕文件的读写,以及时间格式换算。"""
from __future__ import annotations

import re
from pathlib import Path

from .engine import Cue


def srt_timestamp(sec: float) -> str:
    """秒 -> SRT 时间格式 HH:MM:SS,mmm。"""
    sec = max(0.0, sec)
    ms = int(round(sec * 1000))
    h, ms = divmod(ms, 3_600_000)
    m, ms = divmod(ms, 60_000)
    s, ms = divmod(ms, 1000)
    return f"{h:02d}:{m:02d}:{s:02d},{ms:03d}"


def ass_timestamp(sec: float) -> str:
    """秒 -> ASS 时间格式 H:MM:SS.cc。"""
    sec = max(0.0, sec)
    cs = int(round(sec * 100))
    h, cs = divmod(cs, 360_000)
    m, cs = divmod(cs, 6000)
    s, cs = divmod(cs, 100)
    return f"{h}:{m:02d}:{s:02d}.{cs:02d}"


def write_srt(cues: list[Cue], path: str, use_raw: bool = False) -> str:
    """写 SRT。use_raw=True 时强制输出机器原话那一层。"""
    lines: list[str] = []
    for n, c in enumerate(cues, 1):
        text = c.raw_text if use_raw else c.pick
        if not text.strip():
            continue
        lines.append(str(n))
        lines.append(f"{srt_timestamp(c.start)} --> {srt_timestamp(c.end)}")
        lines.append(text.strip())
        lines.append("")
    content = "\n".join(lines).rstrip() + "\n"
    Path(path).write_text(content, encoding="utf-8")
    return path


_ASS_HEADER = """[Script Info]
ScriptType: v4.00+
WrapStyle: 2
ScaledBorderAndShadow: yes

[V4+ Styles]
Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding
Style: Default, {FontName}, {FontSize}, {PrimaryColour}, &H000000FF, {OutlineColour}, &H00000000, {Bold}, 0, 0, 0, 100, 100, 0, 0, 1, {Outline}, {Shadow}, {Alignment}, 20, 20, {MarginV}, 1

[Events]
Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text
"""


def write_ass(cues: list[Cue], path: str, style: dict, use_raw: bool = False) -> str:
    """写 ASS。样式从 style 字典读取。"""
    header = _ASS_HEADER.format(
        FontName=style.get("FontName", "Microsoft YaHei"),
        FontSize=style.get("FontSize", 36),
        PrimaryColour=style.get("PrimaryColour", "&H00FFFFFF"),
        OutlineColour=style.get("OutlineColour", "&H00000000"),
        Bold=style.get("Bold", 0),
        Outline=style.get("Outline", 2),
        Shadow=style.get("Shadow", 1),
        Alignment=style.get("Alignment", 2),
        MarginV=style.get("MarginV", 40),
    )
    lines = [header]
    for c in cues:
        text = c.raw_text if use_raw else c.pick
        if not text.strip():
            continue
        escaped = text.strip().replace("\\", "\\\\").replace("{", "\\{").replace("}", "\\}")
        lines.append(
            f"Dialogue: 0,{ass_timestamp(c.start)},{ass_timestamp(c.end)},Default,,0,0,0,,{escaped}"
        )
    content = "\n".join(lines).rstrip() + "\n"
    Path(path).write_text(content, encoding="utf-8")
    return path


_TS_PATTERN = re.compile(
    r"(\d{2}):(\d{2}):(\d{2}),(\d{3})\s*-->\s*(\d{2}):(\d{2}):(\d{2}),(\d{3})"
)


def _to_seconds(h, m, s, ms) -> float:
    return int(h) * 3600 + int(m) * 60 + int(s) + int(ms) / 1000.0


def read_srt(path: str) -> list[Cue]:
    """把已有 SRT 解析回 Cue 列表。时间轴文本放进 raw_text。"""
    raw = Path(path).read_text(encoding="utf-8")
    blocks = [b.strip() for b in raw.split("\n\n") if b.strip()]
    cues: list[Cue] = []
    for i, block in enumerate(blocks, 1):
        lines = block.splitlines()
        ts_line = next((l for l in lines if "-->" in l), None)
        if not ts_line:
            continue
        m = _TS_PATTERN.search(ts_line)
        if not m:
            continue
        start = _to_seconds(*m.group(1, 2, 3, 4))
        end = _to_seconds(*m.group(5, 6, 7, 8))
        text = "\n".join(l for l in lines if l != ts_line and not l.strip().isdigit())
        cues.append(Cue(index=i, start=start, end=end, raw_text=text.strip()))
    return cues
