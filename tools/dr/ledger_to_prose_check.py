#!/usr/bin/env python3
"""散文↔台帳の追跡検査.

検証可能なレポートは、散文中の各数値・断定に `(claim:cNNN)` か `[[cNNN]]` の
マーカで台帳行を紐づける。
本スクリプトは散文側の citation_error_rate を測り、次を検査する:

  E1 壊れた参照 : 散文が台帳に無い claim_id を参照
  E2 未検証参照 : 散文が verified でない主張を確定として参照
                  (段落に「要確認/暫定/未検証」等の明記がある場合、および補足主張を
                   抜き取りで非選定にした場合は W3 に降格 — 正直なラベル付けを罰しない)
  E3 数値ドリフト: マーカ直前の数値が、参照先台帳行の value_num と食い違う
                  (例: 散文「8 µm (claim:c001)」だが台帳は 8.2 µm)
  W1 未追跡数値 : 数値+単位がどのマーカからも離れている(出典紐づけ漏れの疑い)
  W2 未使用主張 : 台帳の decision_driving が散文から一度も参照されない

使い方:
    python3 tools/dr/ledger_to_prose_check.py <prose.md> <claims.jsonl>

終了コード: 0 = ERROR なし / 1 = ERROR あり / 2 = ファイル無し等
dr_gate の R3(台帳内引用整合)に対し、本スクリプトは散文側を見る。
"""
from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

from validate_ledger import load_and_validate
from numeric_compare import compare, _decimals_of

MARKER_RE = re.compile(r"\(claim:(c\d+)\)|\[\[(c\d+)\]\]")
# 数値+任意の単位(measurement っぽいものだけ拾う)
NUM_UNIT_RE = re.compile(
    r"([-+]?\d[\d,]*\.?\d*)\s*(%|g|kg|mg|µg|µL|uL|mL|L|µm|um|mm|nm|JPY|円|V|h|min|s|℃)?",
)


def _num_before(text: str, pos: int, window: int = 60):
    """pos の手前 window 文字から、最後に出る数値(+単位)を返す。無ければ None。"""
    seg = text[max(0, pos - window):pos]
    last = None
    for m in NUM_UNIT_RE.finditer(seg):
        raw = m.group(1)
        if not any(ch.isdigit() for ch in raw):
            continue
        last = (raw, (m.group(2) or "").strip())
    if not last:
        return None
    raw, unit = last
    try:
        val = float(raw.replace(",", ""))
    except ValueError:
        return None
    return val, unit, raw


# 散文が「確定ではない」と明記しているかを判定する語。reporting.md「事実と仮説を分ける」の
# 語頭ラベル(確定 / 仮説 / 暫定値(要再測) / 要確認)と、検証状態の明示表現に合わせる。
HEDGE_WORDS = ("要確認", "暫定", "未検証", "未了", "仮説", "unverified", "unreachable")


def _is_hedged(prose: str, pos: int) -> bool:
    """マーカ位置を含む段落に「確定ではない」旨の明記があるか。

    段落 = 空行で区切られた塊。段落単位で見るのは、語頭ラベル(『**要確認:** …』)が
    その段落全体に掛かる書き方を規約が採っているため(行単位だと箇条書きの2行目以降を
    取りこぼす)。
    """
    start = prose.rfind("\n\n", 0, pos) + 2
    end = prose.find("\n\n", pos)
    if end == -1:
        end = len(prose)
    para = prose[start:end]
    return any(w in para for w in HEDGE_WORDS)


