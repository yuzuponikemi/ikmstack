#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""harness_map.py — docs/harness-map.md の棚卸し(生成部)を再生成/検証する。

ハーネスの「何があるか」(棚卸し)は機械可読ソースから決定論で生成し、
「なぜ・どう繋がるか」(手書き部 = 層図・narrative)と分離する
(policy-map / report_meta と同じ二重帳簿パターン)。

ソース(すべて repo 内の機械可読物。ここに無いものは手書き部の領分):
  - .claude/skills/*/SKILL.md              frontmatter: name / description
  - docs/conventions/policy-registry.json  規約ルールと実行時強制の有無
  - .githooks/pre-commit                   コミット関門の並び(out=$(python …) を抽出)
  - tools/*.py / tools/*.sh / tools/<pkg>/ 道具と1行説明(docstring / 先頭コメント)

使い方:
  python3 tools/harness_map.py          # 再生成(マーカ間のみ書き換え)
  python3 tools/harness_map.py --check  # 検証のみ(ずれていれば exit 1)
"""
from __future__ import annotations

import json
import os
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
MAP_PATH = ROOT / "docs" / "harness-map.md"

MARK = "gen:harness-map:{key}:{pos}"


def esc(s: str) -> str:
    """Markdown 表セル用エスケープ。"""
    return s.replace("|", "\\|").strip()


def first_sentence(s: str, limit: int = 110) -> str:
    s = " ".join(s.split())
    if "。" in s:
        s = s.split("。")[0] + "。"
    else:
        m = re.search(r"(?<!\be\.g)(?<!\bi\.e)(?<!\betc)\.\s", s)
        if m:
            s = s[: m.start() + 1]
    if len(s) > limit:
        s = s[:limit].rstrip() + "…"
    return s


def rel_from_map(p: Path) -> str:
    return os.path.relpath(p, MAP_PATH.parent).replace("\\", "/")


def parse_frontmatter(text: str) -> dict:
    lines = text.splitlines()
    if not lines or lines[0].strip() != "---":
        return {}
    fm: dict[str, str] = {}
    i = 1
    while i < len(lines) and lines[i].strip() != "---":
        m = re.match(r"^([A-Za-z][\w-]*):\s*(.*)$", lines[i])
        if m:
            key, val = m.group(1), m.group(2).strip()
            if val in ("|", ">", "|-", ">-", ""):
                block: list[str] = []
                j = i + 1
                while j < len(lines) and (
                    lines[j].startswith((" ", "\t")) or lines[j].strip() == ""
                ):
                    block.append(lines[j].strip())
                    j += 1
                joined = " ".join(x for x in block if x)
                if joined:
                    fm[key] = joined
                    i = j
                    continue
            fm[key] = val
        i += 1
    return fm


def sec_summary() -> list[str]:
    n_skills = len(list((ROOT / ".claude" / "skills").glob("*/SKILL.md")))
    reg = json.loads(
        (ROOT / "docs" / "conventions" / "policy-registry.json").read_text(encoding="utf-8")
    )
    n_rules = len(reg["rules"])
    # enforced_by は「—(機械強制はしない…)」のような真値の説明文を持つことがある。
    # 実際に機械が強制するものだけ数える。
    n_enforced = sum(1 for r in reg["rules"]
                     if (r.get("enforced_by") or "").strip()
                     and not (r.get("enforced_by") or "").lstrip().startswith("—"))
    hook = (ROOT / ".githooks" / "pre-commit").read_text(encoding="utf-8")
    n_gates = len(re.findall(r"out=\$\((?:\"\$PY\"|python3?) ", hook))
    n_tools = len([p for p in (ROOT / "tools").iterdir() if p.suffix in (".py", ".sh")]) \
        + len([d for d in (ROOT / "tools").iterdir() if d.is_dir() and not d.name.startswith("_")])
    n_agents = len(list((ROOT / ".claude" / "agents").glob("*.md")))
    return [
        f"スキル **{n_skills}** / エージェント **{n_agents}** / "
        f"規約ルール **{n_rules}**(うち実行時強制 {n_enforced}) / "
        f"pre-commit 関門 **{n_gates}** / tools **{n_tools}**"
    ]


