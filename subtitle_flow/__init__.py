"""给视频添加字幕,并复核后修改 —— 核心流程包。"""
# © 2026 薯条 Allen (binbin0570) — 个人封装的字幕处理工具 (MIT License)
from .engine import Cue, Issue, Transcript
from .formats import read_srt, write_srt, write_ass
from .settings import Settings
from .runner import run_all

__all__ = [
    "Cue",
    "Issue",
    "Transcript",
    "read_srt",
    "write_srt",
    "write_ass",
    "Settings",
    "run_all",
]
__version__ = "1.0.0"
