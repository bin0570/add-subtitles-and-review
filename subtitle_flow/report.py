"""生成人看的复核报告:一个 Markdown,一个交互式 HTML。

两者都让整条流程可复核:
  - 每步决定都列出来
  - 原话 vs 修正并排
  - 画面帧可见
  - 每条修正可在页面上采用/保留,并能导出决定 JSON
"""
from __future__ import annotations

import html as htmlmod
import json
from datetime import datetime
from pathlib import Path

from .engine import Cue, Transcript
from .settings import Settings

LEVEL_LABEL = {"info": "提示", "warn": "警告", "error": "错误"}


def build_report(out_dir: str, transcript: Transcript, settings: Settings,
                 summary: dict, media_name: str) -> dict[str, str]:
    out = Path(out_dir)
    out.mkdir(parents=True, exist_ok=True)

    md = _markdown(transcript, summary, media_name)
    md_path = str(out / "REVIEW.md")
    md_path = Path(md_path)
    md_path.write_text(md, encoding="utf-8")

    html_path = str(out / "review.html")
    _write_html(html_path, transcript, settings, summary, media_name)
    return {"review_md": str(md_path), "review_html": html_path}


def _markdown(transcript: Transcript, summary: dict, media_name: str) -> str:
    L: list[str] = []
    L.append(f"# 字幕复核报告 · {htmlmod.escape(media_name)}")
    L.append("")
    L.append(f"生成时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}  ")
    L.append(f"语言: {transcript.language} · 条数: {len(transcript.cues)} · 热词: {','.join(transcript.hotwords) or '无'}")
    L.append("")
    L.append("## 流程时间线(可复核)")
    L.append("")
    for step in summary.get("trace", []):
        L.append(f"- **{step['stage']}** `{step['time']}` — {step['note']}")
    L.append("")
    L.append("## 逐条复核")
    L.append("")
    L.append("| # | 时间 | 原话 | 修正 | 标记 | 画面 |")
    L.append("|---|------|------|------|------|------|")
    for c in transcript.cues:
        flags = "; ".join(f"[{LEVEL_LABEL.get(i.level, i.level)}]{i.reason}" for i in c.issues)
        vis = ("一致" if c.visual_ok else ("冲突" if c.visual_ok is False else "未核对"))
        L.append(
            f"| {c.index} | {c.start:.1f}-{c.end:.1f}s | {c.raw_text} "
            f"| {c.fixed_text or '—'} | {flags or '—'} | {vis} |"
        )
    L.append("")
    L.append("## 修正汇总")
    L.append("")
    changed = [c for c in transcript.cues if c.is_fixed]
    if changed:
        for c in changed:
            L.append(f"- #{c.index}: `{c.raw_text}` → `{c.fixed_text}`")
    else:
        L.append("- 无自动修正建议。")
    return "\n".join(L)


def _write_html(path: str, transcript: Transcript, settings: Settings,
                summary: dict, media_name: str) -> None:
    data = {
        "media": media_name,
        "generated": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "language": transcript.language,
        "hotwords": transcript.hotwords,
        "summary": summary,
        "cues": [c.to_dict() for c in transcript.cues],
    }
    payload = json.dumps(data, ensure_ascii=False)
    page = _HTML_TEMPLATE.replace("/*__DATA__*/", payload)
    Path(path).write_text(page, encoding="utf-8")


