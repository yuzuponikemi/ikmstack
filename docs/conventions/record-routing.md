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

**実験系 skill**（`/exp-new` `/exp-report` `/exp-checkpoint` `/exp-deck` `/regen-outputs`）は
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

## 設計の背景

- E001_sidecar-routing（v1）で `/lab-log` のサイドカー分岐を実装・検証した。
- v2 でカバーした穴：**実験系 skill を他 repo から起動したときの汚染**、
  **複数 notebook**、**resurfacing**。
- 「ツールは cwd 基準」の原則（install モデルでは `__file__` が symlink で張り付く）は
  記録層 tips `method-install-model-cwd-resolution.md` を参照。
