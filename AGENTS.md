# AGENTS.md

AI コーディングエージェント向けのリポジトリ規約。
対応: Claude Code, Cursor, GitHub Copilot, Gemini CLI ほか AGENTS.md 互換ツール。

## このリポジトリは何か

検証・開発ログのハブ。複数リポジトリにまたがる実験・検証・データ解析の
「計画 → スクリプト → 結果まとめ」を一元管理する。

ナレッジベース（KB）とは役割が異なる:

| リポジトリ | 役割 | ライフサイクル |
|---|---|---|
| 本リポジトリ | 検証ログ・実験記録・解析スクリプト | 追記中心、雑多でよい |
| 共有ナレッジベース (KB) | 蒸留された恒久知識 | 推敲して安定させる |
| Google Drive | 生データ・大容量の解析結果 | git には入れない |

## 3層運用（ハーネス / 記録 / プロダクト）

開発環境は役割の異なる3層に分ける。**どこを編集するか**の最上位の判断軸。

| 層 | 役割 | 実体 | 編集する場所 |
|---|---|---|---|
| ① 仕組み（ハーネス） | 再利用できる skill・tool・規約 | **ikmstack**（このリポジトリ = 正典） | **ikmstack** で編集し、`setup` で各マシンに install / 更新する |
| ② 記録（ラボノート） | 実験・ログ・tips・決定の版管理された記録 | **ikmnote**（記録層。ハイブリッド：ノート＋サイドカー） | **ikmnote のみ**。ハーネスは持ち込まない（ikmstack の install を consume する） |
| ③ プロダクトコード | 出荷するソース | 各プロダクトリポジトリ | クリーンに保つ（ハーネスも記録も入れない） |

**リトマス**：「再利用できる仕組みか」→① ikmstack /「知見・記録か」→② ikmnote /「出荷ソースか」→③ プロダクト。

- ハーネス改善は必ず ① ikmstack で行い、`setup` の再実行で各マシン・各記録層に反映する。実体で直して急ぐ場合も、汎用部分は後で ikmstack へ backport する（cherry-pick。実体固有のコンテンツ・ブランドは混ぜない）。
- **記録の書き先は起動場所に依らず自動で決まる**（skill が `tools/sidecar.py` で解決する）。
  実験一式は**常にノート根**（cross-repo なので `sidecar/` に閉じ込めない。関与 repo は
  `MANIFEST.md` に書く）、日次ログだけは起動元 repo に紐づけて
  `sidecar/<slug>/logs/` に集約する。**③ プロダクトには絶対に書かない**。
  規約は [docs/conventions/record-routing.md](docs/conventions/record-routing.md)。
- 背景の詳細は ikmnote の `tips/method-harness-record-product-architecture.md` を参照。

## 三大原則

1. **git はテキスト + 生成スクリプトだけ**。図やデータ(CSV・画像・動画・バイナリ)は
   git に入れず、**生成スクリプトでローカル再現できる**状態にする。
   - **生データ・大容量・完成形の図付きレポート** → Google Drive(正本)、`MANIFEST.md` からリンク。
   - **図(プロット)** → git に置かない。各実験の **`regenerate.ps1`** を 1 回流せば、
     生データから決定論的に再生成され、レポートを図付きでローカルプレビューできる
     (出力先は `.gitignore` 済 = `_generated/` などの出力ディレクトリ)。
   - 目安: 1 ファイル 1 MB 超・再現不能・手編集物は Drive へ。
   - **再現性の鍵は「生データ(Drive)+ スクリプト(git)+ commit SHA(MANIFEST)」**。
     図そのものを git で運ぶのではなく、図を作る手順を git で運ぶ。
   - `regenerate.ps1` と図リンクが満たすべき3条件(R1〜R3、`tools/check_report_figures.py` で検査)は
   <!-- policy:figures-not-in-git@97b4297f -->
     **[docs/conventions/figures-regen.md](docs/conventions/figures-regen.md)** に従う。

2. **実験は 1 ディレクトリに閉じる**。`experiments/_template/` をコピーして始める。

