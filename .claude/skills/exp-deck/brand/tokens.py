"""組織のブランドトークン —— pptx(deckgen) と CSS の単一ソース.

標準スライドの配色・字面を1か所に集約する。deckgen.py はここを import してテーマに使う。
スクリプトとして実行すると、隣に `brand.css`(HTML/Artifact 用の再利用スタイル)を再生成する:

  python .claude/skills/exp-deck/brand/tokens.py

色は '#' 無しの 16進(pptx の RGBColor が使いやすいため)。CSS 側では '#' を補う。
"""
from pathlib import Path

# --- palette (hex, no '#') ----------------------------------------------------
PURPLE      = "531872"  # primary brand purple (band, rules)
PURPLE_DEEP = "3D1259"  # gradient start / depth
PURPLE_HEAD = "6C2A87"  # headings(セクション見出し・level-0 箇条書き)
GREEN       = "4E9D69"  # accent(brand sage #73AE7A を小文字でも読めるよう少し濃く)
GREEN_DISP  = "5FA873"  # 大きな表示用(セクション/ディバイダのタイトル)
INK         = "313131"  # 見出し・本文テキスト
GRAY        = "6B6B6B"  # 補足・抑えめ
FOOTER_BG   = "EAEAEA"  # フッターの細帯
ORANGE      = "E89A51"  # データ副系列
RED         = "C0392B"  # 機能色: 制約/トレードオフ・行動・要注意(ブランド色ではない)
WHITE       = "FFFFFF"

FONT_JP    = "Meiryo"    # 日本語が崩れない
FONT_LATIN = "Segoe UI"  # deck に近いヒューマニスト・サンセリフ

# deck.py の color 文字列 → 実色(後方互換: "navy" は今やブランド紫)
SEMANTIC = {
    "navy":   PURPLE_HEAD,
    "purple": PURPLE_HEAD,
    "green":  GREEN,
    "red":    RED,
    "gray":   GRAY,
    "ink":    INK,
    "white":  WHITE,
}


def _css() -> str:
    h = lambda c: "#" + c
    return f"""/* Brand Theme — 再利用可能スライド/ドキュメント スタイル.
   自動生成: brand/tokens.py が単一ソース。手で編集せず tokens.py を直して再生成すること。
   使い方(HTML): <link rel="stylesheet" href="brand.css"> し、.brand-slide / .brand-band /
   .brand-title / .brand-h / .brand-accent / .brand-tradeoff / .brand-footer / .brand-source を使う。 */
:root {{
  --brand-purple:       {h(PURPLE)};
  --brand-purple-deep:  {h(PURPLE_DEEP)};
  --brand-purple-head:  {h(PURPLE_HEAD)};
  --brand-green:        {h(GREEN)};
  --brand-green-disp:   {h(GREEN_DISP)};
  --brand-ink:          {h(INK)};
  --brand-gray:         {h(GRAY)};
  --brand-footer-bg:    {h(FOOTER_BG)};
  --brand-orange:       {h(ORANGE)};
  --brand-red:          {h(RED)};
  --brand-font: "{FONT_LATIN}", "{FONT_JP}", system-ui, sans-serif;
}}

.brand-slide {{
  position: relative; box-sizing: border-box;
  width: 100%; max-width: 1280px; aspect-ratio: 16 / 9; margin: 0 auto;
  background: #fff; color: var(--brand-ink);
  font-family: var(--brand-font); padding: 3.2% 4% 5%;
}}

/* 表紙/ディバイダのグラデ帯(背景画像を入れるなら background-image を足す) */
.brand-band {{
  background: linear-gradient(105deg, var(--brand-purple-deep) 0%, var(--brand-purple) 55%, var(--brand-purple-head) 100%);
  color: #fff;
}}
.brand-slide--title {{ padding: 0; }}
.brand-slide--title .brand-band {{ height: 55%; padding: 5% 4%; }}

/* コンテンツ見出し: 濃色タイトル + テーマカラーの細罫 */
.brand-title {{ font-size: 2.0rem; font-weight: 700; color: var(--brand-ink); margin: 0 0 .35rem; }}
.brand-title::after {{ content: ""; display: block; height: 3px; background: var(--brand-purple); margin-top: .4rem; }}
.brand-eyebrow {{ font-size: .8rem; letter-spacing: .08em; text-transform: uppercase; color: var(--brand-gray); }}

.brand-h        {{ color: var(--brand-purple-head); font-weight: 700; }}   /* 見出し(navy相当) */
.brand-accent   {{ color: var(--brand-green); font-weight: 700; }}         /* 緑の強調・区切り */
.brand-display  {{ color: var(--brand-green-disp); font-weight: 700; font-size: 2.4rem; }}
.brand-tradeoff {{ color: var(--brand-red); font-weight: 700; }}           /* 制約/トレードオフ・要注意 */
.brand-muted    {{ color: var(--brand-gray); }}

/* 図/表の出典(自己完結の来歴) */
.brand-source {{ font-size: .62rem; color: var(--brand-gray); line-height: 1.35; }}

/* フッター: 左ロゴ(別途 img)・右ページ番号 */
.brand-footer {{
  position: absolute; left: 0; right: 0; bottom: 0; height: 6%;
  display: flex; align-items: center; justify-content: space-between;
  padding: 0 1.5%; font-size: .6rem; color: var(--brand-gray);
  border-top: 1px solid var(--brand-footer-bg);
}}
.brand-footer img {{ height: 60%; }}
"""


if __name__ == "__main__":
    out = Path(__file__).with_name("brand.css")
    out.write_text(_css(), encoding="utf-8")
    print("wrote", out)
