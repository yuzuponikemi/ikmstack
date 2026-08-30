---
name: exp-new
description: Scaffold a new experiment in this lab repo — copy experiments/_template, record involved repos' commit SHAs into MANIFEST.md, create the mirrored Google Drive folder, and draft PLAN.md. Use when starting a new experiment, validation, investigation, or analysis (e.g. "新しい実験を始める").
---

# exp-new — 実験立ち上げ

AGENTS.md「実験のワークフロー」手順を一括実行する。漏れやすいのは
**SHA 記録**と **Drive ミラー作成**なので必ず両方やる。

## Step 0: 作業ディレクトリを解決（必須）

実験は**記録層（ノート）の中**に作る。プロダクト repo から起動された場合も、
まずノート根へ移動する（③ プロダクトに `experiments/` を作らない）:

```bash
cd "$(python3 "$(cat ~/.ikmstack/install-path)/tools/sidecar.py" notebook)"
```

以降の相対パス（`tools/…` / `experiments/…`）はここから解決する。実験は cross-repo
なので `sidecar/<slug>/` ではなく**常にノート根**（関与 repo は MANIFEST に書く）。
詳細は [記録のルーティング規約](../../../docs/conventions/record-routing.md)。
`notebook 未登録` エラーなら `./setup --notebook <dir>` の実行を案内する。

## 入力(ユーザーに確認。引数で与えられていれば省略)

1. **topic スラッグ**(英数ケバブ、実験番号を含める。例: `E001_stage-tension`)
2. **目的・仮説**(PLAN.md に書く一行ずつでよい)
3. **関与リポジトリ**(`../` の隣接リポジトリ名。ワークスペース地図 = 親フォルダの CLAUDE.md 参照)

## 手順

1. **実験IDを採番する(コピーより先)** — 採番済みの最大番号を見て +1 する:
   ```bash
   ls -d experiments/E* 2>/dev/null | sort
   ```
   「直前に見た実験の次だから E010」と機械的に決めない。**並行セッションが先に採番している
   ことがある**(実際に E010 を二重採番し、事後に E011 へ改番して復旧した)。
   `experiments/INDEX.md` は commit 済みの `REPORT.md` から生成されるので採番直後の実験は
   載らない — **ディレクトリ一覧が採番済みの真実**。
   正本: AGENTS.md「実験 ID と 命名規約」
   <!-- policy:experiment-id-numbering@df108c26 -->
   - フォーマットはデフォルトで `E###` (例: `E001_stage-tension`)。日付は付けない。
2. `experiments/_template/` を `experiments/<実験ID>_<topic>/` にコピー。
   **`experiments/_template` はハーネスへの symlink なので、必ず `-L` を付ける**:
   ```bash
   mkdir -p "experiments/<実験ID>_<topic>"
   cp -RL experiments/_template/. "experiments/<実験ID>_<topic>/"
   ```
   ⚠️ `cp -R experiments/_template experiments/<ID>` と書くと、macOS の `cp -R` は
   **symlink をそのままコピー**する。結果、実験ディレクトリがハーネスのテンプレを指す
   symlink になり、**以降の書き込みが全部ハーネス側のテンプレを破壊する**（実際に起きた）。
   - コピー後に `ls -ld experiments/<ID>` で **symlink でない**ことを確かめる。
3. **PLAN.md** に記入: 目的 / 仮説 / 手順(分かる範囲) / 関与リポジトリ / 関連チケット等 (設定されている場合)
4. **MANIFEST.md** に関与リポジトリの commit SHA を記録:
   ```
   git -C ../<repo> rev-parse --short HEAD
   ```
   再現性はこれで担保する(サブモジュールは使わない)
5. **Drive ミラー**を作成: `.lab-config.json` に設定されている Google Drive ルート配下の `experiments/<実験ID>_<topic>/`
   - 作成したパスを MANIFEST.md に記録。
6. **`REPORT.md` のフロントマターを記入し `experiments/INDEX.md` を生成** —
   `REPORT.md` 冒頭に `experiment_id`(=ディレクトリ名)/ `status`(初期は `planning`)/ `period_start` / `summary` を書き、`python3 tools/report_meta.py` を実行(INDEX 行を手書きしない)。
   <!-- policy:report-meta-regen@a43c35f7 -->
7. **次にやることは `PLAN.md`(次の計画)に書く**。

## リマインド(立ち上げ時に必要なら案内)

- データ(CSV・画像・>1MB)は git に入れず Drive へ。ローカル一時作業は `data/`(.gitignore 済)
- **図は git に入れない**。`regenerate.sh`(テンプレに同梱)を実験の入力/出力に合わせて書き、
  図はローカル再生成でプレビューする(三大原則#1)。**入力は Drive 正本を直読み**(R1。ローカル固有
  パス禁止、差は Drive のマウント先のみ)、**出力は `_generated/` に統一**(R2。.gitignore 済)。
  図リンクは出力先を正しい相対深さで指す(R3。`tools/check_report_figures.py` が pre-commit で検査)
  <!-- policy:figures-not-in-git@97b4297f -->
- Notebook はセル出力をクリアして保存(`python3 tools/strip_nb_outputs.py`)
<!-- policy:nb-strip-outputs@3ca1441e -->
- レポート作成は **exp-report**、終了時の ナレッジ昇格は **kb-promote** スキルを使う。