_HTML_TEMPLATE = """<!doctype html>
<html lang="zh">
<head>
<meta charset="utf-8"/>
<meta name="viewport" content="width=device-width, initial-scale=1"/>
<title>字幕复核 · 给视频加字幕然后复核</title>
<style>
  :root{--bg:#f6f7f9;--card:#fff;--line:#e3e6ea;--ink:#1f2329;--mut:#6b7280;
        --ok:#16a34a;--warn:#d97706;--err:#dc2626;--acc:#2563eb;}
  *{box-sizing:border-box}
  body{margin:0;font:14px/1.5 -apple-system,"Segoe UI",Roboto,"Microsoft YaHei",sans-serif;
       background:var(--bg);color:var(--ink)}
  header{padding:16px 20px;background:var(--card);border-bottom:1px solid var(--line)}
  header h1{margin:0;font-size:18px}
  header .meta{color:var(--mut);font-size:12px;margin-top:4px}
  .toolbar{padding:12px 20px;display:flex;gap:10px;flex-wrap:wrap;align-items:center;
           background:var(--card);border-bottom:1px solid var(--line)}
  .toolbar button{cursor:pointer;border:1px solid var(--line);background:#fff;border-radius:8px;
                  padding:6px 12px;font-size:13px}
  .toolbar button.active{background:var(--acc);color:#fff;border-color:var(--acc)}
  .steps{padding:12px 20px;display:flex;gap:8px;flex-wrap:wrap}
  .step{background:var(--card);border:1px solid var(--line);border-radius:10px;padding:8px 10px;font-size:12px;min-width:150px}
  .step b{display:block;font-size:13px}
  .step span{color:var(--mut)}
  main{padding:12px 20px 40px}
  table{width:100%;border-collapse:collapse;background:var(--card)}
  th,td{border:1px solid var(--line);padding:8px 10px;vertical-align:top;text-align:left}
  th{background:#eef1f5;position:sticky;top:0}
  tr.cue.flagged td:first-child{box-shadow:inset 3px 0 0 var(--warn)}
  .raw{color:var(--mut)}
  .fix{color:var(--acc);font-weight:600}
  .badge{display:inline-block;border-radius:999px;padding:1px 8px;font-size:11px;margin:2px 4px 2px 0}
  .b-info{background:#e0f2fe;color:#0369a1}
  .b-warn{background:#fef3c7;color:#92400e}
  .b-error{background:#fee2e2;color:#991b1b}
  .shots{display:flex;gap:6px;margin-top:6px}
  .shots img{height:64px;border:1px solid var(--line);border-radius:6px;background:#ddd}
  .acts button{cursor:pointer;border:1px solid var(--line);background:#fff;border-radius:6px;
               padding:3px 8px;font-size:12px;margin-right:4px}
  .acts button.on{background:var(--acc);color:#fff;border-color:var(--acc)}
  .vis-note{color:var(--mut);font-size:12px;margin-top:4px}
  footer{padding:14px 20px;color:var(--mut);font-size:12px}
  code{background:#eef1f5;padding:1px 5px;border-radius:4px}
</style>
</head>
<body>
<header>
  <h1>字幕复核面板 · 给视频加字幕然后复核</h1>
  <div class="meta" id="meta"></div>
</header>

<div class="toolbar">
  <span>显示文本:</span>
  <button id="showRaw">原话</button>
  <button id="showFix" class="active">修正(推荐)</button>
  <button id="allFix">全部采用修正</button>
  <button id="allRaw">全部保留原话</button>
  <button id="export">导出决定(JSON)</button>
  <span id="tally" style="color:var(--mut);margin-left:auto"></span>
</div>

<div class="steps" id="steps"></div>

<main>
  <table>
    <thead><tr><th>#</th><th>时间</th><th>原话</th><th>修正建议</th>
      <th>标记</th><th>画面核对</th><th>操作</th></tr></thead>
    <tbody id="rows"></tbody>
  </table>
</main>

<footer>
  每条都能在上方「操作」里采用修正 / 保留原话 / 手动改。导出 JSON 后用
  <code>cli.py export</code> 重产出最终 SRT / ASS / MP4。原话始终保留,可追溯、可回退。
</footer>

<script>
const DATA = /*__DATA__*/;
const pick = {};              // index -> "raw" | "fix" | 自定义文本
DATA.cues.forEach(c => pick[c.index] = c.is_fixed ? "fix" : "raw");
let showLayer = "fix";

function esc(t){return (t||"").replace(/[&<>"]/g,c=>({"&":"&amp;","<":"&lt;",">":"&gt;",'"':"&quot;"}[c]));}

function render(){
  document.getElementById("meta").textContent =
    "生成 " + DATA.generated + " · 语言 " + DATA.language + " · 条数 " + DATA.cues.length + " · 热词 " + (DATA.hotwords.join("、")||"无");
  document.getElementById("steps").innerHTML = (DATA.summary.trace||[]).map(s =>
    `<div class="step"><b>${esc(s.stage)}</b><span>${esc(s.time)} · ${esc(s.note)}</span></div>`).join("");
  const rows = DATA.cues.map(c => {
    const flagged = c.issues.length > 0;
    const raw = esc(c.raw_text);
    const fix = c.fixed_text ? esc(c.fixed_text) : "—";
    const badges = c.issues.map(i => `<span class="badge b-${i.level}">[${i.level}] ${esc(i.reason)}</span>`).join("");
    const shots = (c.frames||[]).map(f => `<img src="${esc(f)}"/>`).join("");
    const vis = c.visual_ok===true?"一致":(c.visual_ok===false?"冲突":"未核对");
    const visNote = c.visual_note?`<div class="vis-note">画面: ${esc(c.visual_note)}（${vis}）</div>`:"";
    return `<tr class="cue ${flagged?'flagged':''}" data-i="${c.index}">
      <td>${c.index}</td>
      <td>${c.start.toFixed(1)}-${c.end.toFixed(1)}s</td>
      <td class="raw">${raw}</td>
      <td class="fix">${fix}</td>
      <td>${badges||"—"}</td>
      <td>${vis}${visNote}${shots?`<div class="shots">${shots}</div>`:""}</td>
      <td class="acts">
        <button data-act="raw">保留原话</button>
        <button data-act="fix">采用修正</button>
        <button data-act="edit">手动改</button>
      </td>
    </tr>`;
  }).join("");
  document.getElementById("rows").innerHTML = rows;
  const fixed = DATA.cues.filter(c => pick[c.index]==="fix" && c.fixed_text).length;
  const flagged = DATA.cues.filter(c => c.issues.length>0).length;
  document.getElementById("tally").textContent = "标记 " + flagged + " · 采用修正 " + fixed;
  bind();
}

function bind(){
  document.querySelectorAll("#rows tr").forEach(tr=>{
    const i = +tr.dataset.i;
    tr.querySelectorAll(".acts button").forEach(b=>{
      b.onclick=()=>{
        const act=b.dataset.act;
        if(act==="edit"){
          const cur = DATA.cues.find(c=>c.index===i);
          const v=prompt("编辑该条文本:", cur.fixed_text||cur.raw_text);
          if(v!==null) pick[i]=v;
        } else pick[i]=act;
        render();
      };
    });
  });
}

function setLayer(l){showLayer=l;document.getElementById("showRaw").classList.toggle("active",l==="raw");
  document.getElementById("showFix").classList.toggle("active",l==="fix");}

document.getElementById("showRaw").onclick=()=>setLayer("raw");
document.getElementById("showFix").onclick=()=>setLayer("fix");
document.getElementById("allFix").onclick=()=>{DATA.cues.forEach(c=>pick[c.index]=c.is_fixed?"fix":"raw");render();};
document.getElementById("allRaw").onclick=()=>{DATA.cues.forEach(c=>pick[c.index]="raw");render();};
document.getElementById("export").onclick=()=>{
  const out = DATA.cues.map(c=>({
    index:c.index, start:c.start, end:c.end,
    raw_text:c.raw_text, fixed_text:c.fixed_text,
    decision: (pick[c.index]==="fix"&&c.fixed_text)?c.fixed_text:
      (typeof pick[c.index]==="string"&&pick[c.index]!=="raw"&&pick[c.index]!=="fix"?pick[c.index]:c.raw_text)
  }));
  const blob=new Blob([JSON.stringify({media:DATA.media,cues:out},null,2)],{type:"application/json"});
  const a=document.createElement("a");a.href=URL.createObjectURL(blob);
  a.download="subtitle_choices.json";a.click();
};
render();
</script>
</body>
</html>
"""
