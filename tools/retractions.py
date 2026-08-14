#!/usr/bin/env python3
"""retractions.py — 撤回(retraction)の横断集計を docs/retractions.md に生成する(依存なし)

二重帳簿の生成側。入力は 2 つで、どちらも人が書いた一次情報:

  1. **生きた記録** — experiments/<id>/reports/*.md のフロントマター
     (`corrects` / `retraction_type` / `discovered_by`)。書式の正本と検査は
     docs/conventions/reporting.md「改訂・撤回の記録」/ tools/report_meta.py。
  2. **ブートストラップ** — docs/retractions-bootstrap.jsonl
     規約導入(2026-08-06)より前の撤回を、コミット本文から遡って分類した凍結台帳。
     初期分布を作るためだけのもので、**追記しない**(以後は 1 の経路で貯まる)。

主要指標は件数ではなく **発見経路(discovered_by)の内訳**。撤回が増えること自体は
悪ではなく、「人間の指摘に依存し続けているか」が独立検証層の実力を映す。

使い方
------
  python tools/retractions.py           # docs/retractions.md を再生成
  python tools/retractions.py --check   # 差分があれば exit 1(生成し忘れ検出)

pre-commit の関門にはしない(生成し忘れの実害が小さいため。週次 watch で拾う)。
"""
from __future__ import annotations

import argparse
import json
import sys
from collections import Counter, defaultdict
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from report_meta import (  # noqa: E402
    DISCOVERED_BY,
    RETRACTION_TYPES,
    parse_frontmatter,
)

MARKER = "retractions"
UNKNOWN = "(未分類)"


class Entry:
    """1 件の撤回。生きた記録とブートストラップを同じ形に揃える。"""

    def __init__(self, date, experiment, ref, corrects, rtype, discovered, note, origin):
        self.date = date or ""
        self.experiment = experiment
        self.ref = ref
        self.corrects = corrects
        self.rtype = rtype or UNKNOWN
        self.discovered = discovered or UNKNOWN
        self.note = note or ""
        self.origin = origin  # "frontmatter" | "bootstrap"

    @property
    def month(self) -> str:
        return self.date[:7] if len(self.date) >= 7 else "(不明)"


def collect_frontmatter(exp_dir: Path) -> list[Entry]:
    out = []
    for report in sorted(exp_dir.glob("*/reports/*.md")):
        if report.name == "INDEX.md" or report.parent.parent.name.startswith("_"):
            continue
        try:
            meta = parse_frontmatter(report)
        except Exception:
            continue  # 壊れたフロントマターは report_meta 側が報告する
        if not meta or not meta.get("corrects"):
            continue
        corrects = meta["corrects"]
        if isinstance(corrects, list):
            corrects = ", ".join(corrects)
        out.append(
            Entry(
                date=str(meta.get("created") or ""),
                experiment=report.parent.parent.name,
                ref=str(meta.get("report_id") or report.name),
                corrects=str(corrects),
                rtype=meta.get("retraction_type"),
                discovered=meta.get("discovered_by"),
                note=str(meta.get("summary") or "")[:80],
                origin="frontmatter",
            )
        )
    return out


def collect_bootstrap(path: Path) -> list[Entry]:
    if not path.exists():
        return []
    out = []
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("//"):
            continue
        d = json.loads(line)
        out.append(
            Entry(
                date=d.get("date", ""),
                experiment=d.get("experiment", ""),
                ref=d.get("commit", ""),
                corrects=d.get("corrects", ""),
                rtype=d.get("retraction_type"),
                discovered=d.get("discovered_by"),
                note=d.get("note", ""),
                origin="bootstrap",
            )
        )
    return out


