#!/usr/bin/env python3
"""index_html.py — experiments/INDEX.html(ソート/フィルタ可能な読みビュー)生成

正本は report_meta.py と同じ「各 experiments/<id>/REPORT.md のフロントマター」。
そこから並べ替え・状態フィルタ・全文検索のできる自己完結 HTML を生成する。
生成物は派生ビューであり git にはコミットしない(.gitignore 済み)。

使い方
------
  python tools/index_html.py             # experiments/INDEX.html を生成
  python tools/report_meta.py            # INDEX.md 再生成時にも自動で再生成される

依存なし(stdlib のみ)。外部 CSS/JS を参照しない単一 HTML を書き出す。
"""
from __future__ import annotations

import argparse
import json
import sys
from datetime import date, datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import report_meta  # noqa: E402  (parse_frontmatter / EXPERIMENT_STATUS / load_config を共用)

STATUS_LABEL = {
    "planning": "📋 計画中",
    "active": "🔄 実施中",
    "done": "✅ 完了",
    "paused": "⚪ 中断/保留",
}
# フィルタチップと状態ソートの表示順
STATUS_ORDER = ["active", "planning", "paused", "done"]


def _parse_date(s: str | None) -> date | None:
    if not s:
        return None
    try:
        return date.fromisoformat(str(s))
    except ValueError:
        return None


def collect(exp_dir: Path, config: dict) -> tuple[list[dict], list[str]]:
    """REPORT.md フロントマターを行データに変換して返す。(rows, warnings)"""
    rows: list[dict] = []
    warnings: list[str] = []
    today = date.today()
    jira_enabled = config.get("jira_enabled", False)
    jira_base = config.get("jira_base_url", "https://atlassian.net/browse/")
    prefix = config.get("experiment_id_prefix", "E")
    required = ["experiment_id", "status", "summary"] + (["jira"] if jira_enabled else [])
    for report in sorted(exp_dir.glob("*/REPORT.md")):
        if report.parent.name.startswith("_"):
            continue
        try:
            meta = report_meta.parse_frontmatter(report)
        except report_meta.MetaError as e:
            warnings.append(str(e))
            continue
        if meta is None:
            warnings.append(f"フロントマター無し(HTML 未反映): {report}")
            continue
        if any(not meta.get(k) for k in required):
            warnings.append(f"必須キー欠落(HTML 未反映): {report}")
            continue
        status = meta["status"]
        if status not in report_meta.EXPERIMENT_STATUS:
            warnings.append(f"不正 status='{status}'(HTML 未反映): {report}")
            continue
        eid = meta["experiment_id"]
        start = _parse_date(meta.get("period_start"))
        end = _parse_date(meta.get("period_end"))
        # 経過日数: 完了なら期間長、継続中なら今日まで(開始日込み)
        days = ((end or today) - start).days + 1 if start else None
        n_reports = len(
            [p for p in (report.parent / "reports").glob("*.md") if p.name != "INDEX.md"]
        ) if (report.parent / "reports").is_dir() else 0
        rows.append(
            {
                "id": eid,
                "num": (
                    report_meta._jira_num(meta["jira"]) if jira_enabled
                    else report_meta._exp_num(eid, prefix)
                ),
                "jira": meta.get("jira") or "",
                "jiraUrl": f"{jira_base}{meta['jira']}" if jira_enabled else "",
                "status": status,
                "badge": report_meta.EXPERIMENT_STATUS[status],
                "start": meta.get("period_start") or "",
                "end": meta.get("period_end") or "",
                "days": days,
                "reports": n_reports,
                "summary": meta["summary"],
                # ローカル絶対パス(vscode:// リンク用。生成物はローカル専用なので可)
                "path": report.resolve().as_posix(),
            }
        )
    return rows, warnings


