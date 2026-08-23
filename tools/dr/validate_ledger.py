#!/usr/bin/env python3
"""claims.jsonl(主張台帳)のスキーマ検証.

スキーマ定義: tools/dr/claims_schema.md
stdlib のみ。決定論チェック(数値の真偽は LLM でなくコードで行う)。

使い方:
    python3 tools/dr/validate_ledger.py <path>/claims.jsonl

終了コード: 0 = エラーなし(警告はあってもよい) / 1 = スキーマエラーあり / 2 = ファイル無し
dr_gate.py からは load_and_validate() を import して使う。
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

CLAIM_TYPES = {"fact", "inference", "derived"}
RISKS = {"decision_driving", "supporting"}
VERIF_STATUS = {"unverified", "verified", "refuted", "unreachable"}
VERIF_METHODS = {None, "refetch+quote+numeric", "nli", "recompute", "sampled-skip"}
# 調査(ディープリサーチ)用の任意フィールド。既存台帳との後方互換のため、
# 欠けていても ERROR にはしない(網羅ゲート dr_coverage.py が必要な場面で FAIL させる)。
STANCES = {None, "supports", "refutes", "neutral"}
DATE_RE = re.compile(r"^\d{4}-\d{2}-\d{2}$")


class Issue:
    """1 件の検証指摘。level は ERROR(スキーマ違反) か WARN(推奨違反)。"""

    def __init__(self, level: str, line: int, claim_id: str, msg: str):
        self.level = level
        self.line = line
        self.claim_id = claim_id
        self.msg = msg

    def __str__(self) -> str:
        cid = self.claim_id or "?"
        return f"[{self.level}] L{self.line} ({cid}): {self.msg}"


def _check_record(rec: dict, line: int, issues: list[Issue]) -> None:
    cid = rec.get("claim_id", "")

    def err(msg: str) -> None:
        issues.append(Issue("ERROR", line, cid, msg))

    def warn(msg: str) -> None:
        issues.append(Issue("WARN", line, cid, msg))

    # --- 必須・型 ---
    for field in ("claim_id", "subject", "attribute"):
        if not rec.get(field) or not isinstance(rec.get(field), str):
            err(f"必須の文字列フィールド '{field}' が無い/空")

    claim_type = rec.get("claim_type")
    if claim_type not in CLAIM_TYPES:
        err(f"claim_type は {sorted(CLAIM_TYPES)} のいずれか (実際: {claim_type!r})")

    risk = rec.get("risk")
    if risk not in RISKS:
        err(f"risk は {sorted(RISKS)} のいずれか (実際: {risk!r})")

    # --- 数値の整合 ---
    if "value_num" in rec and rec["value_num"] is not None:
        if not isinstance(rec["value_num"], (int, float)) or isinstance(rec["value_num"], bool):
            err(f"value_num は数値 (実際: {rec['value_num']!r})")
        if not rec.get("unit"):
            warn("value_num があるのに unit が無い(数値照合に単位が要る)")

    # --- claim_type ごとの接地要件 ---
    if claim_type == "fact":
        for field in ("source_url", "source_accessed", "verbatim_quote"):
            if not rec.get(field):
                err(f"claim_type=fact は '{field}' 必須(quote-first・接地)")
        if not rec.get("value_raw"):
            warn("fact に value_raw が無い(出典表記そのままを残すこと)")
    elif claim_type == "derived":
        deriv = rec.get("derivation")
        if not isinstance(deriv, dict):
            err("claim_type=derived は derivation オブジェクト必須")
        else:
            if not deriv.get("formula"):
                err("derivation.formula が無い")
            # 機械 recompute には vars(変数名→claim_id)が要る。
            # 後方互換で inputs(claim_id のリスト)も許容するが、vars 推奨。
            vars_map = deriv.get("vars")
            inputs = deriv.get("inputs")
            has_vars = isinstance(vars_map, dict) and vars_map
            has_inputs = isinstance(inputs, list) and inputs
            if not has_vars and not has_inputs:
                err("derivation.vars(変数名→claim_id の dict)か inputs(claim_id リスト)が要る")
            if has_vars:
                for vname, cid in vars_map.items():
                    if not isinstance(cid, str):
                        err(f"derivation.vars['{vname}'] は claim_id 文字列")
            elif has_inputs:
                warn("derivation に vars が無い(inputs のみ)=numeric_compare の自動recompute不可")
        if not rec.get("value_raw"):
            warn("derived に value_raw(計算結果の表記)が無い")

    # --- 日付書式 ---
    sa = rec.get("source_accessed")
    if sa and not DATE_RE.match(str(sa)):
        warn(f"source_accessed は YYYY-MM-DD 形式が望ましい (実際: {sa!r})")

    # --- citation_axes ---
    ca = rec.get("citation_axes")
    if not isinstance(ca, dict):
        err("citation_axes オブジェクト必須 {reachable, relevant, supports}")
    else:
        for axis in ("reachable", "relevant", "supports"):
            if axis not in ca:
                err(f"citation_axes.{axis} が無い(null 可)")
            elif ca[axis] not in (True, False, None):
                err(f"citation_axes.{axis} は true/false/null (実際: {ca[axis]!r})")

    # --- 調査フィールド(任意。research_schema.md / dr_coverage.py 用)---
    for field in ("question_id", "source_id"):
        val = rec.get(field)
        if val is not None and not isinstance(val, str):
            err(f"{field} は文字列か null (実際: {val!r})")
    stance = rec.get("stance")
    if stance not in STANCES:
        err(f"stance は {sorted(x for x in STANCES if x)} か null (実際: {stance!r})")

    # --- verification ---
    v = rec.get("verification")
    if not isinstance(v, dict):
        err("verification オブジェクト必須")
        return
    status = v.get("status")
    if status not in VERIF_STATUS:
        err(f"verification.status は {sorted(VERIF_STATUS)} (実際: {status!r})")
    if v.get("method") not in VERIF_METHODS:
        warn(f"verification.method が想定外 (実際: {v.get('method')!r})")
    if status in ("verified", "refuted", "unreachable"):
        if not v.get("checked_at"):
            warn(f"status={status} なのに checked_at が無い")
        if not v.get("verifier"):
            warn(f"status={status} なのに verifier が無い")
    if status == "refuted" and not v.get("verdict_note"):
        warn("refuted なら verdict_note に出典側の実際の値を書くこと")


def load_and_validate(path: Path) -> tuple[list[dict], list[Issue]]:
    """台帳を読み、(レコード列, 指摘列) を返す。JSON パース不能行も ERROR として記録。"""
    records: list[dict] = []
    issues: list[Issue] = []
    seen_ids: dict[str, int] = {}

    for line_no, raw in enumerate(path.read_text(encoding="utf-8").splitlines(), start=1):
        if not raw.strip():
            continue
        try:
            rec = json.loads(raw)
        except json.JSONDecodeError as e:
            issues.append(Issue("ERROR", line_no, "", f"JSON パース失敗: {e}"))
            continue
        if not isinstance(rec, dict):
            issues.append(Issue("ERROR", line_no, "", "オブジェクト(dict)でない行"))
            continue
        rec["_line"] = line_no
        records.append(rec)

        cid = rec.get("claim_id")
        if cid:
            if cid in seen_ids:
                issues.append(
                    Issue("ERROR", line_no, cid, f"claim_id 重複(L{seen_ids[cid]} と)")
                )
            else:
                seen_ids[cid] = line_no

        _check_record(rec, line_no, issues)

    return records, issues


def main() -> int:
    ap = argparse.ArgumentParser(description="claims.jsonl のスキーマ検証")
    ap.add_argument("path", help="claims.jsonl へのパス")
    ap.add_argument("--quiet", action="store_true", help="WARN を抑制")
    args = ap.parse_args()

    path = Path(args.path)
    if not path.is_file():
        print(f"[FATAL] ファイルが無い: {path}", file=sys.stderr)
        return 2

    records, issues = load_and_validate(path)
    errors = [i for i in issues if i.level == "ERROR"]
    warns = [i for i in issues if i.level == "WARN"]

    for i in issues:
        if i.level == "WARN" and args.quiet:
            continue
        print(str(i))

    print(
        f"\n=== validate_ledger: {len(records)} 主張 / "
        f"ERROR {len(errors)} / WARN {len(warns)} ==="
    )
    if errors:
        print("[FAIL] スキーマエラーあり。修正してから dr_gate に進む。")
        return 1
    print("[OK] スキーマ検証パス。")
    return 0


if __name__ == "__main__":
    sys.exit(main())
