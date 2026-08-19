"""语义校对环节。

让语义模型通读转写结果,挑出同音错、语序断裂、标点缺失等问题,
每条给出"改后文本+原因",写进 fixed_text 层,不碰原话。
"""
from __future__ import annotations

import json
import re
from typing import Iterator

from .engine import Cue, Transcript
from .settings import Settings
from .smart import SmartClient

_SYSTEM_PROMPT = (
    "你是严谨的中文字幕校对员。对给定的带时间轴字幕片段,检查:\n"
    "1) 同音/近音错别字(人名、地名、品牌、术语等);\n"
    "2) 语义不通或语序断裂;\n"
    "3) 明显多字/漏字;\n"
    "4) 缺少必要标点。\n"
    "只修确有把握的错,不要改写风格,不要删减信息。\n"
    "必须返回 JSON: {\"changes\": [{\"idx\": 帧序号, \"fixed\": 修正后文本或null, "
    "\"level\": \"info|warn|error\", \"why\": 原因}]}。\n"
    "idx 与输入一致;没问题的片段不要列出。"
)

_USER_TEMPLATE = (
    "以下是自动语音识别(ASR)的字幕片段,热词={hotwords}。\n"
    "请逐条校对并返回 JSON。\n\n{chunk}"
)

_THINK_RE = re.compile(r"<think>.*?</think>", re.DOTALL)
_JSON_BLOCK_RE = re.compile(r"```(?:json)?\s*(\{.*?\})\s*```", re.DOTALL)


def _extract_changes_json(raw: str) -> dict | None:
    """从模型输出里可靠地抽出 changes JSON。

    qwen3.6 常带 <think>...</think> 思考块, 且可能把 JSON 包在 ```json ``` 里。
    处理顺序: 剥思考块 -> 优先取代码块里的 JSON -> 否则从含 changes 的最外层 {..} 解析。
    """
    cleaned = _THINK_RE.sub("", raw)
    # 1) 命中 ```json {...} ``` 代码块
    m = _JSON_BLOCK_RE.search(cleaned)
    if m:
        try:
            return json.loads(m.group(1))
        except Exception:
            pass
    # 2) 找从 {"changes" 开始的完整 JSON
    start = cleaned.find('{"changes"')
    if start == -1:
        start = cleaned.find('{\n  "changes"')
    if start != -1:
        end = start
        depth = 0
        for i in range(start, len(cleaned)):
            ch = cleaned[i]
            if ch == "{":
                depth += 1
            elif ch == "}":
                depth -= 1
                if depth == 0:
                    end = i + 1
                    break
        if end > start:
            try:
                return json.loads(cleaned[start:end])
            except Exception:
                pass
    # 3) 最后兜底
    m = re.search(r"\{.*\}", cleaned, re.DOTALL)
    if m:
        try:
            return json.loads(m.group(0))
        except Exception:
            return None
    return None


def _as_chunks(items: list, size: int) -> Iterator[list]:
    for i in range(0, len(items), size):
        yield items[i:i + size]


class GrammarCheck:
    def __init__(self, settings: Settings):
        self.settings = settings
        self.client = SmartClient(settings)

    def run(self, transcript: Transcript) -> Transcript:
        if self.settings.mock:
            return self._mock(transcript)
        size = max(1, self.settings.grammar_chunk)
        for chunk in _as_chunks(transcript.cues, size):
            self._check_chunk(transcript, chunk)
        return transcript

    def _check_chunk(self, transcript: Transcript, chunk: list[Cue]) -> None:
        lines = [f"[{c.index}] ({c.start:.1f}-{c.end:.1f}s) {c.raw_text}" for c in chunk]
        user = _USER_TEMPLATE.format(
            hotwords=",".join(transcript.hotwords) or "无",
            chunk="\n".join(lines),
        )
        raw = self.client.chat(
            [{"role": "system", "content": _SYSTEM_PROMPT},
             {"role": "user", "content": user}],
            model=self.settings.grammar_model,
            temperature=0.1,
            json_mode=False,  # Groq 的 qwen 对长提示的强制 JSON 校验不稳, 改靠正则提取
        )
        self._apply(raw, transcript)

    def _apply(self, raw: str, transcript: Transcript) -> None:
        obj = _extract_changes_json(raw)
        if not obj:
            return
        changes = obj.get("changes", [])
        by_idx = {c.index: c for c in transcript.cues}
        for ch in changes:
            cue = by_idx.get(ch.get("idx"))
            if not cue:
                continue
            fixed = ch.get("fixed")
            if fixed and fixed != cue.raw_text:
                cue.fixed_text = fixed
                cue.mark("grammar", ch.get("level", "warn"), ch.get("why", "语义校对建议修改。"), fixed)
            else:
                cue.mark("grammar", ch.get("level", "info"), ch.get("why", "语义复核通过。"))

    def _mock(self, transcript: Transcript) -> Transcript:
        for cue in transcript.cues:
            if "旧晋山" in cue.raw_text:
                cue.fixed_text = cue.raw_text.replace("旧晋山", "旧金山")
                cue.mark("grammar", "error", "同音错字:「旧晋山」应为「旧金山」(热词)。", cue.fixed_text)
            elif cue.confidence < 0.85:
                cue.mark("grammar", "info", "置信度偏低,已通读无明显错误。")
        return transcript
