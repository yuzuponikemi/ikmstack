#!/usr/bin/env python3
"""synthesis_extract.py — cross-experiment synthesis material extractor (依存なし)

report_meta.py が「1 実験 = 1 行の INDEX」を frontmatter から生成するのと同じ
二重帳簿思想の一段上。ここでは **全 experiments/*/REPORT.md を横断**して、
frontmatter + 「次のアクション」+「KB への昇格」+ 実験間の相互参照を機械抽出し、
横断ビュー 3 種の**素材**になる構造化データを吐く。

正本はあくまで各 REPORT.md(frontmatter + 本文)。このスクリプトは常設リビング文書を
作らず、**オンデマンド生成**の入力を作るだけ(設計原則)。gbrain 索引が
git に遅れる構造のため、ここでは brain を介さず **git 作業ツリーを直接**読む
(鮮度ラグに依存しない)。

抽出する 3 ビューの素材:
  (1) map          — 現在地マップ: 各実験の id/status/期間/要約/未完アクション数/参照
  (2) links        — 矛盾候補の材料: 実験間の相互参照エッジ + 各ノードの要約
                     (矛盾そのものは判定しない。人 / LLM / gbrain に渡す素材)
  (3) backlog      — 未昇格バックログ: 未完アクション・KB 未昇格・派生チケット候補・tips

使い方
------
  python tools/synthesis_extract.py                 # JSON を stdout へ
  python tools/synthesis_extract.py --markdown      # 3 ビューを Markdown で
  python tools/synthesis_extract.py --out <dir>     # JSON + Markdown をファイル出力
  python tools/synthesis_extract.py <experiments>   # 既定: リポジトリの experiments/

frontmatter の解析は report_meta.parse_frontmatter を再利用(パーサの二重持ち回避)。
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

# パーサは report_meta が単一の権威。同ディレクトリから読み込む。
sys.path.insert(0, str(Path(__file__).resolve().parent))
from report_meta import parse_frontmatter, MetaError, load_config  # noqa: E402
import synthesis_topical  # noqa: E402  (装置名・技術語の近接検出。分割モジュール)

# --- 正規表現 ----------------------------------------------------------------
# 実験 ID の接頭辞はノート固有(.lab-config.json)。実験間参照 [[E067]] / E-067 /
# E067 / ../E067_.../ / E076-R010 を一律捕捉する。接頭辞は大小文字を区別する
# (1 文字接頭辞が指数表記 1.2e-3 などを拾わないように)。
_CFG = load_config(Path.cwd())
PREFIX = str(_CFG.get("experiment_id_prefix", "E"))
_REF_RE = re.compile(rf"(?<![A-Za-z0-9]){re.escape(PREFIX)}-?0*(\d{{1,5}})")
# 見出し行(## / ###)。# レベルとテキストを取る。
_HEADING_RE = re.compile(r"^(#{2,4})\s+(.*?)\s*$")
# チェックボックス項目: "- [ ] text" / "- [x] text"(インデント許容)
_TASK_RE = re.compile(r"^\s*[-*]\s+\[([ xX])\]\s+(.*?)\s*$")

# 次アクション節と見なす見出し(表記ゆれを吸収)
_ACTION_HEADINGS = ("次のアクション", "次にやること", "次の計画", "todo", "to-do")
_KB_HEADINGS = ("kb への昇格", "kbへの昇格", "kb 昇格", "知見の昇格")

# 優先度・派生課題を示すキーワード(未完アクションの分類用)
_PRIORITY_KW = ("最優先", "優先", "急ぎ", "先行")
_DERIVED_KW = ("別チケット", "別課題", "チケット化", "起票", "子チケット")
_PROMOTE_KW = ("昇格", "kb")

# KB 節の状態判定キーワード
_KB_NONE_KW = ("なし",)
_KB_DONE_KW = ("kb/", "kb docs", "pr #", "pr#", "昇格済")
_KB_PENDING_KW = ("昇格候補", "昇格を検討", "昇格予定", "確度が上がれば", "確度が上がった", "検討")


def _norm(s: str) -> str:
    return s.strip().lower()


# --- 本文の節分割 ------------------------------------------------------------
def split_sections(body: str) -> dict[str, list[str]]:
    """本文を「見出しテキスト -> その節の行リスト」に分割する。

    同名見出しがあれば行を連結する(実運用では稀)。frontmatter 除去後の本文を渡す。
    """
    sections: dict[str, list[str]] = {}
    current = "__preamble__"
    sections[current] = []
    for line in body.splitlines():
        m = _HEADING_RE.match(line)
        if m:
            current = m.group(2).strip()
            sections.setdefault(current, [])
            continue
        sections.setdefault(current, []).append(line)
    return sections


def _strip_frontmatter(text: str) -> str:
    lines = text.splitlines()
    if not lines or lines[0].strip() != "---":
        return text
    for i in range(1, len(lines)):
        if lines[i].strip() == "---":
            return "\n".join(lines[i + 1:])
    return text


def _find_section(sections: dict[str, list[str]], names: tuple[str, ...]) -> list[str]:
    """見出し名(正規化・部分一致)で節本文を返す。無ければ空。"""
    for heading, lines in sections.items():
        h = _norm(heading)
        if any(n in h for n in names):
            return lines
    return []


# --- アクション抽出 ----------------------------------------------------------
def extract_actions(lines: list[str], self_num: int | None) -> list[dict]:
    """チェックボックス項目を {done, text, priority, derived_refs, promote} に構造化。"""
    out = []
    for line in lines:
        m = _TASK_RE.match(line)
        if not m:
            continue
        done = m.group(1).lower() == "x"
        text = m.group(2).strip()
        low = text.lower()
        refs = sorted({int(g) for g in _REF_RE.findall(text)} - ({self_num} if self_num else set()))
        out.append({
            "done": done,
            "text": text,
            "priority": any(k in text for k in _PRIORITY_KW),
            "derived_ticket": any(k in text for k in _DERIVED_KW) or (not done and bool(refs)),
            "derived_refs": refs,
            "promote": any(k in low for k in _PROMOTE_KW),
        })
    return out


# --- KB 昇格節の状態判定 -----------------------------------------------------
def classify_kb(lines: list[str]) -> dict:
    text = "\n".join(lines).strip()
    low = text.lower()
    if not text:
        return {"status": "missing", "text": ""}
    has_done = any(k in low for k in _KB_DONE_KW)
    has_pending = any(k in low for k in _KB_PENDING_KW)
    # 「なし」が実質本文(リンクや PR 参照が無い)なら none
    only_none = (any(k in text for k in _KB_NONE_KW) and not has_done)
    if has_done and not has_pending:
        status = "promoted"
    elif has_pending:
        status = "pending"
    elif only_none:
        status = "none"
    else:
        status = "unknown"
    return {"status": status, "text": text[:400]}


# --- 相互参照抽出 ------------------------------------------------------------
def extract_refs(body: str, self_num: int | None) -> dict[int, int]:
    """本文中の実験 ID 参照を {番号: 出現回数} で返す(自己参照除外)。"""
    counts: dict[int, int] = {}
    for g in _REF_RE.findall(body):
        n = int(g)
        if self_num and n == self_num:
            continue
        counts[n] = counts.get(n, 0) + 1
    return counts


def _self_num(meta: dict) -> int | None:
    """実験の通し番号。JIRA 連携があればチケット番号、無ければ実験 ID の数字部。"""
    for source in (meta.get("jira") or "", (meta.get("experiment_id") or "").split("_")[0]):
        digits = "".join(c for c in source if c.isdigit())
        if digits:
            return int(digits)
    return None


# --- 実験 1 件の抽出 ---------------------------------------------------------
def extract_experiment(report: Path) -> dict:
    text = report.read_text(encoding="utf-8")
    meta = parse_frontmatter(report) or {}
    self_num = _self_num(meta)
    body = _strip_frontmatter(text)
    sections = split_sections(body)

    actions = extract_actions(_find_section(sections, _ACTION_HEADINGS), self_num)
    kb = classify_kb(_find_section(sections, _KB_HEADINGS))
    refs = extract_refs(body, self_num)

    open_actions = [a for a in actions if not a["done"]]
    return {
        "experiment_id": meta.get("experiment_id") or report.parent.name,
        "jira": meta.get("jira"),
        "num": self_num,
        "status": meta.get("status"),
        "period_start": meta.get("period_start"),
        "period_end": meta.get("period_end"),
        "summary": meta.get("summary"),
        "action_total": len(actions),
        "action_open": len(open_actions),
        "action_done": len(actions) - len(open_actions),
        "actions_open": open_actions,
        "kb": kb,
        "refs": {str(k): v for k, v in sorted(refs.items())},
        "path": str(report.relative_to(report.parent.parent.parent)),
    }


# --- tips スキャン(KB 前段の在庫) ------------------------------------------
def scan_tips(repo_root: Path) -> list[dict]:
    tips_dir = repo_root / "tips"
    out = []
    if not tips_dir.is_dir():
        return out
    for f in sorted(tips_dir.glob("*.md")):
        if f.name == "README.md":
            continue
        lines = f.read_text(encoding="utf-8").splitlines()
        title = next((ln.lstrip("# ").strip() for ln in lines if ln.startswith("#")), f.stem)
        body = "\n".join(lines).lower()
        promoted = any(k in body for k in _KB_DONE_KW)
        out.append({
            "file": f.name,
            "title": title,
            "kind": f.stem.split("-", 1)[0],  # mechanism / method
            "promoted_ref": promoted,
        })
    return out


# --- コーパス全体の抽出 ------------------------------------------------------
def build_corpus(exp_dir: Path) -> dict:
    repo_root = exp_dir.parent
    experiments = []
    warnings = []
    for report in sorted(exp_dir.glob("*/REPORT.md")):
        if report.parent.name.startswith("_"):
            continue
        try:
            experiments.append(extract_experiment(report))
        except MetaError as e:
            warnings.append(f"parse error: {report}: {e}")
    experiments.sort(key=lambda e: e["num"] or 0)
    return {
        "generated_from": str(exp_dir),
        "experiment_count": len(experiments),
        "experiments": experiments,
        "tips": scan_tips(repo_root),
        "warnings": warnings,
    }


# --- 3 ビューの導出(素材レベル) --------------------------------------------
def view_map(corpus: dict) -> list[dict]:
    return [
        {
            "num": e["num"], "experiment_id": e["experiment_id"], "status": e["status"],
            "period": _fmt_period(e), "open": e["action_open"], "done": e["action_done"],
            "refs": sorted(int(k) for k in e["refs"]), "summary": _clip(e["summary"], 120),
        }
        for e in corpus["experiments"]
    ]


def view_links(corpus: dict) -> list[dict]:
    """相互参照エッジ(A->B)。矛盾検出の材料。双方向参照はクラスタの核。"""
    by_num = {e["num"]: e for e in corpus["experiments"] if e["num"]}
    edges = []
    for e in corpus["experiments"]:
        for tgt_s, cnt in e["refs"].items():
            tgt = int(tgt_s)
            reciprocal = e["num"] in {int(k) for k in by_num.get(tgt, {}).get("refs", {})}
            edges.append({
                "from": e["num"], "to": tgt, "count": cnt, "reciprocal": reciprocal,
                "from_summary": _clip(e["summary"], 90),
                "to_known": tgt in by_num,
                "to_summary": _clip(by_num.get(tgt, {}).get("summary"), 90) if tgt in by_num else None,
            })
    edges.sort(key=lambda x: (not x["reciprocal"], -x["count"]))
    return edges


def view_backlog(corpus: dict) -> dict:
    open_actions, derived, promote_pending = [], [], []
    for e in corpus["experiments"]:
        for a in e["actions_open"]:
            row = {"num": e["num"], "experiment_id": e["experiment_id"],
                   "text": _clip(a["text"], 160), "priority": a["priority"]}
            open_actions.append(row)
            if a["derived_ticket"]:
                derived.append({**row, "refs": a["derived_refs"]})
            if a["promote"]:
                promote_pending.append(row)
    kb_unpromoted = [
        {"num": e["num"], "experiment_id": e["experiment_id"],
         "kb_status": e["kb"]["status"], "note": _clip(e["kb"]["text"], 120)}
        for e in corpus["experiments"]
        if e["kb"]["status"] in ("pending", "none", "missing")
    ]
    return {
        "open_actions": open_actions,
        "priority_actions": [a for a in open_actions if a["priority"]],
        "derived_ticket_candidates": derived,
        "kb_promotion_pending": promote_pending,
        "kb_unpromoted_experiments": kb_unpromoted,
        "tips_inventory": corpus["tips"],
    }


# --- 整形ヘルパ --------------------------------------------------------------
def _fmt_period(e: dict) -> str:
    s, en = e.get("period_start") or "", e.get("period_end") or ""
    if s and en:
        return f"{s}〜{en}"
    return f"{s}〜" if s else ""


def _clip(s: str | None, n: int) -> str:
    if not s:
        return ""
    s = " ".join(s.split())
    return s if len(s) <= n else s[: n - 1] + "…"


# --- Markdown レンダラ(手順3 骨格) -----------------------------------------
_STATUS_BADGE = {"planning": "📋", "active": "🔄", "done": "✅", "paused": "⚪"}


def render_markdown(corpus: dict) -> str:
    m = view_map(corpus)
    links = view_links(corpus)
    bl = view_backlog(corpus)
    topical = corpus.get("views", {}).get("topical") \
        or synthesis_topical.build_topical(Path(corpus["generated_from"]), corpus["experiments"])
    id_by_num = {e["num"]: e["experiment_id"] for e in corpus["experiments"] if e["num"]}
    out: list[str] = []
    out.append("# state-of-the-lab(自動生成・素材)\n")
    out.append(f"_生成元: `{corpus['generated_from']}` / 実験数: {corpus['experiment_count']}_\n")
    out.append("> これは `synthesis_extract.py` の機械抽出素材。矛盾・接続の最終判断は人 / LLM が行う。\n")

    out.append("\n## (1) 現在地マップ\n")
    out.append(f"| {PREFIX} | 実験 | 状態 | 期間 | 未完 | 参照 | 要約 |")
    out.append("|---|---|---|---|---|---|---|")
    for r in m:
        badge = _STATUS_BADGE.get(r["status"], r["status"] or "?")
        refs = " ".join(f"{PREFIX}{x}" for x in r["refs"]) or "—"
        out.append(f"| {r['num']} | `{r['experiment_id']}` | {badge} | {r['period']} | "
                   f"{r['open']} | {refs} | {r['summary']} |")

    out.append("\n## (2) 矛盾候補の材料 — 実験間参照エッジ\n")
    out.append("_双方向(reciprocal)参照はクラスタの核。要約を突き合わせて矛盾/接続を判断する。_\n")
    out.append("| From | To | 回数 | 双方向 | From 要約 | To 要約 |")
    out.append("|---|---|---|---|---|---|")
    for e in links:
        recip = "✅" if e["reciprocal"] else ""
        to = f"{PREFIX}{e['to']}" + ("" if e["to_known"] else " (外部)")
        out.append(f"| {PREFIX}{e['from']} | {to} | {e['count']} | {recip} | "
                   f"{e['from_summary']} | {e['to_summary'] or '—'} |")

    out.append("\n## (2b) topical 近接 — 装置名・技術語の共有(参照リンク非依存)\n")
    out.append("_★=topical のみ(実験 ID の相互参照が無いのに語彙が近い=参照グラフの見落とし候補)。_\n")
    out.append("| A | B | score | 新規 | 共有語 |")
    out.append("|---|---|---|---|---|")
    for e in topical["edges"][:30]:
        star = "★" if e["topical_only"] else ""
        out.append(f"| {PREFIX}{e['a']} | {PREFIX}{e['b']} | {e['score']} | {star} | "
                   f"{', '.join(e['shared'])} |")

    out.append("\n## (3) 未昇格バックログ\n")
    out.append(f"\n### 優先アクション({len(bl['priority_actions'])})\n")
    for a in bl["priority_actions"]:
        out.append(f"- **{PREFIX}{a['num']}** {a['text']}")
    out.append(f"\n### 派生チケット候補({len(bl['derived_ticket_candidates'])})\n")
    for a in bl["derived_ticket_candidates"]:
        refs = " ".join(f"{PREFIX}{x}" for x in a["refs"]) if a["refs"] else ""
        out.append(f"- {PREFIX}{a['num']}: {a['text']} {('→ ' + refs) if refs else ''}")
    out.append(f"\n### KB 未昇格の実験({len(bl['kb_unpromoted_experiments'])})\n")
    for k in bl["kb_unpromoted_experiments"]:
        out.append(f"- {PREFIX}{k['num']} `{k['experiment_id']}` — {k['kb_status']}: {k['note']}")
    out.append(f"\n### tips 在庫(KB 前段, {len(bl['tips_inventory'])})\n")
    for t in bl["tips_inventory"]:
        flag = " (KB 参照あり)" if t["promoted_ref"] else ""
        out.append(f"- `{t['file']}` [{t['kind']}] {t['title']}{flag}")

    out.append(f"\n### 全未完アクション({len(bl['open_actions'])})\n")
    for a in bl["open_actions"]:
        p = "⭐ " if a["priority"] else ""
        out.append(f"- {p}{PREFIX}{a['num']}: {a['text']}")
    return "\n".join(out) + "\n"


# --- ドライバ ----------------------------------------------------------------
def main(argv: list[str]) -> int:
    for stream in (sys.stdout, sys.stderr):
        try:
            stream.reconfigure(encoding="utf-8")  # type: ignore[attr-defined]
        except (AttributeError, ValueError):
            pass
    ap = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("experiments", nargs="?", help="experiments/ ディレクトリ")
    ap.add_argument("--markdown", action="store_true", help="3 ビューを Markdown 出力")
    ap.add_argument("--out", help="JSON + Markdown をこのディレクトリに書き出す")
    args = ap.parse_args(argv)

    if args.experiments:
        exp_dir = Path(args.experiments)
    else:
        # install モデルでは tools/ が harness への symlink。cwd(=記録層)基準で解決する。
        exp_dir = Path.cwd() / "experiments"
    if not exp_dir.is_dir():
        print(f"experiments ディレクトリが見つからない: {exp_dir}", file=sys.stderr)
        return 2

    corpus = build_corpus(exp_dir)
    corpus["views"] = {
        "map": view_map(corpus),
        "links": view_links(corpus),
        "backlog": view_backlog(corpus),
        "topical": synthesis_topical.build_topical(exp_dir, corpus["experiments"]),
    }

    for w in corpus["warnings"]:
        print(f"NOTE: {w}", file=sys.stderr)

    if args.out:
        out_dir = Path(args.out)
        out_dir.mkdir(parents=True, exist_ok=True)
        (out_dir / "synthesis.json").write_text(
            json.dumps(corpus, ensure_ascii=False, indent=2), encoding="utf-8")
        (out_dir / "state-of-the-lab.md").write_text(render_markdown(corpus), encoding="utf-8")
        print(f"書き出し: {out_dir/'synthesis.json'} / {out_dir/'state-of-the-lab.md'}")
        return 0

    if args.markdown:
        print(render_markdown(corpus))
    else:
        print(json.dumps(corpus, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