def sec_gates() -> list[str]:
    lines = (ROOT / ".githooks" / "pre-commit").read_text(encoding="utf-8").splitlines()
    rows = []
    step = 0
    for idx, line in enumerate(lines):
        # フックは `"$PY"`(python3 優先解決)でインタプリタを呼ぶ。表示は python3 に揃える
        # (macOS には `python` が無いので、そのままコピペして動く形にする)。
        m = re.search(r"out=\$\((?:\"\$PY\"|python3?) ([^)]+?)\s+2>&1\)", line)
        if not m:
            continue
        step += 1
        cmd = "python3 " + m.group(1).strip()
        # 直前の連続コメントブロックの先頭行を「何を守るか」として拾う
        j = idx - 1
        while j >= 0 and lines[j].strip() == "":
            j -= 1
        end = j
        while j >= 0 and lines[j].lstrip().startswith("#"):
            j -= 1
        head = ""
        k = j + 1
        while k <= end:
            ls = lines[k].lstrip()
            if ls.startswith("#") and not ls.startswith("#!"):
                head = ls.lstrip("#").strip()
                break
            k += 1
        rows.append(f"| {step} | `{cmd}` | {esc(first_sentence(head, 90))} |")
    return [
        "| # | 検査コマンド | 何を守るか(フックのコメント1行目) |",
        "|---|---|---|",
        *rows,
    ]


def sec_rules() -> list[str]:
    reg = json.loads(
        (ROOT / "docs" / "conventions" / "policy-registry.json").read_text(encoding="utf-8")
    )
    rows = []
    for r in reg["rules"]:
        enforced = r.get("enforced_by", "")
        cell = f"`{esc(enforced)}`" if enforced else "—(散文。policy gate は写し同期のみ)"
        rows.append(
            f"| `{r['id']}` | {esc(r['title'])} | {r['canonical']['file']} | {cell} |"
        )
    return [
        "| rule id | ルール | 正本 | 実行時強制(決定論) |",
        "|---|---|---|---|",
        *rows,
    ]


def sec_skills() -> list[str]:
    rows = []
    for p in sorted((ROOT / ".claude" / "skills").glob("*/SKILL.md")):
        fm = parse_frontmatter(p.read_text(encoding="utf-8"))
        name = fm.get("name", p.parent.name)
        desc = first_sentence(fm.get("description", ""))
        rows.append(f"| [{name}]({rel_from_map(p)}) | {esc(desc)} |")
    return ["| スキル | 一言(description 冒頭) |", "|---|---|", *rows]


def _doc_line(p: Path) -> str:
    text = p.read_text(encoding="utf-8", errors="replace")
    if p.suffix == ".py":
        m = re.search(r'"""(.*?)"""', text, re.S)
        if m:
            for line in m.group(1).strip().splitlines():
                if line.strip():
                    return line.strip()
    for line in text.splitlines():
        ls = line.strip()
        if ls.startswith(("#!", "# -*-", "<#")):
            continue
        if ls.startswith("#"):
            t = ls.lstrip("#").strip()
            if t:
                return t
        elif ls:
            break
    return "—"


def sec_tools() -> list[str]:
    rows = []
    for p in sorted((ROOT / "tools").iterdir()):
        if p.is_file() and p.suffix in (".py", ".sh"):
            rows.append(f"| `tools/{p.name}` | {esc(first_sentence(_doc_line(p)))} |")
        elif p.is_dir() and (p / "README.md").exists():
            head = (p / "README.md").read_text(encoding="utf-8").splitlines()[0]
            head = head.lstrip("#").strip()
            n = len(list(p.glob("*.py")))
            rows.append(f"| `tools/{p.name}/`({n} scripts) | {esc(first_sentence(head))} |")
    return ["| 道具 | 1行説明(docstring/先頭コメント) |", "|---|---|", *rows]


SECTIONS = {
    "summary": sec_summary,
    "gates": sec_gates,
    "rules": sec_rules,
    "skills": sec_skills,
    "tools": sec_tools,
}


def render(current: str) -> str:
    out = current
    for key, fn in SECTIONS.items():
        start = f"<!-- {MARK.format(key=key, pos='start')} -->"
        end = f"<!-- {MARK.format(key=key, pos='end')} -->"
        if start not in out or end not in out:
            sys.exit(f"error: marker pair for section '{key}' not found in {MAP_PATH}")
        head, rest = out.split(start, 1)
        _, tail = rest.split(end, 1)
        body = "\n".join(fn())
        out = f"{head}{start}\n\n{body}\n\n{end}{tail}"
    return out


def main() -> None:
    check = "--check" in sys.argv[1:]
    current = MAP_PATH.read_text(encoding="utf-8")
    new = render(current)
    if new == current:
        print(f"harness map: up to date ({MAP_PATH.relative_to(ROOT)})")
        return
    if check:
        print(
            "harness map: STALE — 棚卸し(生成部)がソースとずれています。\n"
            "  → python3 tools/harness_map.py で再生成し、git add してください。"
        )
        sys.exit(1)
    # Path.write_text() gained `newline` in 3.10; 3.9 でも動くよう open() を使う。
    with MAP_PATH.open("w", encoding="utf-8", newline="\n") as fh:
        fh.write(new)
    print(f"wrote {MAP_PATH.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
