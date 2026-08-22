#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""notebook_map.py — 記録層(ノート)の地図に手書きされた skill 一覧の鮮度検査。

ハーネス(① ikmstack)で skill を増減しても、② 記録層の地図は**別 repo**にあるため
編集時に視界へ入らず、構造的に腐る(2026-08-22、実体 14 個に対し地図は 8 個のまま
放置されていた)。harness_map.py がハーネス自身の棚卸しに対してやっていることを、
ノート側の写しに対してやる。

  ソース(実体)   : .claude/skills/*/SKILL.md の frontmatter `name:`
  検査対象(写し) : ~/.ikmstack/notebooks に登録された各ノートの直下 *.md のうち、
                   <!-- harness-skills:begin --> … <!-- harness-skills:end -->
                   で囲まれた領域

**宣言されたものだけを見る。** マーカで囲まれていない言及(README の例示など)は
検査しない — 「網羅のつもりの一覧」と「例として挙げただけ」は機械には区別できず、
区別を書き手に宣言させるのが唯一壊れない方法だから(policy の写しがピンを持つのと同じ型)。

領域内で skill は **`` `/name` `` 形式**(バッククォートで囲み、スラッシュ始まり)で書く。
これが列挙の目印になる。散文中の単語や `ikmstack/tools/foo.py` のようなパスを
skill 名と誤認しないよう、バッククォート直後がスラッシュであることまで要求する。

ノートは別 repo でありコミットを止める筋合いが無いので、既定は**警告のみ**(exit 0)。

使い方:
  python3 tools/notebook_map.py           # 検査(差分は警告、exit 0)
  python3 tools/notebook_map.py --strict  # 差分があれば exit 1
  python3 tools/notebook_map.py --list    # 実体の skill 一覧だけ出す
"""
from __future__ import annotations

import os
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
STATE_DIR = Path(os.environ.get("IKMSTACK_STATE", Path.home() / ".ikmstack"))

BEGIN = "<!-- harness-skills:begin -->"
END = "<!-- harness-skills:end -->"
SKILL_REF = re.compile(r"`/([a-z0-9][a-z0-9-]*)`")


def parse_frontmatter(text: str) -> dict:
    """SKILL.md 先頭の YAML frontmatter から素朴に key: value を拾う。"""
    if not text.startswith("---"):
        return {}
    end = text.find("\n---", 3)
    if end == -1:
        return {}
    out: dict[str, str] = {}
    for line in text[3:end].splitlines():
        if not line.strip() or line.lstrip().startswith("#"):
            continue
        if ":" in line and not line.startswith((" ", "\t")):
            k, _, v = line.partition(":")
            out[k.strip()] = v.strip().strip("'\"")
    return out


def actual_skills() -> set[str]:
    names = set()
    for p in sorted((ROOT / ".claude" / "skills").glob("*/SKILL.md")):
        fm = parse_frontmatter(p.read_text(encoding="utf-8"))
        names.add(fm.get("name") or p.parent.name)
    return names


def notebooks() -> list[Path]:
    seen, out = set(), []
    for fname in ("notebooks", "notebook"):
        f = STATE_DIR / fname
        if not f.exists():
            continue
        for line in f.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if line and line not in seen:
                seen.add(line)
                out.append(Path(line))
    return out


def declared_regions(md: Path) -> list[str]:
    """マーカで囲まれた領域の本文を返す(1ファイルに複数あってよい)。"""
    try:
        text = md.read_text(encoding="utf-8")
    except (OSError, UnicodeDecodeError):
        return []
    regions, pos = [], 0
    while True:
        i = text.find(BEGIN, pos)
        if i == -1:
            return regions
        j = text.find(END, i)
        if j == -1:
            return regions  # 閉じ忘れは領域なしとして扱う(下で未宣言に見える)
        regions.append(text[i + len(BEGIN):j])
        pos = j + len(END)


def check(strict: bool) -> int:
    actual = actual_skills()
    nbs = notebooks()
    if not nbs:
        print("notebook-map: 登録ノートなし — 検査対象なし")
        return 0

    problems = 0
    for nb in nbs:
        if not nb.is_dir():
            print(f"notebook-map: {nb} — 存在しない(スキップ)")
            continue
        declared: dict[str, set[str]] = {}
        for md in sorted(nb.glob("*.md")):
            found = set()
            for region in declared_regions(md):
                found |= {m.group(1) for m in SKILL_REF.finditer(region)}
            if found:
                declared[md.name] = found
        if not declared:
            print(f"notebook-map: {nb.name} — skill 一覧の宣言なし(スキップ)")
            print(f"  → 網羅一覧のある地図は {BEGIN} … {END} で囲むと検査対象になります")
            continue
        for fname, found in declared.items():
            missing = sorted(actual - found)
            extra = sorted(found - actual)
            if not missing and not extra:
                print(f"notebook-map: {nb.name}/{fname} ✓ ({len(found)} 個一致)")
                continue
            problems += 1
            print(f"notebook-map: {nb.name}/{fname} ⚠ ずれています")
            if missing:
                print(f"  地図に無い(ハーネスにはある): {', '.join('/' + s for s in missing)}")
            if extra:
                print(f"  ハーネスに無い(地図にはある): {', '.join('/' + s for s in extra)}")
    if problems:
        print(f"  → {nbs[0]} の地図を実体に合わせてください"
              if len(nbs) == 1 else "  → 各ノートの地図を実体に合わせてください")
        return 1 if strict else 0
    return 0


def main() -> None:
    args = sys.argv[1:]
    if "--list" in args:
        for s in sorted(actual_skills()):
            print(s)
        return
    sys.exit(check(strict="--strict" in args))


if __name__ == "__main__":
    main()
