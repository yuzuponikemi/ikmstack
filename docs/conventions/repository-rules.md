# リポジトリ共通規約 (詳細)

本ドキュメントは、リポジトリの運用ルールや構成に関する詳細な規定をまとめています。

---

## 1. ディレクトリ構成

リポジトリ内の各ファイル・ディレクトリの役割は以下の通りです。

```
logs/<YYYY>/<YYYY-MM-DD>_<topic>.md   # 日次・トピック単位 of ログ
tips/                                 # 装置運用の機序知識・解析の勘所(現場知見。KB前段)
  README.md                           # 索引と書式
  mechanism-*.md                      # 挙動・不具合の発生機序、トラブルシュート
  method-*.md                         # 解析・調査のやり方、再利用できるコツ
experiments/
  INDEX.md                            # 実験レジストリ(実験ID ↔ 状態 ↔ 要約)
  _template/                          # 実験テンプレート(コピーして使う)
  E###_<topic>/                       # 実験ID。
    PLAN.md                           # ★リビング★ 枠組み・仮説・成功基準 + 次の計画
    REPORT.md                         # ★リビング・唯一の現状サマリ★ 確定事実・現在の結論・未解決
    DECISIONS.md                      # (任意・長期のみ)方針転換の履歴。追記型・R番号なし
    regenerate.ps1                    # 図・自動レポートをローカル再生成(図は git に置かない)
    scripts/                          # 解析スクリプト
    reports/                          # 日付つき一次記録だけ(セッション/検証ごと。R番号あり・追記型)
      INDEX.md                        # レポート索引(状態バッジ + 1行要約)
      E###-R###_<YYYYMMDD>_<topic>.md # 1ファイル=1トピックの詳細レポート
      archive/                        # 旧版・自動生成 raw の退避先
    MANIFEST.md                       # 実験ID + データの所在(Drive)+ 関与リポジトリの commit SHA
    data/                             # ローカル作業用データ置き場(git 管理外)
tools/                                # リポジトリ共通ユーティリティ
  strip_nb_outputs.py                 # Notebook セル出力クリア
  report_meta.py                      # report フロントマター → INDEX.md 生成・検証
  check_report_figures.py             # 図リンクが gitignored 出力先を指すか検査
```

---

## 2. Notebook 規約 (Jupyter .ipynb)

Jupyter Notebook も **git にテキストとしてコミット**します。ただし、差分の肥大化や実行結果の混入を防ぐため、**セル出力 (計算結果・図・実行カウント) は必ずクリアして保存**します。

### 出力のクリア手順
- **手動クリア**: `python tools/strip_nb_outputs.py <nb.ipynb ...>`
- **確認のみ**: `python tools/strip_nb_outputs.py --check <nb.ipynb ...>`
- **自動クリア**: `.gitattributes` 内の `*.ipynb filter=nbstrip` 設定により、`git add` 時に自動でセル出力がクリアされます。

---

## 3. Google Drive 規約

- `experiments/<id>/` と同名のフォルダを Google Drive 側の `experiments\` に作成し、構造をミラーリングします。
- `MANIFEST.md` には Google Drive 上上のパス、ファイル名、おおよそのサイズ、取得日を正確に記録します。
- ローカルで一時的に使用するデータは、実験ディレクトリ下の `data/` （`.gitignore` 済み）に置いて構いません。

---

## 4. ログの書式

日次ログは `logs/<YYYY>/<YYYY-MM-DD>_<topic>.md` に記述します。1日に複数のトピックがある場合は、それぞれ別ファイルとして切り分けます。
ログは以下の見出し構成を最低限維持してください。

```markdown
# YYYY-MM-DD <トピック名>

## 目的
## やったこと
## わかったこと
## 次にやること
```
