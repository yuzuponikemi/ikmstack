#!/usr/bin/env python3
"""派生値の決定論 recompute と数値照合.

数値決定論および内部整合の検証を行う。
台帳の derived 主張を、derivation.formula と vars(変数名→claim_id)から再計算し、
主張値と照合する。**丸め表示を考慮**(0.0542% は表示 0.05% と一致と見なす)。

mismatch のとき「(a) 出典の値が誤り /
(b) 台帳の入力リンクが誤り」の切り分けを促す。recompute は入力が正しくリンク
されていて初めて意味を持つ。

使い方:
    python3 tools/dr/numeric_compare.py <path>/claims.jsonl
    python3 tools/dr/numeric_compare.py <path>/claims.jsonl --only c007

終了コード: 0 = 全 derived が一致 / 1 = mismatch あり / 2 = ファイル無し等
stdlib のみ。式評価は ast ベースのホワイトリスト(eval は使わない)。
"""
from __future__ import annotations

import argparse
import ast
import math
import operator
import sys
from pathlib import Path

from validate_ledger import load_and_validate

# --- 安全な式評価(ast ホワイトリスト)---------------------------------------
_BIN_OPS = {
    ast.Add: operator.add,
    ast.Sub: operator.sub,
    ast.Mult: operator.mul,
    ast.Div: operator.truediv,
    ast.Pow: operator.pow,
    ast.Mod: operator.mod,
}
_UNARY_OPS = {ast.UAdd: operator.pos, ast.USub: operator.neg}
_FUNCS = {
    "sqrt": math.sqrt, "abs": abs, "log": math.log, "log10": math.log10,
    "exp": math.exp, "pow": pow, "min": min, "max": max,
}
_CONSTS = {"pi": math.pi, "e": math.e}


def safe_eval(expr: str, variables: dict[str, float]) -> float:
    """expr を variables(+定数+ホワイトリスト関数)の下で安全に評価する。"""
    names = {**_CONSTS, **variables}

    def _ev(node):
        if isinstance(node, ast.Expression):
            return _ev(node.body)
        if isinstance(node, ast.Constant):
            if isinstance(node.value, (int, float)) and not isinstance(node.value, bool):
                return node.value
            raise ValueError(f"許可されない定数: {node.value!r}")
        if isinstance(node, ast.BinOp) and type(node.op) in _BIN_OPS:
            return _BIN_OPS[type(node.op)](_ev(node.left), _ev(node.right))
        if isinstance(node, ast.UnaryOp) and type(node.op) in _UNARY_OPS:
            return _UNARY_OPS[type(node.op)](_ev(node.operand))
        if isinstance(node, ast.Name):
            if node.id in names:
                return names[node.id]
            raise ValueError(f"未定義の変数/名前: {node.id}")
        if isinstance(node, ast.Call):
            if not isinstance(node.func, ast.Name) or node.func.id not in _FUNCS:
                raise ValueError("許可されない関数呼び出し")
            return _FUNCS[node.func.id](*[_ev(a) for a in node.args])
        raise ValueError(f"許可されない構文: {ast.dump(node)}")

    return float(_ev(ast.parse(expr, mode="eval")))


# --- 丸め考慮の一致判定 -------------------------------------------------------
def _decimals_of(value_raw, value_num) -> int:
    """主張値の表示小数桁数を推定(丸め一致の判定に使う)。"""
    s = None
    if isinstance(value_raw, str):
        # "0.05 %" -> "0.05" / "26,100 mg" -> "26100"
        for tok in value_raw.replace(",", "").split():
            if any(ch.isdigit() for ch in tok):
                s = tok
                break
    if s is None and value_num is not None:
        s = repr(value_num)
    if s and "." in s:
        return len(s.split(".")[-1])
    return 0


def compare(computed: float, claimed: float, decimals: int, rel_tol: float = 0.02):
    """(match, kind, detail) を返す。
    kind: 'exact'(丸め桁で一致) / 'reltol'(相対許容内) / 'mismatch'。
    """
    if round(computed, decimals) == round(claimed, decimals):
        return True, "exact", f"表示{decimals}桁で一致 ({round(computed, decimals)})"
    denom = abs(claimed) if claimed else 1.0
    rel = abs(computed - claimed) / denom
    if rel <= rel_tol:
        return True, "reltol", f"相対差 {rel:.1%} ≤ 許容 {rel_tol:.0%}"
    return False, "mismatch", f"相対差 {rel:.1%}(computed {computed:.4g} vs claimed {claimed:.4g})"


