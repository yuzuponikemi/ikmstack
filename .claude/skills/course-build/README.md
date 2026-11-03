# course-build

任意の知識体系を、単元ごとの章別 HTML 学習ページ(インタラクティブな図・計算例・確認問題つき)と入口ページからなる学習コースに仕立てる Claude Code のスキルです。

## 入れ方

このフォルダ(`course-build/`)を次のどちらかに置きます。

- 自分用: `~/.claude/skills/course-build/`
- プロジェクト用: `<プロジェクト>/.claude/skills/course-build/`

Claude Code で「〇〇の学習教材を作って」「単元ごとの学習ページを作りたい」と頼むと起動します。最初に企画相談(章立て・材料・方向性)から始まります。

## 必要なもの

- Python 3.9 以上
- Node.js 18 以上
- Playwright(ブラウザ検査用。`npm i playwright` と `npx playwright install chromium`)
- 数式を描画するための KaTeX。通常は CDN から読み込まれます。ネットワークが遮断された環境では `sh scripts/setup_katex.sh <保存先>` でローカルに入れます(npm が必要)
- 統計・数値計算の教材の検算には numpy / scipy(スキル自体には不要)

## 中身

- `SKILL.md`: 工程(企画相談 → 一次資料ダイジェスト → 章仕様 → 並行執筆 → 関門 → 独立レビュー → 公開)
- `references/`: 章の執筆仕様、コースの型(`profiles/`)、企画書・執筆指示・査読指示の雛形
- `assets/`: 共通の CSS と JS、章と入口ページの雛形
- `scripts/`: コースの雛形生成(`new_course.py`)、構成と記法の検査(`check_chapter.py`)、ブラウザ検査(`browser_check.mjs`)、自己検査(`selftest.py`)

## 動作確認

```
python scripts/selftest.py --browser
```

`ALL PASS` と出れば、検査の各規則と雛形の生成が動いています(`--browser` は Playwright が必要)。

## 注意

- 公開されている教科書・試験問題の本文・図・問題は転載しない前提で作られています(`references/profiles/exam-cert.md`)。
- 章の HTML は Google Fonts と(数式のある章では)cdnjs の KaTeX を読み込みます。外部読み込みを避けたい場合は、フォントと KaTeX を同梱して `assets/` のリンクを書き換えてください。
- 配布・再配布の条件は、このスキルを配布する組織が決めてください(このファイルにはライセンスを含めていません)。