3. **ベース資料を常に最新・整然に保つ(エントロピー最小が最優先)**。
   `MANIFEST.md` / `PLAN.md` / `REPORT.md` は実験の「現在の正」を映す資料。
   状況が変わったら**その場で更新**し、古びた記述・前提で読み手を混乱させない。
   情報を整理してエントロピーを下げ、整然と保つことが、他のどの体裁よりも優先する。
   - **確定した事実と、意見・仮説・暫定値を混ぜない**(見出し・語頭ラベルで切り分ける)。
   - **詰め込みで不親切にしない**(語を補い節を分ける)。レポートの長さに上限は設けない —
     **整然さが最優先**で、量が増えたら**話題ごとに 1 個別レポートに分ける**(`reports/` に
     1 トピック 1 ファイルで足す)。**個別レポート(`reports/E###-R###`)は
     <!-- policy:report-naming-numbering@eb565f44 -->
     1 本で自走的に読める**よう前提・用語・手法を再共有してよい(読みやすさ > 重複回避)。
     逆に `REPORT.md` は現状サマリ 1 本に保つ。詳細 → reporting.md / exp-report。
   - 運用の詳細(1機能=1権威の文書分け・事実/仮説の分離・鮮度維持)は
   <!-- policy:living-vs-primary@134848f4 -->
     **[docs/conventions/reporting.md](docs/conventions/reporting.md)** に分離。

## 実験 ID と 命名規約

- **実験 ID** = `E###_<topic-slug>`(ディレクトリ名。日付は付けない — 着手日は
  `PLAN.md` の日付・`MANIFEST.md` の記録日・`REPORT.md` の期間で追える)。デフォルトの Experiment ID プレフィックスは `E`（E001, E002, …）。
- **レポート ID** = `E###-R###`。`E###` は実験ID、`R###` は
  **その実験内で 1 から振る通し連番**(R001, R002, …)。改訂版は新 R 番号にせず
  `<元名>_rev.md` とし、原本を残す(exp-report 参照)。欠番・採番済みは
  `reports/INDEX.md` が真実。次番号は INDEX の最大 R+1。
  - **R 番号は「日付つき一次記録」だけに振る**(書き換えない追記型)。`PLAN.md` /
    `REPORT.md` / `DECISIONS.md` のような**書き換えて最新を保つリビング文書には R を振らない**
    (単数正規名のまま)。追記型(R番号)とリビング型(正規名)を命名で区別する。
- **3 ファイル全てに実験 ID を書く**:
  - `PLAN.md` 冒頭: `**実験ID**: E###_<topic>`
  - `MANIFEST.md` 冒頭: `実験ID: E###_<topic>`
  - `REPORT.md` 冒頭の **YAML フロントマター**: `experiment_id: E###_<topic>` ほか
  <!-- policy:frontmatter-schema@6e2e1a63 -->
    (書式は exp-report スキル参照)
- **横断レジストリ** `experiments/INDEX.md` の一覧表は、各 `REPORT.md` のフロントマターから
  `python tools/report_meta.py` が生成する(手編集しない。マーカ間のみ書き換わる)。
  状態・要約を変えたいときは REPORT.md のフロントマターを直してスクリプトを回す。
- **ファイル名規約**: 実験直下の単数リビング文書(`PLAN.md` / `MANIFEST.md` / `REPORT.md` /
  任意の `DECISIONS.md`)は **ID を付けず正規名のまま**にする。一方 `reports/` 配下の
  **1実験に多数ある一次記録は `E###-R###` で一意名**にする。

## 詳細規約(段階的開示・`docs/conventions/`)

頻繁には要らない機械的詳細はここに分離。**該当作業のときに開く**:

