---
name: exp-report
description: Author and register an experiment report using the lab house style — header block (type/status/date/data-era/summary), YYYYMMDD naming, INDEX.md registration with status badges, data-hygiene and no-exaggeration rules. Use when writing up an analysis, measurement, or investigation as a report in any experiment ("レポートにまとめて", "結果レポートを書いて").
---

# exp-report — 実験レポートの作成規約

実験レポートの構成や体裁を全実験で統一し、情報のトレーサビリティを担保します。

> [!IMPORTANT]
> **作業開始前の義務**:
> レポート作成および INDEX の更新を開始する前に、必ず詳細な命名規約や YAML フロントマターの記述例が記載された以下のリファレンスドキュメントを `view_file` で読み込んでください。
> - [exp-report 詳細ガイド・テンプレート](references/exp_report_guide.md)

## Step 0: 作業ディレクトリを解決（必須）

レポートは**記録層（ノート）の中**の実験ディレクトリに書く。プロダクト repo から
起動された場合も、まずノート根へ移動する（③ プロダクトを汚さない）:

```bash
cd "$(python3 "$(cat ~/.ikmstack/install-path)/tools/sidecar.py" notebook)"
```

以降の相対パス（`tools/…` / `experiments/…`）はここから解決する。詳細は
[記録のルーティング規約](../../../docs/conventions/record-routing.md)。
`notebook 未登録` エラーなら `./setup --notebook <dir>` の実行を案内する。

## レポート作成手順

1. **構成の決定とファイル作成**:
   - 単一レポートは `REPORT.md`、複数に渡る場合は `reports/` 下に一次記録ファイル（`E###-R###_...`）を作成します。
   <!-- policy:report-naming-numbering@eb565f44 -->
   - `references/exp_report_guide.md` に記載されている YAML フロントマター（メタデータ）を先頭に必ず記述します。

2. **INDEX の自動生成**:
   - フロントマターの記述後、以下のコマンドを実行してインデックス表を更新・検証します。
   ```sh
   # INDEX の再生成
   python3 tools/report_meta.py

   # 整合性検証
   python3 tools/report_meta.py --check
   ```
   <!-- policy:report-meta-regen@a43c35f7 -->

## 撤回(retraction)を書く

結論・数値を後から取り消したら、**新しい一次記録の frontmatter に撤回の記録を残す**。
これは pre-commit が検査する数少ない意味ルールで、**リンクが解決しないと commit が止まる**。

```yaml
corrects: E###-R00X          # 覆した一次記録(同一実験内。複数可)
retraction_type: stale-source  # 統制語彙(reporting.md の表)
discovered_by: self            # self | user-sme | independent-audit
```
<!-- policy:retraction-record@b39a00ca -->

覆された側(旧版)には `status: superseded` と **`superseded_by:`** を必ず添える。
正本: docs/conventions/reporting.md「改訂・撤回の記録」
