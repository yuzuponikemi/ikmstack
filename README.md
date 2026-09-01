# ikmstack

**① ハーネス層** — 研究・開発方法論の skill・tool・規約を一元管理する軸。
gstack の親戚。記録は持たず、`./setup` で各マシンに install して、記録層（②）や
各プロダクト repo（③）から consume する。

> このリポジトリだけを見れば、環境を**ゼロから再現**できる。install → 記録層作成 →
> 日々の運用 → ハーネス改善 まで、下記だけで完結する。

---

## 3層運用（ハーネス / 記録 / プロダクト）

開発環境を役割の異なる3層に分ける。**どこに何を置き、どこを編集するか**の最上位の判断軸。

| 層 | 実体 | 中身 | 公開度 |
|----|------|------|--------|
| **① 仕組み（ハーネス）** | **ikmstack**（この repo） | skill・tool・規約。`./setup` で global install | 公開可 |
| **② 記録（ラボノート）** | **ikmnote** 等（`./setup --init-notebook` で生成） | 実験・ログ・tips・決定。ハーネスは持たない（install を consume） | private |
| **③ プロダクトコード** | 各プロダクト repo | 出荷ソース。クリーンに保つ（ハーネスも記録も入れない） | 各自 |

**リトマス**：「再利用できる仕組みか」→① ikmstack /「知見・記録か」→② 記録層 /
「出荷ソースか」→③ プロダクト。

**なぜ分けるか**：ハーネスをプロダクトに同居（vendored）させると「どっちを編集」
「merge 衝突」が構造的に起きる。install モデルなら**ハーネスは1ソース**・作業は別 repo
で、プロダクトはクリーンに保てる。

規約の正本は [AGENTS.md](AGENTS.md)。ETHOS 的背景は記録層の
`tips/method-harness-record-product-architecture.md`（gstack を実例に）。

---

## クイックスタート（新しいマシンで、ゼロから）

前提：`bun` は不要。`git` と `python3`（macOS は `python` 未提供＝ python3 前提）。

```bash
# 0. このハーネスを clone
git clone https://github.com/yuzuponikemi/ikmstack.git ~/source/personal/ikmstack

# 1. ハーネスを install（skills → ~/.claude/skills、agents → ~/.claude/agents）
cd ~/source/personal/ikmstack && ./setup

# 2. 記録層（ラボノート）を一から作る ← 1コマンドで scaffold + git init + 配線
./setup --init-notebook ~/source/personal/ikmnote

# 3. 記録層を private repo にして push（任意・持ち運び用）
cd ~/source/personal/ikmnote
git add -A && git commit -m "init: ikmnote (records layer)"
gh repo create <owner>/ikmnote --private --source=. --remote=origin --push

# 4. 使い始める（記録層で Claude Code を開く）
#    /exp-new  新しい実験    /lab-log  日次ログ    /exp-report  レポート
```

既存の記録層 repo を別マシンで配線し直すだけなら：
```bash
cd ~/source/personal/ikmstack && ./setup           # install（1回）
./setup --notebook ~/source/personal/ikmnote       # tools/ + .githooks/ を symlink
```

---

## `./setup` のモード

| コマンド | 何をするか |
|----------|-----------|
| `./setup` | skills → `~/.claude/skills/<name>`、agents → `~/.claude/agents/` に symlink（冪等、トップレベル discovery）。install-path を `~/.ikmstack/install-path` に記録 |
| `./setup --prefix ikm-` | skills を `ikm-<name>` で名前空間化（衝突回避したいとき） |
| `./setup --init-notebook <dir>` | **記録層をゼロから作る**：構造＋`experiments/_template`＋INDEX＋README/AGENTS/CLAUDE＋.gitignore＋.lab-config＋`git init`＋配線。空でない dir は拒否（安全） |
| `./setup --notebook <dir>` | **既存**記録層を配線：`tools/`＋`.githooks/` を gitignore された symlink で張り、`core.hooksPath` を設定 |
| `./setup --sync-notebook <dir>` | **既存ノートにハーネスの更新を届ける**：`experiments/_template` の symlink 張り替え、`.gitignore` の管理ブロック更新、散文（AGENTS/CLAUDE/README）の差分報告。記録には触れない |
| `./setup --forget-notebook <dir>` | notebook の**登録だけ**を解除（記録は消さない）。既定は直近に wire したものへ繰り上がる |
| `./setup --status` | **install 状態を確認**：skills/agents の symlink 健全性、install-path、登録 notebook 一覧（`*` が既定）、総合判定を表示。「入ってるか分からない」時はこれ |
| `./setup --uninstall` | この install が張った global symlink を削除 |

記録層は `tools/`・`.githooks/`・`experiments/_template` を**この install への gitignore された
symlink**として持つ。**ハーネスが所有するものは必ず symlink で配る** — `cp` で配ると
更新が二度と届かず、既存ノートが静かに古くなる（実際に起きた: E003-R001）。
`.gitignore` はノート固有の行があるので、マーカで囲った**管理ブロックだけ**を同期する。
だから記録層の git には**記録だけ**が入り、skill の相対 `tools/…` 呼び出しと
INDEX/図リンクの pre-commit フックはそのまま動く。

**notebook は複数登録できる**（`--notebook` を複数回）。**その notebook の中で作業していれば
そこに書かれ**、プロダクト repo から書くときだけ「既定 = 最後に wire したもの」に集約される。
明示したいときは `--notebook <path|名前>` か環境変数 `IKMSTACK_NOTEBOOK`。

---

## skills（ハーネスが提供する動詞）

`./setup` 後、どの repo でも（特に記録層で）使える：

