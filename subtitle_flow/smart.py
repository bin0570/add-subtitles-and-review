"""一个极简的、OpenAI 兼容格式的大模型 HTTP 客户端。

只用标准库,不依赖第三方包。用来:
  - 语义校对(文本 -> JSON)
  - 画面核对(文本 + base64 图片 -> JSON)

把 llm_base_url 指向任意 OpenAI 兼容网关(FreeLLMAPI / CC Switch / Ollama...)。
"""
from __future__ import annotations

import base64
import json
import urllib.error
import urllib.request
from pathlib import Path

from .settings import Settings


class SmartClient:
    def __init__(self, settings: Settings):
        self.settings = settings
        self.endpoint = settings.llm_base_url.rstrip("/") + "/chat/completions"

    def chat(self, messages: list[dict], model: str, temperature: float = 0.2,
             json_mode: bool = False, images: list[str] | None = None) -> str:
        payload: dict = {
            "model": model,
            "messages": self._with_images(messages, images),
            "temperature": temperature,
        }
        if json_mode:
            payload["response_format"] = {"type": "json_object"}
        req = urllib.request.Request(
            self.endpoint,
            data=json.dumps(payload).encode("utf-8"),
            headers={
                "Content-Type": "application/json",
                "Authorization": f"Bearer {self.settings.llm_api_key}",
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0 Safari/537.36",
            },
            method="POST",
        )
        try:
            with urllib.request.urlopen(req, timeout=self.settings.request_timeout) as resp:
                data = json.loads(resp.read().decode("utf-8"))
            return data["choices"][0]["message"]["content"]
        except urllib.error.HTTPError as e:
            body = e.read().decode("utf-8", "ignore")
            raise RuntimeError(f"大模型请求失败 HTTP {e.code}: {body[:500]}") from e

    @staticmethod
    def _with_images(messages: list[dict], images: list[str] | None) -> list[dict]:
        if not images:
            return messages
        out = [dict(m) for m in messages]
        last = out[-1]
        content = [{"type": "text", "text": last["content"]}]
        for img in images:
            content.append({"type": "image_url", "image_url": {"url": img}})
        last["content"] = content
        return out

    @staticmethod
    def data_uri(path: str) -> str:
        """把图片文件转成 base64 data URI,方便发给视觉模型。"""
        p = Path(path)
        mime = {
            ".jpg": "image/jpeg", ".jpeg": "image/jpeg",
            ".png": "image/png", ".webp": "image/webp",
        }.get(p.suffix.lower(), "image/jpeg")
        encoded = base64.b64encode(p.read_bytes()).decode("ascii")
        return f"data:{mime};base64,{encoded}"
