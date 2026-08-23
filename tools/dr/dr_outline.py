#!/usr/bin/env python3
"""調査の骨組みを台帳から機械的に出す(散文の素材。判断はしない).

`/dr-synth` の入力。下位問いごとに「答え・確度・支持/反証の内訳・独立ソース・
未決着」を集約して Markdown で吐く。**結論を書くのは人/LLM**で、このツールは
台帳にある事実を並べ替えるだけ(散文の意味判定はしない = ハーネス地図の境界線)。

report_meta.py が frontmatter から INDEX を生成するのと同じ二重帳簿の思想:
正本は台帳、これは常設文書を作らないオンデマンド生成。

使い方:
    python3 tools/dr/dr_outline.py <path>/questions.jsonl
    python3 tools/dr/dr_outline.py <path>/questions.jsonl --out outline.md

終了コード: 0 = 生成 / 2 = ファイル無し or スキーマエラー
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

from dr_coverage import DEFAULT_MIN_INDEPENDENT, fold_to_root, _load_or_die
from validate_ledger import load_and_validate
from validate_research import load_questions, load_sources

STATUS_LABEL = {
    "closed": "決着",
    "open": "未決着(調査中)",
    "abandoned": "打ち切り",
    "exploratory": "探索(決着させない)",
}


def build_outline(questions: list[dict], claims: list[dict], sources: list[dict]) -> str:
    s_by_id = {s["source_id"]: s for s in sources if s.get("source_id")}
    out: list[str] = ["# 調査の骨組み(台帳からの生成物 — 散文の素材)", ""]
    out.append("> このファイルは `dr_outline.py` の生成物。正本は台帳(questions/sources/claims)。")
    out.append("> ここに結論を書き足さない — 散文はレポート側に書く。")
    out.append("")

    for q in questions:
        qid = q.get("question_id", "?")
        status = q.get("status", "?")
        mine = [c for c in claims if c.get("question_id") == qid]
        supports = [c for c in mine if c.get("stance") == "supports"]
        refutes = [c for c in mine if c.get("stance") == "refutes"]
        neutral = [c for c in mine if c.get("stance") == "neutral"]
        dd = [c for c in mine if c.get("risk") == "decision_driving"]
        adopted = [s for s in sources
                   if qid in (s.get("question_ids") or []) and s.get("decision") == "adopted"]
        rejected = [s for s in sources
                    if qid in (s.get("question_ids") or []) and s.get("decision") == "rejected"]
        roots = {fold_to_root(s["source_id"], s_by_id) for s in adopted if s.get("source_id")}
        need = q.get("min_independent_sources") or DEFAULT_MIN_INDEPENDENT

        out.append(f"## {qid} [{STATUS_LABEL.get(status, status)}] {q.get('question','')}")
        out.append("")
        out.append(f"- **決着条件**: {q.get('closing_condition') or '(なし)'}")
        if status == "closed":
            out.append(f"- **答え**: {q.get('answer') or '(未記入)'}")
            out.append(f"- **確度**: {q.get('confidence') or '(未記入)'}")
        if q.get("note"):
            out.append(f"- **注記**: {q['note']}")
        out.append(
            f"- **証拠の内訳**: 支持 {len(supports)} / 反証 {len(refutes)} / 中立 {len(neutral)}"
            f" (うち判断駆動 {len(dd)})"
        )
        out.append(f"- **独立ソース**: {len(roots)} 本 (必要 {need} 本 / 採用 {len(adopted)} 本を畳んだ結果)")
        out.append("")

        if refutes or neutral:
            out.append("### 反証・留保(散文で必ず触れる)")
            for c in refutes + neutral:
                out.append(
                    f"- ({c.get('stance')}) `{c.get('claim_id')}` {c.get('subject')} / "
                    f"{c.get('attribute')} = {c.get('value_raw')} — {c.get('source_url') or ''}"
                )
            out.append("")

        if dd:
            out.append("### 判断駆動の主張(claim マーカを打つ対象)")
            for c in dd:
                v = (c.get("verification") or {}).get("status", "unverified")
                out.append(
                    f"- `(claim:{c.get('claim_id')})` {c.get('subject')} / {c.get('attribute')}"
                    f" = {c.get('value_raw')} [{v}]"
                )
            out.append("")

        if rejected:
            out.append("### 探したが採らなかったもの(探索範囲の証拠)")
            for s in rejected:
                out.append(f"- {s.get('title')} — {s.get('decision_reason')} (探索: {s.get('found_via')})")
            out.append("")

    unresolved = [q for q in questions if q.get("status") in ("open", "abandoned")]
    out.append("## 未決着(散文に open question として必ず出す)")
    out.append("")
    if unresolved:
        for q in unresolved:
            out.append(f"- **{q['question_id']}** ({STATUS_LABEL.get(q.get('status'))}): {q.get('question')}"
                       + (f" — {q['note']}" if q.get("note") else ""))
    else:
        out.append("- なし(全ての下位問いが決着 or 探索扱い)")
    out.append("")
    return "\n".join(out)


def main() -> int:
    ap = argparse.ArgumentParser(description="調査の骨組みを台帳から生成する")
    ap.add_argument("questions", help="questions.jsonl へのパス")
    ap.add_argument("--claims", help="claims.jsonl(既定: 同じディレクトリ)")
    ap.add_argument("--sources", help="sources.jsonl(既定: 同上)")
    ap.add_argument("--out", help="書き出し先 .md(既定: 標準出力)")
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

    text = build_outline(questions, claims, sources)
    if args.out:
        Path(args.out).write_text(text, encoding="utf-8")
        print(f"[OK] 骨組みを書き出した: {args.out}")
    else:
        print(text)
    return 0


if __name__ == "__main__":
    sys.exit(main())
