#!/usr/bin/env python3
"""リスク加重サンプリングの選定.

判断駆動(decision_driving)は全数検証(100%)。
補足(supporting)は全数だと高コストなので、ロットサイズに応じて抜き取る。
本スクリプトは「**どの補足主張を検証するか**」を決定論的に選ぶ。
受入判定(不良率の合否)は dr_gate.py が行う(役割分担)。

抜き取り数 n は ISO 2859-1 / ANSI-ASQ Z1.4 の「サンプルサイズ文字(一般検査水準II)」
の**サンプルサイズ表**に従う(この n 値とロット区分は広く公開されている)。

> 制限事項: 「文書の claim 不良率を AQL で管理する」確立した規格事例は未発見。
> 合格判定数 Ac の厳密な値は Z1.4 のマスタ表(有料規格)にあり、本ツールは既定で
> **c=0(欠陥0で合格)の保守プラン**を採る。認証検査が要る場合は規格の Ac を別途用いること。
> ここで決めるのは「検査対象の選定」までで、過剰な精度を主張しない。

使い方:
    python3 tools/dr/sampling_select.py <path>/claims.jsonl [--level II] [--aql 0.065]

終了コード: 0(選定を出力)/ 2(ファイル無し等)
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

from validate_ledger import load_and_validate

# ロットサイズ → サンプルサイズ文字(一般検査水準 II)。(下限, 上限, 文字)
_CODE_LETTER_II = [
    (2, 8, "A"), (9, 15, "B"), (16, 25, "C"), (26, 50, "D"), (51, 90, "E"),
    (91, 150, "F"), (151, 280, "G"), (281, 500, "H"), (501, 1200, "J"),
    (1201, 3200, "K"), (3201, 10000, "L"), (10001, 35000, "M"),
    (35001, 150000, "N"), (150001, 500000, "P"), (500001, 10**12, "Q"),
]
# サンプルサイズ文字 → サンプルサイズ n
_SAMPLE_SIZE = {
    "A": 2, "B": 3, "C": 5, "D": 8, "E": 13, "F": 20, "G": 32, "H": 50,
    "J": 80, "K": 125, "L": 200, "M": 315, "N": 500, "P": 800, "Q": 1250, "R": 2000,
}


def code_letter(lot: int) -> str:
    for lo, hi, letter in _CODE_LETTER_II:
        if lo <= lot <= hi:
            return letter
    return "A" if lot < 2 else "Q"


def systematic_sample(ids: list[str], n: int) -> list[str]:
    """claim_id 昇順に等間隔抽出(決定論・代表性)。n>=len なら全数。"""
    ids = sorted(ids)
    if n >= len(ids):
        return ids
    step = len(ids) / n
    return [ids[int(i * step)] for i in range(n)]


def main() -> int:
    ap = argparse.ArgumentParser(description="リスク加重サンプリングの選定")
    ap.add_argument("path", help="claims.jsonl へのパス")
    ap.add_argument("--level", default="II", help="検査水準(現状 II のみ対応)")
    ap.add_argument("--aql", type=float, default=0.065, help="参考表示する AQL(合否は dr_gate)")
    ap.add_argument("--include-verified", action="store_true",
                    help="検証済みの補足主張も母集団に含める(既定は未検証のみ)")
    args = ap.parse_args()

    path = Path(args.path)
    if not path.is_file():
        print(f"[FATAL] ファイルが無い: {path}", file=sys.stderr)
        return 2
    if args.level != "II":
        print(f"[FATAL] 現状サポートは一般検査水準 II のみ(指定: {args.level})", file=sys.stderr)
        return 2

    records, issues = load_and_validate(path)
    if [i for i in issues if i.level == "ERROR"]:
        print("[FATAL] スキーマエラーあり。先に validate_ledger を通すこと。")
        return 2

    def status(r):
        return (r.get("verification") or {}).get("status", "unverified")

    decision = [r for r in records if r.get("risk") == "decision_driving"]
    supporting = [r for r in records if r.get("risk") == "supporting"]
    if args.include_verified:
        lot = supporting
    else:
        lot = [r for r in supporting if status(r) not in ("verified", "refuted")]

    lot_ids = [r.get("claim_id") for r in lot]
    letter = code_letter(len(lot_ids)) if lot_ids else "-"
    n = min(_SAMPLE_SIZE.get(letter, 0), len(lot_ids)) if lot_ids else 0
    selected = systematic_sample(lot_ids, n) if n else []

    print(f"# sampling_select: {path.name}(一般検査水準 II / 参考AQL {args.aql:.1%})")
    print(f"\n## 判断駆動(全数検証=100%): {len(decision)} 件")
    for r in decision:
        print(f"  - {r.get('claim_id')} {r.get('subject')} / {r.get('attribute')} [{status(r)}]")
    print(f"\n## 補足(抜き取り対象の母集団: {len(lot_ids)} 件)")
    print(f"  サンプルサイズ文字 = {letter} → 抜き取り n = {n}")
    if not selected:
        print("  (母集団が空。検証すべき補足主張なし)")
    else:
        sel_set = set(selected)
        for cid in sorted(lot_ids):
            mark = "★検証" if cid in sel_set else "  skip"
            r = next(x for x in lot if x.get("claim_id") == cid)
            print(f"  {mark}  {cid} {r.get('subject')} / {r.get('attribute')}")
    print("\n> 合格判定数 Ac は既定 c=0(欠陥0で合格)。実際の合否は dr_gate.py の不良率検査で行う。")
    print("> 認証検査が要る場合は Z1.4 マスタ表の Ac を別途適用(本ツールは選定までが責務)。")
    return 0


if __name__ == "__main__":
    sys.exit(main())
