#!/usr/bin/env python3
"""網羅ゲート — 調査が「書かなかったこと」の穴を持たないかを判定する.

受入ゲート(dr_gate.py)が**書いた主張の正しさ**を見るのに対し、こちらは
**調べなかった下位問い・探さなかった反証・孫引きを独立2本と数える誤り**を見る。
調査(ディープリサーチ)は両方を通して初めて受入可とする。

規約の正本: docs/conventions/research.md「網羅ゲート」
スキーマ:   tools/dr/research_schema.md

判定ルール:
  K1 決着の接地   : status=closed の下位問いは decision_driving の主張を1件以上持つ
  K2 独立ソース   : closed は derived_from で畳んだ後の独立ソースを
                    min_independent_sources(既定 2)本以上持つ
  K3 反証の痕跡   : closed は stance=refutes/neutral の主張、または
                    その問い向けの decision=rejected(理由つき)の探索記録を持つ
  K4 参照整合     : question_id / source_id / derived_from が実在の台帳行に解決する
  K5 未決着の開示 : open / abandoned の下位問いが散文に現れる(--prose 指定時のみ)

使い方:
    python3 tools/dr/dr_coverage.py <path>/questions.jsonl
    python3 tools/dr/dr_coverage.py <path>/questions.jsonl --prose <report>.md

終了コード: 0 = 受入可(PASS) / 1 = 差し戻し(FAIL) / 2 = ファイル無し or スキーマエラー
"""
from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

from validate_ledger import load_and_validate
from validate_research import load_questions, load_sources

DEFAULT_MIN_INDEPENDENT = 2


def fold_to_root(source_id: str, by_id: dict[str, dict]) -> str:
    """孫引きを原典まで畳む。独立本数は畳んだ後の root を数える。

    derived_from が台帳内の source_id ならさらに辿り、URL(台帳外の原典)なら
    その URL 文字列を root とする。循環は最初に戻った時点で打ち切る。
    """
    seen: set[str] = set()
    cur = source_id
    while cur in by_id and cur not in seen:
        seen.add(cur)
        parent = by_id[cur].get("derived_from")
        if not parent:
            return cur
        cur = parent
    return cur


def run_gate(
    questions: list[dict],
    claims: list[dict],
    sources: list[dict],
    prose: str | None,
) -> tuple[bool, list[str]]:
    """網羅判定。(pass?, レポート行) を返す。"""
    lines: list[str] = []
    failed = False

    q_by_id = {q["question_id"]: q for q in questions if q.get("question_id")}
    s_by_id = {s["source_id"]: s for s in sources if s.get("source_id")}

    closed = [q for q in questions if q.get("status") == "closed"]
    unresolved = [q for q in questions if q.get("status") in ("open", "abandoned")]

    def claims_of(qid: str) -> list[dict]:
        return [c for c in claims if c.get("question_id") == qid]

    def sources_of(qid: str) -> list[dict]:
        return [s for s in sources if qid in (s.get("question_ids") or [])]

    # --- K1: 決着の接地 ---
    lines.append("## K1 決着の接地(closed に判断駆動の主張があるか)")
    lines.append(f"  closed: {len(closed)} 件 / open+abandoned: {len(unresolved)} 件")
    k1_bad = [q for q in closed if not [c for c in claims_of(q["question_id"])
                                        if c.get("risk") == "decision_driving"]]
    if k1_bad:
        failed = True
        lines.append(f"  [FAIL] 判断駆動の主張が無い closed が {len(k1_bad)} 件:")
        for q in k1_bad:
            lines.append(f"    - {q['question_id']}: {q.get('question')}")
    elif closed:
        lines.append("  [OK] closed は全て decision_driving の主張に接地している")
    else:
        lines.append("  [--] closed な下位問いがまだ無い")

    # --- K2: 独立ソース(孫引きを畳んでから数える)---
    lines.append("## K2 独立ソース(孫引きを畳んだ本数)")
    for q in closed:
        qid = q["question_id"]
        need = q.get("min_independent_sources") or DEFAULT_MIN_INDEPENDENT
        adopted = [s for s in sources_of(qid) if s.get("decision") == "adopted"]
        roots = {fold_to_root(s["source_id"], s_by_id) for s in adopted if s.get("source_id")}
        vendor_only = adopted and all(s.get("tier") == "vendor" for s in adopted)
        if len(roots) < need:
            failed = True
            lines.append(
                f"  [FAIL] {qid}: 独立 {len(roots)} 本 < 必要 {need} 本 "
                f"(採用 {len(adopted)} 本を畳んだ結果)"
            )
        elif vendor_only:
            failed = True
            lines.append(f"  [FAIL] {qid}: 採用出典が vendor(利害関係者)のみ。独立ソースの裏づけが要る")
        else:
            lines.append(f"  [OK] {qid}: 独立 {len(roots)} 本 (>= {need})")
    if not closed:
        lines.append("  [--] 対象なし")

    # --- K3: 反証の痕跡 ---
    lines.append("## K3 反証の痕跡(支持証拠だけで閉じていないか)")
    for q in closed:
        qid = q["question_id"]
        counter_claims = [c for c in claims_of(qid) if c.get("stance") in ("refutes", "neutral")]
        counter_search = [
            s for s in sources_of(qid)
            if s.get("decision") == "rejected" and s.get("decision_reason")
        ]
        if counter_claims or counter_search:
            lines.append(
                f"  [OK] {qid}: 反証主張 {len(counter_claims)} 件 / 棄却記録 {len(counter_search)} 件"
            )
        else:
            failed = True
            lines.append(
                f"  [FAIL] {qid}: 反証側の痕跡が無い"
                "(stance=refutes/neutral の主張か、理由つき decision=rejected の探索記録が要る)"
            )
    if not closed:
        lines.append("  [--] 対象なし")

    # --- K4: 参照整合 ---
    lines.append("## K4 参照整合(ID が実在の台帳行に解決するか)")
    dangling: list[str] = []
    for c in claims:
        qid = c.get("question_id")
        if qid and qid not in q_by_id:
            dangling.append(f"claim {c.get('claim_id')}: question_id={qid} が questions.jsonl に無い")
        sid = c.get("source_id")
        if sid and sid not in s_by_id:
            dangling.append(f"claim {c.get('claim_id')}: source_id={sid} が sources.jsonl に無い")
    for s in sources:
        for qid in s.get("question_ids") or []:
            if qid not in q_by_id:
                dangling.append(f"source {s.get('source_id')}: question_ids の {qid} が解決しない")
        df = s.get("derived_from")
        # URL(台帳外の原典)は解決を要求しない。台帳内 ID のつもりの文字列だけ検査する。
        if df and "://" not in df and df not in s_by_id:
            dangling.append(f"source {s.get('source_id')}: derived_from={df} が解決しない")
    for q in questions:
        parent = q.get("parent")
        if parent and parent not in q_by_id:
            dangling.append(f"question {q.get('question_id')}: parent={parent} が解決しない")
    if dangling:
        failed = True
        lines.append(f"  [FAIL] 解決しない参照が {len(dangling)} 件:")
        lines.extend(f"    - {d}" for d in dangling)
    else:
        lines.append("  [OK] 全ての ID 参照が解決する")

    # --- K5: 未決着の開示(--prose 指定時のみ)---
    lines.append("## K5 未決着の開示(open / abandoned が散文に出ているか)")
    if prose is None:
        lines.append("  [--] --prose 未指定のためスキップ")
    elif not unresolved:
        lines.append("  [--] open / abandoned な下位問いが無い")
    else:
        missing = [q for q in unresolved
                   if not re.search(rf"(?<![A-Za-z0-9]){re.escape(q['question_id'])}(?![0-9])", prose)]
        if missing:
            failed = True
            lines.append(f"  [FAIL] 散文に現れない未決着の問いが {len(missing)} 件:")
            for q in missing:
                lines.append(f"    - {q['question_id']} ({q.get('status')}): {q.get('question')}")
            lines.append("    → REPORT.md / 一次記録に open question として書く(ID を添える)")
        else:
            lines.append(f"  [OK] 未決着 {len(unresolved)} 件は全て散文に現れる")

    return (not failed), lines


