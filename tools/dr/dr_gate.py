#!/usr/bin/env python3
"""受入ゲート — claims.jsonl が「検証済みで受入可」かを判定する.

外部の受入検査ゲート。
**まだ hook には繋がない**(全セッションで発火し事故るため。tools/dr/README.md 参照)。
人が手動で実行し、検証結果を検証する。

判定ルール:
  R1 判断駆動の全数検証  : risk=decision_driving の主張は全て verification.status=verified
  R2 不良率(AQL)        : 検証を試みた中での refuted 率。decision_driving の refuted は即 FAIL、
                           supporting は AQL 閾値(--aql, 既定 6.5%)超で FAIL
  R3 引用整合(citation) : decision_driving の fact は source_url+verbatim_quote 必須。
                           citation_error_rate(欠落/不正の割合)も算出(R003 A1)

使い方:
    python3 tools/dr/dr_gate.py <path>/claims.jsonl [--aql 0.065]

終了コード: 0 = 受入可(PASS) / 1 = 差し戻し(FAIL) / 2 = ファイル無し or スキーマエラー
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

# 同ディレクトリの validate_ledger を再利用(python3 tools/dr/dr_gate.py で sys.path[0]=tools/dr)
from validate_ledger import load_and_validate


def run_gate(records: list[dict], aql: float) -> tuple[bool, list[str]]:
    """受入判定。(pass?, レポート行) を返す。"""
    lines: list[str] = []
    failed = False

    decision = [r for r in records if r.get("risk") == "decision_driving"]
    supporting = [r for r in records if r.get("risk") == "supporting"]

    def status_of(r: dict) -> str:
        return (r.get("verification") or {}).get("status", "unverified")

    # --- R1: 判断駆動は全数 verified ---
    dd_unverified = [r for r in decision if status_of(r) not in ("verified", "refuted")]
    dd_refuted = [r for r in decision if status_of(r) == "refuted"]
    lines.append("## R1 判断駆動の全数検証")
    lines.append(f"  decision_driving 主張: {len(decision)} 件")
    if dd_unverified:
        failed = True
        lines.append(f"  [FAIL] 未検証/未到達が {len(dd_unverified)} 件:")
        for r in dd_unverified:
            lines.append(
                f"    - {r.get('claim_id')} {r.get('subject')} / "
                f"{r.get('attribute')} = {r.get('value_raw')} (status={status_of(r)})"
            )
    else:
        lines.append("  [OK] decision_driving は全て検証試行済み")

    # --- R2: 不良率(refuted) ---
    lines.append("## R2 不良率(AQL)")
    if dd_refuted:
        failed = True
        lines.append(f"  [FAIL] decision_driving に refuted が {len(dd_refuted)} 件(0 が必須):")
        for r in dd_refuted:
            note = (r.get("verification") or {}).get("verdict_note") or "(理由未記載)"
            lines.append(
                f"    - {r.get('claim_id')} {r.get('subject')} / {r.get('attribute')}: {note}"
            )
    else:
        lines.append("  [OK] decision_driving に refuted なし")

    sup_attempted = [r for r in supporting if status_of(r) in ("verified", "refuted")]
    sup_refuted = [r for r in supporting if status_of(r) == "refuted"]
    if sup_attempted:
        rate = len(sup_refuted) / len(sup_attempted)
        verdict = "FAIL" if rate > aql else "OK"
        if verdict == "FAIL":
            failed = True
        lines.append(
            f"  [{verdict}] supporting 不良率 {rate:.1%} "
            f"({len(sup_refuted)}/{len(sup_attempted)}) vs AQL {aql:.1%}"
        )
    else:
        lines.append("  [--] supporting は検証試行なし(抜き取りは Phase 2)")

    # --- R3: 引用整合 / citation_error_rate(R003 A1)---
    lines.append("## R3 引用整合(citation_error_rate)")
    citable = [r for r in records if r.get("claim_type") in ("fact", "derived")]
    malformed = []
    for r in citable:
        if r.get("claim_type") == "fact":
            if not r.get("source_url") or not r.get("verbatim_quote"):
                malformed.append(r)
        else:  # derived
            deriv = r.get("derivation") or {}
            if not deriv.get("inputs"):
                malformed.append(r)
    cer = (len(malformed) / len(citable)) if citable else 0.0
    lines.append(f"  citation_error_rate = {cer:.1%} ({len(malformed)}/{len(citable)})")
    dd_malformed = [r for r in malformed if r.get("risk") == "decision_driving"]
    if dd_malformed:
        failed = True
        lines.append(f"  [FAIL] decision_driving で引用欠落 {len(dd_malformed)} 件:")
        for r in dd_malformed:
            lines.append(f"    - {r.get('claim_id')} {r.get('subject')} / {r.get('attribute')}")
    elif malformed:
        lines.append(f"  [WARN] supporting で引用欠落 {len(malformed)} 件(差し戻しはしない)")
    else:
        lines.append("  [OK] citable 主張は全て引用あり")

    return (not failed), lines


def main() -> int:
    ap = argparse.ArgumentParser(description="受入ゲート(手動)")
    ap.add_argument("path", help="claims.jsonl へのパス")
    ap.add_argument("--aql", type=float, default=0.065, help="supporting の許容不良率(既定 6.5%%)")
    args = ap.parse_args()

    path = Path(args.path)
    if not path.is_file():
        print(f"[FATAL] ファイルが無い: {path}", file=sys.stderr)
        return 2

    records, issues = load_and_validate(path)
    schema_errors = [i for i in issues if i.level == "ERROR"]
    if schema_errors:
        print("[FATAL] スキーマエラーがあるためゲートを実行できない。先に validate_ledger を通すこと:")
        for i in schema_errors:
            print(f"  {i}")
        return 2

    passed, report = run_gate(records, args.aql)
    print(f"# 受入ゲート: {path.name}")
    print("\n".join(report))
    print("\n=== 判定:", "[PASS] 受入可" if passed else "[FAIL] 差し戻し", "===")
    return 0 if passed else 1


if __name__ == "__main__":
    sys.exit(main())
