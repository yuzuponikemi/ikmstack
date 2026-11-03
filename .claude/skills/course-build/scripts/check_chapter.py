#!/usr/bin/env python3
"""Static spec gate for course-build chapter pages (references/chapter-spec.md §3, §5).

Usage:
    python check_chapter.py chapters/C01.html [chapters/C02.html ...] [--min-chars 9000] [--no-node]

Checks per file (FAIL = exit 1):
  - required section ids: intro, anchor, cases, quiz, summary, glossary, refs; >= 3 principle h2 (id p1, p2, ...)
  - header: .goals with 3-5 <li>, .meta present
  - .lab count 3-5; each lab has "やってみること" and an .obs block
  - .ex (worked examples) >= number of principle sections; .why >= 2; .case >= 2
  - quiz: >= 8 items, level mix 基本>=3 / 計算>=3 / 応用 or 診断 >=2, every item has <details>
  - no duplicate id attributes
  - body text (no script/style/svg/tags) >= --min-chars Japanese-ish characters (WARN only)
  - inline <script> blocks parse with `node --check` (skipped with --no-node)
  - notation (chapter-spec §2.5): operators only via macros (\\E \\Var \\Cov \\SE ...), no math symbols in
    prose outside \\( \\) (Greek letters, combining hats, "n = 25"), no pre.calc with symbols, SVG math labels
    use class "m", chapters do not call renderMathInElement themselves
"""
import argparse
import html as htmlmod
import re
import subprocess
import sys
import tempfile
from collections import Counter
from html.parser import HTMLParser
from pathlib import Path

REQUIRED_IDS = ["intro", "anchor", "cases", "quiz", "summary", "glossary", "refs"]


