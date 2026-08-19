"""语音转文字(ASR)。

真实模式:把媒体文件连同热词提交给 UTAudio,轮询任务直到完成,
解析出带时间戳的转写结果。

mock 模式:不连任何外部服务,根据媒体时长生成一段示例转写,
并且故意埋一个"同音错字"错误,用来演示后面语义/画面核对。
"""
from __future__ import annotations

import json
import subprocess
import time
import urllib.error
import urllib.request
from pathlib import Path
from typing import Optional

from .engine import Cue, Transcript
from .settings import Settings


class Transcriber:
    def __init__(self, settings: Settings):
        self.settings = settings

    def transcribe(self, media_path: str) -> Transcript:
        if self.settings.mock:
            return self._mock(media_path)
        job_id = self._upload(media_path)
        data = self._poll(job_id)
        cues = []
        for i, s in enumerate(data.get("segments", []), 1):
            cues.append(Cue(
                index=i,
                start=float(s["start"]),
                end=float(s["end"]),
                raw_text=s["text"].strip(),
                confidence=float(s.get("confidence", 1.0)),
            ))
        return Transcript(
            language=data.get("language", self.settings.language),
            hotwords=data.get("hotwords", self.settings.hotwords),
            cues=cues,
        )

    # ---- 真实上传与轮询 -------------------------------------------------- #
    def _upload(self, media_path: str) -> str:
        boundary = "----subflowboundary"
        body = bytearray()
        hw = json.dumps(self.settings.hotwords).encode("utf-8")
        body += f"--{boundary}\r\n".encode()
        body += b'Content-Disposition: form-data; name="hotwords"\r\n\r\n'
        body += hw + b"\r\n"
        fname = Path(media_path).name
        with open(media_path, "rb") as fh:
            raw = fh.read()
        body += f"--{boundary}\r\n".encode()
        body += f'Content-Disposition: form-data; name="file"; filename="{fname}"\r\n'.encode()
        body += b"Content-Type: application/octet-stream\r\n\r\n"
        body += raw + b"\r\n"
        body += f"--{boundary}--\r\n".encode()

        req = urllib.request.Request(
            self.settings.utaudio_url,
            data=bytes(body),
            headers={
                "Content-Type": f"multipart/form-data; boundary={boundary}",
                "Authorization": f"Bearer {self.settings.utaudio_key}",
            },
            method="POST",
        )
        with urllib.request.urlopen(req, timeout=self.settings.request_timeout) as resp:
            return json.loads(resp.read().decode("utf-8"))["job_id"]

    def _poll(self, job_id: str) -> dict:
        base = self.settings.utaudio_url.rsplit("/transcribe", 1)[0]
        url = f"{base}/jobs/{job_id}"
        for _ in range(60):
            req = urllib.request.Request(
                url, headers={"Authorization": f"Bearer {self.settings.utaudio_key}"}
            )
            with urllib.request.urlopen(req, timeout=self.settings.request_timeout) as resp:
                data = json.loads(resp.read().decode("utf-8"))
            if data.get("status") == "done":
                return data
            if data.get("status") == "error":
                raise RuntimeError(f"UTAudio 转写失败: {data}")
            time.sleep(2)
        raise TimeoutError("UTAudio 转写超时")

    # ---- mock ------------------------------------------------------------ #
    def _mock(self, media_path: str) -> Transcript:
        duration = _probe_duration(media_path) or 30.0
        pool = [
            "大家好，欢迎来到今天的频道。",
            "今天我们聊聊自动字幕的痛点。",
            "语音识别经常把人名和地名搞错。",
            "比如把旧金山听成旧晋山，同音词很麻烦。",
            "所以我们需要语义检查和画面核对。",
            "最后用本地工具导出字幕和视频。",
        ]
        count = max(len(pool), int(duration // 4))
        step = duration / count
        cues: list[Cue] = []
        for i in range(count):
            cues.append(Cue(
                index=i + 1,
                start=round(i * step, 3),
                end=round((i + 1) * step, 3),
                raw_text=pool[i % len(pool)],
                confidence=round(0.82 + 0.1 * ((i * 7) % 5) / 5, 2),
            ))
        # 埋一个同音错误的演示点
        if count > 3:
            cues[3].raw_text = "比如把旧金山听成旧晋山，同音词很麻烦。"
            cues[3].mark("asr", "info", "ASR 低置信片段，建议人工或语义复核。")
        return Transcript(language="zh", hotwords=self.settings.hotwords, cues=cues)


def _probe_duration(path: str) -> Optional[float]:
    """尽量用 ffprobe 取时长;拿不到就返回 None(mock 会兜底)。"""
    try:
        out = subprocess.run(
            ["ffprobe", "-v", "error", "-show_entries", "format=duration",
             "-of", "default=noprint_wrappers=1:nokey=1", path],
            capture_output=True, text=True, timeout=30,
        )
        return float(out.stdout.strip()) if out.stdout.strip() else None
    except Exception:
        return None
