"""烟测:整条流程用 mock 模式跑通(不连外部服务)。"""
from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent


def _run(*args: str):
    import subprocess
    return subprocess.run(
        [sys.executable, "-m", "subtitle_flow.cli", *args],
        cwd=str(ROOT), capture_output=True, text=True,
    )


def test_mock_run(tmp_path):
    media = tmp_path / "sample.mp4"
    media.write_bytes(b"")  # 占位,mock 不真正解码
    out = tmp_path / "out"
    r = _run("run", "--input", str(media), "--output-dir", str(out), "--mock")
    assert r.returncode == 0, r.stderr
    assert (out / "delivery" / "output.srt").exists()
    assert (out / "delivery" / "output.original.srt").exists()
    assert (out / "review.html").exists()
    assert (out / "manifest.json").exists()


def test_export_roundtrip(tmp_path):
    media = tmp_path / "sample.mp4"
    media.write_bytes(b"")
    out = tmp_path / "out"
    r1 = _run("run", "--input", str(media), "--output-dir", str(out), "--mock")
    assert r1.returncode == 0, r1.stderr

    import json
    choices = {
        "cues": [{"index": 4, "decision": "比如把旧金山听成旧金山，同音词很麻烦。"}]
    }
    cpath = tmp_path / "choices.json"
    cpath.write_text(json.dumps(choices, ensure_ascii=False), encoding="utf-8")

    r2 = _run(
        "export",
        "--transcript", str(out / "artifacts" / "3_visual.json"),
        "--choices", str(cpath),
        "--output-dir", str(out),
        "--mock",
    )
    assert r2.returncode == 0, r2.stderr
    assert (out / "delivery_final" / "output.srt").exists()
