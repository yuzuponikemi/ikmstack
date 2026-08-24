#!/usr/bin/env python3
"""出典 PDF をローカルに落とし、読むべきページ窓を推定する(検証の下ごしらえ).

**なぜ要るか**: 独立検証者 dr-verifier は Web 取得しか持たず、
(a) テキスト層の無い PDF を読めず、(b) 取得上限(10 MB)を超える PDF は取得すらできない。
業界の年次調査レポートは PDF が標準なので、**数値の裏取りが最も必要な領域で検証が届かない**
(実例: E007 で Hiscox と Art Basel & UBS の数値3件が unreachable になった)。

**このツールの責務は「読むべき場所の当たりをつける」ことだけ。**
本文の読み取りは検証者が Read ツールで PDF を直接読んで行う — ここで抽出したテキストを
判定の根拠にしてはならない。stdlib だけで書いた抽出は、フォント符号化によっては
静かに文字化けするため、**当たり(hint)としてのみ**使う(distrust-by-construction)。

依存: stdlib のみ(urllib / zlib / hashlib)。

使い方:
    python3 tools/dr/pdf_fetch.py <url>                      # 落として頁数と sha256 を出す
    python3 tools/dr/pdf_fetch.py <url> --find "51%"         # 読むべきページ窓を推定
    python3 tools/dr/pdf_fetch.py <path.pdf> --find "3,100"  # 既にあるファイルにも使える

終了コード: 0 = 成功 / 1 = 見つからない(--find 時) / 2 = 取得失敗
"""
from __future__ import annotations

import argparse
import hashlib
import re
import sys
import urllib.request
import zlib
from pathlib import Path

UA = "Mozilla/5.0 (compatible; ikmstack-dr-verifier/1.0)"
READ_WINDOW = 20  # Read ツールが 1 回で読める最大ページ数


def download(url: str, out: Path) -> Path:
    req = urllib.request.Request(url, headers={"User-Agent": UA})
    with urllib.request.urlopen(req, timeout=120) as resp, out.open("wb") as f:
        while chunk := resp.read(1 << 20):
            f.write(chunk)
    return out


def page_count(data: bytes) -> int:
    """/Type /Page の出現数を数える(/Pages は除く)。概算で足りる用途にのみ使う。"""
    return len(re.findall(rb"/Type\s*/Page(?![s])", data))


def _flate_streams(data: bytes):
    """FlateDecode のストリームを、ファイル内の出現順に復号して yield する。"""
    for m in re.finditer(rb"stream\r?\n", data):
        start = m.end()
        end = data.find(b"endstream", start)
        if end == -1:
            continue
        raw = data[start:end]
        try:
            yield zlib.decompress(raw)
        except zlib.error:
            continue  # 非 Flate(画像・生データ)は飛ばす


def _text_of(stream: bytes) -> str:
    """コンテンツストリームから、テキスト表示演算子のリテラル文字列だけを拾う。

    完全な PDF テキスト抽出ではない(CID フォント・16進文字列は取りこぼす)。
    当たりをつけるための近似であり、判定の根拠には使わない。
    """
    out: list[str] = []
    for m in re.finditer(rb"\((?:\\.|[^\\()])*\)", stream):
        s = m.group(0)[1:-1]
        s = re.sub(rb"\\([()\\])", rb"\1", s)
        out.append(s.decode("latin-1", errors="replace"))
    return " ".join(out)


def find_windows(data: bytes, needle: str) -> list[tuple[int, int, str]]:
    """needle を含むストリームの位置から、読むべきページ窓を推定する。

    ストリームはおおむねページ順に並ぶという経験則を使った**近似**。
    返り値は (窓の先頭ページ, 窓の末尾ページ, 前後の文脈) の列。
    """
    streams = list(_flate_streams(data))
    if not streams:
        return []
    pages = max(page_count(data), 1)
    norm_needle = re.sub(r"\s+", "", needle).lower()
    hits: list[tuple[int, int, str]] = []
    for i, st in enumerate(streams):
        text = _text_of(st)
        if not text:
            continue
        if norm_needle in re.sub(r"\s+", "", text).lower():
            approx = max(1, round((i + 0.5) / len(streams) * pages))
            lo = max(1, approx - READ_WINDOW // 2)
            hits.append((lo, min(pages, lo + READ_WINDOW - 1), " ".join(text.split())[:200]))
    return hits


def main() -> int:
    ap = argparse.ArgumentParser(description="出典 PDF を落として読むべきページ窓を推定する")
    ap.add_argument("target", help="PDF の URL、またはローカルパス")
    ap.add_argument("--find", help="探す文字列(空白は無視して照合)")
    ap.add_argument("--out", help="保存先(既定: カレントの pdf_fetch_<sha8>.pdf)")
    args = ap.parse_args()

    if re.match(r"^https?://", args.target):
        tmp = Path(args.out) if args.out else Path("pdf_fetch_download.pdf")
        try:
            download(args.target, tmp)
        except Exception as e:  # noqa: BLE001 - ネットワーク起因は理由を出して落とす
            print(f"[FATAL] 取得できない: {e}", file=sys.stderr)
            return 2
        path = tmp
    else:
        path = Path(args.target)
        if not path.is_file():
            print(f"[FATAL] ファイルが無い: {path}", file=sys.stderr)
            return 2

    data = path.read_bytes()
    digest = hashlib.sha256(data).hexdigest()
    if not args.out and re.match(r"^https?://", args.target):
        final = path.with_name(f"pdf_fetch_{digest[:8]}.pdf")
        path.replace(final)
        path = final

    pages = page_count(data)
    print(f"path   : {path}")
    print(f"size   : {len(data):,} bytes")
    print(f"sha256 : {digest}")
    print(f"pages  : {pages}(概算)")

    if not args.find:
        print("\n次: 検証者は Read ツールでこの PDF を直接読む(pages 引数でページ範囲を指定)。")
        return 0

    hits = find_windows(data, args.find)
    print(f"\n## '{args.find}' の当たり(hint。判定の根拠にはしない)")
    if not hits:
        print("  該当なし。抽出できない符号化の可能性があるので、"
              "Read でページ窓を総当たりして確認すること(『無い』と断定しない)。")
        return 1
    seen: set[tuple[int, int]] = set()
    for lo, hi, ctx in hits:
        if (lo, hi) in seen:
            continue
        seen.add((lo, hi))
        print(f"  Read の pages 引数に '{lo}-{hi}' を試す  … {ctx}")
    print("\n⚠ ページ番号は近似(ストリーム順からの推定)。外れたら前後の窓も読むこと。")
    return 0


if __name__ == "__main__":
    sys.exit(main())
