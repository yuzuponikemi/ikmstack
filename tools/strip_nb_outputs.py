#!/usr/bin/env python
"""Strip outputs and execution counts from Jupyter notebooks.

Notebooks live in git as TEXT (source), not as data: cell outputs (figures,
computation results) are reproducible by re-running, bloat the repo, and produce
noisy diffs. This tool clears them so .ipynb files stay diff-friendly.

Dependency-free (stdlib json only) so it works on any PC without extra installs.

Usage:
    python tools/strip_nb_outputs.py nb1.ipynb nb2.ipynb   # strip files in place
    python tools/strip_nb_outputs.py --check nb1.ipynb      # exit 1 if not stripped
    python tools/strip_nb_outputs.py < in.ipynb > out.ipynb # stdin->stdout (git clean filter)

As a git clean filter (.gitattributes: `*.ipynb filter=nbstrip`):
    git config filter.nbstrip.clean "python tools/strip_nb_outputs.py"
    git config filter.nbstrip.smudge cat
"""
import json
import sys


def strip(nb):
    """Return (stripped_notebook, changed: bool)."""
    changed = False
    # notebook-level widget state can be huge; drop it
    md = nb.get("metadata", {})
    if md.pop("widgets", None) is not None:
        changed = True
    for cell in nb.get("cells", []):
        if cell.get("cell_type") != "code":
            continue
        if cell.get("outputs"):
            cell["outputs"] = []
            changed = True
        elif "outputs" in cell and cell["outputs"] != []:
            cell["outputs"] = []
            changed = True
        if cell.get("execution_count") is not None:
            cell["execution_count"] = None
            changed = True
        cmd = cell.get("metadata", {})
        for k in ("execution", "scrolled", "collapsed"):
            if cmd.pop(k, None) is not None:
                changed = True
    return nb, changed


def dump(nb):
    # match nbformat: indent=1, non-ASCII preserved, trailing newline
    return json.dumps(nb, indent=1, ensure_ascii=False, sort_keys=False) + "\n"


def main(argv):
    args = [a for a in argv if not a.startswith("-")]
    flags = {a for a in argv if a.startswith("-")}

    if not args:  # stdin -> stdout (git clean filter mode)
        nb = json.load(sys.stdin)
        nb, _ = strip(nb)
        sys.stdout.write(dump(nb))
        return 0

    check = "--check" in flags
    dirty = []
    for path in args:
        with open(path, encoding="utf-8") as f:
            nb = json.load(f)
        nb, changed = strip(nb)
        if check:
            if changed:
                dirty.append(path)
            continue
        if changed:
            with open(path, "w", encoding="utf-8", newline="\n") as f:
                f.write(dump(nb))
            print(f"stripped: {path}")
        else:
            print(f"clean   : {path}")
    if check and dirty:
        sys.stderr.write("notebooks with outputs (run strip_nb_outputs.py):\n")
        for p in dirty:
            sys.stderr.write(f"  {p}\n")
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