def render(entries: list[Entry]) -> list[str]:
    lines: list[str] = []
    total = len(entries)
    if not total:
        return ["まだ 1 件も記録されていない。", "",
                "**これは「撤回が無い」ではなく「記録が回っていない」と読むこと。**"]

    by_type = Counter(e.rtype for e in entries)
    by_disc = Counter(e.discovered for e in entries)
    cross = defaultdict(Counter)
    for e in entries:
        cross[e.rtype][e.discovered] += 1

    # --- 発見経路(主要指標) ---
    lines += ["### 発見経路の内訳(主要指標)", ""]
    lines += ["| 発見経路 | 件数 | 割合 |", "|---|---:|---:|"]
    for key in ["user-sme", "self", "independent-audit", UNKNOWN]:
        n = by_disc.get(key, 0)
        if n:
            lines.append(f"| `{key}` | {n} | {100 * n / total:.0f}% |")
    lines += ["", f"合計 **{total}** 件。"
              "`user-sme` が高いほど、誤りの検出を人間の目に依存している"
              "(= 独立検証層がまだ育っていない)。", ""]

    # --- 類型 × 発見経路 ---
    disc_cols = [k for k in ["self", "user-sme", "independent-audit", UNKNOWN]
                 if any(cross[t].get(k) for t in cross)]
    lines += ["### 類型別(× 発見経路)", ""]
    lines += ["| 類型 | 件数 | " + " | ".join(f"`{c}`" for c in disc_cols) + " |",
              "|---|---:|" + "---:|" * len(disc_cols)]
    for rtype, n in by_type.most_common():
        cells = " | ".join(str(cross[rtype].get(c, 0) or "") for c in disc_cols)
        lines.append(f"| `{rtype}` | {n} | {cells} |")
    lines += ["", "上位の類型が、次に事前チェックへ変換する候補("
              "正本: docs/conventions/reporting.md「改訂・撤回の記録」)。", ""]

    # --- 時系列 ---
    by_month = Counter(e.month for e in entries)
    lines += ["### 月別", "", "| 月 | 件数 |", "|---|---:|"]
    for m in sorted(by_month):
        lines.append(f"| {m} | {by_month[m]} |")
    lines.append("")

    # --- 明細 ---
    lines += ["### 明細", "",
              "| 日付 | 実験 | 記録 | 訂正対象 | 類型 | 発見経路 | 出所 |",
              "|---|---|---|---|---|---|---|"]
    for e in sorted(entries, key=lambda x: (x.date, x.ref), reverse=True):
        lines.append(
            f"| {e.date or '—'} | {e.experiment} | `{e.ref}` | `{e.corrects or '—'}` "
            f"| `{e.rtype}` | `{e.discovered}` | {e.origin} |"
        )
    lines.append("")

    # --- 衛生チェック(語彙外・未分類) ---
    stray_t = sorted({e.rtype for e in entries} - RETRACTION_TYPES - {UNKNOWN})
    stray_d = sorted({e.discovered for e in entries} - DISCOVERED_BY - {UNKNOWN})
    if stray_t or stray_d:
        lines += ["### ⚠ 語彙外の値", ""]
        for v in stray_t:
            lines.append(f"- retraction_type: `{v}`")
        for v in stray_d:
            lines.append(f"- discovered_by: `{v}`")
        lines.append("")
    if by_type.get(UNKNOWN) or by_disc.get(UNKNOWN):
        lines += [f"> {UNKNOWN} が残っている = 記入漏れ。"
                  "類型が付かない撤回は集計に効かない。", ""]
    return lines


SCAFFOLD = """# 撤回(retraction)の横断集計

> **この表は生成物**。`python tools/retractions.py` が各実験の
> `reports/*.md` のフロントマター(`corrects` / `retraction_type` / `discovered_by`)と
> `docs/retractions-bootstrap.jsonl` から組む。**手で編集しない**。
> 書式・統制語彙の正本は `docs/conventions/reporting.md`「改訂・撤回の記録」。

<!-- gen:{marker}:start -->
<!-- gen:{marker}:end -->
"""


def apply_block(path: Path, body: list[str], check: bool) -> bool:
    start, end = f"<!-- gen:{MARKER}:start -->", f"<!-- gen:{MARKER}:end -->"
    if not path.exists():
        # 記録層(ノート)には最初この文書が無い。生成物なので雛形ごと作ってよい。
        if check:
            return True
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(SCAFFOLD.format(marker=MARKER), encoding="utf-8")
    text = path.read_text(encoding="utf-8")
    if start not in text or end not in text:
        raise SystemExit(f"{path}: マーカ {start} / {end} が無い")
    pre, rest = text.split(start, 1)
    _, post = rest.split(end, 1)
    new_text = pre + start + "\n\n" + "\n".join(body).rstrip() + "\n\n" + end + post
    if new_text == text:
        return False
    if not check:
        path.write_text(new_text, encoding="utf-8")
    return True


def main(argv: list[str]) -> int:
    for stream in (sys.stdout, sys.stderr):
        try:
            stream.reconfigure(encoding="utf-8")  # type: ignore[attr-defined]
        except (AttributeError, ValueError):
            pass
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--check", action="store_true", help="差分があれば exit 1(生成し忘れ検出)")
    args = ap.parse_args(argv)

    # install モデルでは tools/ が harness への symlink。cwd(=記録層)基準で解決する。
    root = Path.cwd()
    entries = collect_frontmatter(root / "experiments")
    entries += collect_bootstrap(root / "docs" / "retractions-bootstrap.jsonl")
    out = root / "docs" / "retractions.md"
    changed = apply_block(out, render(entries), args.check)

    if args.check:
        if changed:
            print(f"--check: {out} が古い(python tools/retractions.py で再生成)")
            return 1
        print(f"--check: {out} は最新({len(entries)} 件)")
        return 0
    print(f"{'更新' if changed else '変更なし'}: {out}({len(entries)} 件)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
