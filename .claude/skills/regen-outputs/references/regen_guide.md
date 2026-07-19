# regen-outputs ローカル再生成・詳細ガイド

本ドキュメントは、Git 管理対象外の図や自動生成レポートをローカルで再生成・プレビューする際の手順と規約をまとめています。

---

## 1. 原則 (図は git にコミットしない)

三大原則#1 に基づき、図（グラフやプロットなど）は Git 管理下に置きません。Git に保存するのは「テキストと生成スクリプト」のみです。
図付きでレポートをプレビューしたいときは、各実験の **`regenerate.ps1`** を実行して決定論的に図を再生成します。

---

## 2. 再生成の手順

1. **対象実験の決定**:
   - 再生成したい実験ディレクトリ（例: `experiments/E001_my-topic/`）を確認します。
2. **Drive データの用意 (R1規約)**:
   - 入力データの正本は Google Drive 上に存在する必要があります。
   - `regenerate.ps1` が Drive フォルダを直読みするため、共有ドライブが見える状態にしておきます。
   - **PC のドライブレターが異なる場合**: `-DriveRoot 'X:\Shared drives\...\my-lab-repo'` のように引数で DriveRoot を渡します。
3. **スクリプトの実行**:
   ```powershell
   pwsh experiments/E###_<topic>/regenerate.ps1
   ```
4. **レポートのプレビュー**:
   - `REPORT.md` や `reports/*.md` をプレビューします。
   - 図は `_generated/`（または一部古い形式では `figures/`）に生成され、Markdown 内の相対リンク解決によって画像が表示されるようになります。

---

## 3. 出力先規約 (R2・R3)

- **新規実験 (R2)**: 図の出力先は `.gitignore` された `_generated/` ディレクトリに統一します。
- **図リンクの整合性 (R3)**: 
  - 図リンクが出力先とずれていると画像が表示されません。
  - `tools/check_report_figures.py` がこれを事前検査し、誤りがあれば Git コミットが防止（pre-commit）されます。

---

## 4. `regenerate.ps1` がない実験の立ち上げ

新規の実験や `regenerate.ps1` を持たない古い実験では、`experiments/_template/regenerate.ps1` を雛形（テンプレート）としてコピーし、入力データと出力パスに合わせてカスタマイズします。
