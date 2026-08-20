---
name: add-subtitles-and-review
description: Add high-quality, reviewable subtitles to a video or audio file. Transcribes speech, proofreads it (fixes homophone errors and adds punctuation), and outputs SRT/ASS/burned-in-subtitle MP4 plus a reviewable HTML panel. Use whenever the user asks to add subtitles, burn subtitles, make subtitles, create SRT/ASS, transcribe a video into subtitles, or review/correct a subtitle. Powered by a local subtitle_flow package plus the Groq free API.
---

# 给视频加字幕然后复核

给视频/音频生成可复核字幕：**语音转写 → 语义校对(纠同音错字/补标点) → 画面核对 → 本地交付 SRT/ASS/带字幕MP4/复核面板**。

## 何时用
用户拿视频/音频来要"加字幕""出字幕""做中文字幕""烧字幕""审字幕"。

## 怎么调用(最重要)
用一个集中的入口脚本一键跑完，无需手动拼命令：

```bash
python "C:/Users/Allen/.workbuddy/skills/add-subtitles-and-review/scripts/subtitle_cli.py" run --input "<用户视频或音频的绝对路径>"
```

- `--input 路径`：视频(mp4/mov/mkv...)或音频(mp3/wav/m4a...)，**必填**，用用户给的真实路径。
- `--out 目录`：可选，默认项目下 `out_<时间戳>`。
- `--mock`：离线演示，不连 Groq。

脚本会自动：定位本地项目 → 用项目 `config.json` 里的 Groq key → 跑完整流程 → 打印产物路径（SRT/ASS/MP4/复核面板）。

## 产物位置
跑完会在输出目录的 `delivery/` 下生成：
- `output.mp4`（已烧字幕的视频）
- `output.srt`（推荐字幕）
- `output.ass`、`output.original.srt`（原话回溯）
- `REVIEW.md` + `review.html`（复核面板）

## 依赖
- 本地项目：`C:\Users\Allen\WorkBuddy\github make a vedio\add-subtitles-and-review\subtitle_flow`
- Groq 免费 API key（在项目 `config.json`）
- 本机有 ffmpeg

## 注意
- 视频容器会先自动抽音频再转写；字幕字号按分辨率自适应，竖屏/横屏/4K 都不出屏。
- 若脚本报"找不到 config.json / key"，请用户把 Groq key 填进项目 `config.json`。
