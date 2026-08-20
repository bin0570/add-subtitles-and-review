---
name: 给视频加字幕然后复核
author: 薯条 Allen (binbin0570)
description: 给视频/音频自动生成高质量字幕并复核。语音转写 → 语义校对(纠同音错字/补标点) → 画面核对 → 本地交付 SRT/ASS/带字幕MP4/复核面板。用户说"给视频加字幕"、"字幕"、"SRT"、"烧字幕"、"加字幕复核"时使用。核心代码在本地项目 add-subtitles-and-review（subtitle_flow 包），本 skill 用 Groq 免费 API 驱动。
read_when:
  - 用户需要给视频/音频生成、校对或添加字幕
  - 用户提到 字幕、SRT、ASS、烧字幕、加字幕、ASR、语音转文字、字幕复核
  - 用户给了视频/音频文件路径想加字幕
---

# 给视频加字幕然后复核

一条可复核的字幕流程：**语音转写 → 语义校对 → 画面核对 → 本地交付**。核心代码在你的本地项目里（`subtitle_flow` 包），用 **Groq 免费 API** 驱动，无需下载模型、不花钱、无额度压力。

## 何时使用
- 用户拿视频/音频来，要"加字幕""出字幕""做中文字幕""审字幕"。
- 需要自动纠同音错字（如品牌名、地名被 ASR 听错）+ 补标点。
- 需要产出 SRT / ASS / 带字幕的 MP4 / 可复核的面板。

## 核心路径（写死在脚本里，别改）
- 项目代码：`C:\Users\Allen\WorkBuddy\github make a vedio\add-subtitles-and-review\`
- 配置：项目下 `config.json`（含 Groq key，Git 已忽略、不公开）
- 本 skill 脚本：`scripts\subtitle_cli.py`

## 用法（交给技能脚本，一行搞定）
```bash
python "C:\Users\Allen\.workbuddy\skills\add-subtitles-and-review\scripts\subtitle_cli.py" run --input "视频或音频路径" [--out 输出目录]
```
脚本会自动：定位项目、用 config.json 的 key、调 subtitle_flow 全流程、打印产物路径（SRT/ASS/MP4/复核面板）。

参数：
- `--input 路径`：视频（mp4/mov/mkv...）或音频（mp3/wav/m4a...），必填。
- `--out 目录`：输出目录，默认项目下 `out_<时间戳>`（避免污染仓库）。
- `--mock`：离线演示，不连 Groq、不需 key。

## 复核面板
跑完提示里会给 `review.html` 路径，用浏览器打开即可：逐条看「原话/修正」、标记、抽帧，可导出决定再重新生成最终字幕。

## 注意
- 若提示找不到 key，让用户把 Groq key 填进项目 `config.json`（或脚本里 `SUB_GROQ_API_KEY` 环境变量）。
- 视频容器会自动抽音频转写；字幕字号按分辨率自适应，竖屏/横屏/4K 都不出屏。
