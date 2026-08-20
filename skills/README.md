# 字幕 skill · 两套版本（WorkBuddy + Codex）

本目录放「给视频加字幕然后复核」skill 的两个版本，供备份与在其它机器/环境安装。

## 说明
两套脚本逻辑相同（都是调本地 `subtitle_flow` 包 + Groq 免费 API），只是 **SKILL.md 的格式针对各自宿主** 编写：
- `workbuddy/` → 装到 WorkBuddy 技能库
- `codex/` → 装到 Codex skill 目录

> ⚠️ 入口脚本里的 `PROJECT` 指向本机绝对路径（`C:\Users\Allen\WorkBuddy\github make a vedio\add-subtitles-and-review`）。换机器后请改成你自己的项目路径，并确认 `config.json` 里填了 Groq key。

## 安装

### WorkBuddy 版
把 `workbuddy/` 整个目录复制到：
```
C:\Users\Allen\.workbuddy\skills\add-subtitles-and-review\
```

### Codex 版
把 `codex/` 整个目录复制到：
```
C:\Users\Allen\.codex\skills\add-subtitles-and-review\
```
（可选：在 `C:\Users\Allen\.codex\AGENTS.md` 里加一段“给视频加字幕 → 调该 skill 脚本”的指引，方便 Codex 自然语言触发。）

## 一键用法（两版通用）
```bash
python "<skill目录>/scripts/subtitle_cli.py" run --input "视频或音频绝对路径"
```
产物自动生成在输入文件旁的 `_subtitle_out_<时间戳>/delivery/`（output.mp4 / output.srt / output.ass / review.html）。
