# 使用说明（USAGE）

讲两件事：**用之前要准备什么** + **怎么用**。读完就能跑。

---

## 一、用之前要准备的事（清单）

| # | 要准备的东西 | 必须？ | 说明 |
|---|--------------|--------|------|
| 1 | Python 3.11+ | ✅ 必须 | 代码运行环境。无需任何第三方 Python 包（HTTP 用标准库）。 |
| 2 | ffmpeg + ffprobe | 真实烧 MP4 才要 | 装好并加入系统 PATH。只想看 SRT/ASS 和复核面板可跳过。 |
| 3 | UTAudio ASR 服务 | 真实转写才要 | 语音→文字 API。地址 + key 填进 `config.json` 的 `utaudio_url` / `utaudio_key`。 |
| 4 | OpenAI 兼容 LLM 网关 | 真实校对才要 | 默认指向本机 `http://127.0.0.1:31415/v1`（FreeLLMAPI/CC Switch/Ollama 等）。网关里要有 `qwen3.7-flash`（语义）、`qwen3.7-f-vision`（画面）。 |
| 5 | hotwords（热词） | 可选 | 在 `config.json` 填视频里的专有名词（人名/地名/品牌），能大幅降低 ASR 误识。 |

> **没有 3、4 也能先试**：加 `--mock`，全流程离线跑通，纯看效果、不连任何外部服务。

---

## 二、怎么跑（三条命令）

先切到项目根目录：
```bash
cd add-subtitles-and-review
```

### 1）先试这个（零依赖，推荐第一步）
```bash
python -m subtitle_flow.cli run --input 你的视频.mp4 --output-dir out --mock
```
跑完在 `out/` 下生成字幕和 `review.html`。

### 2）接真实服务跑
先改 `config.json`（填 UTAudio 地址/key、LLM 网关、hotwords），然后：
```bash
python -m subtitle_flow.cli run --input 你的视频.mp4 --output-dir out --config config.json
```

### 3）复核完，按你的决定重新生成最终字幕
在 `review.html` 逐条决定后，点「导出决定(JSON)」得 `subtitle_choices.json`，再跑：
```bash
python -m subtitle_flow.cli export \
    --transcript out/artifacts/3_visual.json \
    --choices subtitle_choices.json --output-dir out
```

---

## 三、复核面板 `review.html` 怎么用

用浏览器打开 `out/review.html`（双击即可）。这是整个流程的"控制台"：

- **原话 / 修正** 顶部切换：看转写原话，还是看修正后的。
- **每条**三个按钮：
  - `保留原话`：这一条退回机器原话（不改）
  - `采用修正`：采用模型建议的修正
  - `手动改`：自己手改这一条
- **标记徽章**：语义/画面打的点，带理由（同音错、画面冲突等）。
- **画面帧**：被标记片段会在疑点附近抽几张图，直接看画面佐证。
- **导出决定(JSON)**：把你所有决定导出来，交给 `export` 命令重新生成。

> 原始转写文本**永远保留**，随时可回退，改不坏。

---

## 四、输出文件都是啥

运行后 `out/` 目录：
```
out/
  manifest.json          # 全流程时间线 + 配置快照（复核入口）
  artifacts/
    1_asr.json           # 转写原话（时间轴/置信度/热词）
    2_grammar.json       # 语义校对标记与修正建议
    3_visual.json        # 画面核对结论 + 抽帧路径
    4_delivery.json      # 交付物路径
    frames/              # 疑点附近抽出的画面帧
  delivery/
    output.srt           # 推荐（修正）
    output.ass
    output.original.srt  # 原话回溯
    output.mp4           # 烧字幕视频（真实模式才有）
  REVIEW.md              # 人读的复核报告
  review.html            # 交互式复核面板
```

---

## 五、常见问题

- **`--mock` 是啥？** 离线模拟。转写/语义/画面都用内置假数据，只为让你看流程长啥样、面板怎么用。不产生真实字幕。
- **没装 ffmpeg 会怎样？** 真实运行还能出 SRT/ASS 和复核面板；只有 `output.mp4` 烧字幕那步会报错。装好 ffmpeg 再跑即可。
- **怎么换模型 / 换网关？** 改 `config.json` 的 `llm_base_url`、`grammar_model`、`visual_model`、`utaudio_url` 等；也可用环境变量 `SUB_` 前缀覆盖（如 `SUB_LLM_BASE_URL=...`）。
- **想回退到原话？** 交付目录里有 `output.original.srt`；或用 `--original` 重新跑交付。
- **怎么只交付原话不要修改？** 跑的时候加 `--original`。
