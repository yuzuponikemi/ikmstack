# ---
# jupyter:
#   jupytext:
#     formats: ipynb,py:percent
#     text_representation:
#       extension: .py
#       format_name: percent
#   kernelspec:
#     display_name: Python 3
#     language: python
#     name: python3
# ---

# %% [markdown]
# # 検算ノートブック: ⟦E###-R###⟧ ⟦レポート短題⟧
#
# **per-report 検算(1レポート1検算)**。検証対象は1本のレポート ⟦E###-R###⟧。
# その数値主張と**載せる各図を作るまでの計算過程**を、パイプラインと独立に計算し直して突き合わせる。
# - 被検査対象(subject): ⟦pipeline スクリプトと出力(中間CSV/統計CSV/図PNG)⟧
# - 独立再計算(this notebook): 同じ生/中間データから別ルートで計算し突合
# 炙り出す論点(例): ⟦パーセンタイル算法 / std 自由度 / センチネルスコープ / スライス / data-era⟧

# %%
import re          # for parsing captured pipeline stdout (see run_script)
import statistics
import subprocess
import sys
from pathlib import Path

import numpy as np
import pandas as pd
from IPython.display import Image, display
# from matplotlib.cbook import boxplot_stats  # ← 箱ひげ図の四分位を検算するとき

NB_DIR = Path(__file__).resolve().parent if "__file__" in globals() else Path.cwd()
EXP = NB_DIR.parent
OUT = EXP / "outputs"          # ⟦pipeline 出力の置き場に合わせる⟧
FIG = EXP / "figures"          # ⟦図PNGの置き場⟧
SCRIPTS = EXP / "scripts"
LONG_CSV = OUT / "⟦intermediate.csv⟧"   # gitignore されがち(大)
STATS_CSV = OUT / "⟦stats.csv⟧"          # tracked されがち
# 検算の前提: 中間物と統計/図を同一ランに揃える。ずれると型 i の件数突合が(正しく)落ちる。
assert LONG_CSV.exists() and STATS_CSV.exists(), (
    "pipeline 出力が無い/不整合。まず1ランで揃える:\n"
    f"  python -X utf8 {SCRIPTS / '⟦analyze.py⟧'}\n"
    f"  python {SCRIPTS / '⟦plot.py⟧'}")

# %% [markdown]
# ### 表描画ヘルパ(Styler で HTML table。`print(df.to_string())` の <pre> は崩れる)

# %%
_TABLE_STYLES = [
    {"selector": "table", "props": "border-collapse:collapse; font-size:12px; margin:4px 0;"},
    {"selector": "th", "props": "background:#efedf6; color:#2d2a4a; padding:3px 8px; "
                                 "border:1px solid #d8d4e8; text-align:right;"},
    {"selector": "td", "props": "padding:3px 8px; border:1px solid #e7e4f0; text-align:right; "
                                 "font-variant-numeric:tabular-nums;"},
    {"selector": "caption", "props": "caption-side:top; text-align:left; font-weight:600; "
                                     "color:#2d2a4a; padding:4px 0;"},
]


def show(df, caption=None, highlight=None, precision=4):
    """DataFrame -> clean HTML table. `highlight`=cols flagged red when >~0 (diff columns)."""
    sty = (df.style.format(precision=precision, na_rep="").hide(axis="index")
           .set_table_styles(_TABLE_STYLES))
    if caption:
        sty = sty.set_caption(caption)
    if highlight:
        cols = [c for c in highlight if c in df.columns]
        if cols:
            sty = sty.map(lambda v: "color:#b3261e; font-weight:600;"
                          if isinstance(v, (int, float)) and v > 1e-9 else "", subset=cols)
    display(sty)


def _pct_nearest(sorted_vals, q):
    """Nearest-rank percentile — replicate the pipeline's convention if it uses one."""
    if not sorted_vals:
        return np.nan
    return sorted_vals[min(len(sorted_vals) - 1, int(q * (len(sorted_vals) - 1) + 0.5))]