| skill | 用途 |
|-------|------|
| `/exp-new` | 実験を立ち上げ（`experiments/_template` をコピー、MANIFEST に SHA、PLAN 起草） |
| `/exp-report` | ハウススタイルでレポートを執筆・INDEX 登録 |
| `/exp-checkpoint` | 一区切りで living docs＋INDEX＋ログをまとめて最新化 |
| `/lab-log` | 日次ログ（目的/やったこと/わかったこと/次にやること） |
<!-- policy:lab-log-format@a0eca25e -->
| `/dr-plan` | 調査の主問いを下位問いへ分解し、決着条件つきの台帳にする（調査の起点） |
| `/dr-collect` | 出典を探索して2台帳（探索の記録・主張）を埋める（反証探索を含む） |
| `/dr-synth` | 台帳から論証を組み、確度・反証・未決着つきのレポートにする |
| `/dr-audit` | レポートの事実・数値を独立検証（主張台帳→出典照合→受入ゲート） |
| `/kb-promote` | 確定知見を共有ナレッジベースへ昇格 |
<!-- policy:kb-promotion@d1b964ea -->
| `/exp-deck` | レポートから共有用スライド（.pptx）を生成 |
| `/regen-outputs` | 図・自動レポートをローカル再生成（図は git に入れない） |
| `/report-checksum` | レポート1本の数値と図の計算過程を独立再計算で検算（左右2ペイン HTML） |
| `/readability-review` | そのレポート1本だけで読めるか（自走性）を隔離レビューで検査 |
| `/procedure-new` | 手順書を3層（Runbook / Principles / Notes）に起こす |
| `/runbook-review` | Runbook が「知らない人でも実行できる」原子性を満たすか関門にする |
| `/pr-review-doc` | 実装 PR を図解 HTML のレビューガイドにする（読者レベル較正あり） |
| `/harness-edit` | ハーネス自身（skill・AGENTS・conventions）を正本/写しの規律で改訂する |

agent：`dr-verifier`（主張を独立検証、`/dr-audit` が使う）。

**どこで起動しても正しい場所に着地する**（[記録のルーティング規約](docs/conventions/record-routing.md)）：
実験系（`/exp-new` `/exp-report` `/exp-checkpoint` `/exp-deck` `/regen-outputs`）は
起動元がどこでも**ノート根**で動く（プロダクト repo に `experiments/` を作らない）。
`/lab-log` だけは起動元に紐づけ、プロダクト repo なら `sidecar/<slug>/logs/` に集約する。

---

## ハーネスを改善する（3層運用の要）

**ハーネス改善は必ずここ（ikmstack）で行う。記録層やプロダクトには持ち込まない。**

```bash
cd ~/source/personal/ikmstack
# skill / tool / 規約 / setup / template を編集
./setup            # 再実行で symlink・install を更新（記録層は symlink 経由で自動反映）
git commit ... && git push
```

- skill は `python3 tools/…` を相対で呼ぶ（記録層の cwd から解決される）。
- 記録層で見つけたハーネス不具合も**ここで**直す（例：`python`→`python3`、フック改行/実行ビット）。
- **規約・スキルを直すときは `/harness-edit`**。1ルール=1正本＋写しのピン留めを
  `tools/policy_gate.py` が pre-commit で守る（対応表は `docs/conventions/policy-map.md`）。
  部品を足したら `python3 tools/harness_map.py` で棚卸しを再生成する。

---

## リポジトリ地図

```
.claude/skills/<skill>/SKILL.md   スキル本体（棚卸しは docs/harness-map.md が生成）
.claude/agents/*.md               サブエージェント（dr-verifier）
tools/                            report_meta.py / check_report_figures.py /
                                  sidecar.py（記録のルーティング）/
                                  strip_nb_outputs.py / dr/*（dr-audit 用）
                                  policy_gate.py / harness_map.py（ハーネス自己保守）/
                                  log_draft.py / retractions.py / synthesis_*.py /
                                  index_html.py / report_readview.py（読みビュー。
                                  調査台帳が隣にあれば claim/問い/出典を
                                  ホバーで確かめられる形で重ねる）
docs/conventions/                 reporting / figures-regen / repository-rules /
                                  record-routing（どこで起動しても正しく着地する規約）/
                                  policy-map + policy-registry.json（1ルール=1正本）
docs/harness-map.md               ハーネスの全体像と棚卸し（生成部は harness_map.py）
.githooks/pre-commit              INDEX↔フロントマター・図リンク・
                                  opt-in ゲート（.dr-gate / .numbers-gate）・ハーネス規約
experiments/_template/            実験の雛形（/exp-new がコピー）
experiments/INDEX.md              実験レジストリの空雛形（report_meta が生成）
notebook-template/                記録層の雛形（--init-notebook が {{NOTEBOOK}} 置換で展開）
setup                             install / --init-notebook / --notebook / --uninstall
AGENTS.md                         規約の正本（実験ID・レポート/ログ書式・Drive・KB）
docs/ONBOARDING.md                新規参加者向けの読む順（層構成・ツアー・複雑箇所）
```
<!-- policy:nb-strip-outputs@3ca1441e -->
<!-- policy:dr-gate-opt-in@fd4434e1 -->

初めてこの repo を読むなら [docs/ONBOARDING.md](docs/ONBOARDING.md) が最短経路
（`/understand` のナレッジグラフから生成。グラフ本体 `.ua/` は生成物なので git には入れない）。

---

## 名前（naming）

役割で名前を分けている。「note ＝ 記録」なので**記録層は `ikmnote`**、
機械（skill・tool・規約）である**ハーネスは `ikmstack`**（gstack の親戚）。
どちらを触るべきかが名前で分かるようにするのが狙い。
