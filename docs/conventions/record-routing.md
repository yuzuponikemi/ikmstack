# 記録のルーティング規約（サイドカー経路 v2）

「**どこで起動しても、記録は記録層に着地し、プロダクト repo は汚れない**」を保証する規約。
実体は [`tools/sidecar.py`](../../tools/sidecar.py)。3層運用そのものは [AGENTS.md](../../AGENTS.md) 参照。

## 解決の2軸

書き先は **scope（何を書くか）× mode（今どこにいるか）** で決まる。

| scope | 対象 | 書き先 | 理由 |
|---|---|---|---|
| `log` | 日次ログ（`/lab-log`） | mode に従う（下表） | ログはセッション＝作業した repo に紐づく |
| `experiment` | 実験一式（`experiments/E###_*`） | **常にノート根** | 実験は本質的に cross-repo。関与 repo は `MANIFEST.md` に複数書く。1つの `sidecar/<slug>/` に閉じ込めると嘘になる |

| mode | 判定 | `scope=log` の書き先 |
|---|---|---|
| `notebook` | cwd が登録 notebook 配下 | `<notebook>/logs/<YYYY>/` |
| `sidecar` | それ以外（プロダクト repo 等） | `<notebook>/sidecar/<slug>/logs/<YYYY>/` |

`slug` は cwd の git remote(origin) を正規化した `owner-repo`（SSH/HTTPS は同一キーに畳む）。
remote が無ければ toplevel のディレクトリ名。

## skill 側の作法

**実験系 skill**（`/exp-new` `/exp-report` `/exp-checkpoint` `/exp-deck` `/exp-artifact` `/regen-outputs`）は
相対パスで `tools/…` `experiments/…` を呼ぶ。プロダクト repo から起動されるとそこに
`experiments/` を作ってしまう（＝③ を汚す）ので、**必ず先にノート根へ cd する**：

```bash
cd "$(python3 "$(cat ~/.ikmstack/install-path)/tools/sidecar.py" notebook)"
```

**ログ系 skill**（`/lab-log`）は書き先ディレクトリだけを受け取る（cd しない）：

```bash
python3 "$(cat ~/.ikmstack/install-path)/tools/sidecar.py" ensure      # → 書き先の logs ディレクトリ
```

install-path 経由で呼ぶのは、プロダクト repo には `tools/` の symlink が無いため。

## 複数 notebook

`~/.ikmstack/notebooks`（1行1パス・wire 順）に配線済みを全部持ち、
`~/.ikmstack/notebook` が **既定**（＝ sidecar 記録の集約先。最後に wire したもの）。

解決順：

1. `--notebook <path|名前>` または環境変数 `IKMSTACK_NOTEBOOK`（明示指定が最優先）
2. cwd を含む登録 notebook（入れ子なら最も深いもの）→ `mode=notebook`
3. 既定 notebook → `mode=sidecar`

つまり **notebook A の中で作業していれば A に書かれる**（既定が B でも間違えない）。
プロダクト repo から書くときだけ既定が効く。一覧は `sidecar.py list` / `setup --status`。

## resurfacing（過去記録の提示）

その repo に戻ってきたとき、過去の記録を見失わないための呼び出し：

```bash
python3 "$(cat ~/.ikmstack/install-path)/tools/sidecar.py" recent --limit 5
```

cwd の slug に紐づく過去ログ（新しい順）と、`MANIFEST.md` がその repo に言及している
関連実験を返す。`/lab-log` は Step 0 でこれを見て、**同日同トピックなら追記**・
継続作業なら前回ログを踏まえる。

## ノート側の地図が持つ skill 一覧（harness-skills マーカ）

記録層の地図（`workspace-map.CLAUDE.md` や `CLAUDE.md`）は、ハーネスの skill 一覧を
**手書きの写し**として持つことがある。この写しは構造的に腐る — skill の増減は必ず
① ハーネス側で起きるが、そのとき ② ノートの地図は別 repo にあって視界に入らない。

そこで、**網羅のつもりの一覧はマーカで宣言する**：

```markdown
<!-- harness-skills:begin -->
… `/exp-new` `/lab-log` … （網羅一覧。skill は `` `/name` `` 形式で書く）
<!-- harness-skills:end -->
```

