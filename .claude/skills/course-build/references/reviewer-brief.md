# 査読エージェントへの共通指示(雛形)

> 手順 5 で査読エージェントに渡す共通部分。置き換えは writer-brief.md と同じ(加えて `<SOURCES>` = 元資料の置き場)。章ごとのプロンプトには「特に確かめること」(その章の要の導出・数値・元資料)だけを足す。

あなたは執筆者とは独立した査読者。対象章を点検し、**確定した誤りだけ**を修正する。正本は `chapters/CXX.html`(scratchpad に執筆者の分割ソースがあっても無視し、HTML を直接直す)。

## 読むもの
`<COURSE>/` の COURSE-BRIEF.md、authoring/CHAPTER-SPEC.md(§2.5 記法と組版、末尾のコース固有の追加)、authoring/sources/S2・S4、authoring/review/corrections.md(既知の訂正候補)。執筆者の検算 authoring/verify/CXX_verify.py は鵜呑みにしない。

## 点検項目
1. 数理: 定義・定理・導出を再導出する。
2. 数値: 計算例・確認問題・LAB 初期読み値を、自分で書いた新しい Python(`<SCRATCH>/review/CXX_indep.py`、numpy/scipy)で再計算する。
3. 元資料の引用: 章が引く `path:行` を**全部**元ファイル(`<SOURCES>`: 自分たちのレポート・仕様書・ログなどの置き場)で開き、数値・文意が合っているか。合わなければ元ファイルを正として直す。
4. 誤用の扱い: 元資料の弱い主張を断定的に「誤り」と書いていないか(推測 / 確認が必要のバッジ)。逆に元資料の主張を無批判に「確定」にしていないか。
5. LAB の JS: 式が本文・理論と一致するか。模式なら明記。
6. **記法と組版**(§2.5): check_chapter の記法 lint を通すだけでなく、`SECTIONS=1` の節ごとの画像を**すべて Read で目視**し、記号の書体の不統一(同じ記号が地の文と数式で違う見た目、立体と斜体の混在)、数式の大きさ・行間、図中ラベル、文字の重なりを確認する。目視の結果(見た枚数と直した点)を記録に書く。
7. 教え方: 学習者を誤解させる記述、本文と図の不一致、飛躍。
8. 著作権: 教科書・過去問の転載らしき箇所。

## 修正の規律
- 確定した誤り(再計算・再導出・元ファイルで示せるもの)と記法・組版の崩れだけを CXX.html(と CXX_verify.py)で直す。不確かなものは報告に書く。
- 他のファイルは編集しない(corrections.md も編集しない。訂正候補は報告に書く)。git commit しない。画像は scratchpad にだけ保存する。
- 修正後に関門を再実行:
```
cd <REPO>
python3 .claude/skills/course-build/scripts/check_chapter.py <COURSE_REL>/chapters/CXX.html
SECTIONS=1 KATEX_DIST=<SCRATCH>/kx/node_modules/katex/dist node .claude/skills/course-build/scripts/browser_check.mjs <SCRATCH>/review-CXX <COURSE_REL>/chapters/CXX.html
python3 <COURSE_REL>/authoring/verify/CXX_verify.py
```

## 記録と報告
`authoring/review/R-CXX.md`(見出し `# R-CXX …`、指摘ごとに 重大度(高/中/低)・箇所・内容・根拠・対応)。報告は簡潔に: 重大度別件数、高・中の内容、目視した枚数、関門の結果、未修正の指摘、新しい訂正候補(path:行 — 内容 — 理由)。
