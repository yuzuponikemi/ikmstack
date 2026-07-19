# 図と regenerate.ps1 の規約(R1〜R3)

> AGENTS.md「三大原則 #1(git はテキスト + 生成スクリプトだけ)」の詳細。
> 図を git に載せず、生データ(Drive)+ スクリプト(git)+ SHA(MANIFEST)で再現する運用の機械的ルール。

## 図は git に置かない

- **生データ・大容量・完成形の図付きレポート** → Google Drive(正本)、`MANIFEST.md` からリンク。
- **図(プロット)** → git に置かない。各実験の **`regenerate.ps1`** を 1 回流せば、
  生データから決定論的に再生成され、レポートを図付きでローカルプレビューできる
  (出力先は `.gitignore` 済 = `_generated/` などの出力先)。
- 目安: 1 ファイル 1 MB 超・再現不能・手編集物は Drive へ。
- **再現性の鍵は「生データ(Drive)+ スクリプト(git)+ commit SHA(MANIFEST)」**。

## regenerate.ps1 と図リンクが満たすべき3条件(必須)

`tools/check_report_figures.py` で検査します。次を機械的に守ります:

- **R1(入力は Drive 正本)**: `regenerate.ps1` と各スクリプトの入力は **Drive の生データを直接**
  読む。`D:\...` のような **PC 固有ローカルパスを入力の正本にしない**(別 PC・clone で再現不能になる)。
  PC 差はドライブレターのみとし、env / `-DriveRoot` で上書きできるようにする。データが無ければ
  「Drive を同期せよ(MANIFEST 参照)」で fail する。
  - **R1b(未取得データは fail ではなく skip)**: 事前登録(`status: planning`)で**まだ測定していない**
    解析スクリプトは、入力欠如時に `exit 1`(失敗)ではなく **`exit 2`(SKIP)** を返す。`regenerate.ps1`
    は `exit 2` を `$skipped`(「データ未取得・事前登録」)に振り分け、`$fail`(本物の破損)と区別する。
- **R2(出力は単一の gitignored ディレクトリ)**: 図の出力先は実験ごとに1つに揃える。
  新規実験は **`_generated/`**(テンプレ標準)。
- **R3(レポートの図リンクは出力先だけを指す)**: `REPORT.md` / `reports/**.md` の図リンクは
  上記出力ディレクトリ配下を、**各ファイルの位置から正しい相対深さ**で指す
  (例 `reports/x.md` → `../_generated/...`、`reports/archive/x.md` → `../../_generated/...`)。
  `tools/check_report_figures.py` がこれを検査し、pre-commit で commit を止める。
