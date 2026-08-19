# 示例运行

## 1) 离线演示(无需任何外部服务)
```bash
cd add-subtitles-and-review
python -m subtitle_flow.cli run --input examples/sample.mp4 --output-dir out --mock
```
运行后打开 `out/review.html` 查看交互式复核面板。

## 2) 真实运行
```bash
python -m subtitle_flow.cli run --input 视频.mp4 --output-dir out --config config.json
```

## 3) 按复核决定重新生成
在 `out/review.html` 点「导出决定(JSON)」得到 `subtitle_choices.json`,然后:
```bash
python -m subtitle_flow.cli export \
    --transcript out/artifacts/3_visual.json \
    --choices subtitle_choices.json --output-dir out
```

产物结构与完整说明见 [USAGE.md](../USAGE.md)。
