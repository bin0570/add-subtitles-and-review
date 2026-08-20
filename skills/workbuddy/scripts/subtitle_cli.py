#!/usr/bin/env python3
"""给视频加字幕然后复核 —— skill 入口脚本。

薄封装: 定位本地项目里的 subtitle_flow 包, 调用其 CLI 跑完整流程。
这样核心代码只在项目里维护一份, skill 只是调用入口。
"""
from __future__ import annotations

import argparse
import os
import subprocess
import sys
from datetime import datetime
from pathlib import Path

# 本地项目根路径(核心代码所在地)
PROJECT = Path(r"C:\Users\Allen\WorkBuddy\github make a vedio\add-subtitles-and-review")

# 优先用 WorkBuddy 托管 Python; 否则用系统 python
PYTHON = r"C:\Users\Allen\.workbuddy\binaries\python\versions\3.13.12\python.exe"
if not os.path.exists(PYTHON):
    PYTHON = sys.executable


def find_config() -> str | None:
    """找 config.json(含 key)。不存在返回 None。"""
    candidates = [
        PROJECT / "config.json",
        PROJECT / "config.sample.json",
    ]
    for c in candidates:
        if c.exists():
            return str(c)
    return None


def main() -> int:
    p = argparse.ArgumentParser(prog="add-subtitles-and-review")
    p.add_argument("--input", required=True, help="视频/音频文件路径")
    p.add_argument("--out", default=None, help="输出目录(默认项目下 out_<时间戳>)")
    p.add_argument("--mock", action="store_true", help="离线演示(不连 Groq)")
    args = p.parse_args()

    src = Path(args.input).expanduser().resolve()
    if not src.exists():
        print(f"错误: 找不到输入文件 {src}", file=sys.stderr)
        return 1

    if not PROJECT.exists():
        print(f"错误: 找不到本地项目 {PROJECT}", file=sys.stderr)
        return 1

    config = None if args.mock else find_config()
    if not args.mock and not config:
        print("错误: 找不到 config.json。请把 Groq key 填进项目 config.json,"
              "或用环境变量 SUB_GROQ_API_KEY。", file=sys.stderr)
        return 1

    # 默认输出到输入文件同一目录下的 "_subtitle_out_<时间戳>", 用户在自己文件旁拿成品, 不污染项目仓库。
    out_dir = args.out or str(src.parent / f"_subtitle_out_{datetime.now().strftime('%Y%m%d_%H%M%S')}")

    cmd = [PYTHON, "-m", "subtitle_flow.cli", "run",
           "--input", str(src), "--output-dir", out_dir]
    if args.mock:
        cmd.append("--mock")
    elif config:
        cmd += ["--config", config]

    print(f"[字幕skill] 项目: {PROJECT}")
    print(f"[字幕skill] 媒体: {src}")
    print(f"[字幕skill] 输出: {out_dir}")
    print("[字幕skill] 正在运行: 转写→语义校对→烧字幕... (Groq, 约几十秒)\n")

    env = os.environ.copy()
    gkey = os.environ.get("SUB_GROQ_API_KEY")
    if gkey:
        env["SUB_GROQ_API_KEY"] = gkey

    result = subprocess.run(cmd, cwd=str(PROJECT), env=env)
    return result.returncode


if __name__ == "__main__":
    sys.exit(main())
