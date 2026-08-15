#!/usr/bin/env python3
"""gen_readview.py — 読みビュー(HTML)生成の共通ステップ。

各実験の regenerate スクリプトの末尾から 1 行で呼ぶ。ブロックを複製せず、
変更点をここ 1 か所に集約する:

    python3 "$(dirname "$0")/../../tools/gen_readview.py" "$(dirname "$0")"

**図の再生成後に呼ぶこと**(生成済み PNG を base64 で埋め込むため)。
MD が正本・HTML は派生ビュー(git には入れない)。

mistune 未導入の環境では**スキップ扱い**(終了コード 0)。図・レポート本体には
影響しないので、regenerate 全体を落とさない。
"""
from __future__ import annotations

import subprocess
import sys
from pathlib import Path

TOOLS_DIR = Path(__file__).resolve().parent


def main(argv: list[str]) -> int:
    if not argv:
        print("usage: gen_readview.py <experiment dir>", file=sys.stderr)
        return 2
    exp_dir = Path(argv[0]).resolve()
    print("\n▶ 読みビュー生成 (report_readview)")
    r = subprocess.run(
        [sys.executable, "-X", "utf8", str(TOOLS_DIR / "report_readview.py"), str(exp_dir)],
        capture_output=True, text=True,
    )
    print((r.stdout or "").rstrip())
    if r.returncode != 0:
        err = (r.stderr or "").strip()
        if "mistune" in err:
            print("NOTE: mistune 未導入のため読みビューをスキップ "
                  "(`pip install mistune` で有効化)。図・レポートには影響なし。")
            return 0
        print(err, file=sys.stderr)
        print("WARN: 読みビュー生成に失敗。図・レポートには影響なし。", file=sys.stderr)
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