def run_script(path, *, cwd=None):
    """Run a pipeline/plot script as a black box and return its stdout (the subject under test).

    encoding="utf-8" is REQUIRED, not optional. The child is launched with -X utf8 so it
    emits UTF-8, but a kernel started WITHOUT -X utf8 (this is how nbconvert runs) would
    otherwise decode the pipe with the Windows locale (cp1252) and mojibake non-ASCII —
    e.g. "±" -> "Â±" — silently breaking any downstream string match (panel/state names).
    The trap hides because a direct `python -X utf8 verify.py` run decodes fine; only the
    nbconvert render fails. See memory: subprocess-utf8-decode-windows.
    """
    p = subprocess.run([sys.executable, "-X", "utf8", str(path)],
                       capture_output=True, text=True, encoding="utf-8",
                       cwd=str(cwd) if cwd else str(EXP))
    assert p.returncode == 0, p.stderr
    return p.stdout


TOL = 1e-3
long = pd.read_csv(LONG_CSV, encoding="utf-8-sig")

# %% [markdown]
# ## 1. 入力サニティ(抽出結果を人間の目に晒す)
# ⟦列スキーマ・件数・圧力/状態など、後段の乖離が「計算違い」か「入力違い」かを切り分ける前提を出す⟧

# %%
# ⟦FILL: e.g. show(long["metric"].value_counts()...) ⟧

# %% [markdown]
# ## 2. data-era ドリフト(情報提供 — 非ゲート)
# レポートの数値は執筆時スナップショット。再実行で母数が動くのは正常なので **assert しない**。
# 凍結値は対象レポートから転記(出典明記)。

# %%
# ⟦FILL: R###_FROZEN = {...}; 現在値と並べて show(); assert しない⟧

# %% [markdown]
# ## 3. 数値主張の検算(型 i: 独立再計算 + 統計CSV突合)
# 算法選択を暴くため、**パーセンタイル/std を両方**計算して並べ、どちらが pipeline と一致するかを見る。

# %%
# ⟦FILL: recompute each row (median / p_nearest vs p_numpy / std_pop vs std_samp),
#        merge with pipeline stats CSV, show(diff, highlight=[...]),
#        assert median一致 & p_nearest一致 & not p_numpy & std_pop一致 & not std_samp ⟧
# If the pipeline prints its answer instead of writing a CSV, capture it black-box:
#   out = run_script(SCRIPTS / "⟦analyze.py⟧"); parse `out` with re (utf-8-safe helper).

# %% [markdown]
# ## 4. 図を作るまでの計算過程の検算(図ごと)
# レポートが載せる**各図**について: ①図がエンコードする統計を独立再計算 → ②図PNGと並べる
# ③不変条件を assert(圧力/スライス・n・ソート順・センチネルスコープ)。
# 箱ひげは matplotlib が描く四分位(`boxplot_stats`)を被検査値に、numpy 線形で独立突合できる。

# %%
# ⟦FILL per figure: recompute -> show(table) -> assert invariants -> display(Image(FIG/"NN_*.png")) ⟧

# %% [markdown]
# ## 5. 境界検査(型 ii: 件数突合 / silent-drop)
# 一本道変換は独立再計算が作れないので、「出力を生むはずの入力があるのに出力が出ているか」を件数で突合。
# 見つからない罠は**捏造せず degrade**(サンプルに無ければ「無い」と正直に報告)。

# %%
# ⟦FILL: per-device / per-state counts; input>0 -> output>0; assert or honest degrade ⟧

# %% [markdown]
# ## 6. パイプラインの決定的ロジック(隠さない)

# %%
def show_span(path, lo, hi, title):
    src = path.read_text(encoding="utf-8").splitlines()
    print(f"\n# ===== {title}  ({path.name} L{lo}-{hi}) =====")
    print("\n".join(src[lo - 1:hi]))


# ⟦FILL: show_span(SCRIPTS/"...", <lo>, <hi>, "<what>") for the decisive functions ⟧

# %% [markdown]
# ## まとめ(この検算で炙り出したこと)
# ⟦FILL: 番号付きで、算法選択・スライス・スコープ・data-era・カバレッジ主張の裏取りを列挙⟧
