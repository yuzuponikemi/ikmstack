# {{NOTEBOOK}} — ② 記録層（ラボノート）

実験・ログ・tips・決定の**版管理された記録**。3層運用の②。
ハーネス（skill・tool・規約）は持たず、**① ikmstack** の install を consume する。
プロダクトコード（③）はここではなく各プロダクト repo でクリーンに保つ。

## ハイブリッド運用（ノート型 ＋ サイドカー型）

- **ノート型**：実験・データ解析そのものは `experiments/E###_<topic>/` で**ここで回す**
  （実験一式が1ディレクトリに閉じる）。
- **サイドカー型**（任意）：プロダクト repo で作業した際の決定/ログを、プロダクトを汚さず
  ここへ集約する経路。`.lab-config.json` に意図を宣言（ルーティング実装は今後）。

## リポジトリ地図

| 場所 | 役割 |
|---|---|
| `experiments/INDEX.md` | 実験レジストリ（`report_meta.py` が自動生成） |
| `experiments/_template/` | 実験の雛形（`/exp-new` がコピー） |
| `experiments/E###_<topic>/` | 実験本体（PLAN/REPORT/MANIFEST/DECISIONS/reports/scripts） |
| `logs/<YYYY>/<date>_<topic>.md` | 日次・トピック単位のログ（`/lab-log`） |
| `tips/` | 現場知見・KB前段（`mechanism-*` / `method-*`） |
| `decisions/` | 横断的な方針決定の記録（任意） |
| `.lab-config.json` | このノートの設定（gitignore。`.template` が雛形） |
| `tools/`・`.githooks/` | **gitignore された symlink**（ikmstack から。git には入れない） |

## セットアップ（新しいマシンで）

```bash
# ① ハーネスを install（1回）
cd <path-to>/ikmstack && ./setup
# ② このノートを配線（tools/ + .githooks/ を symlink、gitignore 済）
./setup --notebook <path-to>/{{NOTEBOOK}}
```

これで `/exp-new` `/lab-log` `/exp-report` `/dr-audit` 等の ikmstack skills が
このノートで使える。

## 規約

ハーネスの使い方・実験ID/レポート/ログの書式は **ikmstack の AGENTS.md** が正本。
各 skill の `SKILL.md` にも手順が入っている。このノート固有の補足は本 README と
[AGENTS.md](AGENTS.md) に置く。
