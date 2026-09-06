#!/usr/bin/env python3
"""exp_artifact.py — 実験を「読み物 Artifact」にするための抽出と検査(依存なし)

`/exp-artifact` の機械側。**執筆者(LLM)が一次記録を手で書き写さないため**にある。

E013 で手作業で1本作ったとき、撤回台帳16行を REPORT.md の表から手で転記した。
転記は写し間違いを生むし、フロントマターに機械可読な撤回記録(`corrects` /
`retraction_type` / `discovered_by`)が既にあるのに使っていなかった。
正本は docs/conventions/reporting.md「改訂・撤回の記録」で、集計側は
tools/retractions.py。本ツールは同じ入力を **1実験ぶんだけ** 記事の骨組みとして出す。

2 つのサブコマンド:

  skeleton — 実験から記事の骨組みを JSON で出す(散文は書かない)。
             メタ・一次記録の一覧・撤回台帳・図の在庫・ゲートの有無。
  check    — 組み上げた HTML を実験と突き合わせる。
             (a) 存在しない一次記録を引いていないか(捏造引用の検出)
             (b) 各 <figure> が一次記録の出典を持つか(追跡可能性)

check は「数値が正しいか」は見ない(それは dr_gate / report-checksum の役目
= AGENTS.md「1 機能 = 1 権威」)。見るのは **その数字を読者が辿れるか** だけで、
tools/check_untraceable_numbers.py と同じ「アンカー近接」の考え方を、
markdown ではなく派生成果物(HTML)の側に当てたもの。

使い方
------
  python3 tools/exp_artifact.py skeleton experiments/E013_multi-agent-collaboration
  python3 tools/exp_artifact.py check    experiments/E013_multi-agent-collaboration article.html
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from report_meta import parse_frontmatter  # noqa: E402

# 一次記録の参照。<実験ID>-R### が正規形(正本: reporting.md「レポート命名・R 番号」)。
RECORD_RE = re.compile(r"\bE\d{3}-R\d{3}\b")
# 記事本文では実験IDを省いて R033 と書くことが多いので、そちらも拾う。
SHORT_RE = re.compile(r"(?<![-\w])R\d{3}\b")
FIGURE_RE = re.compile(r"<figure\b.*?</figure>", re.S | re.I)
# 一次記録のファイル名: <実験ID>-R###_YYYYMMDD_<slug>_<種別>.md
FNAME_RE = re.compile(r"^(?P<id>E\d{3}-R\d{3})_(?P<date>\d{8})_(?P<slug>.+)_(?P<type>[^_]+)\.md$")


def _first_heading(path: Path, rid: str) -> str:
    """`# <id> <題>` の題だけを返す。無ければ空文字。"""
    for line in path.read_text(encoding="utf-8").splitlines():
        if line.startswith("# "):
            return line[2:].strip().removeprefix(rid).strip()
    return ""


def collect_records(exp: Path) -> list[dict]:
    """reports/*.md を一次記録の一覧にする(INDEX.md と台帳 .jsonl は除く)。"""
    out: list[dict] = []
    for md in sorted((exp / "reports").glob("*.md")):
        if md.name == "INDEX.md":
            continue
        m = FNAME_RE.match(md.name)
        try:
            meta = parse_frontmatter(md) or {}
        except Exception as e:  # 壊れたフロントマターは report_meta 側が報告する
            meta = {"_parse_error": str(e)}
        rid = str(meta.get("report_id") or (m.group("id") if m else md.stem))
        corrects = meta.get("corrects")
        if isinstance(corrects, list):
            corrects = ", ".join(corrects)
        out.append({
            "id": rid,
            "date": (m.group("date") if m else ""),
            "type": str(meta.get("type") or (m.group("type") if m else "")),
            "status": str(meta.get("status") or ""),
            "title": _first_heading(md, rid),
            "summary": str(meta.get("summary") or ""),
            "corrects": str(corrects) if corrects else None,
            "retraction_type": meta.get("retraction_type"),
            "discovered_by": meta.get("discovered_by"),
            "superseded_by": meta.get("superseded_by"),
            "path": str(md.relative_to(exp.parent.parent)) if exp.is_absolute() else str(md),
        })
    return out


def collect_figures(exp: Path) -> list[dict]:
    """_generated/ 配下の図。git には入らない(正本: figures-regen.md)ので、
    存在しなければ regenerate.sh を先に回す必要があることを呼び出し側に知らせる。"""
    gen = exp / "_generated"
    figs = []
    if gen.is_dir():
        for p in sorted(gen.rglob("*")):
            if p.suffix.lower() in {".png", ".svg", ".jpg", ".jpeg", ".webp"}:
                figs.append({"path": str(p.relative_to(exp)), "bytes": p.stat().st_size})
    return figs


def skeleton(exp: Path) -> dict:
    report = exp / "REPORT.md"
    meta = (parse_frontmatter(report) or {}) if report.exists() else {}
    title = ""
    if report.exists():
        for line in report.read_text(encoding="utf-8").splitlines():
            if line.startswith("# "):
                title = line[2:].strip()
                break
    records = collect_records(exp)
    retractions = [r for r in records if r["corrects"]]
    figs = collect_figures(exp)
    return {
        "experiment": {
            "id": str(meta.get("experiment_id") or exp.name),
            "dir": exp.name,
            "title": title,
            "status": str(meta.get("status") or ""),
            "period_start": str(meta.get("period_start") or ""),
            "period_end": str(meta.get("period_end") or ""),
            "summary": str(meta.get("summary") or ""),
        },
        "counts": {
            "records": len(records),
            "retractions": len(retractions),
            "figures": len(figs),
        },
        "records": records,
        "retractions": retractions,
        "figures": figs,
        "gates": {
            # 台帳のある実験は dr_gate を共有前ゲートに使える(正本: reporting.md
            # 「いつ検証するか — 共有前ゲート」)。無ければ数値を1件ずつ潰す。
            "dr_gate": (exp / ".dr-gate").exists(),
            "numbers_gate": (exp / ".numbers-gate").exists(),
            "claims_ledger": (exp / "reports" / "claims.jsonl").exists(),
        },
        "regenerate_sh": (exp / "regenerate.sh").exists(),
    }


def find_problems(html: str, known_full: set[str], known_short: set[str]) -> list[str]:
    """HTML と実在する一次記録 ID から違反を列挙する(純関数 — selftest はここを叩く)。"""
    problems: list[str] = []

    # (a) 存在しない一次記録を引いていないか。
    #     E013 自身の知見 —— 逐語引用65件のうち3件が出典に存在しない合成文だった。
    #     派生成果物でも同じことが起きるので、機械で弾く。
    for cited in sorted(set(RECORD_RE.findall(html))):
        if cited not in known_full:
            problems.append(f"存在しない一次記録を参照: {cited}")
    for cited in sorted(set(SHORT_RE.findall(html))):
        if cited not in known_short:
            problems.append(f"存在しない一次記録を参照: {cited}")

    # (b) 各 <figure> は一次記録の出典を持つか。
    for i, fig in enumerate(FIGURE_RE.findall(html), 1):
        if not (RECORD_RE.search(fig) or SHORT_RE.search(fig)):
            head = re.sub(r"<[^>]+>", " ", fig)[:60].strip()
            problems.append(f"figure {i} に出典(一次記録 ID)が無い: {head!r}")
    return problems


def check(exp: Path, html_path: Path) -> int:
    html = html_path.read_text(encoding="utf-8")
    records = collect_records(exp)
    known_full = {r["id"] for r in records}
    known_short = {r["id"].split("-")[-1] for r in records}

    problems = find_problems(html, known_full, known_short)
    figures = FIGURE_RE.findall(html)

    print(f"実験 {exp.name}: 一次記録 {len(records)} 本 / 記事の図 {len(figures)} 点", flush=True)
    if problems:
        print(f"\nexp-artifact check: FAIL ({len(problems)} 件)", file=sys.stderr)
        for p in problems:
            print(f"  - {p}", file=sys.stderr)
        return 1
    print("exp-artifact check: PASS (引用は実在し、図はすべて出典を持つ)")
    return 0


# --- 回帰テスト -------------------------------------------------------------
# 「道具を作ったら必ず回帰テストを添える」(E013 の昇格候補)。歯止めが一度も
# 機械検査されていなかった E013-R014 の型を、この道具自身で踏まないための最低限。
FIXTURES: list[tuple[str, str, int]] = [
    ("実在の引用と出典つきの図は通る",
     '<p>R012 の再現。</p><figure><h4>図</h4><span>出典 E013-R031 §2</span></figure>', 0),
    ("実験IDを省いた出典も通る",
     '<figure><h4>図</h4><span>出典 R031</span></figure>', 0),
    ("存在しない一次記録は落ちる(捏造引用)",
     '<figure><h4>図</h4><span>出典 R099</span></figure>', 1),
    ("存在しない完全形の一次記録も落ちる",
     '<p>E013-R404 による。</p>', 1),
    ("出典の無い図は落ちる",
     '<figure><h4>図</h4><p>数字だけ 42%</p></figure>', 1),
    ("図が複数あれば出典の無いものだけ落ちる",
     '<figure><span>R012</span></figure><figure><p>なし</p></figure>', 1),
    ("figure の外の散文は出典を要求しない",
     '<p>変形は対照側からしか出ていない。</p>', 0),
]


def selftest() -> int:
    known_full = {"E013-R012", "E013-R031"}
    known_short = {"R012", "R031"}
    failed = 0
    for name, html, want in FIXTURES:
        got = len(find_problems(html, known_full, known_short))
        ok = (got > 0) == (want > 0)
        print(f"  [{'ok' if ok else 'NG'}] {name}" + ("" if ok else f" (期待 {want} 件相当 / 実際 {got} 件)"))
        failed += 0 if ok else 1
    print(f"exp-artifact selftest: {'PASS' if not failed else 'FAIL'} "
          f"({len(FIXTURES) - failed}/{len(FIXTURES)})")
    return 1 if failed else 0


def main(argv: list[str]) -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)
    s = sub.add_parser("skeleton", help="記事の骨組みを JSON で出す")
    s.add_argument("experiment", help="実験ディレクトリ (experiments/E###_<topic>)")
    c = sub.add_parser("check", help="組み上げた HTML を実験と突き合わせる")
    c.add_argument("experiment", help="実験ディレクトリ")
    c.add_argument("html", help="公開前の HTML")
    sub.add_parser("selftest", help="check の判定ロジックの回帰テスト")
    a = ap.parse_args(argv)

    if a.cmd == "selftest":
        return selftest()

    exp = Path(a.experiment).resolve()
    if not exp.is_dir():
        print(f"実験ディレクトリが無い: {exp}", file=sys.stderr)
        return 2

    if a.cmd == "skeleton":
        print(json.dumps(skeleton(exp), ensure_ascii=False, indent=2))
        return 0

    html = Path(a.html)
    if not html.is_file():
        print(f"HTML が無い: {html}", file=sys.stderr)
        return 2
    return check(exp, html)


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
