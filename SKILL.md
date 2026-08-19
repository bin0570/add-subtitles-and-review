---
name: 给视频加字幕然后复核
author: 薯条 Allen (binbin0570)
description: 一条可复核的字幕处理流程。语音转写 → 语义校对 → 画面核对 → 本地交付 SRT/ASS/MP4。保留原话、交互式复核、整条流程可追溯。自己封装的工具,非调用外部 skill。
read_when:
  - 用户需要给视频/音频生成或校对字幕
  - 用户提到 ASR、字幕校对、SRT、ASS、烧字幕、字幕复核
  - 用户要求"可复核""保留原话""画面核对字幕"
---

# 给视频加字幕然后复核

将「转写 → 校对 → 画面核对 → 交付」串成一条**可被完整复核**的字幕流程。本工具是独立重写封装,不调用任何外部字幕 skill。

## 何时使用
- 给视频/音频做高质量字幕,并需要可追溯、可回退。
- 需要识别同音错字、语义断裂,并用画面佐证。
- 需要一站式交付 SRT / ASS / 带字幕 MP4。

## 流程（四段,每段落盘可复核）
1. **语音转写** `1_asr`: UTAudio 把媒体转成带时间轴+热词的文字(原话只读)。
2. **语义校对** `2_grammar`: qwen3.7-flash 逐段校对,给修正建议与原因(写进固定层,不动原话)。
3. **画面核对** `3_visual`: 对带标记片段在疑点附近抽 3 帧,送 qwen3.7-f-vision 判断画面是否与字幕冲突。
4. **交付** `4_delivery`: 本地 FFmpeg 出 `output.srt`(修正版)/`output.ass`/`output.original.srt`(原话)/`output.mp4`(烧字幕)。

## 关键设计
- **保留原话**: `Cue.raw_text` 只读,修正只在 `Cue.fixed_text`。`output.original.srt` 一键回退。
- **可复核**: `out/artifacts/*.json` + `manifest.json` 记录每段输入/输出/配置; `review.html` 交互面板可切原话/修正、逐条采用或手改、看抽帧与标记、导出决定。
- **离线可演示**: `--mock` 不连外部服务即可跑通全流程并生成复核面板。

## 调用方式(CLI)
```
python -m subtitle_flow.cli run --input 视频.mp4 --output-dir out --mock
python -m subtitle_flow.cli run --input 视频.mp4 --output-dir out --config config.json
python -m subtitle_flow.cli export --transcript out/artifacts/3_visual.json --choices 决定.json --output-dir out
```

## 依赖
- Python 3.11+(无需第三方 Python 包)。
- 真实烧 MP4 需本机 `ffmpeg`/`ffprobe` 并入 PATH。
- 真实转写需 UTAudio(`config.json` 的 `utaudio_url`/`utaudio_key`)。
- 真实校对需 OpenAI 兼容 LLM 网关(默认 `http://127.0.0.1:31415/v1`),含模型 `qwen3.7-flash`、`qwen3.7-f-vision`。
- 没有上述服务也能跑: 加 `--mock`。

完整准备清单与命令见 [USAGE.md](USAGE.md)。
