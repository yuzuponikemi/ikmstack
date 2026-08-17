#!/usr/bin/env python3
"""pptx_preview.py — .pptx を目視確認用の PDF に描き起こす(GUI 不要).

## なぜ要るか

exp-deck の目視確認は本来 LibreOffice の `--convert-to pdf` で行う想定だが、Office 系も
LibreOffice も無い Mac では手段が無い。Keynote は AppleScript で書き出せるものの、
pptx を開くと**インポート警告のモーダルが出て AppleEvent が固まる**(解除には
osascript への assistive access 付与が要る)。どちらも **CI・自動化に載らない**。

このツールは `python-pptx` で **生成物そのもの**を読み、図形・画像・テキストを実座標で
PDF に描き直す。GUI もライセンスも要らず、何度でも同じ結果になる。

## 何を保証し、何を保証しないか(重要)

- **保証する**: 図形/画像/テキスト枠の**位置・寸法・重なり・色**、画像の縦横比、
  段落ごとの文字サイズと色。deckgen は全要素を絶対座標で置くので、ここが見えれば
  「はみ出し・かぶり・落丁」は目視で判る。
- **保証しない**: PowerPoint/Keynote と**同一の字送り**。行送り・禁則・フォント差で
  1〜2 行ぶんの折り返し差は出る。**近似レンダラであって、真のレンダラではない**。
  最終的な体裁は配布先アプリで確認すること。

使い方:
  uv run --with python-pptx --with matplotlib \
    python3 tools/pptx_preview.py <deck.pptx> [-o out.pdf] [--png-dir DIR]
  既定の出力先: 入力と同じディレクトリの <stem>.preview.pdf
  `--png-dir` は 1 スライド 1 枚の PNG も出す(PDF を開く手段が無い環境・
  エージェントが直接見る場合はこちら。PDF の描画には poppler が要る)。
"""
from __future__ import annotations

import argparse
import io
import sys
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.font_manager  # noqa: E402
import matplotlib.pyplot as plt  # noqa: E402
from matplotlib.backends.backend_pdf import PdfPages  # noqa: E402
from matplotlib.patches import Rectangle  # noqa: E402

from pptx import Presentation  # noqa: E402
from pptx.util import Emu  # noqa: E402

EMU_PER_IN = 914400.0

# 日本語が豆腐にならないよう、実在する和文フォントを選ぶ(図生成スクリプトと同じ型)
for _f in ("Hiragino Sans", "Hiragino Maru Gothic Pro", "Arial Unicode MS", "AppleGothic"):
    if any(_x.name == _f for _x in matplotlib.font_manager.fontManager.ttflist):
        matplotlib.rcParams["font.family"] = _f
        break


def _in(v) -> float:
    return (v or 0) / EMU_PER_IN


def _hex(color) -> str | None:
    """python-pptx の色を #rrggbb に。テーマ参照や未設定は None(=描かない)。"""
    try:
        rgb = color.rgb
    except (AttributeError, TypeError, ValueError):
        return None
    return f"#{rgb}" if rgb is not None else None


def _wrap(text: str, width_in: float, size_pt: float) -> list[str]:
    """枠幅に収まるよう素朴に折り返す。全角=1em / 半角=0.5em の近似。

    真の字送りではない(→ モジュール docstring の「保証しない」)。行数の目安を得て、
    枠から溢れていないかを目で見るのが目的。
    """
    if size_pt <= 0:
        return [text]
    em_per_line = max(width_in * 72.0 / size_pt, 1.0)
    lines, cur, w = [], "", 0.0
    for ch in text:
        if ch == "\n":
            lines.append(cur); cur, w = "", 0.0
            continue
        cw = 1.0 if ord(ch) > 0x2E80 else 0.5
        if w + cw > em_per_line and cur:
            lines.append(cur); cur, w = ch, cw
        else:
            cur += ch; w += cw
    if cur or not lines:
        lines.append(cur)
    return lines


