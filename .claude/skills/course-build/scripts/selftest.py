#!/usr/bin/env python3
"""Self-test for the course-build gates and scaffold (run after editing the skill).

    python selftest.py            # lint fixtures + scaffold of every profile + course.js macros
    python selftest.py --browser  # also run browser_check on a scaffolded hub (needs Playwright)

Exit 0 = all pass. A gate that cannot fail is no gate: the bad fixture must trigger every notation rule.
"""
import argparse
import json
import subprocess
import sys
import tempfile
from pathlib import Path

HERE = Path(__file__).resolve().parent
SKILL = HERE.parent
sys.path.insert(0, str(HERE))
import check_chapter as cc  # noqa: E402

BAD = """<!doctype html><html><body data-ch="C99"><div class="wrap"><main>
<h2 id="intro">1. 導入</h2>
<p>真のレート λ = 2 で n = 25 のとき推定量 λ̂ を使う。</p>
<p>分散は \\(\\operatorname{Var}(X)\\) と書き、期待値は \\(E[X]\\)、標準誤差は \\(\\mathrm{SE}\\)。</p>
<pre class="calc">E[λ̂] = nλ/(n-1)</pre>
<svg viewBox="0 0 10 10"><text x="1" y="1">λ = 2</text></svg>
</main><script>document.addEventListener("DOMContentLoaded",()=>{ renderMathInElement(document.body,{}); });</script>
</div></body></html>"""

GOOD = """<!doctype html><html><body data-ch="C99"><div class="wrap"><main>
<h2 id="intro">1. 導入</h2>
<p>真のレート \\(\\lambda = 2\\) で \\(n = 25\\) のとき推定量 \\(\\hat\\lambda\\) を使う。</p>
<p>分散は \\(\\Var(X)\\)、期待値は \\(\\E[X]\\)、標準誤差は \\(\\SE\\)。</p>
<div class="calc">\\[\\begin{aligned}\\E[\\hat\\lambda] &= \\frac{n\\lambda}{n-1}\\end{aligned}\\]</div>
<svg viewBox="0 0 10 10"><text class="m" x="1" y="1">λ = 2</text></svg>
<label>値 <span class="m">σ</span></label>
</main><script>document.addEventListener("DOMContentLoaded",()=>{ TC.renderMath(document.body); });</script>
</div></body></html>"""

EXPECT_BAD = ["renderMathInElement", "operator not via macro", "bare E[", "pre.calc with math symbols",
              "Greek letter in prose", "combining accent in prose", "variable assignment in prose", "SVG <text>"]

fails = []


def check(cond, msg):
    print(("ok   " if cond else "FAIL ") + msg)
    if not cond:
        fails.append(msg)


# 1. notation lint: the bad fixture must trip every rule, the good one none
bad = [r for r, _, _ in cc.lint_notation(BAD)]
for key in EXPECT_BAD:
    check(any(key in r for r in bad), f"lint flags: {key}")
good = cc.lint_notation(GOOD)
check(not good, f"lint passes the good fixture ({[r for r, _, _ in good]})")

# 2. scaffold every profile, config parses, no placeholders left
node = subprocess.run(["node", "--version"], capture_output=True).returncode == 0
import new_course as nc  # noqa: E402
for prof in sorted(nc.PROFILE_SLOTS):
    with tempfile.TemporaryDirectory() as t:
        root = Path(t) / "c"
        r = subprocess.run([sys.executable, str(HERE / "new_course.py"), str(root), "--title", "T", "--tag", "TAG",
                            "--profile", prof, "--chapters", "C01:一", "C02:二"], capture_output=True, text=True)
        check(r.returncode == 0, f"scaffold {prof}")
        files = ["index.html", "chapters/_template.html", "assets/course-config.js", "assets/course.js", "assets/course.css",
                 "authoring/CHAPTER-SPEC.md", "COURSE-BRIEF.md"]
        check(all((root / f).exists() for f in files), f"scaffold {prof}: files present")
        left = [f for f in ("index.html", "chapters/_template.html") if "{ANCHOR" in (root / f).read_text(encoding="utf-8")
                or "{COURSE_" in (root / f).read_text(encoding="utf-8")]
        check(not left, f"scaffold {prof}: no unreplaced placeholders {left}")
        if node:
            js = (f"global.window={{}};require('{root}/assets/course-config.js');"
                  "console.log(JSON.stringify(window.COURSE.chapters.length))")
            o = subprocess.run(["node", "-e", js], capture_output=True, text=True)
            check(o.stdout.strip() == "2", f"scaffold {prof}: course-config.js parses (2 chapters)")
        # the chapter template itself must pass the notation lint (placeholders only)
        tl = cc.lint_notation((root / "chapters" / "_template.html").read_text(encoding="utf-8"))
        check(not tl, f"scaffold {prof}: template passes notation lint ({[r for r, _, _ in tl]})")

# 3. course.js: macros defined and todo chapters excluded from navigation
if node:
    js = ("global.window=globalThis;global.document={addEventListener(){}};"
          "window.COURSE={title:'t',hub:'h',chapters:[['C01','a','a.html'],['C02','b','b.html','todo']]};"
          f"require('{SKILL}/assets/course.js');"
          "console.log(JSON.stringify([Object.keys(TC.MATH_MACROS).includes('\\\\Var'),TC.CHAPTERS.length]))")
    o = subprocess.run(["node", "-e", js], capture_output=True, text=True)
    check(o.stdout.strip() == "[true,1]", f"course.js: macros defined, todo chapters excluded ({o.stdout.strip()} {o.stderr.strip()[:80]})")

# 4. optional: browser gate on a scaffolded hub
ap = argparse.ArgumentParser()
ap.add_argument("--browser", action="store_true")
if ap.parse_args().browser:
    with tempfile.TemporaryDirectory() as t:
        root = Path(t) / "c"
        subprocess.run([sys.executable, str(HERE / "new_course.py"), str(root), "--title", "T", "--tag", "TAG",
                        "--profile", "exam-cert", "--chapters", "C01:一"], capture_output=True)
        r = subprocess.run(["node", str(HERE / "browser_check.mjs"), str(Path(t) / "shots"), str(root / "index.html")],
                           capture_output=True, text=True)
        check(r.returncode == 0, "browser_check on scaffolded hub\n" + r.stdout[-300:])

print("\nALL PASS" if not fails else f"\n{len(fails)} FAILED")
sys.exit(1 if fails else 0)
