---
name: regen-outputs
description: Regenerate an experiment's figures and auto-reports locally so reports preview with images — sync raw data from Drive, run the experiment's regenerate.sh, open the generated .md. Figures are not committed to git (AGENTS.md 三大原則#1); this is how anyone (esp. on a fresh clone) reads reports with figures. Use when "図付きで読みたい", "レポートをプレビュー", "図を再生成", "regenerate を回して"
---

# regen-outputs — 図・自動レポートのローカル再生成

Git 管理外の図や自動生成レポートを、生データと `regenerate.sh` を用いて決定論的にローカルで再生成し、画像付きでレポートをプレビューできるようにします。

> [!IMPORTANT]
> **作業開始前の義務**:
> 再生成を実行する前に、必ず Drive の同期ルールや出力先規約が記載された以下のリファレンスドキュメントを `view_file` で読み込んでください。
> - [regen-outputs 詳細ガイド・規約](references/regen_guide.md)

## Step 0: 作業ディレクトリを解決（必須）

対象の実験は**記録層（ノート）の中**にある。プロダクト repo から起動された場合も、
まずノート根へ移動する（出力先の `.gitignore` 規約もノート側にあるため）:

```bash
cd "$(python3 "$(cat ~/.ikmstack/install-path)/tools/sidecar.py" notebook)"
```

詳細は [記録のルーティング規約](../../../docs/conventions/record-routing.md)。

## 再生成の実行コマンド

1. **Google Drive データの同期確認**:
   - 入力データ（Drive 側）が最新であることを確認します。

2. **再生成の実行**:
   ```powershell
   sh experiments/E###_<topic>/regenerate.sh
   ```
   ※ Drive のマウント先が既定と違う場合は、環境変数 `LAB_DRIVE` で上書きします。
