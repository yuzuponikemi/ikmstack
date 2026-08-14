#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""pr_merge_guard.py — PreToolUse guard: PR は draft 作成まで・マージはユーザー承認後。

Why this exists
---------------
2026-07-19 のフィードバック「勝手にマージまでやらないで、draft PR を作ったところで
聞いてほしい」を、記憶(弱いガード)でなくフック(構造ガード)で強制する。
フックは判定を出すだけ、壊れたら permissions.ask の
backstop(`Bash(gh pr merge:*)` 等)に自動回帰する(fail-open-to-ask)。

Decision (PreToolUse hookSpecificOutput.permissionDecision):
  * gh pr merge / gh api …/merge / mergePullRequest (GraphQL):
        通常                       -> deny (draft PR を作って停止し、ユーザーに委ねる)
        break-glass マーカー付き    -> ask  (ユーザーの承認プロンプトが最終確認になる)
        break-glass = コマンドに PR_MERGE_APPROVED=1 を含める(bash なら
        `PR_MERGE_APPROVED=1 gh pr merge …`)。silent allow は絶対に出さない。
  * gh pr create で --draft/-d 無し -> deny (--draft を付けて再実行させる)
  * それ以外                        -> 何も出さない(通常フローに委ねる)

Note: push-to-main の ask 判定は意図的に持たない。記録層は main 直コミット運用で、
そこに ask を挟むと承認プロンプトの主因になるため。main 保護は本ガードの
マージ deny + draft 強制(PR レビュー経路)で担う。

Fail-safe by construction: 例外時・パース不能時は何も emit せず終了する。
このスクリプトが消えても、settings.json 側のラッパー(`[ -f … ] && python …`)と
ask backstop が守る。登録は setup-runbook §3.4 / 検査は env_doctor。

stdlib only. 監査: 判定を 1 行 JSON で ~/.claude/pr-guard-audit.jsonl に追記(best-effort)。
"""
from __future__ import annotations

import json
import os
import re
import sys
from datetime import datetime, timezone

AUDIT = os.path.join(os.path.expanduser("~"), ".claude", "pr-guard-audit.jsonl")

MERGE_RE = re.compile(r"\bgh\s+pr\s+merge\b")
API_MERGE_RE = re.compile(
    r"\bgh\s+api\b.{0,400}?(pulls/[^\s/'\"]+/merge\b|mergePullRequest|merge_method)",
    re.IGNORECASE | re.DOTALL,
)
CREATE_RE = re.compile(r"\bgh\s+pr\s+create\b")
DRAFT_RE = re.compile(r"(^|\s)(--draft|-d)\b")
BREAKGLASS_RE = re.compile(r"PR_MERGE_APPROVED\s*[:=]\s*['\"]?1")


def _audit(record: dict) -> None:
    try:
        record["ts"] = datetime.now(tz=timezone.utc).isoformat(timespec="seconds")
        with open(AUDIT, "a", encoding="utf-8") as fh:
            fh.write(json.dumps(record, ensure_ascii=False) + "\n")
    except Exception:
        pass


def _emit(decision: str, reason: str) -> None:
    print(
        json.dumps(
            {
                "hookSpecificOutput": {
                    "hookEventName": "PreToolUse",
                    "permissionDecision": decision,
                    "permissionDecisionReason": reason,
                }
            },
            ensure_ascii=False,
        )
    )


def handle(command: str, cwd: str | None) -> None:
    breakglass = bool(BREAKGLASS_RE.search(command))

    if MERGE_RE.search(command) or API_MERGE_RE.search(command):
        if breakglass:
            _audit({"decision": "ask", "kind": "merge-breakglass", "command": command[:500]})
            _emit(
                "ask",
                "PR merge with break-glass marker — the user's approval on this prompt "
                "is the final confirmation (pr-draft-then-ask policy).",
            )
        else:
            _audit({"decision": "deny", "kind": "merge", "command": command[:500]})
            _emit(
                "deny",
                "PR merge is user-gated (pr-draft-then-ask): create a DRAFT PR, report "
                "it, and stop. If the user has explicitly said to merge, re-run with "
                "PR_MERGE_APPROVED=1 prefixed so their approval prompt confirms it.",
            )
        return

    if CREATE_RE.search(command) and not DRAFT_RE.search(command):
        _audit({"decision": "deny", "kind": "create-non-draft", "command": command[:500]})
        _emit(
            "deny",
            "PRs must be created as drafts (pr-draft-then-ask): add --draft to "
            "gh pr create, then report the PR URL and stop.",
        )
        return


def main() -> None:
    try:
        raw = sys.stdin.read()
        payload = json.loads(raw) if raw.strip() else {}
        if payload.get("tool_name") not in ("Bash", "PowerShell"):
            return
        command = (payload.get("tool_input") or {}).get("command") or ""
        if not command:
            return
        handle(command, payload.get("cwd"))
    except Exception:
        return  # emit nothing -> ask backstop / normal flow (fail-safe)


if __name__ == "__main__":
    main()