def check(prose: str, by_id: dict[str, dict]) -> tuple[list[str], list[str], dict]:
    errors: list[str] = []
    warns: list[str] = []
    refs: list[str] = []

    for m in MARKER_RE.finditer(prose):
        cid = m.group(1) or m.group(2)
        refs.append(cid)
        claim = by_id.get(cid)
        if claim is None:
            errors.append(f"[E1] 壊れた参照: 台帳に無い {cid}")
            continue
        verification = claim.get("verification") or {}
        status = verification.get("status")
        if status != "verified":
            # 規約(reporting.md「いつ検証するか」)は「潰せなかった数値は成果物から落とすか
            # 『暫定』と明記する」を許している。散文がその明記をしている場合、または
            # 補足主張を抜き取りで意図的に検証対象外にした場合は、E2(差し戻し)ではなく
            # W3(注意)に落とす — さもないと「正直にラベルを付けた散文」が
            # 「ラベルを外した散文」より強く罰せられ、ラベルを外す誘因が生まれる。
            if _is_hedged(prose, m.start()):
                warns.append(
                    f"[W3] 未検証参照(暫定と明記あり): {cid} (status={status})"
                )
            elif verification.get("method") == "sampled-skip":
                warns.append(
                    f"[W3] 未検証参照(抜き取りで非選定): {cid} (status={status})"
                )
            else:
                errors.append(
                    f"[E2] 未検証参照: {cid} を確定として引用(status={status})"
                )
        # E3 数値ドリフト
        found = _num_before(prose, m.start())
        vnum = claim.get("value_num")
        if found and isinstance(vnum, (int, float)) and not isinstance(vnum, bool):
            pval, punit, praw = found
            decimals = _decimals_of(praw, pval)
            ok, _, detail = compare(pval, float(vnum), decimals)
            if not ok:
                errors.append(
                    f"[E3] 数値ドリフト: 散文 {praw}{punit} vs 台帳 {cid}={vnum}{claim.get('unit') or ''} ({detail})"
                )

    # W1 未追跡数値: マーカから遠い measurement
    marker_spans = [m.span() for m in MARKER_RE.finditer(prose)]

    def near_marker(pos: int, window: int = 60) -> bool:
        return any(abs(pos - s[0]) <= window or abs(pos - s[1]) <= window for s in marker_spans)

    for m in NUM_UNIT_RE.finditer(prose):
        if not m.group(2):  # 単位が無い数値は measurement と見なさない(誤検出抑制)
            continue
        if not any(ch.isdigit() for ch in m.group(1)):
            continue
        if not near_marker(m.start()):
            warns.append(f"[W1] 未追跡数値: '{m.group(1)}{m.group(2)}'(近傍に claim マーカ無し)")

    # W2 未使用の decision_driving
    referenced = set(refs)
    for cid, claim in by_id.items():
        if claim.get("risk") == "decision_driving" and cid not in referenced:
            warns.append(f"[W2] 未使用の判断駆動主張: {cid} {claim.get('subject')} / {claim.get('attribute')}")

    rate_total = len(refs)
    rate_bad = len([e for e in errors if e.startswith(("[E1]", "[E2]", "[E3]"))])
    stats = {"refs": rate_total, "bad": rate_bad,
             "rate": (rate_bad / rate_total) if rate_total else 0.0}
    return errors, warns, stats


def main() -> int:
    ap = argparse.ArgumentParser(description="散文↔台帳の追跡検査(R003 A1)")
    ap.add_argument("prose", help="散文 markdown へのパス")
    ap.add_argument("ledger", help="claims.jsonl へのパス")
    ap.add_argument("--quiet", action="store_true", help="WARN を抑制")
    args = ap.parse_args()

    prose_path, ledger_path = Path(args.prose), Path(args.ledger)
    for p in (prose_path, ledger_path):
        if not p.is_file():
            print(f"[FATAL] ファイルが無い: {p}", file=sys.stderr)
            return 2

    records, issues = load_and_validate(ledger_path)
    if [i for i in issues if i.level == "ERROR"]:
        print("[FATAL] 台帳にスキーマエラー。先に validate_ledger を通すこと。")
        return 2
    by_id = {r.get("claim_id"): r for r in records}

    errors, warns, stats = check(prose_path.read_text(encoding="utf-8"), by_id)
    for e in errors:
        print(e)
    if not args.quiet:
        for w in warns:
            print(w)

    print(f"\n# ledger_to_prose_check: {prose_path.name}")
    print(f"  参照マーカ {stats['refs']} 件 / 散文側 citation_error_rate = "
          f"{stats['rate']:.1%} ({stats['bad']}/{stats['refs']})")
    print(f"  ERROR {len(errors)} / WARN {len(warns)}")
    if errors:
        print("[FAIL] 散文と台帳の追跡に破れあり。")
        return 1
    print("[OK] 散文の参照は全て検証済み台帳行に追跡可能。")
    return 0


if __name__ == "__main__":
    sys.exit(main())
