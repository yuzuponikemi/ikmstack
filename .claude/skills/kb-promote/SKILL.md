---
name: kb-promote
description: Promote settled findings from an experiment to a shared Knowledge Base (KB) — extract confirmed knowledge from the report, draft a polished doc under KB/docs/, open a PR, and link the promotion target back from the report. Use when an experiment's conclusions are final ("KB に昇格して", "確定知見をまとめて").
---

# kb-promote — 確定知見のナレッジベース昇格

実験で得られた**確定した知見だけ**を清書して、長期共有のためのナレッジベース（KB）へ移す。

## 手順

### 1. 昇格対象の抽出

- 実験の `REPORT.md`(現状サマリ＝唯一の権威)から**確定事実のみ**抽出。
  未解決指摘が残る項目、暫定値は昇格しない(レポートに留める)。
- 校正値などは適用範囲(装置・条件)を明記する。

### 2. 配置先の決定

ナレッジベース内の適切なカテゴリ（例：トラブルシューティング、仕様、運用手順、アーキテクチャ）に配置。
既存ページに追記すべきか新規ページかを先に判断する。

### 3. 清書

- 推敲した完成文書として書く(ログ調・時系列調にしない)。
- 根拠として実験ディレクトリ・レポート・チケットを参照リンク。

### 4. PR 作成(KB 側)

1. ナレッジベースリポジトリでブランチを切り、コミットする。
2. プルリクエスト（PR）を作成し、PR 本文に昇格元（実験のパス）を記載する。

### 5. リンクバック(実験リポジトリ側・必須)

- 実験の `REPORT.md` に昇格先を追記:
  ```markdown
  ## KB 昇格
  - <知見の一行要約> → `[KB_REP_NAME]/docs/<path>`(PR #N)
  ```
- 当日のログにも昇格した旨を一行残す。
