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

_JSON_SEARCH = re.compile(r"\{.*\}", re.DOTALL)


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
            json_mode=True,
        )
        self._apply(raw, transcript)

    def _apply(self, raw: str, transcript: Transcript) -> None:
        try:
            obj = json.loads(_JSON_SEARCH.search(raw).group(0))
            changes = obj.get("changes", [])
        except Exception:
            return
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
