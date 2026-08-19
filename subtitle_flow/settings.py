"""统一读取配置:优先 config.json,环境变量 `SUB_` 前缀可覆盖。

配置项以键值形式存在,代码通过 Settings 数据类访问。
"""
from __future__ import annotations

import json
import os
from dataclasses import dataclass, field, asdict
from typing import Any

ENV_PREFIX = "SUB_"

DEFAULTS: dict[str, Any] = {
    # 转写后端: "utaudio" | "groq"
    "asr_backend": "groq",
    "utaudio_url": "https://api.utaudio.com/v1/transcribe",
    "utaudio_key": "",
    "groq_base_url": "https://api.groq.com/openai/v1",
    "groq_api_key": "",
    "whisper_model": "whisper-large-v3-turbo",
    # LLM(OpenAI 兼容)后端
    "llm_base_url": "https://api.groq.com/openai/v1",
    "llm_api_key": "",
    "grammar_model": "qwen/qwen3.6-27b",
    "visual_model": "qwen/qwen3.6-27b",
    "language": "zh",
    "hotwords": [],
    "ffmpeg_bin": "ffmpeg",
    "ffprobe_bin": "ffprobe",
    "mock": False,
    "frame_window": 0.5,
    "frame_count": 3,
    "grammar_chunk": 15,
    "request_timeout": 120,
    "ass_style": {
        "FontName": "Microsoft YaHei",
        "FontSize": 36,
        "PrimaryColour": "&H00FFFFFF",
        "OutlineColour": "&H00000000",
        "Bold": 0,
        "Outline": 2,
        "Shadow": 1,
        "Alignment": 2,
        "MarginV": 40,
    },
}


@dataclass
class Settings:
    asr_backend: str = DEFAULTS["asr_backend"]
    utaudio_url: str = DEFAULTS["utaudio_url"]
    utaudio_key: str = DEFAULTS["utaudio_key"]
    groq_base_url: str = DEFAULTS["groq_base_url"]
    groq_api_key: str = DEFAULTS["groq_api_key"]
    whisper_model: str = DEFAULTS["whisper_model"]
    llm_base_url: str = DEFAULTS["llm_base_url"]
    llm_api_key: str = DEFAULTS["llm_api_key"]
    grammar_model: str = DEFAULTS["grammar_model"]
    visual_model: str = DEFAULTS["visual_model"]
    language: str = DEFAULTS["language"]
    hotwords: list = field(default_factory=list)
    ffmpeg_bin: str = DEFAULTS["ffmpeg_bin"]
    ffprobe_bin: str = DEFAULTS["ffprobe_bin"]
    mock: bool = DEFAULTS["mock"]
    frame_window: float = DEFAULTS["frame_window"]
    frame_count: int = DEFAULTS["frame_count"]
    grammar_chunk: int = DEFAULTS["grammar_chunk"]
    request_timeout: int = DEFAULTS["request_timeout"]
    ass_style: dict = field(default_factory=lambda: dict(DEFAULTS["ass_style"]))

    @classmethod
    def load(cls, path: str | None = None) -> "Settings":
        data: dict[str, Any] = {}
        if path and os.path.exists(path):
            with open(path, "r", encoding="utf-8") as fh:
                data.update(json.load(fh))
        data.update(_env_overrides())
        if "hotwords" in data and isinstance(data["hotwords"], str):
            data["hotwords"] = [h.strip() for h in data["hotwords"].split(",") if h.strip()]
        if "ass_style" not in data:
            data["ass_style"] = dict(DEFAULTS["ass_style"])
        known = set(cls.__dataclass_fields__)  # type: ignore[attr-defined]
        filtered = {k: v for k, v in data.items() if k in known}
        return cls(**filtered)

    def to_dict(self) -> dict:
        return asdict(self)


def _env_overrides() -> dict[str, Any]:
    out: dict[str, Any] = {}
    for key, val in os.environ.items():
        if not key.startswith(ENV_PREFIX):
            continue
        name = key[len(ENV_PREFIX):].lower()
        if name == "hotwords":
            out[name] = [h.strip() for h in val.split(",") if h.strip()]
        elif name == "mock":
            out[name] = val.lower() in ("1", "true", "yes")
        elif name in ("frame_window", "request_timeout"):
            out[name] = float(val) if name == "frame_window" else int(val)
        elif name in ("frame_count", "grammar_chunk"):
            out[name] = int(val)
        else:
            out[name] = val
    return out
