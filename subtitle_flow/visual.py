"""画面核对环节。

对每个带标记的片段,在时间中点附近抽几张帧(用 FFmpeg),
再把"画面 + 字幕文字"一起交给视觉模型,判断画面是否与字幕一致。
能抓住"语义看着对、但画面上路牌/幻灯片明明写的是另一个词"的情况。
"""
from __future__ import annotations

import base64
import json
import re
import subprocess
from pathlib import Path

from .engine import Cue, Transcript
from .settings import Settings
from .smart import SmartClient

_SYSTEM_PROMPT = (
    "你是视频字幕核对员。我会给你按时间顺序的几张视频帧,以及对应的配音/字幕文字。\n"
    "请判断画面内容(尤其画面自带的文字:标题、PPT、路牌、人名条)是否与字幕一致。\n"
    "只回答 JSON: {\"consistent\": bool, \"confidence\": 0-1, \"note\": str}。\n"
    "如果画面出现与字幕冲突的文字,务必指出。"
)

_USER_TEMPLATE = '字幕/配音文字: "{text}"\n请核对以上画面帧与这段文字是否一致,并返回 JSON。'

_JSON_SEARCH = re.compile(r"\{.*\}", re.DOTALL)

_PLACEHOLDER_PNG = (
    "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mNk+M8A"
    "AAMBAQDJ/pLvAAAAAElFTkSuQmCC"
)


class VisualCheck:
    def __init__(self, settings: Settings):
        self.settings = settings
        self.client = SmartClient(settings)

    def run(self, transcript: Transcript, media_path: str, frame_dir: str) -> Transcript:
        Path(frame_dir).mkdir(parents=True, exist_ok=True)
        # 当 LLM 后端指向 Groq 时, 已知无适用的开源视觉模型, 温和跳过画面核对,
        # 只抽帧供人工查看, 不因缺视觉 key 阻塞整条流程。
        backends_to_skip = ("api.groq.com",)
        skip_visual = any(h in (self.settings.llm_base_url or "").lower() for h in backends_to_skip)
        targets = [c for c in transcript.cues if c.has_issues]
        for cue in targets:
            frames = self._grab(cue, media_path, frame_dir)
            cue.frames = frames
            if self.settings.mock:
                self._mock(cue)
                continue
            if skip_visual:
                cue.mark("visual", "info", "画面核对跳过:当前后端(groq)暂无适用视觉模型,请人工查看抽帧。")
                continue
            self._inspect(cue, frames)
        return transcript

    # ---- 抽帧 ------------------------------------------------------------ #
    def _grab(self, cue: Cue, media_path: str, frame_dir: str) -> list[str]:
        mid = (cue.start + cue.end) / 2.0
        n = self.settings.frame_count
        offsets = [0.0] if n <= 1 else [
            round(-self.settings.frame_window
                  + 2 * self.settings.frame_window * i / (n - 1), 3)
            for i in range(n)
        ]
        out_frames: list[str] = []
        for j, off in enumerate(offsets, 1):
            when = max(0.0, mid + off)
            out = str(Path(frame_dir) / f"cue{cue.index:03d}_shot{j}.jpg")
            if self.settings.mock:
                _write_placeholder(out)
                out_frames.append(out)
                continue
            try:
                subprocess.run(
                    [self.settings.ffmpeg_bin, "-y", "-ss", f"{when:.3f}", "-i", media_path,
                     "-frames:v", "1", "-q:v", "2", out],
                    capture_output=True, timeout=30,
                )
                if Path(out).exists():
                    out_frames.append(out)
            except Exception:
                continue
        return out_frames

    # ---- 真实调用 -------------------------------------------------------- #
    def _inspect(self, cue: Cue, frames: list[str]) -> None:
        if not frames:
            return
        images = [self.client.data_uri(f) for f in frames]
        raw = self.client.chat(
            [{"role": "system", "content": _SYSTEM_PROMPT},
             {"role": "user", "content": _USER_TEMPLATE.format(text=cue.pick)}],
            model=self.settings.visual_model,
            temperature=0.0,
            images=images,
        )
        try:
            obj = json.loads(_JSON_SEARCH.search(raw).group(0))
            cue.visual_ok = bool(obj.get("consistent"))
            cue.visual_note = obj.get("note", "")
            level = "info" if cue.visual_ok else "error"
            tail = f" {cue.visual_note}" if cue.visual_note else ""
            cue.mark("visual", level,
                     "画面核对:一致。" if cue.visual_ok else "画面核对:与字幕冲突。", )
            if tail:
                cue.mark("visual", level, tail)
        except Exception:
            cue.visual_ok = None
            cue.visual_note = raw[:200]
            cue.mark("visual", "warn", "画面核对该段返回无法解析,请人工查看。")

    # ---- mock ------------------------------------------------------------ #
    def _mock(self, cue: Cue) -> None:
        if "旧金山" in cue.pick:
            cue.visual_ok = True
            cue.visual_note = "画面路牌显示「旧金山」,与修正后字幕一致。"
            cue.mark("visual", "info", "画面核对:一致。路牌显示旧金山。")
        else:
            cue.visual_ok = None
            cue.mark("visual", "info", "画面未见明显冲突文字。")


def _write_placeholder(path: str) -> None:
    """写一张 1x1 PNG,让 mock 模式下复核面板也有帧可显示。"""
    with open(path, "wb") as fh:
        fh.write(base64.b64decode(_PLACEHOLDER_PNG))
