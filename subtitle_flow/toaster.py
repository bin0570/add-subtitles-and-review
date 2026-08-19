"""把字幕交付成文件的环节。

统一产出:
  - output.srt(推荐,使用修正后文本)
  - output.ass(带样式的字幕)
  - output.original.srt(机器原话,随时回退)
  - 可选:output.mp4(把字幕烧进视频)

mock 模式下不真正调用 FFmpeg,mp4 返回 None。
"""
from __future__ import annotations

import subprocess
from pathlib import Path

from .engine import Cue
from .formats import write_srt, write_ass
from .settings import Settings


class Burner:
    def __init__(self, settings: Settings):
        self.settings = settings

    def dump_texts(self, cues: list[Cue], out_dir: str, use_raw: bool = False) -> dict:
        """写 SRT + ASS + 原话 SRT。返回各自路径。"""
        d = Path(out_dir)
        d.mkdir(parents=True, exist_ok=True)
        srt = str(d / "output.srt")
        ass = str(d / "output.ass")
        srt_raw = str(d / "output.original.srt")
        write_srt(cues, srt, use_raw=use_raw)
        write_ass(cues, ass, self.settings.ass_style, use_raw=use_raw)
        write_srt(cues, srt_raw, use_raw=True)
        return {"srt": srt, "ass": ass, "srt_original": srt_raw}

    def burn_mp4(self, media_path: str, ass_path: str, out_dir: str) -> str | None:
        if self.settings.mock:
            return None
        d = Path(out_dir)
        d.mkdir(parents=True, exist_ok=True)
        out = str(d / "output.mp4")
        ass_esc = ass_path.replace("\\", "/")
        cmd = [
            self.settings.ffmpeg_bin, "-y", "-i", media_path,
            "-vf", f"subtitles='{ass_esc}'",
            "-c:a", "copy", "-c:v", "libx264", "-crf", "20", out,
        ]
        try:
            subprocess.run(cmd, capture_output=True, text=True, timeout=600, check=True)
        except subprocess.CalledProcessError as e:
            raise RuntimeError(f"FFmpeg 失败: {e.stderr[-500:]}") from e
        except FileNotFoundError:
            raise RuntimeError("未找到 ffmpeg,请先安装并加入 PATH。")
        return out if Path(out).exists() else None