def generate(exp_dir: Path, out_path: Path | None = None) -> Path:
    config = report_meta.load_config(exp_dir.parent)
    rows, warnings = collect(exp_dir, config)
    for w in warnings:
        print(f"NOTE: {w}")
    out = out_path or (exp_dir / "INDEX.html")
    counts = {s: sum(1 for r in rows if r["status"] == s) for s in STATUS_ORDER}
    payload = {
        "rows": rows,
        "statusLabel": STATUS_LABEL,
        "statusOrder": STATUS_ORDER,
        "counts": counts,
        # JIRA 連携は .lab-config.json の jira_enabled 次第。無効ならその列ごと出さない
        "jiraEnabled": bool(config.get("jira_enabled", False)),
        "generated": datetime.now().strftime("%Y-%m-%d %H:%M"),
    }
    data_json = json.dumps(payload, ensure_ascii=False).replace("</", "<\\/")
    html = _TEMPLATE.replace("__DATA__", data_json)
    out.write_text(html, encoding="utf-8")
    return out


# --- 自己完結 HTML テンプレート(外部参照なし / light・dark 両対応) ------------
_TEMPLATE = """<!DOCTYPE html>
<html lang="ja">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>実験レジストリ INDEX</title>
<style>
  :root {
    --bg: #f8f9fb; --panel: #ffffff; --text: #1c2330; --muted: #66707f;
    --border: #dde2ea; --accent: #5b4b9e; --accent-soft: #ece8f7;
    --hover: #f1f3f8; --chip-off: #eef0f4;
  }
  @media (prefers-color-scheme: dark) {
    :root {
      --bg: #14161c; --panel: #1d2029; --text: #e6e9ef; --muted: #9aa3b2;
      --border: #333846; --accent: #a99bdc; --accent-soft: #2c2741;
      --hover: #262a36; --chip-off: #262a33;
    }
  }
  * { box-sizing: border-box; }
  body {
    margin: 0; padding: 1.2rem clamp(0.8rem, 3vw, 2.5rem);
    background: var(--bg); color: var(--text);
    font-family: "Segoe UI", "Yu Gothic UI", "Hiragino Sans", Meiryo, sans-serif;
    font-size: 14px; line-height: 1.55;
  }
  h1 { font-size: 1.25rem; margin: 0 0 .2rem; }
  .meta { color: var(--muted); font-size: .82rem; margin-bottom: 1rem; }
  .controls {
    display: flex; flex-wrap: wrap; gap: .5rem; align-items: center;
    margin-bottom: .8rem;
  }
  #search {
    flex: 1 1 240px; max-width: 420px; padding: .45rem .7rem;
    border: 1px solid var(--border); border-radius: 8px;
    background: var(--panel); color: var(--text); font-size: .9rem;
  }
  #search:focus { outline: 2px solid var(--accent); outline-offset: -1px; }
  .chip {
    border: 1px solid var(--border); border-radius: 999px;
    padding: .3rem .8rem; cursor: pointer; user-select: none;
    background: var(--accent-soft); color: var(--text); font-size: .85rem;
    white-space: nowrap;
  }
  .chip.off { background: var(--chip-off); color: var(--muted); opacity: .65; }
  .count-note { color: var(--muted); font-size: .82rem; margin-left: auto; }
  .tablewrap {
    overflow-x: auto; border: 1px solid var(--border); border-radius: 10px;
    background: var(--panel);
  }
  table { border-collapse: collapse; width: 100%; min-width: 880px; }
  th, td { padding: .5rem .65rem; text-align: left; vertical-align: top; }
  thead th {
    position: sticky; top: 0; background: var(--panel); z-index: 1;
    border-bottom: 2px solid var(--border); font-size: .82rem;
    color: var(--muted); white-space: nowrap; cursor: pointer; user-select: none;
  }
  thead th.nosort { cursor: default; }
  thead th .arrow { color: var(--accent); }
  tbody tr { border-bottom: 1px solid var(--border); cursor: pointer; }
  tbody tr:hover { background: var(--hover); }
  tbody tr:last-child { border-bottom: none; }
  td.num { text-align: right; font-variant-numeric: tabular-nums; white-space: nowrap; }
  td.nowrap { white-space: nowrap; }
  td.status { white-space: nowrap; }
  a { color: var(--accent); text-decoration: none; }
  a:hover { text-decoration: underline; }
  .expid { font-family: Consolas, "Cascadia Mono", monospace; font-size: .85rem; }
  .summary {
    display: -webkit-box; -webkit-line-clamp: 2; -webkit-box-orient: vertical;
    overflow: hidden; color: var(--text);
  }
  tr.open .summary { display: block; -webkit-line-clamp: unset; }
  .hint { color: var(--muted); font-size: .78rem; margin-top: .6rem; }
  .empty { padding: 1.2rem; color: var(--muted); text-align: center; }
</style>
</head>
<body>
<h1>実験レジストリ INDEX</h1>
<div class="meta">生成: <span id="generated"></span> ・ 正本は各実験の REPORT.md フロントマター(再生成: <code>python tools/index_html.py</code>)</div>

<div class="controls">
  <input id="search" type="search" placeholder="検索 (ID / 要約)…">
  <span id="chips"></span>
  <span class="count-note"><span id="shown"></span> / <span id="total"></span> 件</span>
</div>

<div class="tablewrap">
  <table>
    <thead><tr id="headrow"></tr></thead>
    <tbody id="rows"></tbody>
  </table>
</div>
<div class="hint">行クリックで要約を全文表示 / 列見出しクリックで並べ替え(再クリックで昇降切替) / 実験IDクリックで VSCode の REPORT.md を開く</div>

<script type="application/json" id="data">__DATA__</script>
<script>
(function () {
  const D = JSON.parse(document.getElementById("data").textContent);
  document.getElementById("generated").textContent = D.generated;
  document.getElementById("total").textContent = D.rows.length;

  const statusRank = Object.fromEntries(D.statusOrder.map((s, i) => [s, i]));
  const COLS = [
    { key: "status", label: "状態", cls: "status" },
    { key: "num",    label: "実験", cls: "nowrap" },
    ...(D.jiraEnabled ? [{ key: "jira", label: "JIRA", cls: "nowrap" }] : []),
    { key: "start",  label: "開始", cls: "nowrap" },
    { key: "end",    label: "終了", cls: "nowrap" },
    { key: "days",   label: "日数", cls: "num" },
    { key: "reports", label: "Rpt", cls: "num" },
    { key: "summary", label: "1 行要約", nosort: true },
  ];
  const state = { sort: "num", dir: -1, q: "", on: new Set(D.statusOrder), open: new Set() };

  // --- status filter chips ---
  const chips = document.getElementById("chips");
  D.statusOrder.forEach((s) => {
    const b = document.createElement("button");
    b.className = "chip";
    b.textContent = D.statusLabel[s] + " " + D.counts[s];
    b.onclick = () => {
      state.on.has(s) ? state.on.delete(s) : state.on.add(s);
      b.classList.toggle("off", !state.on.has(s));
      render();
    };
    chips.appendChild(b);
  });

  // --- sortable header ---
  const headrow = document.getElementById("headrow");
  COLS.forEach((c) => {
    const th = document.createElement("th");
    th.dataset.key = c.key;
    if (c.nosort) th.className = "nosort";
    else th.onclick = () => {
      if (state.sort === c.key) state.dir *= -1;
      else { state.sort = c.key; state.dir = c.key === "num" ? -1 : 1; }
      render();
    };
    headrow.appendChild(th);
  });

  document.getElementById("search").addEventListener("input", (e) => {
    state.q = e.target.value.trim().toLowerCase();
    render();
  });

  function sortVal(r, key) {
    if (key === "status") return statusRank[r.status];
    if (key === "days" || key === "reports" || key === "num") return r[key] ?? -1;
    if (key === "end") return r.end || "9999-99-99"; // 継続中は最新扱い
    return r[key] || "";
  }
  function esc(s) {
    return s.replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;")
            .replace(/"/g, "&quot;");
  }
  function hl(text) {
    const e = esc(text);
    if (!state.q) return e;
    const i = e.toLowerCase().indexOf(esc(state.q));
    return i < 0 ? e : e.slice(0, i) + "<mark>" + e.slice(i, i + state.q.length) + "</mark>" + e.slice(i + state.q.length);
  }

  function render() {
    // header arrows
    headrow.querySelectorAll("th").forEach((th, i) => {
      const c = COLS[i];
      th.innerHTML = esc(c.label) + (state.sort === c.key
        ? ' <span class="arrow">' + (state.dir > 0 ? "▲" : "▼") + "</span>" : "");
    });
    let rows = D.rows.filter((r) => state.on.has(r.status));
    if (state.q) {
      rows = rows.filter((r) =>
        (r.id + " " + r.jira + " " + r.summary).toLowerCase().includes(state.q));
    }
    rows.sort((a, b) => {
      const va = sortVal(a, state.sort), vb = sortVal(b, state.sort);
      const cmp = va < vb ? -1 : va > vb ? 1 : (a.num - b.num);
      return cmp * state.dir;
    });
    document.getElementById("shown").textContent = rows.length;

    const tb = document.getElementById("rows");
    if (!rows.length) {
      tb.innerHTML = '<tr><td colspan="' + COLS.length + '" class="empty">該当する実験がありません</td></tr>';
      return;
    }
    tb.innerHTML = rows.map((r) => {
      const open = state.open.has(r.id) ? " class=\\"open\\"" : "";
      return "<tr data-id=\\"" + esc(r.id) + "\\"" + open + ">"
        + "<td class=\\"status\\" title=\\"" + esc(D.statusLabel[r.status]) + "\\">" + r.badge + "</td>"
        + "<td class=\\"nowrap\\"><a class=\\"expid\\" href=\\"vscode://file/" + esc(r.path) + "\\" title=\\"" + esc(r.id) + " の REPORT.md を VSCode で開く\\">" + hl(r.id.split("_")[0]) + "</a><br><span class=\\"expid\\" style=\\"color:var(--muted)\\">" + hl(r.id.slice(r.id.indexOf("_") + 1)) + "</span></td>"
        + (D.jiraEnabled
            ? "<td class=\\"nowrap\\"><a href=\\"" + esc(r.jiraUrl) + "\\" target=\\"_blank\\" rel=\\"noopener\\">" + hl(r.jira) + "</a></td>"
            : "")
        + "<td class=\\"nowrap\\">" + esc(r.start) + "</td>"
        + "<td class=\\"nowrap\\">" + (r.end ? esc(r.end) : "<span style=\\"color:var(--muted)\\">〜</span>") + "</td>"
        + "<td class=\\"num\\">" + (r.days ?? "") + "</td>"
        + "<td class=\\"num\\">" + r.reports + "</td>"
        + "<td><div class=\\"summary\\">" + hl(r.summary) + "</div></td>"
        + "</tr>";
    }).join("");

    tb.querySelectorAll("tr[data-id]").forEach((tr) => {
      tr.addEventListener("click", (ev) => {
        if (ev.target.closest("a")) return; // let links work
        const id = tr.dataset.id;
        state.open.has(id) ? state.open.delete(id) : state.open.add(id);
        tr.classList.toggle("open");
      });
    });
  }
  render();
})();
</script>
</body>
</html>
"""


def main(argv: list[str]) -> int:
    for stream in (sys.stdout, sys.stderr):
        try:
            stream.reconfigure(encoding="utf-8")  # type: ignore[attr-defined]
        except (AttributeError, ValueError):
            pass
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("experiments", nargs="?", help="experiments/ ディレクトリ(既定: リポジトリ内)")
    ap.add_argument("--out", help="出力パス(既定: <experiments>/INDEX.html)")
    args = ap.parse_args(argv)

    # install モデルでは tools/ が harness への symlink。cwd(=記録層)基準で解決する。
    exp_dir = Path(args.experiments) if args.experiments else Path.cwd() / "experiments"
    if not exp_dir.is_dir():
        print(f"experiments ディレクトリが見つからない: {exp_dir}", file=sys.stderr)
        return 2
    out = generate(exp_dir, Path(args.out) if args.out else None)
    print(f"生成: {out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