class Scan(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.ids = []
        self.h2_ids = []
        self.classes = Counter()
        self.stack = []  # (tag, classes)
        self.skip = 0  # inside script/style/svg
        self.text = []
        self.scripts = []
        self._script_buf = None
        self.goals_li = 0
        self.labs = []  # per lab: {"try": bool, "obs": bool}
        self.quiz = []  # per item: {"lv": str, "details": bool}
        self._in_lv = False
        self._lab_depth = None
        self._quiz_depth = None
        self._qi_depth = None
        self._goals_depth = None

    def handle_starttag(self, tag, attrs):
        a = dict(attrs)
        cls = (a.get("class") or "").split()
        if "id" in a:
            self.ids.append(a["id"])
            if tag == "h2":
                self.h2_ids.append(a["id"])
        for c in cls:
            self.classes[c] += 1
        depth = len(self.stack)
        if tag in ("script", "style", "svg"):
            self.skip += 1
            if tag == "script" and "src" not in a:
                self._script_buf = []
        if "goals" in cls:
            self._goals_depth = depth
        if tag == "li" and self._goals_depth is not None:
            self.goals_li += 1
        if "lab" in cls and tag == "div":
            self._lab_depth = depth
            self.labs.append({"try": False, "obs": False})
        if "obs" in cls and self._lab_depth is not None:
            self.labs[-1]["obs"] = True
        if tag == "ol" and "quiz" in cls:
            self._quiz_depth = depth
        if tag == "li" and self._quiz_depth is not None and depth == self._quiz_depth + 1:
            self._qi_depth = depth
            self.quiz.append({"lv": "", "details": False})
        if self._qi_depth is not None:
            if tag == "details":
                self.quiz[-1]["details"] = True
            if "lv" in cls:
                self._in_lv = True
        if tag not in ("br", "img", "input", "meta", "link", "hr", "source", "path", "circle", "line", "rect"):
            self.stack.append((tag, cls))

    def handle_endtag(self, tag):
        if tag in ("script", "style", "svg"):
            self.skip = max(0, self.skip - 1)
            if tag == "script" and self._script_buf is not None:
                self.scripts.append("".join(self._script_buf))
                self._script_buf = None
        # pop to matching tag
        for i in range(len(self.stack) - 1, -1, -1):
            if self.stack[i][0] == tag:
                del self.stack[i:]
                break
        depth = len(self.stack)
        if self._goals_depth is not None and depth <= self._goals_depth:
            self._goals_depth = None
        if self._lab_depth is not None and depth <= self._lab_depth:
            self._lab_depth = None
        if self._qi_depth is not None and depth < self._qi_depth + 0 + 1 and tag == "li":
            self._qi_depth = None
        if self._quiz_depth is not None and depth <= self._quiz_depth:
            self._quiz_depth = None
        if tag == "span":
            self._in_lv = False

    def handle_data(self, data):
        if self._script_buf is not None:
            self._script_buf.append(data)
        if self.skip:
            return
        self.text.append(data)
        if self._lab_depth is not None and "やってみること" in data:
            self.labs[-1]["try"] = True
        if self._in_lv and self.quiz:
            self.quiz[-1]["lv"] += data.strip()

OPS = r"(?:E|Var|Cov|Corr|SE|MSE|Bias|AIC|BIC|logit)"
MATH_RE = re.compile(r"\\\((.*?)\\\)|\\\[(.*?)\\\]", re.S)
GREEK = r"[\u0391-\u03a9\u03b1-\u03c9]"
COMB = r"[\u0300-\u036f]"


def lint_notation(raw: str):
    """Return list of (rule, count, samples) for notation violations."""
    out = []
    body = raw.split("<main>", 1)[-1].split("</main>", 1)[0]
    scripts = " ".join(re.findall(r"<script>(.*?)</script>", raw, flags=re.S))
    if re.search(r"renderMathInElement\s*\(", scripts):
        out.append(("chapter calls renderMathInElement (course.js renders with shared macros)", 1, []))
    body = re.sub(r"<script.*?</script>|<style.*?</style>", "", body, flags=re.S)
    svgs = re.findall(r"<svg.*?</svg>", body, flags=re.S)
    body = re.sub(r"<svg.*?</svg>", "", body, flags=re.S)
    math = [a or b for a, b in MATH_RE.findall(body)]

    def add(rule, hits):
        if hits:
            out.append((rule, len(hits), hits[:4]))

    add("operator not via macro (use \\Var \\Cov \\E \\SE ...)",
        [m.group(0) for seg in math for m in re.finditer(r"\\(?:operatorname|mathrm|text|textrm)\{" + OPS + r"\}", seg)])
    add("bare operator name in math (use \\Var( \\Cov( ...)",
        [m.group(0) for seg in math for m in re.finditer(r"(?<![\\A-Za-z{])(?:Var|Cov|Corr|SE|MSE|Bias|AIC|BIC)(?=\s*(?:\(|\[|\\left|\\big|\\Big))", seg)])
    add("bare E[ in math (use \\E[ / \\E\\left[)",
        [m.group(0) for seg in math for m in re.finditer(r"(?<![\\A-Za-z{_^])E(?=\s*(?:\[|\\left\[|\\bigl?\[|\\Bigl?\[))", seg)])
    # prose: drop math, drop elements marked as math-in-text (.m .mu .nomath) and code
    prose = MATH_RE.sub(" ", body)
    prose = re.sub(r'<(\w+)[^>]*class="[^"]*\b(?:m|mu|nomath)\b[^"]*"[^>]*>.*?</\1>', " ", prose, flags=re.S)
    prose = re.sub(r"<code>.*?</code>", " ", prose, flags=re.S)
    calc = re.findall(r'<pre class="calc">(.*?)</pre>', prose, flags=re.S)
    add("pre.calc with math symbols (write the derivation as \\[\\begin{aligned}...\\end{aligned}\\])",
        [htmlmod.unescape(c)[:40].replace("\n", " ") for c in calc if re.search(GREEK + "|" + COMB, htmlmod.unescape(c))])
    prose = re.sub(r'<pre class="calc">.*?</pre>', " ", prose, flags=re.S)
    text = htmlmod.unescape(re.sub(r"<[^>]+>", " ", prose))
    ctx = lambda m: text[max(0, m.start() - 8): m.end() + 6].replace("\n", " ")
    add("Greek letter in prose (wrap in \\( \\))", [ctx(m) for m in re.finditer(GREEK, text)])
    add("combining accent in prose (use \\hat \\bar in math)", [ctx(m) for m in re.finditer(COMB, text)])
    add("variable assignment in prose like 'n = 25' (wrap in \\( \\))",
        [ctx(m) for m in re.finditer(r"(?<![A-Za-z0-9_.])[A-Za-z](?:_[A-Za-z0-9]+)?\s*[=<>≤≥≠]\s*-?\d", text)])
    # SVG text: math symbols must carry class m
    svgbad = []
    for sv in svgs:
        for m in re.finditer(r"<text([^>]*)>(.*?)</text>", sv, flags=re.S):
            t = htmlmod.unescape(re.sub(r"<[^>]+>", "", m.group(2)))
            if re.search(GREEK + "|" + COMB, t) and 'class="m' not in m.group(1) and "class='m" not in m.group(1) and '"m"' not in m.group(2):
                svgbad.append(t[:30])
    add('SVG <text> with math symbols lacks class="m"', svgbad)
    return out


def check(path: Path, min_chars: int, use_node: bool, notation: bool = True):
    raw = path.read_text(encoding="utf-8")
    s = Scan()
    s.feed(raw)
    fails, warns, info = [], [], []

    for rid in REQUIRED_IDS:
        if rid not in s.h2_ids:
            fails.append(f"missing <h2 id=\"{rid}\">")
    principles = [i for i in s.h2_ids if re.fullmatch(r"p\d+", i)]
    if len(principles) < 3:
        fails.append(f"principle sections h2#p1.. = {len(principles)} (need >= 3)")
    if not (3 <= s.goals_li <= 5):
        fails.append(f".goals items = {s.goals_li} (need 3-5)")
    if not s.classes["meta"]:
        fails.append("missing .meta")

    n_lab = len(s.labs)
    if not (3 <= n_lab <= 5):
        fails.append(f".lab count = {n_lab} (need 3-5)")
    for i, lab in enumerate(s.labs, 1):
        if not lab["try"]:
            fails.append(f"LAB {i}: no 「やってみること」")
        if not lab["obs"]:
            fails.append(f"LAB {i}: no .obs")
    if s.classes["ex"] < len(principles):
        fails.append(f".ex worked examples = {s.classes['ex']} < principle sections {len(principles)}")
    if s.classes["why"] < 2:
        fails.append(f".why = {s.classes['why']} (need >= 2)")
    if s.classes["case"] < 2:
        fails.append(f".case = {s.classes['case']} (need >= 2)")

    lv = Counter()
    for q in s.quiz:
        k = q["lv"]
        lv["基本" if "基本" in k else "計算" if "計算" in k else "応用" if ("応用" in k or "診断" in k) else "?"] += 1
    if len(s.quiz) < 8:
        fails.append(f"quiz items = {len(s.quiz)} (need >= 8)")
    if lv["基本"] < 3 or lv["計算"] < 3 or lv["応用"] < 2:
        fails.append(f"quiz level mix 基本{lv['基本']}/計算{lv['計算']}/応用・診断{lv['応用']} (need 3/3/2)")
    if lv["?"]:
        fails.append(f"quiz items without .lv level = {lv['?']}")
    nodet = sum(1 for q in s.quiz if not q["details"])
    if nodet:
        fails.append(f"quiz items without <details> answer = {nodet}")

    dup = [k for k, v in Counter(s.ids).items() if v > 1]
    if dup:
        fails.append(f"duplicate ids: {', '.join(dup[:10])}")

    body = re.sub(r"\s+", "", "".join(s.text))
    jp = len(re.findall(r"[぀-ヿ㐀-鿿]", body))
    if jp < min_chars:
        warns.append(f"Japanese chars = {jp} (< {min_chars})")

    if use_node:
        for i, src in enumerate(s.scripts, 1):
            with tempfile.NamedTemporaryFile("w", suffix=".js", delete=False, encoding="utf-8") as f:
                f.write(src)
            r = subprocess.run(["node", "--check", f.name], capture_output=True, text=True)
            if r.returncode != 0:
                fails.append(f"inline script #{i} syntax error: {r.stderr.strip().splitlines()[-1] if r.stderr else '?'}")

    if notation:
        for rule, n, samples in lint_notation(raw):
            fails.append(f"notation: {rule}: {n} " + (" | ".join(repr(x) for x in samples) if samples else ""))

    info.append(f"labs={n_lab} quiz={len(s.quiz)}(基本{lv['基本']}/計算{lv['計算']}/応用{lv['応用']}) "
                f"ex={s.classes['ex']} why={s.classes['why']} case={s.classes['case']} "
                f"badges fact/hyp/unk/c={s.classes['b-fact']}/{s.classes['b-hyp']}/{s.classes['b-unk']}/{s.classes['b-c']} "
                f"jp_chars={jp} scripts={len(s.scripts)}")
    return fails, warns, info


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("files", nargs="+")
    ap.add_argument("--min-chars", type=int, default=9000)
    ap.add_argument("--no-node", action="store_true")
    ap.add_argument("--no-notation", action="store_true", help="skip the notation lint (legacy pages only)")
    a = ap.parse_args()
    bad = 0
    for f in a.files:
        p = Path(f)
        fails, warns, info = check(p, a.min_chars, not a.no_node, not a.no_notation)
        print(f"{'FAIL' if fails else 'PASS'} {p}")
        for x in info:
            print(f"  info: {x}")
        for x in warns:
            print(f"  WARN: {x}")
        for x in fails:
            print(f"  FAIL: {x}")
        bad += bool(fails)
    sys.exit(1 if bad else 0)


if __name__ == "__main__":
    main()
