#!/usr/bin/env python3
"""questions.jsonl / sources.jsonl(調査の2台帳)のスキーマ検証.

スキーマ定義: tools/dr/research_schema.md
運用規約:     docs/conventions/research.md
stdlib のみ。決定論チェック(意味の妥当性は見ない = ハーネス地図の境界線)。

使い方:
    python3 tools/dr/validate_research.py <path>/questions.jsonl
    python3 tools/dr/validate_research.py <path>/sources.jsonl
    python3 tools/dr/validate_research.py <dir>          # 両方をまとめて

終了コード: 0 = エラーなし / 1 = スキーマエラーあり / 2 = ファイル無し
dr_coverage.py からは load_questions() / load_sources() を import して使う。
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

from validate_ledger import Issue

Q_STATUS = {"open", "closed", "abandoned", "exploratory"}
CONFIDENCE = {None, "high", "medium", "low"}
TIERS = {"primary", "secondary", "tertiary", "vendor"}
DECISIONS = {"adopted", "rejected", "pending"}
DATE_RE = re.compile(r"^\d{4}-\d{2}-\d{2}$")


def _load_jsonl(path: Path, id_field: str) -> tuple[list[dict], list[Issue]]:
    """JSONL を読み、(レコード列, 指摘列) を返す。ID 重複もここで検出する。"""
    records: list[dict] = []
    issues: list[Issue] = []
    seen: dict[str, int] = {}

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

        rid = rec.get(id_field)
        if rid:
            if rid in seen:
                issues.append(Issue("ERROR", line_no, str(rid), f"{id_field} 重複(L{seen[rid]} と)"))
            else:
                seen[rid] = line_no
    return records, issues


def _check_question(rec: dict, line: int, issues: list[Issue]) -> None:
    qid = str(rec.get("question_id") or "")

    def err(msg: str) -> None:
        issues.append(Issue("ERROR", line, qid, msg))

    def warn(msg: str) -> None:
        issues.append(Issue("WARN", line, qid, msg))

    for field in ("question_id", "question"):
        if not rec.get(field) or not isinstance(rec.get(field), str):
            err(f"必須の文字列フィールド '{field}' が無い/空")

    status = rec.get("status")
    if status not in Q_STATUS:
        err(f"status は {sorted(Q_STATUS)} のいずれか (実際: {status!r})")

    # 決着条件。exploratory(最初から決着させない探索)だけ免除する。
    if status != "exploratory" and not rec.get("closing_condition"):
        err("closing_condition(決着条件)が無い。書けない問いは分解し直すか exploratory にする")

    if status == "closed":
        if not rec.get("answer"):
            err("status=closed なのに answer が無い(何で決着したかを書く)")
        if rec.get("confidence") not in {"high", "medium", "low"}:
            err(f"status=closed は confidence 必須 (実際: {rec.get('confidence')!r})")
    if rec.get("confidence") not in CONFIDENCE:
        err(f"confidence は high/medium/low か null (実際: {rec.get('confidence')!r})")

    if status == "abandoned" and not rec.get("note"):
        err("status=abandoned は note に打ち切り理由を書く(決着と区別するため)")

    mis = rec.get("min_independent_sources")
    if mis is not None:
        if not isinstance(mis, int) or isinstance(mis, bool) or mis < 1:
            err(f"min_independent_sources は 1 以上の整数か null (実際: {mis!r})")
        elif mis < 2 and not rec.get("note"):
            warn("min_independent_sources を 2 未満に下げた理由を note に書くこと")

    if rec.get("refutation_searched") not in (True, False, None):
        err(f"refutation_searched は true/false/null (実際: {rec.get('refutation_searched')!r})")


def _check_source(rec: dict, line: int, issues: list[Issue]) -> None:
    sid = str(rec.get("source_id") or "")

    def err(msg: str) -> None:
        issues.append(Issue("ERROR", line, sid, msg))

    def warn(msg: str) -> None:
        issues.append(Issue("WARN", line, sid, msg))

    for field in ("source_id", "url", "title", "found_via"):
        if not rec.get(field) or not isinstance(rec.get(field), str):
            err(f"必須の文字列フィールド '{field}' が無い/空")

    tier = rec.get("tier")
    if tier not in TIERS:
        err(f"tier は {sorted(TIERS)} のいずれか (実際: {tier!r})")

    decision = rec.get("decision")
    if decision not in DECISIONS:
        err(f"decision は {sorted(DECISIONS)} のいずれか (実際: {decision!r})")

    # 棄却理由は「探したが無かった」を残すための中核。空欄を許すと台帳の意味が消える。
    if decision == "rejected" and not rec.get("decision_reason"):
        err("decision=rejected は decision_reason 必須(なぜ採らなかったか。『該当記述なし』も可)")

    if decision == "adopted":
        if not rec.get("accessed"):
            err("decision=adopted は accessed(取得日)必須")
        if not rec.get("snapshot"):
            warn("adopted なのに snapshot が無い(link rot で再現不能になる。取れないなら note に理由)")

    accessed = rec.get("accessed")
    if accessed and not DATE_RE.match(str(accessed)):
        warn(f"accessed は YYYY-MM-DD 形式 (実際: {accessed!r})")

    qids = rec.get("question_ids")
    if not isinstance(qids, list):
        err("question_ids は配列(空配列可)")
    elif any(not isinstance(q, str) for q in qids):
        err("question_ids の要素は文字列(question_id)")

    df = rec.get("derived_from")
    if df is not None and not isinstance(df, str):
        err(f"derived_from は文字列(source_id か原典 URL)か null (実際: {df!r})")


def load_questions(path: Path) -> tuple[list[dict], list[Issue]]:
    records, issues = _load_jsonl(path, "question_id")
    for rec in records:
        _check_question(rec, rec["_line"], issues)
    return records, issues


def load_sources(path: Path) -> tuple[list[dict], list[Issue]]:
    records, issues = _load_jsonl(path, "source_id")
    for rec in records:
        _check_source(rec, rec["_line"], issues)
    return records, issues


def _validate_one(path: Path, quiet: bool) -> tuple[int, int]:
    """1 ファイルを検証して (ERROR 数, レコード数) を返す。"""
    if path.name.startswith("questions"):
        records, issues = load_questions(path)
        label = "下位問い"
    else:
        records, issues = load_sources(path)
        label = "出典"

    errors = [i for i in issues if i.level == "ERROR"]
    print(f"# {path.name}")
    for i in issues:
        if i.level == "WARN" and quiet:
            continue
        print(f"  {i}")
    warns = len(issues) - len(errors)
    print(f"  === {len(records)} {label} / ERROR {len(errors)} / WARN {warns} ===")
    return len(errors), len(records)


def main() -> int:
    ap = argparse.ArgumentParser(description="questions.jsonl / sources.jsonl のスキーマ検証")
    ap.add_argument("path", help="台帳ファイル、または両方を含むディレクトリ")
    ap.add_argument("--quiet", action="store_true", help="WARN を抑制")
    args = ap.parse_args()

    target = Path(args.path)
    if target.is_dir():
        paths = [p for p in (target / "questions.jsonl", target / "sources.jsonl") if p.is_file()]
        if not paths:
            print(f"[FATAL] {target} に questions.jsonl / sources.jsonl が無い", file=sys.stderr)
            return 2
    elif target.is_file():
        paths = [target]
    else:
        print(f"[FATAL] ファイルが無い: {target}", file=sys.stderr)
        return 2

    total_errors = sum(_validate_one(p, args.quiet)[0] for p in paths)
    if total_errors:
        print(f"\n[FAIL] スキーマエラー {total_errors} 件。修正してから dr_coverage に進む。")
        return 1
    print("\n[OK] スキーマ検証パス。")
    return 0


if __name__ == "__main__":
    sys.exit(main())
