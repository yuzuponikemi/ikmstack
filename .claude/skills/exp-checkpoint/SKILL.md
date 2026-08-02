---
name: exp-checkpoint
description: At a milestone for an experiment, bring its uppercase living docs and INDEX up to date and write the log — in one fixed pass so nothing is skipped. Run REPORT.md (always), PLAN.md / DECISIONS.md / MANIFEST.md (if changed), regenerate INDEX with report_meta.py, then write/update the lab log. Use whenever a piece of work reaches a stopping point ("一区切りついた", "ドキュメントを最新化して", "実験をチェックポイント").
---

# exp-checkpoint — 実験の区切り同期

作業が一区切りついた段階で、実験の各種リビング文書（大文字系ファイル）、インデックス、日次ログを一元的に最新化します。

> [!IMPORTANT]
> **作業開始前の義務**:
> ドキュメントの同期を開始する前に、必ず詳細な確認対象と手順が記載された以下のリファレンスドキュメントを `view_file` で読み込んでください。
> - [exp-checkpoint 同期手順・詳細](references/checkpoint_procedure.md)

## Step 0: 作業ディレクトリを解決（必須）

同期対象は**記録層（ノート）の中**の実験。プロダクト repo から起動された場合も、
まずノート根へ移動する（③ プロダクトを汚さない）:

```bash
cd "$(python3 "$(cat ~/.ikmstack/install-path)/tools/sidecar.py" notebook)"
```

以降の相対パス（`tools/…` / `experiments/…`）はここから解決する。ただし手順3の
**日次ログだけは `lab-log` 規約に従いサイドカー分岐する**（起動元 repo に紐づくため。
`sidecar.py ensure` が返すディレクトリに書く）。詳細は
[記録のルーティング規約](../../../docs/conventions/record-routing.md)。

## 実行の流れ

1. **リビング文書 (大文字系) の同期**:
   - `REPORT.md` は必須更新。
   - `PLAN.md` / `DECISIONS.md` / `MANIFEST.md` は変更があった場合に更新。

2. **INDEX の再生成**:
   - フロントマターの変更後、`python3 tools/report_meta.py` および `python3 tools/report_meta.py --check` を実行して整合性を確認します。

3. **日次ログの作成と報告**:
   - 日次ログ（`logs/` 下）を `lab-log` 規約で更新し、最後に更新・確認結果をユーザーに報告します。