| 文書 | いつ読む |
|---|---|
| [docs/conventions/repository-rules.md](docs/conventions/repository-rules.md) | ディレクトリ構成・Notebook 規約・Google Drive 規約・ログの書式を確認するとき |
| [docs/conventions/figures-regen.md](docs/conventions/figures-regen.md) | 図・`regenerate.ps1`・図リンクを書く/直すとき(R1〜R3、三大原則#1の詳細) |
| [docs/conventions/reporting.md](docs/conventions/reporting.md) | レポート/plan を書くとき(1機能=1権威・命名/R番号・事実/仮説の分離・撤回の記録・検証ゲート・鮮度維持) |
| [docs/conventions/record-routing.md](docs/conventions/record-routing.md) | 記録がどの層に着地するか迷ったとき(ノート根 / sidecar の振り分け正本) |
| [docs/conventions/policy-map.md](docs/conventions/policy-map.md) | 規約そのものを直すとき(1ルール=1正本の対応表。改訂手順は harness-edit スキル) |
| [docs/harness-map.md](docs/harness-map.md) | ハーネスの全体像を思い出したいとき・部品(スキル/ゲート/ツール)を足すとき(棚卸しは `python tools/harness_map.py` が生成・pre-commit が鮮度を検査) |

## レポートの構成(要点。詳細 → [docs/conventions/reporting.md](docs/conventions/reporting.md))

**1機能=1権威**。同じ役割の文書を2つ作らない。
- **リビング文書(R番号なし・正規名。常に最新化)**: `REPORT.md` (現状サマリ・最初に読む唯一の権威) / `PLAN.md` (計画) / `DECISIONS.md` (決定履歴)。
- **一次記録 `reports/E###-R###_*.md` (R番号あり・追記型)**: 各セッション/検証ごとの詳細な根拠・数値・図リンク。

## 実験のワークフロー

1. `experiments/_template/` を `experiments/E###_<topic>/` にコピーする(`/exp-new`)
2. `PLAN.md` に 実験ID / 目的・仮説・成功基準・関与リポジトリを書く
3. 着手時に `MANIFEST.md` へ 実験ID と関与リポジトリの commit SHA を記録する
   (`git -C ../<repo> rev-parse --short HEAD`)。再現性はこれで担保する
   (サブモジュールは使わない)
4. データは Drive の対応フォルダに置き、`MANIFEST.md` にパス・サイズ・取得日を記録する
5. `REPORT.md` にフロントマターを書き、`python tools/report_meta.py` で `experiments/INDEX.md` を生成する
6. **各セッション/検証の結末は一次記録 `reports/E###-R###_<YYYYMMDD>_<topic>.md`(フロントマター付き)に書き、`python tools/report_meta.py` で `reports/INDEX.md` を再生成する**
   (整合確認のみなら `python tools/report_meta.py --check`。pre-commit も同じ検査を回す)
7. 区切りで **`REPORT.md`(現状サマリ)を最新の結論に更新**する(覆った結論を残さない。`/exp-checkpoint`)。
   `MANIFEST.md` / `PLAN.md`(長期なら `DECISIONS.md` も)が現実とずれていないか確認する。
   確定した恒久知識は KB へ昇格する(`/kb-promote`。任意)

## 知見の昇格(tips → KB)

- **`tips/`** は現場知見の前段。挙動・不具合の発生機序(`mechanism-*.md`)と、
  再利用できる調査・解析のやり方(`method-*.md`)を、雑でよいので早く書く。
- **KB**(共有ナレッジベース)は蒸留された恒久知識。実験の結論が固まったら
  `/kb-promote` で昇格させ、昇格先を元レポートから逆リンクする。
- 昇格の基準は「**他の実験・他の人が前提として使えるまで確定したか**」。
  確定していない知見は tips とレポートに留め、KB に上げない。

## スクリプト規約(.ps1 / .py ほか実行コード)

**スクリプトの中身は全部英語で書く**(コメント・出力メッセージとも)。
日本語は レポート / ログ / ドキュメント側に書き、実行コードには入れない。
理由: 実機・計測PCの CP932 コンソールで文字化け・PowerShell 5.1 の ParseException の
温床になるため。どうしても日本語が必要な対話メッセージ等のみ **UTF-8 BOM 付き**(次善策)。

**機械強制の範囲**: 最悪ケース(実機/計測PCで走るスクリプトの起動不能)を確実に止めるため、
`tools/check_script_encoding.py` が `experiments/<id>/scripts/**/*.ps1` を検査し、
**非ASCII かつ BOM なし**(=CP932/PS5.1 で ParseException する形)を pre-commit で弾く
(ASCII が第一選択、UTF-8 BOM は許容)。開発PC専用コード(解析/作図 `.py`・`regenerate.ps1`・
`tools/` 等。Python3/PS7 は UTF-8 を正しく読み、図ラベルの日本語は意図的)は機械強制の対象外だが、
上の「英語で書く」原則自体は全実行コードに適用する。

## 複数リポジトリにまたがる作業

- 横断検証のセッションは ② 記録層(ノート)で起動するのが基本。③ プロダクト repo から
  起動した場合も、記録は `tools/sidecar.py` がノート側へ振り分ける(③ は無変更のまま)。
- 隣接リポジトリの地図は親フォルダの `CLAUDE.md`(ワークスペース地図)を参照する。
- 横断作業で隣のリポジトリが必要になったら `/add-dir ../<repo>` を提案してよい。