def _load_or_die(path: Path, loader, label: str) -> list[dict]:
    if not path.is_file():
        print(f"[FATAL] {label} が無い: {path}", file=sys.stderr)
        sys.exit(2)
    records, issues = loader(path)
    errors = [i for i in issues if i.level == "ERROR"]
    if errors:
        print(f"[FATAL] {label} にスキーマエラー。先に validate を通すこと:", file=sys.stderr)
        for i in errors:
            print(f"  {i}", file=sys.stderr)
        sys.exit(2)
    return records


def main() -> int:
    ap = argparse.ArgumentParser(description="網羅ゲート(調査)")
    ap.add_argument("questions", help="questions.jsonl へのパス")
    ap.add_argument("--claims", help="claims.jsonl(既定: questions.jsonl と同じディレクトリ)")
    ap.add_argument("--sources", help="sources.jsonl(既定: 同上)")
    ap.add_argument("--prose", help="散文レポート .md(K5 を有効にする)")
    args = ap.parse_args()

    qpath = Path(args.questions)
    if not qpath.is_file():
        print(f"[FATAL] ファイルが無い: {qpath}", file=sys.stderr)
        return 2
    base = qpath.parent
    cpath = Path(args.claims) if args.claims else base / "claims.jsonl"
    spath = Path(args.sources) if args.sources else base / "sources.jsonl"

    questions = _load_or_die(qpath, load_questions, "questions.jsonl")
    sources = _load_or_die(spath, load_sources, "sources.jsonl")
    claims = _load_or_die(cpath, load_and_validate, "claims.jsonl")

    prose = None
    if args.prose:
        ppath = Path(args.prose)
        if not ppath.is_file():
            print(f"[FATAL] 散文が無い: {ppath}", file=sys.stderr)
            return 2
        prose = ppath.read_text(encoding="utf-8")

    passed, report = run_gate(questions, claims, sources, prose)
    print(f"# 網羅ゲート: {qpath.name}")
    print("\n".join(report))
    print("\n=== 判定:", "[PASS] 網羅は受入可" if passed else "[FAIL] 差し戻し", "===")
    if passed:
        print("次: python3 tools/dr/dr_gate.py <台帳>/claims.jsonl (受入ゲート = 書いた数値の正しさ)")
    return 0 if passed else 1


if __name__ == "__main__":
    sys.exit(main())
