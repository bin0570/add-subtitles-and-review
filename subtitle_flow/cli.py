"""命令行入口。

用法:
  python -m subtitle_flow.cli run   --input 视频.mp4 --output-dir out [--mock] [--config config.json] [--original]
  python -m subtitle_flow.cli export --transcript out/artifacts/3_visual.json --choices choices.json --output-dir out
"""
from __future__ import annotations

import argparse
import json
import sys

from .settings import Settings
from .runner import run_all, apply_choices


def _print_summary(s: dict) -> None:
    print("\n=== 字幕处理完成 ===")
    print(f"媒体:{s['media']}")
    print(f"条数:{s['cues']} · 标记:{s['flagged']} · 修正:{s['fixed']}")
    print("产出:")
    for k, v in s["artifacts"].items():
        print(f"  - {k:14s}: {v}")
    print("\n复核整条流程: 用浏览器打开", s["artifacts"]["review_html"])
    print("回退原话: delivery/output.original.srt")


def cmd_run(args) -> int:
    settings = Settings.load(args.config)
    if args.mock:
        settings.mock = True
    summary = run_all(args.input, args.output_dir, settings, use_raw=args.original)
    _print_summary(summary)
    return 0


def cmd_export(args) -> int:
    settings = Settings.load(args.config)
    if args.mock:
        settings.mock = True
    subs = apply_choices(args.transcript, args.choices, args.output_dir, settings)
    print("已按复核决定重新生成:")
    for k, v in subs.items():
        print(f"  - {k}: {v}")
    return 0


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog="subtitle-flow",
        description="给视频添加字幕,并复核后修改 (可复核字幕处理流程)",
    )
    sub = p.add_subparsers(dest="cmd", required=True)

    r = sub.add_parser("run", help="跑完整流程")
    r.add_argument("--input", required=True, help="视频/音频文件")
    r.add_argument("--output-dir", default="out", help="产物目录")
    r.add_argument("--config", default=None, help="config.json 路径")
    r.add_argument("--mock", action="store_true", help="离线演示模式")
    r.add_argument("--original", action="store_true", help="只按原话交付")

    e = sub.add_parser("export", help="按复核决定重新生成")
    e.add_argument("--transcript", required=True, help="转写 JSON(如 3_visual.json)")
    e.add_argument("--choices", required=True, help="复查导出的决定 JSON")
    e.add_argument("--output-dir", default="out")
    e.add_argument("--config", default=None)
    e.add_argument("--mock", action="store_true")
    return p


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    return cmd_run(args) if args.cmd == "run" else cmd_export(args)


if __name__ == "__main__":
    sys.exit(main())