# --- recompute --------------------------------------------------------------
def recompute(claim: dict, by_id: dict[str, dict]) -> dict:
    """1 件の derived 主張を再計算。結果 dict を返す。"""
    cid = claim.get("claim_id")
    deriv = claim.get("derivation") or {}
    formula = deriv.get("formula")
    vars_map = deriv.get("vars")
    out = {"claim_id": cid, "status": "skip", "detail": ""}

    if not formula:
        out["detail"] = "formula 無し"
        return out
    if not isinstance(vars_map, dict) or not vars_map:
        out["status"] = "skip"
        out["detail"] = "vars マッピング無し=自動recompute不可(inputs のみ)。vars を付与すること"
        return out

    variables: dict[str, float] = {}
    for vname, in_cid in vars_map.items():
        src = by_id.get(in_cid)
        if src is None:
            out["status"] = "error"
            out["detail"] = f"入力 {in_cid} が台帳に無い(vars['{vname}'])"
            return out
        v = src.get("value_num")
        if not isinstance(v, (int, float)) or isinstance(v, bool):
            out["status"] = "error"
            out["detail"] = f"入力 {in_cid} の value_num が数値でない"
            return out
        variables[vname] = float(v)

    try:
        computed = safe_eval(formula, variables)
    except Exception as e:  # noqa: BLE001 - 式評価の失敗は判定に集約
        out["status"] = "error"
        out["detail"] = f"式評価失敗: {e}"
        return out

    claimed = claim.get("value_num")
    if not isinstance(claimed, (int, float)) or isinstance(claimed, bool):
        out["status"] = "error"
        out["detail"] = "主張の value_num が数値でない"
        return out

    decimals = _decimals_of(claim.get("value_raw"), claimed)
    match, kind, detail = compare(computed, float(claimed), decimals)
    out.update(
        status="match" if match else "mismatch",
        computed=computed, claimed=float(claimed), kind=kind, detail=detail,
        inputs={k: (variables[k], vars_map[k]) for k in variables},
    )
    return out


def main() -> int:
    ap = argparse.ArgumentParser(description="派生値の決定論 recompute と照合")
    ap.add_argument("path", help="claims.jsonl へのパス")
    ap.add_argument("--only", help="この claim_id だけ recompute")
    args = ap.parse_args()

    path = Path(args.path)
    if not path.is_file():
        print(f"[FATAL] ファイルが無い: {path}", file=sys.stderr)
        return 2

    records, issues = load_and_validate(path)
    if [i for i in issues if i.level == "ERROR"]:
        print("[FATAL] スキーマエラーあり。先に validate_ledger を通すこと。")
        return 2

    by_id = {r.get("claim_id"): r for r in records}
    derived = [r for r in records if r.get("claim_type") == "derived"]
    if args.only:
        derived = [r for r in derived if r.get("claim_id") == args.only]

    print(f"# numeric_compare: {path.name} — derived {len(derived)} 件")
    any_mismatch = False
    for claim in derived:
        res = recompute(claim, by_id)
        cid = res["claim_id"]
        st = res["status"]
        if st == "match":
            tag = "[OK]"
        elif st == "mismatch":
            tag = "[MISMATCH]"
            any_mismatch = True
        elif st == "skip":
            tag = "[SKIP]"
        else:
            tag = "[ERROR]"
            any_mismatch = True
        print(f"\n{tag} {cid}: {claim.get('subject')} / {claim.get('attribute')}")
        if "computed" in res:
            print(f"    formula : {claim['derivation']['formula']}")
            print(f"    inputs  : " + ", ".join(
                f"{k}={val:g} (<-{cid2})" for k, (val, cid2) in res["inputs"].items()))
            print(f"    computed: {res['computed']:.4g}   claimed: {res['claimed']:g}")
        print(f"    => {res['detail']}")
        if st == "mismatch":
            print("    ⚠️ 再現しない: (a) 出典の値が誤り / "
                  "(b) 台帳の入力リンクが誤り を切り分けよ。")
            print("       出典自身の導出基準(どの量を分母/入力に取るか)を読んでから出典を疑うこと。")

    print(f"\n=== numeric_compare:", "[FAIL] mismatch あり" if any_mismatch else "[OK] 全 derived 一致", "===")
    return 1 if any_mismatch else 0


if __name__ == "__main__":
    sys.exit(main())