- 宣言された領域だけを `tools/notebook_map.py` が実体（`.claude/skills/*/SKILL.md`）と
  照合する。囲まれていない言及（README の例示など）は検査しない。
  「網羅のつもり」と「例として挙げただけ」は機械に区別できないので、書き手が宣言する。
- 領域内では skill を **`` `/name` `` 形式**（バッククォートで囲み、スラッシュ始まり）
  で書く。これが列挙の目印になる。`ikmstack/tools/foo.py` のようなパスを
  skill 名と誤認しないため、バッククォート直後がスラッシュであることまで要求する。
- 検査は **① ハーネス側の pre-commit** で走る。ドリフトを作った側のコミットで
  気づかせるため。ノートは別 repo で、そこでは直せないので**警告のみ**（コミットは通る）。

```bash
python3 tools/notebook_map.py           # 検査（警告のみ）
python3 tools/notebook_map.py --strict  # 差分があれば exit 1
```

一覧を写さずに済むならそれが最善（正本は `./setup --status`）。
マーカは「それでも読み物として一覧を置きたい」場合の担保である。

## 多台運用（複数マシンで同じハーネス＋ノートを使う）

repo が2つあることは、実は負担の主因ではない。**ikmstack は「たまに pull するだけ」**
（改修は1台で行う）で、毎日同期が要るのは記録層だけ。仮に1 repo に統合しても
記録の同期は同じだけ発生する。統合は公開度（ハーネスは公開／記録は private）と
install モデル（`~/.claude/skills` は ikmstack への symlink）を壊すので採らない。

代わりに、多台運用の痛点を3つ潰す。

### ① 一括同期 — `./setup --sync`

```bash
./setup --sync
```

ハーネスと `~/.ikmstack/notebooks` の全ノートを fetch し、`--ff-only` で pull する。
**未コミットがある repo は触らない**（記録を優先し、勝手に巻き込まない）。
ff-only で通らない＝分岐している場合は、そう報告して手作業に委ねる。

### ② 状態の可視化 — `./setup --status`

多台運用でいちばん痛いのは衝突そのものではなく、**A機で push し忘れて B機で
作業を始め、分岐すること**。`--status` は各 repo の「未push / 未pull / 未コミット」を
出す。**fetch はしない**（遅い・ネットワークが要る）ので、未pull の数は
「前回 fetch 時点」であることを明示する。fetch するのは `--sync` だけ。

### ③ 記録層の自動 push（opt-in、既定は無効）

```bash
cd <ノート> && git config --bool ikmstack.autopush true
```

`.githooks/post-commit` がコミット後に push する。記録層は追記中心で、マシンごとに
触るファイルが違う（`experiments/E###/`・`logs/<年>/<日付>_<topic>.md`）ため、
衝突リスクより分岐を防ぐ利得が上回る。**ハーネス側は既定のまま無効にしておく**
—— ハーネスの変更は全マシン・全ノートへ即座に波及するので、push は意図的に行う。

### 生成物はマージせず再生成する

`experiments/INDEX.md` は `tools/report_meta.py` が全実験の `REPORT.md` から
決定論で作る**生成物**。行を突き合わせても正しくならないうえ、2台で別々の実験を
作れば毎回衝突する。そこで:

- `.gitattributes`（ハーネス管理ブロック）で `experiments/INDEX.md merge=union` を宣言し、
  **衝突させずに素通し**する。
- 直後に `.githooks/post-merge` が `report_meta.py` を走らせ、**作り直した内容で上書き**する。

二重帳簿パターン（生成部は機械が作り、人間は narrative だけ書く）を、マージにも
適用したもの。同じ理屈が当てはまる生成物が増えたら、両ブロックに足す。

## 設計の背景

- E001_sidecar-routing（v1）で `/lab-log` のサイドカー分岐を実装・検証した。
- v2 でカバーした穴：**実験系 skill を他 repo から起動したときの汚染**、
  **複数 notebook**、**resurfacing**。
- 「ツールは cwd 基準」の原則（install モデルでは `__file__` が symlink で張り付く）は
  記録層 tips `method-install-model-cwd-resolution.md` を参照。
