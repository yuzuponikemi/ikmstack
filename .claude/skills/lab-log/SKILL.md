---
name: lab-log
description: Write or update a daily lab log with the standard headings (目的/やったこと/わかったこと/次にやること), linking related experiments, repos, and KB pages. Routes automatically to the right place — the notebook's logs/ when run inside it, or the notebook's sidecar/<slug>/ when run from a product repo (keeping that repo clean). Use at session wrap-up, or when the user says "今日のログを書いて", "セッションをまとめて", "ログに残して".
<!-- policy:lab-log-format@a0eca25e -->
---

# lab-log — 日次ログ作成

セッションの作業を `<logs>/<YYYY>/<YYYY-MM-DD>_<topic>.md` に記録する。
追記中心・雑多でよい(推敲しない)。1 日に複数トピックあれば複数ファイル。

## Step 0: 書き先を解決（サイドカー経路）

**どこで作業していたか**で書き先が変わる。まず解決する（どの cwd でも動くよう
install-path 経由で呼ぶ。プロダクト repo には `tools/` が無いため相対呼びは不可）:

```bash
python3 "$(cat ~/.ikmstack/install-path)/tools/sidecar.py" ensure
```

出力の1行が**書き先の logs ディレクトリ**。以降の `<logs>` はこれに読み替える。

- **記録層(ikmnote)内で作業していた** → `<notebook>/logs/<YYYY>/`（従来通り）。
- **プロダクト repo など別リポジトリで作業していた** → `<notebook>/sidecar/<slug>/logs/<YYYY>/`
  に書く。**プロダクト repo は一切汚さない**（記録はすべて記録層に集約）。`slug` は
  その repo の git remote から決まる。`ensure` はディレクトリと（サイドカー時は）
  `README.md` も用意する。
- notebook が複数登録されていても、**その中で作業していればその notebook** に書かれる
  （既定は最後に wire したもの）。明示したいときは `--notebook <path|名前>` か
  環境変数 `IKMSTACK_NOTEBOOK`。詳細は
  [記録のルーティング規約](../../../docs/conventions/record-routing.md)。
- `notebook 未登録` エラーなら「ikmstack で `./setup --notebook <dir>` を実行」を案内する。

## Step 0.5: 過去の記録を確認（resurfacing）

**書き始める前に**、同じ文脈の過去記録を必ず見る（重複ファイルを作らない・継続作業を
見失わないため）:

```bash
python3 "$(cat ~/.ikmstack/install-path)/tools/sidecar.py" recent --limit 5
```

- 直近ログ（新しい順）と、`MANIFEST.md` がこの repo に言及している**関連実験**が返る。
- **同日・同トピックのファイルがあれば新規作成せず追記**する。
- 前回の「次にやること」が今日の作業に繋がっているなら、冒頭でその継続である旨に触れる。
- 関連実験があれば、ログから `experiments/<ID>/` へリンクを張る。

## 手順

1. Step 0 が返した `<logs>` の下に、今日の日付・トピックでファイル名を決める。
   **同日同トピックの既存ファイルがあれば追記・更新する**(重複ファイルを作らない)
2. 見出しは最低限この 4 つ:
   ```markdown
   # YYYY-MM-DD <トピック>

   ## 目的
   ## やったこと
   ## わかったこと
   ## 次にやること
   - [ ] ...
   ```
3. セッションを振り返って書く。特に拾うもの:
   - **意思決定とその理由**(採用案だけでなく不採用案と却下理由)
   - 非自明なハマりどころ
   - 確定した知見 → 「次にやること」に ナレッジベース昇格 候補として記載
4. **リンクを必ず張る**: 関連する実験ディレクトリ(`experiments/...`)、隣接リポジトリ、ナレッジベースページ
5. **次にやること**は各実験の `PLAN.md`(次の計画)/ `REPORT.md`(次のアクション)が正本。
   ログには要点だけ書き、詳細 TODO はそちらに反映する。

## 書かないもの

- 生データや大きな図(Drive + MANIFEST.md の領分)
- コードから読み取れる事実の再説明(リンクで足りる)
