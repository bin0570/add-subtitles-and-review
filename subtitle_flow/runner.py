"""总编排:按顺序跑四个环节,每个环节落一份产物,最后写 overall 清单。

设计要点:
  - 每步结果存成 JSON,方便人核查并单独重跑。
  - 原话永不覆盖,任何修正都在 fixed_text 层。
  - mock 模式全程离线可跑,方便先看流程长什么样。
  - 跑完生成报告(report 模块处理)。
"""
from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path

from .engine import Transcript
from .settings import Settings
from .transcriber import Transcriber
from .grammar import GrammarCheck
from .visual import VisualCheck
from .toaster import Burner
from .report import build_report


def run_all(media_path: str, out_dir: str, settings: Settings, use_raw: bool = False) -> dict:
    media = Path(media_path)
    if not media.exists():
        raise FileNotFoundError(media_path)

    out = Path(out_dir)
    out.mkdir(parents=True, exist_ok=True)
    (out / "artifacts").mkdir(exist_ok=True)
    frames_dir = out / "artifacts" / "frames"

    trace: list[dict] = []
    stamp = lambda: datetime.now().strftime("%H:%M:%S")  # noqa: E731

    def save(stage: str, note: str, payload) -> None:
        trace.append({"stage": stage, "time": stamp(), "note": note})
        target = out / "artifacts" / f"{stage}.json"
        with open(target, "w", encoding="utf-8") as fh:
            if hasattr(payload, "to_dict"):
                json.dump(payload.to_dict(), fh, ensure_ascii=False, indent=2)
            else:
                json.dump(payload, fh, ensure_ascii=False, indent=2)

    # 1) 转写 ---------------------------------------------------------------
    transcript: Transcript = Transcriber(settings).transcribe(str(media))
    save("1_asr", f"转写完成: {len(transcript.cues)} 条,热词 {len(transcript.hotwords)}", transcript)

    # 2) 语义校对 -----------------------------------------------------------
    transcript = GrammarCheck(settings).run(transcript)
    save("2_grammar", "语义校对完成,生成修正建议与标记", transcript)

    # 3) 画面核对 -----------------------------------------------------------
    transcript = VisualCheck(settings).run(transcript, str(media), str(frames_dir))
    save("3_visual", "画面核对完成(疑点附近抽帧验证)", transcript)

    # 4) 交付 ---------------------------------------------------------------
    burner = Burner(settings)
    subs = burner.dump_texts(transcript.cues, str(out / "delivery"), use_raw=use_raw)
    mp4 = burner.burn_mp4(str(media), subs["ass"], str(out / "delivery"))
    trace.append({"stage": "4_delivery", "time": stamp(), "note": "交付 SRT/ASS/MP4 完成"})
    with open(out / "artifacts" / "4_delivery.json", "w", encoding="utf-8") as fh:
        json.dump({"subtitles": subs, "mp4": mp4}, fh, ensure_ascii=False, indent=2)

    # overall ---------------------------------------------------------------
    summary = {
        "tool": "add-subtitles-and-review",
        "media": media.name,
        "settings": {k: v for k, v in settings.to_dict().items() if k != "ass_style"},
        "ass_style": settings.ass_style,
        "trace": trace,
        "generated": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
    }
    with open(out / "manifest.json", "w", encoding="utf-8") as fh:
        json.dump(summary, fh, ensure_ascii=False, indent=2)

    report = build_report(str(out), transcript, settings, summary, media.name)

    return {
        "media": media.name,
        "out_dir": str(out),
        "cues": len(transcript.cues),
        "flagged": sum(1 for c in transcript.cues if c.issues),
        "fixed": sum(1 for c in transcript.cues if c.is_fixed),
        "artifacts": {
            "manifest": str(out / "manifest.json"),
            "asr": str(out / "artifacts" / "1_asr.json"),
            "grammar": str(out / "artifacts" / "2_grammar.json"),
            "visual": str(out / "artifacts" / "3_visual.json"),
            "srt": subs["srt"],
            "ass": subs["ass"],
            "srt_original": subs["srt_original"],
            "mp4": mp4,
            "review_md": report["review_md"],
            "review_html": report["review_html"],
        },
    }


def apply_choices(transcript_json: str, choices_json: str, out_dir: str, settings: Settings) -> dict:
    """按导出的人工决定重新生成最终字幕。"""
    with open(transcript_json, "r", encoding="utf-8") as fh:
        data = json.load(fh)
    with open(choices_json, "r", encoding="utf-8") as fh:
        decisions = json.load(fh)
    pick_map = {
        d["index"]: d.get("decision") or d.get("fixed_text") or d.get("raw_text")
        for d in decisions.get("cues", [])
    }

    from .engine import Cue  # noqa: PLC0415

    cues: list[Cue] = []
    for s in data["cues"]:
        cue = Cue.from_dict(s)
        chosen = pick_map.get(cue.index)
        if chosen and chosen != cue.raw_text:
            cue.fixed_text = chosen
        cues.append(cue)

    burner = Burner(settings)
    return burner.dump_texts(cues, str(Path(out_dir) / "delivery_final"), use_raw=False)
