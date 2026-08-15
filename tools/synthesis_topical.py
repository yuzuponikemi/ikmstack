#!/usr/bin/env python3
"""synthesis_topical.py — topical proximity between experiments (依存なし)

synthesis_extract.py の参照エッジ(実験 ID の明示リンク)は、実験が互いを ID で
参照して初めて繋がる。だが **同じ対象・同じ症状**を扱いながら他実験を
ID で参照しない実験は、参照グラフに乗らず「孤立」に見える(人の目には繋がるのに)。

このモジュールは REPORT.md 本文の **装置名・技術語の共有**から実験間の近接を推定し、
参照グラフの見落としを補完する。手法は依存を増やさない軽量 TF-IDF ライク:

  1. 各 REPORT 本文から語を抽出(ASCII 技術語 + カタカナ語)。
  2. df(語が現れる実験数)を数え、汎用語(df >= 半数)を落とし、残りに idf 重み。
  3. 実験ペアの共有語について idf を合計してスコア化。共有語も添えて説明可能にする。

参照エッジと違い「なぜ近いか(共有語)」を出すので、矛盾/接続の人手判断の材料になる。
"""
from __future__ import annotations

import math
import re
from pathlib import Path

# ASCII 技術語(3文字以上)+ カタカナ語(2文字以上、長音含む)
_TERM_RE = re.compile(r"[A-Za-z][A-Za-z0-9_]{2,}|[ァ-ヶ][ァ-ヶー]{1,}")

# ノイズ語(構造語・URL 断片・体裁語)。df フィルタで拾えない固定ノイズだけ列挙。
_STOP = {
    "reports", "report", "experiment", "data", "note", "index", "jira", "http",
    "https", "com", "www", "browse", "github", "the",
    "and", "for", "with", "this", "that", "are", "was", "から", "また", "など",
    "rerpot", "docs", "conventions", "readme", "manifest", "plan", "decisions",
    "レポート", "データ", "ファイル", "これ", "それ", "とき", "ため", "こと",
}
# R### / 実験ID### / PR### / 数字のみ は語彙から除外
_JUNK_RE = re.compile(r"^(?:r|fl|pr|no|id)\d+$|^\d+$", re.IGNORECASE)


def _strip_frontmatter(text: str) -> str:
    lines = text.splitlines()
    if not lines or lines[0].strip() != "---":
        return text
    for i in range(1, len(lines)):
        if lines[i].strip() == "---":
            return "\n".join(lines[i + 1:])
    return text


def experiment_terms(report: Path) -> set[str]:
    """REPORT.md 本文から語彙集合を返す(小文字化・ノイズ除去)。"""
    body = _strip_frontmatter(report.read_text(encoding="utf-8"))
    out: set[str] = set()
    for m in _TERM_RE.findall(body):
        t = m.lower()
        if t in _STOP or _JUNK_RE.match(t):
            continue
        out.add(t)
    return out


def build_topical(exp_dir: Path, experiments: list[dict],
                  min_score: float = 2.0, top_shared: int = 6) -> dict:
    """近接エッジ(無向・a<b)と各実験の特徴語を返す。

    experiments は synthesis_extract の実験レコード(num / experiment_id / summary / refs)。
    """
    # 1) 語彙抽出
    terms: dict[int, set[str]] = {}
    meta: dict[int, dict] = {}
    for e in experiments:
        fl = e.get("num")
        if not fl:
            continue
        report = exp_dir / e["experiment_id"] / "REPORT.md"
        if not report.exists():
            continue
        terms[fl] = experiment_terms(report)
        meta[fl] = e

    n = len(terms)
    if n < 2:
        return {"edges": [], "term_count": {}}

    # 2) df と idf。汎用語(df >= 半数)は落とす。
    df: dict[str, int] = {}
    for ts in terms.values():
        for t in ts:
            df[t] = df.get(t, 0) + 1
    generic_cut = max(2, math.ceil(n * 0.5))
    idf = {
        t: math.log(n / c)
        for t, c in df.items()
        if c < generic_cut and c >= 1
    }

    # 3) ペアスコア。参照グラフ(refs)で既に繋がっているかも記録。
    fls = sorted(terms)
    edges = []
    for i, a in enumerate(fls):
        a_ref = {int(k) for k in meta[a].get("refs", {})}
        for b in fls[i + 1:]:
            shared = [t for t in (terms[a] & terms[b]) if t in idf]
            if not shared:
                continue
            score = sum(idf[t] for t in shared)
            if score < min_score:
                continue
            shared.sort(key=lambda t: idf[t], reverse=True)
            b_ref = {int(k) for k in meta[b].get("refs", {})}
            ref_linked = (b in a_ref) or (a in b_ref)
            edges.append({
                "a": a, "b": b,
                "score": round(score, 2),
                "shared": shared[:top_shared],
                "ref_linked": ref_linked,           # 参照グラフに既にある?
                "topical_only": not ref_linked,     # 参照では見えない新規接続?
            })
    edges.sort(key=lambda x: x["score"], reverse=True)
    return {
        "edges": edges,
        "term_count": {a: len(terms[a]) for a in fls},
        "generic_cut": generic_cut,
    }


def neighbors(topical: dict, fl: int, limit: int = 8) -> list[dict]:
    """指定した実験番号の近接相手を score 降順で返す(参照グラフ非依存の関連候補)。"""
    out = []
    for e in topical["edges"]:
        if e["a"] == fl:
            out.append({"other": e["b"], **_pick(e)})
        elif e["b"] == fl:
            out.append({"other": e["a"], **_pick(e)})
    out.sort(key=lambda x: x["score"], reverse=True)
    return out[:limit]


def _pick(e: dict) -> dict:
    return {"score": e["score"], "shared": e["shared"],
            "ref_linked": e["ref_linked"], "topical_only": e["topical_only"]}
