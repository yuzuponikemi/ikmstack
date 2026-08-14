#!/usr/bin/env python3
"""Build a side-by-side (report | verification) 2-pane review HTML for report-checksum.

The default deliverable of a per-report 検算: the target report's readview HTML on
the left, the verification HTML on the right, each independently scrollable, with a
draggable divider. It references the two HTML files by relative path (no duplication),
so regenerating either updates the review view automatically.

Usage:
  python build_review_view.py \
    --report <exp>/_generated/<E###-R###>_*.readview.html \
    --verify <exp>/verification/verify_<id>.html \
    --out    <exp>/verification/review_<E###-R###>_side-by-side.html \
    [--title "E059-R001 レビュー"] [--left-label "..."] [--right-label "..."]

Open the result in a browser (VSCode has no synced two-HTML view):
  ! start <out>
"""
from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path

_TEMPLATE = """<!doctype html>
<html lang="ja">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{title}</title>
<style>
  :root {{ --bar:#2d2a4a; --bar-fg:#fff; --divider:#b9b4d0; --divider-hover:#7c6fd6; }}
  * {{ box-sizing:border-box; }}
  html,body {{ height:100%; margin:0; font-family:"Segoe UI",system-ui,sans-serif; }}
  .wrap {{ display:flex; flex-direction:column; height:100vh; }}
  header.top {{ flex:0 0 auto; background:var(--bar); color:var(--bar-fg);
    padding:6px 12px; font-size:13px; display:flex; gap:16px; align-items:center; }}
  header.top .hint {{ margin-left:auto; opacity:.75; font-size:12px; }}
  .panes {{ flex:1 1 auto; display:flex; min-height:0; }}
  .pane {{ display:flex; flex-direction:column; min-width:120px; min-height:0; }}
  .pane .label {{ flex:0 0 auto; background:#efedf6; color:#2d2a4a; font-size:12px;
    font-weight:600; padding:4px 10px; border-bottom:1px solid #d8d4e8; }}
  .pane .label.rgt {{ background:#e7f3ec; color:#1e5b38; }}
  .pane iframe {{ flex:1 1 auto; width:100%; border:0; background:#fff; }}
  #left {{ flex:0 0 50%; }}
  #right {{ flex:1 1 auto; }}
  .divider {{ flex:0 0 6px; cursor:col-resize; background:var(--divider); position:relative; }}
  .divider:hover, .divider.drag {{ background:var(--divider-hover); }}
  .divider::after {{ content:"\\22EE\\22EE"; position:absolute; top:50%; left:50%;
    transform:translate(-50%,-50%) rotate(90deg); color:#fff; font-size:10px; letter-spacing:-2px; }}
</style>
</head>
<body>
<div class="wrap">
  <header class="top">
    <b>{title}</b>
    <span>左 = {left_label}</span><span>右 = {right_label}</span>
    <span class="hint">中央の帯をドラッグで幅調整 · 各ペインは独立スクロール</span>
  </header>
  <div class="panes" id="panes">
    <div class="pane" id="left"><div class="label">📄 {left_label}</div>
      <iframe id="fLeft" title="report"></iframe></div>
    <div class="divider" id="divider" title="ドラッグで幅調整"></div>
    <div class="pane" id="right"><div class="label rgt">🔎 {right_label}</div>
      <iframe id="fRight" title="verification"></iframe></div>
  </div>
</div>
<script>
  // Assign via JS so the browser URL-encodes non-ASCII (Japanese) filenames correctly.
  document.getElementById("fLeft").src  = {report_rel!r};
  document.getElementById("fRight").src = {verify_rel!r};
  const panes=document.getElementById("panes"), left=document.getElementById("left"),
        divider=document.getElementById("divider"); let dragging=false;
  divider.addEventListener("mousedown",(e)=>{{ dragging=true; divider.classList.add("drag");
    document.body.style.userSelect="none";
    document.querySelectorAll("iframe").forEach(f=>f.style.pointerEvents="none"); e.preventDefault(); }});
  window.addEventListener("mousemove",(e)=>{{ if(!dragging) return;
    const r=panes.getBoundingClientRect(); let px=Math.max(120,Math.min(r.width-120,e.clientX-r.left));
    left.style.flex="0 0 "+px+"px"; }});
  window.addEventListener("mouseup",()=>{{ if(!dragging) return; dragging=false; divider.classList.remove("drag");
    document.body.style.userSelect="";
    document.querySelectorAll("iframe").forEach(f=>f.style.pointerEvents=""); }});
</script>
</body>
</html>
"""


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--report", required=True, type=Path, help="target report readview HTML")
    ap.add_argument("--verify", required=True, type=Path, help="verification HTML")
    ap.add_argument("--out", required=True, type=Path, help="output review-view HTML")
    ap.add_argument("--title", default="レビュー: 本命レポート ｜ 検算")
    ap.add_argument("--left-label", default="本命レポート")
    ap.add_argument("--right-label", default="検算")
    args = ap.parse_args()

    # Windows consoles default to cp1252; paths/labels may be non-ASCII (Japanese).
    for stream in (sys.stdout, sys.stderr):
        try:
            stream.reconfigure(encoding="utf-8")
        except (AttributeError, ValueError):
            pass

    for p, what in ((args.report, "report"), (args.verify, "verify")):
        if not p.exists():
            raise SystemExit(f"{what} HTML not found: {p}\n"
                             "(generate the report readview / run the verification first)")

    out_dir = args.out.resolve().parent
    out_dir.mkdir(parents=True, exist_ok=True)
    # relative paths from the shell's own directory (forward slashes for the browser)
    report_rel = os.path.relpath(args.report.resolve(), out_dir).replace(os.sep, "/")
    verify_rel = os.path.relpath(args.verify.resolve(), out_dir).replace(os.sep, "/")

    html = _TEMPLATE.format(title=args.title, left_label=args.left_label,
                            right_label=args.right_label,
                            report_rel=report_rel, verify_rel=verify_rel)
    args.out.write_text(html, encoding="utf-8")
    print("wrote review-view:", args.out)
    print("  left  (report):", report_rel)
    print("  right (verify):", verify_rel)
    print(f"open in a browser:\n  ! start {args.out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