def _draw_text(ax, shape, sw_in: float) -> None:
    left, top = _in(shape.left), _in(shape.top)
    width = _in(shape.width) or sw_in
    y = top + 0.06
    for para in shape.text_frame.paragraphs:
        runs = [r for r in para.runs if r.text]
        if not runs:
            y += 0.14
            continue
        size = next((r.font.size.pt for r in runs if r.font.size), 18.0)
        color = next((_hex(r.font.color) for r in runs if _hex(r.font.color)), "#313131")
        bold = any(r.font.bold for r in runs)
        indent = 0.22 * (para.level or 0)
        text = "".join(r.text for r in runs)
        for line in _wrap(text, width - indent, size):
            ax.text(left + indent, y, line, fontsize=size * 0.92, color=color,
                    fontweight="bold" if bold else "normal",
                    ha="left", va="top", zorder=3)
            y += size / 72.0 * 1.35
        y += 0.05


def render(pptx_path: Path, out_path: Path, png_dir: Path | None = None) -> int:
    prs = Presentation(str(pptx_path))
    sw_in = _in(prs.slide_width or Emu(12192000))
    sh_in = _in(prs.slide_height or Emu(6858000))
    n = 0
    with PdfPages(out_path) as pdf:
        for idx, slide in enumerate(prs.slides, 1):
            fig = plt.figure(figsize=(sw_in, sh_in), dpi=110)
            ax = fig.add_axes((0, 0, 1, 1))
            ax.set_xlim(0, sw_in); ax.set_ylim(sh_in, 0)   # 左上原点(pptx と同じ向き)
            ax.axis("off")
            ax.add_patch(Rectangle((0, 0), sw_in, sh_in, facecolor="white", zorder=0))
            for shape in slide.shapes:
                if shape.left is None:
                    continue
                l, t = _in(shape.left), _in(shape.top)
                w, h = _in(shape.width), _in(shape.height)
                if shape.shape_type == 13:                      # PICTURE
                    try:
                        img = plt.imread(io.BytesIO(shape.image.blob))
                        ax.imshow(img, extent=(l, l + w, t + h, t), zorder=2,
                                  aspect="auto")
                    except Exception:                            # noqa: BLE001
                        ax.add_patch(Rectangle((l, t), w, h, fill=False, zorder=2,
                                               edgecolor="#C0392B", linestyle="--"))
                        ax.text(l + w / 2, t + h / 2, "[画像を描画できず]", ha="center",
                                va="center", fontsize=9, color="#C0392B", zorder=3)
                    continue
                if shape.has_text_frame and shape.text_frame.text.strip():
                    _draw_text(ax, shape, sw_in)
                    continue
                fill = None
                try:
                    if shape.fill.type is not None:
                        fill = _hex(shape.fill.fore_color)
                except (AttributeError, TypeError, ValueError):
                    fill = None
                if fill:
                    ax.add_patch(Rectangle((l, t), w, h, facecolor=fill, zorder=1,
                                           edgecolor="none"))
            ax.text(sw_in - 0.06, sh_in - 0.04, f"[preview p{idx}]", ha="right",
                    va="bottom", fontsize=6, color="#9a9a9a", zorder=4)
            pdf.savefig(fig)
            if png_dir is not None:
                fig.savefig(png_dir / f"slide-{idx:02d}.png", dpi=96)
            plt.close(fig)
            n = idx
    return n


def main(argv: list[str]) -> int:
    ap = argparse.ArgumentParser(description=".pptx を目視確認用 PDF に描き起こす")
    ap.add_argument("pptx")
    ap.add_argument("-o", "--out", default=None)
    ap.add_argument("--png-dir", default=None,
                    help="1 スライド 1 枚の PNG も書き出す(PDF が開けない環境用)")
    args = ap.parse_args(argv)
    src = Path(args.pptx).resolve()
    if not src.exists():
        print(f"not found: {src}", file=sys.stderr)
        return 2
    out = Path(args.out).resolve() if args.out else src.with_suffix(".preview.pdf")
    out.parent.mkdir(parents=True, exist_ok=True)
    png_dir = None
    if args.png_dir:
        png_dir = Path(args.png_dir).resolve()
        png_dir.mkdir(parents=True, exist_ok=True)
    n = render(src, out, png_dir)
    print(f"wrote {out}  ({n} pages, {out.stat().st_size / 1024:.0f} KB)")
    if png_dir:
        print(f"wrote {n} PNGs -> {png_dir}")
    print("NOTE: 近似レンダラです。位置・重なり・落丁の確認用で、字送りは配布先アプリと"
          "一致しません。", file=sys.stderr)
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
