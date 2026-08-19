"""字幕流程的数据模型。

这里的核心思想:一段话被"转写"出来后,
原始文本永远保留,任何修正都写进另一层,互不覆盖。
这样无论改多少次,都能随时回到机器原话。
"""
from __future__ import annotations

from dataclasses import dataclass, field, asdict
from typing import Optional


@dataclass
class Issue:
    """某个环节提出的可复核问题。"""
    stage: str          # 来源环节: asr / grammar / visual
    level: str          # 轻量级: info / warn / error
    reason: str
    suggest: str = ""   # 给修正建议文本


@dataclass
class Cue:
    """一条字幕。start/end 是秒。"""
    index: int
    start: float
    end: float
    raw_text: str            # ASR 原话,永不被改动
    fixed_text: str = ""     # 修正层,空表示未修正
    confidence: float = 1.0
    hotwords: list[str] = field(default_factory=list)
    issues: list[Issue] = field(default_factory=list)
    frames: list[str] = field(default_factory=list)   # 画面核对抽出的帧
    visual_note: str = ""
    visual_ok: Optional[bool] = None

    @property
    def is_fixed(self) -> bool:
        return bool(self.fixed_text) and self.fixed_text != self.raw_text

    @property
    def pick(self) -> str:
        """当前显示的文本:优先修正层,否则原话。"""
        return self.fixed_text if self.fixed_text else self.raw_text

    @property
    def has_issues(self) -> bool:
        return len(self.issues) > 0

    def mark(self, stage: str, level: str, reason: str, suggest: str = "") -> None:
        self.issues.append(Issue(stage, level, reason, suggest))

    def to_dict(self) -> dict:
        d = asdict(self)
        d["is_fixed"] = self.is_fixed
        d["has_issues"] = self.has_issues
        return d

    @classmethod
    def from_dict(cls, d: dict) -> "Cue":
        return cls(
            index=d["index"], start=d["start"], end=d["end"],
            raw_text=d["raw_text"], fixed_text=d.get("fixed_text", ""),
            confidence=d.get("confidence", 1.0), hotwords=d.get("hotwords", []),
            issues=[Issue(**i) for i in d.get("issues", [])],
            frames=d.get("frames", []),
            visual_note=d.get("visual_note", ""),
            visual_ok=d.get("visual_ok"),
        )


@dataclass
class Transcript:
    language: str = "zh"
    hotwords: list[str] = field(default_factory=list)
    cues: list[Cue] = field(default_factory=list)

    def to_dict(self) -> dict:
        return {
            "language": self.language,
            "hotwords": self.hotwords,
            "cues": [c.to_dict() for c in self.cues],
        }
