#!/usr/bin/env python3
"""Scaffold a course-build course directory.

Usage:
    python new_course.py <course_dir> --title "統計検定準1級ノート" --tag "STATS-J1" \
        --profile exam-cert --chapters "C01:最尤推定" "C02:検定と検出力"

Creates (never overwrites existing files):
  <course_dir>/index.html                 hub page (from hub-template.html)
  <course_dir>/assets/course.css|js       shared runtime (copied from the skill)
  <course_dir>/assets/course-config.js    chapter list (all chapters marked "todo")
  <course_dir>/chapters/_template.html    chapter skeleton with placeholders filled from the profile
  <course_dir>/authoring/CHAPTER-SPEC.md  copy of references/chapter-spec.md + the profile appended
  <course_dir>/authoring/sources/  authoring/review/  authoring/verify/
"""
import argparse
import json
import re
import shutil
from pathlib import Path

SKILL = Path(__file__).resolve().parent.parent

def load_profiles():
    """Profiles are references/profiles/*.md; line 2 holds `<!-- slots: KEY=value | ... -->`."""
    out = {}
    for f in sorted((SKILL / "references" / "profiles").glob("*.md")):
        m = re.search(r"<!--\s*slots:\s*(.*?)\s*-->", f.read_text(encoding="utf-8")[:600])
        if m:
            out[f.stem] = dict(kv.split("=", 1) for kv in (x.strip() for x in m.group(1).split("|")) if "=" in kv)
    return out


PROFILE_SLOTS = load_profiles()


def write_new(path: Path, text: str):
    if path.exists():
        print(f"skip (exists): {path}")
        return
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")
    print(f"created: {path}")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("course_dir")
    ap.add_argument("--title", required=True)
    ap.add_argument("--tag", required=True, help="eyebrow tag, e.g. STATS-J1 or OPT-01")
    ap.add_argument("--profile", choices=sorted(PROFILE_SLOTS), required=True)
    ap.add_argument("--chapters", nargs="+", required=True, help='"C01:タイトル" ...')
    ap.add_argument("--no-math", action="store_true", help="drop KaTeX lines from the chapter template")
    a = ap.parse_args()

    root = Path(a.course_dir)
    rel = root.as_posix()
    slots = dict(PROFILE_SLOTS[a.profile], COURSE_TITLE=a.title, COURSE_TAG=a.tag, COURSE_DIR=rel)

    def fill(s: str) -> str:
        for k, v in slots.items():
            s = s.replace("{" + k + "}", v)
        return s

    for f in ("course.css", "course.js"):
        dst = root / "assets" / f
        if not dst.exists():
            dst.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(SKILL / "assets" / f, dst)
            print(f"created: {dst}")

    chs = []
    for c in a.chapters:
        cid, _, title = c.partition(":")
        chs.append([cid, title or cid, f"{cid}.html", "todo"])
    write_new(root / "assets" / "course-config.js",
              "// Course data for course.js and the hub page. Hrefs are relative to chapters/.\n"
              "// Remove the 4th element \"todo\" when a chapter passes the spec gate.\n"
              "window.COURSE = {\n"
              f"  title: {json.dumps(a.title, ensure_ascii=False)},\n"
              '  hub: "../index.html",\n'
              "  chapters: [\n"
              + "".join(f"    {json.dumps(c, ensure_ascii=False)},\n" for c in chs)
              + "  ],\n  summaries: {},\n};\n")

    tpl = fill((SKILL / "assets" / "_template.html").read_text(encoding="utf-8"))
    if a.no_math:
        tpl = re.sub(r"<!-- MATH.*?auto-render\.min\.js\" defer></script>\n", "", tpl, flags=re.S)
    write_new(root / "chapters" / "_template.html", tpl)
    write_new(root / "index.html", fill((SKILL / "assets" / "hub-template.html").read_text(encoding="utf-8")))

    spec = (SKILL / "references" / "chapter-spec.md").read_text(encoding="utf-8")
    prof = (SKILL / "references" / "profiles" / f"{a.profile}.md").read_text(encoding="utf-8")
    write_new(root / "authoring" / "CHAPTER-SPEC.md",
              spec + f"\n\n---\n\n# このコースの差し替え枠(プロファイル {a.profile})\n\n" + prof.split("\n", 1)[1])
    write_new(root / "COURSE-BRIEF.md", (SKILL / "references" / "brief-template.md").read_text(encoding="utf-8")
              .replace("<コース名>", a.title))
    for d in ("sources", "review", "verify"):
        (root / "authoring" / d).mkdir(parents=True, exist_ok=True)
        keep = root / "authoring" / d / ".gitkeep"
        if not any((root / "authoring" / d).iterdir()):
            keep.touch()


if __name__ == "__main__":
    main()
