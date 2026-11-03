# 執筆エージェントへの共通指示(雛形)

> 手順 3 で執筆エージェントに渡す共通部分。`<REPO>`(リポジトリの絶対パス)・`<COURSE>`(コースの絶対パス)・`<COURSE_REL>`(リポジトリからの相対パス)・`<SCRATCH>`(scratchpad)・`<REFERENCE_CHAPTER>`(作り込みの参考章、例: 既に完成した章)を置き換えて scratchpad に保存し、章ごとのプロンプトでは「このファイルを最初に読み、CXX を担当章に読み替えて従う」と書いて、章固有の中身(BRIEF の該当行・LAB 案・前後の章)だけを足す。統計コースの試作で使った文面。

## 必ず最初に読むもの
1. `<COURSE>/COURSE-BRIEF.md`(方針の正本。§1 読者と到達点、§3 材料、§4 章立て、§7 決定事項)
2. `<COURSE>/authoring/CHAPTER-SPEC.md`(章執筆仕様。全要素が必須。**§2.5 記法と組版**と末尾の「このコース固有の追加」を特に)
3. `authoring/sources/S4_*.md`(実例の台帳と注意点)、`S2_notation-and-conventions.md`(記法の約束・台帳)、`S1`・`S3`(試験範囲と問われ方)
4. 雛形 `chapters/_template.html`、`assets/course.js`(TC.canvas / TC.range / TC.seg / TC.rng / TC.randn / TC.reducedMotion / TC.renderMath / TC.MATH_MACROS)
5. インタラクティブ図の作り込みの水準の参考: `<REFERENCE_CHAPTER>`(分類・ROC の操作図がある章など、作り込みの水準が分かるもの)

## 元資料の扱い
- S4・BRIEF の数値は二次情報。**使う数値は必ず元ファイル(自分たちのレポート・仕様書・ログなど)の該当行を自分で開いて確かめ**、`<p class="src">出典: <元ファイルのパス>:行</p>` のように書く。元ファイルと合わなければ元ファイルを正とし、報告に書く。
- 元資料の統計的に弱い主張は、出典つきの事例にして断定せず `推測` / `確認が必要` バッジ。訂正候補は報告に「訂正候補: path:行 — 内容 — 理由」で列挙する。
- 元資料に無い新しい計算は「本教材の計算」と明記。

## 記法(機械で検査される)
- 記号は地の文・表・問題・キャプションでも必ず `\( \)`。Unicode のギリシャ文字・λ̂ のような合成ハット・「n = 25」を地の文に書かない。
- 演算子はマクロ `\E \Var \Cov \Corr \SE \MSE \AIC \logit \argmax \iid \T \dd` だけ(立体)。`\operatorname{Var}`・素の `E[` は不可。
- 計算例は `<div class="calc">\[\begin{aligned} … \end{aligned}\]</div>`。`pre.calc` に記号を書かない。
- 章のスクリプトで `renderMathInElement` を呼ばない(course.js が描画する)。LAB が数式を差し込むときは `TC.renderMath(el)`。
- LAB のラベル・読み値・SVG の変数は `<span class="m">`/`<text class="m">`、canvas は `italic 14px KaTeX_Math, serif`。

## 規律
- 他の章・README・COURSE-BRIEF・sources・assets・CHAPTER-SPEC は編集しない。git commit はしない。画像はリポジトリ内に作らず scratchpad にだけ保存する。
- 教科書・過去問の文章・問題・図を写さない。確認問題はオリジナル。

## 完了前の自己検査(全部実行して結果を報告)
```
cd <REPO>
python3 .claude/skills/course-build/scripts/check_chapter.py <COURSE_REL>/chapters/CXX.html
SECTIONS=1 KATEX_DIST=<SCRATCH>/kx/node_modules/katex/dist node .claude/skills/course-build/scripts/browser_check.mjs <SCRATCH>/shots-CXX <COURSE_REL>/chapters/CXX.html
python3 <COURSE_REL>/authoring/verify/CXX_verify.py
```
check_chapter(記法を含む)と browser_check を PASS させる。`shots-CXX/CXX-sNN.png`(節ごとの画像)を**全部 Read で目視**し、記号の書体の統一・数式の大きさ・図中ラベル・文字の重なりを確かめて直す。CXX-360.png も見る。

## 報告(簡潔に)
仕様要素ごとの有/無、check_chapter の info 行、browser_check の結果(katex 数)、節ごとの目視で直した点、verify の一致状況、使った元資料の path:行 一覧(元ファイルで確認済みか)、訂正候補、未完成の要素。
