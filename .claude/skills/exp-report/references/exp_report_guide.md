# exp-report 実験レポート作成規約・詳細ガイド

本ドキュメントは、実験レポートの作成手順、命名規約、およびメタデータのフロントマター仕様を詳細に定めています。

---

## 1. 配置とレポート規模の使い分け

レポートはその目的と規模に応じて、適切な場所に配置します。

- **小規模な実験** (調査1回で完了):
  - 実験ディレクトリ直下の `REPORT.md` に直接結果を記載します。
  - フロントマターの記述と「結論を冒頭に書く」原則を守れば、`reports/INDEX.md` は不要です。
- **複数レポートが発生する実験**:
  - 各セッションや検証ごとに、`reports/` 配下に「日付つき一次記録」（例: `E###-R###_...`）を作成します。
  - ディレクトリ直下には `REPORT.md`（現状サマリ＝最初に読む唯一の権威）、`PLAN.md`（現在の計画）、および長期キャンペーンに限り `DECISIONS.md`（方針転換履歴）を配置します。

---

## 2. 命名規約

- **一次記録の命名形式**: `E###-R###_<YYYYMMDD>_<内容>_<種別>.md`
  - `E###` = 実験ID。`R###` = この実験内で 1 から振る通し連番。
  - 次番号は `reports/INDEX.md` 内の最大 R 番号 + 1 とします。
  - 種別の一例: `設計` / `結果` / `検証` / `検討` / `再解析` / `実装` / `比較` / `監査` / `事前登録` など。
- **改訂版の命名**: 監査などで修正が必要な場合、新規に R 番号を振るのではなく、`E###-R###_<元名>_rev.md` とし、元のファイルを残します。
- **図の管理**: 図（グラフやプロットなど）は Git 管理せず、Google Drive 上のフォルダ、あるいは `.gitignore` された出力先に保存します。

---

## 3. フロントマター (YAML仕様)

メタデータは YAML フロントマターが正本となり、INDEX 表はスクリプトで自動生成されます。

### 個別レポート (`reports/E###-R###_*.md`) 用
```markdown
---
# jira: Project-###                  # 任意
report_id: E###-R###
type: <種別>                       # 結果/検証/設計/検討/再解析/実装/比較/監査/事前登録/付録/レビュー …
status: active                     # active | superseded | historical | planning
created: YYYY-MM-DD
data_era:                          # 任意
summary: <1 文で結論。INDEX の1行要約に流用>
---

# <タイトル>

> 🔗 **前提/関連/後続**: <関連レポートのファイル名(リンク)>
> 📝 **要約**: <必要なら詳細な抄録(本文側)>
```

### 実験現状サマリー (`REPORT.md`) 用
```markdown
---
# jira: Project-###                  # 任意
experiment_id: E###_<topic>       # ディレクトリ名と一致させる
status: planning                   # planning | active | done | paused
period_start: YYYY-MM-DD
period_end:                        # 空＝継続中
summary: <experiments/INDEX.md の1行要約>
---
```

---

## 4. ステータストークンとバッジ対応表

| 個別レポート `status` | reports/INDEX バッジ | | 実験 `status` | experiments/INDEX バッジ |
| :--- | :--- | :--- | :--- | :--- |
| `active` | 🟢 現結論の根拠 | | `planning` | 📋 計画中 |
| `superseded` | 🟡 部分置換(注記必須) | | `active` | 🔄 実施中 |
| `historical` | ⚪ 記録 | | `done` | ✅ 完了 |
| `planning` | 📋 計画中 | | `paused` | ⚪ 中断/保留 |

---

## 5. INDEX の登録と自動生成

INDEX ページは手書きせず、フロントマターをもとにスクリプトを実行して生成します。
レポートを追加または更新したら、必ず以下のスクリプトを実行してください。

```sh
# INDEX 表の再生成 (experiments/INDEX.md および各 reports/INDEX.md)
python tools/report_meta.py

# 整合性の検証のみを実行 (差分やエラーがあれば exit code 1)
python tools/report_meta.py --check
```

※ `<id>/reports/INDEX.md` と `experiments/INDEX.md` には、生成マーカー (`<!-- gen:...-index:start -->` および `:end -->`) が記述されている必要があります。
