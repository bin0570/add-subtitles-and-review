# 给视频加字幕然后复核

> 仓库地址：https://github.com/bin0570/add-subtitles-and-review （slug 为 `add-subtitles-and-review`，显示名为中文）

> **作者：薯条 Allen（[@bin0570](https://github.com/bin0570)）· 个人封装、独立重写的字幕工具 · MIT License**

📖 **完整使用说明（准备清单 + 命令 + 复核面板用法）见 [USAGE.md](USAGE.md)。**

一条**可复核、可回退**的字幕处理流程。把"自动字幕"从黑盒变成白盒：
每一步的结果、每一处修改的理由，都看得见、改得了、退得回。

```
视频/音频
   │
   ├─ ① 语音转写 (UTAudio ASR) ─────► 带时间轴 + 热词的文字
   │
   ├─ ② 语义校对 (qwen3.7-flash) ───► 错字 / 语句断裂 / 标点标记 + 修正建议
   │
   ├─ ③ 画面核对 (qwen3.7-f-vision) ─► 疑点附近抽 3 帧，核对画面与字幕是否一致
   │
   └─ ④ 本地交付 (FFmpeg) ──────────► SRT / ASS / 带字幕 MP4
```

---

## 一、字幕痛点与需求起源

### 痛点
1. **ASR 误识同音词**：人名、地名、品牌、术语（"旧金山"↔"旧晋山"）一错就闹笑话。
2. **长音频语义断裂**：分段转写丢失上下文，句子被切散。
3. **字幕与画面打架**：画面已有标题/路牌/PPT 文字，字幕却写错或重复——只看声音发现不了。
4. **改了不知道为什么改**：多数工具直接覆盖原话，出错了无法追溯、无法回退。
5. **交付格式割裂**：SRT、ASS、带字幕 MP4 要分别用不同工具来回倒腾。
6. **隐私与可控性**：把视频丢给第三方在线字幕服务，素材外泄风险高。

### 需求起源
视频创作者 / 内容团队需要**高质量且可信**的字幕，但现有方案把「转写—校对—核对—交付」切成互不相通的几段。本工具把它们串成一条**可被人类全程复核**的流程：

- **转写给时间轴**，解决"在哪"。
- **语义校对查逻辑与错字**，解决"字对不对"。
- **画面核对查画面一致性**，补足"声音看不到的画面信息"。
- **本地交付**，解决"隐私 + 一站式格式"。
- 关键原则：**原话永不被覆盖**，所有修改都是叠加层，可追溯、可回退。

---

## 二、保留原话功能

- 转写结果进入 `Cue.raw_text`，**只读、绝不修改**。
- 语义/画面的修改进入独立的 `Cue.fixed_text` 叠加层。
- 切换显示层即可选择交付「原话」或「修正」：
  - CLI：`--original` 强制交付原话。
  - 交付目录同时产出 `output.srt`（修正/推荐）、`output.original.srt`（原话回溯）。
  - 复核面板顶部「原话 / 修正」一键切换。

---

## 三、改果预览与交互功能

`review.html` 是交互式复核面板（浏览器直接打开）：

- **原话 / 修正** 全局切换，逐条并排对比。
- 每条可 **保留原话 / 采用修正 / 手动改** 三种操作。
- 标记（语义、画面）以彩色徽章展示，附理由。
- **疑点片段展示抽出的画面帧** + 画面核对结论（一致 / 冲突 / 未核对）。
- **导出决定(JSON)**：把你的决定导出，再用 CLI `export` 重新生成最终字幕，无需重复跑模型。

---

## 四、支持查看与复核整条流程

每次运行都会在 `out/artifacts/` 落盘每阶段产物 + `manifest.json`：

```
out/
  manifest.json            # 全流程时间线 + 配置快照（复核入口）
  artifacts/
    1_asr.json             # 转写原话（时间轴、置信度、热词）
    2_grammar.json         # 语义校对标记与修正建议
    3_visual.json          # 画面核对结论 + 抽帧路径
    4_delivery.json        # 交付物路径
    frames/                # 疑点附近抽取的帧
  delivery/
    output.srt             # 推荐（修正）
    output.ass
    output.original.srt    # 原话回溯
    output.mp4             # 烧字幕视频（真实模式）
  REVIEW.md                # 人类可读复核报告
  review.html              # 交互式复核面板
```

打开 `review.html` 即可从头到尾查看：流程走到哪、每处修改为何改、画面是否佐证。

---

## 五、快速开始

```bash
# 1) 离线演示（无需任何外部服务）
python -m subtitle_flow.cli run --input sample.mp4 --output-dir out --mock

# 2) 真实运行（指向你的服务）
python -m subtitle_flow.cli run --input video.mp4 --output-dir out --config config.json

# 3) 按复核面板导出的决定重新生成字幕
python -m subtitle_flow.cli export \
    --transcript out/artifacts/3_visual.json \
    --choices subtitle_choices.json --output-dir out
```

### 配置（config.json 或环境变量 `SUB_` 前缀）
| 字段 | 说明 | 默认 |
|------|------|------|
| `utaudio_url` / `utaudio_key` | UTAudio ASR 端点与密钥 | — |
| `llm_base_url` | OpenAI 兼容网关 | `http://127.0.0.1:31415/v1` |
| `llm_api_key` | 网关密钥 | `sk-local` |
| `grammar_model` | 语义校对模型 | `qwen3.7-flash` |
| `visual_model` | 画面核对模型 | `qwen3.7-f-vision` |
| `hotwords` | 热词列表，提升 ASR 准确率 | `[]` |
| `ffmpeg_bin` / `ffprobe_bin` | 本地二进制 | `ffmpeg` / `ffprobe` |
| `mock` | 离线模拟 | `false` |

---

## 六、依赖
- Python 3.11+
- 本地已安装 `ffmpeg` / `ffprobe`（真实交付阶段需要；mock 模式不需要）
- 无需第三方 Python 包（HTTP 用标准库实现）
