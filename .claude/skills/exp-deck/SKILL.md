---
name: exp-deck
description: Generate a shareable, peer-review-ready slide deck (.pptx) from an experiment's report — restructure REPORT.md into the "背景→結論→行動→根拠→確度→Discussion/Future Work" narrative that doubles as a consulting-style message AND a rigorous discussion substrate (reproducibility, trade-offs, fact-vs-inference, open questions), build a real editable PowerPoint with python-pptx (figures embedded, per-figure provenance), verify it visually, and deliver to the experiment's Google Drive folder so members without GitHub access can view and co-edit. Use when wrapping up an analysis for sharing/reporting to other members ("報告スライドを作って", "まとめスライドにして", "メンバに共有できる形にして", "レポートをスライド化").
---

# exp-deck — 報告スライド (.pptx) の生成

`REPORT.md` (作業記録) を、GitHub を見られない他メンバーに共有可能な PowerPoint 形式 (`.pptx`) の伝達資料に変換します。

> [!IMPORTANT]
> **トークン節約とコンテキスト管理の義務**:
> 親エージェントは、本プロセスにおいて `REPORT.md` や `PLAN.md` などの巨大な原稿ドキュメント、および生成される `deck.py` のコードを直接 `view_file` 等で読み込んではいけません。必ず独立した一時的な **Subagent (サブエージェント)** を起動し、スライドの設計・執筆・ビルド・検証作業を完全に委譲してください。親エージェントのコンテキストには、作成結果と構成のサマリーのみを記録し、長大な原稿テキストの流入を防いでください。

> [!IMPORTANT]
> **作業開始前の義務**:
> 本スキルを実行・適用する前に、必ず詳細なデザイン原則、Subagent への指示プロンプトテンプレート、および検証手順が記載された以下のリファレンスドキュメントを `view_file` で読み込んでください。
> - [exp-deck 詳細ガイド・デザイン原則](references/deck_design_principles.md)

## Step 0: 作業ディレクトリを解決（必須。Subagent にも引き継ぐ）

対象の実験・`deck.py`・図はすべて**記録層（ノート）の中**にある。プロダクト repo から
起動された場合も、まずノート根へ移動する:

```bash
cd "$(python3 "$(cat ~/.ikmstack/install-path)/tools/sidecar.py" notebook)"
```

`deckgen.py` は install 先の `.claude/skills/exp-deck/` にあるため、ノート根から呼ぶ場合は
`"$(cat ~/.ikmstack/install-path)/.claude/skills/exp-deck/deckgen.py"` を使う。詳細は
[記録のルーティング規約](../../../docs/conventions/record-routing.md)。

## 概要と基本手順 (Subagent への指示概要)

1. **`deck.py` の新規作成**: 
   対象実験のディレクトリに `deck.py` を作成し、ヘッダ定数とスライド定義（`SLIDES` リスト）を記述します。
   - 物語の型 (背景 → 結論 → 行動 → 根拠 → 確度 → Discussion & Future Work) を厳守してください。
   - メリットだけでなく、「制約/トレードオフ」項目（赤 `red`）を必ず1つ以上含めてください。
   - `deck.py` の定義スキーマは `deckgen.py` 冒頭の docstring を参照してください。

2. **PowerPoint スライドの生成**:
   ```sh
   uv run --with python-pptx \
     "$(cat ~/.ikmstack/install-path)/.claude/skills/exp-deck/deckgen.py" \
     experiments/<ID>/deck.py
   ```

3. **目視確認と配布**:
   LibreOffice のヘッドレス変換で PDF/PNG を書き出し、レイアウト崩れを目視で確認します(下記)。
   完成した `.pptx` および `.pdf` は Google Drive の実験フォルダへコピーし、メンバーに渡します。
